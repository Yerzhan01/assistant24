from __future__ import annotations
"""Contact model - Address book for meeting invitations and task assignments."""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func, JSON
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class Contact(Base):
    """
    Contact model for storing client/partner information.
    Used for AI to map names to phone numbers and send meeting invitations.
    """
    __tablename__ = "contacts"
    
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
    
    # Contact name
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    # Tags for categorization
    tags: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False
        # Note: PostgreSQL does not support btree indexes on JSON columns
    )
    
    # Phone number (clean format for GreenAPI: 77712345678)
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    
    # Email
    email:Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Name aliases for AI matching (e.g., ["Асхат", "Асеке", "Дизайнер"])
    aliases: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        default=list,
        nullable=True
    )
    
    # Company
    company:Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Position/Role
    position:Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Notes
    notes:Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Source (manual, auto_extracted, imported)
    source: Mapped[str] = mapped_column(
        String(50),
        default="manual"
    )
    
    # CRM Segment (client, partner, supplier, investor, other)
    segment: Mapped[str] = mapped_column(
        String(50),
        default="other",
        index=True
    )
    
    # Last interaction date (for tracking neglected contacts)
    last_interaction: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
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
    tenant: Mapped["Tenant"] = relationship(back_populates="contacts")
    
    def __repr__(self) -> str:
        return f"<Contact {self.name} ({self.phone})>"
    
    def matches_name(self, query: str) -> bool:
        """Check if contact matches a name query (case-insensitive)."""
        query_lower = query.lower().strip()
        
        # Check main name
        if query_lower in self.name.lower():
            return True
        
        # Check aliases
        if self.aliases:
            for alias in self.aliases:
                if query_lower in alias.lower():
                    return True
        
        return False
    
    @property
    def whatsapp_chat_id(self) -> str:
        """Get WhatsApp chat ID format."""
        clean_phone = self.phone.replace("+", "").replace(" ", "").replace("-", "")
        return f"{clean_phone}@c.us"
