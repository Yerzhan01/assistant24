from __future__ import annotations
"""Ideas module for business ideas bank."""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.idea import Idea
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class IdeasModule(BaseModule):
    """
    Ideas module handles business ideas with priorities and categories.
    """
    
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
        user_id:Optional[ UUID ] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process idea intent."""
        try:
            content = intent_data.get("content", "")
            category = intent_data.get("category", "business")
            priority = intent_data.get("priority", "medium")
            
            # Normalize priority
            if priority not in ["high", "medium", "low"]:
                priority = "medium"
            
            # Translate category for display
            category_names = {
                "ru": {
                    "business": "бизнес",
                    "marketing": "маркетинг",
                    "product": "продукт",
                    "operations": "операции",
                    "other": "другое"
                },
                "kz": {
                    "business": "бизнес",
                    "marketing": "маркетинг",
                    "product": "өнім",
                    "operations": "операциялар",
                    "other": "басқа"
                }
            }
            
            priority_names = {
                "ru": {"high": "высокий", "medium": "средний", "low": "низкий"},
                "kz": {"high": "жоғары", "medium": "орташа", "low": "төмен"}
            }
            
            # Create idea
            idea = Idea(
                tenant_id=tenant_id,
                user_id=user_id,
                title=content,
                category=category,
                priority=priority,
                status="new"
            )
            
            self.db.add(idea)
            await self.db.flush()
            
            # Format response
            cat_display = category_names.get(language, {}).get(category, category)
            pri_display = priority_names.get(language, {}).get(priority, priority)
            
            message = t(
                "modules.ideas.saved",
                language,
                content=content[:100] + "..." if len(content) > 100 else content,
                category=cat_display,
                priority=pri_display
            )
            
            return ModuleResponse(
                success=True,
                message=message,
                data={
                    "id": str(idea.id),
                    "content": content,
                    "category": category,
                    "priority": priority
                }
            )
            
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=t("errors.invalid_data", language)
            )
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
Бизнес идеяларды анықтау.

Шығару керек:
- content: идея мазмұны
- category: санат (business, marketing, product, operations, other)
- priority: басымдық (high, medium, low) — идеяның маңыздылығына байланысты

Мысалдар:
- "Идея: Instagram-да жарнама іске қосу" → {"content": "Instagram-да жарнама іске қосу", "category": "marketing", "priority": "high"}
- "Жаңа өнім шығару керек" → {"content": "Жаңа өнім шығару керек", "category": "product", "priority": "medium"}
"""
        else:
            return """
Определяй бизнес-идеи.

Извлекай:
- content: содержание идеи (обязательно)
- category: категория (business, marketing, product, operations, other) - по умолчанию "business"
- priority: приоритет (high, medium, low) — по умолчанию "medium"

Примеры:
- "Идея: запустить рекламу в Instagram" → {"content": "Запустить рекламу в Instagram", "category": "marketing", "priority": "high"}
- "Надо сделать мобильное приложение" → {"content": "Сделать мобильное приложение", "category": "product", "priority": "medium"}
- "Хочу открыть новую точку" → {"content": "Открыть новую точку", "category": "business", "priority": "high"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "идея", "нужно", "надо", "хочу", "планирую",
            "сделать", "создать", "запустить",
            "идея", "керек", "жасау", "құру", "бастау"
        ]
