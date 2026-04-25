"""Birdeye API gateway client with Redis caching."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import requests
from flask import current_app


class BirdeyeGatewayError(Exception):
    """Base error from Birdeye gateway calls."""


class BirdeyeRateLimitError(BirdeyeGatewayError):
    """Raised when Birdeye returns HTTP 429."""

    def __init__(self, message: str, retry_after: int, stale_data: dict[str, Any] | None = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.stale_data = stale_data


@dataclass
class BirdeyeResult:
    """Result wrapper for gateway responses."""

    data: dict[str, Any]
    from_cache: bool = False


class BirdeyeGatewayClient:
    """Client responsible for external Birdeye calls and caching."""

    def __init__(
        self,
        api_base_url: str,
        api_key: str | None,
        redis_client=None,
        timeout: int = 15,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.redis_client = redis_client
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {
            "accept": "application/json",
            "x-chain": "solana",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    @staticmethod
    def _hash_params(params: dict[str, Any] | None) -> str:
        if not params:
            return "no-params"
        encoded = json.dumps(params, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode("utf-8")).hexdigest()[:16]

    def _cache_keys(self, endpoint: str, params: dict[str, Any] | None) -> tuple[str, str]:
        endpoint_key = endpoint.strip("/").replace("/", ":")
        params_hash = self._hash_params(params)
        base = f"birdeye:{endpoint_key}:{params_hash}"
        return base, f"{base}:stale"

    def _load_cache(self, key: str) -> dict[str, Any] | None:
        if not self.redis_client:
            return None
        raw = self.redis_client.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _save_cache(self, key: str, stale_key: str, data: dict[str, Any], ttl: int):
        if not self.redis_client:
            return
        serialized = json.dumps(data)
        self.redis_client.setex(key, ttl, serialized)
        # Keep a stale backup for graceful fallbacks on 429s.
        self.redis_client.setex(stale_key, ttl * 3, serialized)

    def fetch(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        ttl_seconds: int = 300,
        cache_enabled: bool = False,
    ) -> BirdeyeResult:
        """Fetch endpoint data, optionally using Redis caching."""
        cache_key = stale_key = ""
        if cache_enabled:
            cache_key, stale_key = self._cache_keys(endpoint, params)
            cached = self._load_cache(cache_key)
            if cached is not None:
                return BirdeyeResult(data=cached, from_cache=True)

        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        response = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "60"))
            stale_data = self._load_cache(stale_key) if cache_enabled else None
            raise BirdeyeRateLimitError(
                message="Birdeye rate limit exceeded",
                retry_after=retry_after,
                stale_data=stale_data,
            )

        if response.status_code >= 500:
            raise BirdeyeGatewayError("Birdeye service unavailable")

        if response.status_code >= 400:
            raise BirdeyeGatewayError(f"Birdeye request failed with status {response.status_code}")

        payload = response.json()

        if cache_enabled:
            self._save_cache(cache_key, stale_key, payload, ttl_seconds)

        return BirdeyeResult(data=payload, from_cache=False)


def get_birdeye_client() -> BirdeyeGatewayClient:
    """Get or initialize a request-scoped Birdeye client from app extensions."""
    client = current_app.extensions.get("birdeye_client")
    if client is not None:
        return client

    client = BirdeyeGatewayClient(
        api_base_url=current_app.config.get("BIRDEYE_API_BASE_URL", "https://public-api.birdeye.so"),
        api_key=current_app.config.get("BIRDEYE_API_KEY") or os.getenv("BIRDEYE_API_KEY"),
        redis_client=current_app.extensions.get("redis_client"),
        timeout=current_app.config.get("BIRDEYE_TIMEOUT_SECONDS", 15),
    )
    current_app.extensions["birdeye_client"] = client
    return client
