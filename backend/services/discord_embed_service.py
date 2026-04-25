"""Discord embed utilities for alert testing and notifications."""
from __future__ import annotations

import time
from typing import Any


def create_test_embed() -> dict[str, Any]:
    """Create a standard Discord embed for test alerts with orange branding."""
    return {
        "title": "🧪 Test Alert - Birdeye Radar Dashboard",
        "description": "Your alert connection is working perfectly!",
        "color": int("FF8C00", 16),  # Orange #FF8C00
        "fields": [
            {
                "name": "Status",
                "value": "✅ Connection Verified",
                "inline": True,
            },
            {
                "name": "Timestamp",
                "value": f"<t:{int(time.time())}:R>",
                "inline": True,
            },
        ],
        "thumbnail": {
            "url": "https://www.birdeye.so/favicon.ico",
            "height": 64,
            "width": 64,
        },
        "footer": {
            "text": "Birdeye Radar Alert Monitor",
        },
    }


def create_alert_embed(
    title: str,
    description: str,
    token_address: str = "",
    token_name: str = "",
    fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a standard Discord embed for price/volume alerts."""
    embed_fields = fields or []
    if token_name:
        embed_fields.insert(0, {"name": "Token", "value": f"`{token_name}`", "inline": True})

    return {
        "title": title,
        "description": description,
        "color": int("FF8C00", 16),  # Orange #FF8C00
        "fields": embed_fields,
        "footer": {
            "text": "Birdeye Radar Alert Monitor",
        },
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
