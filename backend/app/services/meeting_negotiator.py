from __future__ import annotations
"""Meeting negotiator service for autonomous meeting scheduling."""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import google.generativeai as genai
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.meeting_negotiation import MeetingNegotiation, NegotiationStatus
from app.models.meeting import Meeting
from app.models.contact import Contact
from app.models.user import User
from app.services.whatsapp_bot import WhatsAppBotService
from app.services.contact_service import ContactService

logger = logging.getLogger(__name__)


# AI Prompt for parsing contact's response
NEGOTIATION_PARSE_PROMPT_RU = """
Разбери ответ контакта на предложение о встрече.

Сообщение: "{message}"
Предложенные слоты:
{slots_formatted}

Верни JSON (только JSON, без markdown):
{{
  "intent": "accept_slot" | "suggest_other" | "decline" | "unclear",
  "selected_slot_index": 0-{max_index} или null,
  "suggested_datetime": "YYYY-MM-DD HH:MM" или null,
  "decline_reason": "причина отказа" или null,
  "needs_clarification": true/false
}}

Правила:
- "accept_slot": если выбран один из предложенных слотов (среда, вторник, 14:00 и т.д.)
- "suggest_other": если предлагает другое время
- "decline": если отказывается от встречи
- "unclear": если не понятен ответ
"""

NEGOTIATION_PARSE_PROMPT_KZ = """
Кездесу ұсынысына жауапты талда.

Хабарлама: "{message}"
Ұсынылған уақыт:
{slots_formatted}

JSON қайтар:
{{
  "intent": "accept_slot" | "suggest_other" | "decline" | "unclear",
  "selected_slot_index": 0-{max_index} немесе null,
  "suggested_datetime": "YYYY-MM-DD HH:MM" немесе null,
  "decline_reason": "бас тарту себебі" немесе null,
  "needs_clarification": true/false
}}
"""


class MeetingNegotiator:
    """
    AI-powered autonomous meeting negotiator.
    Handles the full cycle: propose slots → parse response → confirm meeting.
    """
    
    def __init__(
        self, 
        db: AsyncSession, 
        whatsapp: WhatsAppBotService,
        api_key:Optional[ str ] = None,
        language: str = "ru"
    ):
        self.db = db
        self.whatsapp = whatsapp
        self.api_key = api_key or settings.gemini_api_key
        self.language = language
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None
    
    async def initiate_negotiation(
        self,
        tenant_id: UUID,
        initiator_user_id: UUID,
        contact_name: str,
        meeting_title: str,
        meeting_notes:Optional[ str ] = None,
        days_ahead: int = 7,
        num_slots: int = 3,
        whatsapp_instance_id: str = "",
        whatsapp_token: str = ""
    ) -> Dict[str, Any]:
        """
        Start autonomous meeting negotiation.
        1. Find contact
        2. Find available slots
        3. Send proposal to contact
        """
        # Find contact
        contact_service = ContactService(self.db)
        contact = await contact_service.find_by_name(tenant_id, contact_name)
        
        if not contact:
            return {
                "status": "error",
                "message": f"Контакт '{contact_name}' не найден. Добавьте его номер телефона.",
                "need_phone": True,
                "contact_name": contact_name
            }
        
        # Find available slots (placeholder - would integrate with calendar)
        slots = await self._find_available_slots(tenant_id, days_ahead, num_slots)
        
        # Create negotiation record
        negotiation = MeetingNegotiation(
            tenant_id=tenant_id,
            initiator_user_id=initiator_user_id,
            contact_id=contact.id,
            status=NegotiationStatus.INITIATED.value,
            meeting_title=meeting_title,
            meeting_notes=meeting_notes,
            proposed_slots=[s.isoformat() for s in slots],
            whatsapp_chat_id=contact.whatsapp_chat_id,
            expires_at=datetime.now() + timedelta(days=3)
        )
        
        self.db.add(negotiation)
        await self.db.flush()
        
        # Send proposal to contact
        await self._send_slot_proposal(
            negotiation, contact, slots,
            whatsapp_instance_id, whatsapp_token
        )
        
        negotiation.status = NegotiationStatus.SLOTS_SENT.value
        await self.db.flush()
        
        return {
            "status": "success",
            "negotiation_id": str(negotiation.id),
            "message": f"Отправил предложение {contact.name} с тремя вариантами времени.",
            "proposed_slots": [s.strftime("%d.%m %H:%M") for s in slots]
        }
    
    async def _find_available_slots(
        self,
        tenant_id: UUID,
        days_ahead: int = 7,
        num_slots: int = 3
    ) -> List[datetime]:
        """
        Find available time slots.
        TODO: Integrate with actual calendar/meetings to check availability.
        """
        now = datetime.now()
        slots = []
        
        # Generate slots for next weekdays at business hours
        current = now + timedelta(days=1)
        
        while len(slots) < num_slots and current <= now + timedelta(days=days_ahead):
            # Skip weekends
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                # Add slots at 10:00, 14:00, 16:00
                for hour in [10, 14, 16]:
                    slot = current.replace(hour=hour, minute=0, second=0, microsecond=0)
                    if slot > now and len(slots) < num_slots:
                        slots.append(slot)
                        break
            
            current += timedelta(days=1)
        
        return slots
    
    async def _send_slot_proposal(
        self,
        negotiation: MeetingNegotiation,
        contact: Contact,
        slots: List[datetime],
        instance_id: str,
        token: str
    ) -> None:
        """Send meeting proposal with time slots to contact."""
        # Format day names
        day_names_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_names_kz = ["Дс", "Сс", "Ср", "Бс", "Жм", "Сн", "Жс"]
        day_names = day_names_kz if self.language == "kz" else day_names_ru
        
        slots_text = "\n".join([
            f"{i+1}. {day_names[s.weekday()]} {s.strftime('%d.%m')} в {s.strftime('%H:%M')}"
            for i, s in enumerate(slots)
        ])
        
        if self.language == "kz":
            message = f"""Сәлеметсіз бе, {contact.name}! 👋

Сізбен кездесу ұйымдастырғым келеді.
📝 Тақырып: {negotiation.meeting_title}

Қай уақыт ыңғайлы?
{slots_text}

Нөмірін жазыңыз немесе басқа уақытты ұсыныңыз."""
        else:
            message = f"""Здравствуйте, {contact.name}! 👋

Хочу организовать встречу с вами.
📝 Тема: {negotiation.meeting_title}

Какое время удобно?
{slots_text}

Напишите номер или предложите другое время."""
        
        result = await self.whatsapp.send_message(
            instance_id, token,
            contact.phone,
            message
        )
        
        if result.get("idMessage"):
            negotiation.last_message_id = result["idMessage"]
            negotiation.message_count += 1
    
    async def process_contact_response(
        self,
        tenant_id: UUID,
        chat_id: str,
        message_text: str,
        instance_id: str,
        token: str
    ) -> Dict[str, Any]:
        """
        Process contact's response to meeting proposal.
        Uses AI to parse intent and extract selected slot/alternative time.
        """
        # Find active negotiation for this chat
        stmt = select(MeetingNegotiation).where(
            and_(
                MeetingNegotiation.tenant_id == tenant_id,
                MeetingNegotiation.whatsapp_chat_id == chat_id,
                MeetingNegotiation.status.in_([
                    NegotiationStatus.SLOTS_SENT.value,
                    NegotiationStatus.WAITING_RESPONSE.value,
                    NegotiationStatus.NEGOTIATING.value
                ])
            )
        ).order_by(MeetingNegotiation.created_at.desc())
        
        result = await self.db.execute(stmt)
        negotiation = result.scalar_one_or_none()
        
        if not negotiation:
            return {"status": "no_active_negotiation"}
        
        # Parse response with AI
        parsed = await self._parse_response(negotiation, message_text)
        
        if not parsed:
            return {"status": "parse_failed"}
        
        intent = parsed.get("intent")
        
        if intent == "accept_slot":
            # Contact accepted a proposed slot
            slot_index = parsed.get("selected_slot_index", 0)
            slots = negotiation.get_proposed_datetimes()
            
            if 0 <= slot_index < len(slots):
                selected_slot = slots[slot_index]
                return await self._confirm_meeting(
                    negotiation, selected_slot, instance_id, token
                )
        
        elif intent == "suggest_other":
            # Contact suggested different time
            suggested = parsed.get("suggested_datetime")
            if suggested:
                try:
                    suggested_dt = datetime.fromisoformat(suggested)
                    return await self._handle_counter_proposal(
                        negotiation, suggested_dt, instance_id, token
                    )
                except:
                    pass
            
            # Ask for clarification
            negotiation.status = NegotiationStatus.NEGOTIATING.value
            return {"status": "needs_clarification", "negotiation_id": str(negotiation.id)}
        
        elif intent == "decline":
            negotiation.status = NegotiationStatus.CANCELLED.value
            reason = parsed.get("decline_reason", "")
            return {
                "status": "declined",
                "negotiation_id": str(negotiation.id),
                "reason": reason
            }
        
        # Unclear response
        negotiation.status = NegotiationStatus.NEGOTIATING.value
        return {"status": "unclear", "needs_clarification": True}
    
    async def _parse_response(
        self,
        negotiation: MeetingNegotiation,
        message: str
    ) ->Optional[ dict ]:
        """Parse contact's response using AI."""
        if not self.model:
            return None
        
        slots = negotiation.get_proposed_datetimes()
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        
        slots_formatted = "\n".join([
            f"{i}: {day_names[s.weekday()]} {s.strftime('%d.%m %H:%M')}"
            for i, s in enumerate(slots)
        ])
        
        prompt_template = NEGOTIATION_PARSE_PROMPT_KZ if self.language == "kz" else NEGOTIATION_PARSE_PROMPT_RU
        prompt = prompt_template.format(
            message=message,
            slots_formatted=slots_formatted,
            max_index=len(slots) - 1
        )
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean markdown
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            return json.loads(text)
        except Exception as e:
            logger.error(f"Failed to parse negotiation response: {e}")
            return None
    
    async def _confirm_meeting(
        self,
        negotiation: MeetingNegotiation,
        selected_slot: datetime,
        instance_id: str,
        token: str
    ) -> Dict[str, Any]:
        """Confirm meeting and create calendar entry."""
        # Update negotiation
        negotiation.selected_slot = selected_slot
        negotiation.status = NegotiationStatus.CONFIRMED.value
        
        # Create meeting
        meeting = Meeting(
            tenant_id=negotiation.tenant_id,
            title=negotiation.meeting_title,
            description=negotiation.meeting_notes,
            scheduled_at=selected_slot,
            reminder_minutes=60,
            attendee_name=negotiation.contact.name if negotiation.contact else None
        )
        
        self.db.add(meeting)
        await self.db.flush()
        
        negotiation.meeting_id = meeting.id
        
        # Get contact for confirmation message
        contact = await self.db.get(Contact, negotiation.contact_id)
        
        # Send confirmation to contact
        if self.language == "kz":
            confirm_msg = f"✅ Керемет! Кездесу расталды:\n📅 {selected_slot.strftime('%d.%m.%Y')} {selected_slot.strftime('%H:%M')}\n📝 {negotiation.meeting_title}"
        else:
            confirm_msg = f"✅ Отлично! Встреча подтверждена:\n📅 {selected_slot.strftime('%d.%m.%Y')} в {selected_slot.strftime('%H:%M')}\n📝 {negotiation.meeting_title}"
        
        if contact:
            await self.whatsapp.send_message(
                instance_id, token,
                contact.phone,
                confirm_msg
            )
        
        return {
            "status": "confirmed",
            "negotiation_id": str(negotiation.id),
            "meeting_id": str(meeting.id),
            "selected_slot": selected_slot.isoformat(),
            "message": f"Встреча с {contact.name if contact else 'контактом'} подтверждена на {selected_slot.strftime('%d.%m %H:%M')} ✅"
        }
    
    async def _handle_counter_proposal(
        self,
        negotiation: MeetingNegotiation,
        suggested_time: datetime,
        instance_id: str,
        token: str
    ) -> Dict[str, Any]:
        """Handle when contact suggests a different time."""
        negotiation.status = NegotiationStatus.NEGOTIATING.value
        negotiation.message_count += 1
        
        # For now, auto-accept reasonable times
        # In full implementation, would check initiator's calendar
        
        # If time is in business hours, accept it
        if 9 <= suggested_time.hour <= 18 and suggested_time.weekday() < 5:
            return await self._confirm_meeting(
                negotiation, suggested_time, instance_id, token
            )
        
        # Otherwise, notify initiator for decision
        return {
            "status": "counter_proposal",
            "negotiation_id": str(negotiation.id),
            "suggested_time": suggested_time.isoformat(),
            "message": f"Контакт предложил другое время: {suggested_time.strftime('%d.%m %H:%M')}. Подтвердить?"
        }
    
    async def get_active_negotiations(
        self,
        tenant_id: UUID
    ) -> List[MeetingNegotiation]:
        """Get all active negotiations for a tenant."""
        stmt = select(MeetingNegotiation).where(
            and_(
                MeetingNegotiation.tenant_id == tenant_id,
                MeetingNegotiation.status.in_([
                    NegotiationStatus.INITIATED.value,
                    NegotiationStatus.SLOTS_SENT.value,
                    NegotiationStatus.WAITING_RESPONSE.value,
                    NegotiationStatus.NEGOTIATING.value
                ])
            )
        ).order_by(MeetingNegotiation.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
