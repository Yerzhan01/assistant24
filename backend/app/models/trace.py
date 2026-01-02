"""Trace model for request tracing and debugging."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Trace(Base):
    """
    Stores traces of AI request processing for debugging.
    
    Each trace contains:
    - The original user message
    - All processing steps with timing
    - Final result and any errors
    """
    __tablename__ = "traces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Short trace ID for easy lookup (e.g., "abc123")
    trace_id = Column(String(12), unique=True, nullable=False, index=True)
    
    # Tenant and user context
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Source: "web", "telegram", "whatsapp"
    source = Column(String(20), default="web")
    
    # Original message
    user_message = Column(Text, nullable=False)
    
    # Processing steps as JSON array
    # Each step: {"name": str, "duration_ms": int, "data": dict, "error": str|null}
    steps = Column(JSON, default=list)
    
    # Gemini API details
    gemini_model = Column(String(50), nullable=True)
    gemini_prompt_tokens = Column(Integer, nullable=True)
    gemini_response_tokens = Column(Integer, nullable=True)
    gemini_raw_response = Column(Text, nullable=True)
    
    # Intent classification result
    classified_intents = Column(JSON, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    
    # Final result
    final_response = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)
    
    # Timing
    total_duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def add_step(
        self, 
        name: str, 
        duration_ms: int = 0, 
        data: Dict[str, Any] = None,
        error: str = None
    ) -> None:
        """Add a processing step to the trace."""
        if self.steps is None:
            self.steps = []
        
        step = {
            "name": name,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {},
        }
        if error:
            step["error"] = error
            
        self.steps.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for API response."""
        return {
            "id": str(self.id),
            "trace_id": self.trace_id,
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "source": self.source,
            "user_message": self.user_message,
            "steps": self.steps or [],
            "gemini_model": self.gemini_model,
            "classified_intents": self.classified_intents,
            "ai_reasoning": self.ai_reasoning,
            "final_response": self.final_response,
            "success": self.success,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "total_duration_ms": self.total_duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
