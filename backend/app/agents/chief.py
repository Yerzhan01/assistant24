from __future__ import annotations
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from app.agents.base import BaseAgent, AgentTool, AgentResponse
from app.core.i18n import t

class ChiefOfStaffAgent(BaseAgent):
    """
    Chief of Staff (CoS) Agent.
    
    Acts as the primary interface for the user.
    - Routes complex requests to specialist agents.
    - Handles general conversation.
    - Synthesizes information from multiple sources.
    """
    
    @property
    def name(self) -> str:
        return "ChiefOfStaff"

    @property
    def role_description(self) -> str:
        return "You are the Chief of Staff, a high-level executive assistant. You coordinate other agents (Finance, Calendar, etc.) to fulfill user requests."

    def get_system_prompt(self) -> str:
        return """
        Ты — умный личный секретарь бизнесмена. НЕ просто исполнитель команд, а НАСТОЯЩИЙ помощник!
        
        ТВОЯ ЗАДАЧА: Понять что хочет пользователь и ПРОАКТИВНО предложить помощь.
        
        🧠 ЦЕПОЧКА РАССУЖДЕНИЙ (Chain of Thought):
        Прежде чем вызвать инструмент, ПОДУМАЙ:
        1. Что именно хочет пользователь? (Действие, Вопрос или Приветствие)
        2. Какой агент лучше всего подходит? (finance, calendar, tasks и т.д.)
        3. Хватает ли мне параметров?
        
        💡 ПРИМЕРЫ ПРАВИЛЬНОГО ПОВЕДЕНИЯ (Few-Shot):
        
        User: "Назначь встречу с Асхатом завтра в 5 вечера"
        Thought: Пользователь хочет создать встречу. Нужен агент calendar. Есть имя (Асхат), дата (завтра), время (17:00).
        Action: transfer_to_calendar
        
        User: "Сколько мы потратили на маркетинг?"
        Thought: Речь про расходы и деньги. Это агент finance.
        Action: transfer_to_finance
        
        User: "Позвонить клиенту завтра"
        Thought: Это задача на звонок. Нужен агент tasks.
        Action: transfer_to_tasks
        
        Action: transfer_to_calendar (внутри агента уже вызовется create_meeting_with_followup)

        User: "Напиши текст для возврата долга"
        Thought: Пользователь просит написать/составить текст. Это задача для копирайтинга/идей.
        Action: transfer_to_ideas

        User: "Придумай поздравление для Асхата"
        Thought: Нужно придумать текст/идею.
        Action: transfer_to_ideas
        
        User: "Напиши Ержану привет"
        Thought: Пользователь хочет отправить WhatsApp сообщение. Есть имя (Ержан), сообщение (привет).
        Action: transfer_to_whatsapp
        
        User: "Отправь Асхату сообщение как дела"
        Thought: Запрос на отправку сообщения в WhatsApp.
        Action: transfer_to_whatsapp
        
        ЕСЛИ ПОЛЬЗОВАТЕЛЬ ГОВОРИТ О ПОЕЗДКЕ/ПУТЕШЕСТВИИ:
        Например: "Хочу поехать в Ташкент", "Лечу в Дубай"
        → Ответь ТЕКСТОМ с предложениями...
        
        ПРИВЕТСТВИЯ (ТОЛЬКО ЭТИ СЛОВА ОТДЕЛЬНО):
        "Привет", "Салем", "Здравствуй", "Здравствуйте", "Доброе утро", "Добрый день", "Hi", "Hello"
        → get_proactive_briefing()
        
        НЕ ПРИВЕТСТВИЕ (не вызывай брифинг):
        - "Сегодня о чём говорили?" — это ВОПРОС, ответь из контекста
        - "Что сегодня делать?" — это ВОПРОС, используй transfer_to_tasks или calendar
        - Любой текст с вопросом — это НЕ приветствие!
        
        DND / НЕ БЕСПОКОИТЬ:
        - "Я занят", "Не беспокоить", "Режим тишины на 2 часа"
        → set_dnd_status(enabled=True, duration_hours=...)
        - "Я свободен", "Выключи режим тишины"
        → set_dnd_status(enabled=False)

        ДОСТУПНЫЕ АГЕНТЫ:
        - finance_agent: баланс, доходы, расходы
        - calendar_agent: встречи, расписание
        - tasks_agent: задачи
        - contacts_agent: контакты
        - birthday_agent: дни рождения
        - ideas_agent: идеи
        - debtor_agent: долги, счета
        - knowledge_agent: поиск в интернете
        - travel_agent: путешествия, отели, билеты
        - whatsapp_agent: WhatsApp сообщения (напиши, отправь кому-то)
        
        ВАЖНО! Если пользователь говорит:
        - "напиши [имя] [сообщение]" → transfer_to_whatsapp
        - "отправь [имя] [сообщение]" → transfer_to_whatsapp
        - "скажи [имя] [сообщение]" → transfer_to_whatsapp
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            # Proactive briefing for greetings
            AgentTool(
                name="get_proactive_briefing",
                description="Проактивный брифинг при приветствии. Показывает расписание, задачи, ДР, предложения.",
                parameters={},
                function=self._get_proactive_briefing
            ),
            # DND Status
            AgentTool(
                name="set_dnd_status",
                description="Включить/выключить режим 'Не беспокоить' (DND).",
                parameters={
                    "enabled": {"type": "boolean", "description": "True = включить, False = выключить"},
                    "duration_hours": {"type": "number", "description": "На сколько часов (опционально)"}
                },
                function=self._set_dnd_status
            ),
            # Simple handoffs
            AgentTool(
                name="transfer_to_finance",
                description="Баланс, доходы, расходы (простые запросы).",
                parameters={},
                function=lambda: "handoff:finance_agent"
            ),
            AgentTool(
                name="transfer_to_calendar",
                description="Встречи, расписание (простые запросы).",
                parameters={},
                function=lambda: "handoff:calendar_agent"
            ),
            AgentTool(
                name="transfer_to_tasks",
                description="Задачи (простые запросы).",
                parameters={},
                function=lambda: "handoff:tasks_agent"
            ),
            AgentTool(
                name="transfer_to_contacts",
                description="Контакты (простые запросы).",
                parameters={},
                function=lambda: "handoff:contacts_agent"
            ),
            AgentTool(
                name="transfer_to_birthday",
                description="Дни рождения (простые запросы).",
                parameters={},
                function=lambda: "handoff:birthday_agent"
            ),
            AgentTool(
                name="transfer_to_ideas",
                description="Идеи (простые запросы).",
                parameters={},
                function=lambda: "handoff:ideas_agent"
            ),
            AgentTool(
                name="transfer_to_debtor",
                description="Долги, счета (простые запросы).",
                parameters={},
                function=lambda: "handoff:debtor_agent"
            ),
            AgentTool(
                name="transfer_to_knowledge",
                description="Поиск в интернете (простые запросы).",
                parameters={},
                function=lambda: "handoff:knowledge_agent"
            ),
            AgentTool(
                name="transfer_to_travel",
                description="Путешествия, отели, рейсы, курс валют.",
                parameters={},
                function=lambda: "handoff:travel_agent"
            ),
            AgentTool(
                name="transfer_to_whatsapp",
                description="Отправить сообщение кому-то через WhatsApp. ИСПОЛЬЗУЙ когда пользователь говорит 'напиши', 'отправь', 'скажи' + имя.",
                parameters={},
                function=lambda: "handoff:whatsapp_agent"
            ),
            # Universal multi-step orchestration
            AgentTool(
                name="execute_multi_task",
                description="Выполнить НЕСКОЛЬКО действий подряд. Используй для составных запросов с 2+ действиями.",
                parameters={
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Массив шагов. Каждый шаг: 'agent.tool(param1=value1, param2=value2)'"
                    }
                },
                function=self._execute_multi_task
            ),
        ]
    
    async def _get_proactive_briefing(self) -> str:
        """Generate proactive briefing with suggestions."""
        from sqlalchemy import select, extract
        from app.models.meeting import Meeting
        from app.models.task import Task
        from app.models.birthday import Birthday
        
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        
        sections = ["☀️ Доброе утро!\n"]
        
        # Today's meetings
        today_start = now.replace(hour=0, minute=0, second=0)
        today_end = today_start + timedelta(days=1)
        
        meetings_stmt = select(Meeting).where(
            Meeting.tenant_id == self.tenant_id,
            Meeting.start_time >= today_start,
            Meeting.start_time < today_end
        ).order_by(Meeting.start_time).limit(5)
        meetings_result = await self.db.execute(meetings_stmt)
        meetings = meetings_result.scalars().all()
        
        if meetings:
            sections.append("📅 **Сегодня:**")
            for m in meetings:
                time_str = m.start_time.strftime("%H:%M")
                sections.append(f"  • {time_str} — {m.title}")
        else:
            sections.append("📅 Сегодня встреч нет")
        
        # Overdue/due today tasks
        tasks_stmt = select(Task).where(
            Task.tenant_id == self.tenant_id,
            Task.status != "done",
            Task.deadline <= today_end
        ).limit(5)
        tasks_result = await self.db.execute(tasks_stmt)
        tasks = tasks_result.scalars().all()
        
        if tasks:
            sections.append("\n✅ **Задачи на сегодня:**")
            for t in tasks:
                sections.append(f"  • {t.title}")
        
        # Tomorrow's birthdays
        tomorrow_month = tomorrow.month
        tomorrow_day = tomorrow.day
        
        birthdays_stmt = select(Birthday).where(
            Birthday.tenant_id == self.tenant_id,
            extract('month', Birthday.date) == tomorrow_month,
            extract('day', Birthday.date) == tomorrow_day
        ).limit(3)
        birthdays_result = await self.db.execute(birthdays_stmt)
        birthdays = birthdays_result.scalars().all()
        
        if birthdays:
            sections.append("\n🎂 **Завтра день рождения:**")
            for b in birthdays:
                sections.append(f"  • {b.name}")
        
        # === OVERDUE INVOICES ===
        from app.models.invoice import Invoice
        
        overdue_stmt = select(Invoice).where(
            Invoice.tenant_id == self.tenant_id,
            Invoice.status != "paid",
            Invoice.due_date < now
        ).limit(3)
        overdue_result = await self.db.execute(overdue_stmt)
        overdue_invoices = overdue_result.scalars().all()
        
        if overdue_invoices:
            total = sum(float(inv.amount) for inv in overdue_invoices)
            sections.append(f"\n⚠️ **Просроченные долги ({total:,.0f} ₸):**")
            for inv in overdue_invoices:
                days = (now.date() - inv.due_date.date()).days if inv.due_date else 0
                sections.append(f"  • {inv.debtor_name}: {float(inv.amount):,.0f} ₸ ({days} дней)")
        
        # === NEGLECTED CONTACTS ===
        from app.models.contact import Contact
        from sqlalchemy import func
        
        contacts_stmt = select(Contact).where(Contact.tenant_id == self.tenant_id).limit(10)
        contacts_result = await self.db.execute(contacts_stmt)
        contacts = contacts_result.scalars().all()
        
        neglected = []
        cutoff = now - timedelta(days=14)
        for c in contacts:
            meeting_stmt = select(func.max(Meeting.start_time)).where(
                Meeting.tenant_id == self.tenant_id,
                Meeting.contact_id == c.id
            )
            meeting_result = await self.db.execute(meeting_stmt)
            last = meeting_result.scalar()
            if not last or last < cutoff:
                neglected.append(c.name)
        
        if neglected:
            sections.append(f"\n💡 **Давно не связывались ({len(neglected)}):**")
            for name in neglected[:3]:
                sections.append(f"  • {name}")
        
        # Add helpful suggestion
        sections.append("\n🤖 Чем могу помочь?")
        
        return "\n".join(sections)
    
    async def _execute_multi_task(self, steps = None) -> str:
        """Execute multiple steps across different agents."""
        if not steps:
            return "❌ Не указаны шаги для выполнения"
        
        # Convert RepeatedComposite (protobuf) to Python list
        steps_list = list(steps)
        
        # Return special command for Runtime
        import json
        return f"MULTI_TASK:{json.dumps(steps_list)}"
    
    async def _set_dnd_status(self, enabled: bool = True, duration_hours: float = 0) -> str:
        """Enable or disable Do Not Disturb mode."""
        from app.models.user import User
        
        # Get active user (try both user_id first, then default to first user of tenant)
        target_user_id = self.user_id
        
        if not target_user_id:
            # Fallback to finding first admin/owner
            result = await self.db.execute(select(User).where(User.tenant_id == self.tenant_id).limit(1))
            user = result.scalars().first()
        else:
            user = await self.db.get(User, target_user_id)
            
        if not user:
            return "❌ Ошибка: Пользователь не найден для установки статуса."
            
        user.dnd_enabled = enabled
        
        if enabled and duration_hours > 0:
            user.dnd_until = datetime.now() + timedelta(hours=duration_hours)
            msg = f"🌙 Режим 'Не беспокоить' включен на {duration_hours} ч. (до {user.dnd_until.strftime('%H:%M')})."
        elif enabled:
            user.dnd_until = None # Indefinitely
            msg = "🌙 Режим 'Не беспокоить' включен (бессрочно). Скажите 'Я свободен', чтобы отключить."
        else:
            user.dnd_until = None
            msg = "☀️ Режим 'Не беспокоить' выключен. Вы снова онлайн!"
            
        await self.db.commit()
        return msg


