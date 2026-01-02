from __future__ import annotations
"""Calendar service for event management and iCal feed generation."""
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting, RecurrenceType, MeetingStatus
from app.models.tenant import Tenant


class CalendarService:
    """
    Service for calendar operations including:
    - Event CRUD with date range queries
    - Recurring event expansion
    - iCal/ICS feed generation
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_events(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime,
        include_cancelled: bool = False,
        expand_recurring: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get events within a date range.
        Optionally expands recurring events into instances.
        """
        # Base query
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.start_time >= start_date,
                Meeting.start_time <= end_date
            )
        )
        
        if not include_cancelled:
            stmt = stmt.where(Meeting.status != MeetingStatus.CANCELLED.value)
        
        stmt = stmt.order_by(Meeting.start_time)
        
        result = await self.db.execute(stmt)
        meetings = result.scalars().all()
        
        events = []
        
        for meeting in meetings:
            events.append(self._meeting_to_dict(meeting))
        
        # Also check for recurring meetings that started before the range
        if expand_recurring:
            recurring_events = await self._get_recurring_instances(
                tenant_id, start_date, end_date
            )
            events.extend(recurring_events)
        
        # Sort by start time
        events.sort(key=lambda e: e["start_time"])
        
        return events
    
    def _meeting_to_dict(self, meeting: Meeting) -> Dict[str, Any]:
        """Convert meeting to dictionary."""
        return {
            "id": str(meeting.id),
            "title": meeting.title,
            "description": meeting.description,
            "location": meeting.location,
            "start_time": meeting.start_time.isoformat(),
            "end_time": meeting.end_time.isoformat() if meeting.end_time else None,
            "is_all_day": meeting.is_all_day,
            "timezone": meeting.timezone,
            "color": meeting.color,
            "icon": meeting.icon,
            "priority": meeting.priority,
            "status": meeting.status,
            "attendee_name": meeting.attendee_name,
            "attendees": [{"name": a} if isinstance(a, str) else a for a in (meeting.attendees or [])],
            "is_recurring": meeting.is_recurring,
            "recurrence_type": meeting.recurrence_type,
            "parent_id": str(meeting.parent_meeting_id) if meeting.parent_meeting_id else None,
        }
    
    async def _get_recurring_instances(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Expand recurring meetings into virtual instances."""
        # Get recurring meetings that started before range and might have instances in range
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.recurrence_type != RecurrenceType.NONE.value,
                Meeting.parent_meeting_id.is_(None),
                Meeting.start_time < start_date,
                or_(
                    Meeting.recurrence_end_date.is_(None),
                    Meeting.recurrence_end_date >= start_date
                )
            )
        )
        
        result = await self.db.execute(stmt)
        recurring = result.scalars().all()
        
        instances = []
        
        for meeting in recurring:
            expanded = self._expand_recurrence(meeting, start_date, end_date)
            instances.extend(expanded)
        
        return instances
    
    def _expand_recurrence(
        self,
        meeting: Meeting,
        start_date: datetime,
        end_date: datetime,
        max_instances: int = 100
    ) -> List[Dict[str, Any]]:
        """Generate instances for a recurring meeting within date range."""
        instances = []
        
        current = meeting.start_time
        duration = meeting.end_time - meeting.start_time if meeting.end_time else timedelta(hours=1)
        rec_type = meeting.recurrence_type
        interval = meeting.recurrence_interval or 1
        
        # Calculate time deltas
        if rec_type == RecurrenceType.DAILY.value:
            delta = timedelta(days=interval)
        elif rec_type == RecurrenceType.WEEKLY.value:
            delta = timedelta(weeks=interval)
        elif rec_type == RecurrenceType.BIWEEKLY.value:
            delta = timedelta(weeks=2)
        elif rec_type == RecurrenceType.MONTHLY.value:
            delta = timedelta(days=30 * interval)  # Approximation
        elif rec_type == RecurrenceType.YEARLY.value:
            delta = timedelta(days=365 * interval)
        else:
            return []
        
        count = 0
        while current <= end_date and count < max_instances:
            # Check end conditions
            if meeting.recurrence_end_date and current > meeting.recurrence_end_date:
                break
            if meeting.recurrence_count and count >= meeting.recurrence_count:
                break
            
            # Add if in range
            if current >= start_date:
                instance = self._meeting_to_dict(meeting)
                instance["start_time"] = current.isoformat()
                instance["end_time"] = (current + duration).isoformat()
                instance["is_instance"] = True
                instance["instance_date"] = current.isoformat()
                instances.append(instance)
            
            current += delta
            count += 1
        
        return instances
    
    async def generate_ical_feed(
        self,
        tenant_id: UUID,
        months_ahead: int = 6
    ) -> str:
        """
        Generate iCal/ICS feed for a tenant.
        Returns a VCALENDAR string that can be subscribed to.
        """
        # Get tenant for calendar name
        tenant = await self.db.get(Tenant, tenant_id)
        if not tenant:
            return self._empty_vcalendar()
        
        # Date range
        now = datetime.now()
        start = now - timedelta(days=30)  # Include past month
        end = now + timedelta(days=30 * months_ahead)
        
        # Get all events
        events = await self.get_events(
            tenant_id, start, end,
            include_cancelled=False,
            expand_recurring=False  # Use RRULE instead of expanding
        )
        
        # Get recurring meetings for RRULE
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.status != MeetingStatus.CANCELLED.value,
                Meeting.parent_meeting_id.is_(None)
            )
        )
        result = await self.db.execute(stmt)
        meetings = result.scalars().all()
        
        # Build VCALENDAR
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Digital Secretary//Calendar//RU",
            f"X-WR-CALNAME:{tenant.business_name}",
            "X-WR-TIMEZONE:Asia/Almaty",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]
        
        # Add timezone
        lines.extend(self._vtimezone_almaty())
        
        # Add events
        for meeting in meetings:
            lines.extend(self._meeting_to_vevent(meeting))
        
        lines.append("END:VCALENDAR")
        
        return "\r\n".join(lines)
    
    def _meeting_to_vevent(self, meeting: Meeting) -> List[str]:
        """Convert meeting to VEVENT lines."""
        lines = ["BEGIN:VEVENT"]
        
        # UID
        lines.append(f"UID:{meeting.to_ical_uid()}")
        
        # Timestamps
        now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        lines.append(f"DTSTAMP:{now}")
        
        # Start/End
        if meeting.is_all_day:
            start_str = meeting.start_time.strftime("%Y%m%d")
            lines.append(f"DTSTART;VALUE=DATE:{start_str}")
            if meeting.end_time:
                end_str = meeting.end_time.strftime("%Y%m%d")
                lines.append(f"DTEND;VALUE=DATE:{end_str}")
        else:
            start_str = meeting.start_time.strftime("%Y%m%dT%H%M%S")
            lines.append(f"DTSTART;TZID={meeting.timezone}:{start_str}")
            if meeting.end_time:
                end_str = meeting.end_time.strftime("%Y%m%dT%H%M%S")
                lines.append(f"DTEND;TZID={meeting.timezone}:{end_str}")
        
        # Summary and description
        lines.append(f"SUMMARY:{self._escape_ical(meeting.title)}")
        if meeting.description:
            lines.append(f"DESCRIPTION:{self._escape_ical(meeting.description)}")
        if meeting.location:
            lines.append(f"LOCATION:{self._escape_ical(meeting.location)}")
        
        # Status
        status_map = {
            MeetingStatus.SCHEDULED.value: "TENTATIVE",
            MeetingStatus.CONFIRMED.value: "CONFIRMED",
            MeetingStatus.COMPLETED.value: "CONFIRMED",
            MeetingStatus.CANCELLED.value: "CANCELLED",
        }
        lines.append(f"STATUS:{status_map.get(meeting.status, 'TENTATIVE')}")
        
        # Priority
        priority_map = {"low": 9, "medium": 5, "high": 3, "urgent": 1}
        lines.append(f"PRIORITY:{priority_map.get(meeting.priority, 5)}")
        
        # Recurrence
        rrule = meeting.generate_rrule()
        if rrule:
            lines.append(f"RRULE:{rrule}")
        
        # Attendees
        if meeting.attendees:
            for att in meeting.attendees:
                if isinstance(att, dict) and att.get("email"):
                    lines.append(f"ATTENDEE;CN={att.get('name', '')}:mailto:{att['email']}")
        
        lines.append("END:VEVENT")
        return lines
    
    def _escape_ical(self, text: str) -> str:
        """Escape text for iCal format."""
        return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    
    def _vtimezone_almaty(self) -> List[str]:
        """Generate VTIMEZONE for Asia/Almaty."""
        return [
            "BEGIN:VTIMEZONE",
            "TZID:Asia/Almaty",
            "X-LIC-LOCATION:Asia/Almaty",
            "BEGIN:STANDARD",
            "TZOFFSETFROM:+0600",
            "TZOFFSETTO:+0500",
            "TZNAME:+05",
            "DTSTART:19700101T000000",
            "END:STANDARD",
            "END:VTIMEZONE",
        ]
    
    def _empty_vcalendar(self) -> str:
        """Return empty calendar."""
        return "\r\n".join([
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Digital Secretary//Calendar//RU",
            "END:VCALENDAR"
        ])
    
    @staticmethod
    def generate_feed_token() -> str:
        """Generate a secure random token for iCal feed URL."""
        return secrets.token_urlsafe(32)
