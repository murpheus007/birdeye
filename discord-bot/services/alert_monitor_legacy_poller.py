"""Legacy background alert polling (disabled in favor of on-demand command handlers)."""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import aiohttp
import discord
from discord.ext import commands, tasks
from sqlalchemy import text

from services.database_service import DatabaseService


logger = logging.getLogger(__name__)

EMBED_COLOR_ORANGE = 0xFF8A00

# Cache TTLs (seconds)
CACHE_TTL_PRICE_STATS = 30      # Price/stats: 30s
CACHE_TTL_TOKEN_LIST = 300      # Token lists: 5m
CACHE_TTL_OHLCV = 600           # OHLCV: 10m


def send_orange_alert(data: dict[str, Any]) -> discord.Embed:
    """Build an orange alert embed payload for Discord delivery."""
    token_name = data.get("token_name") or "Unknown Token"
    token_address = data.get("token_address") or "N/A"
    current_price = data.get("current_price")
    security_rating = data.get("security_rating")
    birdeye_chart_url = data.get("birdeye_chart_url") or "https://birdeye.so"
    reasons = data.get("reasons") or []

    reason_lines = "\n".join(f"- {reason}" for reason in reasons) or "- Alert conditions met"
    description = f"{reason_lines}\n\n[View Birdeye Chart]({birdeye_chart_url})"

    embed = discord.Embed(
        title=token_name,
        description=description,
        color=EMBED_COLOR_ORANGE,
        url=birdeye_chart_url,
    )
    embed.add_field(name="Token Address", value=f"`{token_address}`", inline=False)
    embed.add_field(
        name="Current Price",
        value=f"${current_price:.6f}" if isinstance(current_price, (int, float)) else "Unavailable",
        inline=True,
    )
    embed.add_field(
        name="Security Rating",
        value=str(security_rating) if security_rating is not None else "Unavailable",
        inline=True,
    )
    embed.set_footer(text="Birdeye Alert Engine")
    return embed


class LegacyAlertMonitorPollerCog(commands.Cog):
    """Polls alert rules and sends Discord embed notifications."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseService()
        self.birdeye_api_base = os.getenv("BIRDEYE_API_BASE_URL", "https://public-api.birdeye.so")
        self.birdeye_api_key = os.getenv("BIRDEYE_API_KEY", "")
        self.dashboard_base_url = os.getenv("DASHBOARD_BASE_URL", "https://birdeyeradar.site")
        self._cooldown_seconds = int(os.getenv("ALERT_RULE_COOLDOWN_SECONDS", "300"))
        self._last_sent: dict[str, float] = {}
        self.http_session: aiohttp.ClientSession | None = None
        
        # Dynamic throttling state
        self._throttle_interval_normal = 180  # 3 minutes for normal operation
        self._throttle_interval_fast = 60     # 60 seconds for high-priority mode
        self._high_priority_alerts_active = False  # Flag for high-priority alerts
        self._last_cache_refresh = 0  # Track last token list refresh
        self._cache_ttl = 300  # 5-minute token list cache
        
        logger.info("Legacy alert monitor poller is disabled; use on-demand helpers from command handlers.")

    def cog_unload(self):
        self.alert_rule_loop.cancel()

    @tasks.loop(seconds=60)
    async def alert_rule_loop(self):
        """
        Check all alert rules with dynamic throttling.
        Normal: every 3 minutes. High-priority: every 60 seconds.
        Uses cached token data to reduce API calls.
        """
        if not self.http_session:
            self.http_session = aiohttp.ClientSession()

        try:
            rules = self.db.list_active_alert_rules()
            if not rules:
                return

            now_ts = time.time()
            
            # Check if any rules are high-priority (frequent re-checks)
            self._high_priority_alerts_active = any(
                rule.get("priority") == "high" or rule.get("target_price") is not None
                for rule in rules
            )
            
            # Throttle execution dynamically
            if hasattr(self, '_last_loop_ts'):
                elapsed = now_ts - self._last_loop_ts
                if not self._high_priority_alerts_active and elapsed < self._throttle_interval_normal:
                    logger.debug("Throttling alert loop (normal mode). Next check in %.0fs", 
                                 self._throttle_interval_normal - elapsed)
                    return
            
            self._last_loop_ts = now_ts
            
            # Refresh token list cache if expired
            if now_ts - self._last_cache_refresh > self._cache_ttl:
                # Let each rule fetch its own data; cache is handled server-side
                self._last_cache_refresh = now_ts
            
            for rule in rules:
                await self._evaluate_and_notify(rule)
        except Exception:
            logger.exception("Alert loop failed")

    @alert_rule_loop.before_loop
    async def before_alert_rule_loop(self):
        await self.bot.wait_until_ready()

    async def _evaluate_and_notify(self, rule: dict[str, Any]):
        token_address = rule["token_address"]
        token_name = token_address

        current_price = await self._fetch_token_price(token_address)
        security_score = await self._fetch_token_security_score(token_address)
        if security_score.get("token_name"):
            token_name = security_score["token_name"]

        triggered_reasons: list[str] = []

        target_price = rule.get("target_price")
        if target_price is not None and current_price is not None:
            target_price_f = float(target_price)
            if current_price >= target_price_f:
                triggered_reasons.append(
                    f"Price target hit: `${current_price:.6f}` >= `${target_price_f:.6f}`"
                )

        security_threshold = rule.get("security_threshold")
        current_security = security_score.get("score")
        if security_threshold is not None and current_security is not None:
            if current_security < int(security_threshold):
                triggered_reasons.append(
                    f"Security warning: score dropped to **{current_security}** (< {security_threshold})"
                )

        if not triggered_reasons:
            return

        condition_key = "|".join(sorted(triggered_reasons))
        if self.db.has_recent_notification(
            alert_rule_id=rule["rule_id"],
            token_address=token_address,
            condition_key=condition_key,
            hours=4,
        ):
            logger.info(
                "Skipping duplicate alert: rule_id=%s token=%s condition=%s",
                rule["rule_id"],
                token_address,
                condition_key,
            )
            self.db.log_notification_attempt(
                alert_rule_id=rule["rule_id"],
                token_address=token_address,
                condition_key=condition_key,
                status="skipped",
                detail="Skipped due to idempotency window (4h)",
            )
            return

        dedupe_key = f"{rule['rule_id']}:{'|'.join(triggered_reasons)}"
        now_ts = time.time()
        if dedupe_key in self._last_sent and now_ts - self._last_sent[dedupe_key] < self._cooldown_seconds:
            return

        birdeye_chart_url = f"https://birdeye.so/token/{token_address}?chain=solana"
        embed = send_orange_alert(
            data={
                "token_name": token_name,
                "token_address": token_address,
                "current_price": current_price,
                "security_rating": current_security,
                "reasons": triggered_reasons,
                "birdeye_chart_url": birdeye_chart_url,
            },
        )

        delivery_channel = (rule.get("delivery_channel") or "webhook").lower()
        if delivery_channel == "dm":
            discord_user_id = rule.get("discord_user_id")
            if not discord_user_id:
                logger.warning("Skipping alert rule %s due to missing Discord user ID", rule["rule_id"])
                self.db.log_notification_attempt(
                    alert_rule_id=rule["rule_id"],
                    token_address=token_address,
                    condition_key=condition_key,
                    status="failed",
                    detail="Missing discord_user_id",
                )
                return
            sent_ok, error_detail = await self._send_embed_to_user(discord_user_id, embed)
        else:
            webhook_url = rule.get("discord_webhook_url")
            if not webhook_url:
                logger.warning("Skipping alert rule %s due to missing webhook URL", rule["rule_id"])
                self.db.log_notification_attempt(
                    alert_rule_id=rule["rule_id"],
                    token_address=token_address,
                    condition_key=condition_key,
                    status="failed",
                    detail="Missing discord_webhook_url",
                )
                return
            sent_ok, error_detail = await self._send_embed_to_webhook(webhook_url, embed)

        if sent_ok:
            logger.info("Alert delivered successfully for token=%s rule_id=%s", token_address, rule["rule_id"])
            self.db.log_notification_attempt(
                alert_rule_id=rule["rule_id"],
                token_address=token_address,
                condition_key=condition_key,
                status="success",
                detail=f"Delivered via {delivery_channel}",
            )
            self._last_sent[dedupe_key] = now_ts
        else:
            logger.error(
                "Alert delivery failed for token=%s rule_id=%s detail=%s",
                token_address,
                rule["rule_id"],
                error_detail,
            )
            self.db.log_notification_attempt(
                alert_rule_id=rule["rule_id"],
                token_address=token_address,
                condition_key=condition_key,
                status="failed",
                detail=error_detail,
            )

    async def _fetch_token_price(self, token_address: str) -> float | None:
        endpoint = f"{self.birdeye_api_base.rstrip('/')}/defi/price"
        payload = await self._call_birdeye(endpoint, {"address": token_address})
        if not payload:
            return None

        data = payload.get("data") or {}
        value = data.get("value")
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def _fetch_token_security_score(self, token_address: str) -> dict[str, Any]:
        endpoint = f"{self.birdeye_api_base.rstrip('/')}/defi/token_security"
        payload = await self._call_birdeye(endpoint, {"address": token_address})
        if not payload:
            return {}

        data = payload.get("data") or {}
        raw_score = data.get("score")
        score = None
        if raw_score is not None:
            try:
                score = int(raw_score)
            except (TypeError, ValueError):
                score = None

        token_name = data.get("tokenName") or data.get("name") or token_address
        return {"score": score, "token_name": token_name}

    async def _call_birdeye(self, url: str, params: dict[str, str]) -> dict[str, Any] | None:
        # Determine cache TTL based on endpoint
        cache_ttl = self._get_cache_ttl_for_endpoint(url)
        
        # Try cache first (if applicable)
        if cache_ttl > 0:
            cache = await self._get_redis_cache()
            if cache:
                cached_response = await cache.get(self._make_cache_key(url, params))
                if cached_response:
                    logger.debug(f"Cache hit for Birdeye endpoint: {url}")
                    return cached_response
        
        if not self.http_session:
            self.http_session = aiohttp.ClientSession()

        headers = {"accept": "application/json", "x-chain": "solana"}
        if self.birdeye_api_key:
            headers["x-api-key"] = self.birdeye_api_key

        try:
            async with self.http_session.get(url, params=params, headers=headers, timeout=15) as resp:
                if resp.status == 429:
                    retry_after = resp.headers.get("Retry-After", "60")
                    logger.warning("Birdeye 429 (rate limited) received for %s. retry_after=%s. Activating throttle mode.", 
                                   url, retry_after)
                    # Enable fast-checking mode to back off gracefully
                    self._high_priority_alerts_active = False
                    return None

                # Handle 400 errors (including compute units limit)
                if resp.status == 400:
                    body_text = await resp.text()
                    if "usage limit" in body_text.lower() or "compute unit" in body_text.lower():
                        logger.warning("Birdeye 400: Compute Units limit exceeded. Throttling alerts.")
                        # Don't set high_priority_alerts to False here; let throttling state persist
                        return None
                    logger.warning("Birdeye 400 error for %s: %s", url, body_text[:500])
                    # Return None for generic 400 errors too
                    return None

                if resp.status >= 400:
                    body = await resp.text()
                    logger.warning("Birdeye request failed. status=%s body=%s", resp.status, body[:500])
                    return None

                result = await resp.json()

                # Cache the successful response if applicable
                if cache_ttl > 0 and result:
                    cache = await self._get_redis_cache()
                    if cache:
                        await cache.set(self._make_cache_key(url, params), result, cache_ttl)
                        logger.debug(f"Cache store for Birdeye endpoint: {url} (ttl={cache_ttl}s)")

                return result
        except aiohttp.ClientError:
            logger.exception("Network error calling Birdeye endpoint: %s", url)
            return None
        except Exception:
            logger.exception("Unexpected error calling Birdeye endpoint: %s", url)
            return None

    def _get_cache_ttl_for_endpoint(self, url: str) -> int:
        """Determine cache TTL (seconds) based on Birdeye endpoint."""
        if "/defi/price" in url or "/defi/token_security" in url:
            return CACHE_TTL_PRICE_STATS
        if "trending" in url:
            return CACHE_TTL_TOKEN_LIST
        if "/ohlcv" in url:
            return CACHE_TTL_OHLCV
        return 0  # No cache

    def _make_cache_key(self, url: str, params: dict[str, str]) -> str:
        """Create a deterministic cache key."""
        param_str = "|".join(f"{k}={v}" for k, v in sorted(params.items())) if params else ""
        return f"{url}:{param_str}"

    async def _get_redis_cache(self):
        """Get Redis cache instance."""
        try:
            from services.redis_cache import get_redis_cache
            return await get_redis_cache()
        except Exception:
            logger.debug("Redis cache unavailable")
            return None

    async def _send_embed_to_webhook(self, webhook_url: str, embed: discord.Embed) -> tuple[bool, str | None]:
        if not self.http_session:
            self.http_session = aiohttp.ClientSession()

        try:
            webhook = discord.Webhook.from_url(webhook_url, session=self.http_session)
            await webhook.send(embed=embed, username="Birdeye Alerts", wait=False)
            return True, None
        except Exception as exc:
            logger.exception("Failed to send alert embed to webhook")
            return False, str(exc)

    async def _send_embed_to_user(self, discord_user_id: str | int, embed: discord.Embed) -> tuple[bool, str | None]:
        try:
            user = await self.bot.fetch_user(int(discord_user_id))
            await user.send(embed=embed)
            return True, None
        except Exception as exc:
            logger.exception("Failed to send alert embed as DM")
            return False, str(exc)


async def setup(bot: commands.Bot):
    """Entrypoint for cog loading."""
    await bot.add_cog(LegacyAlertMonitorPollerCog(bot))
