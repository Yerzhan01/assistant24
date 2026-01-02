from __future__ import annotations
"""Webhook routes for Telegram and WhatsApp."""
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, status

from app.services.telegram_bot import get_telegram_service
from app.services.whatsapp_bot import get_whatsapp_service


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/telegram/{tenant_id}")
async def telegram_webhook(
    tenant_id: UUID,
    request: Request
) -> Dict[str, str]:
    """Handle incoming Telegram webhook for a specific tenant."""
    try:
        update_data = await request.json()
        service = get_telegram_service()
        result = await service.process_update(tenant_id, update_data)
        
        return result or {"status": "ignored"}
    except Exception as e:
        # Don't raise - Telegram expects 200 response
        return {"status": "error", "message": str(e)}


@router.post("/whatsapp/{tenant_id}")
async def whatsapp_webhook(
    tenant_id: UUID,
    request: Request
) -> Dict[str, str]:
    """Handle incoming GreenAPI webhook for a specific tenant."""
    try:
        webhook_data = await request.json()
        service = get_whatsapp_service()
        result = await service.process_webhook(tenant_id, webhook_data)
        
        return result or {"status": "ignored"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
