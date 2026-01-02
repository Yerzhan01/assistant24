from __future__ import annotations
"""Autonomous Debt Collector service."""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import google.generativeai as genai
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.invoice import Invoice, InvoiceStatus, ReminderStatus
from app.models.contact import Contact
from app.models.tenant import Tenant
from app.services.whatsapp_bot import WhatsAppBotService

logger = logging.getLogger(__name__)


# AI prompt for generating polite reminder message
REMINDER_MESSAGE_PROMPT_RU = """
Сгенерируй вежливое напоминание об оплате. Тон дружелюбный но деловой.

Данные:
- Имя должника: {debtor_name}
- Сумма: {amount} {currency}
- Описание: {description}
- Номер договора: {contract_number}
- Дней просрочено: {days_overdue}
- Номер напоминания: {reminder_number}

Правила:
- Если это первое напоминание — очень мягко и вежливо
- Если второе — чуть настойчивее, упомяни срок
- Если третье+ — серьёзно, упомяни возможные последствия
- Максимум 3-4 предложения
- Не используй "уважаемый" — пиши по имени
- Заканчивай фразой типа "Спасибо за понимание!"

Верни ТОЛЬКО текст сообщения, без кавычек.
"""

REMINDER_MESSAGE_PROMPT_KZ = """
Төлем туралы сыпайы еске салу жаса. Достық, бірақ іскери үн.

Деректер:
- Борышкер аты: {debtor_name}
- Сома: {amount} {currency}
- Сипаттама: {description}
- Шарт нөмірі: {contract_number}
- Мерзімі өткен күндер: {days_overdue}
- Еске салу нөмірі: {reminder_number}

Ережелер:
- Егер бірінші еске салу болса — өте жұмсақ
- Егер екінші болса — мерзімді атап өт
- Егер үшінші+ болса — салдарды атап өт
- Максимум 3-4 сөйлем
- "Құрметті" қолданба, атын жаз

Тек хабарлама мәтінін қайтар.
"""


class DebtCollectorService:
    """
    Autonomous debt collection service.
    - Tracks overdue invoices
    - Generates polite reminder messages
    - Sends notifications to owner for approval
    - Sends reminders to debtors upon approval
    """
    
    def __init__(
        self,
        db: AsyncSession,
        whatsapp:Optional[ WhatsAppBotService ] = None,
        api_key:Optional[ str ] = None,
        language: str = "ru"
    ):
        self.db = db
        self.whatsapp = whatsapp or WhatsAppBotService()
        self.api_key = api_key or settings.gemini_api_key
        self.language = language
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None
    
    async def check_overdue_invoices(self, tenant_id: UUID) -> List[Dict[str, Any]]:
        """
        Check for overdue invoices and prepare reminder messages.
        Returns list of invoices needing attention.
        """
        now = datetime.now()
        
        # Find overdue unpaid invoices
        stmt = select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_([
                    InvoiceStatus.SENT.value,
                    InvoiceStatus.OVERDUE.value
                ]),
                Invoice.due_date < now,
                Invoice.message_approved == False
            )
        ).order_by(Invoice.due_date)
        
        result = await self.db.execute(stmt)
        invoices = result.scalars().all()
        
        actions_needed = []
        
        for invoice in invoices:
            # Update status
            invoice.update_reminder_status()
            
            # Check if we should send reminder (min 2 days between reminders)
            should_remind = True
            if invoice.last_reminder_sent:
                days_since = (now - invoice.last_reminder_sent).days
                should_remind = days_since >= 2
            
            if should_remind:
                # Generate message if not already prepared
                if not invoice.prepared_message:
                    message = await self._generate_reminder_message(invoice)
                    invoice.prepared_message = message
                
                actions_needed.append({
                    "invoice_id": str(invoice.id),
                    "debtor_name": invoice.debtor_name,
                    "amount": float(invoice.amount),
                    "currency": invoice.currency,
                    "days_overdue": invoice.days_overdue,
                    "reminder_count": invoice.reminder_count,
                    "prepared_message": invoice.prepared_message,
                    "debtor_phone": invoice.debtor_phone
                })
        
        await self.db.flush()
        return actions_needed
    
    async def _generate_reminder_message(self, invoice: Invoice) -> str:
        """Generate polite reminder message using AI."""
        if not self.model:
            return self._fallback_message(invoice)
        
        prompt_template = REMINDER_MESSAGE_PROMPT_KZ if self.language == "kz" else REMINDER_MESSAGE_PROMPT_RU
        
        prompt = prompt_template.format(
            debtor_name=invoice.debtor_name,
            amount=f"{invoice.amount:,.0f}",
            currency=invoice.currency,
            description=invoice.description,
            contract_number=invoice.contract_number or "—",
            days_overdue=invoice.days_overdue,
            reminder_number=invoice.reminder_count + 1
        )
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to generate reminder: {e}")
            return self._fallback_message(invoice)
    
    def _fallback_message(self, invoice: Invoice) -> str:
        """Fallback message without AI."""
        if self.language == "kz":
            return f"{invoice.debtor_name}, сәлем! {invoice.description} бойынша {invoice.amount:,.0f} {invoice.currency} төлемді еске саламыз. Рахмет!"
        else:
            return f"{invoice.debtor_name}, добрый день! Напоминаю про оплату: {invoice.description} на сумму {invoice.amount:,.0f} {invoice.currency}. Спасибо!"
    
    async def approve_and_send_reminder(
        self,
        invoice_id: UUID,
        tenant: Tenant,
        custom_message:Optional[ str ] = None
    ) -> Dict[str, Any]:
        """
        Approve and send reminder to debtor.
        Called when owner approves the prepared message.
        """
        invoice = await self.db.get(Invoice, invoice_id)
        if not invoice or invoice.tenant_id != tenant.id:
            return {"status": "error", "message": "Invoice not found"}
        
        # Use custom message or prepared message
        message = custom_message or invoice.prepared_message
        if not message:
            return {"status": "error", "message": "No message to send"}
        
        # Get phone number
        phone = invoice.debtor_phone
        if not phone and invoice.contact_id:
            contact = await self.db.get(Contact, invoice.contact_id)
            if contact:
                phone = contact.phone
        
        if not phone:
            return {"status": "error", "message": "No phone number for debtor"}
        
        # Send via WhatsApp
        if tenant.greenapi_instance_id and tenant.greenapi_token:
            await self.whatsapp.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                phone,
                message
            )
        else:
            return {"status": "error", "message": "WhatsApp not configured"}
        
        # Update invoice
        invoice.message_approved = True
        invoice.reminder_count += 1
        invoice.last_reminder_sent = datetime.now()
        invoice.next_reminder_date = datetime.now() + timedelta(days=3)
        invoice.prepared_message = None  # Clear for next reminder
        
        await self.db.flush()
        
        return {
            "status": "success",
            "message": f"Reminder sent to {invoice.debtor_name}",
            "reminder_number": invoice.reminder_count
        }
    
    async def get_owner_notification(
        self,
        tenant_id: UUID,
        overdue_invoices: List[dict]
    ) -> str:
        """Generate notification message for owner about overdue invoices."""
        if not overdue_invoices:
            return ""
        
        if self.language == "kz":
            lines = ["⚠️ Мерзімі өткен төлемдер:"]
            for inv in overdue_invoices[:5]:  # Max 5 in notification
                lines.append(f"• {inv['debtor_name']}: {inv['amount']:,.0f} {inv['currency']} ({inv['days_overdue']} күн)")
            lines.append("\nМен сыпайы еске салу дайындадым. Жіберейін бе?")
        else:
            lines = ["⚠️ Просроченные оплаты:"]
            for inv in overdue_invoices[:5]:
                lines.append(f"• {inv['debtor_name']}: {inv['amount']:,.0f} {inv['currency']} ({inv['days_overdue']} дн.)")
            lines.append("\nЯ подготовил вежливые напоминания. Отправить?")
        
        return "\n".join(lines)
    
    async def get_due_soon_invoices(self, tenant_id: UUID, days: int = 3) -> List[Invoice]:
        """Get invoices due within N days."""
        now = datetime.now()
        due_date = now + timedelta(days=days)
        
        stmt = select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.status == InvoiceStatus.SENT.value,
                Invoice.due_date > now,
                Invoice.due_date <= due_date
            )
        ).order_by(Invoice.due_date)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_summary(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get debt collection summary for tenant."""
        # Overdue
        stmt = select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.status == InvoiceStatus.OVERDUE.value
            )
        )
        result = await self.db.execute(stmt)
        overdue = list(result.scalars().all())
        
        # Due soon
        due_soon = await self.get_due_soon_invoices(tenant_id)
        
        # Paid this month
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        stmt = select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.status == InvoiceStatus.PAID.value,
                Invoice.paid_date >= month_start
            )
        )
        result = await self.db.execute(stmt)
        paid = list(result.scalars().all())
        
        return {
            "overdue_count": len(overdue),
            "overdue_amount": sum(float(i.amount) for i in overdue),
            "due_soon_count": len(due_soon),
            "due_soon_amount": sum(float(i.amount) for i in due_soon),
            "paid_this_month": len(paid),
            "collected_amount": sum(float(i.amount) for i in paid)
        }
