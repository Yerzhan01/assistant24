from __future__ import annotations
from typing import List
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.agents.base import BaseAgent, AgentTool
from app.core.i18n import t
from sqlalchemy import select, func
from app.models.finance import FinanceRecord

class FinanceAgent(BaseAgent):
    """
    Finance Agent. Specialized in money matters.
    """
    
    @property
    def name(self) -> str:
        return "FinanceAgent"

    @property
    def role_description(self) -> str:
        return "You are the Finance Specialist. You handle invoices, transactions, and reports."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — Финансовый Агент цифрового секретаря.
        
        ИНСТРУМЕНТЫ:
        - get_balance: показать баланс
        - add_income: записать доход (amount, description)
        - add_expense: записать расход (amount, description)
        
        УМНЫЕ УТОЧНЕНИЯ:
        
        ✅ Если есть сумма → записывай СРАЗУ!
        ❓ Если нет суммы → спроси "Какая сумма?"
        
        Описание — НЕ ОБЯЗАТЕЛЬНО. Если не указано, используй "Доход" или "Расход".
        
        НЕ СПРАШИВАЙ:
        - Категорию (по умолчанию income/expense)
        - Дату (по умолчанию сегодня)
        
        Примеры:
        - "Получил 50000 от Асхата" → add_income(amount=50000, description="от Асхата")
        - "Потратил 10000 на такси" → add_expense(amount=10000, description="на такси")
        - "Доход" → Ответить: "Какая сумма?"
        - "100000 доход" → add_income(amount=100000)
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="get_balance",
                description="Получить текущий баланс и финансовую сводку.",
                parameters={},
                function=self._get_balance
            ),
            AgentTool(
                name="add_income",
                description="Записать доход. Параметры: amount (сумма), description (описание).",
                parameters={
                    "amount": {"type": "number", "description": "Сумма дохода"},
                    "description": {"type": "string", "description": "Описание дохода"}
                },
                function=self._add_income
            ),
            AgentTool(
                name="add_expense",
                description="Записать расход. Параметры: amount (сумма), description (описание).",
                parameters={
                    "amount": {"type": "number", "description": "Сумма расхода"},
                    "description": {"type": "string", "description": "Описание расхода"}
                },
                function=self._add_expense
            ),
            AgentTool(
                name="forecast_cashflow",
                description="Прогноз cash flow на конец месяца.",
                parameters={},
                function=self._forecast_cashflow
            ),
            AgentTool(
                name="analyze_expenses",
                description="Анализ расходов по категориям.",
                parameters={},
                function=self._analyze_expenses
            ),
        ]
        
    async def _get_balance(self) -> str:
        """Get real balance from database with smart trend analysis."""
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
        
        # Get income this month
        income_stmt = select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.tenant_id == self.tenant_id,
            FinanceRecord.type == "income",
            FinanceRecord.record_date >= month_start.date()
        )
        income_result = await self.db.execute(income_stmt)
        income = income_result.scalar() or 0
        
        # Get expenses this month
        expense_stmt = select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.tenant_id == self.tenant_id,
            FinanceRecord.type == "expense",
            FinanceRecord.record_date >= month_start.date()
        )
        expense_result = await self.db.execute(expense_stmt)
        expenses = expense_result.scalar() or 0
        
        # === SMART TREND ANALYSIS ===
        # Get previous month income
        prev_income_stmt = select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.tenant_id == self.tenant_id,
            FinanceRecord.type == "income",
            FinanceRecord.record_date >= prev_month_start.date(),
            FinanceRecord.record_date < month_start.date()
        )
        prev_income_result = await self.db.execute(prev_income_stmt)
        prev_income = float(prev_income_result.scalar() or 0)
        
        # Get previous month expenses
        prev_expense_stmt = select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.tenant_id == self.tenant_id,
            FinanceRecord.type == "expense",
            FinanceRecord.record_date >= prev_month_start.date(),
            FinanceRecord.record_date < month_start.date()
        )
        prev_expense_result = await self.db.execute(prev_expense_stmt)
        prev_expenses = float(prev_expense_result.scalar() or 0)
        
        # Calculate trends
        income_float = float(income)
        expense_float = float(expenses)
        balance = income_float - expense_float
        
        trends = []
        if prev_income > 0:
            income_change = ((income_float - prev_income) / prev_income) * 100
            if abs(income_change) >= 10:
                trend_emoji = "📈" if income_change > 0 else "📉"
                trends.append(f"{trend_emoji} Доход: {income_change:+.0f}% к прошлому месяцу")
        
        if prev_expenses > 0:
            expense_change = ((expense_float - prev_expenses) / prev_expenses) * 100
            if abs(expense_change) >= 10:
                trend_emoji = "⚠️" if expense_change > 20 else "📊"
                trends.append(f"{trend_emoji} Расходы: {expense_change:+.0f}% к прошлому месяцу")
        
        trend_section = ""
        if trends:
            trend_section = "\n\n💡 Тренды:\n" + "\n".join(trends)
        
        return f"""💰 Финансовая сводка за {now.strftime('%B %Y')}:

📈 Доход: +{income_float:,.0f} ₸
📉 Расход: -{expense_float:,.0f} ₸
━━━━━━━━━━━━━━━
💵 Баланс: {balance:,.0f} ₸{trend_section}"""
    
    async def _add_income(self, amount: float = 0, description: str = "") -> str:
        """Record income."""
        if amount <= 0:
            return "❌ Укажите сумму дохода"
        
        record = FinanceRecord(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            type="income",
            amount=Decimal(str(amount)),
            category="income",
            description=description or "Доход",
            record_date=date.today()
        )
        self.db.add(record)
        await self.db.commit()
        
        return f"✅ Записан доход: +{amount:,.0f} KZT ({description or 'Доход'})"
    
    async def _add_expense(self, amount: float = 0, description: str = "") -> str:
        """Record expense."""
        if amount <= 0:
            return "❌ Укажите сумму расхода"
        
        record = FinanceRecord(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            type="expense",
            amount=Decimal(str(amount)),
            category="expense",
            description=description or "Расход",
            record_date=date.today()
        )
        self.db.add(record)
        await self.db.commit()
        
        return f"✅ Записан расход: -{amount:,.0f} KZT ({description or 'Расход'})"
    
    async def _forecast_cashflow(self) -> str:
        """Forecast cash flow to end of month."""
        from calendar import monthrange
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)
        _, days_in_month = monthrange(now.year, now.month)
        days_passed = now.day
        days_left = days_in_month - days_passed
        
        # Current month income
        income_stmt = select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.tenant_id == self.tenant_id,
            FinanceRecord.type == "income",
            FinanceRecord.record_date >= month_start.date()
        )
        income = float((await self.db.execute(income_stmt)).scalar() or 0)
        
        # Current month expenses
        expense_stmt = select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.tenant_id == self.tenant_id,
            FinanceRecord.type == "expense",
            FinanceRecord.record_date >= month_start.date()
        )
        expenses = float((await self.db.execute(expense_stmt)).scalar() or 0)
        
        # Forecast
        daily_income = income / days_passed if days_passed > 0 else 0
        daily_expense = expenses / days_passed if days_passed > 0 else 0
        forecast_income = income + (daily_income * days_left)
        forecast_expense = expenses + (daily_expense * days_left)
        forecast_balance = forecast_income - forecast_expense
        
        warning = ""
        if forecast_balance < 0:
            warning = "\n\n⚠️ **Прогноз отрицательный!**\n💡 Сократите расходы"
        
        return f"""📊 **Прогноз cash flow:**

📅 День {days_passed}/{days_in_month}

**Сейчас:** {income - expenses:,.0f} ₸
**К концу месяца:** ~{forecast_balance:,.0f} ₸{warning}"""
    
    async def _analyze_expenses(self) -> str:
        """Analyze expenses by category."""
        now = datetime.now()
        month_start = now.replace(day=1)
        
        stmt = select(FinanceRecord).where(
            FinanceRecord.tenant_id == self.tenant_id,
            FinanceRecord.type == "expense",
            FinanceRecord.record_date >= month_start.date()
        )
        expenses = (await self.db.execute(stmt)).scalars().all()
        
        if not expenses:
            return "📊 Нет расходов за этот месяц"
        
        # Group by keywords
        categories = {}
        keywords = {"такси": "🚕 Транспорт", "еда": "🍔 Еда", "обед": "🍔 Еда",
                    "зарплата": "💼 Зарплата", "офис": "🏢 Офис", "аренда": "🏢 Офис"}
        
        for exp in expenses:
            desc = (exp.description or "").lower()
            cat = "📦 Прочее"
            for kw, c in keywords.items():
                if kw in desc:
                    cat = c
                    break
            categories[cat] = categories.get(cat, 0) + float(exp.amount)
        
        total = sum(categories.values())
        lines = [f"📊 **Расходы за {now.strftime('%B')}:**\n"]
        for cat, amt in sorted(categories.items(), key=lambda x: -x[1]):
            pct = amt / total * 100 if total else 0
            lines.append(f"{cat}: {amt:,.0f} ₸ ({pct:.0f}%)")
        lines.append(f"\n💰 Всего: {total:,.0f} ₸")
        
        return "\n".join(lines)


