from __future__ import annotations
"""System event model for autonomous agent persistence - PostgreSQL compatible."""
from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemEvent(Base):
    """Log of system events for autonomous agent persistence."""
    __tablename__ = "system_events"
    
    # Primary key - UUID
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # Tenant - UUID to match tenants.id
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Event type
    event_type: Mapped[str] = mapped_column(String(50), index=True) 
    # types: "morning_briefing", "meeting_reminder", "task_reminder"
    
    # Reference to related entity (e.g., task_id or meeting_id)
    reference_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # Additional details
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
