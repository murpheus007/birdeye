import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { WhaleWatchItem } from '../types/types'
import { terminalApi } from '../services/terminalApi'
import { LoadingPulse } from '../components/terminal/LoadingPulse'

const format = (value: number) => `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`

type WhaleMode = 'gainers' | 'losers'

const WhalesView = () => {
  const [rows, setRows] = useState<WhaleWatchItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<WhaleMode>('gainers')

  const loadWhaleData = async () => {
    try {
      setError(null)
      const payload = await terminalApi.getWhaleRows(10)
      setRows(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load whale activity')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    setLoading(true)
    void loadWhaleData()

    const interval = setInterval(() => {
      if (active) {
        void loadWhaleData()
      }
    }, 60000) // Refresh every minute

    return () => {
      active = false
      clearInterval(interval)
    }
  }, [mode])

  const sorted = useMemo(() => [...rows].sort((a, b) => (b.pnl ?? 0) - (a.pnl ?? 0)), [rows])
  const visibleRows = useMemo(() => {
    if (mode === 'losers') {
      return sorted.filter((item) => Number(item.pnl ?? 0) < 0)
    }
    return sorted
  }, [mode, sorted])

  return (
    <section className="panel h-full p-4 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
      <div className="mb-4">
        <p className="panel-title">Whales</p>
        <h1 className="font-display text-2xl text-zinc-100">Gainers / Losers War Board</h1>
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => setMode('gainers')}
            className={`rounded-lg border px-3 py-1 text-xs ${
              mode === 'gainers' ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-300' : 'border-line text-zinc-400'
            }`}
          >
            Gainers
          </button>
          <button
            onClick={() => setMode('losers')}
            className={`rounded-lg border px-3 py-1 text-xs ${
              mode === 'losers' ? 'border-rose-500/60 bg-rose-500/10 text-rose-300' : 'border-line text-zinc-400'
            }`}
          >
            Losers
          </button>
        </div>
      </div>

      {loading && <LoadingPulse message="Analyzing whale activity" />}
      {error && <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-300">{error}</div>}

      {!loading && !error && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {visibleRows.map((item) => {
            const isProfitable = (item.pnl ?? 0) >= 0
            return (
              <Link
                key={item.address}
                to={`/whale/${item.address}`}
                className="group rounded-xl border border-line bg-zinc-900/40 p-3 transition hover:border-neonOrange/50 hover:bg-zinc-900/60 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="font-mono text-xs text-zinc-200 group-hover:text-neonOrange transition">
                    {item.address.length > 16 ? `${item.address.slice(0, 8)}...${item.address.slice(-6)}` : item.address}
                  </p>
                  <p className={`font-mono text-xs ${isProfitable ? 'text-emerald-300' : 'text-rose-300'}`}>
                    {isProfitable ? '+' : ''}{format(Number(item.pnl ?? 0))}
                  </p>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-zinc-400">
                  <div className="rounded-md bg-black/35 p-2">
                    <p className="text-zinc-500">Volume</p>
                    <p className="font-mono text-zinc-200">{format(Number(item.volume ?? 0))}</p>
                  </div>
                  <div className="rounded-md bg-black/35 p-2">
                    <p className="text-zinc-500">Trades</p>
                    <p className="font-mono text-zinc-200">{Number(item.trade_count ?? 0).toLocaleString()}</p>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}

      {!loading && !error && mode === 'losers' && !visibleRows.length && (
        <div className="mt-3 rounded-xl border border-line bg-zinc-900/30 p-3 text-xs text-zinc-500">
          No negative-PnL wallets are being returned by the current Birdeye whale endpoint at this time.
        </div>
      )}
    </section>
  )
}

export default WhalesView
