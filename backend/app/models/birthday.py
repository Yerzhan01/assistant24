from __future__ import annotations
"""Birthday model - For tracking birthdays."""
from datetime import datetime, date
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Integer, String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant

class Birthday(Base):
    """
    Birthday model.
    Tracks birthdays of important contacts/people.
    """
    __tablename__ = "birthdays"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Tenant
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Individual's name
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Date of birth (stored as date only, year is optional conceptually but required by Date type usually,
    # often we store full date or just month/day. Let's assume full date for now or handle year=1 for unknowns)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Optional phone for automated greeting
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Reminder settings (days before)
    reminder_days: Mapped[int] = mapped_column(Integer, default=3)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
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
    tenant: Mapped["Tenant"] = relationship(back_populates="birthdays")

    def __repr__(self) -> str:
        return f"<Birthday {self.name} ({self.date})>"
