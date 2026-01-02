from __future__ import annotations
"""Settings routes for bot configuration."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import CurrentTenant, Database
from app.services.telegram_bot import get_telegram_service
from app.services.whatsapp_bot import get_whatsapp_service
from app.core.config import settings as app_settings
from typing import Optional


router = APIRouter(prefix="/settings", tags=["settings"])


# Schemas
class TelegramSettings(BaseModel):
    bot_token: str


class WhatsAppSettings(BaseModel):
    instance_id: str
    token: str
    phone:Optional[ str ] = None


class LanguageSettings(BaseModel):
    language: str  # "ru" or "kz"


class AISettings(BaseModel):
    enabled: bool
    custom_api_key:Optional[ str ] = None


class TelegramStatusResponse(BaseModel):
    connected: bool
    webhook_url:Optional[ str ] = None


class WhatsAppStatusResponse(BaseModel):
    connected: bool
    phone:Optional[ str ] = None


@router.post("/telegram", response_model=TelegramStatusResponse)
async def setup_telegram(
    request: TelegramSettings,
    tenant: CurrentTenant,
    db: Database
):
    """Configure Telegram bot for tenant."""
    # Update tenant with bot token
    tenant.telegram_bot_token = request.bot_token
    
    base_url = app_settings.base_url
    
    # Set up webhook
    try:
        service = get_telegram_service()
        webhook_url = await service.setup_webhook(
            tenant.id, 
            request.bot_token,
            base_url
        )
        
        await db.commit()
        
        return TelegramStatusResponse(
            connected=True,
            webhook_url=webhook_url
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to set up Telegram bot: {str(e)}"
        )


@router.delete("/telegram")
async def disconnect_telegram(
    tenant: CurrentTenant,
    db: Database
):
    """Disconnect Telegram bot."""
    tenant.telegram_bot_token = None
    await db.commit()
    return {"status": "disconnected"}


@router.post("/whatsapp", response_model=WhatsAppStatusResponse)
async def setup_whatsapp(
    request: WhatsAppSettings,
    tenant: CurrentTenant,
    db: Database
):
    """Configure WhatsApp via GreenAPI for tenant."""
    # Update tenant
    tenant.greenapi_instance_id = request.instance_id
    tenant.greenapi_token = request.token
    tenant.whatsapp_phone = request.phone
    
    base_url = app_settings.base_url
    webhook_url = f"{base_url}/api/v1/webhooks/whatsapp/{tenant.id}"
    
    # Set up webhook
    try:
        service = get_whatsapp_service()
        await service.setup_webhook(
            request.instance_id,
            request.token,
            webhook_url
        )
        
        await db.commit()
        
        return WhatsAppStatusResponse(
            connected=True,
            phone=request.phone
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to set up WhatsApp: {str(e)}"
        )


@router.delete("/whatsapp")
async def disconnect_whatsapp(
    tenant: CurrentTenant,
    db: Database
):
    """Disconnect WhatsApp."""
    tenant.greenapi_instance_id = None
    tenant.greenapi_token = None
    tenant.whatsapp_phone = None
    await db.commit()
    return {"status": "disconnected"}


@router.get("/whatsapp/status")
async def get_whatsapp_status(
    tenant: CurrentTenant
):
    """
    Get WhatsApp instance status.
    
    Returns the current state of the WhatsApp instance:
    - "notAuthorized" - Need to scan QR code
    - "authorized" - Connected and ready
    - "blocked" - Instance is blocked
    - "sleepMode" - Instance in sleep mode
    """
    if not tenant.greenapi_instance_id or not tenant.greenapi_token:
        return {
            "connected": False,
            "state": "notConfigured",
            "message": "WhatsApp not configured. Please add instance ID and token."
        }
    
    try:
        service = get_whatsapp_service()
        state_response = await service.get_state_instance(
            tenant.greenapi_instance_id,
            tenant.greenapi_token
        )
        
        state = state_response.get("stateInstance", "unknown")
        
        return {
            "connected": state == "authorized",
            "state": state,
            "phone": tenant.whatsapp_phone,
            "instance_id": tenant.greenapi_instance_id,
            "message": _get_state_message(state)
        }
    except Exception as e:
        return {
            "connected": False,
            "state": "error",
            "message": f"Failed to check status: {str(e)}"
        }


@router.get("/whatsapp/qr")
async def get_whatsapp_qr(
    tenant: CurrentTenant
):
    """
    Get QR code for WhatsApp authorization.
    
    Returns base64 encoded QR code image if instance is not authorized.
    If already authorized, returns empty qr field.
    """
    if not tenant.greenapi_instance_id or not tenant.greenapi_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WhatsApp not configured. Please add instance ID and token first."
        )
    
    try:
        service = get_whatsapp_service()
        
        # First check state
        state_response = await service.get_state_instance(
            tenant.greenapi_instance_id,
            tenant.greenapi_token
        )
        state = state_response.get("stateInstance", "unknown")
        
        if state == "authorized":
            return {
                "state": "authorized",
                "qr": None,
                "message": "WhatsApp already connected! QR code not needed."
            }
        
        # Get QR code
        qr_response = await service.get_qr(
            tenant.greenapi_instance_id,
            tenant.greenapi_token
        )
        
        # GreenAPI returns: {"type": "qrCode", "message": "base64_image_data"}
        # or {"type": "error", "message": "error text"}
        if qr_response.get("type") == "qrCode":
            return {
                "state": state,
                "qr": qr_response.get("message"),  # Base64 QR image
                "message": "Scan this QR code with WhatsApp on your phone"
            }
        elif qr_response.get("type") == "alreadyLogged":
            return {
                "state": "authorized",
                "qr": None,
                "message": "WhatsApp already connected!"
            }
        else:
            return {
                "state": state,
                "qr": None,
                "message": qr_response.get("message", "Failed to get QR code")
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get QR code: {str(e)}"
        )


def _get_state_message(state: str) -> str:
    """Get human-readable message for WhatsApp state."""
    messages = {
        "notAuthorized": "Not authorized. Scan QR code to connect.",
        "authorized": "Connected and ready!",
        "blocked": "Instance is blocked. Contact support.",
        "sleepMode": "Instance in sleep mode. Will wake up on first message.",
        "starting": "Instance is starting up...",
        "unknown": "Unknown state. Try refreshing."
    }
    return messages.get(state, f"State: {state}")


@router.patch("/language")
async def update_language(
    request: LanguageSettings,
    tenant: CurrentTenant,
    db: Database
):
    """Update tenant's preferred language."""
    if request.language not in ["ru", "kz"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Language must be 'ru' or 'kz'"
        )
    
    tenant.language = request.language
    await db.commit()
    
    return {"language": tenant.language}


@router.patch("/ai")
async def update_ai_settings(
    request: AISettings,
    tenant: CurrentTenant,
    db: Database
):
    """Update AI settings for tenant."""
    tenant.ai_enabled = request.enabled
    
    if request.custom_api_key is not None:
        tenant.gemini_api_key = request.custom_api_key or None
    
    await db.commit()
    
    return {
        "ai_enabled": tenant.ai_enabled,
        "has_custom_key": bool(tenant.gemini_api_key)
    }
