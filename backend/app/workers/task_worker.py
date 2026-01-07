from __future__ import annotations
"""Task reminder worker - Celery tasks for task deadline reminders."""
import asyncio
import logging
from datetime import datetime

from celery import shared_task

from app.core.database import async_session_maker
from app.services.group_task_manager import GroupTaskManager
from app.services.whatsapp_bot import WhatsAppBotService
from app.models.tenant import Tenant
from app.models.task import Task

logger = logging.getLogger(__name__)


@shared_task(name="check_task_deadlines")
def check_task_deadlines() -> dict:
    """
    Check for tasks with upcoming or overdue deadlines.
    Sends reminders to assigned users via WhatsApp.
    """
    return asyncio.run(_check_task_deadlines())


async def _check_task_deadlines() -> dict:
    """Async implementation of deadline checker."""
    stats = {
        "overdue_reminders": 0,
        "upcoming_reminders": 0,
        "errors": 0
    }
    
    async with async_session_maker() as db:
        try:
            # Get all active tenants with WhatsApp configured
            from sqlalchemy import select
            stmt = select(Tenant).where(Tenant.is_active == True)
            result = await db.execute(stmt)
            tenants = result.scalars().all()
            
            whatsapp = WhatsAppBotService()
            
            for tenant in tenants:
                if not tenant.whatsapp_instance_id or not tenant.whatsapp_api_token:
                    continue
                
                manager = GroupTaskManager(db, language=tenant.language or "ru")
                
                # Check overdue tasks
                overdue = await manager.get_overdue_tasks(tenant.id)
                for task in overdue:
                    await _send_overdue_reminder(
                        whatsapp, tenant, task, db
                    )
                    stats["overdue_reminders"] += 1
                
                # Check tasks due in 24 hours
                upcoming = await manager.get_tasks_due_soon(tenant.id, hours=24)
                for task in upcoming:
                    await _send_upcoming_reminder(
                        whatsapp, tenant, task
                    )
                    stats["upcoming_reminders"] += 1
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Task deadline check failed: {e}")
            stats["errors"] += 1
            await db.rollback()
    
    return stats


async def _send_overdue_reminder(
    whatsapp: WhatsAppBotService,
    tenant: Tenant,
    task: Task,
    db
):
    """Send overdue task reminder."""
    if not task.assignee or not task.assignee.whatsapp_phone:
        return
    
    if not task.group or not task.group.whatsapp_chat_id:
        return
    
    # Format message
    days_overdue = (datetime.now() - task.deadline).days if task.deadline else 0
    
    if tenant.language == "kz":
        message = f"⏰ @{task.assignee.whatsapp_phone}, «{task.title}» тапсырмасы бойынша жағдай қалай?\n"
        message += f"📅 Дедлайн: {task.deadline.strftime('%d.%m.%Y') if task.deadline else 'белгісіз'}"
        if days_overdue > 0:
            message += f" ({days_overdue} күн бұрын өтті)"
    else:
        message = f"⏰ @{task.assignee.whatsapp_phone}, как дела с «{task.title}»?\n"
        message += f"📅 Дедлайн: {task.deadline.strftime('%d.%m.%Y') if task.deadline else 'не указан'}"
        if days_overdue > 0:
            message += f" (просрочено на {days_overdue} дн.)"
    
    try:
        # Send to group
        await whatsapp.send_message(
            instance_id=tenant.whatsapp_instance_id,
            token=tenant.whatsapp_api_token,
            phone=task.group.whatsapp_chat_id.replace("@g.us", ""),
            text=message,
            is_group=True
        )
        
        # Mark reminder sent
        task.reminder_sent = True
        
        logger.info(f"Sent overdue reminder for task {task.id}")
    except Exception as e:
        logger.error(f"Failed to send overdue reminder: {e}")


async def _send_upcoming_reminder(
    whatsapp: WhatsAppBotService,
    tenant: Tenant,
    task: Task
):
    """Send upcoming deadline reminder."""
    if not task.assignee or not task.assignee.whatsapp_phone:
        return
    
    if not task.group or not task.group.whatsapp_chat_id:
        return
    
    # Calculate hours remaining
    time_remaining = task.deadline - datetime.now() if task.deadline else None
    hours_remaining = int(time_remaining.total_seconds() / 3600) if time_remaining else 0
    
    if tenant.language == "kz":
        message = f"⚠️ @{task.assignee.whatsapp_phone}, «{task.title}» тапсырмасы бойынша дедлайн жақындады!\n"
        message += f"⏳ Қалды: {hours_remaining} сағат"
    else:
        message = f"⚠️ @{task.assignee.whatsapp_phone}, приближается дедлайн по задаче «{task.title}»!\n"
        message += f"⏳ Осталось: {hours_remaining} ч."
    
    try:
        await whatsapp.send_message(
            instance_id=tenant.whatsapp_instance_id,
            token=tenant.whatsapp_api_token,
            phone=task.group.whatsapp_chat_id.replace("@g.us", ""),
            text=message,
            is_group=True
        )
        
        logger.info(f"Sent upcoming reminder for task {task.id}")
    except Exception as e:
        logger.error(f"Failed to send upcoming reminder: {e}")


@shared_task(name="send_meeting_invitation")
def send_meeting_invitation(
    tenant_id: str,
    contact_phone: str,
    contact_name: str,
    meeting_title: str,
    meeting_datetime: str,
    inviter_name: str
) -> dict:
    """Send meeting invitation via WhatsApp."""
    return asyncio.run(_send_meeting_invitation(
        tenant_id, contact_phone, contact_name,
        meeting_title, meeting_datetime, inviter_name
    ))


async def _send_meeting_invitation(
    tenant_id: str,
    contact_phone: str,
    contact_name: str,
    meeting_title: str,
    meeting_datetime: str,
    inviter_name: str
) -> dict:
    """Async implementation of meeting invitation."""
    async with async_session_maker() as db:
        try:
            from sqlalchemy import select
            from uuid import UUID
            
            stmt = select(Tenant).where(Tenant.id == UUID(tenant_id))
            result = await db.execute(stmt)
            tenant = result.scalar_one_or_none()
            
            if not tenant or not tenant.whatsapp_instance_id:
                return {"status": "error", "message": "Tenant not found or WhatsApp not configured"}
            
            # Parse datetime
            dt = datetime.fromisoformat(meeting_datetime)
            date_str = dt.strftime("%d.%m.%Y")
            time_str = dt.strftime("%H:%M")
            
            # Build invitation message
            if tenant.language == "kz":
                message = f"Сәлеметсіз бе, {contact_name}! 👋\n\n"
                message += f"{inviter_name} Сізді кездесуге шақырады.\n\n"
                message += f"📅 Күні: {date_str}\n"
                message += f"🕒 Уақыты: {time_str}\n"
                message += f"📝 Тақырыбы: {meeting_title}\n\n"
                message += "Бұл цифрлық көмекшіден автоматты хабарлама."
            else:
                message = f"Здравствуйте, {contact_name}! 👋\n\n"
                message += f"{inviter_name} запланировал с Вами встречу.\n\n"
                message += f"📅 Дата: {date_str}\n"
                message += f"🕒 Время: {time_str}\n"
                message += f"📝 Тема: {meeting_title}\n\n"
                message += "Это автоматическое сообщение от цифрового помощника."
            
            whatsapp = WhatsAppBotService()
            result = await whatsapp.send_message(
                instance_id=tenant.whatsapp_instance_id,
                token=tenant.whatsapp_api_token,
                phone=contact_phone,
                text=message
            )
            
            return {"status": "sent", "result": result}
            
        except Exception as e:
            logger.error(f"Failed to send meeting invitation: {e}")
            return {"status": "error", "message": str(e)}
