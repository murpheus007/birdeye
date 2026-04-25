"""On-demand Birdeye lookup helpers with strict Redis TTL caching."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Literal

import aiohttp

from .birdeye_error_handler import BirdeyeErrorResponse
from .redis_cache import get_redis_cache, make_cache_key

logger = logging.getLogger(__name__)

BirdeyeSource = Literal["live", "cached"]

PRICE_TTL_SECONDS = 300
TOKEN_SECURITY_TTL_SECONDS = 3600
OHLCV_TTL_SECONDS = 600
TRENDING_TTL_SECONDS = 300
WHALES_TTL_SECONDS = 300


@dataclass(slots=True)
class BirdeyeFetchResult:
    """Birdeye payload plus cache metadata for user-facing transparency."""

    data: Any | None
    source: BirdeyeSource
    ttl_seconds: int | None
    cache_key: str
    message: str | None = None

    @property
    def is_throttled(self) -> bool:
        return self.message == BirdeyeErrorResponse.DATA_THROTTLED_MESSAGE

    def cache_notice(self) -> str:
        if self.message:
            return self.message
        if self.source == "cached" and self.ttl_seconds is not None:
            return f"Data cached, expires in {format_duration(self.ttl_seconds)}."
        return "Fetched live from Birdeye."


class BirdeyeLookupService:
    """Reusable async Birdeye client for on-demand Discord command handlers."""

    def __init__(self):
        self.base_url = os.getenv("BIRDEYE_API_BASE_URL", "https://public-api.birdeye.so").rstrip("/")
        self.api_key = os.getenv("BIRDEYE_API_KEY", "")
        self.session: aiohttp.ClientSession | None = None

    async def ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def _request_json(
        self,
        endpoint: str,
        params: dict[str, str],
        cache_ttl: int,
    ) -> BirdeyeFetchResult:
        cache_key = make_cache_key("birdeye", endpoint, self._params_key(params))
        cache = await get_redis_cache()

        cached_payload = await cache.get(cache_key)
        if cached_payload is not None:
            ttl_seconds = await cache.ttl(cache_key)
            return BirdeyeFetchResult(
                data=cached_payload,
                source="cached",
                ttl_seconds=ttl_seconds,
                cache_key=cache_key,
            )

        await self.ensure_session()
        headers = {"accept": "application/json", "x-chain": "solana"}
        if self.api_key:
            headers["X-API-KEY"] = self.api_key

        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.get(url, params=params, headers=headers, timeout=20) as resp:
                body_text = await resp.text()
                if resp.status >= 400:
                    if BirdeyeErrorResponse.is_compute_units_error(resp.status, body_text):
                        logger.warning("Birdeye compute units limit exceeded: endpoint=%s", endpoint)
                        return BirdeyeFetchResult(
                            data=None,
                            source="live",
                            ttl_seconds=None,
                            cache_key=cache_key,
                            message=BirdeyeErrorResponse.DATA_THROTTLED_MESSAGE,
                        )
                    logger.warning("Birdeye request failed status=%s endpoint=%s body=%s", resp.status, endpoint, body_text[:500])
                    return BirdeyeFetchResult(
                        data=None,
                        source="live",
                        ttl_seconds=None,
                        cache_key=cache_key,
                        message=f"Birdeye request failed ({resp.status}).",
                    )

                try:
                    payload = await resp.json()
                except Exception:
                    logger.warning("Birdeye returned non-JSON payload for endpoint=%s", endpoint)
                    return BirdeyeFetchResult(
                        data=None,
                        source="live",
                        ttl_seconds=None,
                        cache_key=cache_key,
                        message="Birdeye returned an unreadable response.",
                    )

                if cache_ttl > 0:
                    await cache.set(cache_key, payload, cache_ttl)
                return BirdeyeFetchResult(
                    data=payload,
                    source="live",
                    ttl_seconds=cache_ttl,
                    cache_key=cache_key,
                )
        except Exception:
            logger.exception("Birdeye call failed endpoint=%s", endpoint)
            return BirdeyeFetchResult(
                data=None,
                source="live",
                ttl_seconds=None,
                cache_key=cache_key,
                message="Birdeye request failed unexpectedly.",
            )

    @staticmethod
    def _params_key(params: dict[str, str]) -> str:
        return "|".join(f"{key}={value}" for key, value in sorted(params.items()))

    async def fetch_price(self, token_address: str) -> BirdeyeFetchResult:
        return await self._request_json("/defi/price", {"address": token_address}, PRICE_TTL_SECONDS)

    async def fetch_token_security(self, token_address: str) -> BirdeyeFetchResult:
        return await self._request_json("/defi/token_security", {"address": token_address}, TOKEN_SECURITY_TTL_SECONDS)

    async def fetch_ohlcv(
        self,
        token_address: str,
        timeframe: str = "1H",
        time_from: int | None = None,
        time_to: int | None = None,
    ) -> BirdeyeFetchResult:
        params = {
            "address": token_address,
            "type": timeframe,
            "currency": "usd",
        }
        if time_from is not None:
            params["time_from"] = str(time_from)
        if time_to is not None:
            params["time_to"] = str(time_to)
        return await self._request_json("/defi/ohlcv", params, OHLCV_TTL_SECONDS)

    async def fetch_trending_tokens(self, limit: int = 5) -> BirdeyeFetchResult:
        params = {"sort_by": "rank", "sort_type": "asc", "offset": "0", "limit": str(limit)}
        return await self._request_json("/defi/token_trending", params, TRENDING_TTL_SECONDS)

    async def fetch_whales_snapshot(self, timeframe: str = "24h", limit: int = 5) -> BirdeyeFetchResult:
        params = {"timeframe": timeframe, "limit": str(limit)}
        return await self._request_json("/trader/gainers-losers", params, WHALES_TTL_SECONDS)


_service: BirdeyeLookupService | None = None


async def get_birdeye_service() -> BirdeyeLookupService:
    global _service
    if _service is None:
        _service = BirdeyeLookupService()
    return _service


async def fetch_price(token_address: str) -> BirdeyeFetchResult:
    service = await get_birdeye_service()
    return await service.fetch_price(token_address)


async def fetch_token_security(token_address: str) -> BirdeyeFetchResult:
    service = await get_birdeye_service()
    return await service.fetch_token_security(token_address)


async def fetch_ohlcv(token_address: str, timeframe: str = "1H", time_from: int | None = None, time_to: int | None = None) -> BirdeyeFetchResult:
    service = await get_birdeye_service()
    return await service.fetch_ohlcv(token_address, timeframe=timeframe, time_from=time_from, time_to=time_to)


async def fetch_trending_tokens(limit: int = 5) -> BirdeyeFetchResult:
    service = await get_birdeye_service()
    return await service.fetch_trending_tokens(limit=limit)


async def fetch_whales_snapshot(timeframe: str = "24h", limit: int = 5) -> BirdeyeFetchResult:
    service = await get_birdeye_service()
    return await service.fetch_whales_snapshot(timeframe=timeframe, limit=limit)


def format_duration(seconds: int) -> str:
    minutes, remainder = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if remainder and not hours:
        parts.append(f"{remainder}s")
    if not parts:
        return "0s"
    return " ".join(parts)
