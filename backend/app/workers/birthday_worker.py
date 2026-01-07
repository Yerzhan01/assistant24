from __future__ import annotations
"""Birthday reminder worker - sends notifications for upcoming birthdays."""
import asyncio
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select, and_, update, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.i18n import t
from app.models.birthday import Birthday
from app.models.tenant import Tenant
from app.workers.celery_app import celery_app
from app.workers.reminder_worker import _send_notification


@celery_app.task(name="check_birthday_reminders")
def check_birthday_reminders():
    """Check for birthdays that need reminders sent."""
    asyncio.get_event_loop().run_until_complete(_check_birthday_reminders())


async def _check_birthday_reminders():
    """Async implementation of birthday reminder check."""
    async with async_session_maker() as db:
        today = date.today()
        current_year = today.year
        
        # Check birthdays in the next 7 days
        for days_ahead in [7, 3, 1]:
            target_date = today + timedelta(days=days_ahead)
            
            # Find birthdays on this date (matching month and day)
            stmt = select(Birthday).where(
                and_(
                    extract('month', Birthday.birth_date) == target_date.month,
                    extract('day', Birthday.birth_date) == target_date.day
                )
            )
            
            result = await db.execute(stmt)
            birthdays = result.scalars().all()
            
            for birthday in birthdays:
                await _process_birthday_reminder(db, birthday, days_ahead, current_year)
        
        await db.commit()


from datetime import timedelta


async def _process_birthday_reminder(
    db: AsyncSession,
    birthday: Birthday,
    days_ahead: int,
    current_year: int
):
    """Process reminder for a single birthday."""
    # Skip if this reminder was already sent this year
    if birthday.reminders_sent_year == current_year:
        reminder_key = str(days_ahead)
        if birthday.reminders_sent.get(reminder_key):
            return
    else:
        # Reset reminders for new year
        birthday.reminders_sent = {}
        birthday.reminders_sent_year = current_year
    
    # Check if this days_ahead is in the remind_days list
    if days_ahead not in birthday.remind_days:
        return
    
    # Get tenant
    tenant = await db.get(Tenant, birthday.tenant_id)
    if not tenant:
        return
    
    lang = tenant.language
    
    # Format days text
    days_text_map = {
        "ru": {1: "Завтра", 3: "Через 3 дня", 7: "Через неделю"},
        "kz": {1: "Ертең", 3: "3 күннен кейін", 7: "Бір аптадан кейін"}
    }
    days_text = days_text_map.get(lang, days_text_map["ru"]).get(days_ahead, f"Через {days_ahead} дней")
    
    message = t(
        "modules.birthday.reminder",
        lang,
        days_text=days_text,
        name=birthday.person_name
    )
    
    await _send_notification(tenant, message)
    
    # Mark as sent
    birthday.reminders_sent[str(days_ahead)] = True
    
    stmt = update(Birthday).where(Birthday.id == birthday.id).values(
        reminders_sent=birthday.reminders_sent,
        reminders_sent_year=current_year
    )
    await db.execute(stmt)


@celery_app.task(name="send_birthday_greeting")
def send_birthday_greeting(birthday_id: str, tenant_id: str):
    """Send birthday greeting on the actual day."""
    asyncio.get_event_loop().run_until_complete(
        _send_birthday_greeting(UUID(birthday_id), UUID(tenant_id))
    )


async def _send_birthday_greeting(birthday_id: UUID, tenant_id: UUID):
    """Async implementation of birthday greeting."""
    async with async_session_maker() as db:
        birthday = await db.get(Birthday, birthday_id)
        tenant = await db.get(Tenant, tenant_id)
        
        if not birthday or not tenant:
            return
        
        lang = tenant.language
        
        if lang == "kz":
            message = f"🎂 Бүгін {birthday.person_name} туған күні! Құттықтауды ұмытпаңыз!"
        else:
            message = f"🎂 Сегодня день рождения: {birthday.person_name}! Не забудьте поздравить!"
        
        await _send_notification(tenant, message)
