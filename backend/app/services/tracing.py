"""
Tracing Service for Digital Secretary.

Provides comprehensive request tracing for debugging AI bot issues.
Logs every step of message processing with timing and data.

Usage:
    async with TracingService(db, tenant_id, message) as trace:
        trace.log_rag("Found 3 documents", {"docs": [...]})
        trace.log_gemini_request(prompt, response)
        trace.log_intent("meeting", 0.95, {...})
        trace.log_module_execution("meeting", result)
"""
from __future__ import annotations

import logging
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trace import Trace

logger = logging.getLogger("tracing")


def generate_trace_id() -> str:
    """Generate a short, human-readable trace ID."""
    return secrets.token_hex(6)  # 12 characters


class TraceContext:
    """
    Context manager for tracing a single request.
    
    Automatically saves trace to database on exit.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_message: str,
        user_id: Optional[UUID] = None,
        source: str = "web"
    ):
        self.db = db
        self.trace = Trace(
            trace_id=generate_trace_id(),
            tenant_id=tenant_id,
            user_id=user_id,
            source=source,
            user_message=user_message,
            steps=[],
            created_at=datetime.utcnow()
        )
        self.start_time = time.perf_counter()
        self._step_start_time = None
        
        # Log start
        logger.info(f"[{self.trace.trace_id}] START: {user_message[:100]}...")
    
    @property
    def trace_id(self) -> str:
        return self.trace.trace_id
    
    def _elapsed_ms(self) -> int:
        """Get elapsed time since start in milliseconds."""
        return int((time.perf_counter() - self.start_time) * 1000)
    
    def _step_elapsed_ms(self) -> int:
        """Get elapsed time since step start in milliseconds."""
        if self._step_start_time is None:
            return 0
        return int((time.perf_counter() - self._step_start_time) * 1000)
    
    def start_step(self, name: str) -> None:
        """Start timing a new step."""
        self._step_start_time = time.perf_counter()
        logger.debug(f"[{self.trace_id}] → Step: {name}")
    
    def end_step(self, name: str, data: Dict[str, Any] = None, error: str = None) -> None:
        """End current step and log it."""
        duration = self._step_elapsed_ms()
        self.trace.add_step(name, duration, data, error)
        
        if error:
            logger.warning(f"[{self.trace_id}] ✗ {name}: {error} ({duration}ms)")
        else:
            logger.info(f"[{self.trace_id}] ✓ {name} ({duration}ms)")
    
    def log_step(self, name: str, data: Dict[str, Any] = None, error: str = None) -> None:
        """Log a step with current timestamp (no timing)."""
        self.trace.add_step(name, 0, data, error)
        
        if error:
            logger.warning(f"[{self.trace_id}] ✗ {name}: {error}")
        else:
            logger.info(f"[{self.trace_id}] • {name}")
    
    def log_rag(self, context: str, metadata: Dict[str, Any] = None) -> None:
        """Log RAG context retrieval."""
        data = {
            "context_length": len(context) if context else 0,
            "has_context": bool(context),
            **(metadata or {})
        }
        self.log_step("rag_retrieval", data)
    
    def log_gemini_request(
        self,
        prompt: str,
        response_text: str,
        model: str = None,
        prompt_tokens: int = None,
        response_tokens: int = None
    ) -> None:
        """Log Gemini API call."""
        self.trace.gemini_model = model
        self.trace.gemini_prompt_tokens = prompt_tokens
        self.trace.gemini_response_tokens = response_tokens
        self.trace.gemini_raw_response = response_text[:2000]  # Limit size
        
        data = {
            "model": model,
            "prompt_length": len(prompt),
            "response_length": len(response_text),
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
        }
        self.log_step("gemini_api_call", data)
    
    def log_intent_classification(
        self,
        intents: List[Dict[str, Any]],
        reasoning: str = None
    ) -> None:
        """Log intent classification result."""
        self.trace.classified_intents = intents
        self.trace.ai_reasoning = reasoning
        
        intent_summary = ", ".join([
            f"{i.get('intent')}({i.get('confidence', 0):.2f})" 
            for i in intents
        ])
        
        data = {
            "intents": intent_summary,
            "count": len(intents),
            "reasoning_preview": reasoning[:200] if reasoning else None
        }
        self.log_step("intent_classification", data)
        
        logger.info(f"[{self.trace_id}] 🎯 Intents: {intent_summary}")
        if reasoning:
            logger.debug(f"[{self.trace_id}] 💭 Reasoning: {reasoning}")
    
    def log_module_execution(
        self,
        module_id: str,
        success: bool,
        result_message: str = None,
        error: str = None
    ) -> None:
        """Log module execution."""
        data = {
            "module": module_id,
            "success": success,
            "result_preview": result_message[:200] if result_message else None
        }
        self.log_step(f"module_{module_id}", data, error)
        
        if success:
            logger.info(f"[{self.trace_id}] ✅ Module {module_id}: OK")
        else:
            logger.warning(f"[{self.trace_id}] ❌ Module {module_id}: {error}")
    
    def log_error(self, error_type: str, error_message: str) -> None:
        """Log an error."""
        self.trace.success = False
        self.trace.error_type = error_type
        self.trace.error_message = error_message
        
        self.log_step("error", {"type": error_type}, error_message)
        logger.error(f"[{self.trace_id}] 🔥 {error_type}: {error_message}")
    
    def set_final_response(self, response: str, success: bool = True) -> None:
        """Set the final response."""
        self.trace.final_response = response
        self.trace.success = success
    
    async def save(self) -> None:
        """Save trace to database."""
        self.trace.total_duration_ms = self._elapsed_ms()
        
        try:
            self.db.add(self.trace)
            await self.db.flush()
            
            logger.info(
                f"[{self.trace_id}] END: "
                f"{'✅' if self.trace.success else '❌'} "
                f"({self.trace.total_duration_ms}ms)"
            )
        except Exception as e:
            # CRITICAL: Rollback to clear the corrupted transaction state
            try:
                await self.db.rollback()
            except Exception:
                pass  # Ignore rollback errors
            logger.error(f"[{self.trace_id}] Failed to save trace: {e}")


class TracingService:
    """
    Service for managing request traces.
    
    Usage:
        service = TracingService(db)
        trace = service.start_trace(tenant_id, message)
        # ... processing ...
        await trace.save()
        
    Or as context manager:
        async with service.trace(tenant_id, message) as t:
            t.log_step("something", {...})
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def start_trace(
        self,
        tenant_id: UUID,
        user_message: str,
        user_id: Optional[UUID] = None,
        source: str = "web"
    ) -> TraceContext:
        """Start a new trace."""
        return TraceContext(
            db=self.db,
            tenant_id=tenant_id,
            user_message=user_message,
            user_id=user_id,
            source=source
        )
    
    @asynccontextmanager
    async def trace(
        self,
        tenant_id: UUID,
        user_message: str,
        user_id: Optional[UUID] = None,
        source: str = "web"
    ):
        """Context manager for tracing."""
        ctx = self.start_trace(tenant_id, user_message, user_id, source)
        try:
            yield ctx
        except Exception as e:
            ctx.log_error(type(e).__name__, str(e))
            raise
        finally:
            await ctx.save()
    
    async def get_traces(
        self,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
        success_only: bool = None
    ) -> List[Trace]:
        """Get traces for a tenant."""
        from sqlalchemy import select, desc
        
        stmt = select(Trace).where(
            Trace.tenant_id == tenant_id
        ).order_by(desc(Trace.created_at))
        
        if success_only is not None:
            stmt = stmt.where(Trace.success == success_only)
        
        stmt = stmt.offset(offset).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_trace_by_id(self, trace_id: str) -> Optional[Trace]:
        """Get a specific trace by its short ID."""
        from sqlalchemy import select
        
        stmt = select(Trace).where(Trace.trace_id == trace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def search_traces(
        self,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        search_text: Optional[str] = None,
        error_only: bool = False,
        limit: int = 50
    ) -> List[Trace]:
        """Search traces with filters."""
        from sqlalchemy import select, desc, or_
        
        stmt = select(Trace).where(Trace.tenant_id == tenant_id)
        
        if user_id:
            stmt = stmt.where(Trace.user_id == user_id)
        
        if error_only:
            stmt = stmt.where(Trace.success == False)
        
        if search_text:
            stmt = stmt.where(
                or_(
                    Trace.user_message.ilike(f"%{search_text}%"),
                    Trace.error_message.ilike(f"%{search_text}%"),
                    Trace.trace_id.ilike(f"%{search_text}%")
                )
            )
        
        stmt = stmt.order_by(desc(Trace.created_at)).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
