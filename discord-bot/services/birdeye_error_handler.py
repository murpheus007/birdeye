"""
API error handler utilities for graceful Birdeye 400 error responses.
Transforms 400 errors (compute units limit) into user-friendly DATA_THROTTLED responses.
"""
from __future__ import annotations

import logging
import json
from typing import Any

logger = logging.getLogger(__name__)


class BirdeyeErrorResponse:
    """Wrapper for Birdeye API errors with graceful handling."""

    # HTTP 400 with "compute units usage limit exceeded" message
    DATA_THROTTLED_ERROR_CODE = "DATA_THROTTLED"
    DATA_THROTTLED_MESSAGE = "Radar is cooling down to save energy. Try again in 60s."

    @staticmethod
    def is_compute_units_error(status: int, body: str) -> bool:
        """Check if error is specifically compute units limit."""
        if status != 400:
            return False
        return "usage limit" in body.lower() or "compute unit" in body.lower()

    @staticmethod
    def get_throttled_response() -> dict[str, str]:
        """Return user-friendly throttled response."""
        return {
            "error": BirdeyeErrorResponse.DATA_THROTTLED_ERROR_CODE,
            "message": BirdeyeErrorResponse.DATA_THROTTLED_MESSAGE,
        }

    @staticmethod
    def format_api_error_response(status: int, body: str) -> dict[str, Any] | None:
        """
        Transform Birdeye 400 errors into graceful responses.
        Returns None for other errors (let them bubble up).
        """
        if BirdeyeErrorResponse.is_compute_units_error(status, body):
            logger.warning("Birdeye compute units limit exceeded. Returning throttled response.")
            return BirdeyeErrorResponse.get_throttled_response()

        # Other 400 errors: continue normal error handling
        return None


async def handle_birdeye_response(response_data: dict[str, Any] | None, status: int, body: str) -> dict[str, Any] | None:
    """
    Handle Birdeye API response, including graceful error transformation.

    Args:
        response_data: Parsed JSON response (if available)
        status: HTTP status code
        body: Raw response body text

    Returns:
        Modified response or None if should be treated as error
    """
    # If we got a successful response, return it
    if status < 400:
        return response_data

    # Check for compute units error and transform it
    throttled_response = BirdeyeErrorResponse.format_api_error_response(status, body)
    if throttled_response:
        return throttled_response

    # Other errors: return None (caller will treat as failed request)
    return None
