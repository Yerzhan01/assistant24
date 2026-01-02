from __future__ import annotations
"""Debtor module for debt/invoice management via AI chat."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import pytz

from app.models.invoice import Invoice, InvoiceStatus
from app.models.contact import Contact
from app.modules.base import BaseModule, ModuleInfo, ModuleResponse


class DebtorModule(BaseModule):
    """
    Debtor module handles recording debts/invoices through AI chat.
    """
    
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
        """Process debt recording intent."""
        try:
            debtor_name = intent_data.get("debtor_name")
            amount = intent_data.get("amount")
            
            if not debtor_name or not amount:
                return ModuleResponse(
                    success=False,
                    message="Не удалось распознать имя должника или сумму." if language != "kz" else "Борышкердің аты немесе сомасы анықталмады."
                )

            # Try to find existing contact
            result = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.name.ilike(f"%{debtor_name}%")
                )
            )
            contact = result.scalars().first()
            
            # Create invoice
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
            
            amount_fmt = f"{invoice.amount:,.0f} {invoice.currency}"
            
            if language == "kz":
                message = f"✅ Қарыз тіркелді:\n👤 {invoice.debtor_name}\n💰 {amount_fmt}\n📅 Мерзімі: {invoice.due_date.strftime('%d.%m.%Y')}"
            else:
                message = f"✅ Долг записан:\n👤 {invoice.debtor_name}\n💰 {amount_fmt}\n📅 Срок: {invoice.due_date.strftime('%d.%m.%Y')}"
            
            return ModuleResponse(
                success=True,
                message=message,
                data={
                    "id": str(invoice.id),
                    "debtor": invoice.debtor_name,
                    "amount": float(invoice.amount)
                }
            )
            
        except Exception as e:
            return ModuleResponse(
                success=False,
                message=f"Ошибка сохранения долга: {str(e)}"
            )
    
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
            
        return now + timedelta(days=7) # Default 1 week

    def get_ai_instructions(self, language: str = "ru") -> str:
        if language == "kz":
            return """
Қарыздар мен шоттарды басқару.

Шығару керек:
- debtor_name: борышкердің аты (адам немесе компания)
- amount: сомасы (сан)
- currency: валюта (KZT, USD, т.б., әдепкі KZT)
- description: сипаттамасы (не үшін)
- relative_date: мерзімі ("ертең", "бір аптадан кейін")

Мысалдар:
- "Арман 5000 теңге қарыз алды" → {"debtor_name": "Арман", "amount": 5000, "description": "Қарыз"}
- "ТОО СтройГрупп шот выставить 150000 түскі асқа" → {"debtor_name": "ТОО СтройГрупп", "amount": 150000, "description": "Түскі ас"}
"""
        else:
            return """
Учет долгов и выставление счетов.

Извлекай:
- debtor_name: имя должника или название компании
- amount: сумма (число)
- currency: валюта (KZT, USD, etc, default KZT)
- description: описание (за что)
- relative_date: срок ("завтра", "через неделю", "через месяц")

Примеры:
- "Запиши долг 5000 тенге Арман обед" → {"debtor_name": "Арман", "amount": 5000, "description": "обед"}
- "Выставь счет компании Рога и Копыта на 100000 за услуги" → {"debtor_name": "Рога и Копыта", "amount": 100000, "description": "услуги"}
- "Напомни Саше вернуть 2000 завтра" → {"debtor_name": "Саша", "amount": 2000, "relative_date": "завтра"}
"""

    def get_intent_keywords(self) -> List[str]:
        return [
            "долг", "дебиторка", "қарыз", "вернуть", "счет", "invoice", "debt",
            "запиши долг", "выставь счет"
        ]
