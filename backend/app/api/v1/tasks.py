"""API routes for Tasks management."""
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
from app.models.task import Task, TaskStatus, TaskPriority

router = APIRouter(prefix="/api/v1", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None
    assignee_id: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    assignee_id: Optional[str] = None


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all tasks for tenant."""
    query = select(Task).where(Task.tenant_id == tenant.id)
    
    if status and status != "all":
        query = query.where(Task.status == status)
        
    query = query.order_by(desc(Task.created_at))
    
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {"tasks": [
        {
            "id": str(t.id),
            "title": t.title,
            "description": t.description or "",
            "priority": t.priority,
            "status": t.status,
            "due_date": t.deadline.isoformat() if t.deadline else None,
            "assignee_id": str(t.assignee_id) if t.assignee_id else None,
            "created_at": t.created_at.isoformat() if t.created_at else ""
        }
        for t in tasks
    ]}


@router.post("/tasks", status_code=201)
async def create_task(
    data: TaskCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task."""
    task = Task(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        status=TaskStatus.NEW.value,
        deadline=datetime.fromisoformat(data.due_date) if data.due_date else None,
        assignee_id=uuid.UUID(data.assignee_id) if data.assignee_id else None
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description or "",
        "priority": task.priority,
        "status": task.status,
        "due_date": task.deadline.isoformat() if task.deadline else None,
        "created_at": task.created_at.isoformat() if task.created_at else ""
    }


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    data: TaskUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update a task."""
    task = await db.get(Task, uuid.UUID(task_id))
    if not task or task.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.priority is not None:
        task.priority = data.priority
    if data.status is not None:
        task.status = data.status
        if data.status == "done":
            task.completed_at = datetime.now()
    if data.due_date is not None:
        task.deadline = datetime.fromisoformat(data.due_date) if data.due_date else None
    if data.assignee_id is not None:
        task.assignee_id = uuid.UUID(data.assignee_id) if data.assignee_id else None
    
    await db.commit()
    await db.refresh(task)
    
    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "priority": task.priority
    }


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Delete a task."""
    task = await db.get(Task, uuid.UUID(task_id))
    if not task or task.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.delete(task)
    await db.commit()
    return None
