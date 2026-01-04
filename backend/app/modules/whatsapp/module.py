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
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
WhatsApp арқылы хабарлама жіберу.

Шығару керек:
- action: "send_message" (жіберу), "check_chat" (тексеру), "analyze_chat" (талдау), "stats" (статистика)  
- name: контакт аты
- message: хабарлама мәтіні

Мысалдар:
- "Ержанға жаз тұру керек" → {"action": "send_message", "name": "Ержан", "message": "Тұру керек!"}
- "Маратпен переписканы тексер" → {"action": "check_chat", "name": "Марат"}
- "Переписканы талда" → {"action": "analyze_chat", "name": "..."}
- "WhatsApp статистикасы" → {"action": "stats"}
"""
        else:
            return """
Отправка сообщений через WhatsApp.

Извлекай:
- action: "send_message" (отправить), "check_chat" (проверить переписку), "analyze_chat" (анализ), "stats" (статистика)
- name: имя контакта  
- message: текст сообщения

ВАЖНО: Если пользователь говорит "напиши", "отправь", "скажи" + имя + что сказать — это send_message!
ВАЖНО: Если "анализ переписки", "проанализируй чат" — это analyze_chat!

Примеры:
- "Напиши Ержану чтобы он встал" → {"action": "send_message", "name": "Ержан", "message": "Вставай!"}
- "Напиши Ержану привет" → {"action": "send_message", "name": "Ержан", "message": "Привет!"}
- "Напиши ему как дела" → {"action": "send_message", "name": "...", "message": "Как дела?"}
- "Отправь Асхату сообщение привет как дела" → {"action": "send_message", "name": "Асхат", "message": "Привет, как дела?"}
- "Проверь переписку с Маратом" → {"action": "check_chat", "name": "Марат"}
- "Проанализируй переписку с Ержаном" → {"action": "analyze_chat", "name": "Ержан"}
- "Анализ чата с Асхатом" → {"action": "analyze_chat", "name": "Асхат"}
- "Кто сегодня писал" → {"action": "stats"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "напиши", "отправь", "скажи", "сообщение", "whatsapp", "ватсап", "уатсап",
            "жаз", "жібер", "хабарлама",
            "переписка", "чат", "кто писал", "статистика чатов",
            "анализ", "проанализируй", "талда",
            "write", "send", "message", "analyze"
        ]

