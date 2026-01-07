from __future__ import annotations
"""Finance module for income/expense tracking."""
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.finance import FinanceRecord
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class FinanceModule(BaseModule):
    """
    Finance module handles income and expense tracking.
    Supports: create, list, delete, balance, report
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
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process finance intent."""
        try:
            action = intent_data.get("action", "create").lower()
            
            handlers = {
                "list": self._list_records,
                "show": self._list_records,
                "history": self._list_records,
                "create": self._create_record,
                "add": self._create_record,
                "delete": self._delete_record,
                "remove": self._delete_record,
                "balance": self._get_balance,
                "report": self._get_report,
                "summary": self._get_report,
                "stats": self._get_report,
            }
            
            handler = handlers.get(action, self._create_record)
            return await handler(intent_data, tenant_id, user_id, language)
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(f"Finance processing failed: {e}")
            return ModuleResponse(
                success=False,
                message=t("errors.invalid_data", language)
            )

    async def _list_records(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID, 
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """List recent finance records."""
        limit = intent_data.get("limit", 10)
        record_type = intent_data.get("type")  # income/expense or None for all
        
        query = select(FinanceRecord).where(
            FinanceRecord.tenant_id == tenant_id
        ).order_by(FinanceRecord.record_date.desc()).limit(limit)
        
        if record_type:
            query = query.where(FinanceRecord.type == record_type)
        
        result = await self.db.execute(query)
        records = result.scalars().all()
        
        if not records:
            msg = "Тіркелген операциялар жоқ." if language == "kz" else "Нет записанных операций."
            return ModuleResponse(success=True, message=msg)
        
        # Format list
        lines = []
        for r in records:
            icon = "📈" if r.type == "income" else "📉"
            amount_str = f"{r.amount:,.0f}".replace(",", " ")
            date_str = r.record_date.strftime("%d.%m")
            cat = r.counterparty or r.category or ""
            lines.append(f"{icon} {date_str}: {amount_str} ₸ — {cat}")
        
        header = "Соңғы операциялар:" if language == "kz" else "Последние операции:"
        message = header + "\n" + "\n".join(lines)
        
        return ModuleResponse(
            success=True,
            message=message,
            data={"records": [{"id": str(r.id), "type": r.type, "amount": str(r.amount)} for r in records]}
        )

    async def _get_balance(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID, 
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Get current balance (income - expenses)."""
        # Sum income
        income_query = select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            and_(
                FinanceRecord.tenant_id == tenant_id,
                FinanceRecord.type == "income"
            )
        )
        income_result = await self.db.execute(income_query)
        total_income = income_result.scalar() or Decimal(0)
        
        # Sum expenses
        expense_query = select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            and_(
                FinanceRecord.tenant_id == tenant_id,
                FinanceRecord.type == "expense"
            )
        )
        expense_result = await self.db.execute(expense_query)
        total_expense = expense_result.scalar() or Decimal(0)
        
        balance = total_income - total_expense
        
        income_str = f"{total_income:,.0f}".replace(",", " ")
        expense_str = f"{total_expense:,.0f}".replace(",", " ")
        balance_str = f"{balance:,.0f}".replace(",", " ")
        
        if language == "kz":
            message = f"💰 Баланс: {balance_str} ₸\n📈 Кіріс: {income_str} ₸\n📉 Шығыс: {expense_str} ₸"
        else:
            message = f"💰 Баланс: {balance_str} ₸\n📈 Доходы: {income_str} ₸\n📉 Расходы: {expense_str} ₸"
        
        return ModuleResponse(
            success=True,
            message=message,
            data={"balance": str(balance), "income": str(total_income), "expense": str(total_expense)}
        )

    async def _get_report(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID, 
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Get financial report for a period."""
        period = intent_data.get("period", "month").lower()
        
        today = date.today()
        if period in ["week", "неделя", "апта"]:
            start_date = today - timedelta(days=7)
            period_name = "аптаға" if language == "kz" else "неделю"
        elif period in ["month", "месяц", "ай"]:
            start_date = today - timedelta(days=30)
            period_name = "айға" if language == "kz" else "месяц"
        elif period in ["year", "год", "жыл"]:
            start_date = today - timedelta(days=365)
            period_name = "жылға" if language == "kz" else "год"
        else:
            start_date = today - timedelta(days=30)
            period_name = "айға" if language == "kz" else "месяц"
        
        # Get records for period
        query = select(FinanceRecord).where(
            and_(
                FinanceRecord.tenant_id == tenant_id,
                FinanceRecord.record_date >= start_date
            )
        )
        result = await self.db.execute(query)
        records = result.scalars().all()
        
        # Calculate totals
        total_income = sum(r.amount for r in records if r.type == "income")
        total_expense = sum(r.amount for r in records if r.type == "expense")
        balance = total_income - total_expense
        
        # Group by category
        expense_by_cat: Dict[str, Decimal] = {}
        for r in records:
            if r.type == "expense":
                cat = r.category or "другое"
                expense_by_cat[cat] = expense_by_cat.get(cat, Decimal(0)) + r.amount
        
        # Format message
        income_str = f"{total_income:,.0f}".replace(",", " ")
        expense_str = f"{total_expense:,.0f}".replace(",", " ")
        balance_str = f"{balance:,.0f}".replace(",", " ")
        
        if language == "kz":
            message = f"📊 Есеп ({period_name}):\n\n📈 Кіріс: {income_str} ₸\n📉 Шығыс: {expense_str} ₸\n💰 Айырма: {balance_str} ₸"
        else:
            message = f"📊 Отчёт за {period_name}:\n\n📈 Доходы: {income_str} ₸\n📉 Расходы: {expense_str} ₸\n�� Разница: {balance_str} ₸"
        
        # Add top expense categories
        if expense_by_cat:
            sorted_cats = sorted(expense_by_cat.items(), key=lambda x: x[1], reverse=True)[:5]
            cat_header = "\n\n🏷️ Негізгі шығындар:" if language == "kz" else "\n\n🏷️ Основные расходы:"
            message += cat_header
            for cat, amount in sorted_cats:
                amt_str = f"{amount:,.0f}".replace(",", " ")
                message += f"\n• {cat}: {amt_str} ₸"
        
        return ModuleResponse(
            success=True,
            message=message,
            data={"income": str(total_income), "expense": str(total_expense), "balance": str(balance)}
        )

    async def _delete_record(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID, 
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Delete a finance record."""
        record_id = intent_data.get("record_id") or intent_data.get("id")
        
        if not record_id:
            # Delete the last record
            query = select(FinanceRecord).where(
                FinanceRecord.tenant_id == tenant_id
            ).order_by(FinanceRecord.created_at.desc()).limit(1)
            result = await self.db.execute(query)
            record = result.scalar_one_or_none()
        else:
            try:
                from uuid import UUID as UUIDType
                record = await self.db.get(FinanceRecord, UUIDType(record_id))
            except:
                record = None
        
        if not record or record.tenant_id != tenant_id:
            msg = "Жазба табылмады." if language == "kz" else "Запись не найдена."
            return ModuleResponse(success=False, message=msg)
        
        amount_str = f"{record.amount:,.0f}".replace(",", " ")
        await self.db.delete(record)
        await self.db.flush()
        
        if language == "kz":
            message = f"🗑️ Жазба өшірілді: {amount_str} ₸ ({record.type})"
        else:
            type_name = "доход" if record.type == "income" else "расход"
            message = f"🗑️ Удалена запись: {amount_str} ₸ ({type_name})"
        
        return ModuleResponse(success=True, message=message)

    async def _create_record(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID, 
        user_id: Optional[UUID],
        language: str
    ) -> ModuleResponse:
        """Create a new finance record (income/expense)."""
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
            return ModuleResponse(success=False, message=msg)

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
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
Қаржылық операцияларды басқару: кірістер мен шығыстар.

Шығару керек:
- action: "create", "list", "delete", "balance", "report"
- type: "income" (кіріс) немесе "expense" (шығыс)
- amount: сома (тек сан)
- category: санат (жалақы, жоба, такси, тамақ, кеңсе, т.б.)
- counterparty: кімнен/кімге (атау)
- period: "week", "month", "year" (есеп үшін)

Мысалдар:
- "Асқаттан 50000 алдым" → {"action": "create", "type": "income", "amount": 50000, "counterparty": "Асқат"}
- "Такси 2000 тг" → {"action": "create", "type": "expense", "amount": 2000, "category": "такси"}
- "Менің балансым қанша?" → {"action": "balance"}
- "Апталық есеп" → {"action": "report", "period": "week"}
- "Соңғы операциялар" → {"action": "list"}
- "Соңғы жазбаны өшір" → {"action": "delete"}
"""
        else:
            return """
Управление финансами: доходы и расходы.

Извлекай:
- action: "create", "list", "delete", "balance", "report"
- type: "income" (доход) или "expense" (расход)
- amount: сумма (только число)
- category: категория (зарплата, проект, такси, еда, офис, и т.д.)
- counterparty: от кого/кому (имя или название)
- period: "week", "month", "year" (для отчёта)

Примеры:
- "Получил 50000 от Асхата" → {"action": "create", "type": "income", "amount": 50000, "counterparty": "Асхат"}
- "Такси 2000 тг" → {"action": "create", "type": "expense", "amount": 2000, "category": "такси"}
- "Какой у меня баланс?" → {"action": "balance"}
- "Отчёт за неделю" → {"action": "report", "period": "week"}
- "Покажи историю" → {"action": "list"}
- "Удали последнюю запись" → {"action": "delete"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "получил", "заплатил", "потратил", "доход", "расход",
            "зарплата", "деньги", "тенге", "тг", "₸",
            "баланс", "отчёт", "история", "финансы",
            "алдым", "төледім", "жұмсадым", "кіріс", "шығыс",
            "баланс", "есеп", "қаржы"
        ]
