"""
Configuration for Discord bot
"""
import os
from dotenv import load_dotenv

load_dotenv()


class BotConfig:
    """Bot configuration"""
    
    # Bot settings
    TOKEN = os.getenv('DISCORD_TOKEN')
    PREFIX = os.getenv('BOT_PREFIX', '!')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/1')
    
    # Solana
    SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL')

    # Birdeye
    BIRDEYE_API_BASE_URL = os.getenv('BIRDEYE_API_BASE_URL', 'https://public-api.birdeye.so')
    BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY')

    # Alerts
    DASHBOARD_BASE_URL = os.getenv('DASHBOARD_BASE_URL', 'https://birdeyeradar.site')
    ALERT_RULE_COOLDOWN_SECONDS = int(os.getenv('ALERT_RULE_COOLDOWN_SECONDS', '300'))
    
    # Behavior
    COMMAND_TIMEOUT = 30
    ACTIVITY_STATUS = "📊 Solana Trading"


def validate_config():
    """Validate configuration"""
    if not BotConfig.TOKEN:
        raise ValueError("DISCORD_TOKEN is not set")
    
    if not BotConfig.DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    
    if not BotConfig.SOLANA_RPC_URL:
        raise ValueError("SOLANA_RPC_URL is not set")
