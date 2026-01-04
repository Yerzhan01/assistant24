from __future__ import annotations
from typing import Optional
from redis import asyncio as aioredis
from app.core.config import settings

class RedisClient:
    _instance: Optional[aioredis.Redis] = None

    @classmethod
    def get_client(cls) -> aioredis.Redis:
        if cls._instance is None:
            cls._instance = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return cls._instance

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
