"""API routes for Ideas management."""
from __future__ import annotations

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db
from app.models.tenant import Tenant
from sqlalchemy import select, desc
from app.models.idea import Idea, IdeaPriority, IdeaStatus

router = APIRouter(prefix="/api/v1", tags=["ideas"])

from app.models.idea import Idea, IdeaPriority, IdeaStatus

@router.get("/ideas")
async def list_ideas(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all ideas."""
    query = select(Idea).where(Idea.tenant_id == tenant.id)
    query = query.order_by(desc(Idea.created_at))
    
    result = await db.execute(query)
    ideas = result.scalars().all()
    
    return {"ideas": [
        {
            "id": str(i.id),
            "title": i.title,
            "description": i.description,
            "category": i.category,
            "priority": i.priority,
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else ""
        }
        for i in ideas
    ]}

class IdeaCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "business"
    priority: str = "medium"

@router.post("/ideas", status_code=201)
async def create_idea(
    data: IdeaCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    idea = Idea(
        tenant_id=tenant.id,
        title=data.title,
        description=data.description,
        category=data.category,
        priority=data.priority,
        status=IdeaStatus.NEW.value
    )
    
    db.add(idea)
    await db.commit()
    await db.refresh(idea)
    
    return {"id": str(idea.id), "status": "created"}

@router.delete("/ideas/{idea_id}", status_code=204)
async def delete_idea(
    idea_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    try:
        i_uuid = uuid.UUID(idea_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    query = select(Idea).where(
        Idea.id == i_uuid,
        Idea.tenant_id == tenant.id
    )
    result = await db.execute(query)
    idea = result.scalar_one_or_none()
    
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    await db.delete(idea)
    await db.commit()
