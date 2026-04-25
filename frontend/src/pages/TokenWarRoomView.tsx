import { Bell, Shield, TrendingUp, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { CandlestickSeries, LineSeries, createChart, IChartApi, UTCTimestamp } from 'lightweight-charts'
import { motion } from 'framer-motion'
import {
  OhlcvCandle,
  SecurityReport,
  TokenLifecycle,
  TokenOverview,
  TokenPriceStat,
  TokenTradeData,
} from '../types/types'
import { OhlcvInterval, terminalApi } from '../services/terminalApi'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useToast } from '../contexts/ToastContext'

const compact = (value: number) => `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`

const SkeletonCard = () => <div className="h-20 animate-pulse rounded-xl border border-line bg-zinc-900/35" />

const TokenWarRoomView = () => {
  const { address = 'So11111111111111111111111111111111111111112' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { theme } = useTheme()
  const { pushToast } = useToast()

  // Determine where the user came from for the dynamic Back button
  const fromRoute = (location.state as { from?: string } | null)?.from ?? 'radar'
  const backLabel = fromRoute === 'explorer' ? 'Back to Explorer' : fromRoute === 'watchlist' ? 'Back to Watchlist' : 'Back to Radar'
  const backPath = fromRoute === 'explorer' ? '/explorer' : fromRoute === 'watchlist' ? '/watchlist' : '/radar'

  const [overview, setOverview] = useState<TokenOverview | null>(null)
  const [candles, setCandles] = useState<OhlcvCandle[]>([])
  const [security, setSecurity] = useState<SecurityReport | null>(null)
  const [priceStats, setPriceStats] = useState<TokenPriceStat[]>([])
  const [tradeData, setTradeData] = useState<TokenTradeData | null>(null)
  const [lifecycle, setLifecycle] = useState<TokenLifecycle | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chartType, setChartType] = useState<'candlestick' | 'line'>('candlestick')
  const [timeframe, setTimeframe] = useState<OhlcvInterval>('1H')
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false)
  const [targetPriceInput, setTargetPriceInput] = useState('')
  const [priceChangeInput, setPriceChangeInput] = useState('')
  const [alertType, setAlertType] = useState<'webhook' | 'dm'>('webhook')
  const [alertSubmitting, setAlertSubmitting] = useState(false)

  const chartRef = useRef<HTMLDivElement | null>(null)
  const chartInstance = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const lineSeriesRef = useRef<any>(null)

  const readAccentColor = (alpha: number) => {
    const channel = getComputedStyle(document.documentElement).getPropertyValue('--accent-rgb').trim() || '255 143 64'
    return `rgb(${channel} / ${alpha})`
  }

  useEffect(() => {
    let active = true
    const run = async () => {
      setLoading(true)
      setError(null)
      try {
        const [overviewPayload, candlesPayload, securityPayload, statsPayload, tradePayload, lifecyclePayload, watchlist] =
          await Promise.all([
            terminalApi.getTokenOverview(address),
            terminalApi.getOhlcv(address, timeframe),
            terminalApi.getSecurity(address),
            terminalApi.getPriceStats(address),
            terminalApi.getTradeData(address),
            terminalApi.getAllTimeTrades(address),
            terminalApi.getWatchlist(),
          ])
  // Chart persistence: keep existing candles if only timeframe changed (not address)
  // This prevents re-fetching when toggling between Market Cap/FDV views
  const displayedCandlesPayload = candlesPayload && candlesPayload.length > 0 ? candlesPayload : candles

        if (!active) {
          return
        }

        setOverview(overviewPayload)
        setCandles(displayedCandlesPayload)
        setSecurity(securityPayload)
        setPriceStats(statsPayload)
        setTradeData(tradePayload)
        setLifecycle(lifecyclePayload)
        setSaved(watchlist.some((item) => item.token_address === address))
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load war room data')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void run()

    return () => {
      active = false
    }
  }, [address, timeframe])

  useEffect(() => {
    if (!chartRef.current || chartInstance.current) {
      return
    }

    const chart = createChart(chartRef.current, {
      layout: {
        background: { color: '#050505' },
        textColor: '#a1a1aa',
      },
      rightPriceScale: { borderColor: '#27272a' },
      timeScale: { borderColor: '#27272a' },
      grid: {
        vertLines: { color: readAccentColor(0.08) },
        horzLines: { color: readAccentColor(0.08) },
      },
      width: chartRef.current.clientWidth,
      height: 340,
    })

    chartInstance.current = chart

    const resizeObserver = new ResizeObserver(() => {
      if (chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth })
      }
    })
    resizeObserver.observe(chartRef.current)

    return () => {
      resizeObserver.disconnect()
      candlestickSeriesRef.current = null
      lineSeriesRef.current = null
      chartInstance.current = null
      chart.remove()
    }
  }, [theme])

  useEffect(() => {
    const chart = chartInstance.current
    if (!chart || !candles.length) {
      return
    }

    if (candlestickSeriesRef.current) {
      chart.removeSeries(candlestickSeriesRef.current)
      candlestickSeriesRef.current = null
    }

    if (lineSeriesRef.current) {
      chart.removeSeries(lineSeriesRef.current)
      lineSeriesRef.current = null
    }

    if (chartType === 'candlestick') {
      const series = chart.addSeries(CandlestickSeries, {
        upColor: readAccentColor(1),
        downColor: '#f43f5e',
        borderVisible: false,
        wickUpColor: readAccentColor(0.9),
        wickDownColor: '#f43f5e',
      })

      series.setData(
        candles.map((candle) => ({
          time: candle.unixTime as UTCTimestamp,
          open: candle.o,
          high: candle.h,
          low: candle.l,
          close: candle.c,
        })),
      )
      candlestickSeriesRef.current = series
    } else {
      const line = chart.addSeries(LineSeries, {
        color: readAccentColor(1),
        lineWidth: 2,
      })

      line.setData(
        candles.map((candle) => ({
          time: candle.unixTime as UTCTimestamp,
          value: candle.c,
        })),
      )
      lineSeriesRef.current = line
    }

    chart.timeScale().fitContent()
  }, [candles, chartType, theme])

  const activityGrid = useMemo(
    () => [
      { label: 'Total Trades (24h)', value: tradeData?.totalTrade24h?.toLocaleString() ?? '0' },
      { label: 'Unique Traders (24h)', value: tradeData?.uniqueTrader24h?.toLocaleString() ?? '0' },
      { label: 'Large Order Flow', value: compact(Number(tradeData?.largeOrderFlow ?? 0)) },
      { label: 'Volume (24h)', value: compact(Number(tradeData?.volume24h ?? 0)) },
      { label: 'Total Markets', value: tradeData?.market?.toLocaleString() ?? '0' },
      { label: 'Holders', value: tradeData?.holder?.toLocaleString() ?? '0' },
    ],
    [tradeData],
  )

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {overview?.logoURI && (
            <img
              src={overview.logoURI}
              alt={overview.symbol}
              className="h-10 w-10 rounded-full border border-line bg-zinc-900 object-cover"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
            />
          )}
          <div>
            <p className="panel-title">War Room</p>
            <h1 className="font-display text-3xl text-zinc-100">{overview?.symbol ?? 'Token'} Tactical View</h1>
            <p className="font-mono text-xs text-zinc-500">{address}</p>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => {
              setIsAlertModalOpen(true)
            }}
            className="rounded-xl border border-line bg-zinc-900/50 px-3 py-2 text-sm text-zinc-300 hover:border-neonOrange/40"
          >
            <Bell className="mr-1 inline h-4 w-4" />
            Set Alert
          </button>
          <button
            onClick={async () => {
              if (!overview) return
              setSaving(true)
              try {
                await terminalApi.saveWatchlist(address, overview.symbol, overview.name)
                setSaved(true)
                pushToast(`${overview.symbol} added to watchlist.`, 'success')
              } catch (err) {
                pushToast(err instanceof Error ? err.message : 'Failed to add to watchlist', 'error')
              } finally {
                setSaving(false)
              }
            }}
            disabled={saving || saved}
            className="rounded-xl border border-neonOrange/50 bg-neonOrange/15 px-3 py-2 text-sm text-neonOrange disabled:opacity-50"
          >
            {saved ? 'On Watchlist' : saving ? 'Saving...' : 'Add Watchlist'}
          </button>
          <button
            onClick={() => navigate(backPath)}
            className="rounded-xl border border-line px-3 py-2 text-sm text-zinc-300 hover:border-neonOrange/30"
          >
            {backLabel}
          </button>
        </div>
      </div>

      {error && <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div>}

      <motion.div layout className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <div className="rounded-xl border border-line bg-zinc-900/40 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-zinc-500">Market Cap</p>
              <p className="font-mono text-lg text-zinc-100">{compact(Number(overview?.marketCap ?? 0))}</p>
            </div>
            <div className="rounded-xl border border-line bg-zinc-900/40 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-zinc-500">FDV</p>
              <p className="font-mono text-lg text-zinc-100">{compact(Number(overview?.fdv ?? 0))}</p>
            </div>
            <div className="rounded-xl border border-line bg-zinc-900/40 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-zinc-500">Circulating Supply</p>
              <p className="font-mono text-lg text-zinc-100">{Number(overview?.circulatingSupply ?? 0).toLocaleString()}</p>
            </div>
            <div className="rounded-xl border border-line bg-zinc-900/40 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-zinc-500">Security</p>
              <p className="flex items-center gap-1 font-mono text-lg text-zinc-100">
                <Shield className="h-4 w-4 text-neonOrange" />
                {security?.risk_level ?? 'UNKNOWN'}
              </p>
            </div>
          </>
        )}
      </motion.div>

      <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <article className="rounded-xl border border-line bg-zinc-950/60 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
          <div className="mb-2 flex items-center justify-between">
            <p className="panel-title">{chartType === 'candlestick' ? 'Candlestick' : 'Line'} Chart</p>
            <div className="flex items-center gap-2">
              <select
                value={chartType}
                onChange={(event) => setChartType(event.target.value as 'candlestick' | 'line')}
                className="rounded-lg border border-line bg-zinc-900/70 px-2 py-1 text-xs text-zinc-200 outline-none focus:border-neonOrange/60"
              >
                <option value="candlestick">Candlestick</option>
                <option value="line">Line</option>
              </select>
              <select
                value={timeframe}
                onChange={(event) => setTimeframe(event.target.value as OhlcvInterval)}
                className="rounded-lg border border-line bg-zinc-900/70 px-2 py-1 text-xs text-zinc-200 outline-none focus:border-neonOrange/60"
              >
                <option value="1m">1m</option>
                <option value="5m">5m</option>
                <option value="30m">30m</option>
                <option value="1H">1h</option>
                <option value="4H">4h</option>
                <option value="1D">24h</option>
              </select>
              <span className="font-mono text-xs text-zinc-500">/defi/ohlcv · {timeframe === '1D' ? '24h' : timeframe}</span>
            </div>
          </div>
          <div ref={chartRef} className="h-[340px] w-full rounded-lg bg-[#050505]" />
        </article>

        <article className="space-y-3 rounded-xl border border-line bg-zinc-950/60 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
          <div>
            <p className="panel-title">Security Status</p>
            {loading ? (
              <SkeletonCard />
            ) : (
              <div className="mt-2 space-y-2 rounded-lg border border-line bg-black/35 p-3 text-xs max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
                <p className="flex items-center gap-2 text-zinc-200">
                  <Shield className="h-3.5 w-3.5 text-neonOrange" />
                  Mint Authority: {security?.mint_authority ?? 'Renounced'}
                </p>
                <p className="flex items-center gap-2 text-zinc-200">
                  <Shield className="h-3.5 w-3.5 text-neonOrange" />
                  Freeze Authority: {security?.freeze_authority ?? 'Renounced'}
                </p>
                <p className="font-mono text-zinc-400">Risk Score: {security?.score ?? 'N/A'}</p>
              </div>
            )}
          </div>

          <div>
            <p className="panel-title">Life of Token</p>
            {loading ? (
              <SkeletonCard />
            ) : (
              <div className="mt-2 rounded-lg border border-line bg-black/35 p-3 text-xs max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
                <p className="text-zinc-400">ATH vs Current</p>
                <p className="font-mono text-zinc-200">
                  {compact(Number(lifecycle?.ath ?? 0))} / {compact(Number(lifecycle?.current ?? 0))}
                </p>
                <p className="mt-1 text-zinc-400">Drawdown: {Number(lifecycle?.drawdownPercent ?? 0).toFixed(2)}%</p>
              </div>
            )}
          </div>
        </article>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
        <article className="rounded-xl border border-line bg-zinc-950/60 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
          <p className="panel-title">Activity Grid</p>
          {loading ? (
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : (
            <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
              {activityGrid.map((metric) => (
                <div key={metric.label} className="rounded-lg border border-line bg-black/35 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
                  <p className="text-[11px] uppercase tracking-[0.1em] text-zinc-500">{metric.label}</p>
                  <p className="mt-1 font-mono text-sm text-zinc-100">{metric.value}</p>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="rounded-xl border border-line bg-zinc-950/60 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
          <p className="panel-title">Price Stats</p>
          <div className="mt-2 space-y-2">
            {loading ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : (
              priceStats.map((stat) => (
                <div key={stat.timeframe} className="rounded-lg border border-line bg-black/35 p-3 text-xs max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
                  <div className="flex items-center justify-between">
                    <p className="font-display text-zinc-200">{stat.timeframe}</p>
                    <p className={stat.priceChangePercent >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
                      <TrendingUp className="mr-1 inline h-3 w-3" />
                      {stat.priceChangePercent.toFixed(2)}%
                    </p>
                  </div>
                  <p className="mt-1 font-mono text-zinc-400">Price: {compact(stat.price)}</p>
                  <p className="font-mono text-zinc-500">Updated: {new Date(stat.updateUnix * 1000).toLocaleTimeString()}</p>
                </div>
              ))
            )}
          </div>
        </article>
      </div>

      {isAlertModalOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-line bg-[#0b0b0b] p-4 max-md:rounded-none max-md:border-0 max-md:bg-[#0b0b0b] max-md:p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="panel-title">Alert Config</p>
                <h2 className="font-display text-xl text-zinc-100">Set Price Alert</h2>
              </div>
              <button
                onClick={() => setIsAlertModalOpen(false)}
                className="rounded-lg border border-line p-2 text-zinc-500 hover:text-zinc-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {!isAuthenticated && (
              <p className="mb-3 rounded-lg border border-rose-400/40 bg-rose-500/10 p-2 text-xs text-rose-300">
                Sign in with your wallet from the top bar before creating alerts.
              </p>
            )}

            {tradeData?.price != null && (
              <div className="mb-3 rounded-lg border border-neonOrange/30 bg-neonOrange/8 px-3 py-2 text-xs text-zinc-300">
                Current Price:{' '}
                <span className="font-mono font-semibold text-neonOrange">
                  ${tradeData.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 8 })}
                </span>
              </div>
            )}

            <div className="space-y-3">
              <label className="block text-xs text-zinc-500">
                Target Price ($)
                <input
                  value={targetPriceInput}
                  onChange={(event) => setTargetPriceInput(event.target.value)}
                  placeholder="0.125"
                  className="mt-1 h-10 w-full rounded-lg border border-line bg-zinc-900/60 px-3 text-sm text-zinc-100 outline-none focus:border-neonOrange/50"
                />
              </label>

              <label className="block text-xs text-zinc-500">
                Price Change (%)
                <input
                  value={priceChangeInput}
                  onChange={(event) => setPriceChangeInput(event.target.value)}
                  placeholder="10"
                  className="mt-1 h-10 w-full rounded-lg border border-line bg-zinc-900/60 px-3 text-sm text-zinc-100 outline-none focus:border-neonOrange/50"
                />
              </label>

              <label className="block text-xs text-zinc-500">
                Delivery Type
                <select
                  value={alertType}
                  onChange={(event) => setAlertType(event.target.value as 'webhook' | 'dm')}
                  className="mt-1 h-10 w-full rounded-lg border border-line bg-zinc-900/60 px-3 text-sm text-zinc-100 outline-none focus:border-neonOrange/50"
                >
                  <option value="webhook">Webhook</option>
                  <option value="dm">Discord DM</option>
                </select>
              </label>

              {(targetPriceInput || priceChangeInput) && (
                <p className="rounded-lg border border-line bg-zinc-900/40 px-3 py-2 text-xs text-zinc-400">
                  {targetPriceInput && priceChangeInput
                    ? `Triggers if price hits $${targetPriceInput} or changes by ${priceChangeInput}%`
                    : targetPriceInput
                      ? `Triggers if price hits $${targetPriceInput}`
                      : `Triggers if price changes by ${priceChangeInput}%`}
                </p>
              )}

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setIsAlertModalOpen(false)}
                  className="rounded-lg border border-line px-3 py-2 text-xs text-zinc-300"
                >
                  Cancel
                </button>
                <button
                  disabled={alertSubmitting || !isAuthenticated}
                  onClick={async () => {
                    const alertDescription = targetPriceInput && priceChangeInput
                      ? `Triggers if price hits $${targetPriceInput} or changes by ${priceChangeInput}%`
                      : targetPriceInput
                        ? `Triggers if price hits $${targetPriceInput}`
                        : priceChangeInput
                          ? `Triggers if price changes by ${priceChangeInput}%`
                          : undefined
                    setAlertSubmitting(true)
                    try {
                      await terminalApi.createAlert({
                        token_address: address,
                        token_name: overview?.name ?? overview?.symbol,
                        token_logo_url: overview?.logoURI,
                        alert_description: alertDescription,
                        target_price: targetPriceInput ? Number(targetPriceInput) : undefined,
                        price_change_percent: priceChangeInput ? Number(priceChangeInput) : undefined,
                        alert_type: alertType,
                      })
                      setIsAlertModalOpen(false)
                      pushToast('New alert created successfully.', 'success')
                    } catch (err) {
                      const message = err instanceof Error ? err.message : 'Failed to create alert'
                      if (message.includes('discord_user_id is required')) {
                        pushToast('Discord User ID is missing for DM alerts. Add it in Settings.', 'error')
                      } else {
                        pushToast(message, 'error')
                      }
                    } finally {
                      setAlertSubmitting(false)
                    }
                  }}
                  className="rounded-lg border border-neonOrange/50 bg-neonOrange/15 px-3 py-2 text-xs text-neonOrange disabled:opacity-50"
                >
                  {alertSubmitting ? 'Creating...' : 'Create Alert'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

export default TokenWarRoomView
