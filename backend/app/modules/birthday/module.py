from __future__ import annotations
"""Birthday module for birthday reminders."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.birthday import Birthday
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class BirthdayModule(BaseModule):
    """
    Birthday module handles birthday tracking and reminders.
    """
    
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
        user_id:Optional[ UUID ] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process birthday intent."""
        try:
            person_name = intent_data.get("person_name", "")
            relationship = intent_data.get("relationship", "other")
            notes = intent_data.get("notes")
            
            # Parse date
            print(f"DEBUG BIRTHDAY INTENT: {intent_data}")
            birth_date = self._parse_date(intent_data)
            print(f"DEBUG BIRTHDAY DATE: {birth_date}")
            
            if not birth_date or not person_name:
                return ModuleResponse(
                    success=False,
                    message=t("errors.invalid_data", language)
                )
            
            # Create birthday
            birthday = Birthday(
                tenant_id=tenant_id,
                # user_id is not in model
                name=person_name, # model uses 'name', not 'person_name'
                date=birth_date,
                # relationship is not in model!
                notes=notes,
                reminder_days=3
            )
            
            self.db.add(birthday)
            await self.db.flush()
            
            # Format date for display
            months = {
                "ru": ["января", "февраля", "марта", "апреля", "мая", "июня",
                       "июля", "августа", "сентября", "октября", "ноября", "декабря"],
                "kz": ["қаңтар", "ақпан", "наурыз", "сәуір", "мамыр", "маусым",
                       "шілде", "тамыз", "қыркүйек", "қазан", "қараша", "желтоқсан"]
            }
            
            month_name = months.get(language, months["ru"])[birth_date.month - 1]
            date_display = f"{birth_date.day} {month_name}"
            
            message = t(
                "modules.birthday.saved",
                language,
                name=person_name,
                date=date_display
            )
            
            return ModuleResponse(
                success=True,
                message=message,
                data={
                    "id": str(birthday.id),
                    "person_name": person_name,
                    "birth_date": birth_date.isoformat()
                }
            )
            
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=t("errors.invalid_data", language)
            )
    
    def _parse_date(self, data: Dict[str, Any]) ->Optional[ date ]:
        """Parse birth date from intent data."""
        # Month mapping
        month_map = {
            # Russian
            "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
            "мая": 5, "июня": 6, "июля": 7, "августа": 8,
            "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
            "январь": 1, "февраль": 2, "март": 3, "апрель": 4,
            "май": 5, "июнь": 6, "июль": 7, "август": 8,
            "сентябрь": 9, "октябрь": 10, "ноябрь": 11, "декабрь": 12,
            # Kazakh
            "қаңтар": 1, "ақпан": 2, "наурыз": 3, "сәуір": 4,
            "мамыр": 5, "маусым": 6, "шілде": 7, "тамыз": 8,
            "қыркүйек": 9, "қазан": 10, "қараша": 11, "желтоқсан": 12,
        }
        
        # Try ISO format first
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
                # Robust day extraction (handle "7 го", "7th", etc)
                if isinstance(day, str):
                    day_match = re.search(r'\d+', day)
                    if day_match:
                        day = int(day_match.group())
                    else:
                        return None
                else:
                    day = int(day)
                
                # Robust month extraction
                if isinstance(month, str):
                    # Clean month string
                    month_clean = month.lower().strip()
                    # Check for "7-го марта" case where month might be separate or part of string
                    month = month_map.get(month_clean, None)
                    if not month:
                         # Try to parse if month is a number in string "03"
                         if month_clean.isdigit():
                             month = int(month_clean)
                else:
                    month = int(month)
                
                if day and month:
                    # Use current year for simplicity, but handle leap years if needed
                    try:
                        return date(datetime.now().year, month, day)
                    except ValueError:
                        # Day is out of range for month (e.g. Feb 30)
                        return None

            except (ValueError, TypeError):
                pass
        
        return None
    
    def get_ai_instructions(self, language: str = "ru") -> str:

        if language == "kz":
            return """
Туған күндерді анықтау.

Шығару керек:
- person_name: адамның аты
- date: туған күні YYYY-MM-DD форматында (егер жыл белгісіз болса, ағымдағы жылды қолданыңыз). Жергілікті уақытты ескеріп, "ертең", "бүгін", "келесі аптада" деген сөздерді нақты күнге айналдырыңыз.
- relationship: қатынас түрі (client, partner, friend, family, colleague, other)
- notes: қосымша ақпарат

Мысалдар:
- "Әйелімнің туған күні 15 наурыз" → {"person_name": "әйелім", "date": "2025-03-15", "relationship": "family"}
- "Болаттың туған күні ертең" (егер бүгін 2025-01-01 болса) → {"person_name": "Болат", "date": "2025-01-02"}
"""
        else:
            return """
Определяй дни рождения.

Извлекай:
- person_name: имя человека
- date: дата рождения в формате YYYY-MM-DD (если год неизвестен, используй текущий или следующий, если дата уже прошла). Преобразуй "завтра", "сегодня", "через неделю" в конкретную дату.
- relationship: тип отношений (client, partner, friend, family, colleague, other)
- notes: дополнительная информация

Примеры:
- "День рождения жены 15 марта" → {"person_name": "жена", "date": "2025-03-15", "relationship": "family"}
- "У Болата ДР завтра" (если сегодня 2025-01-01) → {"person_name": "Болат", "date": "2025-01-02"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "день рождения", "др", "родился", "юбилей", "дата рождения",
            "туған күн", "туылды", "мерейтой"
        ]
