from __future__ import annotations
"""Debtor module for debt/invoice management via AI chat."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import pytz

from app.models.invoice import Invoice, InvoiceStatus
from app.models.contact import Contact
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class DebtorModule(BaseModule):
    """Debtor module handles recording debts/invoices through AI chat."""
    
    def __init__(self, db: AsyncSession, timezone: str = "Asia/Almaty") -> None:
        self.db = db
        self.timezone = pytz.timezone(timezone)
    
    @property
    def info(self) -> ModuleInfo:
        return ModuleInfo(
            module_id="debtor",
            name_ru="Дебиторка",
            name_kz="Дебиторлық қарыз",
            description_ru="Учёт долгов и выставление счетов",
            description_kz="Қарыздарды есепке алу",
            icon="💰"
        )
    
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """Process debt intent."""
        try:
            action = intent_data.get("action", "create").lower()
            
            handlers = {
                "list": self._list_debts,
                "show": self._list_debts,
                "all": self._list_debts,
                "create": self._create_debt,
                "add": self._create_debt,
                "delete": self._delete_debt,
                "remove": self._delete_debt,
                "paid": self._mark_paid,
                "done": self._mark_paid,
                "stats": self._get_stats,
            }
            
            handler = handlers.get(action, self._create_debt)
            return await handler(intent_data, tenant_id, language)
            
        except Exception as e:
            return ModuleResponse(success=False, message=f"Ошибка: {str(e)}")
    
    async def _list_debts(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """List all unpaid debts."""
        result = await self.db.execute(
            select(Invoice)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status != InvoiceStatus.PAID.value
            )
            .order_by(Invoice.due_date.asc())
            .limit(20)
        )
        debts = result.scalars().all()
        
        if not debts:
            if language == "kz":
                return ModuleResponse(success=True, message="💰 Қарыздар жоқ.")
            return ModuleResponse(success=True, message="💰 Долгов нет.")
        
        total = sum(d.amount for d in debts)
        
        if language == "kz":
            message = f"💰 Қарыздар ({len(debts)}), барлығы: {total:,.0f} ₸:"
        else:
            message = f"💰 Должники ({len(debts)}), всего: {total:,.0f} ₸:"
        
        for d in debts:
            due_str = d.due_date.strftime("%d.%m") if d.due_date else ""
            message += f"\n👤 {d.debtor_name} — {d.amount:,.0f} ₸ (до {due_str})"
        
        return ModuleResponse(success=True, message=message)
    
    async def _create_debt(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Create a new debt record."""
        debtor_name = intent_data.get("debtor_name") or intent_data.get("name", "")
        amount = intent_data.get("amount")
        
        if not debtor_name or not amount:
            if language == "kz":
                return ModuleResponse(success=False, message="Борышкердің аты немесе сомасы анықталмады.")
            return ModuleResponse(success=False, message="Укажите имя должника и сумму.")
        
        # Try to find existing contact
        result = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.name.ilike(f"%{debtor_name}%")
            ).limit(1)
        )
        contact = result.scalar_one_or_none()
        
        invoice = Invoice(
            tenant_id=tenant_id,
            contact_id=contact.id if contact else None,
            debtor_name=contact.name if contact else debtor_name,
            description=intent_data.get("description", "Долг"),
            amount=float(amount),
            currency=intent_data.get("currency", "KZT"),
            due_date=self._parse_due_date(intent_data) or datetime.now(self.timezone),
            status=InvoiceStatus.SENT.value
        )
        
        self.db.add(invoice)
        await self.db.flush()
        
        amount_fmt = f"{invoice.amount:,.0f} ₸"
        
        if language == "kz":
            message = f"✅ Қарыз тіркелді:\n👤 {invoice.debtor_name}\n💰 {amount_fmt}\n📅 Мерзімі: {invoice.due_date.strftime('%d.%m.%Y')}"
        else:
            message = f"✅ Долг записан:\n👤 {invoice.debtor_name}\n💰 {amount_fmt}\n📅 Срок: {invoice.due_date.strftime('%d.%m.%Y')}"
        
        return ModuleResponse(success=True, message=message)
    
    async def _mark_paid(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        debtor_name = intent_data.get("debtor_name") or intent_data.get("name", "")
        payment_amount = intent_data.get("amount")
        
        if not debtor_name:
            return ModuleResponse(success=False, message="Кто оплатил?" if language != "kz" else "Кім төледі?")
        
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.debtor_name.ilike(f"%{debtor_name}%"),
                Invoice.status != InvoiceStatus.PAID.value
            ).limit(1)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return ModuleResponse(success=False, message=f"Долг {debtor_name} не найден.")
        
        original_amount = float(invoice.amount)
        name = invoice.debtor_name
        
        if payment_amount is not None and payment_amount > 0:
            payment = float(payment_amount)
            
            if payment >= original_amount:
                invoice.status = InvoiceStatus.PAID.value
                invoice.paid_at = datetime.now(self.timezone)
                await self.db.flush()
                return ModuleResponse(success=True, message=f"Долг {name} полностью погашен: {original_amount:,.0f} тг")
            else:
                remaining = original_amount - payment
                invoice.amount = remaining
                await self.db.flush()
                return ModuleResponse(success=True, message=f"{name} оплатил {payment:,.0f} тг. Остаток: {remaining:,.0f} тг")
        else:
            invoice.status = InvoiceStatus.PAID.value
            invoice.paid_at = datetime.now(self.timezone)
            await self.db.flush()
            return ModuleResponse(success=True, message=f"Долг {name} погашен: {original_amount:,.0f} тг")

    async def _delete_debt(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Delete a debt."""
        debtor_name = intent_data.get("debtor_name") or intent_data.get("name", "")
        
        if not debtor_name:
            if language == "kz":
                return ModuleResponse(success=False, message="Қай қарызды жою керек?")
            return ModuleResponse(success=False, message="Какой долг удалить?")
        
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.debtor_name.ilike(f"%{debtor_name}%")
            ).limit(1)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            if language == "kz":
                return ModuleResponse(success=False, message=f"'{debtor_name}' қарызы табылмады.")
            return ModuleResponse(success=False, message=f"Долг '{debtor_name}' не найден.")
        
        name = invoice.debtor_name
        await self.db.delete(invoice)
        await self.db.flush()
        
        if language == "kz":
            return ModuleResponse(success=True, message=f"🗑️ {name} қарызы жойылды.")
        return ModuleResponse(success=True, message=f"🗑️ Долг {name} удалён.")
    
    async def _get_stats(
        self,
        intent_data: Dict[str, Any],
        tenant_id: UUID,
        language: str
    ) -> ModuleResponse:
        """Get debt statistics."""
        # Unpaid
        unpaid_result = await self.db.execute(
            select(func.sum(Invoice.amount)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.status != InvoiceStatus.PAID.value
            )
        )
        unpaid = unpaid_result.scalar_one_or_none() or 0
        
        # Count
        count_result = await self.db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.status != InvoiceStatus.PAID.value
            )
        )
        count = count_result.scalar_one_or_none() or 0
        
        if language == "kz":
            message = f"💰 Дебиторлық статистика:\n👥 Борышкерлер: {count}\n💵 Жалпы сома: {unpaid:,.0f} ₸"
        else:
            message = f"💰 Статистика долгов:\n👥 Должников: {count}\n💵 Общая сумма: {unpaid:,.0f} ₸"
        
        return ModuleResponse(success=True, message=message)
    
    def _parse_due_date(self, data: Dict[str, Any]) -> Optional[datetime]:
        """Parse due date."""
        from datetime import timedelta
        now = datetime.now(self.timezone)
        
        if "due_date" in data:
            try:
                return datetime.fromisoformat(data["due_date"])
            except:
                pass
        
        relative = data.get("relative_date", "").lower()
        if relative in ["завтра", "tomorrow", "ертең"]:
            return now + timedelta(days=1)
        elif relative in ["через неделю", "бір аптадан кейін"]:
            return now + timedelta(days=7)
        elif relative in ["через месяц", "бір айдан кейін"]:
            return now + timedelta(days=30)
        
        # Try to parse date like "5 февраля"
        import re
        month_map = {
            "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
            "мая": 5, "июня": 6, "июля": 7, "августа": 8,
            "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
        }
        match = re.search(r'(\d+)\s*(\w+)', str(relative))
        if match:
            day = int(match.group(1))
            month_name = match.group(2).lower()
            month = month_map.get(month_name)
            if month:
                year = now.year if month >= now.month else now.year + 1
                try:
                    return datetime(year, month, day, tzinfo=self.timezone)
                except:
                    pass
        
        return now + timedelta(days=7)

    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
💰 ДЕБИТОРЛЫҚ МОДУЛІ

Әрекеттер (action):
- "list" — барлық қарыздарды көрсету
- "create" — жаңа қарыз жазу
- "paid" — қарыз төленді деп белгілеу
- "delete" — қарызды жою
- "stats" — статистика

Мысалдар:
- "Кім маған қарыз?" → {"action": "list"}
- "Қарыздар тізімі" → {"action": "list"}
- "Арман 5000 теңге қарыз" → {"action": "create", "debtor_name": "Арман", "amount": 5000}
- "Арман төледі" → {"action": "paid", "debtor_name": "Арман"}
- "Арман 5000 төледі" → {"action": "paid", "debtor_name": "Арман", "amount": 5000}
"""
        else:
            return """
💰 МОДУЛЬ ДЕБИТОРКИ

Действия (action):
- "list" — показать всех должников
- "create" — записать новый долг
- "paid" — отметить как оплаченный
- "delete" — удалить долг
- "stats" — статистика

Примеры запросов → JSON:
- "Кто мне должен?" → {"action": "list"}
- "Покажи должников" → {"action": "list"}
- "Список долгов" → {"action": "list"}
- "Арман должен 5000 тенге" → {"action": "create", "debtor_name": "Арман", "amount": 5000}
- "Шынгыс должен 500000 до 5 февраля" → {"action": "create", "debtor_name": "Шынгыс", "amount": 500000, "relative_date": "5 февраля"}
- "Арман оплатил" → {"action": "paid", "debtor_name": "Арман"}
- "Арман оплатил 5000" → {"action": "paid", "debtor_name": "Арман", "amount": 5000}
- "Шынгыс вернул долг" → {"action": "paid", "debtor_name": "Шынгыс"}
- "Сколько мне должны?" → {"action": "stats"}
"""

    def get_intent_keywords(self) -> List[str]:
        return [
            "долг", "должен", "должник", "должники", "дебиторка", 
            "кто должен", "кто мне должен", "оплатил", "вернул",
            "қарыз", "борышкер", "кім қарыз"
        ]
