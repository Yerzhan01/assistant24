from __future__ import annotations
"""API routes for calendar and events management."""
import secrets
from datetime import datetime, timedelta
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db, get_language
from app.models.meeting import Meeting, RecurrenceType, MeetingStatus, MeetingPriority
from app.models.tenant import Tenant
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


# ==================== Schemas ====================

class EventCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description:Optional[ str ] = None
    location:Optional[ str ] = None
    start_time: datetime
    end_time:Optional[ datetime ] = None
    is_all_day: bool = False
    timezone: str = "Asia/Almaty"
    color: str = "#3B82F6"
    icon:Optional[ str ] = None
    priority: str = MeetingPriority.MEDIUM.value
    attendee_name:Optional[ str ] = None
    attendees:Optional[ List[dict] ] = None
    reminder_minutes: List[int] = [60, 15]
    
    # Recurrence
    recurrence_type: str = RecurrenceType.NONE.value
    recurrence_interval: int = 1
    recurrence_days:Optional[ List[int] ] = None
    recurrence_end_date:Optional[ datetime ] = None
    recurrence_count:Optional[ int ] = None


class EventUpdate(BaseModel):
    title:Optional[ str ] = None
    description:Optional[ str ] = None
    location:Optional[ str ] = None
    start_time:Optional[ datetime ] = None
    end_time:Optional[ datetime ] = None
    is_all_day:Optional[ bool ] = None
    color:Optional[ str ] = None
    icon:Optional[ str ] = None
    priority:Optional[ str ] = None
    status:Optional[ str ] = None
    attendee_name:Optional[ str ] = None
    attendees:Optional[ List[dict] ] = None
    reminder_minutes:Optional[ List[int] ] = None
    recurrence_type:Optional[ str ] = None
    recurrence_interval:Optional[ int ] = None
    recurrence_days:Optional[ List[int] ] = None
    recurrence_end_date:Optional[ datetime ] = None
    recurrence_count:Optional[ int ] = None


class EventResponse(BaseModel):
    id: str
    title: str
    description:Optional[ str ]
    location:Optional[ str ]
    start_time: str
    end_time:Optional[ str ]
    is_all_day: bool
    timezone: str
    color: str
    icon:Optional[ str ]
    priority: str
    status: str
    attendee_name:Optional[ str ]
    attendees:Optional[ List[dict] ]
    is_recurring: bool
    recurrence_type: str
    parent_id:Optional[ str ] = None
    is_instance: bool = False


class FeedUrlResponse(BaseModel):
    feed_url: str
    instructions: str


# ==================== Event Endpoints ====================

@router.get("/events", response_model=List[EventResponse])
async def list_events(
    start: str = Query(..., description="Start date for range (ISO format or YYYY-MM-DD)"),
    end: str = Query(..., description="End date for range (ISO format or YYYY-MM-DD)"),
    include_cancelled: bool = Query(False),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get events within a date range."""
    try:
        # Parse dates flexibly - accept both date-only and full datetime
        from dateutil import parser as date_parser
        start_date = date_parser.parse(start)
        end_date = date_parser.parse(end)
        
        # If end is date-only (no time), set to end of day
        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = end_date.replace(hour=23, minute=59, second=59)
        
        service = CalendarService(db)
        return await service.get_events(
            tenant_id=tenant.id,
            start_date=start_date,
            end_date=end_date,
            include_cancelled=include_cancelled
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(
    data: EventCreate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Create a new calendar event."""
    meeting = Meeting(
        tenant_id=tenant.id,
        **data.model_dump()
    )
    
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    
    service = CalendarService(db)
    return service._meeting_to_dict(meeting)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific event."""
    stmt = select(Meeting).where(
        and_(Meeting.id == event_id, Meeting.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Event not found")
    
    service = CalendarService(db)
    return service._meeting_to_dict(meeting)


@router.patch("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update an event."""
    stmt = select(Meeting).where(
        and_(Meeting.id == event_id, Meeting.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Event not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(meeting, key, value)
    
    await db.commit()
    await db.refresh(meeting)
    
    service = CalendarService(db)
    return service._meeting_to_dict(meeting)


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: UUID,
    delete_series: bool = Query(False, description="Delete all recurring instances"),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Delete an event."""
    stmt = select(Meeting).where(
        and_(Meeting.id == event_id, Meeting.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # If deleting series, delete parent (cascade will handle instances)
    if delete_series and meeting.parent_meeting_id:
        parent = await db.get(Meeting, meeting.parent_meeting_id)
        if parent:
            await db.delete(parent)
    else:
        await db.delete(meeting)
    
    await db.commit()


@router.post("/events/{event_id}/complete", response_model=EventResponse)
async def complete_event(
    event_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Mark an event as completed."""
    stmt = select(Meeting).where(
        and_(Meeting.id == event_id, Meeting.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Event not found")
    
    meeting.status = MeetingStatus.COMPLETED.value
    await db.commit()
    await db.refresh(meeting)
    
    service = CalendarService(db)
    return service._meeting_to_dict(meeting)


# ==================== Quick Actions ====================

@router.get("/today", response_model=List[EventResponse])
async def get_today_events(
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get today's events."""
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    
    service = CalendarService(db)
    return await service.get_events(tenant.id, start, end)


@router.get("/week", response_model=List[EventResponse])
async def get_week_events(
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get this week's events."""
    now = datetime.now()
    start = now - timedelta(days=now.weekday())  # Monday
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    
    service = CalendarService(db)
    return await service.get_events(tenant.id, start, end)


@router.get("/upcoming", response_model=List[EventResponse])
async def get_upcoming_events(
    limit: int = Query(10, le=50),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming events."""
    now = datetime.now()
    end = now + timedelta(days=30)
    
    service = CalendarService(db)
    events = await service.get_events(tenant.id, now, end)
    return events[:limit]


# ==================== iCal Feed ====================

@router.get("/feed-url", response_model=FeedUrlResponse)
async def get_feed_url(
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get the iCal feed URL for subscribing in Google Calendar."""
    # Check if tenant has a feed token, if not create one
    if not hasattr(tenant, 'calendar_feed_token') or not tenant.calendar_feed_token:
        # Store token in tenant (we'll add this field)
        token = CalendarService.generate_feed_token()
        # For now just generate a fresh token each time
    else:
        token = tenant.calendar_feed_token
    
    # Generate token for URL
    token = CalendarService.generate_feed_token()
    
    # Build URL (would be configured in production)
    base_url = "https://api.yourservice.kz"  # Configure this
    feed_url = f"{base_url}/api/v1/calendar/feed/{tenant.id}.ics?token={token}"
    
    instructions = """
Как добавить в Google Календарь:
1. Откройте Google Календарь → Настройки
2. Выберите "Добавить календарь" → "По URL"
3. Вставьте эту ссылку
4. События синхронизируются автоматически

Примечание: обновление может занять несколько часов.
"""
    
    return FeedUrlResponse(feed_url=feed_url, instructions=instructions)


@router.get("/feed/{tenant_id}.ics")
async def get_ical_feed(
    tenant_id: UUID,
    token: str = Query(..., description="Feed access token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Public iCal feed endpoint.
    This is the URL users add to Google Calendar.
    """
    # Verify tenant exists (in production, verify token)
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Calendar not found")
    
    # Verify token matches stored token for security
    if not tenant.calendar_feed_token or tenant.calendar_feed_token != token:
        # Use constant time comparison if possible, but python str comparison is fast enough for this context
        # Log incident?
        # logger.warning(f"Invalid calendar feed access attempt for tenant {tenant_id}")
        raise HTTPException(status_code=403, detail="Invalid access token")
    
    # Generate iCal content
    service = CalendarService(db)
    ical_content = await service.generate_ical_feed(tenant_id)
    
    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename={tenant.business_name}_calendar.ics"
        }
    )


# ==================== Available Slots ====================

@router.get("/available-slots")
async def get_available_slots(
    date: datetime = Query(..., description="Date to check"),
    duration_minutes: int = Query(60, description="Meeting duration"),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get available time slots for a given day."""
    # Get events for the day
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    
    service = CalendarService(db)
    events = await service.get_events(tenant.id, start, end)
    
    # Business hours: 9:00 - 18:00
    business_start = 9
    business_end = 18
    slot_duration = duration_minutes
    
    # Find busy periods
    busy = []
    for event in events:
        event_start = datetime.fromisoformat(event["start_time"])
        event_end = datetime.fromisoformat(event["end_time"]) if event["end_time"] else event_start + timedelta(hours=1)
        busy.append((event_start, event_end))
    
    # Generate available slots
    available = []
    current = start.replace(hour=business_start, minute=0)
    end_of_day = start.replace(hour=business_end, minute=0)
    
    while current + timedelta(minutes=slot_duration) <= end_of_day:
        slot_end = current + timedelta(minutes=slot_duration)
        
        # Check if slot conflicts with any busy period
        is_free = True
        for busy_start, busy_end in busy:
            if not (slot_end <= busy_start or current >= busy_end):
                is_free = False
                break
        
        if is_free:
            available.append({
                "start": current.isoformat(),
                "end": slot_end.isoformat()
            })
        
        current += timedelta(minutes=30)  # 30-min increments
    
    return {"date": date.date().isoformat(), "available_slots": available}
