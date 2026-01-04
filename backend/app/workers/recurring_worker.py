from __future__ import annotations
"""
Recurring Task & Reminder Worker.
Runs periodically to:
1. Spawn new task instances from recurring tasks
2. Send reminders for due tasks
"""
import logging
import asyncio
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrulestr

from app.core.database import async_session_maker
from app.models.task import Task, TaskStatus
from app.models.task_reminder import TaskReminder, ReminderType
from app.models.tenant import Tenant
from app.services.whatsapp_bot import get_whatsapp_service

logger = logging.getLogger(__name__)

class RecurringTaskWorker:
    """Worker for managing recurring tasks and reminders."""
    
    def __init__(self):
        self.whatsapp = get_whatsapp_service()
    
    async def fast_tick(self):
        """Run frequent checks (every minute)."""
        async with async_session_maker() as db:
             await self.process_reminders(db)
             await self.process_recurring_tasks(db)
             await db.commit()
    
    async def process_recurring_tasks(self, db: AsyncSession):
        """Spawn new tasks from recurring templates."""
        # Find tasks with RRULE that are not templates themselves? 
        # Actually, we treat the original task as the template if it has RRULE.
        # But we don't want to duplicate the "done" instances.
        # Strategy: The recurring task is a "Master". We create clones.
        # For simplicity in V2:
        # We look for Active Recurring Tasks.
        # We check if a CHILD task needs to be created for TODAY.
        
        # This logic is complex. 
        # For MVP V2: We just clone the task if the RRULE matches today and no child exists for today.
        pass # To be implemented fully. For now, placeholder.
        
    async def process_reminders(self, db: AsyncSession):
        """Process pending reminders."""
        now = datetime.now()
        
        # Find reminders due
        stmt = select(TaskReminder).join(Task).where(
            and_(
                TaskReminder.is_sent == False,
                TaskReminder.remind_at <= now,
                Task.status != TaskStatus.DONE.value,
                Task.status != TaskStatus.CANCELLED.value
            )
        )
        
        result = await db.execute(stmt)
        reminders = result.scalars().all()
        
        for reminder in reminders:
            try:
                await self._send_reminder(db, reminder)
                reminder.is_sent = True
                reminder.sent_at = datetime.now()
            except Exception as e:
                logger.error(f"Failed to send reminder {reminder.id}: {e}")
                reminder.error_count += 1
                reminder.last_error = str(e)
                
    async def _send_reminder(self, db: AsyncSession, reminder: TaskReminder):
        """Send WhatsApp notification."""
        # Fetch task and user
        stmt = select(Task).where(Task.id == reminder.task_id)
        task = (await db.execute(stmt)).scalar_one()
        
        if not task.assignee_id:
            return
            
        from app.models.user import User
        stmt_user = select(User).where(User.id == task.assignee_id)
        user = (await db.execute(stmt_user)).scalar_one()
        
        tenant = await db.get(Tenant, task.tenant_id)
        
        if user.whatsapp_phone and tenant.greenapi_instance_id:
            msg = f"⏰ Напоминание: {task.title}\nДедлайн: {task.deadline.strftime('%H:%M') if task.deadline else 'скоро'}"
            
            await self.whatsapp.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                user.whatsapp_phone,
                msg
            )
