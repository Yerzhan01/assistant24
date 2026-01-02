from __future__ import annotations
"""Finance module for income/expense tracking."""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.finance import FinanceRecord
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class FinanceModule(BaseModule):
    """
    Finance module handles income and expense tracking.
    """
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="finance",
            name_ru="Финансы",
            name_kz="Қаржы",
            description_ru="Учёт доходов и расходов",
            description_kz="Кірістер мен шығыстарды есепке алу",
            icon="💰"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id:Optional[ UUID ] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process finance intent."""
        try:
            record_type = intent_data.get("type", "income")
            amount = Decimal(str(intent_data.get("amount", 0)))
            category = intent_data.get("category", "other")
            counterparty = intent_data.get("counterparty")
            description = intent_data.get("description")
            
            # Parse date or use today
            record_date_str = intent_data.get("date")
            if record_date_str:
                record_date = date.fromisoformat(record_date_str)
            else:
                record_date = date.today()
            
            # Validation: Amount must be positive
            if amount <= 0:
                msg = "Кешіріңіз, соманы көрсетпедіңіз. Қанша теңге?" if language == "kz" else "Укажите сумму операции (например: 50000)."
                return ModuleResponse(
                    success=False,  # Return false to indicate no record was created
                    message=msg
                )

            # Create record
            record = FinanceRecord(
                tenant_id=tenant_id,
                user_id=user_id,
                type=record_type,
                amount=amount,
                currency=intent_data.get("currency", "KZT"),
                category=category,
                counterparty=counterparty,
                description=description,
                record_date=record_date
            )
            
            self.db.add(record)
            await self.db.flush()
            
            # Format response message
            amount_str = f"{amount:,.0f}".replace(",", " ")
            
            if record_type == "income":
                message = t(
                    "modules.finance.income_recorded", 
                    language,
                    amount=amount_str,
                    counterparty=counterparty or category
                )
            else:
                message = t(
                    "modules.finance.expense_recorded", 
                    language,
                    amount=amount_str,
                    category=category
                )
            
            return ModuleResponse(
                success=True,
                message=message,
                data={
                    "id": str(record.id),
                    "type": record_type,
                    "amount": str(amount),
                    "category": category
                }
            )
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(f"Finance processing failed: {e}")
            return ModuleResponse(
                success=False,
                message=t("errors.invalid_data", language)
            )
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
Қаржылық операцияларды анықтау: кірістер мен шығыстар.

Шығару керек:
- type: "income" (кіріс) немесе "expense" (шығыс)
- amount: сома (тек сан)
- category: санат (жалақы, жоба, такси, тамақ, кеңсе, т.б.)
- counterparty: кімнен/кімге (атау)
- description: қосымша сипаттама

Мысалдар:
- "Асқаттан 50000 алдым" → {"type": "income", "amount": 50000, "counterparty": "Асқат"}
- "Такси 2000 тг" → {"type": "expense", "amount": 2000, "category": "такси"}
- "Жалақы 500к" → {"type": "income", "amount": 500000, "category": "жалақы"}
"""
        else:
            return """
Определяй финансовые операции: доходы и расходы.

Извлекай:
- type: "income" (доход) или "expense" (расход)
- amount: сумма (только число)
- category: категория (зарплата, проект, такси, еда, офис, и т.д.)
- counterparty: от кого/кому (имя или название)
- description: дополнительное описание

Примеры:
- "Получил 50000 от Асхата" → {"type": "income", "amount": 50000, "counterparty": "Асхат"}
- "Такси 2000 тг" → {"type": "expense", "amount": 2000, "category": "такси"}
- "Зарплата 500к" → {"type": "income", "amount": 500000, "category": "зарплата"}
- "Заплатил за обед 5000" → {"type": "expense", "amount": 5000, "category": "еда"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "получил", "заплатил", "потратил", "доход", "расход",
            "зарплата", "деньги", "тенге", "тг", "₸",
            "алдым", "төледім", "жұмсадым", "кіріс", "шығыс"
        ]
