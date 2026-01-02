from __future__ import annotations
"""Idea model - For tracking business ideas."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant

class IdeaPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class IdeaStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    ARCHIVED = "archived"

class Idea(Base):
    """
    Idea model.
    Tracks business ideas, marketing concepts, etc.
    """
    __tablename__ = "ideas"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Tenant
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="other") # business, product, etc

    # Status & Priority
    priority: Mapped[str] = mapped_column(String(20), default=IdeaPriority.MEDIUM.value)
    status: Mapped[str] = mapped_column(String(20), default=IdeaStatus.NEW.value)

    # Metadata
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
    tenant: Mapped["Tenant"] = relationship(back_populates="ideas")

    def __repr__(self) -> str:
        return f"<Idea {self.title}>"
