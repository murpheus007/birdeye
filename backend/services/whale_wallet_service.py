"""Whale wallet detail service powered by native Solana RPC."""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from hashlib import sha256
from typing import Any

import requests
from flask import current_app


class WhaleWalletServiceError(Exception):
    """Raised when whale wallet analysis fails."""


class WhaleWalletService:
    """Fetch and summarize whale wallet activity from Solana RPC."""

    def __init__(self, rpc_url: str | None = None, timeout_seconds: int = 15, redis_client=None, cache_ttl_seconds: int = 90):
        self.rpc_url = rpc_url or os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.timeout_seconds = timeout_seconds
        self.redis_client = redis_client
        self.cache_ttl_seconds = cache_ttl_seconds

    def _cache_key(self, wallet_address: str, limit: int) -> str:
        digest = sha256(f"{wallet_address}:{limit}".encode("utf-8")).hexdigest()[:16]
        return f"whale_wallet:{digest}"

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

    def _set_cached(self, key: str, payload: dict[str, Any]):
        if not self.redis_client:
            return
        self.redis_client.setex(key, self.cache_ttl_seconds, json.dumps(payload))

    def _rpc_call(self, method: str, params: list[Any], retries: int = 3) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                response = requests.post(self.rpc_url, json=payload, timeout=self.timeout_seconds)
                if response.status_code == 429:
                    if attempt < retries - 1:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    raise WhaleWalletServiceError("RPC request failed: 429 Too Many Requests")

                response.raise_for_status()
                data = response.json()
            except requests.RequestException as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise WhaleWalletServiceError(f"RPC request failed: {exc}") from exc

            if data.get("error"):
                raise WhaleWalletServiceError(f"RPC error for {method}: {data['error']}")

            return data.get("result")

        raise WhaleWalletServiceError(f"RPC request failed: {last_error}")

    @staticmethod
    def _extract_token_deltas(tx: dict[str, Any], wallet_address: str) -> dict[str, float]:
        meta = tx.get("meta") or {}
        pre = meta.get("preTokenBalances") or []
        post = meta.get("postTokenBalances") or []

        by_mint: dict[str, float] = defaultdict(float)

        def token_amount(entry: dict[str, Any]) -> float:
            raw = (entry.get("uiTokenAmount") or {}).get("uiAmount")
            return float(raw) if raw is not None else 0.0

        for entry in pre:
            if entry.get("owner") == wallet_address:
                mint = entry.get("mint")
                if mint:
                    by_mint[mint] -= token_amount(entry)

        for entry in post:
            if entry.get("owner") == wallet_address:
                mint = entry.get("mint")
                if mint:
                    by_mint[mint] += token_amount(entry)

        return {mint: delta for mint, delta in by_mint.items() if abs(delta) > 0}

    def get_wallet_detail(self, wallet_address: str, limit: int = 25) -> dict[str, Any]:
        """Return wallet activity summary and recent token deltas."""
        capped_limit = max(5, min(limit, 50))
        tx_fetch_cap = min(capped_limit, 10)
        cache_key = self._cache_key(wallet_address, capped_limit)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        signatures = self._rpc_call(
            "getSignaturesForAddress",
            [wallet_address, {"limit": capped_limit}],
        )

        if not signatures:
            payload = {
                "wallet": wallet_address,
                "summary": {
                    "total_transactions": 0,
                    "buy_count": 0,
                    "sell_count": 0,
                    "neutral_count": 0,
                    "tokens_touched": 0,
                },
                "recent_activity": [],
            }
            self._set_cached(cache_key, payload)
            return payload

        activity: list[dict[str, Any]] = []
        buy_count = 0
        sell_count = 0
        neutral_count = 0
        tokens_touched: set[str] = set()

        for index, row in enumerate(signatures):
            signature = row.get("signature")
            if not signature:
                continue

            token_deltas: dict[str, float] = {}
            primary_mint = "SOL"
            primary_delta = 0.0
            block_time = row.get("blockTime")
            fee_lamports = 0
            status = "success" if row.get("err") is None else "failed"

            if index < tx_fetch_cap:
                try:
                    tx = self._rpc_call(
                        "getTransaction",
                        [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
                    )
                except WhaleWalletServiceError:
                    tx = None

                if tx:
                    token_deltas = self._extract_token_deltas(tx, wallet_address)
                    if token_deltas:
                        primary_mint, primary_delta = max(token_deltas.items(), key=lambda item: abs(item[1]))
                        tokens_touched.update(token_deltas.keys())
                    meta = tx.get("meta") or {}
                    block_time = tx.get("blockTime") or block_time
                    fee_lamports = meta.get("fee", 0)
                    status = "success" if meta.get("err") is None else "failed"

            if primary_delta > 0:
                side = "buy"
                buy_count += 1
            elif primary_delta < 0:
                side = "sell"
                sell_count += 1
            else:
                side = "neutral"
                neutral_count += 1

            activity.append(
                {
                    "signature": signature,
                    "timestamp": block_time,
                    "side": side,
                    "token_address": primary_mint,
                    "token_delta": primary_delta,
                    "fee_lamports": fee_lamports,
                    "status": status,
                }
            )

        payload = {
            "wallet": wallet_address,
            "summary": {
                "total_transactions": len(activity),
                "buy_count": buy_count,
                "sell_count": sell_count,
                "neutral_count": neutral_count,
                "tokens_touched": len(tokens_touched),
            },
            "recent_activity": activity,
        }
        self._set_cached(cache_key, payload)
        return payload


def get_whale_wallet_service() -> WhaleWalletService:
    """Factory for whale wallet detail service."""
    client = current_app.extensions.get("whale_wallet_service")
    if client is not None:
        return client

    client = WhaleWalletService(
        rpc_url=current_app.config.get("SOLANA_RPC_URL") or os.getenv("SOLANA_RPC_URL"),
        timeout_seconds=current_app.config.get("BIRDEYE_TIMEOUT_SECONDS", 15),
        redis_client=current_app.extensions.get("redis_client"),
        cache_ttl_seconds=int(os.getenv("WHALE_WALLET_CACHE_TTL_SECONDS", "90")),
    )
    current_app.extensions["whale_wallet_service"] = client
    return client
