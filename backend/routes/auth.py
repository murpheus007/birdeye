"""Wallet signature authentication and user settings routes."""
from __future__ import annotations

import secrets
import time

from flask import Blueprint, jsonify, request, session
from solders.pubkey import Pubkey
from solders.signature import Signature

from extensions import db
from models.user_models import User
from utils.session_auth import get_authenticated_user, unauthorized_response


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

    user = User.query.filter_by(wallet_address=wallet_address).first()
    if user is None:
        user = User(wallet_address=wallet_address)
        db.session.add(user)
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

    if webhook is not None:
        webhook = webhook.strip() if isinstance(webhook, str) else ""
        user.discord_webhook_url = webhook or None

    if discord_user_id is not None:
        discord_user_id = discord_user_id.strip() if isinstance(discord_user_id, str) else ""
        user.discord_user_id = discord_user_id or None

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
