import { AlertHistoryEntry } from '../../types/types'
import { RadarRow } from '../../services/terminalApi'

type ActiveFeedDropdownProps = {
  open: boolean
  trending: RadarRow[]
  alerts: AlertHistoryEntry[]
  onTokenClick: (address: string) => void
  onClose: () => void
}

const compact = (value: string) => (value.length > 14 ? `${value.slice(0, 6)}...${value.slice(-4)}` : value)

const ActiveFeedDropdown = ({ open, trending, alerts, onTokenClick, onClose }: ActiveFeedDropdownProps) => {
  if (!open) {
    return null
  }

  return (
    <div className="absolute right-0 top-12 z-30 w-[440px] rounded-2xl border border-line bg-black/95 p-4 shadow-neon">
      <div className="mb-3 flex items-center justify-between">
        <p className="panel-title">Active Feed</p>
        <button onClick={onClose} className="font-mono text-xs text-zinc-500 hover:text-zinc-300">
          Close
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <section className="rounded-xl border border-line bg-zinc-900/40 p-3">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-zinc-500">Top 5 Trending</p>
          <div className="space-y-2">
            {(trending.length ? trending : []).slice(0, 5).map((token) => (
              <button
                key={token.address}
                onClick={() => onTokenClick(token.address)}
                className="w-full rounded-lg bg-black/35 px-2 py-1.5 text-left transition hover:bg-neonOrange/10"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-display text-zinc-100">{token.symbol}</span>
                  <span className={token.priceChange24h >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
                    {token.priceChange24h.toFixed(2)}%
                  </span>
                </div>
                <div className="font-mono text-[11px] text-zinc-500">{compact(token.address)}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-line bg-zinc-900/40 p-3">
          <p className="mb-2 text-xs uppercase tracking-[0.18em] text-zinc-500">Recent Alerts</p>
          <div className="space-y-2">
            {alerts.length ? (
              alerts.slice(0, 5).map((alert) => (
                <button
                  key={alert.id}
                  onClick={() => onTokenClick(alert.token_address)}
                  className="w-full rounded-lg bg-black/35 px-2 py-1.5 text-left transition hover:bg-neonOrange/10"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-zinc-100">{compact(alert.token_address)}</span>
                    <span className="text-neonOrange">{alert.status}</span>
                  </div>
                  <div className="text-[11px] text-zinc-500">{alert.condition_key}</div>
                </button>
              ))
            ) : (
              <p className="text-xs text-zinc-500">No alerts yet.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

export default ActiveFeedDropdown
