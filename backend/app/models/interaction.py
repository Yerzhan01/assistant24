from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class InteractionSource(str, Enum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    SYSTEM = "system"

class InteractionRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class UnifiedInteraction(Base):
    """
    Unified log of all interactions across all channels.
    Single Source of Truth for history.
    """
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Optional user link (if known/registered)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Session ID is crucial for grouping.
    # For WhatsApp: "wa:<phone>" or "wa:<group_id>"
    # For Web: "web:<session_uuid>" or "web:<user_id>"
    session_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    source: Mapped[str] = mapped_column(String, nullable=False) # Enum values
    role: Mapped[str] = mapped_column(String, nullable=False)   # Enum values

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Rich metadata: intent, tokens, attachments, context_id, trace_id
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    def __repr__(self) -> str:
        return f"<Interaction {self.source}:{self.role} len={len(self.content)}>"
