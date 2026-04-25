"""Interactive Discord Command Center for Alpha tools."""
from __future__ import annotations

import logging
import os
from typing import Any

import discord
from discord.ext import commands

from services.database_service import DatabaseService
from services.alert_redis_reader import AlertRedisReader
from services.birdeye_lookup import (
    fetch_price,
    fetch_trending_tokens,
    fetch_whales_snapshot,
)

logger = logging.getLogger(__name__)

EMBED_COLOR = int(os.getenv("DISCORD_EMBED_COLOR", "FF8C00"), 16)
DASHBOARD_URL = os.getenv("DASHBOARD_BASE_URL", "https://birdeyeradar.site")


class WhalesTimeframeSelect(discord.ui.Select):
    def __init__(self, cog: "CommandCenterCog"):
        self.cog = cog
        options = [
            discord.SelectOption(label="1h", value="1h", description="Fast whale momentum"),
            discord.SelectOption(label="24h", value="24h", description="Daily whale moves", default=True),
            discord.SelectOption(label="7d", value="7d", description="Weekly whale trend"),
        ]
        super().__init__(
            placeholder="Select whales timeframe",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="whales_timeframe_select",
        )

    async def callback(self, interaction: discord.Interaction):
        timeframe = self.values[0]
        embed = await self.cog.build_whales_embed(timeframe)
        view = WhalesView(self.cog, timeframe=timeframe)
        await interaction.response.edit_message(embed=embed, view=view)


class CommandCenterView(discord.ui.View):
    def __init__(self, cog: "CommandCenterCog"):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="🔥 Trending", style=discord.ButtonStyle.primary, custom_id="cc_trending")
    async def trending_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        embed = await self.cog.build_trending_embed()
        await interaction.response.send_message(embed=embed, view=self.cog.dashboard_link_view(), ephemeral=True)

    @discord.ui.button(label="🐳 Whales", style=discord.ButtonStyle.primary, custom_id="cc_whales")
    async def whales_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        embed = await self.cog.build_whales_embed(timeframe="24h")
        await interaction.response.send_message(embed=embed, view=WhalesView(self.cog, timeframe="24h"), ephemeral=True)

    @discord.ui.button(label="🎯 My Watchlist", style=discord.ButtonStyle.secondary, custom_id="cc_watchlist")
    async def watchlist_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.cog.send_watchlist_for_user(interaction.user, interaction.channel)
        await interaction.response.send_message("Sent your watchlist flow.", ephemeral=True)

    @discord.ui.button(label="🔔 My Alerts", style=discord.ButtonStyle.secondary, custom_id="cc_alerts")
    async def alerts_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.cog.send_alerts_for_user(interaction.user, interaction.channel)
        await interaction.response.send_message("Sent your alerts flow.", ephemeral=True)


class WhalesView(discord.ui.View):
    def __init__(self, cog: "CommandCenterCog", timeframe: str):
        super().__init__(timeout=300)
        self.add_item(WhalesTimeframeSelect(cog))
        self.add_item(
            discord.ui.Button(
                label="View Full Dashboard",
                emoji="🚀",
                style=discord.ButtonStyle.link,
                url=f"{DASHBOARD_URL}/whales?timeframe={timeframe}",
            )
        )


class CommandCenterCog(commands.Cog):
    """Interactive commands for public alpha tools and personal command flows."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseService()
        self.alert_reader = AlertRedisReader(self.db)

    def cog_unload(self):
        pass

    def dashboard_link_view(self, suffix: str = "") -> discord.ui.View:
        view = discord.ui.View(timeout=300)
        view.add_item(
            discord.ui.Button(
                label="View Full Dashboard",
                emoji="🚀",
                style=discord.ButtonStyle.link,
                url=f"{DASHBOARD_URL}{suffix}",
            )
        )
        return view

    async def build_trending_embed(self) -> discord.Embed:
        result = await fetch_trending_tokens(limit=5)
        payload = result.data or {}
        items = (((payload.get("data") or {}).get("tokens") or []))[:5] if isinstance(payload, dict) else []

        embed = discord.Embed(
            title="🚀 Alpha Feed: Trending Tokens",
            description="Top movers from Birdeye Radar right now.",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Signal", value="💰 Momentum + volume shifts", inline=False)

        if not items:
            embed.add_field(name="Status", value=result.cache_notice() if result.message else "No trending data available right now.", inline=False)
            embed.set_footer(text=f"🛡️ Birdeye Radar Command Center • {result.cache_notice()}")
            return embed

        for idx, token in enumerate(items[:5], start=1):
            symbol = token.get("symbol") or "UNKNOWN"
            name = token.get("name") or symbol
            address = token.get("address") or ""
            price = token.get("price")
            try:
                price_str = f"${float(price):,.6f}"
            except (TypeError, ValueError):
                price_str = "N/A"
            line = f"{price_str} | `{address[:6]}...{address[-4:]}`" if address else price_str
            embed.add_field(name=f"#{idx} {name} ({symbol})", value=line, inline=False)

        embed.add_field(name="Cache", value=result.cache_notice(), inline=False)
        embed.set_footer(text="🛡️ Birdeye Radar Command Center")
        return embed

    async def build_whales_embed(self, timeframe: str = "24h") -> discord.Embed:
        result = await fetch_whales_snapshot(timeframe=timeframe, limit=5)
        payload = result.data or {}
        data = (payload.get("data") or {}) if isinstance(payload, dict) else {}
        gainers = (data.get("gainers") or [])[:5]
        losers = (data.get("losers") or [])[:5]

        embed = discord.Embed(
            title=f"🐳 Whale Watch ({timeframe})",
            description="Large-flow gainers and losers from trader activity.",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Signal", value="💰 Whale size + velocity", inline=False)

        if not gainers and not losers:
            embed.add_field(name="Status", value=result.cache_notice() if result.message else "No whale data available for this timeframe.", inline=False)
            embed.set_footer(text=f"🛡️ Birdeye Radar Command Center • {result.cache_notice()}")
            return embed

        def _fmt_token(t: dict[str, Any]) -> str:
            symbol = t.get("symbol") or "UNK"
            change = t.get("priceChangePercent") or t.get("price_change_percent")
            volume = t.get("volume") or t.get("volumeUsd") or t.get("volume_usd")
            try:
                change_str = f"{float(change):+.2f}%"
            except (TypeError, ValueError):
                change_str = "N/A"
            try:
                volume_str = f"${float(volume):,.0f}"
            except (TypeError, ValueError):
                volume_str = "N/A"
            return f"{symbol}: {change_str} | vol {volume_str}"

        if gainers:
            embed.add_field(name="🚀 Top Gainers", value="\n".join(_fmt_token(t) for t in gainers[:5]), inline=False)
        if losers:
            embed.add_field(name="🛡️ Top Losers", value="\n".join(_fmt_token(t) for t in losers[:5]), inline=False)

        embed.add_field(name="Cache", value=result.cache_notice(), inline=False)
        embed.set_footer(text="🛡️ Birdeye Radar Command Center")
        return embed

    async def build_price_embed(self, token_address: str) -> discord.Embed:
        result = await fetch_price(token_address)
        payload = result.data or {}
        data = (payload.get("data") or {}) if isinstance(payload, dict) else {}
        value = data.get("value")

        embed = discord.Embed(
            title="💵 Birdeye Price Check",
            description=f"Token: `{token_address}`",
            color=EMBED_COLOR,
        )

        if value is None:
            embed.add_field(name="Status", value=result.cache_notice(), inline=False)
        else:
            try:
                price_str = f"${float(value):,.6f}"
            except (TypeError, ValueError):
                price_str = "N/A"
            embed.add_field(name="Price", value=price_str, inline=False)
            embed.add_field(name="Cache", value=result.cache_notice(), inline=False)

        embed.set_footer(text="🛡️ Birdeye Radar Command Center")
        return embed

    async def _send_dm_or_notify(self, source_channel: discord.abc.Messageable | None, user: discord.User | discord.Member, embed: discord.Embed, fallback_message: str):
        try:
            await user.send(embed=embed, view=self.dashboard_link_view())
            if source_channel:
                await source_channel.send(f"{user.mention} check your DMs.")
        except discord.Forbidden:
            if source_channel:
                await source_channel.send(f"{user.mention} {fallback_message}")
        except Exception:
            logger.exception("Failed to send DM to user id=%s", user.id)
            if source_channel:
                await source_channel.send(f"{user.mention} could not send a DM right now.")

    async def send_watchlist_for_user(self, user: discord.User | discord.Member, source_channel: discord.abc.Messageable | None):
        wallet = self.db.get_wallet_by_discord_user_id(str(user.id))
        if not wallet:
            embed = discord.Embed(
                title="🎯 Wallet Link Required",
                description="Link your wallet on the website to unlock personal watchlists.",
                color=EMBED_COLOR,
            )
            view = discord.ui.View(timeout=300)
            view.add_item(discord.ui.Button(label="Link Wallet on Website", style=discord.ButtonStyle.link, url=f"{DASHBOARD_URL}/settings"))
            if source_channel:
                await source_channel.send(embed=embed, view=view)
            return

        items = self.db.list_watchlist_by_wallet(wallet)
        embed = discord.Embed(
            title="🎯 My Watchlist",
            description=f"Wallet: `{wallet[:6]}...{wallet[-4:]}`",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Signal", value="🚀 Track your conviction tokens", inline=False)

        if not items:
            embed.add_field(name="Status", value="No watchlist tokens yet. Add some on the dashboard.", inline=False)
        else:
            lines = []
            for idx, item in enumerate(items[:10], start=1):
                symbol = item.get("symbol") or "UNK"
                token_name = item.get("token_name") or symbol
                address = item.get("token_address") or ""
                short_address = f"{address[:6]}...{address[-4:]}" if address else "N/A"
                lines.append(f"{idx}. {token_name} ({symbol}) - `{short_address}`")
            embed.add_field(name="Tokens", value="\n".join(lines), inline=False)

        await self._send_dm_or_notify(
            source_channel=source_channel,
            user=user,
            embed=embed,
            fallback_message="I can't DM you. Please enable DMs or use the dashboard.",
        )

    async def send_alerts_for_user(self, user: discord.User | discord.Member, source_channel: discord.abc.Messageable | None):
        wallet = self.db.get_wallet_by_discord_user_id(str(user.id))
        if not wallet:
            embed = discord.Embed(
                title="🔔 Wallet Link Required",
                description="Link your wallet on the website to sync your personal alerts.",
                color=EMBED_COLOR,
            )
            view = discord.ui.View(timeout=300)
            view.add_item(discord.ui.Button(label="Link Wallet on Website", style=discord.ButtonStyle.link, url=f"{DASHBOARD_URL}/settings"))
            if source_channel:
                await source_channel.send(embed=embed, view=view)
            return

        rules = await self.alert_reader.list_alerts_by_wallet(wallet)
        if not rules:
            rules = self.db.list_alerts_by_wallet(wallet)
        embed = discord.Embed(
            title="🔔 My Active Alerts",
            description=f"Wallet: `{wallet[:6]}...{wallet[-4:]}`",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Signal", value="💰 Active strategy triggers", inline=False)

        if not rules:
            embed.add_field(name="Status", value="No active alerts yet. Create one from the dashboard.", inline=False)
        else:
            lines = []
            for idx, rule in enumerate(rules[:10], start=1):
                pieces = [f"{idx}. `{rule.get('token_address', 'N/A')[:6]}...`"]
                if rule.get("target_price") is not None:
                    pieces.append(f"price >= ${float(rule['target_price']):,.6f}")
                if rule.get("volume_spike_percent_threshold") is not None:
                    pieces.append(f"vol spike >= {float(rule['volume_spike_percent_threshold']):,.0f}%")
                if rule.get("price_change_percent_threshold") is not None:
                    pieces.append(f"whale move >= {float(rule['price_change_percent_threshold']):,.2f}%")
                pieces.append(f"via {rule.get('delivery_channel', 'webhook')}")
                lines.append(" | ".join(pieces))
            embed.add_field(name="Rules", value="\n".join(lines), inline=False)

        await self._send_dm_or_notify(
            source_channel=source_channel,
            user=user,
            embed=embed,
            fallback_message="I can't DM you. Please enable DMs or use the dashboard.",
        )

    @commands.command(name="start")
    async def start_command_center(self, ctx: commands.Context):
        """Main command center with interaction buttons."""
        embed = discord.Embed(
            title="🚀 Birdeye Radar Command Center",
            description="Launch your alpha tools with one tap.",
            color=EMBED_COLOR,
        )
        embed.add_field(name="🔥 Trending", value="Top momentum tokens", inline=True)
        embed.add_field(name="🐳 Whales", value="Big flow and smart money", inline=True)
        embed.add_field(name="🎯 My Watchlist", value="Your wallet-linked list", inline=True)
        embed.add_field(name="🔔 My Alerts", value="Your active alert rules", inline=True)
        embed.set_footer(text="🛡️ Orange Mode Engaged")
        await ctx.send(embed=embed, view=CommandCenterView(self))

    @commands.command(name="trending")
    async def trending_command(self, ctx: commands.Context):
        embed = await self.build_trending_embed()
        await ctx.send(embed=embed, view=self.dashboard_link_view("/explorer"))

    @commands.command(name="whales")
    async def whales_command(self, ctx: commands.Context):
        embed = await self.build_whales_embed(timeframe="24h")
        await ctx.send(embed=embed, view=WhalesView(self, timeframe="24h"))

    @commands.command(name="whale")
    async def whale_command_alias(self, ctx: commands.Context):
        """Alias for !whales to support singular usage."""
        await self.whales_command(ctx)

    @commands.command(name="price")
    async def price_command(self, ctx: commands.Context, token_address: str):
        embed = await self.build_price_embed(token_address)
        await ctx.send(embed=embed)

    @commands.command(name="watchlist")
    async def watchlist_command(self, ctx: commands.Context):
        await self.send_watchlist_for_user(ctx.author, ctx.channel)

    @commands.command(name="myalerts")
    async def myalerts_command(self, ctx: commands.Context):
        await self.send_alerts_for_user(ctx.author, ctx.channel)

    @discord.app_commands.command(name="start", description="Open the Birdeye Radar command center")
    async def start_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🚀 Birdeye Radar Command Center",
            description="Launch your alpha tools with one tap.",
            color=EMBED_COLOR,
        )
        embed.add_field(name="🔥 Trending", value="Top momentum tokens", inline=True)
        embed.add_field(name="🐳 Whales", value="Big flow and smart money", inline=True)
        embed.add_field(name="🎯 My Watchlist", value="Your wallet-linked list", inline=True)
        embed.add_field(name="🔔 My Alerts", value="Your active alert rules", inline=True)
        embed.set_footer(text="🛡️ Orange Mode Engaged")
        await interaction.response.send_message(embed=embed, view=CommandCenterView(self))

    @discord.app_commands.command(name="whales", description="View whale watch snapshot")
    async def whales_slash(self, interaction: discord.Interaction):
        embed = await self.build_whales_embed(timeframe="24h")
        await interaction.response.send_message(embed=embed, view=WhalesView(self, timeframe="24h"))

    @discord.app_commands.command(name="price", description="Fetch a token price once with cache transparency")
    async def price_slash(self, interaction: discord.Interaction, token_address: str):
        embed = await self.build_price_embed(token_address)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandCenterCog(bot))
