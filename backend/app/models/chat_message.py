"""Chat message model for persistent conversation history."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChatMessage(Base):
    """Stores chat messages for persistent conversation history."""
    __tablename__ = "chat_messages"
    
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
    
    # Chat identifier (Telegram chat_id or WhatsApp chat_id)
    chat_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    
    # Message role (user or assistant)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    
    # Message content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    
    def __repr__(self) -> str:
        return f"<ChatMessage {self.role}: {self.content[:50]}...>"
