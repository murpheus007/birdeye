"""Birdeye API client for Discord bot interactive commands."""
from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp

try:
    from .birdeye_error_handler import BirdeyeErrorResponse
except ImportError:
    from birdeye_error_handler import BirdeyeErrorResponse


logger = logging.getLogger(__name__)



class BirdeyeApiClient:
    """Small async client wrapper for Birdeye endpoints used by Discord commands."""

    def __init__(self):
        self.base_url = os.getenv("BIRDEYE_API_BASE_URL", "https://public-api.birdeye.so").rstrip("/")
        self.api_key = os.getenv("BIRDEYE_API_KEY", "")
        self.session: aiohttp.ClientSession | None = None

    async def _get_cache(self):
        """Lazy-import and get Redis cache instance."""
        try:
            from .redis_cache import get_redis_cache
            return await get_redis_cache()
        except Exception:
            logger.debug("Redis cache unavailable; operating without caching")
            return None

    async def ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def request(self, endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any] | None:
        # Build cache key from endpoint and params
        cache_key = f"{endpoint}:{str(sorted(params.items()) if params else '')}"
        
        # Try cache first for supported endpoints
        cache_ttl = self._get_cache_ttl(endpoint)
        if cache_ttl > 0:
            cache = await self._get_cache()
            if cache:
                from .redis_cache import make_cache_key
                full_key = make_cache_key(cache_key)
                cached = await cache.get(full_key)
                if cached:
                    logger.debug(f"Cache hit for endpoint={endpoint}")
                    return cached
        
        await self.ensure_session()
        headers = {"accept": "application/json", "x-chain": "solana"}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key

        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.get(url, params=params or {}, headers=headers, timeout=20) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    # Check if this is a compute units error
                    if BirdeyeErrorResponse.is_compute_units_error(resp.status, body):
                        logger.warning("Birdeye compute units limit exceeded: status=%s endpoint=%s", resp.status, endpoint)
                        return BirdeyeErrorResponse.get_throttled_response()
                    
                    logger.warning("Birdeye call failed status=%s endpoint=%s body=%s", resp.status, endpoint, body)
                    return None
                
                result = await resp.json()
                
                # Store in cache if cacheable
                if cache_ttl > 0 and result:
                    cache = await self._get_cache()
                    if cache:
                        from .redis_cache import make_cache_key
                        full_key = make_cache_key(cache_key)
                        await cache.set(full_key, result, cache_ttl)
                        logger.debug(f"Cache store for endpoint={endpoint} ttl={cache_ttl}s")
                
                return result
        except Exception:
            logger.exception("Birdeye call failed endpoint=%s", endpoint)
            return None
    
    def _get_cache_ttl(self, endpoint: str) -> int:
        """Determine cache TTL (seconds) based on endpoint type. 0 = no cache."""
        # Price/Stats endpoints: 30s
        if any(x in endpoint for x in ["/defi/price", "/defi/token_overview", "/defi/token_security"]):
            return 30
        
        # Token Lists: 5m (300s)
        if any(x in endpoint for x in ["/defi/token_trending", "/trader/gainers-losers"]):
            return 300
        
        # OHLCV: 10m (600s)
        if "/ohlcv" in endpoint:
            return 600
        
        # No cache for other endpoints
        return 0

    async def get_trending_tokens(self, limit: int = 5) -> list[dict[str, Any]]:
        payload = await self.request(
            "/defi/token_trending",
            {"sort_by": "rank", "sort_type": "asc", "offset": "0", "limit": str(limit)},
        )
        return (((payload or {}).get("data") or {}).get("tokens") or [])[:limit]

    async def get_whales_snapshot(self, timeframe: str = "24h", limit: int = 5) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        payload = await self.request("/trader/gainers-losers", {"timeframe": timeframe, "limit": str(limit)})
        data = (payload or {}).get("data") or {}
        gainers = (data.get("gainers") or [])[:limit]
        losers = (data.get("losers") or [])[:limit]
        return gainers, losers

    async def get_token_price_overview(self, token_address: str) -> dict[str, Any] | None:
        """Fetch current price and 24h price change for a single token."""
        payload = await self.request("/defi/token_overview", {"address": token_address})
        data = (payload or {}).get("data") or {}
        if not data:
            return None
        price = data.get("price")
        price_change = data.get("priceChange24hPercent") or data.get("priceChange24h")
        return {"price": price, "priceChange24h": price_change}
