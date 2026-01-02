from __future__ import annotations
"""Application configuration from environment variables."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # App
    app_name: str = "Assistant24"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    
    # Database
    # Database
    database_url: str = "sqlite+aiosqlite:///./digital_secretary.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # Google Gemini AI
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3-flash-preview"
    gemini_thinking_level: str = "medium"  # minimal, low, medium, high
    
    # WhatsApp (Green API Partner)
    green_api_partner_token: Optional[str] = None
    
    # ElevenLabs (Voice transcription)
    elevenlabs_api_key: Optional[str] = None

    # Perplexity AI (Deep Search)
    perplexity_api_key: Optional[str] = None
    
    # Default language
    default_language: str = "ru"  # "ru" or "kz"
    
    # Rate limiting
    rate_limit_requests: int = 100
    
    # Sentry (Error Monitoring)
    sentry_dsn: Optional[str] = None
    
    # Public Domain for Webhooks (Required for GreenAPI)
    base_url: str = "http://localhost:8000"
    
    rate_limit_window: int = 60  # seconds


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
