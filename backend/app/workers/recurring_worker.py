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
        now = datetime.now()
        
        # Find recurring tasks where next_occurrence is due
        stmt = select(Task).where(
            and_(
                Task.is_recurring == True,
                Task.next_occurrence <= now,
                Task.status != TaskStatus.CANCELLED.value
            )
        )
        
        result = await db.execute(stmt)
        recurring_tasks = result.scalars().all()
        
        for template in recurring_tasks:
            try:
                # Calculate next deadline based on pattern
                if template.recurrence_pattern == "daily":
                    new_deadline = now + timedelta(days=1)
                elif template.recurrence_pattern == "weekly":
                    new_deadline = now + timedelta(weeks=1)
                elif template.recurrence_pattern == "monthly":
                    new_deadline = now + relativedelta(months=1)
                else:
                    new_deadline = now + timedelta(weeks=1)
                
                # Set deadline to end of day
                new_deadline = new_deadline.replace(hour=23, minute=59, second=0, microsecond=0)
                
                # Create new task instance
                new_task = Task(
                    tenant_id=template.tenant_id,
                    creator_id=template.creator_id,
                    assignee_id=template.assignee_id,
                    title=template.title,
                    description=template.description,
                    priority=template.priority,
                    status=TaskStatus.NEW.value,
                    deadline=new_deadline,
                    # Link to template but don't make it recurring itself
                    parent_id=template.id,
                    is_recurring=False
                )
                db.add(new_task)
                
                # Update template's next occurrence
                template.last_spawned_at = now
                template.next_occurrence = new_deadline
                
                logger.info(f"Spawned recurring task: {template.title} -> next: {new_deadline}")
                
            except Exception as e:
                logger.error(f"Failed to spawn recurring task {template.id}: {e}")
        
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
