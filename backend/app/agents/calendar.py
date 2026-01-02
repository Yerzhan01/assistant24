from __future__ import annotations
from typing import List
from app.agents.base import BaseAgent, AgentTool
from app.services.calendar_service import CalendarService
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.meeting import Meeting
import re


class CalendarAgent(BaseAgent):
    """Calendar Agent. Manages meetings and schedule."""
    
    @property
    def name(self) -> str:
        return "CalendarAgent"

    @property
    def role_description(self) -> str:
        return "You are the Calendar Specialist. You manage meetings and schedule."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — Календарный Агент цифрового секретаря.
        
        ИНСТРУМЕНТЫ:
        - get_today_meetings, get_tomorrow_meetings, get_week_meetings
        - create_meeting: создать встречу (title, date_str, time_str)
        
        УМНЫЕ УТОЧНЕНИЯ:
        
        ✅ Если есть title + дата + время → создавай сразу!
        ✅ Если есть title + дата (без времени) → создавай с временем 10:00
        ❓ Если есть title, НЕТ даты → спроси "Когда? (дата и время, например: завтра в 15:00)"
        ❓ Если нет title → спроси "С кем встреча и когда?"
        
        НЕ СПРАШИВАЙ:
        - Про место (опционально)
        - Про длительность (по умолчанию 1 час)
        
        Примеры:
        - "Встреча с Асхатом завтра в 14:00" → create_meeting(title="с Асхатом", date_str="завтра", time_str="14:00")
        - "Встреча с Болатом" → Ответить: "Когда? (дата и время, например: завтра в 15:00)"
        - "Запланируй встречу" → Ответить: "С кем и когда?"
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="get_today_meetings",
                description="Получить встречи на сегодня.",
                parameters={},
                function=self._get_today_meetings
            ),
            AgentTool(
                name="get_tomorrow_meetings",
                description="Получить встречи на завтра.",
                parameters={},
                function=self._get_tomorrow_meetings
            ),
            AgentTool(
                name="get_week_meetings",
                description="Получить встречи на эту неделю.",
                parameters={},
                function=self._get_week_meetings
            ),
            AgentTool(
                name="create_meeting",
                description="Создать новую встречу. Параметры: title, date_str (завтра/ДД.ММ), time_str (ЧЧ:ММ).",
                parameters={
                    "title": {"type": "string", "description": "Название встречи"},
                    "date_str": {"type": "string", "description": "Дата (завтра, ДД.ММ)"},
                    "time_str": {"type": "string", "description": "Время (14:00)"}
                },
                function=self._create_meeting
            ),
            AgentTool(
                name="create_meeting_with_followup",
                description="Создать встречу с автоматическим follow-up. После встречи создаётся задача напоминания.",
                parameters={
                    "title": {"type": "string", "description": "Название встречи"},
                    "date_str": {"type": "string", "description": "Дата"},
                    "time_str": {"type": "string", "description": "Время"}
                },
                function=self._create_meeting_with_followup
            ),
        ]
        
    async def _get_today_meetings(self) -> str:
        calendar = CalendarService(self.db)
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        events = await calendar.get_events(self.tenant_id, start, end)
        
        if events:
            lines = ["📅 Встречи сегодня:"]
            for e in events[:5]:
                time_str = datetime.fromisoformat(e["start_time"]).strftime("%H:%M")
                lines.append(f"  {time_str} — {e['title']}")
            return "\n".join(lines)
        return "📅 Сегодня встреч нет"
    
    async def _get_tomorrow_meetings(self) -> str:
        calendar = CalendarService(self.db)
        now = datetime.now()
        start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        events = await calendar.get_events(self.tenant_id, start, end)
        
        if events:
            lines = ["📅 Встречи завтра:"]
            for e in events[:5]:
                time_str = datetime.fromisoformat(e["start_time"]).strftime("%H:%M")
                lines.append(f"  {time_str} — {e['title']}")
            return "\n".join(lines)
        return "📅 Завтра встреч нет"
    
    async def _get_week_meetings(self) -> str:
        calendar = CalendarService(self.db)
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=7)
        events = await calendar.get_events(self.tenant_id, start, end)
        
        if events:
            lines = ["📅 Встречи на эту неделю:"]
            for e in events[:10]:
                start_dt = datetime.fromisoformat(e["start_time"])
                date_str = start_dt.strftime("%d.%m %H:%M")
                lines.append(f"  {date_str} — {e['title']}")
            return "\n".join(lines)
        return "📅 На этой неделе встреч нет"
    
    async def _create_meeting(self, title: str = "", date_str: str = "", time_str: str = "10:00") -> str:
        if not title:
            return "❌ Укажите название встречи"
        
        # Parse date
        now = datetime.now()
        
        if date_str.lower() in ["завтра", "tomorrow"]:
            meeting_date = now + timedelta(days=1)
        elif date_str.lower() in ["послезавтра"]:
            meeting_date = now + timedelta(days=2)
        elif date_str.lower() in ["сегодня", "today", ""]:
            meeting_date = now
        else:
            match = re.match(r"(\d{1,2})\.(\d{1,2})", date_str)
            if match:
                day, month = int(match.group(1)), int(match.group(2))
                meeting_date = datetime(now.year, month, day)
            else:
                meeting_date = now + timedelta(days=1)
        
        # Parse time
        time_match = re.match(r"(\d{1,2}):(\d{2})", time_str)
        if time_match:
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
        else:
            hour, minute = 10, 0
        
        start_time = meeting_date.replace(hour=hour, minute=minute, second=0)
        end_time = start_time + timedelta(hours=1)
        
        # === SMART CONTACT LINKING ===
        contact_info = ""
        contact_id = None
        from app.models.contact import Contact
        
        # Extract potential name from title
        name_match = re.search(r"(?:с\s+)?([А-Яа-яЁёA-Za-z]+)", title)
        if name_match:
            potential_name = name_match.group(1)
            stmt = select(Contact).where(
                Contact.tenant_id == self.tenant_id,
                Contact.name.ilike(f"%{potential_name}%")
            ).limit(1)
            result = await self.db.execute(stmt)
            contact = result.scalar_one_or_none()
            if contact:
                contact_id = contact.id
                contact_info = f"\n📒 Контакт: {contact.name}"
                if contact.phone:
                    contact_info += f" ({contact.phone})"
        
        # === CONFLICT DETECTION ===
        conflict_warning = ""
        conflict_stmt = select(Meeting).where(
            Meeting.tenant_id == self.tenant_id,
            Meeting.start_time >= start_time - timedelta(minutes=30),
            Meeting.start_time <= start_time + timedelta(minutes=30)
        ).limit(1)
        conflict_result = await self.db.execute(conflict_stmt)
        existing_meeting = conflict_result.scalar_one_or_none()
        
        if existing_meeting:
            existing_time = existing_meeting.start_time.strftime("%H:%M")
            conflict_warning = f"\n⚠️ Внимание: уже есть встреча в {existing_time} — \"{existing_meeting.title}\""
        
        # Create meeting
        event = Meeting(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            contact_id=contact_id
        )
        self.db.add(event)
        await self.db.commit()
        
        return f"✅ Встреча запланирована: {title} — {start_time.strftime('%d.%m в %H:%M')}{contact_info}{conflict_warning}"
    
    async def _create_meeting_with_followup(self, title: str = "", date_str: str = "", time_str: str = "10:00") -> str:
        """Create meeting with automatic follow-up task."""
        meeting_result = await self._create_meeting(title, date_str, time_str)
        
        if not meeting_result.startswith("✅"):
            return meeting_result
        
        from app.models.task import Task
        now = datetime.now()
        follow_up_date = now + timedelta(days=1)
        
        follow_up_task = Task(
            tenant_id=self.tenant_id,
            title=f"📞 Follow-up: {title}",
            status="new",
            priority="high",
            deadline=follow_up_date
        )
        self.db.add(follow_up_task)
        await self.db.commit()
        
        return f"{meeting_result}\n\n📋 **Follow-up задача:** 📞 {title} (срок: {follow_up_date.strftime('%d.%m')})"

