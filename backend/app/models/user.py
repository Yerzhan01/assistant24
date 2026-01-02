from __future__ import annotations
"""User model - users within a tenant."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.task import Task


class User(Base):
    """
    User represents an individual person interacting with the bot.
    Users belong to a tenant and can have different roles.
    """
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Tenant relationship
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Identity (at least one must be set)
    telegram_id:Mapped[Optional[int]] = mapped_column(BigInteger, index=True)
    whatsapp_phone:Mapped[Optional[str]] = mapped_column(String(20), index=True)
    
    # Profile
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Role within tenant
    role: Mapped[str] = mapped_column(
        String(20), 
        default="user"  # "owner", "admin", "user"
    )
    
    # Preferences
    language:Mapped[Optional[str]] = mapped_column(String(5))  # Override tenant language
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    last_active_at:Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Do Not Disturb (Shadow Mode)
    dnd_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    dnd_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    created_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys="Task.creator_id",
        back_populates="creator"
    )
    assigned_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys="Task.assignee_id",
        back_populates="assignee"
    )
    
    def __repr__(self) -> str:
        return f"<User {self.name}>"
