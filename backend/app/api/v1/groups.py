from __future__ import annotations
"""API routes for group chats, tasks, and contacts management."""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db, get_language
from app.models.group_chat import GroupChat
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.contact import Contact
from app.services.group_task_manager import GroupTaskManager
from app.services.contact_service import ContactService

router = APIRouter(prefix="/api/v1", tags=["groups", "tasks", "contacts"])


# ==================== Schemas ====================

class GroupChatCreate(BaseModel):
    whatsapp_chat_id: str = Field(..., description="WhatsApp group ID (ends with @g.us)")
    name: str = Field(..., max_length=255)
    description:Optional[ str ] = None
    task_extraction_enabled: bool = True
    silent_mode: bool = True


class GroupChatUpdate(BaseModel):
    name:Optional[ str ] = None
    description:Optional[ str ] = None
    is_active:Optional[ bool ] = None
    task_extraction_enabled:Optional[ bool ] = None
    silent_mode:Optional[ bool ] = None


class GroupChatResponse(BaseModel):
    id: UUID
    whatsapp_chat_id: str
    name: str
    description:Optional[ str ]
    is_active: bool
    task_extraction_enabled: bool
    silent_mode: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description:Optional[ str ] = None
    assignee_id:Optional[ UUID ] = None
    deadline:Optional[ datetime ] = None
    priority: str = TaskPriority.MEDIUM.value


class TaskUpdate(BaseModel):
    title:Optional[ str ] = None
    description:Optional[ str ] = None
    status:Optional[ str ] = None
    assignee_id:Optional[ UUID ] = None
    deadline:Optional[ datetime ] = None
    priority:Optional[ str ] = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description:Optional[ str ]
    status: str
    priority: str
    deadline:Optional[ datetime ]
    assignee_id:Optional[ UUID ]
    creator_id:Optional[ UUID ]
    group_id:Optional[ UUID ]
    is_overdue: bool
    created_at: datetime
    completed_at:Optional[ datetime ]

    class Config:
        from_attributes = True


class ContactCreate(BaseModel):
    name: str = Field(..., max_length=255)
    phone: str = Field(..., max_length=20)
    aliases:Optional[ List[str] ] = None
    email:Optional[ str ] = None
    company:Optional[ str ] = None
    position:Optional[ str ] = None
    notes:Optional[ str ] = None


class ContactUpdate(BaseModel):
    name:Optional[ str ] = None
    phone:Optional[ str ] = None
    aliases:Optional[ List[str] ] = None
    email:Optional[ str ] = None
    company:Optional[ str ] = None
    position:Optional[ str ] = None
    notes:Optional[ str ] = None


class ContactResponse(BaseModel):
    id: UUID
    name: str
    phone: str
    aliases:Optional[ List[str] ]
    email:Optional[ str ]
    company:Optional[ str ]
    position:Optional[ str ]
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Group Chat Endpoints ====================

@router.get("/groups", response_model=List[GroupChatResponse])
@router.get("/whatsapp/groups", response_model=List[GroupChatResponse])
async def list_groups(
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all registered WhatsApp groups."""
    stmt = select(GroupChat).where(GroupChat.tenant_id == tenant.id).order_by(GroupChat.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/groups/sync", response_model=List[GroupChatResponse])
@router.post("/whatsapp/groups/sync", response_model=List[GroupChatResponse])
async def sync_whatsapp_groups(
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync all WhatsApp groups from connected account.
    Automatically imports all groups and lets user toggle which to monitor.
    """
    if not tenant.greenapi_instance_id or not tenant.greenapi_token:
        raise HTTPException(status_code=400, detail="WhatsApp not connected")
    
    from app.services.whatsapp_bot import get_whatsapp_service
    
    whatsapp = get_whatsapp_service()
    
    try:
        # Get all chats from WhatsApp
        chats = await whatsapp.get_chats(
            tenant.greenapi_instance_id,
            tenant.greenapi_token
        )
        
        # Filter only groups (end with @g.us)
        groups = [c for c in chats if c.get("id", "").endswith("@g.us")]
        
        imported = []
        for group_data in groups:
            chat_id = group_data.get("id", "")
            name = group_data.get("name", "") or f"Group {chat_id[:8]}"
            
            # Check if already exists
            stmt = select(GroupChat).where(
                and_(
                    GroupChat.tenant_id == tenant.id,
                    GroupChat.whatsapp_chat_id == chat_id
                )
            )
            existing = await db.execute(stmt)
            if existing.scalar_one_or_none():
                continue  # Already imported
            
            # Create new group (disabled by default)
            group = GroupChat(
                tenant_id=tenant.id,
                whatsapp_chat_id=chat_id,
                name=name,
                is_active=False,  # User will enable manually
                task_extraction_enabled=False,
                silent_mode=True
            )
            db.add(group)
            imported.append(group)
        
        await db.commit()
        
        # Return all groups (existing + new)
        stmt = select(GroupChat).where(GroupChat.tenant_id == tenant.id).order_by(GroupChat.name)
        result = await db.execute(stmt)
        return result.scalars().all()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync groups: {str(e)}")


@router.post("/groups", response_model=GroupChatResponse, status_code=201)
@router.post("/whatsapp/groups", response_model=GroupChatResponse, status_code=201)
async def create_group(
    data: GroupChatCreate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Register a WhatsApp group for task extraction."""
    # Check if group already exists
    stmt = select(GroupChat).where(
        and_(
            GroupChat.tenant_id == tenant.id,
            GroupChat.whatsapp_chat_id == data.whatsapp_chat_id
        )
    )
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Group already registered")
    
    group = GroupChat(
        tenant_id=tenant.id,
        **data.model_dump()
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    
    return group


@router.get("/groups/{group_id}", response_model=GroupChatResponse)
async def get_group(
    group_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific group."""
    stmt = select(GroupChat).where(
        and_(GroupChat.id == group_id, GroupChat.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.patch("/groups/{group_id}", response_model=GroupChatResponse)
async def update_group(
    group_id: UUID,
    data: GroupChatUpdate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update a group's settings."""
    stmt = select(GroupChat).where(
        and_(GroupChat.id == group_id, GroupChat.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    
    await db.commit()
    await db.refresh(group)
    return group


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(
    group_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Unregister a group."""
    stmt = select(GroupChat).where(
        and_(GroupChat.id == group_id, GroupChat.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    await db.delete(group)
    await db.commit()


# ==================== Task Endpoints ====================

@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status:Optional[ str ] = Query(None, description="Filter by status"),
    assignee_id:Optional[ UUID ] = Query(None, description="Filter by assignee"),
    group_id:Optional[ UUID ] = Query(None, description="Filter by group"),
    overdue:Optional[ bool ] = Query(None, description="Filter overdue tasks"),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List tasks with optional filters."""
    stmt = select(Task).where(Task.tenant_id == tenant.id)
    
    if status:
        stmt = stmt.where(Task.status == status)
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if group_id:
        stmt = stmt.where(Task.group_id == group_id)
    if overdue is True:
        stmt = stmt.where(
            and_(
                Task.deadline < datetime.now(),
                Task.status != TaskStatus.DONE.value
            )
        )
    
    stmt = stmt.order_by(Task.deadline.asc().nullslast(), Task.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task manually."""
    task = Task(
        tenant_id=tenant.id,
        **data.model_dump()
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific task."""
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update a task."""
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "status" and value == TaskStatus.DONE.value:
            task.mark_done()
        else:
            setattr(task, key, value)
    
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Mark a task as completed."""
    stmt = select(Task).where(
        and_(Task.id == task_id, Task.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.mark_done()
    await db.commit()
    await db.refresh(task)
    return task


# ==================== Contact Endpoints ====================

@router.get("/contacts", response_model=List[ContactResponse])
async def list_contacts(
    search:Optional[ str ] = Query(None, description="Search by name, phone, or company"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List contacts with optional search."""
    service = ContactService(db)
    return await service.list_contacts(tenant.id, search, limit, offset)


@router.post("/contacts", response_model=ContactResponse, status_code=201)
async def create_contact(
    data: ContactCreate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Create a new contact."""
    # Check if phone already exists
    service = ContactService(db)
    existing = await service.find_by_phone(tenant.id, data.phone)
    if existing:
        raise HTTPException(status_code=400, detail="Contact with this phone already exists")
    
    contact = Contact(
        tenant_id=tenant.id,
        source="manual",
        **data.model_dump()
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific contact."""
    stmt = select(Contact).where(
        and_(Contact.id == contact_id, Contact.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    data: ContactUpdate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update a contact."""
    stmt = select(Contact).where(
        and_(Contact.id == contact_id, Contact.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    
    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Delete a contact."""
    stmt = select(Contact).where(
        and_(Contact.id == contact_id, Contact.tenant_id == tenant.id)
    )
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    await db.delete(contact)
    await db.commit()


@router.get("/contacts/find/{name}", response_model=Optional[ContactResponse ])
async def find_contact_by_name(
    name: str,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Find a contact by name or alias (for AI integration)."""
    service = ContactService(db)
    contact = await service.find_by_name(tenant.id, name)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact
