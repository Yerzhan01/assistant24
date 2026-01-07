from __future__ import annotations
"""Module management routes."""
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentTenant, Database, Language
from app.models.module_settings import TenantModuleSettings
from app.modules.registry import get_registry


router = APIRouter(prefix="/modules", tags=["modules"])


# Schemas
class ModuleInfo(BaseModel):
    module_id: str
    name: str
    description: str
    icon: str
    is_enabled: bool


class ModuleToggleRequest(BaseModel):
    is_enabled: bool


class ModuleSettingsUpdate(BaseModel):
    settings: Dict[str, Any]


@router.get("", response_model=List[ModuleInfo])
async def list_modules(
    tenant: CurrentTenant,
    db: Database,
    lang: Language
):
    """List all available modules with their status for current tenant."""
    registry = get_registry()
    
    # Get tenant's module settings
    stmt = select(TenantModuleSettings).where(
        TenantModuleSettings.tenant_id == tenant.id
    )
    result = await db.execute(stmt)
    settings_map = {s.module_id: s for s in result.scalars().all()}
    
    modules = []
    for module in registry.get_all():
        info = module.info
        setting = settings_map.get(module.module_id)
        
        modules.append(ModuleInfo(
            module_id=module.module_id,
            name=info.get_name(lang),
            description=info.get_description(lang),
            icon=info.icon,
            is_enabled=setting.is_enabled if setting else True  # Default enabled
        ))
    
    return modules


@router.patch("/{module_id}", response_model=ModuleInfo)
async def toggle_module(
    module_id: str,
    request: ModuleToggleRequest,
    tenant: CurrentTenant,
    db: Database,
    lang: Language
):
    """Enable or disable a module for current tenant."""
    registry = get_registry()
    
    # Check if module exists
    module = registry.get(module_id)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module {module_id} not found"
        )
    
    # Update or create setting
    stmt = select(TenantModuleSettings).where(
        TenantModuleSettings.tenant_id == tenant.id,
        TenantModuleSettings.module_id == module_id
    )
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.is_enabled = request.is_enabled
    else:
        setting = TenantModuleSettings(
            tenant_id=tenant.id,
            module_id=module_id,
            is_enabled=request.is_enabled
        )
        db.add(setting)
    
    await db.commit()
    
    info = module.info
    return ModuleInfo(
        module_id=module.module_id,
        name=info.get_name(lang),
        description=info.get_description(lang),
        icon=info.icon,
        is_enabled=setting.is_enabled
    )


@router.get("/{module_id}/settings")
async def get_module_settings(
    module_id: str,
    tenant: CurrentTenant,
    db: Database
) -> Dict[str, Any]:
    """Get settings for a specific module."""
    stmt = select(TenantModuleSettings).where(
        TenantModuleSettings.tenant_id == tenant.id,
        TenantModuleSettings.module_id == module_id
    )
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    
    return setting.settings if setting else {}


@router.put("/{module_id}/settings")
async def update_module_settings(
    module_id: str,
    request: ModuleSettingsUpdate,
    tenant: CurrentTenant,
    db: Database
) -> Dict[str, Any]:
    """Update settings for a specific module."""
    stmt = select(TenantModuleSettings).where(
        TenantModuleSettings.tenant_id == tenant.id,
        TenantModuleSettings.module_id == module_id
    )
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.settings = request.settings
    else:
        setting = TenantModuleSettings(
            tenant_id=tenant.id,
            module_id=module_id,
            is_enabled=True,
            settings=request.settings
        )
        db.add(setting)
    
    await db.commit()
    
    return setting.settings
