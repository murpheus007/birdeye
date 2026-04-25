"""Redis helpers for mirroring alert rules for the Discord bot."""
from __future__ import annotations

import json
import logging

from flask import current_app

from models.user_models import AlertRule


logger = logging.getLogger(__name__)


def alert_rule_key(user_id: int, alert_id: int) -> str:
    return f"alert:user:{user_id}:{alert_id}"


def alert_user_index_key(user_id: int) -> str:
    return f"alert:user:{user_id}"


def alert_user_ids_key(user_id: int) -> str:
    return f"alert:user:{user_id}:ids"


def _get_redis_client(redis_client=None):
    if redis_client is not None:
        return redis_client
    return current_app.extensions.get("redis_client")


def _serialize_alert_rule(alert_rule: AlertRule) -> str:
    return json.dumps(alert_rule.to_dict(), sort_keys=True, separators=(",", ":"))


def store_alert_rule_in_redis(alert_rule: AlertRule, redis_client=None, discord_user_id: str | None = None) -> bool:
    """Mirror an alert rule in Redis for bot consumption."""

    client = _get_redis_client(redis_client)
    if client is None:
        logger.warning(
            "Redis unavailable; alert rule %s for user %s persisted in DB only",
            alert_rule.id,
            alert_rule.user_id,
        )
        return False

    base_payload = alert_rule.to_dict()
    if discord_user_id:
        base_payload["discord_user_id"] = discord_user_id

    payload = json.dumps(base_payload, sort_keys=True, separators=(",", ":"))
    per_alert_key = alert_rule_key(alert_rule.user_id, alert_rule.id)
    user_index_key = alert_user_index_key(alert_rule.user_id)
    user_ids_key = alert_user_ids_key(alert_rule.user_id)

    try:
        pipeline = client.pipeline(transaction=False)
        pipeline.set(per_alert_key, payload)
        pipeline.hset(user_index_key, str(alert_rule.id), payload)
        pipeline.sadd(user_ids_key, alert_rule.id)
        pipeline.execute()
        client.publish("test_alerts", payload)
        logger.info(
            "Mirrored alert rule %s for user %s to Redis keys %s, %s, %s",
            alert_rule.id,
            alert_rule.user_id,
            per_alert_key,
            user_index_key,
            user_ids_key,
        )
        return True
    except Exception:
        logger.exception(
            "Failed to mirror alert rule %s for user %s to Redis",
            alert_rule.id,
            alert_rule.user_id,
        )
        return False


def remove_alert_rule_from_redis(user_id: int, alert_id: int, redis_client=None) -> bool:
    """Remove mirrored alert rule data from Redis after delete."""

    client = _get_redis_client(redis_client)
    if client is None:
        logger.warning("Redis unavailable; skipped cleanup for alert rule %s user %s", alert_id, user_id)
        return False

    per_alert_key = alert_rule_key(user_id, alert_id)
    user_index_key = alert_user_index_key(user_id)
    user_ids_key = alert_user_ids_key(user_id)

    try:
        pipeline = client.pipeline(transaction=False)
        pipeline.delete(per_alert_key)
        pipeline.hdel(user_index_key, str(alert_id))
        pipeline.srem(user_ids_key, alert_id)
        pipeline.execute()
        logger.info(
            "Removed alert rule %s for user %s from Redis keys %s, %s, %s",
            alert_id,
            user_id,
            per_alert_key,
            user_index_key,
            user_ids_key,
        )
        return True
    except Exception:
        logger.exception("Failed to remove alert rule %s for user %s from Redis", alert_id, user_id)
        return False