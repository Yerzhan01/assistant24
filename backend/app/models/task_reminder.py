from __future__ import annotations
"""Task Reminder model - for smart notifications."""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.task import Task


class ReminderType(str, Enum):
    """Reminder type enum."""
    EXACT = "exact"      # Exact time
    BEFORE_15 = "15_min" # 15 min before deadline
    BEFORE_60 = "1_hour" # 1 hour before deadline
    BEFORE_24H = "24_hours" # 24 hours before deadline
    SMART = "smart"      # AI calculated


class TaskReminder(Base):
    """
    Task Reminder model.
    Tracks when to send notifications for a task.
    """
    __tablename__ = "task_reminders"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    task_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # When to remind
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Type of reminder
    type: Mapped[str] = mapped_column(String(20), default=ReminderType.EXACT.value)
    
    # Status
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Error tracking
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    
    # Relationships
    # task: Mapped[Task] = relationship("Task", back_populates="reminders")
