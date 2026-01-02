from __future__ import annotations
"""Enhanced Meeting model for premium calendar system."""
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.contact import Contact


class RecurrenceType(str, Enum):
    """Meeting recurrence types."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class MeetingPriority(str, Enum):
    """Meeting priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MeetingStatus(str, Enum):
    """Meeting status."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Default event colors
EVENT_COLORS = {
    "blue": "#3B82F6",
    "green": "#10B981",
    "red": "#EF4444",
    "yellow": "#F59E0B",
    "purple": "#8B5CF6",
    "pink": "#EC4899",
    "indigo": "#6366F1",
    "teal": "#14B8A6",
}


class Meeting(Base):
    """
    Enhanced meeting model for premium calendar.
    Supports recurrence, colors, timezones, and iCal export.
    """
    __tablename__ = "meetings"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Tenant relationship
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # User who created
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Contact (attendee) - for invitations
    contact_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Meeting details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description:Mapped[Optional[str]] = mapped_column(Text)
    location:Mapped[Optional[str]] = mapped_column(String(255))
    
    # Time (stored in UTC, converted for display)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        index=True
    )
    end_time:Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # All-day event
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timezone (for display and recurrence calculation)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Almaty")
    
    # Visual customization
    color: Mapped[str] = mapped_column(String(20), default="#3B82F6")  # Hex color
    icon:Mapped[Optional[str]] = mapped_column(String(50))  # "call", "person", "coffee"
    
    # Priority
    priority: Mapped[str] = mapped_column(
        String(20), 
        default=MeetingPriority.MEDIUM.value
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=MeetingStatus.SCHEDULED.value,
        index=True
    )
    
    # ==================== Recurrence ====================
    
    # Recurrence type
    recurrence_type: Mapped[str] = mapped_column(
        String(20),
        default=RecurrenceType.NONE.value
    )
    
    # Interval: every N days/weeks/months
    recurrence_interval: Mapped[int] = mapped_column(Integer, default=1)
    
    # For weekly: days of week [0=Mon, 1=Tue, ..., 6=Sun]
    recurrence_days:Optional[ Mapped[List[int] ]] = mapped_column(JSON)
    
    # End date for recurrence (null = forever)
    recurrence_end_date:Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Max occurrences (alternative to end date)
    recurrence_count:Mapped[Optional[int]] = mapped_column(Integer)
    
    # Parent meeting for recurring instances
    parent_meeting_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # Original date (for moved recurring instances)
    original_date:Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # ==================== Attendees ====================
    
    # Attendees as JSON array with status
    # [{"name": "Асхат", "phone": "+77...", "email": "", "status": "pending"}]
    attendees:Optional[ Mapped[List[dict] ]] = mapped_column(JSON, default=list)
    
    # Simple attendee name (for AI extraction)
    attendee_name:Mapped[Optional[str]] = mapped_column(String(255))
    
    # ==================== Reminders ====================
    
    # Reminders (minutes before meeting)
    reminder_minutes: Mapped[List[int]] = mapped_column(
        JSON,
        default=lambda: [60, 15],
        nullable=False
    )
    
    # Notification sent flags
    reminders_sent: Mapped[Dict[str, bool]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    
    # ==================== Timestamps ====================
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # ==================== Relationships ====================
    
    tenant: Mapped["Tenant"] = relationship(back_populates="meetings")
    user: Mapped[Optional["User"]] = relationship()
    contact: Mapped[Optional["Contact"]] = relationship()
    
    # Self-referential for recurring series
    parent: Mapped[Optional["Meeting"]] = relationship(
        remote_side=[id],
        back_populates="instances"
    )
    instances: Mapped[List["Meeting"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Meeting {self.title} at {self.start_time}>"
    
    @property
    def duration_minutes(self) -> int:
        """Get meeting duration in minutes."""
        if not self.end_time:
            return 60  # Default 1 hour
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)
    
    @property
    def is_recurring(self) -> bool:
        """Check if this is a recurring meeting."""
        return self.recurrence_type != RecurrenceType.NONE.value
    
    @property
    def is_instance(self) -> bool:
        """Check if this is an instance of a recurring series."""
        return self.parent_meeting_id is not None
    
    def to_ical_uid(self) -> str:
        """Generate unique ID for iCal."""
        return f"{self.id}@digital-secretary.kz"
    
    def generate_rrule(self) ->Optional[ str ]:
        """Generate RRULE string for iCal."""
        if not self.is_recurring:
            return None
        
        freq_map = {
            RecurrenceType.DAILY.value: "DAILY",
            RecurrenceType.WEEKLY.value: "WEEKLY",
            RecurrenceType.BIWEEKLY.value: "WEEKLY",
            RecurrenceType.MONTHLY.value: "MONTHLY",
            RecurrenceType.YEARLY.value: "YEARLY",
        }
        
        freq = freq_map.get(self.recurrence_type, "WEEKLY")
        interval = self.recurrence_interval
        
        if self.recurrence_type == RecurrenceType.BIWEEKLY.value:
            interval = 2
        
        parts = [f"FREQ={freq}", f"INTERVAL={interval}"]
        
        # Weekly with specific days
        if self.recurrence_type == RecurrenceType.WEEKLY.value and self.recurrence_days:
            day_map = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
            days = ",".join([day_map[d] for d in self.recurrence_days if 0 <= d <= 6])
            if days:
                parts.append(f"BYDAY={days}")
        
        # End conditions
        if self.recurrence_end_date:
            end_str = self.recurrence_end_date.strftime("%Y%m%dT%H%M%SZ")
            parts.append(f"UNTIL={end_str}")
        elif self.recurrence_count:
            parts.append(f"COUNT={self.recurrence_count}")
        
        return ";".join(parts)
