import {
  AlertRuleEntry,
  AlertHistoryEntry,
  AuthChallenge,
  AuthMeResponse,
  OhlcvCandle,
  SearchHit,
  UserSettings,
  TokenLifecycle,
  TokenOverview,
  TokenPriceStat,
  TokenTradeData,
  WatchlistEntry,
  WhaleWatchItem,
} from '../types/types'

const normalizeApiBase = (raw: string | undefined): string => {
  const base = (raw?.trim() || '/api/v1').replace(/\/$/, '')
  if (base.endsWith('/api/v1')) {
    return base
  }
  if (base.endsWith('/api')) {
    return `${base}/v1`
  }
  return base
}

const API_BASE = normalizeApiBase(import.meta.env.VITE_API_URL)

const parseJson = async <T>(response: Response): Promise<T> => {
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const errorCode = (payload as any)?.error
    const errorMessage = (payload as any)?.message ?? `Request failed (${response.status})`
    
    // Check for DATA_THROTTLED error and show throttle toast
    if (errorCode === 'DATA_THROTTLED') {
      showThrottleToast(errorMessage)
    }
    
    const message = errorCode ? `${errorCode}: ${errorMessage}` : errorMessage
    throw new Error(message)
  }
  return payload as T
}

/**
 * Show throttle notification via global toast context if available
 */
let toastNotifier: ((message: string, type: 'error' | 'warning' | 'info') => void) | null = null

export const registerToastNotifier = (notifier: (message: string, type: 'error' | 'warning' | 'info') => void) => {
  toastNotifier = notifier
}

const showThrottleToast = (message?: string) => {
  if (toastNotifier) {
    toastNotifier(
      message || 'Radar is cooling down to save energy. Try again in 60s.',
      'warning'
    )
  }
}

const get = async <T>(path: string): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
  })
  return parseJson<T>(response)
}

const post = async <T>(path: string, body: unknown): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  })
  return parseJson<T>(response)
}

const put = async <T>(path: string, body: unknown): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  })
  return parseJson<T>(response)
}

const del = async <T>(path: string): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  return parseJson<T>(response)
}

const unwrapArray = (payload: any): any[] => {
  const candidates = [
    payload?.data?.items,
    payload?.data?.tokens,
    payload?.data?.data?.items,
    payload?.data?.data?.tokens,
    payload?.data?.data,
    payload?.data,
    payload?.items,
  ]

  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate
    }
  }
  return []
}

export type RadarRow = {
  address: string
  symbol: string
  name: string
  price: number
  priceChange24h: number
  volume24h: number
  liquidity: number
  fdv: number
  buySellRatio: number
  buy24h: number
  sell24h: number
  marketCap?: number
  logoURI?: string
  isHot?: boolean
}

export type OhlcvInterval = '1m' | '5m' | '30m' | '1H' | '4H' | '1D'

export type WhaleWalletDetail = {
  wallet: string
  summary: {
    total_transactions: number
    buy_count: number
    sell_count: number
    neutral_count: number
    tokens_touched: number
  }
  recent_activity: Array<{
    signature: string
    timestamp: number | null
    side: 'buy' | 'sell' | 'neutral'
    token_address: string
    token_delta: number
    fee_lamports: number
    status: 'success' | 'failed'
  }>
}

export const terminalApi = {
  async getAuthChallenge(walletAddress: string): Promise<AuthChallenge> {
    const payload = await get<any>(`/auth/challenge?wallet_address=${encodeURIComponent(walletAddress)}`)
    return payload?.data
  },

  async loginWithWallet(walletAddress: string, message: string, signature: string): Promise<AuthMeResponse> {
    const payload = await post<any>('/auth/login', {
      wallet_address: walletAddress,
      message,
      signature,
    })
    return payload?.data
  },

  async getAuthMe(): Promise<AuthMeResponse> {
    const payload = await get<any>('/auth/me')
    return payload?.data
  },

  async logout(): Promise<void> {
    await post('/auth/logout', {})
  },

  async getSettings(): Promise<UserSettings> {
    const payload = await get<any>('/auth/settings')
    return payload?.data
  },

  async updateSettings(input: Partial<UserSettings>): Promise<UserSettings> {
    const payload = await put<any>('/auth/settings', input)
    return payload?.data
  },

  async createAlert(input: {
    token_address: string
    token_name?: string
    token_logo_url?: string
    alert_description?: string
    target_price?: number
    price_change_percent?: number
    alert_type: 'webhook' | 'dm'
  }): Promise<AlertRuleEntry> {
    const payload = await post<any>('/alerts/create', input)
    return payload?.data
  },

  async sendTestAlert(input: { discord_webhook_url?: string; discord_user_id?: string }): Promise<{ message: string }> {
    const payload = await post<any>('/alerts/test', input)
    return payload?.data ?? { message: 'Test alert queued' }
  },

  async listMyAlerts(): Promise<AlertRuleEntry[]> {
    const payload = await get<any>('/alerts/mine')
    return unwrapArray(payload).map((row: any) => ({
      id: Number(row?.id ?? 0),
      user_id: Number(row?.user_id ?? 0),
      token_address: row?.token_address ?? 'unknown',
      token_name: row?.token_name ?? null,
      token_logo_url: row?.token_logo_url ?? null,
      alert_description: row?.alert_description ?? null,
      status: (row?.status ?? 'active') as 'active' | 'triggered',
      target_price: row?.target_price != null ? Number(row.target_price) : null,
      price_change_percent_threshold:
        row?.price_change_percent_threshold != null ? Number(row.price_change_percent_threshold) : null,
      volume_spike_percent_threshold:
        row?.volume_spike_percent_threshold != null ? Number(row.volume_spike_percent_threshold) : null,
      delivery_channel: (row?.delivery_channel ?? 'webhook') as 'webhook' | 'dm',
      is_active: Boolean(row?.is_active ?? true),
      created_at: row?.created_at ?? new Date().toISOString(),
      updated_at: row?.updated_at ?? new Date().toISOString(),
    }))
  },

  async deleteAlert(alertId: number): Promise<void> {
    await del(`/alerts/${alertId}`)
  },

  async getRadarData(limit = 100): Promise<RadarRow[]> {
    const [memePayload, trendingPayload] = await Promise.all([
      get<any>(`/analysis/meme-list?sort_by=volume_24h_usd&sort_type=desc&offset=0&limit=${limit}`),
      get<any>('/analysis/trending?limit=20'),
    ])

    const trendingAddresses = new Set(unwrapArray(trendingPayload).map((item: any) => item.address))

    return unwrapArray(memePayload).map((item: any) => {
      const buy24h = Number(item?.buy_24h ?? 0)
      const sell24h = Number(item?.sell_24h ?? 0)
      const ratio = sell24h > 0 ? buy24h / sell24h : buy24h > 0 ? 999 : 1

      return {
        address: item?.address ?? 'unknown',
        symbol: item?.symbol ?? 'N/A',
        name: item?.name ?? item?.symbol ?? 'Unknown Token',
        price: Number(item?.price ?? 0),
        priceChange24h: Number(item?.price_change_24h_percent ?? 0),
        volume24h: Number(item?.volume_24h_usd ?? 0),
        liquidity: Number(item?.liquidity ?? 0),
        fdv: Number(item?.fdv ?? 0),
        buySellRatio: ratio,
        buy24h,
        sell24h,
        marketCap: Number(item?.market_cap ?? 0),
        logoURI: item?.logo_uri,
        isHot: trendingAddresses.has(item?.address),
      }
    })
  },

  async getWhaleRows(limit = 10): Promise<WhaleWatchItem[]> {
    const safeLimit = Math.max(1, Math.min(10, Number(limit) || 10))
    const payload = await get<any>(`/analysis/whale-watch?limit=${safeLimit}`)
    return unwrapArray(payload).map((item: any) => ({
      address: item?.address ?? 'unknown',
      network: item?.network,
      pnl: Number(item?.pnl ?? 0),
      volume: Number(item?.volume ?? 0),
      trade_count: Number(item?.trade_count ?? 0),
    }))
  },

  async getWhaleWalletDetail(address: string, limit = 25): Promise<WhaleWalletDetail> {
    const safeLimit = Math.max(5, Math.min(50, Number(limit) || 25))
    const payload = await get<any>(`/analysis/whale-wallet/${encodeURIComponent(address)}?limit=${safeLimit}`)
    const data = payload?.data ?? {}

    return {
      wallet: data?.wallet ?? address,
      summary: {
        total_transactions: Number(data?.summary?.total_transactions ?? 0),
        buy_count: Number(data?.summary?.buy_count ?? 0),
        sell_count: Number(data?.summary?.sell_count ?? 0),
        neutral_count: Number(data?.summary?.neutral_count ?? 0),
        tokens_touched: Number(data?.summary?.tokens_touched ?? 0),
      },
      recent_activity: (data?.recent_activity ?? []).map((row: any) => ({
        signature: row?.signature ?? '',
        timestamp: row?.timestamp ?? null,
        side: row?.side ?? 'neutral',
        token_address: row?.token_address ?? 'SOL',
        token_delta: Number(row?.token_delta ?? 0),
        fee_lamports: Number(row?.fee_lamports ?? 0),
        status: row?.status ?? 'success',
      })),
    }
  },

  async searchTokens(query: string): Promise<SearchHit[]> {
    const payload = await get<any>(`/analysis/search?q=${encodeURIComponent(query)}&target=token`)
    const sections = payload?.data?.data?.items ?? payload?.data?.items ?? []
    const tokenSection = sections.find((section: any) => section?.type === 'token')
    const rows = tokenSection?.result ?? []

    return rows.slice(0, 15).map((item: any) => ({
      address: item?.address,
      symbol: item?.symbol,
      name: item?.name,
      liquidity: Number(item?.liquidity ?? 0),
      fdv: Number(item?.fdv ?? 0),
      logoURI: item?.logo_uri,
      network: item?.network,
    }))
  },

  async getTokenOverview(address: string): Promise<TokenOverview> {
    const payload = await get<any>(`/analysis/token-overview?address=${encodeURIComponent(address)}`)
    const data = payload?.data?.data ?? payload?.data ?? {}
    return {
      address,
      symbol: data?.symbol ?? 'N/A',
      name: data?.name ?? 'Unknown',
      marketCap: Number(data?.marketCap ?? data?.market_cap ?? 0),
      fdv: Number(data?.fdv ?? 0),
      totalSupply: Number(data?.supply ?? data?.totalSupply ?? 0),
      circulatingSupply: Number(data?.circulatingSupply ?? data?.circulating_supply ?? 0),
      holders: Number(data?.holders ?? data?.holder ?? 0),
      logoURI: data?.logoURI ?? data?.logo_uri,
    }
  },

  async getOhlcv(address: string, interval: OhlcvInterval = '1H'): Promise<OhlcvCandle[]> {
    const secondsByInterval: Record<OhlcvInterval, number> = {
      '1m': 60,
      '5m': 300,
      '30m': 1800,
      '1H': 3600,
      '4H': 14400,
      '1D': 86400,
    }
    const now = Math.floor(Date.now() / 1000)
    const from = now - secondsByInterval[interval] * 180
    const payload = await get<any>(
      `/analysis/ohlcv?address=${encodeURIComponent(address)}&type=${interval}&time_from=${from}&time_to=${now}&currency=usd`,
    )

    return unwrapArray(payload).map((item: any) => ({
      address: item?.address ?? address,
      type: item?.type ?? interval,
      currency: item?.currency ?? 'usd',
      unixTime: Number(item?.unixTime ?? 0),
      o: Number(item?.o ?? 0),
      h: Number(item?.h ?? 0),
      l: Number(item?.l ?? 0),
      c: Number(item?.c ?? 0),
      v: Number(item?.v ?? 0),
    }))
  },

  async getPriceStats(address: string): Promise<TokenPriceStat[]> {
    const payload = await get<any>(
      `/analysis/price-stats?address=${encodeURIComponent(address)}&list_timeframe=1m,1h,24h`,
    )
    const rows = unwrapArray(payload)

    const first = rows[0] ?? {}
    const nested = Array.isArray(first?.data) ? first.data : []

    return nested.map((row: any) => ({
      timeframe: row?.time_frame ?? 'N/A',
      price: Number(row?.price ?? 0),
      priceChangePercent: Number(row?.price_change_percent ?? 0),
      updateUnix: Number(row?.unix_time_update_price ?? 0),
    }))
  },

  async getTradeData(address: string): Promise<TokenTradeData> {
    const payload = await get<any>(`/analysis/trade-data?address=${encodeURIComponent(address)}`)
    const data = payload?.data?.data ?? payload?.data ?? {}
    return {
      holder: Number(data?.holder ?? 0),
      market: Number(data?.market ?? 0),
      totalTrade24h: Number(data?.trade_24h_count ?? data?.trade_24h ?? 0),
      uniqueTrader24h: Number(data?.unique_wallet_24h ?? 0),
      volume24h: Number(data?.volume_24h_usd ?? data?.volume_24h ?? 0),
      buy24h: Number(data?.buy_24h ?? 0),
      sell24h: Number(data?.sell_24h ?? 0),
      lastTradeUnix: Number(data?.last_trade_unix_time ?? 0),
      price: Number(data?.price ?? 0),
      largeOrderFlow: Number(data?.volume_buy_24h_usd ?? 0) - Number(data?.volume_sell_24h_usd ?? 0),
    }
  },

  async getAllTimeTrades(address: string): Promise<TokenLifecycle> {
    const payload = await get<any>(`/analysis/all-time-trades?address=${encodeURIComponent(address)}`)
    const rows = unwrapArray(payload)
    const row = rows[0] ?? {}

    const ath = Number(row?.ath_price ?? row?.highest_price ?? 0)
    const current = Number(row?.current_price ?? row?.last_price ?? 0)

    return {
      totalTrade: Number(row?.total_trade ?? 0),
      totalVolumeUsd: Number(row?.total_volume_usd ?? row?.volume_buy_usd ?? 0) + Number(row?.volume_sell_usd ?? 0),
      buyCount: Number(row?.buy ?? 0),
      sellCount: Number(row?.sell ?? 0),
      ath,
      current,
      drawdownPercent: ath > 0 ? ((current - ath) / ath) * 100 : 0,
    }
  },

  async getSecurity(address: string) {
    const payload = await get<any>(`/analysis/security/${encodeURIComponent(address)}`)
    const raw = payload?.data ?? {}
    return {
      token_address: raw?.mint_address ?? address,
      risk_level: raw?.risk_level,
      score: raw?.risk_score ?? raw?.score,
      mint_authority: raw?.mint_authority ?? null,
      freeze_authority: raw?.freeze_authority ?? null,
      is_renounced: raw?.is_renounced ?? false,
      warning: raw?.error,
    }
  },

  async getActiveFeed(): Promise<{ trending: RadarRow[]; alerts: AlertHistoryEntry[] }> {
    const [trending, alertsPayload] = await Promise.all([
      this.getRadarData(5),
      get<any>('/user/alert-history?limit=5'),
    ])

    const alerts = unwrapArray(alertsPayload).map((row: any) => ({
      id: Number(row?.id ?? 0),
      alert_rule_id: Number(row?.alert_rule_id ?? 0),
      token_address: row?.token_address ?? 'unknown',
      condition_key: row?.condition_key ?? 'signal',
      status: row?.status ?? 'unknown',
      detail: row?.detail,
      sent_at: row?.sent_at ?? new Date().toISOString(),
    }))

    return { trending: trending.slice(0, 5), alerts }
  },

  async saveWatchlist(address: string, symbol: string, tokenName: string): Promise<WatchlistEntry> {
    const payload = await post<any>('/user/watchlist', {
      token_address: address,
      symbol,
      token_name: tokenName,
    })

    return payload?.data
  },

  async getWatchlist(): Promise<WatchlistEntry[]> {
    const payload = await get<any>('/user/watchlist')
    return unwrapArray(payload).map((item: any) => ({
      id: Number(item?.id ?? 0),
      user_id: Number(item?.user_id ?? 0),
      token_address: item?.token_address ?? 'unknown',
      token_name: item?.token_name,
      symbol: item?.symbol,
      created_at: item?.created_at ?? new Date().toISOString(),
      updated_at: item?.updated_at ?? new Date().toISOString(),
    }))
  },
}
