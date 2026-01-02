from __future__ import annotations
"""Contract model for tracking business agreements."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from typing import Optional


class Contract(Base):
    """
    Contract record for business agreements and ESF tracking.
    """
    __tablename__ = "contracts"
    
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
    
    # Contract details
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_type: Mapped[str] = mapped_column(
        String(50), 
        default="услуги"
    )  # "услуги", "поставка", "аренда", etc.
    
    # Amount
    amount:Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3), default="KZT")
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), 
        default="pending_esf"
    )  # "draft", "pending_esf", "esf_issued", "completed", "cancelled"
    
    # ESF (Electronic Invoice)
    esf_number:Mapped[Optional[str]] = mapped_column(String(100))
    esf_date:Mapped[Optional[date]] = mapped_column(Date)
    
    # Dates
    contract_date: Mapped[date] = mapped_column(Date, nullable=False)
    deadline:Mapped[Optional[date]] = mapped_column(Date)
    
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
    
    def __repr__(self) -> str:
        return f"<Contract {self.company_name}: {self.status}>"
