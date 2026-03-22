"""Redis client factories shared by the backend and streaming services."""

from __future__ import annotations

from functools import lru_cache

import redis
from redis.asyncio import Redis as AsyncRedis

from backend.core.config import get_settings


@lru_cache
def get_sync_redis() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache
def get_async_redis() -> AsyncRedis:
    settings = get_settings()
    return AsyncRedis.from_url(settings.redis_url, decode_responses=True)
