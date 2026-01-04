from __future__ import annotations
"""Task model - Tasks extracted from group chats or created manually."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.group_chat import GroupChat


class TaskStatus(str, Enum):
    """Task status enum."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    """
    Task model for tracking work items.
    Can be created manually or extracted from WhatsApp group messages.
    """
    __tablename__ = "tasks"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Foreign key to tenant
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Optional: linked group chat (if task came from group)
    group_id:Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("group_chats.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Creator - who assigned the task
    creator_id:Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Assignee - who should complete the task
    assignee_id:Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Task details
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    
    description:Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=TaskStatus.NEW.value,
        index=True
    )
    
    # Priority
    priority: Mapped[str] = mapped_column(
        String(20),
        default=TaskPriority.MEDIUM.value
    )
    

    
    # Original WhatsApp message ID (for reply)
    original_message_id:Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    # Original message text
    original_message_text:Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Reminder settings

    
    # Completion time

    
    # Timestamps

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Reminder flag (Legacy - new system uses TaskReminder table)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="tasks")
    group: Mapped[Optional["GroupChat"]] = relationship(back_populates="tasks")
    creator: Mapped[Optional["User"]] = relationship(
        foreign_keys=[creator_id],
        back_populates="created_tasks"
    )
    assignee: Mapped[Optional["User"]] = relationship(
        foreign_keys=[assignee_id],
        back_populates="assigned_tasks"
    )
    subtasks: Mapped[list["Task"]] = relationship(
        "Task",
        backref="parent", # This creates a 'parent' attribute on the child task
        remote_side=[id] # This tells SQLAlchemy that 'id' on THIS model is the remote side for the 'parent_id' on the related model
    )
    # reminders: Mapped[list["TaskReminder"]] = relationship("TaskReminder", back_populates="task")
    
    def __repr__(self) -> str:
        return f"<Task {self.title[:30]}... ({self.status})>"
    
    def mark_done(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.DONE.value
        self.completed_at = datetime.now()
    
    def mark_in_progress(self) -> None:
        """Mark task as in progress."""
        self.status = TaskStatus.IN_PROGRESS.value
        self.completed_at = None
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.deadline:
            return False
        if self.status == TaskStatus.DONE.value:
            return False
        return datetime.now() > self.deadline

