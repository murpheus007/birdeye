"""
Solana Trading Dashboard - Discord Bot
"""
import os
import json
import logging
import asyncio
import traceback
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
import redis.asyncio as aioredis

from services.database_service import DatabaseService

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Initialize bot with intents
intents = discord.Intents.default()
# Privileged intents are opt-in to avoid startup crashes when not enabled in Discord portal.
intents.message_content = True
intents.guilds = True
intents.members = os.getenv('DISCORD_ENABLE_MEMBERS_INTENT', 'false').lower() == 'true'

bot = commands.Bot(command_prefix=os.getenv('BOT_PREFIX', '!'), intents=intents)
_redis_listener_task: asyncio.Task | None = None
_db_service: DatabaseService | None = None


@bot.event
async def on_ready():
    """Event triggered when bot is ready"""
    global _redis_listener_task
    logger.info(f'Bot logged in as {bot.user}')
    logger.info(f'Bot is running in {len(bot.guilds)} guild(s)')
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} command(s)')
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}')

    if _redis_listener_task is None:
        _redis_listener_task = asyncio.create_task(listen_for_test_alerts())
        logger.info('Started Redis test-alert listener task')


@bot.event
async def on_error(event, *args, **kwargs):
    """Handle bot errors"""
    logger.error(f'Error in {event}', exc_info=True)


@bot.event
async def on_message(message: discord.Message):
    """Ensure prefix commands are processed and give traceability for command routing."""
    if message.author.bot:
        return
    await bot.process_commands(message)


@bot.tree.command(name='ping', description='Check if the bot is alive')
async def ping(interaction: discord.Interaction):
    """Slash command to check bot responsiveness."""
    await interaction.response.send_message(f'Pong! {round(bot.latency * 1000)}ms')


async def load_cogs():
    """Load bot cogs/extensions"""
    # Legacy pollers remain disabled by design; command_center is the primary runtime path.
    extensions = ['services.command_center']
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            logger.info('Loaded extension: %s', ext)
        except Exception as exc:
            module_path = Path(__file__).resolve().parent / Path(*ext.split('.')).with_suffix('.py')
            logger.error('Failed to load extension %s', ext)
            logger.error('Attempted file path: %s | exists=%s', module_path, module_path.exists())
            logger.error('CWD: %s', Path.cwd())
            logger.error('PYTHONPATH: %s', os.getenv('PYTHONPATH', ''))
            logger.error('Exception: %s', exc)
            logger.error('Traceback: %s', traceback.format_exc())
            raise
    logger.info('Cogs loaded successfully')


def _build_test_alert_embed(payload: dict) -> discord.Embed:
    embed = discord.Embed(
        title='🧪 Test Alert - Birdeye Radar',
        description='Backend-to-bot queue is alive.',
        color=0xFF8C00,
    )
    user_id = payload.get('discord_user_id', 'unknown')
    embed.add_field(name='Target', value=f'<@{user_id}>' if str(user_id).isdigit() else str(user_id), inline=True)
    embed.add_field(name='Status', value='Signal path verified', inline=True)
    embed.set_footer(text='🚀 Birdeye Radar Bot Queue | 🛡️ Orange Mode')
    return embed


def _build_alert_created_embed(payload: dict) -> discord.Embed:
    token_name = payload.get('token_name') or 'Unknown Token'
    token_address = payload.get('token_address') or 'N/A'
    target_price = payload.get('target_price')

    embed = discord.Embed(
        title='🔔 Alert Created',
        description='Your alert was synced from backend to bot queue.',
        color=0xFF8C00,
    )
    embed.add_field(name='Token', value=str(token_name), inline=True)
    embed.add_field(name='Address', value=f'`{token_address}`', inline=False)
    embed.add_field(
        name='Target Price',
        value=f'${float(target_price):,.6f}' if target_price is not None else 'N/A',
        inline=True,
    )
    embed.set_footer(text='🚀 Birdeye Radar Bot Queue | 🛡️ Orange Mode')
    return embed


async def listen_for_test_alerts():
    """Subscribe to Redis test_alerts channel and dispatch test DMs."""
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/1')
    redis_client = None
    pubsub = None
    try:
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('test_alerts')
        logger.info('Subscribed to Redis channel: test_alerts')

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                await asyncio.sleep(0.2)
                continue

            data = message.get('data')
            try:
                payload = json.loads(data) if isinstance(data, str) else data
            except Exception:
                logger.error('Invalid test_alert payload: %r', data)
                continue

            if not isinstance(payload, dict):
                logger.warning('test_alert payload must be an object, got: %s', type(payload))
                continue

            logger.info('DEBUG: Bot received test alert request: %s', payload)

            discord_user_id = str(payload.get('discord_user_id', '')).strip()
            if not discord_user_id.isdigit():
                user_id = payload.get('user_id')
                if user_id is not None:
                    try:
                        global _db_service
                        if _db_service is None:
                            _db_service = DatabaseService()
                        mapped_discord_id = _db_service.get_discord_user_id_by_user_id(int(user_id))
                        if mapped_discord_id:
                            discord_user_id = str(mapped_discord_id).strip()
                    except Exception:
                        logger.exception('Failed to resolve discord_user_id from user_id=%s', user_id)

            if not discord_user_id.isdigit():
                logger.warning('test_alert message missing valid discord_user_id: %s', discord_user_id)
                continue

            try:
                user = await bot.fetch_user(int(discord_user_id))
                if payload.get('token_address') and payload.get('user_id') is not None:
                    embed = _build_alert_created_embed(payload)
                else:
                    embed = _build_test_alert_embed(payload)
                await user.send(embed=embed)
                logger.info('Sent queued test alert DM to user_id=%s', discord_user_id)
            except discord.Forbidden:
                logger.warning('Cannot DM user_id=%s (Forbidden)', discord_user_id)
            except Exception:
                logger.exception('Failed dispatching queued test alert to user_id=%s', discord_user_id)
    except Exception:
        logger.exception('Redis test_alert listener crashed')
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe('test_alerts')
                await pubsub.close()
            except Exception:
                logger.debug('pubsub cleanup failed', exc_info=True)
        if redis_client:
            try:
                await redis_client.close()
            except Exception:
                logger.debug('redis cleanup failed', exc_info=True)


async def main():
    """Main bot startup function"""
    token = (os.getenv('DISCORD_TOKEN') or '').strip()
    if not token:
        raise ValueError('DISCORD_TOKEN environment variable is not set')
    
    async with bot:
        await load_cogs()
        await bot.start(token)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
