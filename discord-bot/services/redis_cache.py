"""
Redis cache manager for Birdeye API responses.
Provides TTL-based caching to reduce API compute unit consumption.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, TypeVar, Generic

from redis import asyncio as aioredis

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RedisCache(Generic[T]):
    """Async Redis cache wrapper with TTL support."""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/1")
        self.redis: aioredis.Redis | None = None

    async def connect(self):
        """Establish Redis connection."""
        if not self.redis:
            try:
                self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                await self.redis.ping()
                logger.info("Redis cache connected successfully")
            except Exception as exc:
                logger.warning("Failed to connect to Redis: %s. Cache will be disabled.", exc)
                self.redis = None

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def get(self, key: str) -> T | None:
        """Retrieve value from cache."""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as exc:
            logger.warning("Cache get failed for key=%s: %s", key, exc)

        return None

    async def ttl(self, key: str) -> int | None:
        """Return remaining TTL for a key, or None when unavailable."""
        if not self.redis:
            return None

        try:
            ttl_value = await self.redis.ttl(key)
            if ttl_value is None or ttl_value < 0:
                return None
            return int(ttl_value)
        except Exception as exc:
            logger.warning("Cache ttl check failed for key=%s: %s", key, exc)
            return None

    async def set(self, key: str, value: T, ttl: int) -> bool:
        """Set value in cache with TTL (in seconds)."""
        if not self.redis:
            return False

        try:
            await self.redis.setex(key, ttl, json.dumps(value))
            return True
        except Exception as exc:
            logger.warning("Cache set failed for key=%s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as exc:
            logger.warning("Cache delete failed for key=%s: %s", key, exc)
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.redis:
            return False

        try:
            return await self.redis.exists(key) > 0
        except Exception as exc:
            logger.warning("Cache exists check failed for key=%s: %s", key, exc)
            return False


# Global cache instance
_cache_instance: RedisCache | None = None


async def get_redis_cache() -> RedisCache:
    """Get or create global Redis cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
        await _cache_instance.connect()
    return _cache_instance


async def shutdown_redis_cache():
    """Shutdown global Redis cache instance."""
    global _cache_instance
    if _cache_instance:
        await _cache_instance.disconnect()
        _cache_instance = None


def make_cache_key(*parts: str) -> str:
    """Create a namespaced cache key."""
    return ":".join(["birdeye"] + list(parts))
