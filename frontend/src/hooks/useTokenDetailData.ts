import { useCallback, useEffect, useState } from 'react'
import { OhlcvCandle, SecurityReport, TokenData, WatchlistEntry } from '../types/types'

type TokenDetailData = {
  summary: TokenData | null
  security: SecurityReport | null
  candles: OhlcvCandle[]
  watchlist: WatchlistEntry[]
}

type HookState = {
  data: TokenDetailData | null
  loading: boolean
  saving: boolean
  saved: boolean
  error: string | null
  refresh: () => Promise<void>
  saveToWatchlist: () => Promise<void>
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

const fetchJson = async (url: string, options?: RequestInit): Promise<{ ok: boolean; status: number; data: any }> => {
  const response = await fetch(url, options)
  const payload = await response.json().catch(() => ({}))
  return { ok: response.ok, status: response.status, data: payload }
}

const unwrapList = (payload: any): any[] => {
  const candidates = [payload?.data?.items, payload?.data?.data?.items, payload?.data?.data, payload?.data, payload?.items]
  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate
    }
  }
  return []
}

export const useTokenDetailData = (address: string | undefined): HookState => {
  const [data, setData] = useState<TokenDetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!address) {
      setError('Token address is required')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const now = Math.floor(Date.now() / 1000)
      const timeFrom = now - 86400
      const endpoints = {
        summary: `${API_BASE}/analysis/token-summary?address=${encodeURIComponent(address)}`,
        security: `${API_BASE}/analysis/security/${encodeURIComponent(address)}`,
        ohlcv: `${API_BASE}/analysis/ohlcv?address=${encodeURIComponent(address)}&type=1H&time_from=${timeFrom}&time_to=${now}&currency=usd`,
        watchlist: `${API_BASE}/user/watchlist?user_id=${encodeURIComponent(DEMO_USER_ID)}`,
      }

      const [summaryRes, securityRes, ohlcvRes, watchlistRes] = await Promise.all([
        fetchJson(endpoints.summary),
        fetchJson(endpoints.security),
        fetchJson(endpoints.ohlcv),
        fetchJson(endpoints.watchlist),
      ])

      const summaryJson = summaryRes.data
      const securityJson = securityRes.data
      const ohlcvJson = ohlcvRes.data
      const watchlistJson = watchlistRes.data

      const summary: TokenData = summaryJson?.data ?? {
        token_address: address,
        token_name: address.slice(0, 6),
        symbol: 'TKN',
        current_price: 0,
      }

      const securityPayload = securityJson?.data ?? {}
      const candles = unwrapList(ohlcvJson).map((item: any) => ({
        address: item?.address ?? address,
        type: item?.type ?? '1H',
        currency: item?.currency ?? 'usd',
        unixTime: item?.unixTime ?? item?.unix_time ?? 0,
        o: Number(item?.o ?? item?.open ?? 0),
        h: Number(item?.h ?? item?.high ?? 0),
        l: Number(item?.l ?? item?.low ?? 0),
        c: Number(item?.c ?? item?.close ?? 0),
        v: Number(item?.v ?? item?.volume ?? 0),
      }))

      const watchlist = unwrapList(watchlistJson).map((item: any) => ({
        id: item?.id,
        user_id: item?.user_id,
        token_address: item?.token_address,
        token_name: item?.token_name,
        symbol: item?.symbol,
        created_at: item?.created_at,
        updated_at: item?.updated_at,
      }))

      setData({
        summary,
        security: {
          token_address: address,
          tokenName: securityPayload?.tokenName ?? summary.token_name,
          score: securityPayload?.risk_score ?? securityPayload?.score,
          warning: securityPayload?.error,
          risk_level: securityPayload?.risk_level,
          mint_authority: securityPayload?.mint_authority,
          freeze_authority: securityPayload?.freeze_authority,
          is_renounced: securityPayload?.is_renounced,
        },
        candles,
        watchlist,
      })

      setSaved(watchlist.some((item) => item.token_address === address))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error while loading token detail')
    } finally {
      setLoading(false)
    }
  }, [address])

  const saveToWatchlist = useCallback(async () => {
    if (!address) {
      return
    }

    setSaving(true)
    try {
      const response = await fetchJson(`${API_BASE}/user/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: Number(DEMO_USER_ID),
          token_address: address,
          token_name: data?.summary?.token_name ?? address,
          symbol: data?.summary?.symbol ?? 'TKN',
        }),
      })

      if (!response.ok) {
        throw new Error(response.data?.error ?? `Watchlist save failed (${response.status})`)
      }

      setSaved(true)
    } finally {
      setSaving(false)
    }
  }, [address, data?.summary?.symbol, data?.summary?.token_name])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { data, loading, saving, saved, error, refresh, saveToWatchlist }
}