from __future__ import annotations
from typing import List
from datetime import datetime, timedelta
from app.agents.base import BaseAgent, AgentTool
from sqlalchemy import select
from app.models.contact import Contact


class ContactsAgent(BaseAgent):
    """Contacts Agent. Manages address book."""
    
    @property
    def name(self) -> str:
        return "ContactsAgent"

    @property
    def role_description(self) -> str:
        return "You are the Contacts Specialist. You manage the address book."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — Агент Контактов цифрового секретаря.
        
        ИНСТРУМЕНТЫ:
        - get_all_contacts: показать все контакты
        - search_contact: найти контакт (query)
        - create_contact: создать контакт (name, phone, email)
        - count_contacts: посчитать контакты
        - send_message_to_contact: отправить сообщение контакту через WhatsApp (name, message)
        
        УМНЫЕ УТОЧНЕНИЯ:
        
        ✅ Если есть имя → создавай контакт СРАЗУ!
        ❓ Если нет имени → спроси "Как зовут?"
        
        Телефон и email — НЕ ОБЯЗАТЕЛЬНЫ. Не спрашивай если не указаны.
        
        Примеры:
        - "Контакт Асхат +77001234567" → create_contact(name="Асхат", phone="+77001234567")
        - "Добавь контакт Болат" → create_contact(name="Болат")
        - "Новый контакт" → Ответить: "Как зовут?"
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="get_all_contacts",
                description="Получить все контакты.",
                parameters={},
                function=self._get_all_contacts
            ),
            AgentTool(
                name="search_contact",
                description="Найти контакт по имени.",
                parameters={
                    "query": {"type": "string", "description": "Имя для поиска"}
                },
                function=self._search_contact
            ),
            AgentTool(
                name="create_contact",
                description="Создать новый контакт. Параметры: name, phone, email.",
                parameters={
                    "name": {"type": "string", "description": "Имя контакта"},
                    "phone": {"type": "string", "description": "Телефон"},
                    "email": {"type": "string", "description": "Email"}
                },
                function=self._create_contact
            ),
            # Alias for 'add_contact' (common model hallucination)
            AgentTool(
                name="add_contact",
                description="Создать новый контакт (алиас для create_contact).",
                parameters={
                    "name": {"type": "string", "description": "Имя контакта"},
                    "phone": {"type": "string", "description": "Телефон"},
                    "email": {"type": "string", "description": "Email"}
                },
                function=self._create_contact
            ),
            AgentTool(
                name="count_contacts",
                description="Посчитать количество контактов.",
                parameters={},
                function=self._count_contacts
            ),
            AgentTool(
                name="get_neglected_contacts",
                description="Получить контакты, с которыми давно не связывались.",
                parameters={},
                function=self._get_neglected_contacts
            ),
            AgentTool(
                name="get_contacts_by_segment",
                description="Получить контакты по сегменту (client, partner, supplier, investor).",
                parameters={
                    "segment": {"type": "string", "description": "Сегмент: client, partner, supplier, investor"}
                },
                function=self._get_contacts_by_segment
            ),
            AgentTool(
                name="set_contact_segment",
                description="Установить сегмент для контакта.",
                parameters={
                    "name": {"type": "string", "description": "Имя контакта"},
                    "segment": {"type": "string", "description": "Сегмент: client, partner, supplier, investor"}
                },
                function=self._set_contact_segment
            ),
            AgentTool(
                name="send_message_to_contact",
                description="Отправить сообщение контакту через WhatsApp. Параметры: name (имя контакта), message (текст сообщения).",
                parameters={
                    "name": {"type": "string", "description": "Имя контакта"},
                    "message": {"type": "string", "description": "Текст сообщения"}
                },
                function=self._send_message_to_contact
            ),
        ]
        
    async def _get_all_contacts(self) -> str:
        stmt = select(Contact).where(Contact.tenant_id == self.tenant_id).limit(10)
        result = await self.db.execute(stmt)
        contacts = result.scalars().all()
        
        if contacts:
            lines = ["📒 Контакты:"]
            for c in contacts:
                phone = f" ({c.phone})" if c.phone else ""
                lines.append(f"  • {c.name}{phone}")
            return "\n".join(lines)
        return "📒 Контактов пока нет"
    
    async def _search_contact(self, query: str = "") -> str:
        if not query:
            return "❌ Укажите имя для поиска"
        
        stmt = select(Contact).where(
            Contact.tenant_id == self.tenant_id,
            Contact.name.ilike(f"%{query}%")
        ).limit(5)
        result = await self.db.execute(stmt)
        contacts = result.scalars().all()
        
        if contacts:
            lines = [f"🔍 Найдено по запросу '{query}':"]
            for c in contacts:
                phone = f" — {c.phone}" if c.phone else ""
                email = f" ({c.email})" if c.email else ""
                lines.append(f"  • {c.name}{phone}{email}")
            return "\n".join(lines)
        return f"❌ Контакт '{query}' не найден"
    
    async def _create_contact(self, name: str = "", phone: str = "", email: str = "", comment: str = "", **kwargs) -> str:
        # Debug logging
        import logging
        logger = logging.getLogger("contacts_agent")
        logger.info(f"Creating contact: name='{name}', phone='{phone}', tenant_id='{self.tenant_id}'")

        if not name:
            return "❌ Укажите имя контакта (параметр name)."
        
        # Phone is required (User strict requirement)
        if not phone or phone == "0" or len(phone) < 5:
             target_city = kwargs.get("city") or kwargs.get("location") or ""
             if target_city:
                 return f"❌ Я нашёл информацию, но не могу сохранить контакт '{name}' без номера телефона. Пожалуйста, уточните номер."
             return "❌ Нельзя сохранить контакт без номера телефона. Пожалуйста, укажите номер (параметр phone)."
        
        contact_phone = phone
        
        # Handle extra args
        notes = comment
        if kwargs:
            extra_info = ", ".join([f"{k}: {v}" for k, v in kwargs.items()])
            if notes:
                notes += f"\nAdditional info: {extra_info}"
            else:
                notes = f"Additional info: {extra_info}"
        
        contact = Contact(
            tenant_id=self.tenant_id,
            name=name,
            phone=contact_phone,
            email=email,
            notes=notes,
            tags=[]
        )
        self.db.add(contact)
        await self.db.commit()
        
        details = []
        if phone:
            details.append(f"📞 {phone}")
        
        return f"✅ Контакт сохранён: {name}" + (f" ({', '.join(details)})" if details else "")
    
    async def _count_contacts(self) -> str:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(Contact).where(Contact.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        count = result.scalar()
        return f"📒 У вас {count} контактов"
    
    async def _get_neglected_contacts(self) -> str:
        """Get contacts that haven't been contacted recently."""
        from app.models.meeting import Meeting
        from sqlalchemy import func, and_
        
        now = datetime.now()
        cutoff_date = now - timedelta(days=14)
        
        # Get contacts with their last meeting date
        stmt = select(Contact).where(
            Contact.tenant_id == self.tenant_id
        ).limit(20)
        result = await self.db.execute(stmt)
        contacts = result.scalars().all()
        
        neglected = []
        for c in contacts:
            # Check last meeting with this contact
            meeting_stmt = select(func.max(Meeting.start_time)).where(
                Meeting.tenant_id == self.tenant_id,
                Meeting.contact_id == c.id
            )
            meeting_result = await self.db.execute(meeting_stmt)
            last_meeting = meeting_result.scalar()
            
            if not last_meeting or last_meeting < cutoff_date:
                days_ago = (now - last_meeting).days if last_meeting else None
                neglected.append((c, days_ago))
        
        if not neglected:
            return "✅ Все контакты актуальны!"
        
        # Sort by days ago (longest first)
        neglected.sort(key=lambda x: x[1] if x[1] else 999, reverse=True)
        
        lines = ["💡 Давно не связывались:"]
        for c, days in neglected[:5]:
            days_str = f"{days} дней назад" if days else "никогда"
            lines.append(f"  📞 {c.name}: {days_str}")
            if c.phone and c.phone != "0":
                lines.append(f"     {c.phone}")
        
        return "\n".join(lines)
    
    async def _get_contacts_by_segment(self, segment: str = "") -> str:
        """Get contacts filtered by segment."""
        if not segment:
            return "❌ Укажите сегмент: client, partner, supplier, investor"
        
        segment_names = {
            "client": "🎯 Клиенты", "partner": "🤝 Партнёры",
            "supplier": "📦 Поставщики", "investor": "💰 Инвесторы"
        }
        segment_lower = segment.lower()
        
        stmt = select(Contact).where(
            Contact.tenant_id == self.tenant_id,
            Contact.segment == segment_lower
        ).limit(20)
        result = await self.db.execute(stmt)
        contacts = result.scalars().all()
        
        title = segment_names.get(segment_lower, f"📒 {segment}")
        if contacts:
            lines = [f"{title} ({len(contacts)}):"]
            for c in contacts:
                phone = f" — {c.phone}" if c.phone and c.phone != "0" else ""
                lines.append(f"  • {c.name}{phone}")
            return "\n".join(lines)
        return f"{title}: пока нет контактов"
    
    async def _set_contact_segment(self, name: str = "", segment: str = "") -> str:
        """Set segment for a contact."""
        if not name:
            return "❌ Укажите имя контакта"
        if not segment:
            return "❌ Укажите сегмент: client, partner, supplier, investor"
        
        valid = ["client", "partner", "supplier", "investor", "other"]
        segment_lower = segment.lower()
        if segment_lower not in valid:
            return f"❌ Неверный сегмент. Доступные: {', '.join(valid)}"
        
        stmt = select(Contact).where(
            Contact.tenant_id == self.tenant_id,
            Contact.name.ilike(f"%{name}%")
        ).limit(1)
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if contact:
            contact.segment = segment_lower
            await self.db.commit()
            emoji = {"client": "🎯", "partner": "🤝", "supplier": "📦", "investor": "💰"}.get(segment_lower, "📒")
            return f"✅ {contact.name} → {emoji} {segment_lower}"
        return f"❌ Контакт '{name}' не найден"
    
    async def _send_message_to_contact(self, name: str = "", message: str = "") -> str:
        """Send a WhatsApp message to a contact."""
        import re as regex
        
        if not name:
            return "❌ Укажите имя контакта"
        if not message:
            return "❌ Укажите текст сообщения"
        
        # Find contact
        stmt = select(Contact).where(
            Contact.tenant_id == self.tenant_id,
            Contact.name.ilike(f"%{name}%")
        ).limit(1)
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if not contact:
            return f"❌ Контакт '{name}' не найден"
        
        if not contact.phone or contact.phone == "0":
            return f"❌ У контакта {contact.name} нет номера телефона"
        
        # Get tenant for WhatsApp credentials
        from app.models.tenant import Tenant
        tenant = await self.db.get(Tenant, self.tenant_id)
        
        if not tenant or not tenant.greenapi_instance_id or not tenant.greenapi_token:
            return "❌ WhatsApp не подключен. Настройте в разделе Настройки."
        
        # Format phone for WhatsApp
        phone = regex.sub(r'[^\d]', '', contact.phone)
        if phone.startswith('8') and len(phone) == 11:
            phone = '7' + phone[1:]
        
        # Send via WhatsApp
        try:
            from app.services.whatsapp_bot import get_whatsapp_service
            whatsapp = get_whatsapp_service()
            await whatsapp.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                f"{phone}@c.us",
                message
            )
            return f"✅ Сообщение отправлено {contact.name}: \"{message}\""
        except Exception as e:
            return f"❌ Ошибка отправки: {str(e)}"


