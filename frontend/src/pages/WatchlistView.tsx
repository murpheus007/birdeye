import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bookmark, Trash2 } from 'lucide-react'
import { terminalApi } from '../services/terminalApi'
import { WatchlistEntry } from '../types/types'
import { LoadingPulse } from '../components/terminal/LoadingPulse'
import { useToast } from '../contexts/ToastContext'

const WatchlistView = () => {
  const [items, setItems] = useState<WatchlistEntry[]>([])
  const [metrics, setMetrics] = useState<Record<string, { price: number; change24h: number }>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { pushToast } = useToast()

  const loadWatchlist = async () => {
    try {
      setError(null)
      const payload = await terminalApi.getWatchlist()
      setItems(payload)

      const stats = await Promise.all(
        payload.map(async (item) => {
          try {
            const priceStats = await terminalApi.getPriceStats(item.token_address)
            const day = priceStats.find((row) => row.timeframe === '24h') ?? priceStats[priceStats.length - 1]
            return {
              address: item.token_address,
              price: Number(day?.price ?? 0),
              change24h: Number(day?.priceChangePercent ?? 0),
            }
          } catch {
            return {
              address: item.token_address,
              price: 0,
              change24h: 0,
            }
          }
        }),
      )

      setMetrics(
        stats.reduce<Record<string, { price: number; change24h: number }>>((acc, row) => {
          acc[row.address] = { price: row.price, change24h: row.change24h }
          return acc
        }, {}),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load watchlist')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    void loadWatchlist()

    const interval = setInterval(() => {
      if (active) {
        void loadWatchlist()
      }
    }, 60000) // Refresh every minute

    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  const handleRemove = async (id: number) => {
    // TODO: Implement delete endpoint in backend
    setItems(items.filter((item) => item.id !== id))
    pushToast('Removed from watchlist.', 'success')
  }

  return (
    <section className="panel h-full p-4 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="panel-title">Watchlist</p>
          <h1 className="font-display text-2xl text-zinc-100">Tracked Assets</h1>
        </div>
        <Bookmark className="h-5 w-5 text-neonOrange" />
      </div>

      {loading && <LoadingPulse message="Loading watchlist" />}
      {error && <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-300">{error}</div>}

      {!loading && !error && items.length === 0 && (
        <div className="text-center py-8 text-zinc-400">
          <p className="text-sm">No items in watchlist yet</p>
          <Link to="/explorer" className="text-xs text-neonOrange hover:underline mt-2 inline-block">
            Explore tokens →
          </Link>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.id} className="flex items-center justify-between rounded-lg border border-line bg-zinc-900/30 p-3 transition hover:bg-zinc-900/50 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <Link to={`/token/${item.token_address}`} state={{ from: 'watchlist' }} className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-line bg-zinc-800 text-xs font-display text-neonOrange">
                    {(item.symbol ?? '?').slice(0, 2)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-sm text-neonOrange truncate">{item.symbol}</p>
                    <p className="text-xs text-zinc-400 truncate">{item.token_name}</p>
                    <div className="mt-1 flex items-center gap-3 text-[11px]">
                      <span className="font-mono text-zinc-500">
                        Price ${Number(metrics[item.token_address]?.price ?? 0).toLocaleString(undefined, { maximumFractionDigits: 6 })}
                      </span>
                      <span
                        className={`font-mono ${Number(metrics[item.token_address]?.change24h ?? 0) >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}
                      >
                        24h {Number(metrics[item.token_address]?.change24h ?? 0).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
              <button
                onClick={() => handleRemove(item.id)}
                className="ml-2 p-1.5 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition"
                title="Remove from watchlist"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default WatchlistView
