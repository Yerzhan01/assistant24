from __future__ import annotations
"""WhatsApp module for AI chat integration."""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class WhatsAppModule(BaseModule):
    """
    WhatsApp module handles sending messages and checking chats through AI.
    """
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="whatsapp",
            name_ru="WhatsApp",
            name_kz="WhatsApp",
            description_ru="Отправка сообщений через WhatsApp",
            description_kz="WhatsApp арқылы хабарлама жіберу",
            icon="📱"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process WhatsApp intent."""
        try:
            action = intent_data.get("action", "send_message")
            
            if action == "send_message":
                return await self._send_message(intent_data, tenant_id, language)
            elif action == "check_chat":
                return await self._check_chat(intent_data, tenant_id, language)
            elif action == "analyze_chat":
                return await self._analyze_chat(intent_data, tenant_id, language)
            elif action == "stats":
                return await self._get_stats(tenant_id, language)
            # Group actions
            elif action == "list_groups":
                return await self._list_groups(tenant_id, language)
            elif action == "send_to_group":
                return await self._send_to_group(intent_data, tenant_id, language)
            elif action == "check_group":
                return await self._check_group(intent_data, tenant_id, language)
            elif action == "analyze_group":
                return await self._analyze_group(intent_data, tenant_id, language)
            else:
                return await self._send_message(intent_data, tenant_id, language)
                
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=f"Ошибка WhatsApp: {str(e)}"
            )
    
    async def _send_message(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Send a WhatsApp message to a contact."""
        name = intent_data.get("name") or intent_data.get("contact_name") or intent_data.get("recipient")
        message_text = intent_data.get("message") or intent_data.get("text") or intent_data.get("content")
        
        if not name:
            return ModuleResponse(success=False, message="❓ Кому отправить сообщение?")
        if not message_text:
            return ModuleResponse(success=False, message="❓ Что написать?")
        
        # Find contact
        result = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.name.ilike(f"%{name}%")
            ).limit(1)
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            return ModuleResponse(success=False, message=f"❌ Контакт '{name}' не найден. Сначала сохраните контакт.")
        
        if not contact.phone or contact.phone == "0":
            return ModuleResponse(success=False, message=f"❌ У контакта {contact.name} нет номера телефона")
        
        # Get tenant for WhatsApp credentials
        from app.models.tenant import Tenant
        tenant = await self.db.get(Tenant, tenant_id)
        
        if not tenant or not tenant.greenapi_instance_id or not tenant.greenapi_token:
            return ModuleResponse(success=False, message="❌ WhatsApp не подключен. Настройте в Настройках.")
        
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
                message_text
            )
            return ModuleResponse(
                success=True, 
                message=f"✅ Сообщение отправлено {contact.name}:\n\n\"{message_text}\""
            )
        except Exception as e:
            return ModuleResponse(success=False, message=f"❌ Ошибка отправки: {str(e)}")
    
    async def _check_chat(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Check recent messages with a contact."""
        name = intent_data.get("name") or intent_data.get("contact_name")
        
        if not name:
            return ModuleResponse(success=False, message="❓ Чью переписку проверить?")
        
        # Find contact
        result = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.name.ilike(f"%{name}%")
            ).limit(1)
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            return ModuleResponse(success=False, message=f"❌ Контакт '{name}' не найден")
        
        if not contact.phone:
            return ModuleResponse(success=False, message=f"❌ У контакта {contact.name} нет номера")
        
        # Get tenant
        from app.models.tenant import Tenant
        tenant = await self.db.get(Tenant, tenant_id)
        
        if not tenant or not tenant.greenapi_instance_id or not tenant.greenapi_token:
            return ModuleResponse(success=False, message="❌ WhatsApp не подключен")
        
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
                return ModuleResponse(success=True, message=f"📭 Нет сообщений с {contact.name}")
            
            lines = [f"💬 Последние сообщения с {contact.name}:\n"]
            
            for msg in history[:5]:
                sender = "Вы" if msg.get("fromMe") else contact.name
                text = msg.get("textMessage") or msg.get("caption") or "[медиа]"
                if len(text) > 50:
                    text = text[:50] + "..."
                lines.append(f"  {sender}: {text}")
            
            return ModuleResponse(success=True, message="\n".join(lines))
            
        except Exception as e:
            return ModuleResponse(success=False, message=f"❌ Ошибка: {str(e)}")
    
    async def _get_stats(self, tenant_id: UUID, language: str) -> ModuleResponse:
        """Get WhatsApp stats."""
        from app.models.tenant import Tenant
        tenant = await self.db.get(Tenant, tenant_id)
        
        if not tenant or not tenant.greenapi_instance_id or not tenant.greenapi_token:
            return ModuleResponse(success=False, message="❌ WhatsApp не подключен")
        
        try:
            from app.services.whatsapp_bot import get_whatsapp_service
            whatsapp = get_whatsapp_service()
            
            chats = await whatsapp.get_chats(
                tenant.greenapi_instance_id,
                tenant.greenapi_token
            )
            
            if not chats:
                return ModuleResponse(success=True, message="📊 Нет данных о чатах")
            
            groups = [c for c in chats if c.get("id", "").endswith("@g.us")]
            contacts = [c for c in chats if c.get("id", "").endswith("@c.us")]
            
            msg = f"""📊 **Статистика WhatsApp:**

💬 Всего чатов: {len(chats)}
👥 Групп: {len(groups)}
👤 Контактов: {len(contacts)}"""
            
            return ModuleResponse(success=True, message=msg)
            
        except Exception as e:
            return ModuleResponse(success=False, message=f"❌ Ошибка: {str(e)}")
    
    async def _analyze_chat(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Analyze chat history with AI and provide summary/insights."""
        name = intent_data.get("name") or intent_data.get("contact_name")
        
        if not name:
            return ModuleResponse(success=False, message="❓ Чью переписку проанализировать?")
        
        # Find contact
        result = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.name.ilike(f"%{name}%")
            ).limit(1)
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            return ModuleResponse(success=False, message=f"❌ Контакт '{name}' не найден")
        
        if not contact.phone:
            return ModuleResponse(success=False, message=f"❌ У контакта {contact.name} нет номера")
        
        # Get tenant
        from app.models.tenant import Tenant
        tenant = await self.db.get(Tenant, tenant_id)
        
        if not tenant or not tenant.greenapi_instance_id or not tenant.greenapi_token:
            return ModuleResponse(success=False, message="❌ WhatsApp не подключен")
        
        # Format phone
        phone = re.sub(r'[^\d]', '', contact.phone)
        if phone.startswith('8') and len(phone) == 11:
            phone = '7' + phone[1:]
        
        try:
            from app.services.whatsapp_bot import get_whatsapp_service
            whatsapp = get_whatsapp_service()
            
            # Get more history for analysis
            history = await whatsapp.get_chat_history(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                f"{phone}@c.us",
                count=30
            )
            
            if not history:
                return ModuleResponse(success=True, message=f"📭 Нет сообщений с {contact.name} для анализа")
            
            # Format messages for AI
            messages_text = []
            for msg in history:
                sender = "Я" if msg.get("fromMe") else contact.name
                text = msg.get("textMessage") or msg.get("caption") or "[медиа]"
                timestamp = msg.get("timestamp", "")
                messages_text.append(f"{sender}: {text}")
            
            chat_content = "\n".join(messages_text[-20:])  # Last 20 messages
            
            # Use Gemini for analysis
            import google.generativeai as genai
            from app.core.config import settings
            
            if settings.gemini_api_key:
                genai.configure(api_key=settings.gemini_api_key)
                model = genai.GenerativeModel(settings.gemini_model)
                
                prompt = f"""Проанализируй эту переписку WhatsApp и дай краткий отчёт:

ПЕРЕПИСКА С {contact.name}:
{chat_content}

Формат отчёта:
1. 📝 **Краткое содержание** (2-3 предложения)
2. 🎯 **Основные темы** (список)
3. ⚠️ **Важное/Срочное** (если есть)
4. 💡 **Рекомендации** (что сделать дальше)

Отвечай кратко и по делу."""

                response = model.generate_content(prompt)
                analysis = response.text.strip()
                
                return ModuleResponse(
                    success=True,
                    message=f"📊 **Анализ переписки с {contact.name}:**\n\n{analysis}"
                )
            else:
                # No AI - just show summary
                msg_count = len(history)
                last_msg = history[0] if history else None
                last_text = last_msg.get("textMessage", "")[0:50] if last_msg else "N/A"
                
                return ModuleResponse(
                    success=True,
                    message=f"📊 Переписка с {contact.name}:\n\n📨 Сообщений: {msg_count}\n📝 Последнее: {last_text}..."
                )
            
        except Exception as e:
            return ModuleResponse(success=False, message=f"❌ Ошибка анализа: {str(e)}")
    
    # ==================== Group Actions ====================
    
    async def _list_groups(self, tenant_id: UUID, language: str) -> ModuleResponse:
        """List active WhatsApp groups."""
        from app.models.group_chat import GroupChat
        
        result = await self.db.execute(
            select(GroupChat).where(
                GroupChat.tenant_id == tenant_id,
                GroupChat.is_active == True
            ).order_by(GroupChat.name)
        )
        groups = result.scalars().all()
        
        if not groups:
            return ModuleResponse(
                success=True,
                message="📭 Нет активных групп. Активируйте группы в Настройках → WhatsApp."
            )
        
        lines = ["👥 **Ваши активные группы:**\n"]
        for g in groups:
            lines.append(f"  • {g.name}")
        
        return ModuleResponse(success=True, message="\n".join(lines))
    
    async def _send_to_group(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Send message to a WhatsApp group by name."""
        from app.models.group_chat import GroupChat
        from app.models.tenant import Tenant
        
        group_name = intent_data.get("group_name") or intent_data.get("name")
        message_text = intent_data.get("message") or intent_data.get("text")
        
        if not group_name:
            return ModuleResponse(success=False, message="❓ В какую группу отправить?")
        if not message_text:
            return ModuleResponse(success=False, message="❓ Что написать в группу?")
        
        # Find group by name (fuzzy match, active only)
        result = await self.db.execute(
            select(GroupChat).where(
                GroupChat.tenant_id == tenant_id,
                GroupChat.is_active == True,
                GroupChat.name.ilike(f"%{group_name}%")
            ).limit(1)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            return ModuleResponse(
                success=False,
                message=f"❌ Группа '{group_name}' не найдена или не активирована."
            )
        
        # Get tenant credentials
        tenant = await self.db.get(Tenant, tenant_id)
        if not tenant or not tenant.greenapi_instance_id or not tenant.greenapi_token:
            return ModuleResponse(success=False, message="❌ WhatsApp не подключен")
        
        try:
            from app.services.whatsapp_bot import get_whatsapp_service
            whatsapp = get_whatsapp_service()
            
            await whatsapp.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                group.whatsapp_chat_id,
                message_text
            )
            
            return ModuleResponse(
                success=True,
                message=f"✅ Сообщение отправлено в группу {group.name}:\n\n\"{message_text}\""
            )
        except Exception as e:
            return ModuleResponse(success=False, message=f"❌ Ошибка отправки: {str(e)}")
    
    async def _check_group(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Check recent messages in a group."""
        from app.models.group_chat import GroupChat
        from app.models.tenant import Tenant
        
        group_name = intent_data.get("group_name") or intent_data.get("name")
        
        if not group_name:
            return ModuleResponse(success=False, message="❓ Какую группу проверить?")
        
        # Find group
        result = await self.db.execute(
            select(GroupChat).where(
                GroupChat.tenant_id == tenant_id,
                GroupChat.is_active == True,
                GroupChat.name.ilike(f"%{group_name}%")
            ).limit(1)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            return ModuleResponse(success=False, message=f"❌ Группа '{group_name}' не найдена")
        
        # Get tenant
        tenant = await self.db.get(Tenant, tenant_id)
        if not tenant or not tenant.greenapi_instance_id:
            return ModuleResponse(success=False, message="❌ WhatsApp не подключен")
        
        try:
            from app.services.whatsapp_bot import get_whatsapp_service
            whatsapp = get_whatsapp_service()
            
            history = await whatsapp.get_group_messages(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                group.whatsapp_chat_id,
                count=10
            )
            
            if not history:
                return ModuleResponse(success=True, message=f"📭 Нет сообщений в группе {group.name}")
            
            lines = [f"💬 **Последние сообщения в {group.name}:**\n"]
            for msg in history[:7]:
                sender = msg.get("senderName", "Участник")
                text = msg.get("textMessage") or msg.get("caption") or "[медиа]"
                if len(text) > 60:
                    text = text[:60] + "..."
                lines.append(f"  {sender}: {text}")
            
            return ModuleResponse(success=True, message="\n".join(lines))
            
        except Exception as e:
            return ModuleResponse(success=False, message=f"❌ Ошибка: {str(e)}")
    
    async def _analyze_group(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Analyze group chat with AI."""
        from app.models.group_chat import GroupChat
        from app.models.tenant import Tenant
        
        group_name = intent_data.get("group_name") or intent_data.get("name")
        
        if not group_name:
            return ModuleResponse(success=False, message="❓ Какую группу проанализировать?")
        
        # Find group
        result = await self.db.execute(
            select(GroupChat).where(
                GroupChat.tenant_id == tenant_id,
                GroupChat.is_active == True,
                GroupChat.name.ilike(f"%{group_name}%")
            ).limit(1)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            return ModuleResponse(success=False, message=f"❌ Группа '{group_name}' не найдена")
        
        tenant = await self.db.get(Tenant, tenant_id)
        if not tenant or not tenant.greenapi_instance_id:
            return ModuleResponse(success=False, message="❌ WhatsApp не подключен")
        
        try:
            from app.services.whatsapp_bot import get_whatsapp_service
            whatsapp = get_whatsapp_service()
            
            history = await whatsapp.get_group_messages(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                group.whatsapp_chat_id,
                count=30
            )
            
            if not history:
                return ModuleResponse(success=True, message=f"📭 Нет сообщений для анализа в {group.name}")
            
            # Format for AI
            messages_text = []
            for msg in history:
                sender = msg.get("senderName", "Участник")
                text = msg.get("textMessage") or msg.get("caption") or "[медиа]"
                messages_text.append(f"{sender}: {text}")
            
            chat_content = "\n".join(messages_text[-25:])
            
            # Use Gemini for analysis
            import google.generativeai as genai
            from app.core.config import settings
            
            if settings.gemini_api_key:
                genai.configure(api_key=settings.gemini_api_key)
                model = genai.GenerativeModel(settings.gemini_model)
                
                prompt = f"""Проанализируй переписку группы WhatsApp и дай краткий отчёт:

ГРУППА: {group.name}
ПЕРЕПИСКА:
{chat_content}

Формат отчёта:
1. 📝 **Краткое содержание** (2-3 предложения)
2. 🎯 **Ключевые темы** (список)
3. 👥 **Активные участники** (кто больше пишет)
4. ⚠️ **Важное/Требует внимания** (если есть)
5. 💡 **Рекомендации**

Отвечай кратко и по делу."""

                response = model.generate_content(prompt)
                analysis = response.text.strip()
                
                return ModuleResponse(
                    success=True,
                    message=f"📊 **Анализ группы {group.name}:**\n\n{analysis}"
                )
            else:
                return ModuleResponse(
                    success=True,
                    message=f"📊 Группа {group.name}: {len(history)} сообщений. AI анализ недоступен."
                )
            
        except Exception as e:
            return ModuleResponse(success=False, message=f"❌ Ошибка анализа: {str(e)}")
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
WhatsApp арқылы хабарлама жіберу.

Шығару керек:
- action: "send_message", "check_chat", "analyze_chat", "stats", "list_groups", "send_to_group", "check_group", "analyze_group"
- name: контакт аты
- group_name: топ аты
- message: хабарлама мәтіні

Мысалдар:
- "Ержанға жаз тұру керек" → {"action": "send_message", "name": "Ержан", "message": "Тұру керек!"}
- "Маратпен переписканы тексер" → {"action": "check_chat", "name": "Марат"}
- "Менің топтарым" → {"action": "list_groups"}
- "Жұмыс тобына жаз: сәлем" → {"action": "send_to_group", "group_name": "Жұмыс", "message": "Сәлем!"}
"""
        else:
            return """
Отправка сообщений через WhatsApp.

Извлекай:
- action: "send_message", "check_chat", "analyze_chat", "stats", "list_groups", "send_to_group", "check_group", "analyze_group"
- name: имя контакта
- group_name: название группы  
- message: текст сообщения

ВАЖНО: Если "напиши", "отправь" + имя → send_message
ВАЖНО: Если "напиши в группу", "отправь в группу" → send_to_group
ВАЖНО: Если "мои группы", "покажи группы" → list_groups
ВАЖНО: Если "проанализируй группу" → analyze_group

Примеры ЛИЧНЫХ сообщений:
- "Напиши Ержану привет" → {"action": "send_message", "name": "Ержан", "message": "Привет!"}
- "Проверь переписку с Маратом" → {"action": "check_chat", "name": "Марат"}
- "Проанализируй переписку с Ержаном" → {"action": "analyze_chat", "name": "Ержан"}

Примеры ГРУППОВЫХ сообщений:
- "Покажи мои группы" → {"action": "list_groups"}
- "Напиши в группу Работа привет всем" → {"action": "send_to_group", "group_name": "Работа", "message": "Привет всем!"}
- "Что пишут в группе Семья" → {"action": "check_group", "group_name": "Семья"}
- "Проанализируй группу Проект" → {"action": "analyze_group", "group_name": "Проект"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "напиши", "отправь", "скажи", "сообщение", "whatsapp", "ватсап", "уатсап",
            "жаз", "жібер", "хабарлама",
            "переписка", "чат", "кто писал", "статистика чатов",
            "анализ", "проанализируй", "талда",
            "группа", "группу", "группы", "топ", "топқа",
            "write", "send", "message", "analyze", "group"
        ]


