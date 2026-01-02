"""Admin API Routes - User management and WhatsApp instances."""
from __future__ import annotations

import uuid
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.models.whatsapp_instance import WhatsAppInstance, InstanceStatus
from app.models.meeting import Meeting
from app.models.task import Task
from app.models.finance import FinanceRecord

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


from app.core.config import settings

# Green API Partner configuration
GREEN_API_PARTNER_TOKEN = settings.green_api_partner_token or ""
GREEN_API_BASE_URL = "https://api.green-api.com/partner"


# ============== Response Models ==============

class AdminStatsResponse(BaseModel):
    """Admin statistics response."""
    total_users: int
    active_users: int
    new_users_today: int
    new_users_week: int
    total_meetings: int
    total_tasks: int
    total_transactions: int
    total_messages: int


class AdminUserResponse(BaseModel):
    """Admin user response."""
    id: str
    email: str
    business_name: str
    created_at: datetime
    is_active: bool
    telegram_connected: bool
    whatsapp_connected: bool
    last_activity: Optional[datetime] = None
    stats: dict


class WhatsAppInstanceResponse(BaseModel):
    """WhatsApp instance response."""
    id: str
    instance_id: str
    token: str
    status: str
    assigned_to: Optional[str] = None
    created_at: datetime


class TraceResponse(BaseModel):
    """Trace response model."""
    id: str
    trace_id: str
    tenant_id: str
    source: str
    user_message: str
    success: bool
    error_message: Optional[str] = None
    created_at: datetime
    total_duration_ms: float
    steps: List[Dict[str, Any]]

    class Config:
        from_attributes = True


class TraceListResponse(BaseModel):
    """List of traces response."""
    traces: List[TraceResponse]
    total: int


# ============== Security ==============

async def require_admin(current_tenant: Tenant = Depends(get_current_tenant)):
    """Ensure the user is an admin."""
    ADMIN_EMAILS = ["test@test.kz"]
    if current_tenant.email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_tenant


# ============== Admin Stats ==============

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard statistics."""
    
    # Count users
    total_users = await db.scalar(select(func.count()).select_from(User))
    active_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active == True)
    )
    
    # New users today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_users_today = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= today)
    )
    
    # New users this week
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= week_ago)
    )
    
    # Count meetings
    total_meetings = await db.scalar(select(func.count()).select_from(Meeting))
    
    # Count tasks
    total_tasks = await db.scalar(select(func.count()).select_from(Task))
    
    # Count transactions
    total_transactions = await db.scalar(select(func.count()).select_from(FinanceRecord))
    
    return AdminStatsResponse(
        total_users=total_users or 0,
        active_users=active_users or 0,
        new_users_today=new_users_today or 0,
        new_users_week=new_users_week or 0,
        total_meetings=total_meetings or 0,
        total_tasks=total_tasks or 0,
        total_transactions=total_transactions or 0,
        total_messages=0  # TODO: Implement message counting
    )


# ============== Analytics & Usage ==============

@router.get("/usage")
async def get_usage_analytics(
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI usage analytics (Tokens & Cost).
    
    Pricing (Estimated for Gemini 1.5 Flash):
    - Input: $0.075 / 1M tokens
    - Output: $0.30 / 1M tokens
    - Rate: 1 USD = 500 KZT (approx)
    """
    from app.models.trace import Trace
    
    # Pricing Configuration (USD per 1M tokens)
    PRICING = {
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.0-pro": {"input": 0.50, "output": 1.50},  # Legacy pricing example
        "default": {"input": 0.10, "output": 0.40}
    }
    KZT_RATE = 500.0
    
    # Aggregation Query
    query = select(
        Trace.gemini_model,
        func.sum(Trace.gemini_prompt_tokens).label("prompt_tokens"),
        func.sum(Trace.gemini_response_tokens).label("response_tokens"),
        func.count(Trace.id).label("request_count")
    ).group_by(Trace.gemini_model)
    
    result = await db.execute(query)
    rows = result.all()
    
    usage_breakdown = []
    total_cost_usd = 0.0
    total_tokens = 0
    
    for row in rows:
        model = row.gemini_model or "unknown"
        p_tokens = row.prompt_tokens or 0
        r_tokens = row.response_tokens or 0
        count = row.request_count or 0
        
        # Determine pricing
        price_cfg = PRICING.get(model, PRICING["default"])
        if "flash" in model.lower():
            price_cfg = PRICING["gemini-1.5-flash"]
        
        cost_usd = (p_tokens / 1_000_000 * price_cfg["input"]) + \
                   (r_tokens / 1_000_000 * price_cfg["output"])
        
        total_cost_usd += cost_usd
        total_tokens += (p_tokens + r_tokens)
        
        usage_breakdown.append({
            "model": model,
            "requests": count,
            "prompt_tokens": p_tokens,
            "response_tokens": r_tokens,
            "total_tokens": p_tokens + r_tokens,
            "cost_usd": round(cost_usd, 4),
            "cost_kzt": round(cost_usd * KZT_RATE, 2)
        })
    
    return {
        "total_cost_kzt": round(total_cost_usd * KZT_RATE, 2),
        "total_tokens": total_tokens,
        "currency_rate": KZT_RATE,
        "breakdown": usage_breakdown
    }


# ============== User Management ==============

@router.get("/users")
async def get_admin_users(
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get list of all users with their stats."""
    
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    user_list = []
    for user in users:
        # Get tenant info
        tenant = await db.get(Tenant, user.tenant_id) if user.tenant_id else None
        
        # Get user stats
        meetings_count = await db.scalar(
            select(func.count()).select_from(Meeting).where(Meeting.tenant_id == user.tenant_id)
        ) if user.tenant_id else 0
        
        tasks_count = await db.scalar(
            select(func.count()).select_from(Task).where(Task.tenant_id == user.tenant_id)
        ) if user.tenant_id else 0
        
        transactions_count = await db.scalar(
            select(func.count()).select_from(FinanceRecord).where(FinanceRecord.tenant_id == user.tenant_id)
        ) if user.tenant_id else 0
        
        user_list.append({
            "id": user.id,
            "email": tenant.email if tenant else "N/A",
            "business_name": tenant.business_name if tenant else "N/A",
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_active": user.is_active,
            "telegram_connected": bool(tenant.telegram_bot_token if tenant else False),
            "whatsapp_connected": bool(tenant.whatsapp_instance_id if tenant else False),
            "last_activity": user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.updated_at else None,
            "stats": {
                "meetings": meetings_count or 0,
                "tasks": tasks_count or 0,
                "transactions": transactions_count or 0,
                "messages": 0
            }
        })
    
    return {"users": user_list}


# ============== WhatsApp Instance Management ==============

@router.get("/whatsapp/instances")
async def get_whatsapp_instances(
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all WhatsApp instances."""
    
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(WhatsAppInstance)
        .options(selectinload(WhatsAppInstance.tenant))
        .order_by(WhatsAppInstance.created_at.desc())
    )
    instances = result.scalars().all()
    
    return {"instances": [inst.to_dict() for inst in instances]}


@router.post("/whatsapp/generate")
async def generate_whatsapp_instance(
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Generate new WhatsApp instance via Green API Partner."""
    
    if not GREEN_API_PARTNER_TOKEN:
        # If no partner token, generate mock instance for testing
        instance = WhatsAppInstance(
            id=str(uuid.uuid4()),
            instance_id=f"instance_{uuid.uuid4().hex[:8]}",
            token=f"token_{uuid.uuid4().hex}",
            status=InstanceStatus.AVAILABLE,
            created_at=datetime.utcnow()
        )
        db.add(instance)
        await db.commit()
        
        # Reload with options to avoid MissingGreenlet
        result = await db.execute(
            select(WhatsAppInstance)
            .options(selectinload(WhatsAppInstance.tenant))
            .where(WhatsAppInstance.id == instance.id)
        )
        instance = result.scalar_one()
        return instance.to_dict()
    
    # Call Green API Partner to create instance
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GREEN_API_BASE_URL}/createInstance",
                headers={
                    "Authorization": f"Bearer {GREEN_API_PARTNER_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "webhookUrl": "",  # Will be set later
                    "webhookUrlToken": "",
                    "delaySendMessagesMilliseconds": 1000,
                    "markIncomingMessagesReaded": "yes",
                    "proxyInstance": "yes"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                
                instance = WhatsAppInstance(
                    id=str(uuid.uuid4()),
                    instance_id=data.get("idInstance", f"instance_{uuid.uuid4().hex[:8]}"),
                    token=data.get("apiTokenInstance", f"token_{uuid.uuid4().hex}"),
                    status=InstanceStatus.AVAILABLE,
                    created_at=datetime.utcnow()
                )
                db.add(instance)
                await db.commit()
                db.add(instance)
                await db.commit()
                
                # Reload with options to avoid MissingGreenlet
                result = await db.execute(
                    select(WhatsAppInstance)
                    .options(selectinload(WhatsAppInstance.tenant))
                    .where(WhatsAppInstance.id == instance.id)
                )
                instance = result.scalar_one()
                return instance.to_dict()
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Green API error: {response.text}"
                )
                
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to Green API: {str(e)}"
        )


@router.delete("/whatsapp/instances/{instance_id}")
async def delete_whatsapp_instance(
    instance_id: str,
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete WhatsApp instance."""
    
    instance = await db.get(WhatsAppInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # If connected to Green API, delete from there too
    if GREEN_API_PARTNER_TOKEN and instance.instance_id:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{GREEN_API_BASE_URL}/deleteInstance",
                    headers={
                        "Authorization": f"Bearer {GREEN_API_PARTNER_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    json={"idInstance": instance.instance_id},
                    timeout=30.0
                )
        except httpx.RequestError:
            pass  # Ignore errors when deleting from Green API
    
    await db.delete(instance)
    await db.commit()
    
    return {"status": "deleted", "id": instance_id}


@router.post("/whatsapp/instances/{instance_id}/assign")
async def assign_instance_to_user(
    instance_id: str,
    tenant_id: str,
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Assign WhatsApp instance to a tenant."""
    
    instance = await db.get(WhatsAppInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    instance.assigned_to_tenant_id = tenant_id
    instance.assigned_at = datetime.utcnow()
    instance.status = InstanceStatus.ASSIGNED
    
    # Also update tenant's WhatsApp settings
    tenant.whatsapp_instance_id = instance.instance_id
    tenant.whatsapp_token = instance.token
    
    await db.commit()
    await db.refresh(instance)
    
    return instance.to_dict()


@router.get("/whatsapp/instances/{instance_id}/status")
async def get_instance_status(
    instance_id: str,
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get WhatsApp instance status from Green API.
    
    Returns:
    - stateInstance: "notAuthorized", "authorized", "blocked", "sleepMode"
    """
    from app.services.whatsapp_bot import get_whatsapp_service
    
    instance = await db.get(WhatsAppInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    try:
        service = get_whatsapp_service()
        state_response = await service.get_state_instance(
            instance.instance_id,
            instance.token
        )
        
        state = state_response.get("stateInstance", "unknown")
        
        return {
            "instance_id": instance.instance_id,
            "db_id": instance_id,
            "state": state,
            "connected": state == "authorized",
            "assigned_to": instance.assigned_to_tenant_id,
            "message": _get_state_message_admin(state)
        }
    except Exception as e:
        return {
            "instance_id": instance.instance_id,
            "state": "error",
            "connected": False,
            "message": f"Failed to check status: {str(e)}"
        }


@router.get("/whatsapp/instances/{instance_id}/qr")
async def get_instance_qr(
    instance_id: str,
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get QR code for WhatsApp instance authorization.
    
    Returns base64 encoded QR code image if instance is not authorized.
    """
    from app.services.whatsapp_bot import get_whatsapp_service
    
    instance = await db.get(WhatsAppInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    try:
        service = get_whatsapp_service()
        
        # First check state
        state_response = await service.get_state_instance(
            instance.instance_id,
            instance.token
        )
        state = state_response.get("stateInstance", "unknown")
        
        if state == "authorized":
            return {
                "instance_id": instance.instance_id,
                "state": "authorized",
                "qr": None,
                "message": "Already authorized! QR code not needed."
            }
        
        # Get QR code
        qr_response = await service.get_qr(
            instance.instance_id,
            instance.token
        )
        
        if qr_response.get("type") == "qrCode":
            return {
                "instance_id": instance.instance_id,
                "state": state,
                "qr": qr_response.get("message"),  # Base64 QR image
                "message": "Scan this QR code with WhatsApp"
            }
        elif qr_response.get("type") == "alreadyLogged":
            return {
                "instance_id": instance.instance_id,
                "state": "authorized",
                "qr": None,
                "message": "Already authorized!"
            }
        else:
            return {
                "instance_id": instance.instance_id,
                "state": state,
                "qr": None,
                "message": qr_response.get("message", "Failed to get QR code")
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get QR code: {str(e)}"
        )


class UpdateInstanceRequest(BaseModel):
    """Request to update instance credentials."""
    instance_id: str
    token: str


@router.put("/whatsapp/instances/{db_instance_id}")
async def update_instance_credentials(
    db_instance_id: str,
    request: UpdateInstanceRequest,
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update WhatsApp instance with real credentials from Green API.
    
    Use this to replace mock instance_id and token with real ones.
    """
    from app.services.whatsapp_bot import get_whatsapp_service
    
    instance = await db.get(WhatsAppInstance, db_instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # Validate new credentials by checking state
    try:
        service = get_whatsapp_service()
        state_response = await service.get_state_instance(
            request.instance_id,
            request.token
        )
        state = state_response.get("stateInstance", "unknown")
        
        # Update instance
        old_instance_id = instance.instance_id
        instance.instance_id = request.instance_id
        instance.token = request.token
        
        # If assigned to a tenant, update their settings too
        if instance.assigned_to_tenant_id:
            tenant = await db.get(Tenant, instance.assigned_to_tenant_id)
            if tenant:
                tenant.greenapi_instance_id = request.instance_id
                tenant.greenapi_token = request.token
        
        await db.commit()
        
        return {
            "status": "updated",
            "old_instance_id": old_instance_id,
            "new_instance_id": request.instance_id,
            "state": state,
            "connected": state == "authorized"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid credentials or connection error: {str(e)}"
        )


def _get_state_message_admin(state: str) -> str:
    """Get human-readable message for WhatsApp state (admin version)."""
    messages = {
        "notAuthorized": "Not authorized - needs QR scan",
        "authorized": "Connected and ready",
        "blocked": "Instance blocked",
        "sleepMode": "Sleep mode",
        "starting": "Starting up...",
        "unknown": "Unknown state"
    }
    return messages.get(state, state)


# ============== Tracing / Debug ==============
# Note: Traces are also admin-only for now

@router.get("/traces", response_model=TraceListResponse)
async def get_traces(
    limit: int = 50,
    offset: int = 0,
    error_only: bool = False,
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of recent traces for debugging.
    
    Use this to see all AI interactions and their processing steps.
    """
    from app.services.tracing import TracingService
    from app.models.trace import Trace
    
    tracing = TracingService(db)
    
    if error_only:
        traces = await tracing.search_traces(
            tenant_id=current_tenant.id,
            error_only=True,
            limit=limit
        )
    else:
        # For admin, we might want to see ALL traces, not just current tenant's?
        # But for now, let's keep it scoped to tenant unless admin specifically wants global.
        # Given "test@test.kz" is the admin, they are probably a tenant too.
        # But real "Super Admin" might want to see everyone's.
        # Let's assume usage of search_traces(tenant_id=...) applies. 
        # Actually search_traces filters by tenant_id. 
        # If we want global traces, we need to adjust TracingService or pass a flag.
        # Let's keep it simple: admin sees their own or we need a way to see all.
        # For the requested "Stats" and "Analytics", we are looking at GLOBAL usage in the new endpoint.
        # But here, let's stick to the existing behavior but protected.
        traces = await tracing.get_traces(
            tenant_id=current_tenant.id,
            limit=limit,
            offset=offset
        )
    
    # Count total
    total = await db.scalar(
        select(func.count()).select_from(Trace).where(Trace.tenant_id == current_tenant.id)
    )
    
    return TraceListResponse(
        traces=[TraceResponse(**t.to_dict()) for t in traces],
        total=total or 0
    )


@router.get("/traces/search")
async def search_traces(
    q: Optional[str] = None,
    user_id: Optional[str] = None,
    error_only: bool = False,
    limit: int = 50,
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Search traces with filters.
    
    - q: Search in message text, error messages, or trace ID
    - user_id: Filter by specific user
    - error_only: Show only failed traces
    """
    from app.services.tracing import TracingService
    from uuid import UUID as UUIDType
    
    tracing = TracingService(db)
    
    user_uuid = None
    if user_id:
        try:
            user_uuid = UUIDType(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    # Search all traces for admin? 
    # Current implementation of TracingService.search_traces filters by tenant_id.
    # We might need to lift that restriction for Super Admin.
    # For now, let's use the current tenant ID, assuming the admin logs into the main tenant.
    traces = await tracing.search_traces(
        tenant_id=current_tenant.id,
        user_id=user_uuid,
        search_text=q,
        error_only=error_only,
        limit=limit
    )
    
    return {"traces": [t.to_dict() for t in traces]}


@router.get("/traces/{trace_id}")
async def get_trace_details(
    trace_id: str,
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed trace by its short ID.
    
    Shows all processing steps with timing and data.
    """
    from app.services.tracing import TracingService
    
    tracing = TracingService(db)
    trace = await tracing.get_trace_by_id(trace_id)
    
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    # Admin can view any trace
    # if str(trace.tenant_id) != str(current_tenant.id):
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    return trace.to_dict()


@router.get("/traces/stats")
async def get_trace_stats(
    current_tenant: Tenant = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tracing statistics for the dashboard.
    """
    from app.models.trace import Trace
    from datetime import timedelta
    
    # Total traces
    total = await db.scalar(
        select(func.count()).select_from(Trace).where(Trace.tenant_id == current_tenant.id)
    )
    
    # Failed traces
    failed = await db.scalar(
        select(func.count()).select_from(Trace).where(
            Trace.tenant_id == current_tenant.id,
            Trace.success == False
        )
    )
    
    # Today's traces
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await db.scalar(
        select(func.count()).select_from(Trace).where(
            Trace.tenant_id == current_tenant.id,
            Trace.created_at >= today
        )
    )
    
    # Average duration
    avg_duration = await db.scalar(
        select(func.avg(Trace.total_duration_ms)).where(
            Trace.tenant_id == current_tenant.id,
            Trace.total_duration_ms.isnot(None)
        )
    )
    
    return {
        "total_traces": total or 0,
        "failed_traces": failed or 0,
        "success_rate": round((1 - (failed or 0) / max(total or 1, 1)) * 100, 1),
        "today_traces": today_count or 0,
        "avg_duration_ms": round(avg_duration or 0, 0)
    }

