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

    class Config:
        from_attributes = True

@router.get("", response_model=List[InvoiceResponse])
async def list_invoices(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Invoice)
        .where(Invoice.tenant_id == tenant.id)
        .order_by(Invoice.created_at.desc())
    )
    return result.scalars().all()

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
