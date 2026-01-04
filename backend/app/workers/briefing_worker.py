from __future__ import annotations
"""Celery worker for morning briefing and debt collection."""
import asyncio
import logging
from datetime import datetime

from celery import shared_task

from app.core.database import async_session_maker
from app.models.tenant import Tenant
from app.models.user import User
from app.services.morning_briefing import MorningBriefingService
from app.services.daily_report import DailyReportService
from app.services.debt_collector import DebtCollectorService
from app.services.whatsapp_bot import WhatsAppBotService

logger = logging.getLogger(__name__)


@shared_task(name="send_morning_briefing")
def send_morning_briefing() -> dict:
    """
    Daily task to send morning briefing to all tenants.
    Scheduled for 09:00 every day.
    """
    return asyncio.run(_send_morning_briefing())


@shared_task(name="send_daily_report")
def send_daily_report() -> dict:
    """
    Daily evening report (summary of day).
    Scheduled for 23:00 kz.
    """
    return asyncio.run(_send_daily_report())


async def _send_morning_briefing() -> dict:
    """Send morning briefing to all active tenants."""
    results = {"sent": 0, "failed": 0, "skipped": 0}
    
    async with async_session_maker() as db:
        from sqlalchemy import select
        
        # Get all active tenants with WhatsApp configured
        stmt = select(Tenant).where(
            Tenant.is_active == True,
            Tenant.greenapi_instance_id.isnot(None)
        )
        result = await db.execute(stmt)
        tenants = result.scalars().all()
        
        whatsapp = WhatsAppBotService()
        
        for tenant in tenants:
            try:
                # Get owner user
                stmt = select(User).where(
                    User.tenant_id == tenant.id,
                    User.role == "owner"
                )
                result = await db.execute(stmt)
                owner = result.scalar_one_or_none()
                
                if not owner or not owner.whatsapp_phone:
                    results["skipped"] += 1
                    continue
                
                # Generate briefing
                briefing_service = MorningBriefingService(
                    db,
                    api_key=tenant.gemini_api_key,
                    language=tenant.language or "ru"
                )
                
                user_name = owner.name or tenant.business_name or "Босс"
                briefing = await briefing_service.generate_briefing(
                    tenant.id,
                    user_name
                )
                
                # Send via WhatsApp
                await whatsapp.send_message(
                    tenant.greenapi_instance_id,
                    tenant.greenapi_token,
                    owner.whatsapp_phone,
                    briefing
                )
                
                results["sent"] += 1
                logger.info(f"Morning briefing sent to tenant {tenant.id}")
                
            except Exception as e:
                logger.error(f"Failed to send briefing to tenant {tenant.id}: {e}")
                results["failed"] += 1
    
    return results


async def _send_daily_report() -> dict:
    """Send evening report to all active tenants."""
    results = {"sent": 0, "failed": 0, "skipped": 0}
    
    async with async_session_maker() as db:
        from sqlalchemy import select
        
        # Get active tenants
        stmt = select(Tenant).where(
            Tenant.is_active == True,
            Tenant.greenapi_instance_id.isnot(None)
        )
        result = await db.execute(stmt)
        tenants = result.scalars().all()
        
        whatsapp = WhatsAppBotService()
        
        for tenant in tenants:
            try:
                # Get owner
                stmt = select(User).where(
                    User.tenant_id == tenant.id,
                    User.role == "owner"
                )
                result = await db.execute(stmt)
                owner = result.scalar_one_or_none()
                
                if not owner or not owner.whatsapp_phone:
                    results["skipped"] += 1
                    continue
                
                # Generate report
                service = DailyReportService(
                    db,
                    api_key=tenant.gemini_api_key,
                    language=tenant.language or "ru"
                )
                
                user_name = owner.name or "Босс"
                report = await service.generate_report(tenant.id, user_name)
                
                # Send
                await whatsapp.send_message(
                    tenant.greenapi_instance_id,
                    tenant.greenapi_token,
                    owner.whatsapp_phone,
                    report
                )
                
                results["sent"] += 1
                logger.info(f"Evening report sent to tenant {tenant.id}")
                
            except Exception as e:
                logger.error(f"Failed to send evening report to {tenant.id}: {e}")
                results["failed"] += 1
                
    return results


@shared_task(name="check_overdue_invoices")
def check_overdue_invoices() -> dict:
    """
    Check for overdue invoices and notify owners.
    Scheduled to run every few hours.
    """
    return asyncio.run(_check_overdue_invoices())


async def _check_overdue_invoices() -> dict:
    """Check overdue invoices and prepare reminder notifications."""
    results = {"tenants_checked": 0, "notifications_sent": 0}
    
    async with async_session_maker() as db:
        from sqlalchemy import select
        
        # Get all active tenants
        stmt = select(Tenant).where(
            Tenant.is_active == True,
            Tenant.greenapi_instance_id.isnot(None)
        )
        result = await db.execute(stmt)
        tenants = result.scalars().all()
        
        whatsapp = WhatsAppBotService()
        
        for tenant in tenants:
            try:
                collector = DebtCollectorService(
                    db,
                    whatsapp,
                    api_key=tenant.gemini_api_key,
                    language=tenant.language or "ru"
                )
                
                # Check for overdue invoices
                overdue = await collector.check_overdue_invoices(tenant.id)
                results["tenants_checked"] += 1
                
                if overdue:
                    # Get owner for notification
                    stmt = select(User).where(
                        User.tenant_id == tenant.id,
                        User.role == "owner"
                    )
                    result = await db.execute(stmt)
                    owner = result.scalar_one_or_none()
                    
                    if owner and owner.whatsapp_phone:
                        # Generate notification for owner
                        notification = await collector.get_owner_notification(
                            tenant.id,
                            overdue
                        )
                        
                        # Send notification
                        await whatsapp.send_message(
                            tenant.greenapi_instance_id,
                            tenant.greenapi_token,
                            owner.whatsapp_phone,
                            notification
                        )
                        
                        results["notifications_sent"] += 1
                        logger.info(f"Debt notification sent to tenant {tenant.id}: {len(overdue)} overdue")
                
                await db.commit()
                
            except Exception as e:
                logger.error(f"Failed to check invoices for tenant {tenant.id}: {e}")
    
    return results


@shared_task(name="send_debt_reminder")
def send_debt_reminder(invoice_id: str, tenant_id: str) -> dict:
    """
    Send approved debt reminder to debtor.
    Called when owner approves a reminder.
    """
    return asyncio.run(_send_debt_reminder(invoice_id, tenant_id))


async def _send_debt_reminder(invoice_id: str, tenant_id: str) -> dict:
    """Send debt reminder to specific debtor."""
    from uuid import UUID
    
    async with async_session_maker() as db:
        tenant = await db.get(Tenant, UUID(tenant_id))
        if not tenant:
            return {"status": "error", "message": "Tenant not found"}
        
        whatsapp = WhatsAppBotService()
        collector = DebtCollectorService(
            db,
            whatsapp,
            api_key=tenant.gemini_api_key,
            language=tenant.language or "ru"
        )
        
        result = await collector.approve_and_send_reminder(
            UUID(invoice_id),
            tenant
        )
        
        await db.commit()
        return result


@shared_task(name="generate_weekly_summary")
def generate_weekly_summary() -> dict:
    """
    Weekly summary of collections and finances.
    Scheduled for Monday mornings.
    """
    return asyncio.run(_generate_weekly_summary())


async def _generate_weekly_summary() -> dict:
    """Generate and send weekly collection summary."""
    results = {"sent": 0}
    
    async with async_session_maker() as db:
        from sqlalchemy import select
        
        stmt = select(Tenant).where(
            Tenant.is_active == True,
            Tenant.greenapi_instance_id.isnot(None)
        )
        result = await db.execute(stmt)
        tenants = result.scalars().all()
        
        whatsapp = WhatsAppBotService()
        
        for tenant in tenants:
            try:
                collector = DebtCollectorService(
                    db,
                    language=tenant.language or "ru"
                )
                
                summary = await collector.get_summary(tenant.id)
                
                # Format message
                msg = f"""📊 Недельная сводка по дебиторке:

💰 Собрано за месяц: {summary['collected_amount']:,.0f} ₸
⚠️ Просрочено: {summary['overdue_count']} счетов на {summary['overdue_amount']:,.0f} ₸
⏰ Скоро к оплате: {summary['due_soon_count']} счетов

Удачной недели! 🚀"""
                
                # Get owner
                stmt = select(User).where(
                    User.tenant_id == tenant.id,
                    User.role == "owner"
                )
                result = await db.execute(stmt)
                owner = result.scalar_one_or_none()
                
                if owner and owner.whatsapp_phone:
                    await whatsapp.send_message(
                        tenant.greenapi_instance_id,
                        tenant.greenapi_token,
                        owner.whatsapp_phone,
                        msg
                    )
                    results["sent"] += 1
                    
            except Exception as e:
                logger.error(f"Failed weekly summary for {tenant.id}: {e}")
    
    return results
