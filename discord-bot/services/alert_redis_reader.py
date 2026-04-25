"""Redis-backed alert reader for Discord command flows."""
from __future__ import annotations

import json
import logging
from typing import Any

from services.database_service import DatabaseService
from services.redis_cache import get_redis_cache


logger = logging.getLogger(__name__)


class AlertRedisReader:
    """Read alert rules mirrored into Redis by the Flask backend."""

    def __init__(self, db_service: DatabaseService | None = None):
        self.db = db_service or DatabaseService()

    @staticmethod
    def _alert_key(user_id: int, alert_id: int) -> str:
        return f"alert:user:{user_id}:{alert_id}"

    @staticmethod
    def _alert_index_key(user_id: int) -> str:
        return f"alert:user:{user_id}"

    @staticmethod
    def _alert_ids_key(user_id: int) -> str:
        return f"alert:user:{user_id}:ids"

    async def _redis(self):
        cache = await get_redis_cache()
        return cache.redis

    async def get_alert_rule(self, user_id: int, alert_id: int) -> dict[str, Any] | None:
        redis_client = await self._redis()
        if not redis_client:
            return None

        raw = await redis_client.get(self._alert_key(user_id, alert_id))
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid alert JSON in Redis for user_id=%s alert_id=%s", user_id, alert_id)
            return None

    async def list_alerts_for_user(self, user_id: int) -> list[dict[str, Any]]:
        redis_client = await self._redis()
        if not redis_client:
            return []

        try:
            alert_ids = await redis_client.smembers(self._alert_ids_key(user_id))
            if not alert_ids:
                indexed = await redis_client.hgetall(self._alert_index_key(user_id))
                if indexed:
                    return [self._parse_payload(payload) for payload in indexed.values() if payload]
                return []

            pipeline = redis_client.pipeline(transaction=False)
            for alert_id in sorted(alert_ids, key=lambda item: int(item) if str(item).isdigit() else str(item)):
                pipeline.get(self._alert_key(user_id, int(alert_id)))
            raw_values = await pipeline.execute()

            alerts: list[dict[str, Any]] = []
            for raw in raw_values:
                parsed = self._parse_payload(raw)
                if parsed is not None:
                    alerts.append(parsed)

            alerts.sort(key=lambda item: item.get("created_at") or "", reverse=True)
            return alerts
        except Exception:
            logger.exception("Failed to list alerts from Redis for user_id=%s", user_id)
            return []

    async def list_alerts_by_wallet(self, wallet_address: str) -> list[dict[str, Any]]:
        user_id = self.db.get_user_id_by_wallet(wallet_address)
        if user_id is None:
            return []
        return await self.list_alerts_for_user(user_id)

    @staticmethod
    def _parse_payload(raw: str | None) -> dict[str, Any] | None:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None