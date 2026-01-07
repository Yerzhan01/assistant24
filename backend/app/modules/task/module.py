from __future__ import annotations
"""Task module for task management."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import pytz

from app.models.task import Task, TaskStatus, TaskPriority
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class TaskModule(BaseModule):
    """Task module handles task creation and management."""
    
    def __init__(self, db: AsyncSession, timezone: str = "Asia/Almaty") -> None:
        self.db = db
        self.timezone = pytz.timezone(timezone)
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="task",
            name_ru="Задачи",
            name_kz="Тапсырмалар",
            description_ru="Управление задачами",
            description_kz="Тапсырмаларды басқару",
            icon="📋"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process task intent."""
        try:
            action = intent_data.get("action", "create").lower()
            
            handlers = {
                "list": self._list_tasks,
                "show": self._list_tasks,
                "all": self._list_tasks,
                "today": self._list_today,
                "create": self._create_task,
                "add": self._create_task,
                "complete": self._complete_task,
                "done": self._complete_task,
                "delete": self._delete_task,
                "remove": self._delete_task,
                "stats": self._get_stats,
            }
            
            handler = handlers.get(action, self._create_task)
            return await handler(intent_data, tenant_id, user_id, language)
            
        except Exception as e:
            return ModuleResponse(success=False, message=f"Ошибка: {str(e)}")
    
    async def _list_tasks(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """List all tasks."""
        status_filter = intent_data.get("status")
        
        query = select(Task).where(Task.tenant_id == tenant_id)
        
        if status_filter and status_filter != "all":
            query = query.where(Task.status == status_filter)
        else:
            query = query.where(Task.status != TaskStatus.DONE.value)
        
        query = query.order_by(Task.deadline.asc().nullslast()).limit(20)
        
        result = await self.db.execute(query)
        tasks = result.scalars().all()
        
        if not tasks:
            if language == "kz":
                return ModuleResponse(success=True, message="📋 Тапсырмалар жоқ.")
            return ModuleResponse(success=True, message="📋 Задач нет.")
        
        priority_icons = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        status_icons = {"new": "⬜", "in_progress": "🔄", "done": "✅"}
        
        if language == "kz":
            message = f"📋 Тапсырмалар ({len(tasks)}):"
        else:
            message = f"📋 Задачи ({len(tasks)}):"
        
        for t in tasks:
            s_icon = status_icons.get(t.status, "⬜")
            p_icon = priority_icons.get(t.priority, "🟡")
            deadline_str = ""
            if t.deadline:
                deadline_str = f" (до {t.deadline.strftime('%d.%m')})"
            message += f"\n{s_icon} {p_icon} {t.title}{deadline_str}"
        
        return ModuleResponse(success=True, message=message)
    
    async def _list_today(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """List today's tasks."""
        now = datetime.now(self.timezone)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        result = await self.db.execute(
            select(Task).where(
                Task.tenant_id == tenant_id,
                Task.deadline >= today_start,
                Task.deadline < today_end,
                Task.status != TaskStatus.DONE.value
            ).order_by(Task.deadline.asc())
        )
        tasks = result.scalars().all()
        
        if not tasks:
            if language == "kz":
                return ModuleResponse(success=True, message="📋 Бүгінге тапсырмалар жоқ.")
            return ModuleResponse(success=True, message="📋 На сегодня задач нет.")
        
        if language == "kz":
            message = f"📋 Бүгінгі тапсырмалар ({len(tasks)}):"
        else:
            message = f"📋 Задачи на сегодня ({len(tasks)}):"
        
        for t in tasks:
            time_str = t.deadline.strftime("%H:%M") if t.deadline else ""
            message += f"\n⬜ {t.title}"
            if time_str and time_str != "00:00":
                message += f" ({time_str})"
        
        return ModuleResponse(success=True, message=message)
    
    async def _create_task(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Create a new task."""
        title = intent_data.get("title") or intent_data.get("task_name", "")
        
        if not title:
            if language == "kz":
                return ModuleResponse(success=False, message="Тапсырма атауын көрсетіңіз.")
            return ModuleResponse(success=False, message="Укажите название задачи.")
        
        priority_str = intent_data.get("priority", "medium").lower()
        priority_map = {
            "low": "low", "низкий": "low", "төмен": "low",
            "medium": "medium", "средний": "medium", "орта": "medium",
            "high": "high", "высокий": "high", "жоғары": "high",
            "urgent": "urgent", "срочный": "urgent", "шұғыл": "urgent",
        }
        priority = priority_map.get(priority_str, "medium")
        
        due_date = self._parse_due_date(intent_data)
        
        task = Task(
            tenant_id=tenant_id,
            creator_id=user_id,
            assignee_id=user_id,
            title=title,
            description=intent_data.get("description", ""),
            priority=priority,
            status=TaskStatus.NEW.value,
            deadline=due_date,
            created_at=datetime.now(self.timezone)
        )
        
        self.db.add(task)
        await self.db.flush()
        
        priority_icons = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        p_icon = priority_icons.get(priority, "🟡")
        
        if language == "kz":
            message = f"✅ Тапсырма құрылды:\n{p_icon} {title}"
        else:
            message = f"✅ Задача создана:\n{p_icon} {title}"
        
        if due_date:
            message += f"\n📅 {due_date.strftime('%d.%m.%Y %H:%M')}"
        
        return ModuleResponse(success=True, message=message)
    
    async def _complete_task(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Mark task as complete."""
        title = intent_data.get("title") or intent_data.get("task_name", "")
        
        if not title:
            if language == "kz":
                return ModuleResponse(success=False, message="Қай тапсырманы аяқтау керек?")
            return ModuleResponse(success=False, message="Какую задачу завершить?")
        
        result = await self.db.execute(
            select(Task).where(
                Task.tenant_id == tenant_id,
                Task.title.ilike(f"%{title}%"),
                Task.status != TaskStatus.DONE.value
            ).limit(1)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            if language == "kz":
                return ModuleResponse(success=False, message=f"'{title}' тапсырмасы табылмады.")
            return ModuleResponse(success=False, message=f"Задача '{title}' не найдена.")
        
        task.status = TaskStatus.DONE.value
        task.completed_at = datetime.now(self.timezone)
        await self.db.flush()
        
        if language == "kz":
            return ModuleResponse(success=True, message=f"✅ Тапсырма аяқталды: {task.title}")
        return ModuleResponse(success=True, message=f"✅ Задача выполнена: {task.title}")
    
    async def _delete_task(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Delete a task."""
        title = intent_data.get("title") or intent_data.get("task_name", "")
        
        if not title:
            if language == "kz":
                return ModuleResponse(success=False, message="Қай тапсырманы жою керек?")
            return ModuleResponse(success=False, message="Какую задачу удалить?")
        
        result = await self.db.execute(
            select(Task).where(
                Task.tenant_id == tenant_id,
                Task.title.ilike(f"%{title}%")
            ).limit(1)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            if language == "kz":
                return ModuleResponse(success=False, message=f"'{title}' тапсырмасы табылмады.")
            return ModuleResponse(success=False, message=f"Задача '{title}' не найдена.")
        
        task_title = task.title
        await self.db.delete(task)
        await self.db.flush()
        
        if language == "kz":
            return ModuleResponse(success=True, message=f"🗑️ Тапсырма жойылды: {task_title}")
        return ModuleResponse(success=True, message=f"🗑️ Задача удалена: {task_title}")
    
    async def _get_stats(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Get task statistics."""
        total = await self.db.execute(
            select(func.count(Task.id)).where(Task.tenant_id == tenant_id)
        )
        total_count = total.scalar_one_or_none() or 0
        
        done = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.tenant_id == tenant_id,
                Task.status == TaskStatus.DONE.value
            )
        )
        done_count = done.scalar_one_or_none() or 0
        
        pending = total_count - done_count
        
        if language == "kz":
            message = f"📊 Тапсырмалар статистикасы:\n📋 Барлығы: {total_count}\n✅ Орындалған: {done_count}\n⏳ Күтілуде: {pending}"
        else:
            message = f"📊 Статистика задач:\n📋 Всего: {total_count}\n✅ Выполнено: {done_count}\n⏳ В работе: {pending}"
        
        return ModuleResponse(success=True, message=message)
    
    def _parse_due_date(self, data: Dict[str, Any]) -> Optional[datetime]:
        """Parse due date from intent data."""
        now = datetime.now(self.timezone)
        
        # Direct date
        if "due_date" in data:
            try:
                return datetime.fromisoformat(data["due_date"])
            except:
                pass
        
        # Relative date
        relative = data.get("relative_date", "").lower()
        time_str = data.get("time", "")
        
        hour, minute = 9, 0  # Default 9:00
        if time_str:
            try:
                parts = time_str.replace(":", " ").split()
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            except:
                pass
        
        if relative in ["сегодня", "today", "бүгін"]:
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif relative in ["завтра", "tomorrow", "ертең"]:
            return (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif relative in ["послезавтра", "бүрсігүні"]:
            return (now + timedelta(days=2)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif relative in ["через неделю", "бір аптадан кейін"]:
            return (now + timedelta(days=7)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return None

    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
📋 ТАПСЫРМАЛАР МОДУЛІ

Әрекеттер (action):
- "list" — барлық тапсырмаларды көрсету
- "today" — бүгінгі тапсырмалар
- "create" — жаңа тапсырма құру
- "complete" / "done" — тапсырманы аяқтау
- "delete" — тапсырманы жою
- "stats" — статистика

Мысалдар:
- "Менің тапсырмаларым" → {"action": "list"}
- "Бүгінге не бар?" → {"action": "today"}
- "Ертеңге есеп жазу" → {"action": "create", "title": "Есеп жазу", "relative_date": "ертең"}
- "Есеп жазуды аяқтадым" → {"action": "complete", "title": "Есеп жазу"}
"""
        else:
            return """
📋 МОДУЛЬ ЗАДАЧ

Действия (action):
- "list" — показать все задачи
- "today" — задачи на сегодня
- "create" — создать задачу
- "complete" / "done" — завершить задачу
- "delete" — удалить задачу
- "stats" — статистика

Примеры запросов → JSON:
- "Мои задачи" → {"action": "list"}
- "Покажи задачи" → {"action": "list"}
- "Что на сегодня?" → {"action": "today"}
- "Задачи на сегодня" → {"action": "today"}
- "Задача на завтра: написать отчёт" → {"action": "create", "title": "Написать отчёт", "relative_date": "завтра"}
- "Создай задачу позвонить клиенту" → {"action": "create", "title": "Позвонить клиенту"}
- "Задача выполнена: отчёт" → {"action": "complete", "title": "отчёт"}
- "Удали задачу про отчёт" → {"action": "delete", "title": "отчёт"}
- "Сколько у меня задач?" → {"action": "stats"}
"""

    def get_intent_keywords(self) -> List[str]:
        return [
            "задача", "задачи", "задание", "таск", "мои задачи", "список задач",
            "на сегодня", "на завтра", "что делать",
            "тапсырма", "тапсырмалар", "менің тапсырмаларым"
        ]
