"""Legacy market radar background poller (disabled in favor of on-demand command handlers)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

import aiohttp
import discord
from discord.ext import commands, tasks
from sqlalchemy import text

try:
    from .database_service import DatabaseService
    from .solana_security_checker import SolanaSecurityChecker
except ImportError:
    # Fallback for direct script execution outside package context.
    from services.database_service import DatabaseService
    from services.solana_security_checker import SolanaSecurityChecker

logger = logging.getLogger(__name__)

# Embed color
EMBED_COLOR_ORANGE = 0xFF8A00

# Cache TTL settings (seconds) for different endpoint types
CACHE_TTL_PRICE = 30        # Price endpoints: 30s
CACHE_TTL_TOKEN_LIST = 300  # Token lists/trending: 5m
CACHE_TTL_OHLCV = 600       # OHLCV candles: 10m
CACHE_TTL_TRADERS = 300     # Gainers/Losers: 5m


class LegacyMarketRadarPollerCog(commands.Cog):
    """High-speed market radar with price/volume alerts and whale tracking."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseService()
        self.birdeye_api_base = os.getenv("BIRDEYE_API_BASE_URL", "https://public-api.birdeye.so")
        self.birdeye_api_key = os.getenv("BIRDEYE_API_KEY", "")
        self.solana_checker = SolanaCheckerSingleton.get()
        self._cooldown_seconds = int(os.getenv("ALERT_RULE_COOLDOWN_SECONDS", "60"))
        self._last_sent: dict[str, float] = {}
        self.http_session: aiohttp.ClientSession | None = None

        # Dynamic throttling state for market radar
        self._throttle_interval_normal = 180    # 3 minutes when market is calm
        self._throttle_interval_fast = 30       # 30 seconds when market activity is high
        self._market_volatility_high = False    # Flag to detect high volatility
        self._rate_limit_backoff_until = 0      # Timestamp to back off until

        logger.info("Legacy market radar poller is disabled; use on-demand helpers from command handlers.")

    def cog_unload(self):
        self.alert_rule_loop.cancel()
        self.whale_watch_loop.cancel()

    @tasks.loop(seconds=30)
    async def alert_rule_loop(self):
        """
        Evaluate market radar alert rules with dynamic throttling.
        Normal mode: every 3 minutes. High activity: every 30 seconds.
        Respects API rate limits with automatic backoff.
        """
        if not self.http_session:
            self.http_session = aiohttp.ClientSession()

        try:
            now = time.time()
            
            # Check if we're in rate-limit backoff period
            if now < self._rate_limit_backoff_until:
                logger.debug("Rate limit backoff active. Skipping cycle.")
                return
            
            rules = self.db.list_active_alert_rules()
            if not rules:
                return

            # Detect market volatility (high # of alerts or recent market activity)
            self._market_volatility_high = len(rules) > 5
            
            # Apply dynamic throttling: skip if not in fast mode and time hasn't passed
            if hasattr(self, '_last_loop_ts'):
                elapsed = now - self._last_loop_ts
                interval = self._throttle_interval_fast if self._market_volatility_high else self._throttle_interval_normal
                if elapsed < interval:
                    logger.debug(f"Throttling market radar (elapsed: {elapsed:.0f}s, interval: {interval}s)")
                    return
            
            self._last_loop_ts = now

            tasks = [self._evaluate_and_notify(rule) for rule in rules]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            logger.exception("Alert loop failed")

    @alert_rule_loop.before_loop
    async def before_alert_rule_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=120)
    async def whale_watch_loop(self):
        """
        Poll gainers/losers for whale watch alerts every 2 minutes.
        Scales back to 5 minutes during rate limit periods.
        """
        if not self.http_session:
            self.http_session = aiohttp.ClientSession()

        try:
            now = time.time()
            if now < self._rate_limit_backoff_until:
                logger.debug("Rate limit backoff active. Skipping whale watch cycle.")
                return

            # Fetch top gainers/losers once
            gainers_losers = await self._fetch_traders_gainers_losers()
            if not gainers_losers:
                return

            # Compare against user watchlists
            # (MVP: just fetch and cache for now; real impl would match user alerts)
            logger.info("Whale watch snapshot captured: %d items", len(gainers_losers))
        except Exception:
            logger.exception("Whale watch loop failed")

    @whale_watch_loop.before_loop
    async def before_whale_watch_loop(self):
        await self.bot.wait_until_ready()

    async def _evaluate_and_notify(self, rule: dict[str, Any]):
        """Evaluate single alert rule: price breakout, volume spike, risk."""
        token_address = rule["token_address"]
        rule_id = rule["rule_id"]

        # Fetch OHLCV for volume/price detection
        ohlcv = await self._fetch_ohlcv(token_address, timeframe="1h")
        if not ohlcv:
            return

        token_name = f"Token {token_address[:8]}"
        current_price = await self._fetch_token_price(token_address)
        triggered_reasons: list[str] = []

        # Price breakout detection
        target_price = rule.get("target_price")
        if target_price is not None and current_price is not None:
            target_price_f = float(target_price)
            if current_price >= target_price_f:
                triggered_reasons.append(
                    f"🚀 Price breakout: `${current_price:.6f}` >= target `${target_price_f:.6f}`"
                )

        # Volume spike detection
        volume_threshold = rule.get("volume_threshold_usd")
        volume_1h = self._extract_volume_1h(ohlcv)
        if volume_threshold is not None and volume_1h is not None:
            if volume_1h >= float(volume_threshold):
                triggered_reasons.append(
                    f"📊 Volume spike: `${volume_1h:.0f}` >= threshold `${float(volume_threshold):.0f}`"
                )

        # Price change % detection (whale watch angle)
        price_change_pct = rule.get("price_change_percent_threshold")
        price_change = self._extract_price_change_pct(ohlcv)
        if price_change_pct is not None and price_change is not None:
            if abs(price_change) >= float(price_change_pct):
                direction = "📈 Up" if price_change > 0 else "📉 Down"
                triggered_reasons.append(f"{direction} {abs(price_change):.2f}% whale activity detected")

        if not triggered_reasons:
            return

        # Risk assessment (optional, local RPC check)
        risk_data = None
        if rule.get("include_risk_assessment"):
            risk_data = self.solana_checker.get_token_risk_assessment(token_address)

        # Dedupe and send
        condition_key = "|".join(sorted(triggered_reasons))
        if self.db.has_recent_notification(
            alert_rule_id=rule_id,
            token_address=token_address,
            condition_key=condition_key,
            hours=1,  # Shorter dedup window for fast alerts
        ):
            logger.debug("Skipping duplicate alert: rule=%s", rule_id)
            return

        birdeye_chart_url = f"https://birdeye.so/token/{token_address}?chain=solana"
        embed = self._build_market_radar_embed(
            token_name=token_name,
            token_address=token_address,
            current_price=current_price,
            reasons=triggered_reasons,
            risk_data=risk_data,
            birdeye_chart_url=birdeye_chart_url,
        )

        webhook_url = rule.get("discord_webhook_url")
        delivery_channel = (rule.get("delivery_channel") or "webhook").lower()

        if delivery_channel == "dm":
            discord_user_id = rule.get("discord_user_id")
            if not discord_user_id:
                self.db.log_notification_attempt(
                    alert_rule_id=rule_id,
                    token_address=token_address,
                    condition_key=condition_key,
                    status="failed",
                    detail="Missing discord_user_id for DM delivery",
                )
                return
            sent_ok, error = await self._send_embed_to_user(discord_user_id, embed)
        else:
            if not webhook_url:
                self.db.log_notification_attempt(
                    alert_rule_id=rule_id,
                    token_address=token_address,
                    condition_key=condition_key,
                    status="failed",
                    detail="Missing webhook_url",
                )
                return
            sent_ok, error = await self._send_embed_to_webhook(webhook_url, embed)
        status = "success" if sent_ok else "failed"
        self.db.log_notification_attempt(
            alert_rule_id=rule_id,
            token_address=token_address,
            condition_key=condition_key,
            status=status,
            detail=error or "Sent successfully",
        )
        if sent_ok:
            self.db.mark_alert_triggered(rule_id)
            logger.info("Alert delivered and marked triggered: rule=%s token=%s", rule_id, token_address)

    def _build_market_radar_embed(
        self,
        token_name: str,
        token_address: str,
        current_price: float | None,
        reasons: list[str],
        risk_data: dict[str, Any] | None,
        birdeye_chart_url: str,
    ) -> discord.Embed:
        """Build orange-themed embed for market radar alert."""
        reason_text = "\n".join(reasons) or "Alert conditions met"
        
        embed = discord.Embed(
            title=f"🎯 {token_name}",
            description=reason_text,
            color=EMBED_COLOR_ORANGE,
            url=birdeye_chart_url,
        )
        embed.add_field(name="Token Address", value=f"`{token_address}`", inline=False)
        
        price_str = f"${current_price:.6f}" if current_price else "N/A"
        embed.add_field(name="Current Price", value=price_str, inline=True)

        if risk_data:
            risk_level = risk_data.get("risk_level", "UNKNOWN")
            risk_emoji = "🟢" if risk_level == "LOW" else "🟡" if risk_level == "MEDIUM" else "🔴"
            embed.add_field(
                name="DIY Risk Assessment",
                value=f"{risk_emoji} {risk_level}",
                inline=True,
            )

        embed.set_footer(text="🔔 Birdeye Radar | High-Speed Alert Engine")
        return embed

    async def _fetch_token_price(self, token_address: str) -> float | None:
        """Fetch single token price with Redis cache (60s TTL)."""

        endpoint = f"{self.birdeye_api_base.rstrip('/')}/defi/price"
        payload = await self._call_birdeye(endpoint, {"address": token_address})
        if not payload:
            return None

        price = None
        try:
            price = float(payload.get("data", {}).get("value"))
        except (TypeError, ValueError):
            pass

        return price

    async def _fetch_ohlcv(self, token_address: str, timeframe: str = "1H") -> dict[str, Any] | None:
        """Fetch OHLCV data for volume/price spike detection."""
        # Normalise timeframe to Birdeye's expected format ("1h" -> "1H", "4h" -> "4H", "1d" -> "1D")
        _TYPE_MAP: dict[str, str] = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1H", "4h": "4H", "1d": "1D",
            "1H": "1H", "4H": "4H", "1D": "1D",
        }
        # Seconds per Birdeye interval type (used to compute time_from window)
        _TYPE_SECONDS: dict[str, int] = {
            "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
            "1H": 3600, "4H": 14400, "1D": 86400,
        }
        birdeye_type = _TYPE_MAP.get(timeframe, "1H")
        interval_seconds = _TYPE_SECONDS.get(birdeye_type, 3600)
        now = int(time.time())
        # Fetch a 2-interval window so at least one complete candle is always included
        time_from = now - interval_seconds * 2

        endpoint = f"{self.birdeye_api_base.rstrip('/')}/defi/ohlcv"
        params = {
            "address": token_address,
            "type": birdeye_type,
            "time_from": str(time_from),
            "time_to": str(now),
            "currency": "usd",
        }
        payload = await self._call_birdeye(endpoint, params)
        if not payload:
            return None
        return payload.get("data") or {}

    async def _fetch_traders_gainers_losers(self) -> list[dict[str, Any]] | None:
        """Fetch top gainers/losers for whale watch."""
        endpoint = f"{self.birdeye_api_base.rstrip('/')}/trader/gainers-losers"
        payload = await self._call_birdeye(endpoint, {})
        if not payload:
            return None
        data = payload.get("data") or {}
        gainers = data.get("gainers") or []
        losers = data.get("losers") or []
        return gainers + losers

    async def _get_redis_cache(self):
        """Get Redis cache instance."""
        try:
            from services.redis_cache import get_redis_cache
            return await get_redis_cache()
        except Exception:
            logger.debug("Redis cache unavailable")
            return None

    def _make_cache_key(self, endpoint: str, params: dict[str, str]) -> str:
        """Create deterministic cache key."""
        param_str = "|".join(f"{k}={v}" for k, v in sorted(params.items())) if params else ""
        return f"{endpoint}:{param_str}"

    def _get_cache_ttl_for_endpoint(self, endpoint: str) -> int:
        """Determine cache TTL based on endpoint type."""
        if "/defi/price" in endpoint:
            return CACHE_TTL_PRICE
        if "/defi/ohlcv" in endpoint:
            return CACHE_TTL_OHLCV
        if "/trader/gainers-losers" in endpoint:
            return CACHE_TTL_TRADERS
        if "trending" in endpoint:
            return CACHE_TTL_TOKEN_LIST
        return 0  # No cache

    def _extract_volume_1h(self, ohlcv_data: dict[str, Any]) -> float | None:
        """Extract 1h volume from OHLCV response."""
        if isinstance(ohlcv_data, list) and len(ohlcv_data) > 0:
            item = ohlcv_data[0]
            return float(item.get("volume")) if item.get("volume") is not None else None
        elif isinstance(ohlcv_data, dict):
            return float(ohlcv_data.get("volume")) if ohlcv_data.get("volume") is not None else None
        return None

    def _extract_price_change_pct(self, ohlcv_data: dict[str, Any]) -> float | None:
        """Extract price change % from OHLCV response."""
        if isinstance(ohlcv_data, list) and len(ohlcv_data) > 0:
            item = ohlcv_data[0]
            open_price = float(item.get("o")) if item.get("o") is not None else None
            close_price = float(item.get("c")) if item.get("c") is not None else None
            if open_price and close_price:
                return ((close_price - open_price) / open_price) * 100
        elif isinstance(ohlcv_data, dict):
            open_price = float(ohlcv_data.get("o")) if ohlcv_data.get("o") is not None else None
            close_price = float(ohlcv_data.get("c")) if ohlcv_data.get("c") is not None else None
            if open_price and close_price:
                return ((close_price - open_price) / open_price) * 100
        return None

    async def _call_birdeye(self, url: str, params: dict[str, str]) -> dict[str, Any] | None:
        """Call Birdeye API with built-in retry/rate limit handling."""
        # Try cache first
        cache_ttl = self._get_cache_ttl_for_endpoint(url)
        if cache_ttl > 0:
            cache = await self._get_redis_cache()
            if cache:
                from services.redis_cache import make_cache_key
                full_key = make_cache_key(self._make_cache_key(url, params))
                cached = await cache.get(full_key)
                if cached:
                    logger.debug(f"Cache hit for endpoint={url}")
                    return cached
        
        if not self.http_session:
            self.http_session = aiohttp.ClientSession()

        headers = {"accept": "application/json", "x-chain": "solana"}
        if self.birdeye_api_key:
            headers["X-API-KEY"] = self.birdeye_api_key

        for attempt in range(1, 4):
            try:
                async with self.http_session.get(
                    url, params=params, headers=headers, timeout=20
                ) as resp:
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", "60"))
                        logger.warning(f"Birdeye 429 rate limited. Backing off {retry_after}s")
                        # Activate backoff mode to throttle subsequent requests
                        self._rate_limit_backoff_until = time.time() + retry_after
                        self._market_volatility_high = False
                        if attempt < 3:
                            await asyncio.sleep(min(retry_after, 5))
                            continue
                        return None

                    # Handle 400 errors specifically for compute unit limits
                    if resp.status == 400:
                        body_text = await resp.text()
                        if "usage limit" in body_text.lower() or "compute unit" in body_text.lower():
                            logger.warning("Birdeye 400: Compute Units limit exceeded. Activating 60s backoff.")
                            # Set a 60-second backoff for compute unit limits
                            self._rate_limit_backoff_until = time.time() + 60
                            self._market_volatility_high = False
                            # Return throttled response
                            try:
                                from services.birdeye_error_handler import BirdeyeErrorResponse
                                return BirdeyeErrorResponse.get_throttled_response()
                            except ImportError:
                                pass
                            return None
                        logger.warning(f"Birdeye 400: {url} - {body_text[:200]}")
                        return None

                    if resp.status >= 400:
                        logger.warning(f"Birdeye {resp.status}: {url}")
                        return None

                    result = await resp.json()

                    # Cache successful response
                    if cache_ttl > 0 and result:
                        cache = await self._get_redis_cache()
                        if cache:
                            from services.redis_cache import make_cache_key
                            full_key = make_cache_key(self._make_cache_key(url, params))
                            await cache.set(full_key, result, cache_ttl)
                            logger.debug(f"Cache store for endpoint={url} (ttl={cache_ttl}s)")

                    return result
            except aiohttp.ClientError:
                logger.warning(f"Network error calling {url}")
                return None
            except Exception:
                logger.exception(f"Unexpected error calling {url}")
                return None

        return None

    async def _send_embed_to_webhook(self, webhook_url: str, embed: discord.Embed) -> tuple[bool, str | None]:
        """Send Discord embed via webhook."""
        if not self.http_session:
            self.http_session = aiohttp.ClientSession()

        try:
            webhook = discord.Webhook.from_url(webhook_url, session=self.http_session)
            await webhook.send(embed=embed, username="🔔 Birdeye Radar", wait=False)
            return True, None
        except Exception as exc:
            logger.exception("Failed to send webhook")
            return False, str(exc)

    async def _send_embed_to_user(self, discord_user_id: str | int, embed: discord.Embed) -> tuple[bool, str | None]:
        """Send Discord embed as a DM to a user."""
        try:
            user = await self.bot.fetch_user(int(discord_user_id))
            await user.send(embed=embed)
            return True, None
        except discord.Forbidden:
            logger.warning("Cannot DM user_id=%s (Forbidden – DMs may be disabled)", discord_user_id)
            return False, f"Cannot DM user {discord_user_id}: DMs may be disabled"
        except Exception as exc:
            logger.exception("Failed to send DM to user_id=%s", discord_user_id)
            return False, str(exc)


class SolanaCheckerSingleton:
    """Lazy-load singleton for Solana security checker."""
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = SolanaSecurityChecker()
        return cls._instance


async def setup(bot: commands.Bot):
    """Entrypoint for cog loading."""
    await bot.add_cog(LegacyMarketRadarPollerCog(bot))
