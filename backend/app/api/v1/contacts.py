"""API routes for Contacts management."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db
from app.models.tenant import Tenant
from app.models.contact import Contact

router = APIRouter(prefix="/api/v1", tags=["contacts"])


class ContactCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    notes: Optional[str] = None


class ContactResponse(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


@router.get("/contacts")
async def list_contacts(
    search: Optional[str] = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all contacts for tenant."""
    query = select(Contact).where(Contact.tenant_id == tenant.id)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Contact.name.ilike(search_term),
                Contact.phone.ilike(search_term),
                Contact.company.ilike(search_term)
            )
        )
        
    query = query.order_by(Contact.name)
    
    result = await db.execute(query)
    contacts = result.scalars().all()
    
    return {"contacts": [
        {
            "id": str(c.id),
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "company": c.company,
            "position": c.position,
            "notes": c.notes,
            "is_favorite": c.is_favorite if hasattr(c, "is_favorite") else False,
            "created_at": c.created_at.isoformat() if c.created_at else ""
        }
        for c in contacts
    ]}


@router.post("/contacts", status_code=201)
async def create_contact(
    data: ContactCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Create a new contact."""
    # Check if exists by phone
    if data.phone:
        existing = await db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant.id,
                Contact.phone == data.phone
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Contact with this phone already exists")

    contact = Contact(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name=data.name,
        phone=data.phone,
        email=data.email,
        company=data.company,
        position=data.position,
        notes=data.notes
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    return {
        "id": str(contact.id),
        "name": contact.name,
        "phone": contact.phone,
        "email": contact.email,
        "company": contact.company,
        "position": contact.position,
        "notes": contact.notes,
        "created_at": contact.created_at.isoformat() if contact.created_at else ""
    }


@router.patch("/contacts/{contact_id}")
async def update_contact(
    contact_id: str,
    data: ContactUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update a contact."""
    contact = await db.get(Contact, uuid.UUID(contact_id))
    if not contact or contact.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    if data.name is not None:
        contact.name = data.name
    if data.phone is not None:
        contact.phone = data.phone
    if data.email is not None:
        contact.email = data.email
    if data.company is not None:
        contact.company = data.company
    if data.position is not None:
        contact.position = data.position
    if data.notes is not None:
        contact.notes = data.notes
    
    await db.commit()
    await db.refresh(contact)
    
    return {
        "id": str(contact.id),
        "name": contact.name,
        "phone": contact.phone,
        "email": contact.email,
        "company": contact.company,
        "position": contact.position,
        "notes": contact.notes
    }


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Delete a contact."""
    contact = await db.get(Contact, uuid.UUID(contact_id))
    if not contact or contact.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    await db.delete(contact)
    await db.commit()
    return None
