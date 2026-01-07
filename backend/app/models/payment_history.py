from __future__ import annotations
"""Payment history model for tracking partial payments on invoices."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.invoice import Invoice


class PaymentHistory(Base):
    """
    Tracks individual payments against an invoice.
    Supports partial payments with notes.
    """
    __tablename__ = "payment_history"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now,
        nullable=False
    )
    
    note: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Relationships
    invoice: Mapped["Invoice"] = relationship(back_populates="payments")
    
    def __repr__(self) -> str:
        return f"<Payment {self.amount} on {self.paid_at.strftime('%d.%m.%Y')}>"
