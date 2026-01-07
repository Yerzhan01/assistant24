from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db
from app.models.tenant import Tenant
from app.models.invoice import Invoice, InvoiceStatus
from app.models.contact import Contact

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])

class InvoiceBase(BaseModel):
    debtor_name: str
    amount: float
    currency: str = "KZT"
    description: str
    due_date: datetime
    status: str = "sent"

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    debtor_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None

class InvoiceResponse(InvoiceBase):
    id: UUID
    invoice_number: Optional[str] = None
    created_at: datetime
    days_overdue: int
    paid_amount: float = 0
    remaining_amount: float = 0

    class Config:
        from_attributes = True

@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    from datetime import timezone
    
    result = await db.execute(
        select(Invoice)
        .where(Invoice.tenant_id == tenant.id)
        .order_by(Invoice.created_at.desc())
    )
    invoices = result.scalars().all()
    
    now = datetime.now(timezone.utc)
    
    # Build response manually to compute remaining_amount while session is active
    response = []
    for inv in invoices:
        # Compute days_overdue with timezone awareness
        due = inv.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        days_overdue = max(0, (now - due).days) if inv.status != "paid" else 0
        
        response.append({
            "id": inv.id,
            "debtor_name": inv.debtor_name,
            "amount": float(inv.amount),
            "currency": inv.currency,
            "description": inv.description,
            "due_date": inv.due_date,
            "status": inv.status,
            "invoice_number": inv.invoice_number,
            "created_at": inv.created_at,
            "days_overdue": days_overdue,
            "paid_amount": float(inv.paid_amount or 0),
            "remaining_amount": float(inv.amount) - float(inv.paid_amount or 0)
        })
    return response

@router.post("", response_model=InvoiceResponse)
async def create_invoice(
    invoice_in: InvoiceCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    # Try to link contact
    result = await db.execute(
        select(Contact).where(
            Contact.tenant_id == tenant.id,
            Contact.name.ilike(f"%{invoice_in.debtor_name}%")
        )
    )
    contact = result.scalars().first()
    
    invoice = Invoice(
        **invoice_in.model_dump(),
        tenant_id=tenant.id,
        contact_id=contact.id if contact else None
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice

@router.patch("/{id}", response_model=InvoiceResponse)
async def update_invoice(
    id: UUID,
    invoice_in: InvoiceUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == id,
            Invoice.tenant_id == tenant.id
        )
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    update_data = invoice_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)
    
    if invoice_in.status == "paid" and invoice.status != "paid":
        invoice.mark_paid()
        
    await db.commit()
    await db.refresh(invoice)
    return invoice

@router.delete("/{id}")
async def delete_invoice(
    id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == id,
            Invoice.tenant_id == tenant.id
        )
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    await db.delete(invoice)
    await db.commit()
    return {"success": True}


# ========== Payment History Endpoints ==========

class PaymentCreate(BaseModel):
    amount: float
    note: Optional[str] = None


class PaymentResponse(BaseModel):
    id: UUID
    amount: float
    paid_at: datetime
    note: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/{id}/payments", response_model=PaymentResponse)
async def record_payment(
    id: UUID,
    payment_in: PaymentCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Record a partial or full payment against an invoice."""
    from app.models.payment_history import PaymentHistory
    
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == id,
            Invoice.tenant_id == tenant.id
        )
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Create payment record
    payment = PaymentHistory(
        invoice_id=invoice.id,
        amount=payment_in.amount,
        note=payment_in.note
    )
    db.add(payment)
    
    # Update invoice paid_amount
    invoice.mark_paid(payment_in.amount)
    
    await db.commit()
    await db.refresh(payment)
    return payment


@router.get("/{id}/payments", response_model=List[PaymentResponse])
async def get_payment_history(
    id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get payment history for an invoice."""
    from app.models.payment_history import PaymentHistory
    
    # Verify invoice belongs to tenant
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == id,
            Invoice.tenant_id == tenant.id
        )
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get payments
    result = await db.execute(
        select(PaymentHistory)
        .where(PaymentHistory.invoice_id == id)
        .order_by(PaymentHistory.paid_at.desc())
    )
    return result.scalars().all()

