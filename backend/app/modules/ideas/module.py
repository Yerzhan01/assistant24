from __future__ import annotations
"""Ideas module for business ideas bank."""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.idea import Idea
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class IdeasModule(BaseModule):
    """Ideas module handles business ideas with priorities and categories."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="ideas",
            name_ru="Идеи",
            name_kz="Идеялар",
            description_ru="Банк идей с приоритетами",
            description_kz="Басымдықтары бар идеялар банкі",
            icon="💡"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process idea intent."""
        try:
            action = intent_data.get("action", "create").lower()
            
            handlers = {
                "list": self._list_ideas,
                "show": self._list_ideas,
                "all": self._list_ideas,
                "create": self._create_idea,
                "add": self._create_idea,
                "delete": self._delete_idea,
                "remove": self._delete_idea,
                "stats": self._get_stats,
            }
            
            handler = handlers.get(action, self._create_idea)
            return await handler(intent_data, tenant_id, user_id, language)
            
        except Exception as e:
            return ModuleResponse(success=False, message=f"Ошибка: {str(e)}")
    
    async def _list_ideas(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """List all ideas."""
        result = await self.db.execute(
            select(Idea)
            .where(Idea.tenant_id == tenant_id)
            .order_by(Idea.created_at.desc())
            .limit(20)
        )
        ideas = result.scalars().all()
        
        if not ideas:
            if language == "kz":
                return ModuleResponse(success=True, message="💡 Идеялар тізімі бос.")
            return ModuleResponse(success=True, message="💡 Список идей пуст.")
        
        priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        
        if language == "kz":
            message = f"💡 Идеялар ({len(ideas)}):"
        else:
            message = f"💡 Идеи ({len(ideas)}):"
        
        for idea in ideas:
            p_icon = priority_icons.get(idea.priority, "⬜")
            title = idea.title[:50] + "..." if len(idea.title) > 50 else idea.title
            message += f"\n{p_icon} {title}"
        
        return ModuleResponse(success=True, message=message)
    
    async def _create_idea(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Create a new idea."""
        content = intent_data.get("content") or intent_data.get("title", "")
        
        if not content:
            if language == "kz":
                return ModuleResponse(success=False, message="Идея мазмұнын көрсетіңіз.")
            return ModuleResponse(success=False, message="Укажите содержание идеи.")
        
        category = intent_data.get("category", "business")
        priority = intent_data.get("priority", "medium")
        
        if priority not in ["high", "medium", "low"]:
            priority = "medium"
        
        idea = Idea(
            tenant_id=tenant_id,
            # user_id not in model
            title=content,
            category=category,
            priority=priority,
            status="new"
        )
        
        self.db.add(idea)
        await self.db.flush()
        
        priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        p_icon = priority_icons.get(priority, "⬜")
        
        if language == "kz":
            message = f"💡 Идея сақталды:\n{p_icon} {content}"
        else:
            message = f"💡 Идея сохранена:\n{p_icon} {content}"
        
        return ModuleResponse(success=True, message=message)
    
    async def _delete_idea(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Delete an idea."""
        content = intent_data.get("content") or intent_data.get("title", "")
        
        if not content:
            if language == "kz":
                return ModuleResponse(success=False, message="Қай идеяны жою керек?")
            return ModuleResponse(success=False, message="Какую идею удалить?")
        
        result = await self.db.execute(
            select(Idea).where(
                Idea.tenant_id == tenant_id,
                Idea.title.ilike(f"%{content}%")
            ).limit(1)
        )
        idea = result.scalar_one_or_none()
        
        if not idea:
            if language == "kz":
                return ModuleResponse(success=False, message=f"'{content}' идеясы табылмады.")
            return ModuleResponse(success=False, message=f"Идея '{content}' не найдена.")
        
        title = idea.title
        await self.db.delete(idea)
        await self.db.flush()
        
        if language == "kz":
            return ModuleResponse(success=True, message=f"🗑️ Идея жойылды: {title[:50]}")
        return ModuleResponse(success=True, message=f"🗑️ Идея удалена: {title[:50]}")
    
    async def _get_stats(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Get ideas statistics."""
        total_result = await self.db.execute(
            select(func.count(Idea.id)).where(Idea.tenant_id == tenant_id)
        )
        total = total_result.scalar_one_or_none() or 0
        
        high_result = await self.db.execute(
            select(func.count(Idea.id)).where(
                Idea.tenant_id == tenant_id,
                Idea.priority == "high"
            )
        )
        high = high_result.scalar_one_or_none() or 0
        
        if language == "kz":
            message = f"💡 Идеялар статистикасы:\n📋 Барлығы: {total}\n🔴 Маңызды: {high}"
        else:
            message = f"💡 Статистика идей:\n📋 Всего: {total}\n🔴 Важных: {high}"
        
        return ModuleResponse(success=True, message=message)
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
💡 ИДЕЯЛАР МОДУЛІ

Әрекеттер (action):
- "list" — барлық идеяларды көрсету
- "create" — жаңа идея қосу
- "delete" — идеяны жою
- "stats" — статистика

Мысалдар:
- "Менің идеяларым" → {"action": "list"}
- "Идеялар тізімі" → {"action": "list"}
- "Идея: Instagram жарнама" → {"action": "create", "content": "Instagram жарнама", "priority": "high"}
- "Идеяны жой: жарнама" → {"action": "delete", "content": "жарнама"}
"""
        else:
            return """
💡 МОДУЛЬ ИДЕЙ

Действия (action):
- "list" — показать все идеи
- "create" — добавить идею
- "delete" — удалить идею
- "stats" — статистика

Примеры запросов → JSON:
- "Мои идеи" → {"action": "list"}
- "Покажи идеи" → {"action": "list"}
- "Список идей" → {"action": "list"}
- "Идея: запустить рекламу в Instagram" → {"action": "create", "content": "Запустить рекламу в Instagram", "priority": "high"}
- "Пришла мысль сделать приложение" → {"action": "create", "content": "Сделать приложение"}
- "Удали идею про рекламу" → {"action": "delete", "content": "рекламу"}
- "Сколько у меня идей?" → {"action": "stats"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "идея", "идеи", "мысль", "инсайт", "мои идеи", "список идей",
            "идея", "идеялар", "ой", "пікір", "менің идеяларым"
        ]
