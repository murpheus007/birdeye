"""Centralized Birdeye API client with retries and Redis cache."""
from __future__ import annotations

import json
import os
from hashlib import sha256
from typing import Any

import requests
from flask import current_app
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BirdeyeAPIClientError(Exception):
    """Raised when Birdeye API requests fail."""


class BirdeyeRateLimitError(Exception):
    """Raised when Birdeye API rate limit is exceeded (400 Compute Units)."""


class BirdeyeAPIClient:
    """Typed Birdeye API client with cache and resilient transport."""

    # Cache TTLs per endpoint (in seconds)
    CACHE_TTL_PRICE_STATS = 30      # Price/Stats: 30 seconds
    CACHE_TTL_TOKEN_LIST = 300      # Trending/Token Lists: 5 minutes
    CACHE_TTL_OHLCV = 600           # OHLCV (Chart data): 10 minutes
    CACHE_TTL_SEARCH = 300          # Search: 5 minutes
    CACHE_TTL_WHALE = 300           # Whale watch: 5 minutes
    CACHE_TTL_TOKEN_OVERVIEW = 60   # Token overview: 60 seconds

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        redis_client=None,
        timeout_seconds: int = 15,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.redis_client = redis_client
        self.timeout_seconds = timeout_seconds
        self.default_ttl = 300  # Fallback default

        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _headers(self) -> dict[str, str]:
        headers = {
            "accept": "application/json",
            "x-chain": "solana",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    @staticmethod
    def _cache_key(prefix: str, params: dict[str, Any] | None) -> str:
        encoded = json.dumps(params or {}, sort_keys=True, separators=(",", ":"))
        digest = sha256(encoded.encode("utf-8")).hexdigest()[:16]
        return f"birdeye:{prefix}:{digest}"

    def _get_cached(self, key: str) -> dict[str, Any] | None:
        if not self.redis_client:
            return None
        raw = self.redis_client.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _set_cached(self, key: str, data: dict[str, Any], ttl_seconds: int = 300):
        if not self.redis_client:
            return
        self.redis_client.setex(key, ttl_seconds, json.dumps(data))

    def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        cache_prefix: str | None = None,
        use_cache: bool = False,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        cache_key = None
        if use_cache and cache_prefix:
            cache_key = self._cache_key(cache_prefix, params)
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise BirdeyeAPIClientError(f"Failed to call Birdeye endpoint {endpoint}: {exc}") from exc

        # Handle 400 errors specifically for rate limiting
        if response.status_code == 400:
            response_text = response.text.lower()
            if "usage limit" in response_text or "compute units" in response_text:
                raise BirdeyeRateLimitError(
                    f"Compute Units usage limit exceeded for {endpoint}. Please retry in 60 seconds."
                )
            snippet = response.text[:500]
            raise BirdeyeAPIClientError(
                f"Birdeye API error {response.status_code} for {endpoint}: {snippet}"
            )

        if response.status_code >= 400:
            snippet = response.text[:500]
            raise BirdeyeAPIClientError(
                f"Birdeye API error {response.status_code} for {endpoint}: {snippet}"
            )

        payload = response.json()
        if cache_key:
            # Use provided TTL or fall back to default
            cache_ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
            self._set_cached(cache_key, payload, cache_ttl)
        return payload

    def get_trending_tokens(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch trending tokens with 5-minute Redis cache."""
        return self._request(
            endpoint="/defi/token_trending",
            params=params,
            cache_prefix="trending_tokens",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_TOKEN_LIST,
        )

    def get_meme_tokens(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch meme token list with 5-minute Redis cache."""
        return self._request(
            endpoint="/defi/v3/token/meme/list",
            params=params,
            cache_prefix="meme_list",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_TOKEN_LIST,
        )

    def search(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Search tokens/pairs for command palette with 5-minute cache."""
        return self._request(
            endpoint="/defi/v3/search",
            params=params,
            cache_prefix="search",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_SEARCH,
        )

    def get_token_overview(self, address: str) -> dict[str, Any]:
        """Fetch token overview data for war room header metrics with 60-second cache."""
        return self._request(
            endpoint="/defi/token_overview",
            params={"address": address},
            cache_prefix="token_overview",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_TOKEN_OVERVIEW,
        )

    def get_price_stats_single(self, address: str, list_timeframe: str = "1m,1h,24h") -> dict[str, Any]:
        """Fetch price stats snapshots with 30-second cache for real-time accuracy."""
        return self._request(
            endpoint="/defi/v3/price/stats/single",
            params={"address": address, "list_timeframe": list_timeframe},
            cache_prefix="price_stats_single",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_PRICE_STATS,
        )

    def get_token_trade_data_single(self, address: str) -> dict[str, Any]:
        """Fetch detailed trade activity metrics with 60-second cache."""
        return self._request(
            endpoint="/defi/v3/token/trade-data/single",
            params={"address": address},
            cache_prefix="token_trade_data_single",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_TOKEN_OVERVIEW,
        )

    def get_all_time_trades_single(self, address: str) -> dict[str, Any]:
        """Fetch all-time trade summary statistics with 60-second cache."""
        return self._request(
            endpoint="/defi/v3/all-time/trades/single",
            params={"address": address},
            cache_prefix="all_time_trades_single",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_TOKEN_OVERVIEW,
        )

    def get_token_price(self, address: str) -> dict[str, Any]:
        """Fetch token price with 30-second cache (Market Radar)."""
        return self._request(
            endpoint="/defi/price",
            params={"address": address},
            cache_prefix="mkt_token_price",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_PRICE_STATS,
        )

    def get_ohlcv(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch OHLCV data for price breakouts and volume spikes with 10-minute cache."""
        return self._request(
            endpoint="/defi/ohlcv",
            params=params,
            cache_prefix="ohlcv_data",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_OHLCV,
        )

    def get_traders_gainers_losers(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch Whale Watch data with 5-minute cache."""
        return self._request(
            endpoint="/trader/gainers-losers",
            params=params,
            cache_prefix="whale_watch",
            use_cache=True,
            ttl_seconds=self.CACHE_TTL_WHALE,
        )

    async def batch_fetch_prices_async(self, addresses: list[str], max_concurrent: int = 5) -> dict[str, float | None]:
        """
        Batch-simulate multi_price by polling individual prices with async/await.
        Respects rate limits by limiting concurrent requests.
        Returns dict mapping address -> price or None.
        """
        import asyncio
        prices: dict[str, float | None] = {}
        
        async def fetch_one(addr: str) -> tuple[str, float | None]:
            try:
                result = self.get_token_price(addr)
                data = result.get("data") or {}
                value = data.get("value")
                return addr, float(value) if value is not None else None
            except Exception:
                return addr, None
        
        semaphore = asyncio.Semaphore(max_concurrent)
        async def bounded_fetch(addr: str) -> tuple[str, float | None]:
            async with semaphore:
                return await fetch_one(addr)
        
        tasks = [bounded_fetch(addr) for addr in addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, tuple):
                addr, price = result
                prices[addr] = price
            # on exception, prices dict already has the key mapped as None
        
        return prices


def get_birdeye_api_client() -> BirdeyeAPIClient:
    """Return singleton Birdeye client attached to Flask app extensions."""
    client = current_app.extensions.get("birdeye_api_client")
    if client is not None:
        return client

    client = BirdeyeAPIClient(
        base_url=current_app.config.get("BIRDEYE_API_BASE_URL", "https://public-api.birdeye.so"),
        api_key=current_app.config.get("BIRDEYE_API_KEY") or os.getenv("BIRDEYE_API_KEY"),
        redis_client=current_app.extensions.get("redis_client"),
        timeout_seconds=current_app.config.get("BIRDEYE_TIMEOUT_SECONDS", 15),
    )
    current_app.extensions["birdeye_api_client"] = client
    return client
