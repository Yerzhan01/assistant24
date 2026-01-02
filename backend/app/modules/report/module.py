from __future__ import annotations
"""Report module for analytics and summaries."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.finance import FinanceRecord
from app.models.meeting import Meeting
from app.models.contract import Contract
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class ReportModule(BaseModule):
    """
    Report module generates analytics and summaries.
    """
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="report",
            name_ru="Отчёты",
            name_kz="Есептер",
            description_ru="Аналитика и сводки",
            description_kz="Талдау және жиынтықтар",
            icon="📊"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id:Optional[ UUID ] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process report request."""
        try:
            report_type = intent_data.get("type", "finance")
            period = intent_data.get("period", "month")
            
            # Calculate date range
            start_date, end_date = self._get_date_range(period, intent_data)
            
            if report_type == "finance":
                return await self._generate_finance_report(
                    tenant_id, start_date, end_date, language
                )
            elif report_type == "meetings":
                return await self._generate_meeting_report(
                    tenant_id, start_date, end_date, language
                )
            elif report_type == "contracts":
                return await self._generate_contract_report(
                    tenant_id, language
                )
            else:
                # Default to finance summary
                return await self._generate_finance_report(
                    tenant_id, start_date, end_date, language
                )
                
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=t("errors.invalid_data", language)
            )
    
    def _get_date_range(self, period: str, data: Dict[str, Any]) -> tuple[date, date]:
        """Calculate date range based on period."""
        today = date.today()
        
        if period == "today":
            return today, today
        elif period == "week":
            start = today - timedelta(days=today.weekday())
            return start, today
        elif period == "month":
            start = today.replace(day=1)
            return start, today
        elif period == "year":
            start = today.replace(month=1, day=1)
            return start, today
        elif period == "custom":
            # Parse custom dates
            start_str = data.get("start_date")
            end_str = data.get("end_date")
            if start_str and end_str:
                return date.fromisoformat(start_str), date.fromisoformat(end_str)
        
        # Default to current month
        return today.replace(day=1), today
    
    async def _generate_finance_report(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        language: str
    ) -> ModuleResponse:
        """Generate financial report."""
        # Get income
        income_stmt = select(func.sum(FinanceRecord.amount)).where(
            and_(
                FinanceRecord.tenant_id == tenant_id,
                FinanceRecord.type == "income",
                FinanceRecord.record_date >= start_date,
                FinanceRecord.record_date <= end_date
            )
        )
        income_result = await self.db.execute(income_stmt)
        total_income = income_result.scalar() or Decimal(0)
        
        # Get expenses
        expense_stmt = select(func.sum(FinanceRecord.amount)).where(
            and_(
                FinanceRecord.tenant_id == tenant_id,
                FinanceRecord.type == "expense",
                FinanceRecord.record_date >= start_date,
                FinanceRecord.record_date <= end_date
            )
        )
        expense_result = await self.db.execute(expense_stmt)
        total_expense = expense_result.scalar() or Decimal(0)
        
        # Get top categories for expenses
        category_stmt = select(
            FinanceRecord.category,
            func.sum(FinanceRecord.amount).label('total')
        ).where(
            and_(
                FinanceRecord.tenant_id == tenant_id,
                FinanceRecord.type == "expense",
                FinanceRecord.record_date >= start_date,
                FinanceRecord.record_date <= end_date
            )
        ).group_by(FinanceRecord.category).order_by(
            func.sum(FinanceRecord.amount).desc()
        ).limit(5)
        
        category_result = await self.db.execute(category_stmt)
        top_categories = category_result.all()
        
        # Calculate balance
        balance = total_income - total_expense
        
        # Format numbers
        def fmt(n: Decimal) -> str:
            return f"{n:,.0f}".replace(",", " ")
        
        # Build message
        period_str = f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}"
        
        if language == "kz":
            message = f"""📊 **Қаржылық есеп**
📅 Кезең: {period_str}

💰 Кіріс: {fmt(total_income)} ₸
💸 Шығыс: {fmt(total_expense)} ₸
📈 Баланс: {fmt(balance)} ₸"""
            
            if top_categories:
                message += "\n\n📋 Негізгі шығындар:"
                for cat, total in top_categories:
                    message += f"\n  • {cat}: {fmt(total)} ₸"
        else:
            message = f"""📊 **Финансовый отчёт**
📅 Период: {period_str}

💰 Доходы: {fmt(total_income)} ₸
💸 Расходы: {fmt(total_expense)} ₸
📈 Баланс: {fmt(balance)} ₸"""
            
            if top_categories:
                message += "\n\n📋 Основные расходы:"
                for cat, total in top_categories:
                    message += f"\n  • {cat}: {fmt(total)} ₸"
        
        return ModuleResponse(
            success=True,
            message=message,
            data={
                "income": str(total_income),
                "expense": str(total_expense),
                "balance": str(balance),
                "period": {"start": str(start_date), "end": str(end_date)}
            }
        )
    
    async def _generate_meeting_report(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        language: str
    ) -> ModuleResponse:
        """Generate meetings report."""
        # Get meetings count
        stmt = select(func.count(Meeting.id)).where(
            and_(
                Meeting.tenant_id == tenant_id,
                func.date(Meeting.start_time) >= start_date,
                func.date(Meeting.start_time) <= end_date
            )
        )
        result = await self.db.execute(stmt)
        total_meetings = result.scalar() or 0
        
        # Get completed meetings
        completed_stmt = select(func.count(Meeting.id)).where(
            and_(
                Meeting.tenant_id == tenant_id,
                func.date(Meeting.start_time) >= start_date,
                func.date(Meeting.start_time) <= end_date,
                Meeting.is_completed == True
            )
        )
        completed_result = await self.db.execute(completed_stmt)
        completed = completed_result.scalar() or 0
        
        # Get upcoming meetings
        upcoming_stmt = select(Meeting).where(
            and_(
                Meeting.tenant_id == tenant_id,
                Meeting.start_time >= datetime.now(),
                Meeting.is_cancelled == False
            )
        ).order_by(Meeting.start_time).limit(5)
        
        upcoming_result = await self.db.execute(upcoming_stmt)
        upcoming = upcoming_result.scalars().all()
        
        period_str = f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}"
        
        if language == "kz":
            message = f"""📅 **Кездесулер есебі**
📆 Кезең: {period_str}

📊 Жалпы кездесулер: {total_meetings}
✅ Аяқталған: {completed}
⏳ Алда: {len(upcoming)}"""
            
            if upcoming:
                message += "\n\n🔜 Жақындағы кездесулер:"
                for m in upcoming:
                    dt = m.start_time.strftime('%d.%m %H:%M')
                    message += f"\n  • {dt} — {m.title}"
        else:
            message = f"""📅 **Отчёт по встречам**
📆 Период: {period_str}

📊 Всего встреч: {total_meetings}
✅ Проведено: {completed}
⏳ Предстоит: {len(upcoming)}"""
            
            if upcoming:
                message += "\n\n🔜 Ближайшие встречи:"
                for m in upcoming:
                    dt = m.start_time.strftime('%d.%m %H:%M')
                    message += f"\n  • {dt} — {m.title}"
        
        return ModuleResponse(
            success=True,
            message=message,
            data={
                "total": total_meetings,
                "completed": completed,
                "upcoming": len(upcoming)
            }
        )
    
    async def _generate_contract_report(
        self,
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Generate contracts status report."""
        # Get contracts by status
        stmt = select(
            Contract.status,
            func.count(Contract.id).label('count'),
            func.sum(Contract.amount).label('total')
        ).where(
            Contract.tenant_id == tenant_id
        ).group_by(Contract.status)
        
        result = await self.db.execute(stmt)
        statuses = result.all()
        
        status_names = {
            "ru": {
                "draft": "Черновик",
                "pending_esf": "Ожидает ЭСФ",
                "esf_issued": "ЭСФ выставлен",
                "completed": "Завершён",
                "cancelled": "Отменён"
            },
            "kz": {
                "draft": "Жоба",
                "pending_esf": "ЭСФ күтілуде",
                "esf_issued": "ЭСФ шығарылды",
                "completed": "Аяқталды",
                "cancelled": "Бас тартылды"
            }
        }
        
        def fmt(n) -> str:
            if n is None:
                return "0"
            return f"{n:,.0f}".replace(",", " ")
        
        if language == "kz":
            message = "📄 **Шарттар есебі**\n\n"
            for status, count, total in statuses:
                name = status_names["kz"].get(status, status)
                message += f"• {name}: {count} шт. ({fmt(total)} ₸)\n"
        else:
            message = "📄 **Отчёт по договорам**\n\n"
            for status, count, total in statuses:
                name = status_names["ru"].get(status, status)
                message += f"• {name}: {count} шт. ({fmt(total)} ₸)\n"
        
        # Get contracts pending ESF
        pending_stmt = select(Contract).where(
            and_(
                Contract.tenant_id == tenant_id,
                Contract.status == "pending_esf"
            )
        ).limit(5)
        
        pending_result = await self.db.execute(pending_stmt)
        pending = pending_result.scalars().all()
        
        if pending:
            if language == "kz":
                message += "\n⚠️ ЭСФ күтілуде:"
            else:
                message += "\n⚠️ Ожидают ЭСФ:"
            for c in pending:
                message += f"\n  • {c.company_name}"
        
        return ModuleResponse(
            success=True,
            message=message,
            data={"statuses": {s: {"count": c, "total": str(t or 0)} for s, c, t in statuses}}
        )
    
    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
Есептер мен талдау сұраныстарын анықтау.

Шығару керек:
- type: есеп түрі ("finance", "meetings", "contracts")
- period: кезең ("today", "week", "month", "year", "custom")
- start_date, end_date: арнайы кезең үшін (YYYY-MM-DD)

Мысалдар:
- "Қыркүйек айындағы есеп" → {"type": "finance", "period": "custom", "start_date": "2024-09-01", "end_date": "2024-09-30"}
- "Осы апта қанша жұмсадым?" → {"type": "finance", "period": "week"}
- "Алдағы кездесулерім" → {"type": "meetings", "period": "week"}
- "Шарттар бойынша статистика" → {"type": "contracts"}
"""
        else:
            return """
Определяй запросы на отчёты и аналитику.

Извлекай:
- type: тип отчёта ("finance", "meetings", "contracts")
- period: период ("today", "week", "month", "year", "custom")
- start_date, end_date: для кастомного периода (YYYY-MM-DD)

Примеры:
- "Отчёт за сентябрь" → {"type": "finance", "period": "custom", "start_date": "2024-09-01", "end_date": "2024-09-30"}
- "Сколько потратил на этой неделе?" → {"type": "finance", "period": "week"}
- "Мои встречи на неделю" → {"type": "meetings", "period": "week"}
- "Статистика по договорам" → {"type": "contracts"}
- "Баланс за месяц" → {"type": "finance", "period": "month"}
"""
    
    def get_intent_keywords(self) -> List[str]:
        return [
            "отчёт", "отчет", "статистика", "сколько", "баланс",
            "итого", "за месяц", "за неделю", "сводка",
            "есеп", "статистика", "қанша", "баланс", "жиынтық"
        ]
