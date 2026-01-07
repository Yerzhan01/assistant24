from __future__ import annotations
from typing import List
from datetime import datetime, timedelta
from app.agents.base import BaseAgent, AgentTool
from sqlalchemy import select
from app.models.task import Task


class TasksAgent(BaseAgent):
    """Tasks Agent. Manages to-do items."""
    
    @property
    def name(self) -> str:
        return "TasksAgent"

    @property
    def role_description(self) -> str:
        return "You are the Tasks Specialist. You manage to-do items."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — Агент Задач цифрового секретаря.
        
        ИНСТРУМЕНТЫ:
        - get_all_tasks: показать все задачи
        - create_task: создать задачу (title, due_date)
        - complete_task: завершить задачу
        
        УМНЫЕ УТОЧНЕНИЯ (только если НЕ ХВАТАЕТ важной информации):
        
        ✅ Если есть title → создавай задачу СРАЗУ!
        ❓ Если нет title → спроси "Какую задачу создать?"
        
        Дедлайн — ОПЦИОНАЛЬНО. Если не указан, не спрашивай.
        
        НЕ ДОСТАВАЙ пользователя лишними вопросами!
        Если информации достаточно — СРАЗУ создавай.
        
        Примеры:
        - "Задача позвонить клиенту завтра" → create_task(title="позвонить клиенту", due_date="завтра")
        - "Задача" → Ответить текстом: "Какую задачу создать?"
        - "Добавь задачу купить молоко" → create_task(title="купить молоко")
        - "Напомни позвонить" → create_task(title="позвонить")
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="get_all_tasks",
                description="Получить все задачи.",
                parameters={},
                function=self._get_all_tasks
            ),
            AgentTool(
                name="create_task",
                description="Создать новую задачу. Параметры: title (название), due_date (срок, опционально).",
                parameters={
                    "title": {"type": "string", "description": "Название задачи"},
                    "due_date": {"type": "string", "description": "Срок (завтра, ДД.ММ)"}
                },
                function=self._create_task
            ),
            AgentTool(
                name="complete_task",
                description="Завершить задачу по названию.",
                parameters={
                    "title": {"type": "string", "description": "Название задачи для завершения"}
                },
                function=self._complete_task
            ),
        ]
        
    async def _get_all_tasks(self) -> str:
        stmt = select(Task).where(
            Task.tenant_id == self.tenant_id,
            Task.status != "done"  # Correct TaskStatus value
        ).limit(10)
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()
        
        if tasks:
            lines = ["📋 Ваши задачи:"]
            for t in tasks:
                status_emoji = "⏳" if t.status == "new" else "🔄"
                lines.append(f"  {status_emoji} {t.title}")
            return "\n".join(lines)
        return "📋 Активных задач нет"
    
    async def _create_task(self, title: str = "", due_date: str = "") -> str:
        if not title:
            return "❌ Укажите название задачи"
        
        # Parse due date
        import re
        now = datetime.now()
        parsed_due = None
        
        if due_date:
            if due_date.lower() in ["завтра", "tomorrow"]:
                parsed_due = now + timedelta(days=1)
            elif due_date.lower() in ["послезавтра"]:
                parsed_due = now + timedelta(days=2)
            else:
                match = re.match(r"(\d{1,2})\.(\d{1,2})", due_date)
                if match:
                    day, month = int(match.group(1)), int(match.group(2))
                    parsed_due = datetime(now.year, month, day)
        
        # === SMART CONTACT LINKING ===
        contact_info = ""
        from app.models.contact import Contact
        
        # Extract potential name from title
        name_match = re.search(r"([А-Яа-яЁёA-Za-z]{3,})", title)
        if name_match:
            potential_name = name_match.group(1)
            stmt = select(Contact).where(
                Contact.tenant_id == self.tenant_id,
                Contact.name.ilike(f"%{potential_name}%")
            ).limit(1)
            result = await self.db.execute(stmt)
            contact = result.scalar_one_or_none()
            if contact:
                contact_info = f"\n📒 Связано с: {contact.name}"
                if contact.phone:
                    contact_info += f" ({contact.phone})"
        
        task = Task(
            tenant_id=self.tenant_id,
            title=title,
            status="new",
            deadline=parsed_due
        )
        self.db.add(task)
        await self.db.commit()
        
        due_str = f" (до {parsed_due.strftime('%d.%m')})" if parsed_due else ""
        return f"✅ Задача создана: {title}{due_str}{contact_info}"
    
    async def _complete_task(self, title: str = "") -> str:
        if not title:
            return "❌ Укажите название задачи"
        
        stmt = select(Task).where(
            Task.tenant_id == self.tenant_id,
            Task.title.ilike(f"%{title}%"),
            Task.status != "done"
        ).limit(1)
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if task:
            task.status = "done"  # Correct TaskStatus value
            await self.db.commit()
            return f"✅ Задача завершена: {task.title}"
        return f"❌ Задача '{title}' не найдена"

