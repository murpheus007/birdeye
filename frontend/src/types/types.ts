export interface TokenData {
  token_address: string
  token_name: string
  symbol?: string
  current_price?: number
  security_rating?: number
  volume24h?: number
  price_change_24h?: number
}

export interface SecurityReport {
  token_address: string
  tokenName?: string
  score?: number
  warning?: string
  risk_level?: string
  mint_authority?: string | null
  freeze_authority?: string | null
  is_renounced?: boolean
}

export interface WhaleWatchItem {
  address: string
  network?: string
  pnl?: number
  volume?: number
  trade_count?: number
}

export interface WhaleWatchSnapshot {
  items: WhaleWatchItem[]
}

export interface WatchlistEntry {
  id: number
  user_id: number
  token_address: string
  token_name?: string | null
  symbol?: string | null
  created_at: string
  updated_at: string
}

export interface AlertHistoryEntry {
  id: number
  alert_rule_id: number
  token_address: string
  condition_key: string
  status: string
  detail?: string | null
  sent_at: string
}

export interface AuthUser {
  id: number
  wallet_address: string
  discord_webhook_url?: string | null
  discord_user_id?: string | null
  created_at: string
  updated_at: string
}

export interface AuthMeResponse {
  authenticated: boolean
  user: AuthUser | null
}

export interface AuthChallenge {
  wallet_address: string
  nonce: string
  issued_at: number
  message: string
}

export interface UserSettings {
  wallet_address: string
  discord_webhook_url?: string | null
  discord_user_id?: string | null
}

export interface AlertRuleEntry {
  id: number
  user_id: number
  token_address: string
  token_name?: string | null
  token_logo_url?: string | null
  alert_description?: string | null
  status: 'active' | 'triggered'
  target_price?: number | null
  price_change_percent_threshold?: number | null
  volume_spike_percent_threshold?: number | null
  delivery_channel: 'webhook' | 'dm'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OhlcvCandle {
  address: string
  type: string
  currency?: string
  unixTime: number
  o: number
  h: number
  l: number
  c: number
  v: number
}

export interface SearchHit {
  address: string
  symbol: string
  name: string
  network?: string
  liquidity?: number
  fdv?: number
  logoURI?: string
}

export interface TokenOverview {
  address: string
  symbol: string
  name: string
  marketCap: number
  fdv: number
  totalSupply: number
  circulatingSupply: number
  holders: number
  logoURI?: string
}

export interface TokenPriceStat {
  timeframe: string
  price: number
  priceChangePercent: number
  updateUnix: number
}

export interface TokenTradeData {
  holder: number
  market: number
  totalTrade24h: number
  uniqueTrader24h: number
  volume24h: number
  buy24h: number
  sell24h: number
  lastTradeUnix: number
  price: number
  largeOrderFlow: number
}

export interface TokenLifecycle {
  totalTrade: number
  totalVolumeUsd: number
  buyCount: number
  sellCount: number
  ath: number
  current: number
  drawdownPercent: number
}

export interface UserAlert {
  id: number
  user_id: number
  token_address: string
  target_price?: number | null
  security_threshold?: number | null
  is_active: boolean
}

export interface WalletHolding {
  token_address: string
  symbol?: string
  amount: number
  usd_value: number
}

export interface WalletPortfolio {
  wallet_address: string
  total_value_usd: number
  token_count: number
  tokens: WalletHolding[]
}
