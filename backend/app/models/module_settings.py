from __future__ import annotations
"""Module settings model for per-tenant module configuration."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class TenantModuleSettings(Base):
    """
    Per-tenant module settings.
    Allows enabling/disabling modules and storing module-specific configuration.
    """
    __tablename__ = "tenant_module_settings"
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "module_id", name="uq_tenant_module"),
    )
    
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
    
    # Module identifier
    module_id: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        index=True
    )  # "finance", "meeting", "contract", "ideas", "birthday", "report"
    
    # Enabled/disabled
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Module-specific settings (JSON)
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSON, 
        default=dict,
        nullable=False
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
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="module_settings")
    
    def __repr__(self) -> str:
        status = "ON" if self.is_enabled else "OFF"
        return f"<ModuleSettings {self.module_id}={status}>"
