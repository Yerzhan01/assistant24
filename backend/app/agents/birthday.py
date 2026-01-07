from __future__ import annotations
from typing import List
from datetime import datetime, date
from app.agents.base import BaseAgent, AgentTool
from sqlalchemy import select, extract
from app.models.birthday import Birthday
import re


class BirthdayAgent(BaseAgent):
    """Birthday Agent. Manages birthday reminders."""
    
    @property
    def name(self) -> str:
        return "BirthdayAgent"

    @property
    def role_description(self) -> str:
        return "You are the Birthday Specialist. You manage birthday reminders."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — Агент Дней Рождений цифрового секретаря.
        
        ИНСТРУМЕНТЫ:
        - get_upcoming_birthdays: ближайшие ДР
        - get_all_birthdays: все ДР
        - create_birthday: создать запись (name, date_str)
        
        УМНЫЕ УТОЧНЕНИЯ:
        
        ✅ Если есть имя + дата → создавай СРАЗУ!
        ❓ Если есть имя, НЕТ даты → спроси "Когда день рождения? (ДД.ММ)"
        ❓ Если нет имени → спроси "Чей день рождения?"
        
        НЕ СПРАШИВАЙ про reminder_days (по умолчанию 3 дня).
        
        Примеры:
        - "ДР Армана 15 марта" → create_birthday(name="Арман", date_str="15.03")
        - "У Армана ДР завтра" → create_birthday(name="Арман", date_str="завтра")
        - "День рождения жены" → Ответить: "Какого числа?"
        - "Добавь день рождения" → Ответить: "Чей и когда?"
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="get_upcoming_birthdays",
                description="Получить ближайшие дни рождения.",
                parameters={},
                function=self._get_upcoming_birthdays
            ),
            AgentTool(
                name="get_all_birthdays",
                description="Получить все дни рождения.",
                parameters={},
                function=self._get_all_birthdays
            ),
            AgentTool(
                name="create_birthday",
                description="Создать запись о дне рождения. Параметры: name (имя), date_str (дата ДД.ММ или 'завтра').",
                parameters={
                    "name": {"type": "string", "description": "Имя человека"},
                    "date_str": {"type": "string", "description": "Дата в формате ДД.ММ или 'завтра'"}
                },
                function=self._create_birthday
            ),
        ]
        
    async def _get_upcoming_birthdays(self) -> str:
        now = datetime.now()
        current_month = now.month
        
        stmt = select(Birthday).where(
            Birthday.tenant_id == self.tenant_id,
            extract('month', Birthday.date) == current_month
        ).limit(5)
        result = await self.db.execute(stmt)
        birthdays = result.scalars().all()
        
        if birthdays:
            lines = ["🎂 Ближайшие дни рождения:"]
            for b in birthdays:
                date_str = b.date.strftime("%d.%m")
                lines.append(f"  • {b.name}: {date_str}")
            return "\n".join(lines)
        return "🎂 В этом месяце дней рождения нет"
    
    async def _get_all_birthdays(self) -> str:
        stmt = select(Birthday).where(Birthday.tenant_id == self.tenant_id).limit(10)
        result = await self.db.execute(stmt)
        birthdays = result.scalars().all()
        
        if birthdays:
            lines = ["🎂 Все дни рождения:"]
            for b in birthdays:
                date_str = b.date.strftime("%d.%m")
                lines.append(f"  • {b.name}: {date_str}")
            return "\n".join(lines)
        return "🎂 Дней рождения пока нет"
    
    async def _create_birthday(self, name: str = "", date_str: str = "") -> str:
        if not name:
            return "❌ Укажите имя"
        
        # Parse date
        from datetime import timedelta
        now = datetime.now()
        
        if date_str.lower() in ["завтра", "tomorrow"]:
            birth_date = (now + timedelta(days=1)).date()
        elif date_str.lower() in ["послезавтра"]:
            birth_date = (now + timedelta(days=2)).date()
        elif date_str.lower() in ["сегодня", "today"]:
            birth_date = now.date()
        else:
            # Try to parse DD.MM format
            match = re.match(r"(\d{1,2})\.(\d{1,2})", date_str)
            if match:
                day, month = int(match.group(1)), int(match.group(2))
                birth_date = date(now.year, month, day)
            else:
                # Default to tomorrow
                birth_date = (now + timedelta(days=1)).date()
        
        birthday = Birthday(
            tenant_id=self.tenant_id,
            name=name,
            date=birth_date,
            reminder_days=3
        )
        self.db.add(birthday)
        await self.db.commit()
        
        return f"✅ День рождения сохранён: {name} — {birth_date.strftime('%d.%m')}"

