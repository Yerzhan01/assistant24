"""WhatsApp Instance Model - for Green API Partner integration."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class InstanceStatus(str, Enum):
    """WhatsApp instance status."""
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    EXPIRED = "expired"


class WhatsAppInstance(Base):
    """WhatsApp instance for Green API Partner integration."""
    
    __tablename__ = "whatsapp_instances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    instance_id = Column(String, unique=True, nullable=False, index=True)
    token = Column(String, nullable=False)
    status = Column(SQLEnum(InstanceStatus), default=InstanceStatus.AVAILABLE, nullable=False)
    
    # Assignment tracking - UUID to match tenants.id
    assigned_to_tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationship
    tenant = relationship("Tenant", back_populates="whatsapp_instances")
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "instance_id": self.instance_id,
            "token": self.token,
            "status": self.status.value,
            "assigned_to": self.tenant.business_name if self.tenant else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
