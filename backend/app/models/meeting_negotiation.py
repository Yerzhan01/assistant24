from __future__ import annotations
"""Meeting negotiation model for autonomous scheduling."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func, JSON
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.contact import Contact


class NegotiationStatus(str, Enum):
    """Status of meeting negotiation."""
    INITIATED = "initiated"           # Just started
    SLOTS_SENT = "slots_sent"         # Proposed slots sent to contact
    WAITING_RESPONSE = "waiting"      # Waiting for contact's reply
    NEGOTIATING = "negotiating"       # Back-and-forth discussion
    CONFIRMED = "confirmed"           # Meeting time confirmed
    CANCELLED = "cancelled"           # Negotiation cancelled
    EXPIRED = "expired"               # No response in time


class MeetingNegotiation(Base):
    """
    Tracks autonomous meeting negotiation with external contacts.
    Bot proposes times, parses responses, and confirms meetings.
    """
    __tablename__ = "meeting_negotiations"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Tenant ownership
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Who initiated the meeting request
    initiator_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Contact being negotiated with
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Negotiation status
    status: Mapped[str] = mapped_column(
        String(20),
        default=NegotiationStatus.INITIATED.value,
        index=True
    )
    
    # Meeting details
    meeting_title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    
    meeting_notes:Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Proposed time slots (stored as ISO strings in array)
    proposed_slots: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )
    
    # Selected/confirmed slot
    selected_slot:Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # WhatsApp tracking
    whatsapp_chat_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    
    last_message_id:Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    # Message count for tracking conversation
    message_count: Mapped[int] = mapped_column(default=0)
    
    # Expiry - auto-cancel if no response
    expires_at:Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Created meeting reference
    meeting_id:Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
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
    tenant: Mapped["Tenant"] = relationship(back_populates="negotiations")
    initiator: Mapped["User"] = relationship()
    contact: Mapped["Contact"] = relationship()
    
    def __repr__(self) -> str:
        return f"<MeetingNegotiation {self.meeting_title} ({self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if negotiation is still active."""
        return self.status in (
            NegotiationStatus.INITIATED.value,
            NegotiationStatus.SLOTS_SENT.value,
            NegotiationStatus.WAITING_RESPONSE.value,
            NegotiationStatus.NEGOTIATING.value
        )
    
    def get_proposed_datetimes(self) -> List[datetime]:
        """Parse proposed slots as datetime objects."""
        if not self.proposed_slots:
            return []
        return [datetime.fromisoformat(s) for s in self.proposed_slots]
