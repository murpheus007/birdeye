import { useCallback, useEffect, useState } from 'react'
import { AlertHistoryEntry, TokenData, WatchlistEntry, WhaleWatchItem } from '../types/types'

type CommandCenterData = {
  trending: TokenData[]
  whaleWatch: WhaleWatchItem[]
  watchlist: WatchlistEntry[]
  alertHistory: AlertHistoryEntry[]
}

type HookState = {
  data: CommandCenterData | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

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
const DEMO_USER_ID = import.meta.env.VITE_DEFAULT_USER_ID ?? '1'

const fetchJson = async (url: string): Promise<{ ok: boolean; status: number; data: any }> => {
  const response = await fetch(url)
  const payload = await response.json().catch(() => ({}))
  return { ok: response.ok, status: response.status, data: payload }
}

const unwrapList = (payload: any): any[] => {
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

export const useCommandCenterData = (): HookState => {
  const [data, setData] = useState<CommandCenterData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const endpoints = {
        trending: `${API_BASE}/analysis/trending?limit=5`,
        whaleWatch: `${API_BASE}/analysis/whale-watch?limit=5`,
        watchlist: `${API_BASE}/user/watchlist?user_id=${encodeURIComponent(DEMO_USER_ID)}`,
        alertHistory: `${API_BASE}/user/alert-history?user_id=${encodeURIComponent(DEMO_USER_ID)}&limit=5`,
      }

      const [trendingRes, whaleWatchRes, watchlistRes, alertHistoryRes] = await Promise.all([
        fetchJson(endpoints.trending),
        fetchJson(endpoints.whaleWatch),
        fetchJson(endpoints.watchlist),
        fetchJson(endpoints.alertHistory),
      ])

      const failedEndpoints: string[] = []
      if (!trendingRes.ok) failedEndpoints.push(`trending (${trendingRes.status})`)
      if (!whaleWatchRes.ok) failedEndpoints.push(`whale-watch (${whaleWatchRes.status})`)
      if (!watchlistRes.ok) failedEndpoints.push(`watchlist (${watchlistRes.status})`)
      if (!alertHistoryRes.ok) failedEndpoints.push(`alert-history (${alertHistoryRes.status})`)

      if (failedEndpoints.length > 0) {
        setError(`Some feed panels are using fallback data: ${failedEndpoints.join(', ')}`)
      }

      const trending = unwrapList(trendingRes.data).map((item: any) => ({
        token_address: item?.address ?? item?.token_address ?? 'unknown',
        token_name: item?.name ?? item?.token_name ?? item?.symbol ?? 'Unknown',
        symbol: item?.symbol,
        current_price: item?.price ?? item?.current_price,
        security_rating: item?.score ?? item?.security_rating,
        volume24h: item?.volume_24h ?? item?.volume24h ?? item?.volume24hUSD ?? item?.volume,
        price_change_24h:
          item?.price_change_24h ?? item?.price24hChangePercent ?? item?.change_24h ?? item?.change24h,
      }))

      const whaleWatch = unwrapList(whaleWatchRes.data).map((item: any) => ({
        address: item?.address ?? item?.wallet_address ?? 'unknown',
        network: item?.network,
        pnl: item?.pnl,
        volume: item?.volume,
        trade_count: item?.trade_count,
      }))

      const watchlist = unwrapList(watchlistRes.data).map((item: any) => ({
        id: item?.id,
        user_id: item?.user_id,
        token_address: item?.token_address,
        token_name: item?.token_name,
        symbol: item?.symbol,
        created_at: item?.created_at,
        updated_at: item?.updated_at,
      }))

      const alertHistory = unwrapList(alertHistoryRes.data).map((item: any) => ({
        id: item?.id,
        alert_rule_id: item?.alert_rule_id,
        token_address: item?.token_address,
        condition_key: item?.condition_key,
        status: item?.status,
        detail: item?.detail,
        sent_at: item?.sent_at,
      }))

      setData({ trending, whaleWatch, watchlist, alertHistory })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error while loading command center data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { data, loading, error, refresh }
}