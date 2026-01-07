from __future__ import annotations
"""Contacts module for contact management via AI chat."""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class ContactsModule(BaseModule):
    """
    Contacts module handles creating and managing contacts through AI chat.
    """
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="contacts",
            name_ru="Контакты",
            name_kz="Байланыстар",
            description_ru="Управление контактами",
            description_kz="Байланыстарды басқару",
            icon="👥"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process contact management intent."""
        try:
            action = intent_data.get("action", "create")
            
            if action == "find":
                return await self._find_contact(intent_data, tenant_id, language)
            elif action == "create":
                return await self._create_contact(intent_data, tenant_id, language)
            elif action == "stats":
                return await self._get_stats(tenant_id, language)
            else:
                return await self._create_contact(intent_data, tenant_id, language)
                
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=f"Ошибка работы с контактами: {str(e)}"
            )
    
    async def _create_contact(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID, 
        language: str
    ) -> ModuleResponse:
        """Create a new contact."""
        name = intent_data.get("name") or intent_data.get("contact_name")
        phone = intent_data.get("phone") or intent_data.get("phone_number")
        email = intent_data.get("email")
        company = intent_data.get("company")
        notes = intent_data.get("notes")
        
        # Try to extract from original message if not parsed
        original_message = intent_data.get("original_message", "")
        
        if not name and original_message:
            # Try to extract name (first word after "контакт" or before "номер")
            name_match = re.search(r'контакт[а]?\s+(\w+)', original_message, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).capitalize()
        
        if not phone and original_message:
            # Try to extract phone number
            phone_match = re.search(r'(\+?[78]?\d{10,11})', original_message.replace(" ", "").replace("-", ""))
            if phone_match:
                phone = phone_match.group(1)
        
        if not name:
            if language == "kz":
                return ModuleResponse(success=False, message="Контакттың атын көрсетіңіз.")
            return ModuleResponse(success=False, message="Укажите имя контакта.")
        
        # Clean phone number
        if phone:
            phone = re.sub(r'[^\d+]', '', phone)
            # Ensure Kazakhstan format
            if phone.startswith('8') and len(phone) == 11:
                phone = '+7' + phone[1:]
            elif phone.startswith('7') and len(phone) == 11:
                phone = '+' + phone
        
        # Check if contact already exists
        if phone:
            existing = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.phone == phone
                )
            )
            if existing.scalar_one_or_none():
                if language == "kz":
                    return ModuleResponse(success=False, message=f"Осы нөмірмен байланыс бұрын сақталған.")
                return ModuleResponse(success=False, message=f"Контакт с таким номером уже существует.")
        
        # Create contact
        contact = Contact(
            tenant_id=tenant_id,
            name=name,
            phone=phone,
            email=email,
            company=company,
            notes=notes,
            created_at=datetime.utcnow()
        )
        
        self.db.add(contact)
        await self.db.flush()
        
        # Format response
        if language == "kz":
            message = f"👥 Байланыс сақталды:\n📌 {name}"
            if phone:
                message += f"\n📱 {phone}"
            if email:
                message += f"\n📧 {email}"
            if company:
                message += f"\n🏢 {company}"
        else:
            message = f"👥 Контакт сохранён:\n📌 {name}"
            if phone:
                message += f"\n📱 {phone}"
            if email:
                message += f"\n📧 {email}"
            if company:
                message += f"\n🏢 {company}"
        
        return ModuleResponse(
            success=True,
            message=message,
            data={
                "id": str(contact.id),
                "name": name,
                "phone": phone,
                "email": email
            }
        )
    
    
    async def _get_stats(self, tenant_id: UUID, language: str) -> ModuleResponse:
        """Get contact statistics."""
        from sqlalchemy import func
        
        stmt = select(func.count(Contact.id)).where(Contact.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        count = result.scalar_one_or_none() or 0
        
        if language == "kz":
            return ModuleResponse(success=True, message=f"📊 Барлығы {count} байланыс бар.")
        return ModuleResponse(success=True, message=f"📊 Всего у вас {count} контактов.")

    async def _find_contact(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID, 
        language: str
    ) -> ModuleResponse:
        """Find a contact by name."""
        search_name = intent_data.get("name") or intent_data.get("search_query", "")
        
        if not search_name:
            if language == "kz":
                return ModuleResponse(success=False, message="Кімнің байланысын іздейміз?")
            return ModuleResponse(success=False, message="Укажите имя контакта для поиска.")
        
        # Search for contact
        result = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.name.ilike(f"%{search_name}%")
            ).limit(5)
        )
        contacts = result.scalars().all()
        
        if not contacts:
            if language == "kz":
                return ModuleResponse(success=True, message=f"'{search_name}' бойынша байланыс табылмады.")
            return ModuleResponse(success=True, message=f"Контакт '{search_name}' не найден.")
        
        # Format response
        if language == "kz":
            message = f"📋 Табылған байланыстар ({len(contacts)}):\n"
        else:
            message = f"📋 Найденные контакты ({len(contacts)}):\n"
        
        for c in contacts:
            message += f"\n👤 {c.name}"
            if c.phone:
                message += f" — {c.phone}"
        
        return ModuleResponse(success=True, message=message)
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
Байланыстарды басқару.

Шығару керек:
- action: "create" (қосу), "find" (іздеу), "stats" (санын білу)
- name: байланыс аты
- phone: телефон нөмірі (МАҢЫЗДЫ: алдыңғы хабарлардан ізде!)
- email: электронды пошта
- company: компания

⚠️ МАҢЫЗДЫ: Егер "байланыс сақта" немесе "WhatsApp контактын сақта" десе:
1. Алдыңғы ассистент хабарларынан атау мен телефонды ізде
2. WhatsApp нөмірі әдетте +7(7XX)XXX-XX-XX форматында болады
3. Табылған мәліметтерді data-ға қос

Мысалдар:
- "Нұр Отау байланысын сақта" (алдыңғы: "+7(701)565-46-60") → {"action": "create", "name": "Нұр Отау", "phone": "+77015654660"}
"""
        else:
            return """
Управление контактами.

Извлекай:
- action: "create" (создать), "find" (найти), "stats" (статистика)
- name: имя контакта
- phone: номер телефона (ВАЖНО: ищи в предыдущих сообщениях!)
- email: электронная почта
- company: компания

⚠️ КРИТИЧЕСКИ ВАЖНО: Если пользователь говорит "сохрани контакт" или "сохрани WhatsApp контакт":
1. ОБЯЗАТЕЛЬНО найди имя и телефон в ПРЕДЫДУЩИХ сообщениях ассистента
2. WhatsApp номера обычно в формате +7(7XX)XXX-XX-XX
3. Городские номера: +7(7252)XX-XX-XX
4. Очисти номер от скобок и дефисов: +7(701)565-46-60 → +77015654660

Примеры:
- "Сохрани контакт Нур Отау" (в истории был: "+7(701)565-46-60 (WhatsApp)") → {"action": "create", "name": "Нур Отау", "phone": "+77015654660"}
- "Сохрани WhatsApp контакт" (в истории: "Гостиница: +7(701)123-45-67") → {"action": "create", "name": "Гостиница", "phone": "+77011234567"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "контакт", "добавь контакт", "сохрани контакт", "номер", "телефон",
            "байланыс", "байланыс қос", "нөмір", "телефон",
            "contact", "phone", "save contact", "сколько контактов", "қанша байланыс"
        ]
