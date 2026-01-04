from __future__ import annotations
"""WhatsApp Agent - Handles all WhatsApp interactions."""
from typing import List, Dict, Any
from datetime import datetime
from app.agents.base import BaseAgent, AgentTool
from sqlalchemy import select


class WhatsAppAgent(BaseAgent):
    """
    WhatsApp Agent. Manages WhatsApp messaging and interactions.
    """
    
    @property
    def name(self) -> str:
        return "WhatsAppAgent"

    @property
    def role_description(self) -> str:
        return "You are the WhatsApp Specialist. You handle messaging, chat history, and WhatsApp interactions."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — WhatsApp Агент цифрового секретаря.
        
        ИНСТРУМЕНТЫ:
        - send_message: отправить сообщение контакту (name, message)
        - get_chat_stats: статистика сообщений за сегодня
        - check_chat: проверить переписку с контактом (name)
        
        ВАЖНО: 
        - Если пользователь просит "напиши", "отправь", "скажи" кому-то — используй send_message
        - Если спрашивает "кто писал", "сколько сообщений" — используй get_chat_stats
        - Если хочет проверить переписку — используй check_chat
        
        Примеры:
        - "Напиши Ержану чтобы встал" → send_message(name="Ержан", message="Вставай!")
        - "Отправь Асхату привет" → send_message(name="Асхат", message="Привет!")
        - "Кто сегодня писал?" → get_chat_stats()
        - "Проверь переписку с Маратом" → check_chat(name="Марат")
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="send_message",
                description="Отправить сообщение контакту через WhatsApp. Параметры: name (имя контакта), message (текст).",
                parameters={
                    "name": {"type": "string", "description": "Имя контакта"},
                    "message": {"type": "string", "description": "Текст сообщения"}
                },
                function=self._send_message
            ),
            AgentTool(
                name="get_chat_stats",
                description="Получить статистику сообщений за сегодня.",
                parameters={},
                function=self._get_chat_stats
            ),
            AgentTool(
                name="check_chat",
                description="Проверить последние сообщения с контактом.",
                parameters={
                    "name": {"type": "string", "description": "Имя контакта"}
                },
                function=self._check_chat
            ),
        ]
    
    async def _send_message(self, name: str = "", message: str = "") -> str:
        """Send a WhatsApp message to a contact."""
        import re
        
        if not name:
            return "❌ Укажите имя контакта"
        if not message:
            return "❌ Укажите текст сообщения"
        
        # Find contact
        from app.models.contact import Contact
        stmt = select(Contact).where(
            Contact.tenant_id == self.tenant_id,
            Contact.name.ilike(f"%{name}%")
        ).limit(1)
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if not contact:
            return f"❌ Контакт '{name}' не найден. Сначала сохраните контакт."
        
        if not contact.phone or contact.phone == "0":
            return f"❌ У контакта {contact.name} нет номера телефона"
        
        # Get tenant for WhatsApp credentials
        from app.models.tenant import Tenant
        tenant = await self.db.get(Tenant, self.tenant_id)
        
        if not tenant or not tenant.greenapi_instance_id or not tenant.greenapi_token:
            return "❌ WhatsApp не подключен. Настройте в разделе Настройки → WhatsApp."
        
        # Format phone for WhatsApp
        phone = re.sub(r'[^\d]', '', contact.phone)
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
            return f"✅ Сообщение отправлено {contact.name}:\n\n\"{message}\""
        except Exception as e:
            return f"❌ Ошибка отправки: {str(e)}"
    
    async def _get_chat_stats(self) -> str:
        """Get today's chat statistics."""
        from app.models.tenant import Tenant
        tenant = await self.db.get(Tenant, self.tenant_id)
        
        if not tenant or not tenant.greenapi_instance_id or not tenant.greenapi_token:
            return "❌ WhatsApp не подключен"
        
        try:
            from app.services.whatsapp_bot import get_whatsapp_service
            whatsapp = get_whatsapp_service()
            
            # Get all chats
            chats = await whatsapp.get_chats(
                tenant.greenapi_instance_id,
                tenant.greenapi_token
            )
            
            if not chats:
                return "📊 Нет данных о чатах"
            
            # Count stats
            total_chats = len(chats)
            groups = [c for c in chats if c.get("id", "").endswith("@g.us")]
            contacts = [c for c in chats if c.get("id", "").endswith("@c.us")]
            
            lines = [
                f"📊 **Статистика WhatsApp:**\n",
                f"💬 Всего чатов: {total_chats}",
                f"👥 Групп: {len(groups)}",
                f"👤 Контактов: {len(contacts)}",
            ]
            
            # Show recent chats
            if chats[:5]:
                lines.append("\n📱 Последние активные:")
                for chat in chats[:5]:
                    name = chat.get("name", "") or chat.get("id", "")[:15]
                    lines.append(f"  • {name}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"❌ Ошибка получения статистики: {str(e)}"
    
    async def _check_chat(self, name: str = "") -> str:
        """Check recent messages with a contact."""
        import re
        
        if not name:
            return "❌ Укажите имя контакта"
        
        # Find contact
        from app.models.contact import Contact
        stmt = select(Contact).where(
            Contact.tenant_id == self.tenant_id,
            Contact.name.ilike(f"%{name}%")
        ).limit(1)
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()
        
        if not contact:
            return f"❌ Контакт '{name}' не найден"
        
        if not contact.phone:
            return f"❌ У контакта {contact.name} нет номера"
        
        # Get tenant
        from app.models.tenant import Tenant
        tenant = await self.db.get(Tenant, self.tenant_id)
        
        if not tenant or not tenant.greenapi_instance_id or not tenant.greenapi_token:
            return "❌ WhatsApp не подключен"
        
        # Format phone
        phone = re.sub(r'[^\d]', '', contact.phone)
        if phone.startswith('8') and len(phone) == 11:
            phone = '7' + phone[1:]
        
        try:
            from app.services.whatsapp_bot import get_whatsapp_service
            whatsapp = get_whatsapp_service()
            
            history = await whatsapp.get_chat_history(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                f"{phone}@c.us",
                count=10
            )
            
            if not history:
                return f"📭 Нет сообщений с {contact.name}"
            
            lines = [f"💬 Последние сообщения с {contact.name}:\n"]
            
            for msg in history[:5]:
                sender = "Вы" if msg.get("fromMe") else contact.name
                text = msg.get("textMessage") or msg.get("caption") or "[медиа]"
                if len(text) > 50:
                    text = text[:50] + "..."
                lines.append(f"  {sender}: {text}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"


