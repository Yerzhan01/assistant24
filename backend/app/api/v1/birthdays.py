"""API routes for Birthdays management."""
from __future__ import annotations

from typing import List, Optional
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.api.deps import get_current_tenant, get_db
from app.models.tenant import Tenant
from app.models.birthday import Birthday

router = APIRouter(prefix="/api/v1", tags=["birthdays"])

@router.get("/birthdays")
async def list_birthdays(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all birthdays."""
    query = select(Birthday).where(Birthday.tenant_id == tenant.id)
    query = query.order_by(Birthday.date.asc())
    
    result = await db.execute(query)
    birthdays = result.scalars().all()
    
    return {"birthdays": [
        {
            "id": str(b.id),
            "name": b.name,
            "date": b.date.isoformat(),
            "phone": b.phone,
            "notes": b.notes,
            "reminder_days": b.reminder_days,
            "created_at": b.created_at.isoformat() if b.created_at else ""
        }
        for b in birthdays
    ]}

class BirthdayCreate(BaseModel):
    name: str
    date: str  # YYYY-MM-DD
    phone: Optional[str] = None
    notes: Optional[str] = None
    reminder_days: Optional[int] = 3

@router.post("/birthdays", status_code=201)
async def create_birthday(
    data: BirthdayCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    try:
        birth_date = date.fromisoformat(data.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    birthday = Birthday(
        tenant_id=tenant.id,
        name=data.name,
        date=birth_date,
        phone=data.phone,
        notes=data.notes,
        reminder_days=data.reminder_days or 3
    )
    
    db.add(birthday)
    await db.commit()
    await db.refresh(birthday)
    
    return {"id": str(birthday.id), "status": "created"}

@router.delete("/birthdays/{birthday_id}", status_code=204)
async def delete_birthday(
    birthday_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    try:
        b_uuid = uuid.UUID(birthday_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    query = select(Birthday).where(
        Birthday.id == b_uuid,
        Birthday.tenant_id == tenant.id
    )
    result = await db.execute(query)
    birthday = result.scalar_one_or_none()
    
    if not birthday:
        raise HTTPException(status_code=404, detail="Birthday not found")
        
    await db.delete(birthday)
    await db.commit()
