-- Database initialization script
-- This script runs automatically when PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS bot;

-- Grant permissions
GRANT ALL ON SCHEMA trading TO birdeye;
GRANT ALL ON SCHEMA bot TO birdeye;

-- Create tables (example schema)
CREATE TABLE IF NOT EXISTS trading.tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mint_address VARCHAR(255) UNIQUE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    decimals INTEGER DEFAULT 6,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trading.price_feeds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_id UUID REFERENCES trading.tokens(id) ON DELETE CASCADE,
    price DECIMAL(20, 8) NOT NULL,
    volume_24h DECIMAL(20, 2),
    market_cap DECIMAL(30, 2),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot.guild_config (
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(10),
    notification_channel_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot.watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    guild_id BIGINT REFERENCES bot.guild_config(guild_id) ON DELETE CASCADE,
    token_id UUID REFERENCES trading.tokens(id) ON DELETE CASCADE,
    alert_price DECIMAL(20, 8),
    alert_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (guild_id, token_id)
);

-- Create indexes
CREATE INDEX idx_tokens_symbol ON trading.tokens(symbol);
CREATE INDEX idx_tokens_mint ON trading.tokens(mint_address);
CREATE INDEX idx_price_feeds_token ON trading.price_feeds(token_id);
CREATE INDEX idx_watchlist_guild ON bot.watchlist(guild_id);

-- Grant table permissions
GRANT ALL ON trading.tokens TO birdeye;
GRANT ALL ON trading.price_feeds TO birdeye;
GRANT ALL ON bot.guild_config TO birdeye;
GRANT ALL ON bot.watchlist TO birdeye;
