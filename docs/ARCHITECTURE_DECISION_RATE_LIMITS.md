# Architecture Decision: Rate Limits and On-Demand Birdeye Access

## Status
Accepted

## Context
The Discord bot was using time-based polling in `alert_monitor_legacy_poller.py` and `alert_monitor_market_radar_legacy_poller.py` to repeatedly query Birdeye in the background.

That pattern had three problems:

1. **Compute Unit burn scaled linearly with the number of alerts.**
   Every active alert caused additional price, security, or OHLCV calls on every loop cycle.
2. **The bot was calling Birdeye even when no user was actively asking for data.**
   That meant we were spending quota on background monitoring instead of on user-visible actions.
3. **Rate limiting caused a bad failure mode.**
   Once Birdeye returned 400/usage-limit errors, the polling loops kept retrying, which amplified the problem.

## Decision
We abandoned background polling and moved to an **on-demand, TTL-cached** design.

### New behavior
- Birdeye requests only occur when a Discord user explicitly runs a command.
- The command layer performs a one-time fetch, then saves and displays the result.
- Every Birdeye response is cached in Redis with a strict TTL.
- Discord responses include cache transparency so users know whether the data came from Redis or live from Birdeye.

## Implementation Notes

### Cache TTLs
- Price data: **5 minutes**
- Token security: **1 hour**
- OHLCV: **10 minutes**
- Trending tokens: **5 minutes**
- Whale snapshots: **5 minutes**

### Cache transparency
Command responses now append a notice such as:
- `Fetched live from Birdeye.`
- `Data cached, expires in 4m 30s.`

### What changed in code
- The legacy poller extensions (`alert_monitor_legacy_poller.py` and `alert_monitor_market_radar_legacy_poller.py`) are intentionally disabled and no longer start polling tasks.
- On-demand lookup helpers live in `discord-bot/services/birdeye_lookup.py`.
- The command center now calls those helpers directly.
- The Redis cache helper now exposes TTL inspection so responses can show accurate expiry information.

## Consequences
### Positive
- API usage drops sharply because only user-driven requests hit Birdeye.
- Redis absorbs repeated requests for the same token or timeframe.
- Rate-limit behavior becomes visible and predictable to users.
- The bot becomes easier to reason about and cheaper to operate.

### Tradeoffs
- Background alerting is no longer automatic.
- Users must run commands to refresh data.
- Some workflows now rely on cached data freshness rather than constant monitoring.

## Discord Command Examples

The command center now uses on-demand Birdeye lookups with cache transparency:

- `!trending` or `/trending` - fetches trending tokens once and shows whether the data was live or cached.
- `!whales` or `/whales` - fetches whale snapshot data for the selected timeframe with a cache notice.
- `!price <token_address>` or `/price <token_address>` - performs a one-time price lookup for alert setup or manual checks.
- `!watchlist` and `!myalerts` - use database state only and do not call Birdeye.

Example cache notices:

- `Fetched live from Birdeye.`
- `Data cached, expires in 4m 30s.`

## Rationale
This was the best tradeoff for the current API tier and bounty constraints.

We prefer:
- predictable cost over hidden background consumption,
- user-triggered reads over infinite polling loops,
- and explicit cache boundaries over best-effort retries.

That is a more sustainable architecture for Birdeye’s quota model and keeps the bot responsive without burning Compute Units in the background.
