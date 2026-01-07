from __future__ import annotations
"""Security utilities for authentication and authorization."""
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional, Dict
import hmac
import hashlib

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    # Bcrypt has a 72-byte limit, so truncate if necessary
    password_bytes = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.verify(password_bytes, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # Bcrypt has a 72-byte limit, so truncate if necessary
    password_bytes = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password_bytes)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    
    return encoded_jwt


def decode_access_token(token: str) ->Optional[ Dict[str, Any] ]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.error(f"JWT Decode Error: {e}")
        return None


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256"
) -> bool:
    """
    Verify webhook signature using HMAC.

    Args:
        payload: Raw webhook body as bytes
        signature: Signature from webhook header
        secret: Webhook secret key
        algorithm: Hash algorithm (default: sha256)

    Returns:
        True if signature is valid, False otherwise

    Example:
        signature = request.headers.get("X-Webhook-Signature")
        body = await request.body()
        is_valid = verify_webhook_signature(body, signature, tenant.webhook_secret)
    """
    if not signature or not secret:
        logger.warning("Missing signature or secret for webhook validation")
        return False

    try:
        # Compute expected signature
        if algorithm == "sha256":
            expected = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
        elif algorithm == "sha1":
            expected = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha1
            ).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected, signature)

    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}", exc_info=True)
        return False
