"""Alert management routes scoped to the authenticated wallet user."""
from __future__ import annotations

import logging
import requests
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, jsonify, request

from extensions import db
from models.user_models import AlertRule
from services.alert_redis_sync import remove_alert_rule_from_redis, store_alert_rule_in_redis
from utils.session_auth import get_authenticated_user, unauthorized_response
from services.discord_embed_service import create_test_embed


alerts_bp = Blueprint("alerts", __name__, url_prefix="/api/v1/alerts")
logger = logging.getLogger(__name__)


@alerts_bp.post("/create")
def create_alert():
    user = get_authenticated_user()
    if user is None:
        return unauthorized_response()

    payload = request.get_json(silent=True) or {}
    token_address = (payload.get("token_address") or "").strip()
    if not token_address:
        return jsonify({"error": "token_address is required"}), 400

    target_price = payload.get("target_price")
    price_change_percent = payload.get("price_change_percent")
    # Legacy field kept for backward compatibility
    volume_spike_percent = payload.get("volume_spike_percent")
    delivery_channel = (payload.get("alert_type") or "webhook").strip().lower()
    alert_description = (payload.get("alert_description") or "").strip() or None
    token_name = (payload.get("token_name") or "").strip() or None
    token_logo_url = (payload.get("token_logo_url") or "").strip() or None

    if target_price is None and price_change_percent is None and volume_spike_percent is None:
        return jsonify({"error": "At least one threshold is required"}), 400

    normalized_price = None
    if target_price is not None and target_price != "":
        try:
            normalized_price = Decimal(str(target_price))
        except (InvalidOperation, ValueError):
            return jsonify({"error": "target_price must be numeric"}), 400

    normalized_price_change = None
    if price_change_percent is not None and price_change_percent != "":
        try:
            normalized_price_change = Decimal(str(price_change_percent))
        except (InvalidOperation, ValueError):
            return jsonify({"error": "price_change_percent must be numeric"}), 400

    normalized_volume_spike = None
    if volume_spike_percent is not None and volume_spike_percent != "":
        try:
            normalized_volume_spike = Decimal(str(volume_spike_percent))
        except (InvalidOperation, ValueError):
            return jsonify({"error": "volume_spike_percent must be numeric"}), 400

    if delivery_channel not in {"webhook", "dm"}:
        return jsonify({"error": "alert_type must be one of webhook or dm"}), 400

    if delivery_channel == "webhook" and not user.discord_webhook_url:
        return jsonify({"error": "discord_webhook_url is required for webhook alerts"}), 400

    if delivery_channel == "dm" and not user.discord_user_id:
        return jsonify({"error": "discord_user_id is required for DM alerts"}), 400

    alert_rule = AlertRule(
        user_id=user.id,
        token_address=token_address,
        token_name=token_name,
        token_logo_url=token_logo_url,
        alert_description=alert_description,
        status="active",
        target_price=normalized_price,
        price_change_percent_threshold=normalized_price_change,
        volume_spike_percent_threshold=normalized_volume_spike,
        delivery_channel=delivery_channel,
        is_active=True,
    )
    try:
        db.session.add(alert_rule)
        db.session.flush()
        if not store_alert_rule_in_redis(alert_rule, discord_user_id=user.discord_user_id):
            raise Exception("Redis sync failed")
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to create alert rule in database for user_id=%s", user.id)
        return jsonify({"error": "Failed to create alert"}), 500

    return jsonify({"data": alert_rule.to_dict()}), 201


@alerts_bp.get("/mine")
def list_my_alerts():
    user = get_authenticated_user()
    if user is None:
        return unauthorized_response()

    rules = (
        AlertRule.query.filter_by(user_id=user.id)
        .order_by(AlertRule.created_at.desc())
        .all()
    )
    return jsonify({"data": [rule.to_dict() for rule in rules]}), 200


@alerts_bp.delete("/<int:alert_id>")
def delete_alert(alert_id: int):
    user = get_authenticated_user()
    if user is None:
        return unauthorized_response()

    rule = AlertRule.query.filter_by(id=alert_id, user_id=user.id).first()
    if rule is None:
        return jsonify({"error": "Alert not found"}), 404

    try:
        db.session.delete(rule)
        db.session.flush()
        if not remove_alert_rule_from_redis(user.id, alert_id):
            raise Exception("Redis sync failed")
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to delete alert rule %s for user_id=%s", alert_id, user.id)
        return jsonify({"error": "Failed to delete alert"}), 500

    return jsonify({"data": {"deleted": True, "id": alert_id}}), 200


@alerts_bp.post("/test")
def test_alert():
    """Send a test alert to verify webhook or DM connection."""
    user = get_authenticated_user()
    if user is None:
        return unauthorized_response()

    payload = request.get_json(silent=True) or {}
    # Prefer values from the request body; fall back to the user's saved profile
    webhook_url = (payload.get("discord_webhook_url") or user.discord_webhook_url or "").strip()
    discord_user_id = (payload.get("discord_user_id") or user.discord_user_id or "").strip()

    logger.info(
        "DEBUG: Test alert triggered for webhook=%s discord_user_id=%s auth_user_id=%s",
        bool(webhook_url),
        discord_user_id or "none",
        getattr(user, "id", "unknown"),
    )

    # Validate that at least one destination is available (request body or saved profile)
    if not webhook_url and not discord_user_id:
        return jsonify({"error": "Please provide a Discord ID or Webhook first."}), 400

    embed = create_test_embed()

    # Test webhook if provided
    if webhook_url:
        try:
            response = requests.post(
                webhook_url,
                json={"embeds": [embed]},
                timeout=10,
            )
            if response.status_code not in (200, 204):
                return jsonify(
                    {"error": f"Webhook failed with status {response.status_code}: {response.text}"}
                ), 400
            return jsonify({"data": {"message": "Test alert sent to webhook successfully"}}), 200
        except requests.exceptions.Timeout:
            return jsonify({"error": "Webhook request timed out"}), 408
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Webhook request failed: {str(e)}"}), 400

    # Test DM if provided
    if discord_user_id:
        try:
            redis_client = current_app.extensions.get("redis_client")
            if redis_client is None:
                logger.warning("Redis client unavailable; cannot publish DM test alert")
                return jsonify({"error": "DM test queue is unavailable right now"}), 503

            queue_payload = {
                "discord_user_id": discord_user_id,
                "source": "backend",
                "auth_user_id": user.id,
            }
            redis_client.publish("test_alerts", __import__("json").dumps(queue_payload))
            logger.info("Published test alert to Redis channel test_alerts for discord_user_id=%s", discord_user_id)

            return jsonify(
                {
                    "data": {
                        "message": f"Test DM queued for user {discord_user_id}. "
                        "The bot will send it if it can reach the user via Redis test_alerts channel."
                    }
                }
            ), 200
        except Exception as e:
            return jsonify({"error": f"DM test failed: {str(e)}"}), 400

    return jsonify({"error": "No valid alert destination provided"}), 400
