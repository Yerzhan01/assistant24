from __future__ import annotations
"""Module registry - manages all available modules."""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module_settings import TenantModuleSettings
from app.modules.assistant.module import AssistantModule
from app.modules.meeting.module import MeetingModule
from app.modules.task.module import TaskModule
from app.modules.finance.module import FinanceModule
from app.modules.contacts.module import ContactsModule
from app.modules.ideas.module import IdeasModule
from app.modules.birthday.module import BirthdayModule
from app.modules.contract.module import ContractModule
from app.modules.report.module import ReportModule
from app.modules.debtor.module import DebtorModule

from app.models.module_settings import TenantModuleSettings
from app.modules.base import BaseModule, ModuleInfo


class ModuleRegistry:
    """
    Registry for managing functional modules.
    
    Handles module registration, retrieval, and tenant-specific settings.
    """
    
    def __init__(self) -> None:
        self._modules: Dict[str, BaseModule] = {}
        # self._register_default_modules() # Main.py handles this manually now
    
    def register(self, module: BaseModule) -> None:
        """Register a module."""
        self._modules[module.module_id] = module
    
    def get(self, module_id: str) ->Optional[ BaseModule ]:
        """Get a module by ID."""
        return self._modules.get(module_id)
    
    def get_all(self) -> List[BaseModule]:
        """Get all registered modules."""
        return list(self._modules.values())
    
    def get_all_info(self, language: str = "ru") -> List[Dict[str, Any]]:
        """Get info for all modules in specified language."""
        return [
            {
                "module_id": m.info.module_id,
                "name": m.info.get_name(language),
                "description": m.info.get_description(language),
                "icon": m.info.icon,
            }
            for m in self._modules.values()
        ]
    
    def get_module_ids(self) -> List[str]:
        """Get all registered module IDs."""
        return list(self._modules.keys())
    
    async def get_enabled_modules(
        self, 
        db: AsyncSession, 
        tenant_id: UUID
    ) -> List[BaseModule]:
        """Get all modules enabled for a tenant."""
        # Get tenant's module settings
        stmt = select(TenantModuleSettings).where(
            TenantModuleSettings.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        settings = {s.module_id: s for s in result.scalars().all()}
        
        enabled = []
        for module_id, module in self._modules.items():
            # If no settings exist, module is enabled by default
            if module_id not in settings or settings[module_id].is_enabled:
                enabled.append(module)
        
        return enabled
    
    async def is_module_enabled(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        module_id: str
    ) -> bool:
        """Check if a specific module is enabled for a tenant."""
        stmt = select(TenantModuleSettings).where(
            TenantModuleSettings.tenant_id == tenant_id,
            TenantModuleSettings.module_id == module_id
        )
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()
        
        # Enabled by default if no settings
        return setting.is_enabled if setting else True
    
    async def set_module_enabled(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        module_id: str,
        enabled: bool
    ) -> TenantModuleSettings:
        """Enable or disable a module for a tenant."""
        stmt = select(TenantModuleSettings).where(
            TenantModuleSettings.tenant_id == tenant_id,
            TenantModuleSettings.module_id == module_id
        )
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.is_enabled = enabled
        else:
            setting = TenantModuleSettings(
                tenant_id=tenant_id,
                module_id=module_id,
                is_enabled=enabled
            )
            db.add(setting)
        
        await db.flush()
        return setting
    
    def build_ai_prompt(self, modules: List[BaseModule], language: str = "ru") -> str:
        """
        Build AI system prompt with instructions from all enabled modules.
        """
        module_instructions = []
        
        for module in modules:
            info = module.info
            instructions = module.get_ai_instructions(language)
            
            module_instructions.append(
                f"## {info.icon} {info.get_name(language)} (intent: {module.module_id})\n"
                f"{instructions}"
            )
        
        return "\n\n".join(module_instructions)


# Global registry instance
registry = ModuleRegistry()


def get_registry() -> ModuleRegistry:
    """Get the global module registry."""
    return registry
