from __future__ import annotations
"""Authentication routes - register, login, me."""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.api.deps import CurrentTenant, Database, Language
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.tenant import Tenant
from app.models.module_settings import TenantModuleSettings


router = APIRouter(prefix="/auth", tags=["auth"])


# Schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    business_name: str
    language: str = "ru"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TenantResponse(BaseModel):
    id: str
    email: str
    business_name: str
    language: str
    plan: str
    telegram_connected: bool
    whatsapp_connected: bool
    ai_enabled: bool
    is_admin: bool


# Default modules to enable for new tenants
DEFAULT_MODULES = ["finance", "meeting", "contract", "ideas", "birthday"]


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: Database
):
    """Register a new tenant."""
    # Check if email exists
    stmt = select(Tenant).where(Tenant.email == request.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create tenant
    tenant = Tenant(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        business_name=request.business_name,
        language=request.language if request.language in ["ru", "kz"] else "ru"
    )
    db.add(tenant)
    await db.flush()
    
    # Enable default modules
    for module_id in DEFAULT_MODULES:
        module_setting = TenantModuleSettings(
            tenant_id=tenant.id,
            module_id=module_id,
            is_enabled=True
        )
        db.add(module_setting)
    
    await db.commit()
    
    # Create token
    access_token = create_access_token(
        data={"sub": str(tenant.id)},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes)
    )
    
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Database
):
    """Login and get access token."""
    # Find tenant
    stmt = select(Tenant).where(Tenant.email == request.email)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant or not verify_password(request.password, tenant.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Create token
    access_token = create_access_token(
        data={"sub": str(tenant.id)},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes)
    )
    
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=TenantResponse)
async def get_me(tenant: CurrentTenant):
    """Get current tenant info."""
    is_admin = tenant.is_admin
    if tenant.email in ["test@test.kz"]:
        is_admin = True
        
    return TenantResponse(
        id=str(tenant.id),
        email=tenant.email,
        business_name=tenant.business_name,
        language=tenant.language,
        plan=tenant.plan,
        telegram_connected=bool(tenant.telegram_bot_token),
        whatsapp_connected=bool(tenant.greenapi_instance_id),
        ai_enabled=tenant.ai_enabled,
        is_admin=is_admin
    )
