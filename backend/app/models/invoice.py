from __future__ import annotations
"""Invoice/Debt model for accounts receivable tracking."""
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.contact import Contact
    from app.models.payment_history import PaymentHistory


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class ReminderStatus(str, Enum):
    """Reminder status for debt collection."""
    PENDING = "pending"        # Not yet due
    DUE_SOON = "due_soon"     # Due within 3 days
    OVERDUE = "overdue"       # Past due
    REMINDED = "reminded"     # Reminder sent
    ESCALATED = "escalated"   # Multiple reminders sent


class Invoice(Base):
    """
    Invoice/Debt model for tracking money owed.
    Used by the Autonomous Debt Collector.
    """
    __tablename__ = "invoices"
    
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
    
    # Debtor info
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    debtor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    debtor_phone:Mapped[Optional[str]] = mapped_column(String(20))
    
    # Invoice details
    invoice_number:Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Amount
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="KZT")
    
    # Dates
    issue_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now
    )
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    paid_date:Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=InvoiceStatus.SENT.value,
        index=True
    )
    
    # Reminder tracking
    reminder_status: Mapped[str] = mapped_column(
        String(20),
        default=ReminderStatus.PENDING.value
    )
    reminder_count: Mapped[int] = mapped_column(default=0)
    last_reminder_sent:Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_reminder_date:Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Prepared message (ready to send)
    prepared_message:Mapped[Optional[str]] = mapped_column(Text)
    message_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Contract reference
    contract_number:Mapped[Optional[str]] = mapped_column(String(100))
    
    # Notes
    notes:Mapped[Optional[str]] = mapped_column(Text)
    
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
    tenant: Mapped["Tenant"] = relationship(back_populates="invoices")
    contact: Mapped[Optional["Contact"]] = relationship()
    payments: Mapped[list["PaymentHistory"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="PaymentHistory.paid_at"
    )
    
    # Track partial payments
    paid_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    
    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number or self.id}: {self.amount} {self.currency} from {self.debtor_name}>"
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.status == InvoiceStatus.PAID.value:
            return False
        return datetime.now() > self.due_date
    
    @property
    def days_overdue(self) -> int:
        """Get number of days overdue."""
        if not self.is_overdue:
            return 0
        delta = datetime.now() - self.due_date
        return delta.days
    
    @property
    def days_until_due(self) -> int:
        """Get days until due date."""
        if self.is_overdue:
            return -self.days_overdue
        delta = self.due_date - datetime.now()
        return delta.days
    
    def mark_paid(self, amount: Optional[float] = None) -> None:
        """Mark invoice as fully or partially paid."""
        if amount is None:
            # Full payment
            self.paid_amount = float(self.amount)
        else:
            self.paid_amount = float(self.paid_amount or 0) + float(amount)
        
        # If fully paid, update status
        if self.paid_amount >= float(self.amount):
            self.status = InvoiceStatus.PAID.value
            self.paid_date = datetime.now()
            self.reminder_status = ReminderStatus.PENDING.value
    
    @property
    def remaining_amount(self) -> float:
        """Get remaining amount to be paid."""
        return float(self.amount) - float(self.paid_amount or 0)
    
    def update_reminder_status(self) -> None:
        """Update reminder status based on current date."""
        if self.status == InvoiceStatus.PAID.value:
            return
        
        if self.is_overdue:
            if self.reminder_count > 0:
                self.reminder_status = ReminderStatus.REMINDED.value
            else:
                self.reminder_status = ReminderStatus.OVERDUE.value
                self.status = InvoiceStatus.OVERDUE.value
        elif self.days_until_due <= 3:
            self.reminder_status = ReminderStatus.DUE_SOON.value
