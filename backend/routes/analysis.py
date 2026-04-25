"""Market Radar routes: OHLCV, price breakout detection, whale watch tracking."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from dto.contracts import TokenSummaryDTO
from services.birdeye_api_client import BirdeyeAPIClientError, BirdeyeRateLimitError, get_birdeye_api_client
from services.solana_security_checker import get_solana_security_checker
from services.whale_wallet_service import WhaleWalletServiceError, get_whale_wallet_service


analysis_bp = Blueprint("analysis", __name__, url_prefix="/api/v1/analysis")


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


@analysis_bp.get("/ohlcv")
def ohlcv():
    """Fetch OHLCV data for price/volume spike detection (Market Radar)."""
    client = get_birdeye_api_client()
    params = request.args.to_dict(flat=True)

    try:
        payload = client.get_ohlcv(params=params)
        return jsonify({"source": "birdeye", "data": payload}), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/trending")
def trending():
    """Expose the live trending feed for the command center."""
    client = get_birdeye_api_client()
    params = request.args.to_dict(flat=True)

    try:
        payload = client.get_trending_tokens(params=params)
        return jsonify({"source": "birdeye", "data": payload}), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/meme-list")
def meme_list():
    """Expose meme list feed for dense radar table view."""
    client = get_birdeye_api_client()
    params = request.args.to_dict(flat=True)

    try:
        payload = client.get_meme_tokens(params=params)
        return jsonify({"source": "birdeye", "data": payload}), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/search")
def search():
    """Expose command palette token search."""
    client = get_birdeye_api_client()
    query = request.args.get("q") or request.args.get("keyword")
    target = request.args.get("target", "token")
    params = {"target": target}
    if query:
        params["keyword"] = query

    try:
        payload = client.search(params=params)
        return jsonify({"source": "birdeye", "data": payload}), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/token-summary")
def token_summary():
    """Return Market Radar token summary with local Solana RPC security data."""
    client = get_birdeye_api_client()
    checker = get_solana_security_checker()
    address = request.args.get("address")

    if not address:
        return jsonify({"error": "address query parameter is required"}), 400

    try:
        price_payload = client.get_token_price(address=address)
        price_data = price_payload.get("data") or {}
        
        # Use local Solana RPC for risk assessment (no premium key needed)
        risk_data = checker.get_token_risk_assessment(address)

        dto = TokenSummaryDTO(
            token_address=address,
            token_name=risk_data.get("is_renounced") and "[RENOUNCED]" or f"Token {address[:8]}",
            symbol="TKN",
            current_price=price_data.get("value"),
            security_rating=risk_data.get("risk_score"),
        )
        return jsonify({
            "data": dto.model_dump(),
            "risk_assessment": risk_data,
        }), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/security/<address>")
def security(address: str):
    """Expose live Solana RPC security checks for a token address."""
    checker = get_solana_security_checker()
    return jsonify({"data": checker.get_token_risk_assessment(address)}), 200


@analysis_bp.get("/token-overview")
def token_overview():
    """Expose token overview for war-room header metrics."""
    client = get_birdeye_api_client()
    address = request.args.get("address")
    if not address:
        return jsonify({"error": "address query parameter is required"}), 400

    try:
        payload = client.get_token_overview(address=address)
        return jsonify({"source": "birdeye", "data": payload}), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/price-stats")
def price_stats():
    """Expose price stats snapshots for war-room activity grid."""
    client = get_birdeye_api_client()
    address = request.args.get("address")
    if not address:
        return jsonify({"error": "address query parameter is required"}), 400

    list_timeframe = request.args.get("list_timeframe", "1m,1h,24h")
    try:
        payload = client.get_price_stats_single(address=address, list_timeframe=list_timeframe)
        return jsonify({"source": "birdeye", "data": payload}), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/trade-data")
def trade_data():
    """Expose trade activity details for war-room activity grid."""
    client = get_birdeye_api_client()
    address = request.args.get("address")
    if not address:
        return jsonify({"error": "address query parameter is required"}), 400

    try:
        payload = client.get_token_trade_data_single(address=address)
        return jsonify({"source": "birdeye", "data": payload}), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/all-time-trades")
def all_time_trades():
    """Expose life-of-token trade history summary."""
    client = get_birdeye_api_client()
    address = request.args.get("address")
    if not address:
        return jsonify({"error": "address query parameter is required"}), 400

    try:
        payload = client.get_all_time_trades_single(address=address)
        return jsonify({"source": "birdeye", "data": payload}), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/whale-watch")
def whale_watch():
    """Fetch top gainers/losers for whale-activity tracking."""
    client = get_birdeye_api_client()
    incoming = request.args.to_dict(flat=True)
    params: dict[str, str] = {}

    # Birdeye /trader/gainers-losers accepts limit in [1, 10].
    raw_limit = incoming.get("limit")
    if raw_limit is not None:
        try:
            params["limit"] = str(max(1, min(10, int(raw_limit))))
        except (TypeError, ValueError):
            params["limit"] = "10"
    else:
        params["limit"] = "10"
    
    try:
        payload = client.get_traders_gainers_losers(params)
        return jsonify({"source": "birdeye", "data": payload}), 200
    except (BirdeyeRateLimitError, BirdeyeAPIClientError) as exc:
        resp, status = _handle_birdeye_error(exc)
        return resp, status


@analysis_bp.get("/whale-wallet/<wallet_address>")
def whale_wallet_detail(wallet_address: str):
    """Return native Solana RPC wallet activity details for whale profiles."""
    service = get_whale_wallet_service()
    limit = request.args.get("limit", 25, type=int)

    try:
        payload = service.get_wallet_detail(wallet_address=wallet_address, limit=limit)
        return jsonify({"source": "solana-rpc", "data": payload}), 200
    except WhaleWalletServiceError as exc:
        return jsonify({"error": str(exc)}), 502
