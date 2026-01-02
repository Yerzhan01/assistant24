from __future__ import annotations
"""GroupChat model - WhatsApp group linked to tenant."""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.task import Task


class GroupChat(Base):
    """
    WhatsApp group linked to a business tenant.
    Used for tracking tasks and managing team communication.
    """
    __tablename__ = "group_chats"
    
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
    
    # WhatsApp group ID (format: 123456789-987654321@g.us)
    whatsapp_chat_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Group name
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Description
    description:Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Is this group active for bot processing?
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    
    # Enable AI task extraction from this group
    task_extraction_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    
    # Silent mode - don't reply to non-task messages
    silent_mode: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="group_chats")
    tasks: Mapped[List["Task"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<GroupChat {self.name} ({self.whatsapp_chat_id})>"
