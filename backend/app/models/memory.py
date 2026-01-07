from __future__ import annotations
"""Memory model for RAG system - PostgreSQL compatible with UUID types."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4, UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.contact import Contact


class MemoryType(str, Enum):
    """Types of memories that can be stored."""
    MESSAGE = "message"
    MEETING = "meeting"
    TASK = "task"
    CONTRACT = "contract"
    NOTE = "note"
    IDEA = "idea"
    AGREEMENT = "agreement"
    FINANCE = "finance"


class Memory(Base):
    """
    Memory model for storing records.
    PostgreSQL compatible with UUID types.
    """
    __tablename__ = "memories"
    
    # Primary key - UUID
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Tenant ownership - UUID
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Optional user association - UUID
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Optional contact association - UUID
    contact_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Content type for filtering
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=MemoryType.MESSAGE.value,
        index=True
    )
    
    # Original content text
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # Summary/title for quick display
    summary: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    # Source of the memory
    source: Mapped[str] = mapped_column(
        String(50),
        default="whatsapp"
    )
    
    # Reference to original record (keeping as String since it's flexible)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50))
    reference_id: Mapped[Optional[str]] = mapped_column(String(36))
    
    # Metadata for additional context
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="memories")
    user: Mapped[Optional["User"]] = relationship()
    contact: Mapped[Optional["Contact"]] = relationship()
    
    def __repr__(self) -> str:
        return f"<Memory {self.content_type}: {self.summary or self.content[:50]}...>"
