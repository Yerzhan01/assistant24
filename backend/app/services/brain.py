from __future__ import annotations
"""
Autonomous Brain Service - The proactive agent that works when you sleep.

This service runs periodically (every 5-10 minutes) and performs:
1. Data enrichment (company lookups)
2. Meeting confirmation requests
3. Pending response monitoring
4. Proactive suggestions
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import google.generativeai as genai
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.meeting import Meeting, MeetingStatus
from app.models.meeting_negotiation import MeetingNegotiation, NegotiationStatus
from app.models.task import Task, TaskStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.contact import Contact
from app.models.tenant import Tenant
from app.models.user import User
from app.services.company_enrichment import CompanyEnrichmentService
from app.services.whatsapp_bot import WhatsAppBotService

logger = logging.getLogger(__name__)


class BrainAction:
    """Represents a proactive action the brain wants to take."""
    
    def __init__(
        self,
        action_type: str,
        priority: int,
        message: str,
        data:Optional[ Dict[str, Any] ] = None,
        requires_approval: bool = True
    ):
        self.action_type = action_type  # "enrich", "confirm", "remind", "suggest"
        self.priority = priority  # 1-10 (higher = more urgent)
        self.message = message  # Message to owner
        self.data = data or {}
        self.requires_approval = requires_approval


class AutonomousBrain:
    """
    The Brain that works proactively in background.
    
    Runs every 5-10 minutes via Celery Beat and:
    - Enriches new meetings/contacts with company data
    - Sends confirmation requests for upcoming meetings
    - Monitors pending negotiations
    - Suggests actions based on patterns
    """
    
    def __init__(
        self,
        db: AsyncSession,
        whatsapp:Optional[ WhatsAppBotService ] = None,
        api_key:Optional[ str ] = None,
        language: str = "ru"
    ):
        self.db = db
        self.whatsapp = whatsapp or WhatsAppBotService()
        self.api_key = api_key or settings.gemini_api_key
        self.language = language
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None
    
    async def tick(self, tenant_id: UUID) -> List[BrainAction]:
        """
        Main brain cycle - called every 5-10 minutes.
        Returns list of actions to take or notify about.
        """
        actions = []
        
        # 1. Enrich new meetings with company data
        enrich_actions = await self._check_enrichment_opportunities(tenant_id)
        actions.extend(enrich_actions)
        
        # 2. Check upcoming meetings for confirmation
        confirm_actions = await self._check_meeting_confirmations(tenant_id)
        actions.extend(confirm_actions)
        
        # 3. Check pending negotiations
        negotiation_actions = await self._check_pending_negotiations(tenant_id)
        actions.extend(negotiation_actions)
        
        # 4. Check for patterns and suggestions
        suggestion_actions = await self._generate_suggestions(tenant_id)
        actions.extend(suggestion_actions)
        
        # Sort by priority (highest first)
        actions.sort(key=lambda a: a.priority, reverse=True)
        
        return actions
    
    async def _check_enrichment_opportunities(self, tenant_id: UUID) -> List[BrainAction]:
        """Find meetings/contacts that can be enriched with company data."""
        actions = []
        now = datetime.now()
        
        # Find recent meetings without enriched data
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.start_time >= now,
                Meeting.start_time <= now + timedelta(days=7),
                Meeting.status == MeetingStatus.SCHEDULED.value,
                Meeting.location.is_(None)  # Likely not enriched
            )
        ).limit(5)
        
        result = await self.db.execute(stmt)
        meetings = result.scalars().all()
        
        enricher = CompanyEnrichmentService(api_key=self.api_key)
        
        for meeting in meetings:
            # Try to find company name in title or attendee
            company_name = enricher.extract_company_from_text(meeting.title)
            if not company_name and meeting.attendee_name:
                company_name = enricher.extract_company_from_text(meeting.attendee_name)
            
            if company_name:
                try:
                    enriched = await enricher.enrich_company(company_name)
                    
                    if enriched.get("enriched") and enriched.get("address"):
                        # Create suggestion action
                        actions.append(BrainAction(
                            action_type="enrich",
                            priority=4,
                            message=f"🔍 Нашёл информацию о компании для встречи '{meeting.title}':\n"
                                    f"📍 Адрес: {enriched.get('address')}\n"
                                    f"БИН: {enriched.get('bin', 'не найден')}\n"
                                    f"Добавить в локацию?",
                            data={
                                "meeting_id": str(meeting.id),
                                "enriched_data": enriched
                            },
                            requires_approval=True
                        ))
                except Exception as e:
                    logger.warning(f"Enrichment failed for meeting {meeting.id}: {e}")
        
        return actions
    
    async def _check_meeting_confirmations(self, tenant_id: UUID) -> List[BrainAction]:
        """Check if upcoming meetings need confirmation from attendees."""
        actions = []
        now = datetime.now()
        
        # Meetings in 1-2 hours that aren't confirmed
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.start_time >= now + timedelta(hours=1),
                Meeting.start_time <= now + timedelta(hours=2),
                Meeting.status == MeetingStatus.SCHEDULED.value  # Not yet confirmed
            )
        )
        
        result = await self.db.execute(stmt)
        meetings = result.scalars().all()
        
        for meeting in meetings:
            if meeting.contact_id or meeting.attendee_name:
                actions.append(BrainAction(
                    action_type="confirm",
                    priority=7,  # High priority - meeting is soon
                    message=f"⏰ Встреча '{meeting.title}' через ~1 час.\n"
                            f"Участник: {meeting.attendee_name or 'контакт'}\n"
                            f"Отправить подтверждение 'Всё в силе?'",
                    data={
                        "meeting_id": str(meeting.id),
                        "contact_id": str(meeting.contact_id) if meeting.contact_id else None,
                        "attendee_name": meeting.attendee_name
                    },
                    requires_approval=True
                ))
        
        return actions
    
    async def _check_pending_negotiations(self, tenant_id: UUID) -> List[BrainAction]:
        """Check for stale negotiations that need follow-up."""
        actions = []
        now = datetime.now()
        
        # Negotiations waiting for response for more than 24 hours
        stmt = select(MeetingNegotiation).where(
            and_(
                MeetingNegotiation.tenant_id == tenant_id,
                MeetingNegotiation.status == NegotiationStatus.SLOTS_SENT.value,
                MeetingNegotiation.updated_at < now - timedelta(hours=24)
            )
        )
        
        result = await self.db.execute(stmt)
        negotiations = result.scalars().all()
        
        for neg in negotiations:
            contact = await self.db.get(Contact, neg.contact_id)
            contact_name = contact.name if contact else "контакт"
            
            actions.append(BrainAction(
                action_type="follow_up",
                priority=5,
                message=f"📞 {contact_name} не ответил на предложение о встрече уже 24+ часов.\n"
                        f"Тема: {neg.meeting_title}\n"
                        f"Отправить напоминание?",
                data={
                    "negotiation_id": str(neg.id),
                    "contact_name": contact_name
                },
                requires_approval=True
            ))
        
        return actions
    
    async def _generate_suggestions(self, tenant_id: UUID) -> List[BrainAction]:
        """Generate smart suggestions based on data patterns."""
        actions = []
        now = datetime.now()
        
        # Check for tasks without deadlines that are getting old
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.deadline.is_(None),
                Task.status == TaskStatus.NEW.value,
                Task.created_at < now - timedelta(days=3)
            )
        ).limit(3)
        
        result = await self.db.execute(stmt)
        old_tasks = result.scalars().all()
        
        if old_tasks:
            task_list = "\n".join([f"• {t.title}" for t in old_tasks[:3]])
            actions.append(BrainAction(
                action_type="suggest",
                priority=3,
                message=f"💡 Эти задачи без дедлайна уже 3+ дня:\n{task_list}\n"
                        f"Установить дедлайны?",
                data={
                    "task_ids": [str(t.id) for t in old_tasks]
                },
                requires_approval=True
            ))
        
        # Check for contacts that might need follow-up
        # (no interaction in last 30 days but had meetings before)
        
        return actions
    
    async def execute_action(
        self,
        action: BrainAction,
        tenant: Tenant,
        approved: bool = True
    ) -> Dict[str, Any]:
        """Execute an approved action."""
        if action.action_type == "enrich":
            return await self._execute_enrich(action, tenant)
        elif action.action_type == "confirm":
            return await self._execute_confirm(action, tenant)
        elif action.action_type == "follow_up":
            return await self._execute_follow_up(action, tenant)
        
        return {"status": "unknown_action"}
    
    async def _execute_enrich(
        self,
        action: BrainAction,
        tenant: Tenant
    ) -> Dict[str, Any]:
        """Apply enrichment data to meeting."""
        meeting_id = action.data.get("meeting_id")
        enriched = action.data.get("enriched_data", {})
        
        if not meeting_id:
            return {"status": "error", "message": "No meeting ID"}
        
        from uuid import UUID
        meeting = await self.db.get(Meeting, UUID(meeting_id))
        if not meeting:
            return {"status": "error", "message": "Meeting not found"}
        
        # Apply enriched data
        if enriched.get("address"):
            meeting.location = enriched["address"]
        
        # Add to description
        if enriched.get("bin") or enriched.get("director"):
            extra_info = []
            if enriched.get("bin"):
                extra_info.append(f"БИН: {enriched['bin']}")
            if enriched.get("director"):
                extra_info.append(f"Директор: {enriched['director']}")
            
            if meeting.description:
                meeting.description += f"\n\n📋 {', '.join(extra_info)}"
            else:
                meeting.description = f"📋 {', '.join(extra_info)}"
        
        await self.db.flush()
        
        return {"status": "success", "message": "Meeting enriched"}
    
    async def _execute_confirm(
        self,
        action: BrainAction,
        tenant: Tenant
    ) -> Dict[str, Any]:
        """Send confirmation request to meeting attendee."""
        meeting_id = action.data.get("meeting_id")
        
        if not meeting_id:
            return {"status": "error", "message": "No meeting ID"}
        
        from uuid import UUID
        meeting = await self.db.get(Meeting, UUID(meeting_id))
        if not meeting:
            return {"status": "error", "message": "Meeting not found"}
        
        # Get contact phone
        phone = None
        if meeting.contact_id:
            contact = await self.db.get(Contact, meeting.contact_id)
            if contact:
                phone = contact.phone
        
        if not phone:
            return {"status": "error", "message": "No phone for contact"}
        
        # Send confirmation message
        if self.language == "kz":
            message = f"Сәлеметсіз бе! {meeting.start_time.strftime('%H:%M')}-дегі кездесу күшінде ме? 👋"
        else:
            message = f"Добрый день! Подтвердите, пожалуйста, встречу в {meeting.start_time.strftime('%H:%M')}. Всё в силе? 👋"
        
        if tenant.greenapi_instance_id and tenant.greenapi_token:
            await self.whatsapp.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                phone,
                message
            )
            return {"status": "success", "message": "Confirmation sent"}
        
        return {"status": "error", "message": "WhatsApp not configured"}
    
    async def _execute_follow_up(
        self,
        action: BrainAction,
        tenant: Tenant
    ) -> Dict[str, Any]:
        """Send follow-up for pending negotiation."""
        negotiation_id = action.data.get("negotiation_id")
        
        if not negotiation_id:
            return {"status": "error", "message": "No negotiation ID"}
        
        from uuid import UUID
        neg = await self.db.get(MeetingNegotiation, UUID(negotiation_id))
        if not neg:
            return {"status": "error", "message": "Negotiation not found"}
        
        contact = await self.db.get(Contact, neg.contact_id)
        if not contact:
            return {"status": "error", "message": "Contact not found"}
        
        # Send follow-up
        if self.language == "kz":
            message = f"Сәлеметсіз бе, {contact.name}! Кездесу уақыты туралы жауабыңызды күтемін. Қай уақыт ыңғайлы?"
        else:
            message = f"Здравствуйте, {contact.name}! Напоминаю о согласовании встречи. Какое время вам удобно?"
        
        if tenant.greenapi_instance_id and tenant.greenapi_token:
            await self.whatsapp.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                contact.phone,
                message
            )
            
            neg.message_count += 1
            await self.db.flush()
            
            return {"status": "success", "message": "Follow-up sent"}
        
        return {"status": "error", "message": "WhatsApp not configured"}
    
    async def get_pending_actions_summary(self, tenant_id: UUID) -> str:
        """Get summary of pending brain actions for notification."""
        actions = await self.tick(tenant_id)
        
        if not actions:
            return ""
        
        high_priority = [a for a in actions if a.priority >= 6]
        
        if not high_priority:
            return ""
        
        if self.language == "kz":
            lines = ["🧠 Сіздің назарыңыз қажет:"]
        else:
            lines = ["🧠 Требуется ваше внимание:"]
        
        for action in high_priority[:3]:
            lines.append(f"• {action.message.split(chr(10))[0]}")  # First line only
        
        return "\n".join(lines)
