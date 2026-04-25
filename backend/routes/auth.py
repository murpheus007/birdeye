"""Wallet signature authentication and user settings routes."""
from __future__ import annotations

import secrets
import time

import logging
from flask import current_app, Blueprint, jsonify, request, session
from solders.pubkey import Pubkey
from solders.signature import Signature

from extensions import db
from models.user_models import User
from utils.session_auth import get_authenticated_user, unauthorized_response

logger = logging.getLogger(__name__)


auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

_CHALLENGE_TTL_SECONDS = 300


def _validate_wallet_address(wallet_address: str) -> bool:
    try:
        Pubkey.from_string(wallet_address)
        return True
    except Exception:
        return False


@auth_bp.get("/challenge")
def challenge():
    wallet_address = (request.args.get("wallet_address") or "").strip()
    if not wallet_address:
        return jsonify({"error": "wallet_address is required"}), 400

    if not _validate_wallet_address(wallet_address):
        return jsonify({"error": "Invalid wallet_address"}), 400

    nonce = secrets.token_urlsafe(18)
    issued_at = int(time.time())
    message = (
        "Birdeye Terminal Login\n"
        f"Wallet: {wallet_address}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at}"
    )

    session["auth_challenge"] = {
        "wallet_address": wallet_address,
        "nonce": nonce,
        "issued_at": issued_at,
        "message": message,
    }

    return jsonify(
        {
            "data": {
                "wallet_address": wallet_address,
                "nonce": nonce,
                "issued_at": issued_at,
                "message": message,
            }
        }
    ), 200


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    wallet_address = (payload.get("wallet_address") or "").strip()
    signature = (payload.get("signature") or "").strip()
    message = payload.get("message")

    if not wallet_address or not signature or not message:
        return jsonify({"error": "wallet_address, signature, and message are required"}), 400

    challenge_payload = session.get("auth_challenge") or {}
    if not challenge_payload:
        return jsonify({"error": "No active login challenge"}), 400

    if challenge_payload.get("wallet_address") != wallet_address:
        return jsonify({"error": "Wallet address does not match active challenge"}), 400

    if challenge_payload.get("message") != message:
        return jsonify({"error": "Signed message does not match active challenge"}), 400

    issued_at = int(challenge_payload.get("issued_at") or 0)
    if int(time.time()) - issued_at > _CHALLENGE_TTL_SECONDS:
        session.pop("auth_challenge", None)
        return jsonify({"error": "Login challenge expired"}), 401

    try:
        pubkey = Pubkey.from_string(wallet_address)
        signed = Signature.from_string(signature)
        is_valid = signed.verify(pubkey, message.encode("utf-8"))
    except Exception:
        return jsonify({"error": "Invalid signature payload"}), 400

    if not is_valid:
        return jsonify({"error": "Signature verification failed"}), 401

    discord_user_id = (payload.get("discord_user_id") or "").strip()

    # 1. Check if user exists by wallet_address
    user = User.query.filter_by(wallet_address=wallet_address).first()

    if user:
        # User exists. If discord_user_id provided, ensure it's linked correctly.
        if discord_user_id:
            existing_discord_user = User.query.filter_by(discord_user_id=discord_user_id).first()
            if existing_discord_user and existing_discord_user.id != user.id:
                # Merge: This Discord ID belongs to another user record. 
                # Move this wallet and all its alerts/watchlist to that record.
                logger.info("Merging user %s into %s due to Discord ID link", user.id, existing_discord_user.id)
                
                # Move relations
                for rule in user.alert_rules:
                    rule.user_id = existing_discord_user.id
                for item in user.watchlist_items:
                    item.user_id = existing_discord_user.id
                
                # Free the wallet_address from the current (to-be-deleted) user
                db.session.delete(user)
                db.session.flush()
                
                user = existing_discord_user
                user.wallet_address = wallet_address
            else:
                user.discord_user_id = discord_user_id
    else:
        # 2. Wallet not found. Check if we can find by discord_user_id instead.
        if discord_user_id:
            user = User.query.filter_by(discord_user_id=discord_user_id).first()
            if user:
                # Found by Discord! Link this new wallet to this user.
                logger.info("Linking new wallet %s to existing Discord user %s", wallet_address, user.id)
                user.wallet_address = wallet_address
        
        # 3. Create new user if still not found
        if not user:
            logger.info("Creating new user for wallet %s", wallet_address)
            user = User(wallet_address=wallet_address, discord_user_id=discord_user_id or None)
            db.session.add(user)

    db.session.flush()

    # 4. Redis Sync: Set source of truth mapping Discord -> User ID
    if user.discord_user_id:
        redis_client = current_app.extensions.get("redis_client")
        if redis_client:
            try:
                redis_client.set(f"discord_to_user:{user.discord_user_id}", user.id)
                logger.info("Synced discord_to_user:%s -> %s to Redis", user.discord_user_id, user.id)
            except Exception:
                logger.error("Failed to sync discord_to_user to Redis in login")

    db.session.commit()

    session["user_id"] = user.id
    session["wallet_address"] = user.wallet_address
    session.pop("auth_challenge", None)

    return jsonify({"data": {"authenticated": True, "user": user.to_dict()}}), 200


@auth_bp.post("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("wallet_address", None)
    session.pop("auth_challenge", None)
    return jsonify({"data": {"authenticated": False}}), 200


@auth_bp.get("/me")
def me():
    user = get_authenticated_user()
    if user is None:
        return jsonify({"data": {"authenticated": False, "user": None}}), 200

    return jsonify({"data": {"authenticated": True, "user": user.to_dict()}}), 200


@auth_bp.get("/settings")
def get_settings():
    user = get_authenticated_user()
    if user is None:
        return unauthorized_response()

    return jsonify(
        {
            "data": {
                "wallet_address": user.wallet_address,
                "discord_webhook_url": user.discord_webhook_url,
                "discord_user_id": user.discord_user_id,
            }
        }
    ), 200


@auth_bp.put("/settings")
def update_settings():
    user = get_authenticated_user()
    if user is None:
        return unauthorized_response()

    payload = request.get_json(silent=True) or {}
    webhook = payload.get("discord_webhook_url")
    discord_user_id = payload.get("discord_user_id")

    # Handle Discord User ID first because it might cause a user merge/switch
    if discord_user_id is not None:
        discord_user_id = discord_user_id.strip() if isinstance(discord_user_id, str) else ""
        if discord_user_id:
            # Check if this Discord ID is already linked to another wallet
            existing_user = User.query.filter_by(discord_user_id=discord_user_id).first()
            if existing_user and existing_user.id != user.id:
                # Merge: Current wallet moves to the record that already has this Discord ID
                # This ensures alerts stay tied to the Discord identity.
                current_wallet = user.wallet_address
                
                logger.info("Merging user %s into %s during settings update", user.id, existing_user.id)
                
                # Move relations from the current session user to the existing Discord user
                for rule in user.alert_rules:
                    rule.user_id = existing_user.id
                for item in user.watchlist_items:
                    item.user_id = existing_user.id
                
                # Delete the current (likely new/temporary) user record to free the wallet_address
                db.session.delete(user)
                db.session.flush() # Release wallet_address constraint
                
                user = existing_user
                user.wallet_address = current_wallet
                
                # Update session to point to the correct user record
                session["user_id"] = user.id
                session["wallet_address"] = user.wallet_address
            else:
                user.discord_user_id = discord_user_id
        else:
            user.discord_user_id = None

    # Now update other settings on the (possibly new) 'user' object
    if webhook is not None:
        webhook = webhook.strip() if isinstance(webhook, str) else ""
        user.discord_webhook_url = webhook or None

    db.session.flush()

    if user.discord_user_id:
        redis_client = current_app.extensions.get("redis_client")
        if not redis_client:
            db.session.rollback()
            return jsonify({"error": "Redis client unavailable"}), 500
        try:
            redis_client.set(f"discord_to_user:{user.discord_user_id}", user.id)
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Redis sync failed"}), 500

    db.session.commit()

    return jsonify(
        {
            "data": {
                "wallet_address": user.wallet_address,
                "discord_webhook_url": user.discord_webhook_url,
                "discord_user_id": user.discord_user_id,
            }
        }
    ), 200
