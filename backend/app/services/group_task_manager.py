from __future__ import annotations
"""Group Task Manager - AI service for extracting tasks from group messages."""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import google.generativeai as genai
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.group_chat import GroupChat
from app.models.task import Task, TaskStatus
from app.models.contact import Contact
from app.models.user import User

logger = logging.getLogger(__name__)


# AI Prompts for Group Manager
GROUP_PM_PROMPT_RU = """
Ты — AI-менеджер проектов в рабочем чате WhatsApp.
Твоя цель: извлекать задачи и статусы из переписки команды.

Входящее сообщение от: {sender_name} (Телефон: {sender_phone})
Текст: "{message_text}"

Проанализируй сообщение и верни JSON.

Варианты действий (action):
1. "new_task" — если кто-то поручает задачу другому человеку.
   Пример: "Асхат, подготовь отчет до пятницы" -> assignee: Асхат, task: Отчет, deadline: пятница.
   
2. "status_update" — если кто-то говорит, что сделал или делает что-то.
   Пример: "Я отправил договор клиенту" -> status: done.
   Пример: "Работаю над дизайном" -> status: in_progress.
   
3. "none" — обычный разговор (привет, как дела, шутки, вопросы не про задачи).

Правила:
- Если задача назначена самому себе ("Я сделаю..."), assignee_name = null.
- Если упомянут @номер телефона, используй его как assignee_phone.
- Дедлайн парси относительно сегодняшней даты: {today}.
- Если нет чёткого дедлайна, deadline = null.

Формат ответа (ТОЛЬКО JSON, без markdown):
{{
  "action": "new_task" | "status_update" | "none",
  "confidence": 0.0-1.0,
  "data": {{
     "task_title": "краткое название задачи",
     "task_description": "подробности если есть",
     "assignee_name": "имя человека или null",
     "assignee_phone": "номер телефона или null",
     "status": "done" | "in_progress" | null,
     "deadline": "YYYY-MM-DD" | null,
     "priority": "low" | "medium" | "high" | "urgent"
  }}
}}
"""

GROUP_PM_PROMPT_KZ = """
Сен — WhatsApp жұмыс чатындағы AI жоба менеджері.
Мақсатың: командалық хабарламалардан тапсырмалар мен статустарды анықтау.

Хабарлама жіберуші: {sender_name} (Телефон: {sender_phone})
Мәтін: "{message_text}"

Хабарламаны талда және JSON қайтар.

Әрекет түрлері (action):
1. "new_task" — біреуге тапсырма берілгенде.
2. "status_update" — біреу бірдеңе жасағанын немесе жасап жатқанын айтқанда.
3. "none" — қарапайым әңгіме.

JSON форматы:
{{
  "action": "new_task" | "status_update" | "none",
  "confidence": 0.0-1.0,
  "data": {{
     "task_title": "тапсырма атауы",
     "task_description": "егер болса толық сипаттама",
     "assignee_name": "адам аты немесе null",
     "assignee_phone": "телефон нөмірі немесе null",
     "status": "done" | "in_progress" | null,
     "deadline": "YYYY-MM-DD" | null,
     "priority": "low" | "medium" | "high" | "urgent"
  }}
}}
"""


class GroupTaskManager:
    """
    AI-powered service for extracting and managing tasks from WhatsApp group chats.
    """
    
    # Minimum message length to process (skip "ok", "да", etc.)
    MIN_MESSAGE_LENGTH = 5
    
    # Minimum confidence to create a task
    MIN_CONFIDENCE = 0.6
    
    def __init__(self, db: AsyncSession, api_key:Optional[ str ] = None, language: str = "ru"):
        self.db = db
        self.api_key = api_key or settings.gemini_api_key
        self.language = language
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None
    
    async def process_group_message(
        self,
        tenant_id: UUID,
        group_chat_id: str,
        sender_phone: str,
        sender_name: str,
        message_text: str,
        message_id: str
    ) -> Dict[str, Any]:
        """
        Process a message from a WhatsApp group.
        Returns action taken and response message (if any).
        """
        # Skip short messages
        if len(message_text.strip()) < self.MIN_MESSAGE_LENGTH:
            return {"action": "ignored", "reason": "message_too_short"}
        
        # Get group chat
        group = await self._get_group_chat(tenant_id, group_chat_id)
        if not group or not group.is_active:
            return {"action": "ignored", "reason": "group_not_registered"}
        
        if not group.task_extraction_enabled:
            return {"action": "ignored", "reason": "task_extraction_disabled"}
        
        # Get or create user
        sender_user = await self._get_or_create_user(tenant_id, sender_phone, sender_name)
        
        # Analyze message with AI
        analysis = await self._analyze_message(sender_phone, sender_name, message_text)
        
        if not analysis or analysis.get("action") == "none":
            return {"action": "none", "silent": group.silent_mode}
        
        confidence = analysis.get("confidence", 0)
        if confidence < self.MIN_CONFIDENCE:
            return {"action": "low_confidence", "confidence": confidence}
        
        action = analysis.get("action")
        data = analysis.get("data", {})
        
        if action == "new_task":
            return await self._handle_new_task(
                tenant_id, group, sender_user, message_id, message_text, data
            )
        elif action == "status_update":
            return await self._handle_status_update(
                tenant_id, group, sender_user, data
            )
        
        return {"action": "unknown"}
    
    async def _analyze_message(
        self, 
        sender_phone: str, 
        sender_name: str, 
        message_text: str
    ) ->Optional[ dict ]:
        """Analyze message with AI to extract task information."""
        if not self.model:
            logger.warning("No AI model configured")
            return None
        
        prompt_template = GROUP_PM_PROMPT_KZ if self.language == "kz" else GROUP_PM_PROMPT_RU
        prompt = prompt_template.format(
            sender_name=sender_name,
            sender_phone=sender_phone,
            message_text=message_text,
            today=datetime.now().strftime("%Y-%m-%d")
        )
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean markdown if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            return json.loads(text)
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None
    
    async def _handle_new_task(
        self,
        tenant_id: UUID,
        group: GroupChat,
        creator: User,
        message_id: str,
        message_text: str,
        data: dict
    ) -> Dict[str, Any]:
        """Create a new task from extracted data."""
        task_title = data.get("task_title", "Новая задача")
        task_description = data.get("task_description")
        assignee_name = data.get("assignee_name")
        assignee_phone = data.get("assignee_phone")
        deadline_str = data.get("deadline")
        priority = data.get("priority", "medium")
        
        # Find assignee
        assignee = None
        if assignee_phone:
            assignee = await self._find_user_by_phone(tenant_id, assignee_phone)
        elif assignee_name:
            assignee = await self._find_user_by_name(tenant_id, assignee_name)
            # Also try contacts
            if not assignee:
                contact = await self._find_contact_by_name(tenant_id, assignee_name)
                if contact:
                    assignee = await self._get_or_create_user(
                        tenant_id, contact.phone, contact.name
                    )
        
        # Parse deadline
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str)
            except:
                pass
        
        # Create task
        task = Task(
            tenant_id=tenant_id,
            group_id=group.id,
            creator_id=creator.id,
            assignee_id=assignee.id if assignee else None,
            title=task_title,
            description=task_description,
            status=TaskStatus.NEW.value,
            priority=priority,
            deadline=deadline,
            original_message_id=message_id,
            original_message_text=message_text
        )
        
        self.db.add(task)
        await self.db.flush()
        
        # Build response message
        assignee_mention = f"@{assignee.whatsapp_phone}" if assignee and assignee.whatsapp_phone else (assignee_name or "вам")
        deadline_text = deadline.strftime("%d.%m.%Y") if deadline else "не указан"
        
        if self.language == "kz":
            response_msg = f"✅ Тапсырма жазылды: {task_title}\n📅 Дедлайн: {deadline_text}\n👤 Жауапты: {assignee_mention}"
        else:
            response_msg = f"✅ Задача записана: {task_title}\n📅 Дедлайн: {deadline_text}\n👤 Ответственный: {assignee_mention}"
        
        return {
            "action": "task_created",
            "task_id": str(task.id),
            "response_message": response_msg,
            "reply_to": message_id
        }
    
    async def _handle_status_update(
        self,
        tenant_id: UUID,
        group: GroupChat,
        sender: User,
        data: dict
    ) -> Dict[str, Any]:
        """Update status of an existing task."""
        task_title = data.get("task_title", "").lower()
        new_status = data.get("status", "done")
        
        # Find task assigned to sender with matching title
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.group_id == group.id,
                Task.assignee_id == sender.id,
                Task.status != TaskStatus.DONE.value,
                Task.status != TaskStatus.CANCELLED.value
            )
        ).order_by(Task.created_at.desc())
        
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()
        
        # Find best match by title
        matching_task = None
        for task in tasks:
            if task_title and task_title in task.title.lower():
                matching_task = task
                break
        
        # If no match by title, use most recent task
        if not matching_task and tasks:
            matching_task = tasks[0]
        
        if not matching_task:
            if self.language == "kz":
                return {"action": "no_task_found", "response_message": "⚠️ Сізге тиесілі белсенді тапсырма табылмады."}
            else:
                return {"action": "no_task_found", "response_message": "⚠️ Не нашёл активных задач на тебе."}
        
        # Update status
        if new_status == "done":
            matching_task.mark_done()
        elif new_status == "in_progress":
            matching_task.mark_in_progress()
        
        if self.language == "kz":
            response_msg = f"🔥 Керемет! «{matching_task.title}» тапсырмасы жабылды."
        else:
            response_msg = f"🔥 Круто! Закрыл задачу «{matching_task.title}»."
        
        return {
            "action": "task_updated",
            "task_id": str(matching_task.id),
            "new_status": new_status,
            "response_message": response_msg
        }
    
    async def _get_group_chat(self, tenant_id: UUID, chat_id: str) ->Optional[ GroupChat ]:
        """Get registered group chat."""
        stmt = select(GroupChat).where(
            and_(
                GroupChat.tenant_id == tenant_id,
                GroupChat.whatsapp_chat_id == chat_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_or_create_user(
        self, 
        tenant_id: UUID, 
        phone: str, 
        name: str
    ) -> User:
        """Get or create user by phone."""
        stmt = select(User).where(
            and_(
                User.tenant_id == tenant_id,
                User.whatsapp_phone == phone
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                tenant_id=tenant_id,
                whatsapp_phone=phone,
                name=name,
                role="user"
            )
            self.db.add(user)
            await self.db.flush()
        
        return user
    
    async def _find_user_by_phone(self, tenant_id: UUID, phone: str) ->Optional[ User ]:
        """Find user by phone number."""
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        stmt = select(User).where(
            and_(
                User.tenant_id == tenant_id,
                User.whatsapp_phone == clean_phone
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _find_user_by_name(self, tenant_id: UUID, name: str) ->Optional[ User ]:
        """Find user by name (case-insensitive)."""
        stmt = select(User).where(
            and_(
                User.tenant_id == tenant_id,
                User.name.ilike(f"%{name}%")
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _find_contact_by_name(self, tenant_id: UUID, name: str) ->Optional[ Contact ]:
        """Find contact by name or alias."""
        stmt = select(Contact).where(
            and_(
                Contact.tenant_id == tenant_id,
                or_(
                    Contact.name.ilike(f"%{name}%"),
                    Contact.aliases.any(name)
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_overdue_tasks(self, tenant_id: UUID) -> List[Task]:
        """Get all overdue tasks for reminders."""
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.deadline < datetime.now(),
                Task.status != TaskStatus.DONE.value,
                Task.status != TaskStatus.CANCELLED.value,
                Task.reminder_sent == False
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_tasks_due_soon(
        self, 
        tenant_id: UUID, 
        hours: int = 24
    ) -> List[Task]:
        """Get tasks with upcoming deadlines."""
        now = datetime.now()
        threshold = now + timedelta(hours=hours)
        
        stmt = select(Task).where(
            and_(
                Task.tenant_id == tenant_id,
                Task.deadline >= now,
                Task.deadline <= threshold,
                Task.status != TaskStatus.DONE.value,
                Task.status != TaskStatus.CANCELLED.value
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
