"""Discovery routes for trending and meme token data."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.birdeye_api_client import BirdeyeAPIClientError, BirdeyeRateLimitError, get_birdeye_api_client


discovery_bp = Blueprint("discovery", __name__, url_prefix="/api/v1/discovery")


def _handle_birdeye_error(exc: Exception) -> tuple[dict, int]:
    """Handle Birdeye API errors and return appropriate status codes."""
    if isinstance(exc, BirdeyeRateLimitError):
        return (
            jsonify({
                "error": "DATA_THROTTLED",
                "message": "Radar is cooling down to save energy. Try again in 60s."
            }),
            429  # Too Many Requests
        )
    return (
        jsonify({"error": str(exc)}),
        502  # Bad Gateway
    )


@discovery_bp.get("/token_trending")
@discovery_bp.get("/defi/token_trending")
def token_trending():
    """Proxy Birdeye trending tokens with a 5-minute cache."""
    client = get_birdeye_api_client()
    params = request.args.to_dict(flat=True)

    try:
        payload = client.get_trending_tokens(params=params)
        return jsonify(
            {
                "source": "birdeye",
                "data": payload,
            }
        ), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@discovery_bp.get("/meme_list")
@discovery_bp.get("/defi/v3/token/meme/list")
def meme_list():
    """Proxy Birdeye meme token list with a 5-minute cache."""
    client = get_birdeye_api_client()
    params = request.args.to_dict(flat=True)

    try:
        payload = client.get_meme_tokens(params=params)
        return jsonify(
            {
                "source": "birdeye",
                "data": payload,
            }
        ), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status
