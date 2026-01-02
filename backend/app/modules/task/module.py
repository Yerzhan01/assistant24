from __future__ import annotations
"""Task module for task management via AI chat."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
import pytz

from app.core.i18n import t
from app.models.task import Task, TaskStatus, TaskPriority
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class TaskModule(BaseModule):
    """
    Task module handles creating and managing tasks through AI chat.
    """
    
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
            icon="✅"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process task creation intent."""
        try:
            title = intent_data.get("title") or intent_data.get("task_name", "Задача")
            description = intent_data.get("description", "")
            
            # Parse priority
            priority_str = intent_data.get("priority", "medium").lower()
            priority_map = {
                "low": TaskPriority.LOW,
                "низкий": TaskPriority.LOW,
                "төмен": TaskPriority.LOW,
                "medium": TaskPriority.MEDIUM,
                "средний": TaskPriority.MEDIUM,
                "орта": TaskPriority.MEDIUM,
                "high": TaskPriority.HIGH,
                "высокий": TaskPriority.HIGH,
                "жоғары": TaskPriority.HIGH,
                "urgent": TaskPriority.URGENT,
                "срочный": TaskPriority.URGENT,
                "шұғыл": TaskPriority.URGENT,
            }
            priority = priority_map.get(priority_str, TaskPriority.MEDIUM)
            
            # Parse due date
            due_date = self._parse_due_date(intent_data)
            
            # Create task
            task = Task(
                tenant_id=tenant_id,

                creator_id=user_id,
                assignee_id=user_id,
                title=title,
                description=description,
                priority=priority.value if hasattr(priority, 'value') else priority,
                status=TaskStatus.NEW.value,
                deadline=due_date,
                created_at=datetime.now(self.timezone)
            )
            
            self.db.add(task)
            await self.db.flush()
            
            # Format response
            if due_date:
                date_str = due_date.strftime("%d.%m.%Y")
                if language == "kz":
                    message = f"✅ Тапсырма құрылды:\n📌 {title}\n📅 Мерзімі: {date_str}\n⭐ Маңыздылығы: {priority_str}"
                else:
                    message = f"✅ Задача создана:\n📌 {title}\n📅 Срок: {date_str}\n⭐ Приоритет: {priority_str}"
            else:
                if language == "kz":
                    message = f"✅ Тапсырма құрылды:\n📌 {title}\n⭐ Маңыздылығы: {priority_str}"
                else:
                    message = f"✅ Задача создана:\n📌 {title}\n⭐ Приоритет: {priority_str}"
            
            return ModuleResponse(
                success=True,
                message=message,
                data={
                    "id": str(task.id),
                    "title": title,
                    "due_date": due_date.isoformat() if due_date else None,
                    "priority": priority_str
                }
            )
            
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=f"Ошибка создания задачи: {str(e)}"
            )
    
    def _parse_due_date(self, data: Dict[str, Any]) -> Optional[datetime]:
        """Parse due date from intent data."""
        now = datetime.now(self.timezone)
        
        # Check for explicit date
        if "due_date" in data:
            try:
                return datetime.fromisoformat(data["due_date"])
            except (ValueError, TypeError):
                pass
        
        # Handle relative date
        relative_date = data.get("relative_date", "").lower()
        
        if relative_date in ["сегодня", "today", "бүгін"]:
            return now.replace(hour=23, minute=59, second=0, microsecond=0)
        elif relative_date in ["завтра", "tomorrow", "ертең"]:
            return (now + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
        elif relative_date in ["послезавтра", "бүрсігүні"]:
            return (now + timedelta(days=2)).replace(hour=23, minute=59, second=0, microsecond=0)
        elif relative_date in ["через неделю", "бір аптадан кейін"]:
            return (now + timedelta(days=7)).replace(hour=23, minute=59, second=0, microsecond=0)
        
        return None
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
Тапсырмаларды құру және басқару.

Шығару керек:
- title: тапсырма атауы
- description: сипаттама (бар болса)
- relative_date: "бүгін", "ертең", "бүрсігүні", "бір аптадан кейін"
- priority: "төмен", "орта", "жоғары", "шұғыл"

Мысалдар:
- "Ертеңге есеп жазу" → {"title": "Есеп жазу", "relative_date": "ертең"}
- "Шұғыл: клиентке қоңырау шалу" → {"title": "Клиентке қоңырау шалу", "priority": "шұғыл"}
- "Тапсырма: сайтты жаңарту" → {"title": "Сайтты жаңарту"}
"""
        else:
            return """
Создание и управление задачами.

Извлекай:
- title: название задачи
- description: описание (если есть)
- relative_date: "сегодня", "завтра", "послезавтра", "через неделю"
- priority: "низкий", "средний", "высокий", "срочный"

Примеры:
- "Задача на завтра: написать отчёт" → {"title": "Написать отчёт", "relative_date": "завтра"}
- "Срочно позвонить клиенту" → {"title": "Позвонить клиенту", "priority": "срочный"}
- "Поставь задачу сделать презентацию" → {"title": "Сделать презентацию"}
- "Напомни оплатить счёт завтра" → {"title": "Оплатить счёт", "relative_date": "завтра"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "задача", "задачу", "напомни", "напоминание", "сделать", "поставь",
            "тапсырма", "еске сал", "жасау керек",
            "todo", "task", "reminder"
        ]
