"""API routes for Contracts management."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db
from app.models.tenant import Tenant
from app.models.contract import Contract

router = APIRouter(prefix="/api/v1", tags=["contracts"])


class ContractCreate(BaseModel):
    company_name: str
    contract_type: str = "услуги"
    amount: Optional[float] = None
    currency: str = "KZT"
    status: str = "pending_esf"
    contract_date: date
    deadline: Optional[date] = None
    esf_number: Optional[str] = None
    esf_date: Optional[date] = None
    notes: Optional[str] = None


class ContractUpdate(BaseModel):
    company_name: Optional[str] = None
    contract_type: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    contract_date: Optional[date] = None
    deadline: Optional[date] = None
    esf_number: Optional[str] = None
    esf_date: Optional[date] = None
    notes: Optional[str] = None


@router.get("/contracts")
async def list_contracts(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all contracts for tenant."""
    query = select(Contract).where(Contract.tenant_id == tenant.id)
    query = query.order_by(desc(Contract.created_at))
    
    result = await db.execute(query)
    contracts = result.scalars().all()
    
    return {"contracts": [
        {
            "id": str(c.id),
            "title": f"Договор с {c.company_name} ({c.contract_type})", # Frontend expects title
            "counterparty": c.company_name,
            "amount": float(c.amount) if c.amount is not None else 0,
            "currency": c.currency,
            "start_date": c.contract_date.isoformat(),
            "end_date": c.deadline.isoformat() if c.deadline else None,
            "status": "active" if c.status == "esf_issued" else "draft", # Map status for now
            "description": c.notes,
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
        company_name=data.company_name,
        contract_type=data.contract_type,
        amount=Decimal(str(data.amount)) if data.amount is not None else None,
        currency=data.currency,
        status=data.status,
        contract_date=data.contract_date,
        deadline=data.deadline,
        esf_number=data.esf_number,
        esf_date=data.esf_date,
        notes=data.notes
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    
    return {
        "id": str(contract.id),
        "company_name": contract.company_name,
        "status": contract.status
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
    
    if data.company_name is not None:
        contract.company_name = data.company_name
    if data.contract_type is not None:
        contract.contract_type = data.contract_type
    if data.amount is not None:
        contract.amount = Decimal(str(data.amount))
    if data.currency is not None:
        contract.currency = data.currency
    if data.status is not None:
        contract.status = data.status
    if data.contract_date is not None:
        contract.contract_date = data.contract_date
    if data.deadline is not None:
        contract.deadline = data.deadline
    if data.esf_number is not None:
        contract.esf_number = data.esf_number
    if data.esf_date is not None:
        contract.esf_date = data.esf_date
    if data.notes is not None:
        contract.notes = data.notes
    
    await db.commit()
    await db.refresh(contract)
    
    return {
        "id": str(contract.id),
        "company_name": contract.company_name,
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
