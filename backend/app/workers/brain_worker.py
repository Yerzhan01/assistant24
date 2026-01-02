from __future__ import annotations
"""Celery worker for autonomous brain tasks."""
import asyncio
import logging
from typing import Any, Dict

from celery import shared_task

from app.core.database import async_session_maker
from app.models.tenant import Tenant
from app.models.user import User
from app.services.brain import AutonomousBrain, BrainAction
from app.services.whatsapp_bot import WhatsAppBotService

logger = logging.getLogger(__name__)


@shared_task(name="brain_tick")
def brain_tick() -> dict:
    """
    Main brain cycle - runs every 5-10 minutes.
    Checks all tenants for proactive actions.
    """
    return asyncio.run(_brain_tick())


async def _brain_tick() -> dict:
    """Execute brain tick for all active tenants."""
    results = {
        "tenants_checked": 0,
        "actions_found": 0,
        "notifications_sent": 0
    }
    
    async with async_session_maker() as db:
        from sqlalchemy import select
        
        # Get all active tenants
        stmt = select(Tenant).where(
            Tenant.is_active == True
        )
        result = await db.execute(stmt)
        tenants = result.scalars().all()
        
        whatsapp = WhatsAppBotService()
        
        for tenant in tenants:
            try:
                brain = AutonomousBrain(
                    db,
                    whatsapp,
                    api_key=tenant.gemini_api_key,
                    language=tenant.language or "ru"
                )
                
                # Run brain tick
                actions = await brain.tick(tenant.id)
                results["tenants_checked"] += 1
                results["actions_found"] += len(actions)
                
                # If there are high-priority actions, notify owner
                high_priority = [a for a in actions if a.priority >= 6]
                
                if high_priority and tenant.greenapi_instance_id:
                    # Get owner
                    stmt = select(User).where(
                        User.tenant_id == tenant.id,
                        User.role == "owner"
                    )
                    result = await db.execute(stmt)
                    owner = result.scalar_one_or_none()
                    
                    if owner and owner.whatsapp_phone:
                        summary = await brain.get_pending_actions_summary(tenant.id)
                        if summary:
                            await whatsapp.send_message(
                                tenant.greenapi_instance_id,
                                tenant.greenapi_token,
                                owner.whatsapp_phone,
                                summary
                            )
                            results["notifications_sent"] += 1
                
                await db.commit()
                
            except Exception as e:
                logger.error(f"Brain tick failed for tenant {tenant.id}: {e}")
    
    return results


@shared_task(name="enrich_meeting")
def enrich_meeting(meeting_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Enrich a specific meeting with company data.
    Called when a new meeting is created.
    """
    return asyncio.run(_enrich_meeting(meeting_id, tenant_id))


async def _enrich_meeting(meeting_id: str, tenant_id: str) -> Dict[str, Any]:
    """Enrich meeting with company data."""
    from uuid import UUID
    from app.models.meeting import Meeting
    from app.services.company_enrichment import CompanyEnrichmentService
    
    async with async_session_maker() as db:
        tenant = await db.get(Tenant, UUID(tenant_id))
        if not tenant:
            return {"status": "error", "message": "Tenant not found"}
        
        meeting = await db.get(Meeting, UUID(meeting_id))
        if not meeting or meeting.tenant_id != tenant.id:
            return {"status": "error", "message": "Meeting not found"}
        
        enricher = CompanyEnrichmentService(api_key=tenant.gemini_api_key)
        
        # Try to find company name in title
        company_name = enricher.extract_company_from_text(meeting.title)
        if not company_name and meeting.attendee_name:
            company_name = enricher.extract_company_from_text(meeting.attendee_name)
        
        if not company_name:
            return {"status": "skipped", "message": "No company name found"}
        
        try:
            enriched = await enricher.enrich_company(company_name)
            
            if enriched.get("enriched"):
                # Apply enriched data
                if enriched.get("address") and not meeting.location:
                    meeting.location = enriched["address"]
                
                # Add to description
                extra_info = []
                if enriched.get("bin"):
                    extra_info.append(f"БИН: {enriched['bin']}")
                if enriched.get("director"):
                    extra_info.append(f"Директор: {enriched['director']}")
                
                if extra_info:
                    if meeting.description:
                        meeting.description += f"\n\n📋 {', '.join(extra_info)}"
                    else:
                        meeting.description = f"📋 {', '.join(extra_info)}"
                
                await db.commit()
                
                # Notify owner about enrichment
                whatsapp = WhatsAppBotService()
                stmt = select(User).where(
                    User.tenant_id == tenant.id,
                    User.role == "owner"
                )
                result = await db.execute(stmt)
                owner = result.scalar_one_or_none()
                
                if owner and owner.whatsapp_phone and tenant.greenapi_instance_id:
                    lang = tenant.language or "ru"
                    if lang == "kz":
                        msg = f"🔍 '{meeting.title}' кездесуі үшін ақпарат таптым:\n"
                    else:
                        msg = f"🔍 Нашёл информацию для встречи '{meeting.title}':\n"
                    
                    if enriched.get("address"):
                        msg += f"📍 {enriched['address']}\n"
                    if enriched.get("bin"):
                        msg += f"БИН: {enriched['bin']}"
                    
                    await whatsapp.send_message(
                        tenant.greenapi_instance_id,
                        tenant.greenapi_token,
                        owner.whatsapp_phone,
                        msg
                    )
                
                return {"status": "success", "enriched": enriched}
            
        except Exception as e:
            logger.error(f"Enrichment failed: {e}")
            return {"status": "error", "message": str(e)}
    
    return {"status": "skipped", "message": "No enrichment data found"}


@shared_task(name="send_meeting_confirmation")
def send_meeting_confirmation(meeting_id: str, tenant_id: str) -> Dict[str, Any]:
    """Send confirmation request to meeting attendee."""
    return asyncio.run(_send_meeting_confirmation(meeting_id, tenant_id))


async def _send_meeting_confirmation(meeting_id: str, tenant_id: str) -> Dict[str, Any]:
    """Send meeting confirmation via WhatsApp."""
    from uuid import UUID
    from app.models.meeting import Meeting
    from app.models.contact import Contact
    
    async with async_session_maker() as db:
        tenant = await db.get(Tenant, UUID(tenant_id))
        if not tenant:
            return {"status": "error", "message": "Tenant not found"}
        
        meeting = await db.get(Meeting, UUID(meeting_id))
        if not meeting:
            return {"status": "error", "message": "Meeting not found"}
        
        # Get contact phone
        phone = None
        contact_name = meeting.attendee_name
        
        if meeting.contact_id:
            contact = await db.get(Contact, meeting.contact_id)
            if contact:
                phone = contact.phone
                contact_name = contact.name
        
        if not phone:
            return {"status": "error", "message": "No phone for contact"}
        
        # Generate message
        lang = tenant.language or "ru"
        time_str = meeting.start_time.strftime("%H:%M")
        
        if lang == "kz":
            message = f"Сәлеметсіз бе, {contact_name}! {time_str}-дегі кездесуді растаңызшы. Бәрі күшінде ме? 👋"
        else:
            message = f"Добрый день, {contact_name}! Подтвердите, пожалуйста, встречу в {time_str}. Всё в силе? 👋"
        
        if tenant.greenapi_instance_id and tenant.greenapi_token:
            whatsapp = WhatsAppBotService()
            await whatsapp.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                phone,
                message
            )
            return {"status": "success", "message": "Confirmation sent"}
        
        return {"status": "error", "message": "WhatsApp not configured"}
