"""Chat API - Connects frontend to AI Router for conversational interface."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db
from app.models.tenant import Tenant
from app.services.ai_router import AIRouter

router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat message request."""
    message: str


class ChatResponse(BaseModel):
    """Chat response."""
    response: str
    success: bool = True
    intent: Optional[str] = None
    timestamp: datetime = datetime.now()


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime
    intent: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a chat message through the AI Router with Streaming Response (SSE).
    Returns real-time updates on agent status/thought process.
    """
    # Initialize AI Router
    ai_router = AIRouter(
        db=db,
        api_key=current_tenant.gemini_api_key,
        language=current_tenant.language or "ru",
        enable_rag=True
    )
    
    from fastapi.responses import StreamingResponse
    import asyncio
    import json
    
    # Create a generic queue for stream events
    stream_queue = asyncio.Queue()
    
    # Callback to push status updates to queue
    async def on_status(status_msg: str):
        await stream_queue.put({
            "type": "status",
            "content": status_msg
        })
    
    # Background task wrapper
    async def run_agent():
        try:
            response = await ai_router.process_message(
                message=request.message,
                tenant_id=current_tenant.id,
                user_id=None,
                on_status=on_status
            )
            # Commit changes (critical!)
            await db.commit()
            
            # success result
            await stream_queue.put({
                "type": "result",
                "content": response.message,
                "intent": getattr(response, "intent", None) or "unknown"
            })
        except Exception as e:
            await stream_queue.put({
                "type": "error",
                "content": str(e)
            })
        finally:
            await stream_queue.put(None) # Signal end
    
    # Start agent in background
    asyncio.create_task(run_agent())
    
    # Generator for SSE
    async def event_generator():
        while True:
            data = await stream_queue.get()
            if data is None:
                break
            
            # Format as SSE
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/chat/status")
async def chat_status(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Check if chat/AI is properly configured."""
    
    # Check if Gemini API key is configured
    from app.core.config import settings
    has_api_key = bool(current_tenant.gemini_api_key or settings.gemini_api_key)
    
    return {
        "configured": has_api_key,
        "ai_enabled": current_tenant.ai_enabled,
        "language": current_tenant.language,
        "has_whatsapp": bool(current_tenant.greenapi_instance_id),
        "has_telegram": bool(current_tenant.telegram_bot_token)
    }


@router.get("/chat/history", response_model=list[MessageResponse])
async def get_chat_history(
    limit: int = 50,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get chat history."""
    from sqlalchemy import select, desc
    from app.models.chat import Message
    
    stmt = select(Message).where(
        Message.tenant_id == current_tenant.id
    ).order_by(desc(Message.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    # Return in chronological order
    history = []
    for msg in reversed(messages):
        history.append(MessageResponse(
            id=str(msg.id),
            role="user" if msg.is_user else "assistant",
            content=msg.content,
            timestamp=msg.created_at,
            intent=msg.intent
        ))
        
    return history
