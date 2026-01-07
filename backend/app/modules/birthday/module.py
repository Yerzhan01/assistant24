from __future__ import annotations
"""Birthday module for birthday reminders."""
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID
import re

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.birthday import Birthday
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class BirthdayModule(BaseModule):
    """Birthday module handles birthday tracking and reminders."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="birthday",
            name_ru="Дни рождения",
            name_kz="Туған күндер",
            description_ru="Напоминания о праздниках",
            description_kz="Мерекелер туралы еске салулар",
            icon="🎂"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process birthday intent."""
        try:
            action = intent_data.get("action", "create").lower()
            
            handlers = {
                "list": self._list_birthdays,
                "show": self._list_birthdays,
                "all": self._list_birthdays,
                "upcoming": self._list_upcoming,
                "week": self._list_upcoming,
                "create": self._create_birthday,
                "add": self._create_birthday,
                "delete": self._delete_birthday,
                "remove": self._delete_birthday,
            }
            
            handler = handlers.get(action, self._create_birthday)
            return await handler(intent_data, tenant_id, language)
            
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=f"Ошибка: {str(e)}"
            )
    
    async def _list_birthdays(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """List all birthdays."""
        result = await self.db.execute(
            select(Birthday)
            .where(Birthday.tenant_id == tenant_id)
            .order_by(extract('month', Birthday.date), extract('day', Birthday.date))
            .limit(20)
        )
        birthdays = result.scalars().all()
        
        if not birthdays:
            if language == "kz":
                return ModuleResponse(success=True, message="🎂 Туған күндер тізімі бос.")
            return ModuleResponse(success=True, message="🎂 Список дней рождения пуст.")
        
        if language == "kz":
            message = f"🎂 Туған күндер ({len(birthdays)}):"
        else:
            message = f"🎂 Дни рождения ({len(birthdays)}):"
        
        for b in birthdays:
            date_str = b.date.strftime("%d.%m")
            message += f"\n🎈 {b.name} — {date_str}"
        
        return ModuleResponse(success=True, message=message)
    
    async def _list_upcoming(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """List upcoming birthdays (next 7 days)."""
        today = date.today()
        
        result = await self.db.execute(
            select(Birthday).where(Birthday.tenant_id == tenant_id)
        )
        all_birthdays = result.scalars().all()
        
        # Filter upcoming (within 7 days, considering year wrap)
        upcoming = []
        for b in all_birthdays:
            # Create this year's birthday
            try:
                this_year_bday = b.date.replace(year=today.year)
            except ValueError:
                # Feb 29 in non-leap year
                this_year_bday = b.date.replace(year=today.year, day=28)
            
            # If already passed, check next year
            if this_year_bday < today:
                try:
                    this_year_bday = b.date.replace(year=today.year + 1)
                except ValueError:
                    this_year_bday = b.date.replace(year=today.year + 1, day=28)
            
            days_until = (this_year_bday - today).days
            if 0 <= days_until <= 7:
                upcoming.append((b, days_until, this_year_bday))
        
        # Sort by days until
        upcoming.sort(key=lambda x: x[1])
        
        if not upcoming:
            if language == "kz":
                return ModuleResponse(success=True, message="🎂 Жақын арада туған күндер жоқ.")
            return ModuleResponse(success=True, message="🎂 В ближайшую неделю дней рождения нет.")
        
        if language == "kz":
            message = f"🎂 Жақын арадағы туған күндер ({len(upcoming)}):"
        else:
            message = f"🎂 Ближайшие дни рождения ({len(upcoming)}):"
        
        for b, days, bday_date in upcoming:
            date_str = bday_date.strftime("%d.%m")
            if days == 0:
                when = "сегодня! 🎉" if language == "ru" else "бүгін! 🎉"
            elif days == 1:
                when = "завтра" if language == "ru" else "ертең"
            else:
                when = f"через {days} дн." if language == "ru" else f"{days} күннен кейін"
            message += f"\n🎈 {b.name} — {date_str} ({when})"
        
        return ModuleResponse(success=True, message=message)
    
    async def _create_birthday(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Create a new birthday."""
        person_name = intent_data.get("person_name") or intent_data.get("name", "")
        
        if not person_name:
            if language == "kz":
                return ModuleResponse(success=False, message="Адамның атын көрсетіңіз.")
            return ModuleResponse(success=False, message="Укажите имя человека.")
        
        birth_date = self._parse_date(intent_data)
        
        if not birth_date:
            if language == "kz":
                return ModuleResponse(success=False, message="Туған күнді көрсетіңіз (мысалы: 15 наурыз).")
            return ModuleResponse(success=False, message="Укажите дату рождения (например: 15 марта).")
        
        notes = intent_data.get("notes", "")
        
        birthday = Birthday(
            tenant_id=tenant_id,
            name=person_name,
            date=birth_date,
            notes=notes,
            reminder_days=3
        )
        
        self.db.add(birthday)
        await self.db.flush()
        
        date_str = birth_date.strftime("%d.%m")
        
        if language == "kz":
            message = f"🎂 Туған күн сақталды:\n🎈 {person_name} — {date_str}"
        else:
            message = f"🎂 День рождения сохранён:\n🎈 {person_name} — {date_str}"
        
        return ModuleResponse(success=True, message=message)
    
    async def _delete_birthday(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Delete a birthday."""
        person_name = intent_data.get("person_name") or intent_data.get("name", "")
        
        if not person_name:
            if language == "kz":
                return ModuleResponse(success=False, message="Кімнің туған күнін жою керек?")
            return ModuleResponse(success=False, message="Чей день рождения удалить?")
        
        result = await self.db.execute(
            select(Birthday).where(
                Birthday.tenant_id == tenant_id,
                Birthday.name.ilike(f"%{person_name}%")
            ).limit(1)
        )
        birthday = result.scalar_one_or_none()
        
        if not birthday:
            if language == "kz":
                return ModuleResponse(success=False, message=f"'{person_name}' туған күні табылмады.")
            return ModuleResponse(success=False, message=f"День рождения '{person_name}' не найден.")
        
        name = birthday.name
        await self.db.delete(birthday)
        await self.db.flush()
        
        if language == "kz":
            return ModuleResponse(success=True, message=f"🗑️ {name} туған күні жойылды.")
        return ModuleResponse(success=True, message=f"🗑️ День рождения {name} удалён.")
    
    def _parse_date(self, data: Dict[str, Any]) -> Optional[date]:
        """Parse birth date from intent data."""
        month_map = {
            "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
            "мая": 5, "июня": 6, "июля": 7, "августа": 8,
            "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
            "январь": 1, "февраль": 2, "март": 3, "апрель": 4,
            "май": 5, "июнь": 6, "июль": 7, "август": 8,
            "сентябрь": 9, "октябрь": 10, "ноябрь": 11, "декабрь": 12,
            "қаңтар": 1, "ақпан": 2, "наурыз": 3, "сәуір": 4,
            "мамыр": 5, "маусым": 6, "шілде": 7, "тамыз": 8,
            "қыркүйек": 9, "қазан": 10, "қараша": 11, "желтоқсан": 12,
        }
        
        # Try ISO format
        if "date" in data:
            try:
                return date.fromisoformat(data["date"])
            except (ValueError, TypeError):
                pass
        
        # Try day + month
        day = data.get("day")
        month = data.get("month")
        
        if day and month:
            try:
                if isinstance(day, str):
                    day_match = re.search(r'\d+', day)
                    day = int(day_match.group()) if day_match else None
                else:
                    day = int(day)
                
                if isinstance(month, str):
                    month_clean = month.lower().strip()
                    month = month_map.get(month_clean)
                    if not month and month_clean.isdigit():
                        month = int(month_clean)
                else:
                    month = int(month)
                
                if day and month:
                    return date(datetime.now().year, month, day)
            except (ValueError, TypeError):
                pass
        
        return None
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
🎂 ТУҒАН КҮНДЕР МОДУЛІ

Әрекеттер (action):
- "list" — барлық туған күндерді көрсету
- "upcoming" / "week" — жақын арадағы (7 күн ішінде)
- "create" — жаңа туған күн қосу
- "delete" — туған күнді жою

Мысалдар:
- "Туған күндер тізімі" → {"action": "list"}
- "Жақын арадағы туған күндер" → {"action": "upcoming"}
- "Осы аптадағы туған күндер" → {"action": "week"}
- "Болаттың туған күні 15 наурыз" → {"action": "create", "name": "Болат", "date": "2026-03-15"}
- "Болаттың туған күнін жой" → {"action": "delete", "name": "Болат"}
"""
        else:
            return """
🎂 МОДУЛЬ ДНЕЙ РОЖДЕНИЯ

Действия (action):
- "list" — показать все дни рождения
- "upcoming" / "week" — ближайшие (в течение 7 дней)
- "create" — добавить день рождения
- "delete" — удалить день рождения

Примеры запросов → JSON:
- "Покажи дни рождения" → {"action": "list"}
- "Список дней рождения" → {"action": "list"}
- "Какие дни рождения на этой неделе?" → {"action": "upcoming"}
- "Ближайшие дни рождения" → {"action": "upcoming"}
- "День рождения Болата 15 марта" → {"action": "create", "name": "Болат", "date": "2026-03-15"}
- "У мамы ДР 8 марта" → {"action": "create", "name": "мама", "date": "2026-03-08"}
- "Удали день рождения Болата" → {"action": "delete", "name": "Болат"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "день рождения", "дни рождения", "др", "родился", "юбилей",
            "ближайшие дни рождения", "у кого день рождения",
            "туған күн", "туған күндер", "туылды", "мерейтой"
        ]
