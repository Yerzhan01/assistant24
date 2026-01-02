from __future__ import annotations
"""Meeting module for calendar and scheduling."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID
import re

from sqlalchemy.ext.asyncio import AsyncSession
import pytz

from app.core.i18n import t
from app.models.meeting import Meeting
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class MeetingModule(BaseModule):
    """
    Meeting module handles calendar and scheduling.
    """
    
    def __init__(self, db: AsyncSession, timezone: str = "Asia/Almaty") -> None:
        self.db = db
        self.timezone = pytz.timezone(timezone)
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="meeting",
            name_ru="Встречи",
            name_kz="Кездесулер",
            description_ru="Календарь и планирование",
            description_kz="Күнтізбе және жоспарлау",
            icon="📅"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id:Optional[ UUID ] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process meeting intent."""
        try:
            print(f"DEBUG MEETING: intent_data={intent_data}")
            action = intent_data.get("action", "create")
            query_time = self._parse_datetime(intent_data)
            print(f"DEBUG MEETING: query_time={query_time}")
            
            # Handle LIST/COUNT intent
            if action in ["list", "count", "query"]:
                return await self._list_meetings(tenant_id, query_time, language)
            
            # Handle CANCEL intent
            if action in ["cancel", "delete"]:
                return await self._cancel_meeting(intent_data, tenant_id, user_id, language)

            # Handle RESCHEDULE intent
            if action in ["reschedule", "move", "update"]:
                return await self._reschedule_meeting(intent_data, tenant_id, user_id, language)
            
            # DEFAULT: CREATE intent
            title = intent_data.get("title", "Встреча")
            description = intent_data.get("description")
            location = intent_data.get("location")
            attendees = intent_data.get("attendees", [])
            
            # Handle relative dates
            start_time = query_time
            
            if not start_time:
                print("DEBUG MEETING: start_time is None!")
                return ModuleResponse(
                    success=False,
                    message="ER001: Не удалось определить время встречи." 
                )

            # Validation: specific title or attendees required
            # If title is generic "Встреча" and no attendees/description, ask for more info
            is_generic_title = title.lower() in ["встреча", "кездесу", "meeting"]
            if is_generic_title and not attendees and not description:
                msg = "Кіммен кездесу жоспарлаймыз?" if language == "kz" else "С кем встречаемся? Или уточните тему (например: Встреча с клиентом)."
                return ModuleResponse(
                    success=False, 
                    message=msg
                )
            
            # Duration (default 1 hour)
            duration_minutes = intent_data.get("duration_minutes", 60)
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Create meeting
            meeting = Meeting(
                tenant_id=tenant_id,
                user_id=user_id,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                location=location,
                attendees=[{"name": a} for a in (attendees if isinstance(attendees, list) else [attendees])],
                reminder_minutes=[60, 15]
            )
            
            self.db.add(meeting)
            await self.db.flush()
            
            # Format response
            date_str = start_time.strftime("%d.%m.%Y")
            time_str = start_time.strftime("%H:%M")
            # Handle attendees (dict or str)
            if meeting.attendees:
                attendee_names = []
                for a in meeting.attendees:
                    if isinstance(a, dict):
                        attendee_names.append(a.get("name", "Unknown"))
                    else:
                        attendee_names.append(str(a))
                attendees_str = ", ".join(attendee_names)
            else:
                attendees_str = "-"
            
            message = t(
                "modules.meeting.created",
                language,
                title=title,
                date=date_str,
                time=time_str,
                attendees=attendees_str
            )
            
            return ModuleResponse(
                success=True,
                message=message,
                data={
                    "id": str(meeting.id),
                    "title": title,
                    "start_time": start_time.isoformat(),
                    "attendees": meeting.attendees
                }
            )
            
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=f"Ошибка обработки встречи: {str(e)}"
            )
    
    async def _list_meetings(
        self,
        tenant_id: UUID,
        target_date: Optional[datetime],
        language: str
    ) -> ModuleResponse:
        """List meetings for a specific date."""
        from sqlalchemy import select, and_
        
        if not target_date:
            target_date = datetime.now(self.timezone)
        
        # Define day range
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Query meetings
        result = await self.db.execute(
            select(Meeting).where(
                and_(
                    Meeting.tenant_id == tenant_id,
                    Meeting.start_time >= start_of_day,
                    Meeting.start_time <= end_of_day
                )
            ).order_by(Meeting.start_time)
        )
        meetings = result.scalars().all()
        
        count = len(meetings)
        date_str = target_date.strftime("%d.%m.%Y")
        
        if count == 0:
            msg = f"📅 {date_str}: Жоспар бос." if language == "kz" else f"📅 {date_str}: Планов нет."
            return ModuleResponse(success=True, message=msg)
        
        msg = f"📅 {date_str}: {count} кездесу бар:\n" if language == "kz" else f"📅 {date_str}: {count} встреч(и):\n"
        
        for m in meetings:
            time_str = m.start_time.strftime("%H:%M")
            msg += f"\n⏰ {time_str} — {m.title}"
            
        return ModuleResponse(success=True, message=msg)

    async def _cancel_meeting(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Cancel meetings."""
        from sqlalchemy import select, and_, delete
        
        # Determine scope: specific or all for date
        target_date = self._parse_datetime(intent_data)
        if not target_date:
            target_date = datetime.now(self.timezone)
            
        is_all = intent_data.get("is_all", False)
        
        # Define day range
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        if is_all:
             # Find all meetings for this day
            stmt = select(Meeting).where(
                and_(
                    Meeting.tenant_id == tenant_id,
                    Meeting.start_time >= start_of_day,
                    Meeting.start_time <= end_of_day
                )
            )
            result = await self.db.execute(stmt)
            meetings = result.scalars().all()
            
            if not meetings:
                msg = "На этот день встреч и так нет." if language == "ru" else "Бұл күні кездесулер жоқ."
                return ModuleResponse(success=True, message=msg)
                
            # Perform deletion
            delete_stmt = delete(Meeting).where(
                and_(
                    Meeting.tenant_id == tenant_id,
                    Meeting.start_time >= start_of_day,
                    Meeting.start_time <= end_of_day
                )
            )
            await self.db.execute(delete_stmt)
            await self.db.flush() # Commit handled by caller
            
            msg = f"✅ Отменено встреч: {len(meetings)}" if language == "ru" else f"✅ {len(meetings)} кездесу жойылды"
            return ModuleResponse(success=True, message=msg)
            
        else:
             # Find specific meeting by title or closest time?
             # For now, simplistic approach: only 'all' is fully supported safely via text
             return ModuleResponse(
                 success=False, 
                 message="Для отмены укажите 'отмени все встречи' или удалите через календарь. Отмена конкретной встречи текстом пока в разработке."
             )

    async def _reschedule_meeting(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Reschedule a meeting."""
        from sqlalchemy import select, and_, desc
        
        # New time
        new_time = self._parse_datetime(intent_data)
        if not new_time:
             # Try 'new_time' explicit field if 'time' was mapped to old_time
             if "new_time" in intent_data:
                 intent_data["time"] = intent_data["new_time"] # Hack for reuse parser
                 new_time = self._parse_datetime(intent_data)
        
        if not new_time:
            return ModuleResponse(success=False, message="На какое время перенесем?")

        # Target date (defaults to new_time date if only time changed)
        target_date = new_time.date()
        
        # Find meeting to move
        # 1. By exact ID (not supported in text yet)
        # 2. By old_time if provided
        # 3. By title match on that day
        # 4. Fallback: Most recently created meeting on that day?
        
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                # Filter by approximate date (assume meeting is on the same day unless specified)
                 Meeting.start_time >= datetime.combine(target_date, datetime.min.time()).astimezone(self.timezone),
                 Meeting.start_time <= datetime.combine(target_date, datetime.max.time()).astimezone(self.timezone)
            )
        )
        
        # If old_time provided
        old_time_str = intent_data.get("old_time")
        if old_time_str:
             # Parse old time
             try:
                 oh, om = map(int, old_time_str.split(":"))
                 # We need to filter where hour/minute match approximately
                 # But database stores UTC/localized.
                 # Python filtering might be easier for small sets
                 pass
             except:
                 pass
        
        # Add ordering: Most recently created first!
        stmt = stmt.order_by(desc(Meeting.created_at))
        
        result = await self.db.execute(stmt)
        meetings = result.scalars().all()
        
        if not meetings:
             return ModuleResponse(success=False, message="Встреча для переноса не найдена на этот день.")
             
        # Pick the best candidate
        # Strategy: The most recently created meeting today/target_date is the most likely target for "move it".
        target_meeting = meetings[0]
        
        # Calculate end time duration preserver
        duration = target_meeting.end_time - target_meeting.start_time
        
        # Update
        old_start = target_meeting.start_time
        target_meeting.start_time = new_time
        target_meeting.end_time = new_time + duration
        
        await self.db.flush()
        
        date_str = new_time.strftime("%d.%m")
        time_str = new_time.strftime("%H:%M")
        
        msg = t(
            "modules.meeting.created", # Reuse created msg or generic success
            language,
            title=target_meeting.title,
            date=date_str,
            time=time_str,
            attendees=", ".join([a.get("name","") for a in target_meeting.attendees]) if target_meeting.attendees else "-"
        )
        # Prefix with "Reschuled"
        prefix = "✅ Кездесу ауыстырылды: " if language == "kz" else "✅ Встреча перенесена: "
        
        return ModuleResponse(
            success=True,
            message=prefix + f"{target_meeting.title} — {date_str} в {time_str}"
        )

    def _parse_datetime(self, data: Dict[str, Any]) ->Optional[ datetime ]:
        """Parse datetime from intent data, handling relative dates."""
        now = datetime.now(self.timezone)
        
        # Check for explicit datetime
        if "datetime" in data:
            dt = datetime.fromisoformat(data["datetime"])
            if dt.tzinfo is None:
                return self.timezone.localize(dt)
            return dt
        
        # Handle relative date
        relative_date = data.get("relative_date", "").lower()
        time_str = data.get("time", "12:00")
        
        # Parse time
        try:
            if ":" in time_str:
                hour, minute = map(int, time_str.split(":"))
            else:
                hour = int(time_str)
                minute = 0
        except (ValueError, AttributeError):
            hour, minute = 12, 0
        
        # Determine date
        if relative_date in ["сегодня", "today", "бүгін"]:
            target_date = now.date()
        elif relative_date in ["завтра", "tomorrow", "ертең"]:
            target_date = now.date() + timedelta(days=1)
        elif relative_date in ["послезавтра", "бүрсігүні"]:
            target_date = now.date() + timedelta(days=2)
        elif "date" in data:
            try:
                from datetime import date
                target_date = date.fromisoformat(data["date"])
            except (ValueError, TypeError):
                target_date = now.date()
        else:
            # Fallback for unknown relative_date or missing data
            if "action" in data and data["action"] in ["list", "count", "cancel", "delete"]:
                 target_date = now.date()
            else:
                 target_date = now.date() + timedelta(days=1)
        
        return self.timezone.localize(
            datetime(target_date.year, target_date.month, target_date.day, hour, minute)
        )
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
Кездесулер мен жоспарларды анықтау.

Шығару керек:
- action: "create" (құру), "list" (қарау), "cancel" (жою)
- is_all: true (егер "барлығын" десе)
- title: кездесу атауы
- relative_date: "бүгін", "ертең", "бүрсігүні" немесе нақты күн
- time: уақыт (мысалы "15:00")
- attendees: қатысушылар тізімі
- location: орын (бар болса)
- duration_minutes: ұзақтығы минуттарда (әдепкі 60)

Мысалдар:
- "Ертең қанша кездесу бар?" → {"action": "list", "relative_date": "ертең"}
- "Бүгінгі барлық кездесуді жой" → {"action": "cancel", "relative_date": "бүгін", "is_all": true}
- "Ертең 15:00-де Болатпен кездесу" → {"action": "create", "title": "Болатпен кездесу", "relative_date": "ертең", "time": "15:00", "attendees": ["Болат"]}
"""
        else:
            return """
Определяй встречи и планы.

Извлекай:
- action: "create" (создать), "list" (посмотреть), "cancel" (отменить/удалить), "reschedule" (перенести)
- is_all: true (если "все" или "всю")
- title: название встречи
- relative_date: "сегодня", "завтра", "послезавтра" или конкретная дата
- time: время (например "15:00")
- new_time: новое время (для переноса)
- attendees: список участников
- location: место (если указано)
- duration_minutes: длительность в минутах (по умолчанию 60)

Примеры:
- "Сколько встреч на завтра?" → {"action": "list", "relative_date": "завтра"}
- "Что у меня на сегодня?" → {"action": "list", "relative_date": "сегодня"}
- "Отмени все встречи на завтра" → {"action": "cancel", "relative_date": "завтра", "is_all": true}
- "Перенеси встречу на 11:00" → {"action": "reschedule", "relative_date": "завтра", "new_time": "11:00"}
- "Встреча с Болатом завтра в 15:00" → {"action": "create", "title": "Встреча с Болатом", "relative_date": "завтра", "time": "15:00", "attendees": ["Болат"]}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "встреча", "созвон", "звонок", "митинг", "обед",
            "кездесу", "қоңырау", "жиналыс",
            "сколько встреч", "жоспар", "план", "календарь",
            "отмени", "удали", "жой", "снести",
            "перенеси", "ауыстыр", "move", "reschedule", "поменяй время"
        ]
