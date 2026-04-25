"""Helpers for session-backed wallet authentication."""
from __future__ import annotations

from flask import jsonify, session

from models.user_models import User


def get_authenticated_user() -> User | None:
    """Return authenticated user from session or None."""
    user_id = session.get("user_id")
    wallet_address = session.get("wallet_address")

    if not user_id or not wallet_address:
        return None

    user = User.query.get(user_id)
    if user is None:
        session.pop("user_id", None)
        session.pop("wallet_address", None)
        return None

    if user.wallet_address != wallet_address:
        session.pop("user_id", None)
        session.pop("wallet_address", None)
        return None

    return user


def unauthorized_response(message: str = "Authentication required"):
    """Return standard unauthorized response payload."""
    return jsonify({"error": message}), 401
