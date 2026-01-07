from __future__ import annotations
"""Tenant model for multi-tenancy support."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.module_settings import TenantModuleSettings
    from app.models.user import User
    from app.models.group_chat import GroupChat
    from app.models.task import Task
    from app.models.contact import Contact
    from app.models.memory import Memory
    from app.models.meeting_negotiation import MeetingNegotiation
    from app.models.meeting import Meeting
    from app.models.invoice import Invoice
    from app.models.whatsapp_instance import WhatsAppInstance
    from app.models.birthday import Birthday
    from app.models.idea import Idea


class Tenant(Base):
    """
    Tenant represents a business/organization using the platform.
    Each tenant has their own bots and settings.
    """
    __tablename__ = "tenants"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Basic info
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Telegram Bot
    telegram_bot_token:Mapped[Optional[str]] = mapped_column(Text)
    telegram_webhook_secret:Mapped[Optional[str]] = mapped_column(String(64))
    
    # WhatsApp (GreenAPI)
    greenapi_instance_id:Mapped[Optional[str]] = mapped_column(String(64))
    greenapi_token:Mapped[Optional[str]] = mapped_column(Text)
    whatsapp_phone:Mapped[Optional[str]] = mapped_column(String(20))
    whatsapp_webhook_secret:Mapped[Optional[str]] = mapped_column(String(128))  # For webhook signature validation
    
    # AI Settings
    gemini_api_key:Mapped[Optional[str]] = mapped_column(Text)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Calendar Settings
    calendar_feed_token:Mapped[Optional[str]] = mapped_column(String(64))  # For iCal URL security
    
    # Localization
    language: Mapped[str] = mapped_column(String(5), default="ru")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Almaty")
    
    # Plan & Status
    plan: Mapped[str] = mapped_column(String(20), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
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
    users: Mapped[List["User"]] = relationship("User", back_populates="tenant")
    module_settings: Mapped[List["TenantModuleSettings"]] = relationship(
        "TenantModuleSettings", 
        back_populates="tenant"
    )
    group_chats: Mapped[List["GroupChat"]] = relationship(
        "GroupChat",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    contacts: Mapped[List["Contact"]] = relationship(
        "Contact",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    memories: Mapped[List["Memory"]] = relationship(
        "Memory",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    negotiations: Mapped[List["MeetingNegotiation"]] = relationship(
        "MeetingNegotiation",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    meetings: Mapped[List["Meeting"]] = relationship(
        "Meeting",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    whatsapp_instances: Mapped[List["WhatsAppInstance"]] = relationship(
        "WhatsAppInstance",
        back_populates="tenant"
    )
    birthdays: Mapped[List["Birthday"]] = relationship(
        "Birthday",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    ideas: Mapped[List["Idea"]] = relationship(
        "Idea",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    
    # Property aliases for WhatsApp service compatibility
    @property
    def whatsapp_instance_id(self) ->Optional[ str ]:
        """Alias for greenapi_instance_id."""
        return self.greenapi_instance_id
    
    @property
    def whatsapp_api_token(self) ->Optional[ str ]:
        """Alias for greenapi_token."""
        return self.greenapi_token
    
    def __repr__(self) -> str:
        return f"<Tenant {self.business_name}>"


