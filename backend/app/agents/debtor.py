from __future__ import annotations
from typing import List
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.agents.base import BaseAgent, AgentTool
from sqlalchemy import select
from app.models.invoice import Invoice


class DebtorAgent(BaseAgent):
    """Debtor Agent. Manages invoices and debts."""
    
    @property
    def name(self) -> str:
        return "DebtorAgent"

    @property
    def role_description(self) -> str:
        return "You are the Debtor Specialist. You manage invoices and debts."

    def get_system_prompt(self) -> str:
        return f"""
        Ты — Агент Долгов цифрового секретаря.
        
        Ты умеешь:
        - Показать все счета (get_all_invoices)
        - Показать неоплаченные (get_unpaid_invoices)
        - Создать новый счёт/долг (create_invoice)
        - Отметить как оплачено (mark_paid)
        
        ВАЖНО: Если пользователь говорит "Арман должен 5000" — вызови create_invoice!
        
        Язык: {self.language}
        """

    def get_tools(self) -> List[AgentTool]:
        return [
            AgentTool(
                name="get_all_invoices",
                description="Получить все счета.",
                parameters={},
                function=self._get_all_invoices
            ),
            AgentTool(
                name="get_unpaid_invoices",
                description="Получить неоплаченные счета.",
                parameters={},
                function=self._get_unpaid_invoices
            ),
            AgentTool(
                name="get_overdue_invoices",
                description="Получить просроченные счета с рекомендациями.",
                parameters={},
                function=self._get_overdue_invoices
            ),
            AgentTool(
                name="create_invoice",
                description="Создать счёт/записать долг. Параметры: counterparty (кто должен), amount (сумма), description.",
                parameters={
                    "counterparty": {"type": "string", "description": "Имя должника"},
                    "amount": {"type": "number", "description": "Сумма долга"},
                    "description": {"type": "string", "description": "Описание"}
                },
                function=self._create_invoice
            ),
            AgentTool(
                name="mark_paid",
                description="Отметить счёт как оплаченный по имени контрагента.",
                parameters={
                    "counterparty": {"type": "string", "description": "Имя контрагента"}
                },
                function=self._mark_paid
            ),
        ]
        
    async def _get_all_invoices(self) -> str:
        stmt = select(Invoice).where(Invoice.tenant_id == self.tenant_id).limit(10)
        result = await self.db.execute(stmt)
        invoices = result.scalars().all()
        
        if invoices:
            lines = ["📄 Счета:"]
            for inv in invoices:
                status_emoji = "✅" if inv.status == "paid" else "⏳"
                lines.append(f"  {status_emoji} {inv.debtor_name}: {float(inv.amount):,.0f} KZT")
            return "\n".join(lines)
        return "📄 Счетов нет"
    
    async def _get_unpaid_invoices(self) -> str:
        stmt = select(Invoice).where(
            Invoice.tenant_id == self.tenant_id,
            Invoice.status != "paid"
        ).limit(10)
        result = await self.db.execute(stmt)
        invoices = result.scalars().all()
        
        if invoices:
            total = sum(float(inv.amount) for inv in invoices)
            lines = [f"⏳ Неоплаченные счета (всего: {total:,.0f} KZT):"]
            for inv in invoices:
                lines.append(f"  • {inv.debtor_name}: {float(inv.amount):,.0f} KZT")
            return "\n".join(lines)
        return "✅ Неоплаченных счетов нет"
    
    async def _create_invoice(self, counterparty: str = "", amount: float = 0, description: str = "") -> str:
        if not counterparty:
            return "❌ Укажите имя контрагента/должника"
        if amount <= 0:
            return "❌ Укажите сумму"
        
        now = datetime.now()
        invoice = Invoice(
            tenant_id=self.tenant_id,
            debtor_name=counterparty,
            amount=Decimal(str(amount)),
            description=description or "Долг",
            status="sent",
            issue_date=now,
            due_date=now + timedelta(days=30)
        )
        self.db.add(invoice)
        await self.db.commit()
        
        return f"✅ Записан долг: {counterparty} — {amount:,.0f} KZT"
    
    async def _mark_paid(self, counterparty: str = "") -> str:
        if not counterparty:
            return "❌ Укажите имя контрагента"
        
        stmt = select(Invoice).where(
            Invoice.tenant_id == self.tenant_id,
            Invoice.debtor_name.ilike(f"%{counterparty}%"),
            Invoice.status != "paid"
        ).limit(1)
        result = await self.db.execute(stmt)
        invoice = result.scalar_one_or_none()
        
        if invoice:
            invoice.status = "paid"
            invoice.paid_date = datetime.now()
            await self.db.commit()
            return f"✅ Счёт оплачен: {invoice.debtor_name} — {float(invoice.amount):,.0f} KZT"
        return f"❌ Неоплаченный счёт от '{counterparty}' не найден"
    
    async def _get_overdue_invoices(self) -> str:
        """Get overdue invoices with smart recommendations."""
        now = datetime.now()
        
        stmt = select(Invoice).where(
            Invoice.tenant_id == self.tenant_id,
            Invoice.status != "paid",
            Invoice.due_date < now
        ).order_by(Invoice.due_date).limit(10)
        
        result = await self.db.execute(stmt)
        invoices = result.scalars().all()
        
        if not invoices:
            return "✅ Просроченных долгов нет!"
        
        total = sum(float(inv.amount) for inv in invoices)
        lines = [f"⚠️ Просроченные долги (всего: {total:,.0f} ₸):\n"]
        
        for inv in invoices:
            days_overdue = (now.date() - inv.due_date.date()).days if inv.due_date else 0
            urgency = "🔴" if days_overdue > 30 else "🟡" if days_overdue > 14 else "🟠"
            
            lines.append(f"{urgency} {inv.debtor_name}: {float(inv.amount):,.0f} ₸")
            lines.append(f"   📅 Просрочено {days_overdue} дней")
            
            if days_overdue > 30:
                lines.append(f"   💡 Срочно позвонить!")
            elif days_overdue > 14:
                lines.append(f"   💡 Напомнить о долге")
        
        return "\n".join(lines)


