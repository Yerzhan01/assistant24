from __future__ import annotations
"""Daily Report service for evening summary."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from uuid import UUID

import google.generativeai as genai
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.meeting import Meeting, MeetingStatus
from app.models.task import Task, TaskStatus
from app.models.chat_message import ChatMessage
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)


REPORT_PROMPT_RU = """
Сгенерируй вечерний отчет для предпринимателя. Тон профессиональный, но краткий.

Имя: {user_name}
Дата: {date}

Данные за сегодня:
1. Встречи ({meetings_count}):
{meetings}

2. Выполненные задачи:
{done_tasks}

3. План на завтра:
{pending_tasks}

4. Коммуникации (кто писал/звонил и суть):
{chat_history}

Инструкция:
- Твоя задача — дать "саммари" дня.
- В разделе коммуникаций выдели ГЛАВНОЕ: с кем говорил и о чем договорились (или что просили).
- Если сообщений слишком много, сгруппируй их по контактам.
- Если сообщений не было, напиши "Тихий день".
- В конце предложи 1-2 задачи, которые стоит перенести на завтра или приоритезировать.

Формат:
"Вечерний отчет 🌙
...
 коммуникации ...
...
Итог: ..."
"""

class DailyReportService:
    """
    Service for generating end-of-day reports.
    Includes meetings, tasks, and conversation summaries.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        api_key: Optional[str] = None,
        language: str = "ru"
    ):
        self.db = db
        self.api_key = api_key or settings.gemini_api_key
        self.language = language
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-3-flash-preview") # Use smart model for summary
        else:
            self.model = None

    async def generate_report(
        self,
        tenant_id: UUID,
        user_name: str = "Босс"
    ) -> str:
        """Generate evening report."""
        data = await self._collect_data(tenant_id)
        
        if self.model:
            return await self._generate_with_ai(data, user_name)
        else:
            return self._generate_fallback(data, user_name)

    async def _collect_data(self, tenant_id: UUID) -> Dict[str, Any]:
        """Collect daily data including chats."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # 1. Meetings
        stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.start_time >= today_start,
                Meeting.start_time < today_end,
                Meeting.status != MeetingStatus.CANCELLED.value
            )
        ).order_by(Meeting.start_time)
        result = await self.db.execute(stmt)
        meetings = result.scalars().all()
        
        # 2. Done Tasks
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.updated_at >= today_start,
                Task.status == TaskStatus.DONE.value
            )
        )
        result = await self.db.execute(stmt)
        done_tasks = result.scalars().all()
        
        # 3. Pending/Tomorrow Tasks
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.status != TaskStatus.DONE.value,
                Task.deadline >= today_start, # Include overdue? Maybe separately.
                Task.deadline < today_end + timedelta(days=1) # UP to end of tomorrow
            )
        ).order_by(Task.deadline)
        result = await self.db.execute(stmt)
        pending_tasks = result.scalars().all()
        
        # 4. Chat History (New!)
        # Get messages from today
        stmt = select(ChatMessage).where(
            and_(
                ChatMessage.tenant_id == tenant_id,
                ChatMessage.created_at >= today_start
            )
        ).order_by(ChatMessage.created_at)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        return {
            "date": now.strftime("%d.%m.%Y"),
            "meetings": meetings,
            "done_tasks": done_tasks,
            "pending_tasks": pending_tasks,
            "messages": messages,
            "meetings_count": len(meetings)
        }

    async def _generate_with_ai(self, data: Dict[str, Any], user_name: str) -> str:
        """Use AI to summarize the day."""
        
        # Format Meetings
        meetings_txt = "\n".join([f"- {m.start_time.strftime('%H:%M')} {m.title}" for m in data["meetings"]]) or "Нет встреч"
        
        # Format Tasks
        done_txt = "\n".join([f"- [x] {t.title}" for t in data["done_tasks"]]) or "Нет завершенных"
        pending_txt = "\n".join([f"- [ ] {t.title} (Дедлайн: {t.deadline.strftime('%d.%m %H:%M')})" for t in data["pending_tasks"]]) or "Задач нет"
        
        # Format Chat History for Summary
        # Group by Chat ID to make it readable for AI
        chats: Dict[str, List[str]] = {}
        for msg in data["messages"]:
            chat_id = msg.chat_id
            if chat_id not in chats:
                chats[chat_id] = []
            
            # Format: "User: text" or "AI: text"
            # Try to resolve name if possible? For now raw ID or "You"
            sender = "Вы" if msg.role == "assistant" else "Собеседник" # Or extract name from content if I saved it
            
            # If I saved [Name]: text, use it
            content = msg.content
            if msg.role == "user" and "]: " in content[:30]:
                content = content # Already has name
            else:
                content = f"{sender}: {content}"
                
            chats[chat_id].append(content)
            
        chat_summary_input = ""
        if not chats:
            chat_summary_input = "Сообщений не было."
        else:
            for chat_id, lines in chats.items():
                chat_summary_input += f"\nЧат {chat_id}:\n" + "\n".join(lines[-10:]) # Last 10 msgs per chat to save tokens
                
        prompt = REPORT_PROMPT_RU.format(
            user_name=user_name,
            date=data["date"],
            meetings_count=data["meetings_count"],
            meetings=meetings_txt,
            done_tasks=done_txt,
            pending_tasks=pending_txt,
            chat_history=chat_summary_input
        )
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI Report generation failed: {e}")
            return self._generate_fallback(data, user_name)

    def _generate_fallback(self, data: Dict[str, Any], user_name: str) -> str:
        """Simple fallback if AI fails."""
        lines = [f"🌙 Отчет за {data['date']}:", ""]
        lines.append(f"📅 Встреч: {data['meetings_count']}")
        lines.append(f"✅ Выполнено задач: {len(data['done_tasks'])}")
        lines.append(f"📝 Активных чатов: {len(set(m.chat_id for m in data['messages']))}")
        return "\n".join(lines)
