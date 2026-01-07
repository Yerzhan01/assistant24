from __future__ import annotations
"""Finance model for income/expense tracking."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FinanceRecord(Base):
    """
    Finance record for tracking income and expenses.
    """
    __tablename__ = "finance_records"
    
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
    
    # User who created
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Record type
    type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # "income" or "expense"
    
    # Amount
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), 
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="KZT")
    
    # Categorization
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    # Categories: salary, project, investment, taxi, food, office, etc.
    
    # Details
    counterparty:Mapped[Optional[str]] = mapped_column(String(255))  # Who paid/received
    description:Mapped[Optional[str]] = mapped_column(Text)
    
    # Date of transaction
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<Finance {self.type}: {self.amount} {self.currency}>"
