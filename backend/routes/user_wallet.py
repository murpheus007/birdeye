"""User and wallet routes backed by SQLAlchemy models."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request

from dto.contracts import WalletPortfolioDTO
from extensions import db
from models.user_models import AlertRule, NotificationHistory, User, WatchlistItem
from services.alert_redis_sync import store_alert_rule_in_redis
from utils.session_auth import get_authenticated_user


user_wallet_bp = Blueprint("user_wallet", __name__, url_prefix="/api/v1/user")


@user_wallet_bp.post("/users")
def create_user():
    payload = request.get_json(silent=True) or {}
    wallet_address = payload.get("wallet_address")
    discord_webhook_url = payload.get("discord_webhook_url")
    discord_user_id = payload.get("discord_user_id")

    if not wallet_address:
        return jsonify({"error": "wallet_address is required"}), 400

    existing = User.query.filter_by(wallet_address=wallet_address).first()
    if existing:
        return jsonify({"error": "user with this wallet_address already exists"}), 409

    user = User(
        wallet_address=wallet_address,
        discord_webhook_url=discord_webhook_url,
        discord_user_id=discord_user_id,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"data": user.to_dict()}), 201


@user_wallet_bp.get("/users/<int:user_id>")
def get_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    response = user.to_dict()
    response["alert_rules"] = [rule.to_dict() for rule in user.alert_rules]
    return jsonify({"data": response}), 200


@user_wallet_bp.post("/alert-rules")
def create_alert_rule():
    payload = request.get_json(silent=True) or {}

    user_id = payload.get("user_id")
    token_address = payload.get("token_address")
    target_price = payload.get("target_price")
    volume_threshold_usd = payload.get("volume_threshold_usd")
    price_change_percent_threshold = payload.get("price_change_percent_threshold")
    include_risk_assessment = bool(payload.get("include_risk_assessment", False))

    if not user_id or not token_address:
        return jsonify({"error": "user_id and token_address are required"}), 400

    if target_price is None and volume_threshold_usd is None and price_change_percent_threshold is None:
        return jsonify({"error": "at least one of target_price, volume_threshold_usd, or price_change_percent_threshold is required"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    normalized_price = None
    if target_price is not None:
        try:
            normalized_price = Decimal(str(target_price))
        except (InvalidOperation, ValueError):
            return jsonify({"error": "target_price must be numeric"}), 400

    rule = AlertRule(
        user_id=user.id,
        token_address=token_address,
        target_price=normalized_price,
        volume_threshold_usd=volume_threshold_usd,
        price_change_percent_threshold=price_change_percent_threshold,
        include_risk_assessment=include_risk_assessment,
        is_active=bool(payload.get("is_active", True)),
    )
    try:
        db.session.add(rule)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to create alert rule"}), 500

    store_alert_rule_in_redis(rule, discord_user_id=user.discord_user_id)

    return jsonify({"data": rule.to_dict()}), 201


def _get_or_create_demo_user(user_id: int | None = None) -> User:
    session_user = get_authenticated_user()
    if session_user is not None:
        return session_user

    if user_id is not None:
        user = User.query.get(user_id)
        if user is not None:
          return user

    user = User.query.order_by(User.id.asc()).first()
    if user is not None:
        return user

    existing_demo = User.query.filter_by(wallet_address="demo-wallet").first()
    if existing_demo is not None:
        return existing_demo

    user = User(wallet_address="demo-wallet", discord_webhook_url="local-demo-webhook")
    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        user = User.query.filter_by(wallet_address="demo-wallet").first()
        if user is not None:
            return user
        raise

    return user


@user_wallet_bp.get("/users/<int:user_id>/alert-rules")
def list_alert_rules(user_id: int):
    rules = AlertRule.query.filter_by(user_id=user_id).order_by(AlertRule.created_at.desc()).all()
    return jsonify({"data": [rule.to_dict() for rule in rules]}), 200


@user_wallet_bp.get("/watchlist")
def list_watchlist():
    user_id = request.args.get("user_id", type=int)
    user = _get_or_create_demo_user(user_id)
    items = WatchlistItem.query.filter_by(user_id=user.id).order_by(WatchlistItem.updated_at.desc()).all()
    return jsonify({"data": [item.to_dict() for item in items]}), 200


@user_wallet_bp.post("/watchlist")
def add_watchlist_item():
    payload = request.get_json(silent=True) or {}
    token_address = payload.get("token_address")
    if not token_address:
        return jsonify({"error": "token_address is required"}), 400

    user_id = payload.get("user_id")
    user = _get_or_create_demo_user(user_id)

    existing = WatchlistItem.query.filter_by(user_id=user.id, token_address=token_address).first()
    if existing:
        existing.token_name = payload.get("token_name") or existing.token_name
        existing.symbol = payload.get("symbol") or existing.symbol
        db.session.commit()
        return jsonify({"data": existing.to_dict(), "status": "updated"}), 200

    item = WatchlistItem(
        user_id=user.id,
        token_address=token_address,
        token_name=payload.get("token_name"),
        symbol=payload.get("symbol"),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"data": item.to_dict(), "status": "created"}), 201


@user_wallet_bp.get("/alert-history")
def alert_history():
    user_id = request.args.get("user_id", type=int)
    limit = request.args.get("limit", default=5, type=int)
    user = _get_or_create_demo_user(user_id)

    rows = (
        NotificationHistory.query.join(AlertRule, NotificationHistory.alert_rule_id == AlertRule.id)
        .filter(AlertRule.user_id == user.id)
        .order_by(NotificationHistory.sent_at.desc())
        .limit(limit)
        .all()
    )

    return jsonify({"data": [row.to_dict() for row in rows]}), 200


@user_wallet_bp.get("/wallet/<wallet_address>/token_list")
def wallet_token_list(wallet_address: str):
    """Deprecated wallet token list route kept for compatibility."""
    return jsonify({"error": "wallet token list is not available on this plan"}), 410


@user_wallet_bp.get("/wallet/<wallet_address>/portfolio")
def wallet_portfolio(wallet_address: str):
    """Return contract-aligned wallet portfolio DTO."""
    dto = WalletPortfolioDTO(
        wallet_address=wallet_address,
        total_value_usd=0.0,
        token_count=0,
        tokens=[],
    )
    return jsonify({"data": dto.model_dump()}), 200
