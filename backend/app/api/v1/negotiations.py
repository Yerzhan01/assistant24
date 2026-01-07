from __future__ import annotations
"""API routes for meeting negotiations management."""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant, get_db, get_language
from app.models.meeting_negotiation import MeetingNegotiation, NegotiationStatus
from app.models.contact import Contact
from app.services.meeting_negotiator import MeetingNegotiator
from app.services.whatsapp_bot import WhatsAppBotService

router = APIRouter(prefix="/api/v1/negotiations", tags=["negotiations"])


# ==================== Schemas ====================

class NegotiationCreate(BaseModel):
    contact_name: str = Field(..., description="Name of contact to schedule with")
    meeting_title: str = Field(..., max_length=500)
    meeting_notes:Optional[ str ] = None
    days_ahead: int = Field(7, ge=1, le=30, description="Days ahead to look for slots")
    num_slots: int = Field(3, ge=2, le=5, description="Number of slots to propose")


class NegotiationResponse(BaseModel):
    id: UUID
    status: str
    meeting_title: str
    meeting_notes:Optional[ str ]
    proposed_slots:Optional[ List[str] ]
    selected_slot:Optional[ datetime ]
    contact_name:Optional[ str ] = None
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NegotiationActionResponse(BaseModel):
    status: str
    message: str
    negotiation_id:Optional[ str ] = None
    proposed_slots:Optional[ List[str] ] = None


# ==================== Endpoints ====================

@router.get("", response_model=List[NegotiationResponse])
async def list_negotiations(
    status:Optional[ str ] = Query(None, description="Filter by status"),
    active_only: bool = Query(False, description="Show only active negotiations"),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all meeting negotiations."""
    stmt = select(MeetingNegotiation).where(
        MeetingNegotiation.tenant_id == tenant.id
    )
    
    if status:
        stmt = stmt.where(MeetingNegotiation.status == status)
    elif active_only:
        stmt = stmt.where(MeetingNegotiation.status.in_([
            NegotiationStatus.INITIATED.value,
            NegotiationStatus.SLOTS_SENT.value,
            NegotiationStatus.WAITING_RESPONSE.value,
            NegotiationStatus.NEGOTIATING.value
        ]))
    
    stmt = stmt.order_by(MeetingNegotiation.created_at.desc())
    result = await db.execute(stmt)
    negotiations = result.scalars().all()
    
    # Enrich with contact names
    response = []
    for neg in negotiations:
        neg_dict = {
            "id": neg.id,
            "status": neg.status,
            "meeting_title": neg.meeting_title,
            "meeting_notes": neg.meeting_notes,
            "proposed_slots": neg.proposed_slots,
            "selected_slot": neg.selected_slot,
            "message_count": neg.message_count,
            "created_at": neg.created_at,
            "updated_at": neg.updated_at,
            "contact_name": None
        }
        if neg.contact_id:
            contact = await db.get(Contact, neg.contact_id)
            if contact:
                neg_dict["contact_name"] = contact.name
        response.append(neg_dict)
    
    return response


@router.post("", response_model=NegotiationActionResponse, status_code=201)
async def create_negotiation(
    data: NegotiationCreate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language)
):
    """Start a new meeting negotiation with a contact."""
    if not tenant.greenapi_instance_id or not tenant.greenapi_token:
        raise HTTPException(
            status_code=400,
            detail="WhatsApp (GreenAPI) not configured for this tenant"
        )
    
    whatsapp = WhatsAppBotService()
    negotiator = MeetingNegotiator(db, whatsapp, language=lang)
    
    # Get initiator user (tenant owner for now)
    from app.models.user import User
    stmt = select(User).where(
        and_(User.tenant_id == tenant.id, User.role == "owner")
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="No owner user found")
    
    result = await negotiator.initiate_negotiation(
        tenant_id=tenant.id,
        initiator_user_id=user.id,
        contact_name=data.contact_name,
        meeting_title=data.meeting_title,
        meeting_notes=data.meeting_notes,
        days_ahead=data.days_ahead,
        num_slots=data.num_slots,
        whatsapp_instance_id=tenant.greenapi_instance_id,
        whatsapp_token=tenant.greenapi_token
    )
    
    await db.commit()
    
    return NegotiationActionResponse(
        status=result.get("status", "unknown"),
        message=result.get("message", ""),
        negotiation_id=result.get("negotiation_id"),
        proposed_slots=result.get("proposed_slots")
    )


@router.get("/{negotiation_id}", response_model=NegotiationResponse)
async def get_negotiation(
    negotiation_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific negotiation."""
    stmt = select(MeetingNegotiation).where(
        and_(
            MeetingNegotiation.id == negotiation_id,
            MeetingNegotiation.tenant_id == tenant.id
        )
    )
    result = await db.execute(stmt)
    neg = result.scalar_one_or_none()
    
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    
    contact_name = None
    if neg.contact_id:
        contact = await db.get(Contact, neg.contact_id)
        if contact:
            contact_name = contact.name
    
    return {
        "id": neg.id,
        "status": neg.status,
        "meeting_title": neg.meeting_title,
        "meeting_notes": neg.meeting_notes,
        "proposed_slots": neg.proposed_slots,
        "selected_slot": neg.selected_slot,
        "contact_name": contact_name,
        "message_count": neg.message_count,
        "created_at": neg.created_at,
        "updated_at": neg.updated_at
    }


@router.post("/{negotiation_id}/cancel", response_model=NegotiationActionResponse)
async def cancel_negotiation(
    negotiation_id: UUID,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an active negotiation."""
    stmt = select(MeetingNegotiation).where(
        and_(
            MeetingNegotiation.id == negotiation_id,
            MeetingNegotiation.tenant_id == tenant.id
        )
    )
    result = await db.execute(stmt)
    neg = result.scalar_one_or_none()
    
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    
    if not neg.is_active:
        raise HTTPException(status_code=400, detail="Negotiation is not active")
    
    neg.status = NegotiationStatus.CANCELLED.value
    await db.commit()
    
    return NegotiationActionResponse(
        status="cancelled",
        message="Negotiation cancelled",
        negotiation_id=str(neg.id)
    )


@router.post("/{negotiation_id}/confirm", response_model=NegotiationActionResponse)
async def confirm_negotiation(
    negotiation_id: UUID,
    slot_index: int = Query(..., ge=0, le=4, description="Index of slot to confirm"),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language)
):
    """Manually confirm a slot (for when auto-negotiation needs help)."""
    stmt = select(MeetingNegotiation).where(
        and_(
            MeetingNegotiation.id == negotiation_id,
            MeetingNegotiation.tenant_id == tenant.id
        )
    )
    result = await db.execute(stmt)
    neg = result.scalar_one_or_none()
    
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    
    slots = neg.get_proposed_datetimes()
    if slot_index >= len(slots):
        raise HTTPException(status_code=400, detail="Invalid slot index")
    
    selected_slot = slots[slot_index]
    
    whatsapp = WhatsAppBotService()
    negotiator = MeetingNegotiator(db, whatsapp, language=lang)
    
    result = await negotiator._confirm_meeting(
        neg, selected_slot,
        tenant.greenapi_instance_id,
        tenant.greenapi_token
    )
    
    await db.commit()
    
    return NegotiationActionResponse(
        status=result.get("status", "unknown"),
        message=result.get("message", ""),
        negotiation_id=str(neg.id)
    )
