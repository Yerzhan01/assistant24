"""API dependencies for authentication and tenant context."""
from __future__ import annotations
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.tenant import Tenant
import logging

logger = logging.getLogger(__name__)


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_tenant(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Tenant:
    """
    Get current authenticated tenant from JWT token.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Decode token
    payload = decode_access_token(credentials.credentials)
    if not payload:
        logger.warning("Auth Failed: Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    tenant_id = payload.get("sub")
    if not tenant_id:
        logger.warning("Auth Failed: No sub in payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    # Get tenant from DB with eager loading
    stmt = select(Tenant).options(
        selectinload(Tenant.module_settings)
    ).where(Tenant.id == UUID(tenant_id))
    
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        logger.warning(f"Auth Failed: Tenant {tenant_id} not found in DB")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant not found"
        )
    
    if not tenant.is_active:
        logger.warning(f"Auth Failed: Tenant {tenant_id} is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is deactivated"
        )
    
    # logger.info(f"API Request from Tenant: {tenant.id}")
    return tenant


async def get_optional_tenant(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) ->Optional[ Tenant ]:
    """
    Try to get current tenant, return None if not authenticated.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_tenant(credentials, db)
    except HTTPException:
        return None


def get_language(accept_language: str = Header(default="ru")) -> str:
    """Get preferred language from Accept-Language header."""
    lang = accept_language.lower()[:2]
    return "kz" if lang == "kk" or lang == "kz" else "ru"


# Type aliases for dependency injection
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
OptionalTenant = Annotated[Optional[Tenant], Depends(get_optional_tenant)]
Database = Annotated[AsyncSession, Depends(get_db)]
Language = Annotated[str, Depends(get_language)]
