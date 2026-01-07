"""API routes for Ideas, Birthdays, and Contracts management."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db
from app.models.tenant import Tenant
from app.models.idea import Idea
from app.models.birthday import Birthday
from app.models.contract import Contract

router = APIRouter(prefix="/api/v1", tags=["ideas", "birthdays", "contracts"])


# ============== Ideas ==============

class IdeaCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "business"
    priority: str = "medium"


class IdeaUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class IdeaResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    status: str
    created_at: str


@router.get("/ideas")
async def list_ideas(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all ideas for tenant."""
    result = await db.execute(
        select(Idea)
        .where(Idea.tenant_id == tenant.id)
        .order_by(desc(Idea.created_at))
    )
    ideas = result.scalars().all()
    
    return {"ideas": [
        {
            "id": str(i.id),
            "title": i.content,  # content is used as title
            "description": "",
            "category": i.category,
            "priority": i.priority,
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else ""
        }
        for i in ideas
    ]}


@router.post("/ideas", status_code=201)
async def create_idea(
    data: IdeaCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Create a new idea."""
    idea = Idea(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        content=data.title,  # title goes into content
        category=data.category,
        priority=data.priority,
        status="new"
    )
    db.add(idea)
    await db.commit()
    await db.refresh(idea)
    
    return {
        "id": str(idea.id),
        "title": idea.content,
        "category": idea.category,
        "priority": idea.priority,
        "status": idea.status,
        "created_at": idea.created_at.isoformat() if idea.created_at else ""
    }


@router.patch("/ideas/{idea_id}")
async def update_idea(
    idea_id: str,
    data: IdeaUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update an idea."""
    idea = await db.get(Idea, uuid.UUID(idea_id))
    if not idea or idea.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    if data.title is not None:
        idea.content = data.title
    if data.category is not None:
        idea.category = data.category
    if data.priority is not None:
        idea.priority = data.priority
    if data.status is not None:
        idea.status = data.status
    
    await db.commit()
    await db.refresh(idea)
    
    return {
        "id": str(idea.id),
        "title": idea.content,
        "category": idea.category,
        "priority": idea.priority,
        "status": idea.status
    }


@router.delete("/ideas/{idea_id}", status_code=204)
async def delete_idea(
    idea_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Delete an idea."""
    idea = await db.get(Idea, uuid.UUID(idea_id))
    if not idea or idea.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    await db.delete(idea)
    await db.commit()
    return None


# ============== Birthdays ==============

class BirthdayCreate(BaseModel):
    name: str
    date: str
    phone: Optional[str] = None
    notes: Optional[str] = None
    reminder_days: int = 3


class BirthdayUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    reminder_days: Optional[int] = None


@router.get("/birthdays")
async def list_birthdays(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all birthdays for tenant."""
    result = await db.execute(
        select(Birthday)
        .where(Birthday.tenant_id == tenant.id)
        .order_by(Birthday.date)
    )
    birthdays = result.scalars().all()
    
    return {"birthdays": [
        {
            "id": str(b.id),
            "name": b.person_name,
            "date": b.birth_date.isoformat() if b.birth_date else "",
            "phone": b.phone or "",
            "notes": b.notes or "",
            "reminder_days": b.reminder_days_before or 3,
            "created_at": b.created_at.isoformat() if b.created_at else ""
        }
        for b in birthdays
    ]}


@router.post("/birthdays", status_code=201)
async def create_birthday(
    data: BirthdayCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Create a new birthday reminder."""
    birthday = Birthday(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        person_name=data.name,
        birth_date=datetime.fromisoformat(data.date).date() if data.date else None,
        phone=data.phone,
        notes=data.notes,
        reminder_days_before=data.reminder_days
    )
    db.add(birthday)
    await db.commit()
    await db.refresh(birthday)
    
    return {
        "id": str(birthday.id),
        "name": birthday.person_name,
        "date": birthday.birth_date.isoformat() if birthday.birth_date else "",
        "phone": birthday.phone or "",
        "notes": birthday.notes or "",
        "reminder_days": birthday.reminder_days_before or 3,
        "created_at": birthday.created_at.isoformat() if birthday.created_at else ""
    }


@router.patch("/birthdays/{birthday_id}")
async def update_birthday(
    birthday_id: str,
    data: BirthdayUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update a birthday."""
    birthday = await db.get(Birthday, uuid.UUID(birthday_id))
    if not birthday or birthday.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Birthday not found")
    
    if data.name is not None:
        birthday.person_name = data.name
    if data.date is not None:
        birthday.birth_date = datetime.fromisoformat(data.date).date()
    if data.phone is not None:
        birthday.phone = data.phone
    if data.notes is not None:
        birthday.notes = data.notes
    if data.reminder_days is not None:
        birthday.reminder_days_before = data.reminder_days
    
    await db.commit()
    await db.refresh(birthday)
    
    return {
        "id": str(birthday.id),
        "name": birthday.person_name,
        "date": birthday.birth_date.isoformat() if birthday.birth_date else "",
        "phone": birthday.phone or "",
        "notes": birthday.notes or "",
        "reminder_days": birthday.reminder_days_before or 3
    }


@router.delete("/birthdays/{birthday_id}", status_code=204)
async def delete_birthday(
    birthday_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Delete a birthday."""
    birthday = await db.get(Birthday, uuid.UUID(birthday_id))
    if not birthday or birthday.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Birthday not found")
    
    await db.delete(birthday)
    await db.commit()
    return None


# ============== Contracts ==============

class ContractCreate(BaseModel):
    title: str
    counterparty: str
    amount: float = 0
    currency: str = "KZT"
    start_date: str
    end_date: Optional[str] = None
    status: str = "active"
    description: Optional[str] = None


class ContractUpdate(BaseModel):
    title: Optional[str] = None
    counterparty: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


@router.get("/contracts")
async def list_contracts(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all contracts for tenant."""
    result = await db.execute(
        select(Contract)
        .where(Contract.tenant_id == tenant.id)
        .order_by(desc(Contract.created_at))
    )
    contracts = result.scalars().all()
    
    return {"contracts": [
        {
            "id": str(c.id),
            "title": c.title,
            "counterparty": c.counterparty_name or "",
            "amount": float(c.amount) if c.amount else 0,
            "currency": c.currency or "KZT",
            "start_date": c.start_date.isoformat() if c.start_date else "",
            "end_date": c.end_date.isoformat() if c.end_date else "",
            "status": c.status or "active",
            "description": c.description or "",
            "created_at": c.created_at.isoformat() if c.created_at else ""
        }
        for c in contracts
    ]}


@router.post("/contracts", status_code=201)
async def create_contract(
    data: ContractCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Create a new contract."""
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title=data.title,
        counterparty_name=data.counterparty,
        amount=data.amount,
        currency=data.currency,
        start_date=datetime.fromisoformat(data.start_date).date() if data.start_date else None,
        end_date=datetime.fromisoformat(data.end_date).date() if data.end_date else None,
        status=data.status,
        description=data.description
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    
    return {
        "id": str(contract.id),
        "title": contract.title,
        "counterparty": contract.counterparty_name or "",
        "amount": float(contract.amount) if contract.amount else 0,
        "currency": contract.currency or "KZT",
        "start_date": contract.start_date.isoformat() if contract.start_date else "",
        "end_date": contract.end_date.isoformat() if contract.end_date else "",
        "status": contract.status or "active",
        "description": contract.description or "",
        "created_at": contract.created_at.isoformat() if contract.created_at else ""
    }


@router.patch("/contracts/{contract_id}")
async def update_contract(
    contract_id: str,
    data: ContractUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update a contract."""
    contract = await db.get(Contract, uuid.UUID(contract_id))
    if not contract or contract.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if data.title is not None:
        contract.title = data.title
    if data.counterparty is not None:
        contract.counterparty_name = data.counterparty
    if data.amount is not None:
        contract.amount = data.amount
    if data.currency is not None:
        contract.currency = data.currency
    if data.start_date is not None:
        contract.start_date = datetime.fromisoformat(data.start_date).date()
    if data.end_date is not None:
        contract.end_date = datetime.fromisoformat(data.end_date).date()
    if data.status is not None:
        contract.status = data.status
    if data.description is not None:
        contract.description = data.description
    
    await db.commit()
    await db.refresh(contract)
    
    return {
        "id": str(contract.id),
        "title": contract.title,
        "counterparty": contract.counterparty_name or "",
        "amount": float(contract.amount) if contract.amount else 0,
        "status": contract.status
    }


@router.delete("/contracts/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Delete a contract."""
    contract = await db.get(Contract, uuid.UUID(contract_id))
    if not contract or contract.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    await db.delete(contract)
    await db.commit()
    return None
