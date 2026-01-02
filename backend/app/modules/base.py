from __future__ import annotations
"""Base module class - abstract interface for all functional modules."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ModuleResponse(BaseModel):
    """Response from module processing."""
    success: bool
    message: str  # Message to send to user
    data:Optional[ Dict[str, Any] ] = None  # Optional structured data


@dataclass
class ModuleInfo:
    """Module metadata."""
    module_id: str
    name_ru: str
    name_kz: str
    description_ru: str
    description_kz: str
    icon: str
    
    def get_name(self, lang: str = "ru") -> str:
        """Get name in specified language."""
        return self.name_kz if lang == "kz" else self.name_ru
    
    def get_description(self, lang: str = "ru") -> str:
        """Get description in specified language."""
        return self.description_kz if lang == "kz" else self.description_ru


class BaseModule(ABC):
    """
    Abstract base class for all functional modules.
    
    Each module must implement:
    - info: Module metadata
    - process(): Handle user intent
    - get_ai_instructions(): Provide AI with extraction rules
    """
    
    @property
    @abstractmethod
    def info(self) -> ModuleInfo:
        """Return module metadata."""
        pass
    
    @property
    def module_id(self) -> str:
        """Return module ID."""
        return self.info.module_id
    
    @abstractmethod
    async def process(
        self, 
        intent_data: Dict[str, Any], 
        tenant_id: UUID,
        user_id:Optional[ UUID ] = None,
        language: str = "ru"
    ) -> ModuleResponse:
        """
        Process user intent and return response.
        
        Args:
            intent_data: Extracted data from AI (e.g., amount, counterparty)
            tenant_id: Current tenant UUID
            user_id: Optional user UUID
            language: Response language ("ru" or "kz")
        
        Returns:
            ModuleResponse with status and message
        """
        pass
    
    @abstractmethod
    def get_ai_instructions(self, language: str = "ru") -> str:
        """
        Return instructions for AI on how to extract data for this module.
        
        This is used to build the AI prompt for intent classification.
        
        Args:
            language: Language for examples ("ru" or "kz")
        
        Returns:
            String with extraction rules and examples
        """
        pass
    
    def get_intent_keywords(self) -> List[str]:
        """
        Optional: Return keywords that might indicate this module's intent.
        Used for pre-filtering before AI processing.
        """
        return []
