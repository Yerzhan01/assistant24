"""
Autonomous Event Loop - Proactive agent for scheduled tasks.
Handles:
- Morning briefings
- Birthday reminders
- Task deadlines
- Overdue debt reminders
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional
import asyncio

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.tenant import Tenant
from app.models.birthday import Birthday
from app.models.task import Task
from app.models.invoice import Invoice
from app.models.meeting import Meeting

logger = logging.getLogger(__name__)


class AutonomousLoop:
    """Autonomous Event Loop for proactive agent behavior."""
    
    def __init__(self):
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the autonomous loop."""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("🤖 Autonomous Loop started")
    
    async def stop(self):
        """Stop the autonomous loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🤖 Autonomous Loop stopped")
    
    async def _run_loop(self):
        """Main loop - runs every 5 minutes."""
        while self.running:
            try:
                await self._check_all_tenants()
            except Exception as e:
                logger.error(f"Autonomous loop error: {e}")
            
            # Sleep for 5 minutes
            await asyncio.sleep(300)
    
    async def _check_all_tenants(self):
        """Check all tenants for pending notifications."""
        async with async_session_maker() as db:
            # Get all active tenants
            result = await db.execute(select(Tenant).where(Tenant.is_active == True))
            tenants = result.scalars().all()
            
            for tenant in tenants:
                await self._check_tenant(db, tenant)
    
    async def _check_tenant(self, db: AsyncSession, tenant: Tenant):
        """Check a single tenant for notifications."""
        notifications = []
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        
        from app.models.meeting import Meeting
        from app.models.system_event import SystemEvent
        from sqlalchemy import func
        
        # 1. 🌅 Morning Briefing (09:00 - 10:00)
        if now.hour == 9:
             if not await self._event_exists(db, tenant.id, "morning_briefing", today_str):
                briefing = await self._generate_morning_briefing(db, tenant.id)
                if briefing:
                    await self._send_notification(tenant, briefing)
                    await self._log_event(db, tenant.id, "morning_briefing", "Sent morning briefing")
        
        # 2. 🧠 Smart Reminders (Every loop)
        
        # A. Meetings starting in ~15 mins
        # Pass current loop window to avoid duplicates if loop is fast
        upcoming_meetings = await self._get_upcoming_meetings(db, tenant.id, minutes=15, window=5)
        for m in upcoming_meetings:
            start_time = datetime.fromisoformat(m.start_time)
            msg = f"⏰ Встреча через 15 мин: **{m.title}** ({start_time.strftime('%H:%M')})"
            # Check if recently sent to avoid spam
            if not await self._event_exists(db, tenant.id, "meeting_remind", f"{m.id}_15m"):
                 notifications.append(msg)
                 await self._log_event(db, tenant.id, "meeting_remind", f"{m.id}_15m")

        # B. 🤝 Meeting Follow-up (Recently ended)
        # Check meetings ended 5-10 mins ago
        ended_meetings = await self._get_recently_ended_meetings(db, tenant.id, minutes=10, window=5)
        for m in ended_meetings:
             if not await self._event_exists(db, tenant.id, "meeting_followup", str(m.id)):
                 notifications.append(f"🤝 Встреча **{m.title}** закончилась. Как всё прошло? Записать итоги или создать задачи?")
                 await self._log_event(db, tenant.id, "meeting_followup", str(m.id))
        
        # C. Tasks deadline in ~1 hour
        upcoming_tasks = await self._get_upcoming_tasks(db, tenant.id, minutes=60)
        for t in upcoming_tasks:
            # Simple check to avoid spam - only notify if not notified in last 2 hours? 
            # Ideally task model has 'reminder_sent' bool. Let's use event log with simple key.
            if not await self._event_exists(db, tenant.id, "task_deadline_1h", str(t.id)):
                notifications.append(f"⏳ Дедлайн через час: **{t.title}**")
                await self._log_event(db, tenant.id, "task_deadline_1h", str(t.id))
        
        # 3. ❤️ Well-being Check (15:00 - 16:00)
        if now.hour == 15 and 0 <= now.minute < 10:
             if not await self._event_exists(db, tenant.id, "wellbeing_check", today_str):
                # Count tasks/meetings
                active_count = len(await self._get_todays_tasks(db, tenant.id))
                meeting_count = len(await self._get_todays_meetings(db, tenant.id))
                
                if active_count + meeting_count > 4:
                    notifications.append(f"☕️ У тебя сегодня насыщенный день ({active_count} задач, {meeting_count} встреч).\nМожет, сделаешь перерыв на кофе? Я пока послежу за входящими.")
                    await self._log_event(db, tenant.id, "wellbeing_check", today_str)

        # 4. Birthdays (One-time check at 10:00)
        if now.hour == 10 and 0 <= now.minute < 10:
             if not await self._event_exists(db, tenant.id, "birthday_check", today_str):
                birthdays = await self._get_upcoming_birthdays(db, tenant.id)
                for bday in birthdays:
                    if bday.date.day == now.day:
                        notifications.append(f"🎂 Сегодня день рождения: **{bday.name}**! Не забудь поздравить.")
                await self._log_event(db, tenant.id, "birthday_check", today_str)
        
        if notifications:
            await self._send_notification(tenant, "\n\n".join(notifications))

        # 5. 🧠 Smart Meeting Prep (30 mins before)
        # Use KnowledgeAgent to research meeting context
        prep_meetings = await self._get_upcoming_meetings(db, tenant.id, minutes=30, window=5)
        for m in prep_meetings:
             if not await self._event_exists(db, tenant.id, "meeting_prep", str(m.id)):
                 # Research logic
                 try:
                     from app.agents.knowledge import KnowledgeAgent
                     
                     # Construct query
                     query = f"Кто такой/что такое {m.title}?"
                     if m.attendee_name:
                         query += f" и кто такой {m.attendee_name}?"
                     
                     # Quick research
                     # We need to instantiate agent. It needs DB session but KnowledgeAgent primarily uses API.
                     # However, BaseAgent init requires db.
                     k_agent = KnowledgeAgent(db=db, tenant_id=tenant.id, user_id=m.user_id)
                     
                     # Run research (silently, just get text)
                     research_resp = await k_agent.run(query)
                     text = research_resp.content
                     
                     # Format message
                     prep_msg = (
                         f"🧠 **Подготовка к встрече через 30 мин:**\n"
                         f"📌 **{m.title}**\n\n"
                         f"{text}\n"
                     )
                     
                     await self._send_notification(tenant, prep_msg)
                     await self._log_event(db, tenant.id, "meeting_prep", str(m.id))
                     
                 except Exception as ex:
                     logger.error(f"Meeting prep failed: {ex}")

    async def _event_exists(self, db: AsyncSession, tenant_id, type_str, details_key) -> bool:
        """Check if system event exists (deduplication)."""
        from app.models.system_event import SystemEvent
        from sqlalchemy import select, and_, func
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # Check against details containing the key AND created today (for daily stuff)
        # or just specific key (for meeting/tasks unique IDs)
        
        stmt = select(SystemEvent).where(
            and_(
                SystemEvent.tenant_id == tenant_id,
                SystemEvent.event_type == type_str,
                SystemEvent.details.contains(details_key)
            )
        )
        existing = await db.execute(stmt)
        return existing.scalar_one_or_none() is not None

    async def _log_event(self, db: AsyncSession, tenant_id, type_str, details):
        """Log system event."""
        from app.models.system_event import SystemEvent
        db.add(SystemEvent(tenant_id=tenant_id, event_type=type_str, details=details))
        await db.commit()

    async def _get_upcoming_meetings(self, db: AsyncSession, tenant_id, minutes: int = 15, window: int = 2) -> list:
        """Get meetings starting in X minutes."""
        now = datetime.now()
        target_time = now + timedelta(minutes=minutes)
        # Check window: target_time +/- window minutes
        window_start = target_time - timedelta(minutes=window)
        window_end = target_time + timedelta(minutes=window)
        
        from app.models.meeting import Meeting
        
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.start_time >= window_start.isoformat(),
                Meeting.start_time <= window_end.isoformat()
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def _get_recently_ended_meetings(self, db: AsyncSession, tenant_id, minutes: int = 10, window: int = 5) -> list:
        """Get meetings that ended X minutes ago."""
        now = datetime.now()
        target_end_time = now - timedelta(minutes=minutes)
        
        # Check window around that time
        window_start = target_end_time - timedelta(minutes=window)
        window_end = target_end_time + timedelta(minutes=window)
        
        from app.models.meeting import Meeting
        
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.end_time >= window_start.isoformat(),
                Meeting.end_time <= window_end.isoformat()
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def _get_upcoming_tasks(self, db: AsyncSession, tenant_id, minutes: int = 60) -> list:
        """Get tasks with deadline in X minutes."""
        now = datetime.now()
        target_time = now + timedelta(minutes=minutes)
        
        # Check window: target_time +/- 5 minutes
        window_start = target_time - timedelta(minutes=5)
        window_end = target_time + timedelta(minutes=5)
        
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.status != "done",
                Task.deadline >= window_start,
                Task.deadline <= window_end
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def _generate_morning_briefing(self, db: AsyncSession, tenant_id) -> str:
        """Generate AI daily briefing."""
        lines = ["🌅 **Доброе утро! Твой план на сегодня:**"]
        
        # Meetings
        meetings = await self._get_todays_meetings(db, tenant_id)
        if meetings:
            lines.append("\n📅 **Встречи:**")
            for m in meetings:
                start = datetime.fromisoformat(m.start_time).strftime('%H:%M')
                lines.append(f"• {start} — {m.title}")
        else:
            lines.append("\n📅 Встреч нет.")
            
        # Tasks
        tasks = await self._get_todays_tasks(db, tenant_id)
        if tasks:
            lines.append("\n✅ **Задачи:**")
            for t in tasks:
                lines.append(f"• {t.title}")
        
        return "\n".join(lines)

    async def _get_todays_meetings(self, db: AsyncSession, tenant_id) -> list:
        """Get meetings for today."""
        now = datetime.now()
        start_str = now.replace(hour=0, minute=0, second=0).isoformat()
        end_str = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
        
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.start_time >= start_str,
                Meeting.start_time < end_str
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def _get_todays_tasks(self, db: AsyncSession, tenant_id) -> list:
        """Get tasks for today."""
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.status != "done",
                Task.deadline >= start,
                Task.deadline < end
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def _send_notification(self, tenant: Tenant, text: str):
        """Send notification to tenant via Telegram."""
        if not tenant.telegram_chat_id:
            return
        
        try:
            from aiogram import Bot
            from app.core.config import settings
            
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            
            await bot.send_message(
                chat_id=tenant.telegram_chat_id,
                text=text,
                parse_mode="Markdown"
            )
            
            logger.info(f"📤 Sent notification to {tenant.name}")
            await bot.session.close()
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    
    async def _get_upcoming_birthdays(self, db: AsyncSession, tenant_id) -> list:
        """Get birthdays for today and tomorrow."""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        stmt = select(Birthday).where(
            Birthday.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        all_birthdays = result.scalars().all()
        
        # Filter by month and day (ignore year)
        return [
            b for b in all_birthdays 
            if (b.date.month == today.month and b.date.day == today.day) or
               (b.date.month == tomorrow.month and b.date.day == tomorrow.day)
        ]
    
    async def _get_overdue_tasks(self, db: AsyncSession, tenant_id) -> list:
        """Get tasks past deadline."""
        now = datetime.now()
        
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.status != "done",
                Task.deadline != None,
                Task.deadline < now
            )
        ).limit(5)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def _get_overdue_debts(self, db: AsyncSession, tenant_id) -> list:
        """Get unpaid invoices past due date."""
        now = datetime.now()
        
        stmt = select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.status != "paid",
                Invoice.due_date < now
            )
        ).limit(5)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def _send_notifications(self, tenant: Tenant, notifications: list):
        """Send notifications to tenant via Telegram."""
        if not tenant.telegram_chat_id:
            return
        
        try:
            from aiogram import Bot
            from app.core.config import settings
            
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            
            message = "🤖 **Напоминания:**\n\n" + "\n".join(notifications)
            
            await bot.send_message(
                chat_id=tenant.telegram_chat_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.info(f"📤 Sent {len(notifications)} notifications to {tenant.name}")
            
        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")


# Global instance
autonomous_loop = AutonomousLoop()


async def start_autonomous_loop():
    """Helper to start the loop."""
    await autonomous_loop.start()


async def stop_autonomous_loop():
    """Helper to stop the loop."""
    await autonomous_loop.stop()
