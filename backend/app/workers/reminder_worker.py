from __future__ import annotations
"""Meeting reminder worker - sends notifications for upcoming meetings."""
import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.i18n import t
from app.models.meeting import Meeting
from app.models.tenant import Tenant
from app.services.telegram_bot import get_telegram_service
from app.services.whatsapp_bot import get_whatsapp_service
from app.workers.celery_app import celery_app


from app.workers.celery_app import celery_app


@celery_app.task(name="check_meeting_reminders")
def check_meeting_reminders():
    """Check for meetings that need reminders sent."""
    asyncio.get_event_loop().run_until_complete(_check_meeting_reminders())


async def _check_meeting_reminders():
    """Async implementation of meeting reminder check."""
    async with async_session_maker() as db:
        now = datetime.now()
        
        # Check for meetings in the next 2 hours
        time_window = now + timedelta(hours=2)
        
        # Get all upcoming meetings
        stmt = select(Meeting).where(
            and_(
                Meeting.start_time >= now,
                Meeting.start_time <= time_window,
                Meeting.is_cancelled == False,
                Meeting.is_completed == False
            )
        )
        
        result = await db.execute(stmt)
        meetings = result.scalars().all()
        
        for meeting in meetings:
            await _process_meeting_reminder(db, meeting, now)
        
        await db.commit()


async def _process_meeting_reminder(
    db: AsyncSession, 
    meeting: Meeting, 
    now: datetime
):
    """Process reminder for a single meeting."""
    # Get tenant for language and bot settings
    tenant = await db.get(Tenant, meeting.tenant_id)
    if not tenant:
        return
    
    lang = tenant.language
    minutes_until = int((meeting.start_time - now).total_seconds() / 60)
    
    # Check which reminders need to be sent
    for reminder_minutes in meeting.reminder_minutes:
        reminder_key = str(reminder_minutes)
        
        # Skip if already sent
        if meeting.reminders_sent.get(reminder_key):
            continue
        
        # Check if it's time for this reminder
        # Allow 5 minute window for the check
        if abs(minutes_until - reminder_minutes) <= 5:
            # Send notification
            message = t(
                "modules.meeting.reminder",
                lang,
                minutes=reminder_minutes,
                title=meeting.title
            )
            
            await _send_notification(tenant, message)
            
            # Mark as sent
            meeting.reminders_sent[reminder_key] = True
            
            # Update in DB
            stmt = update(Meeting).where(Meeting.id == meeting.id).values(
                reminders_sent=meeting.reminders_sent
            )
            await db.execute(stmt)


async def _send_notification(tenant: Tenant, message: str):
    """Send notification via available channels."""
    # Try Telegram first
    if tenant.telegram_bot_token and tenant.telegram_chat_id:
        try:
            from aiogram import Bot
            bot = Bot(token=tenant.telegram_bot_token)
            await bot.send_message(chat_id=tenant.telegram_chat_id, text=message)
            await bot.session.close()
        except Exception as e:
            print(f"Failed to send Telegram notification: {e}")
    
    # Try WhatsApp
    if tenant.greenapi_instance_id and tenant.whatsapp_phone:
        try:
            service = get_whatsapp_service()
            await service.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                tenant.whatsapp_phone,
                message
            )
        except Exception as e:
            print(f"Failed to send WhatsApp notification: {e}")


@celery_app.task(name="send_meeting_reminder")
def send_meeting_reminder(meeting_id: str, tenant_id: str, reminder_minutes: int):
    """Send a specific meeting reminder."""
    asyncio.get_event_loop().run_until_complete(
        _send_meeting_reminder(UUID(meeting_id), UUID(tenant_id), reminder_minutes)
    )


async def _send_meeting_reminder(
    meeting_id: UUID, 
    tenant_id: UUID, 
    reminder_minutes: int
):
    """Async implementation of sending a meeting reminder."""
    async with async_session_maker() as db:
        meeting = await db.get(Meeting, meeting_id)
        tenant = await db.get(Tenant, tenant_id)
        
        if not meeting or not tenant:
            return
        
        lang = tenant.language
        message = t(
            "modules.meeting.reminder",
            lang,
            minutes=reminder_minutes,
            title=meeting.title
        )
        
        await _send_notification(tenant, message)
        
        # Mark reminder as sent
        meeting.reminders_sent[str(reminder_minutes)] = True
        await db.commit()
