import { useEffect, useState } from 'react'
import { Bell, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { terminalApi } from '../services/terminalApi'
import { AlertRuleEntry } from '../types/types'
import ConnectWalletButton from '../components/terminal/ConnectWalletButton'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'

const AlertsView = () => {
  const { isAuthenticated } = useAuth()
  const { pushToast } = useToast()
  const navigate = useNavigate()
  const [alerts, setAlerts] = useState<AlertRuleEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const loadAlerts = async () => {
    if (!isAuthenticated) {
      setAlerts([])
      setLoading(false)
      return
    }

    setLoading(true)
    setLoadError(null)
    try {
      const rows = await terminalApi.listMyAlerts()
      setAlerts(rows)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAlerts()
  }, [isAuthenticated])

  const handleDelete = async (id: number, event: React.MouseEvent) => {
    event.stopPropagation()
    try {
      await terminalApi.deleteAlert(id)
      setAlerts((previous) => previous.filter((entry) => entry.id !== id))
      pushToast('Alert deleted successfully.', 'success')
    } catch (err) {
      pushToast(err instanceof Error ? err.message : 'Failed to delete alert', 'error')
    }
  }

  return (
    <section className="panel h-full p-4 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="panel-title">Alerts</p>
          <h1 className="font-display text-2xl text-zinc-100">Alerts Manager</h1>
        </div>
        <Bell className="h-5 w-5 text-neonOrange" />
      </div>

      {!isAuthenticated && (
        <div className="mb-4 rounded-2xl border-2 border-neonOrange/30 bg-neonOrange/8 p-4 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
          <p className="text-sm text-zinc-200">Connect and sign in with your wallet to view and manage your active alerts.</p>
          <p className="mt-1 text-xs text-zinc-400">Your alerts are tied to the connected wallet identity.</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <ConnectWalletButton />
          </div>
        </div>
      )}

      {loading && isAuthenticated && <p className="text-sm text-zinc-400">Loading alerts...</p>}
      {loadError && <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">{loadError}</div>}

      {!loading && !loadError && isAuthenticated && alerts.length === 0 && (
        <div className="rounded-xl border border-line bg-zinc-900/20 p-4 text-sm text-zinc-400 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">No active alerts yet.</div>
      )}

      {!loading && !loadError && isAuthenticated && alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              onClick={() => navigate(`/token/${alert.token_address}`, { state: { from: 'alerts' } })}
              className="flex cursor-pointer items-center justify-between rounded-xl border border-line bg-zinc-900/30 p-3 transition-colors hover:border-neonOrange/30 hover:bg-zinc-900/50 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0"
            >
              <div className="flex min-w-0 items-center gap-3">
                {alert.token_logo_url ? (
                  <img
                    src={alert.token_logo_url}
                    alt={alert.token_name ?? alert.token_address}
                    className="h-8 w-8 flex-shrink-0 rounded-full border border-line bg-zinc-900 object-cover"
                    onError={(e) => {
                      ;(e.currentTarget as HTMLImageElement).style.display = 'none'
                    }}
                  />
                ) : (
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-line bg-zinc-800 text-xs font-bold text-zinc-400">
                    {(alert.token_name ?? alert.token_address.slice(0, 4)).slice(0, 2).toUpperCase()}
                  </div>
                )}
                <div className="min-w-0 space-y-0.5">
                  <div className="flex items-center gap-2">
                    <p className="truncate font-mono text-sm text-zinc-100">
                      {alert.token_name ?? `${alert.token_address.slice(0, 6)}...${alert.token_address.slice(-4)}`}
                    </p>
                    <span
                      className={`flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                        alert.status === 'triggered'
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : 'bg-neonOrange/15 text-neonOrange'
                      }`}
                    >
                      {alert.status === 'triggered' ? 'Triggered' : 'Active'}
                    </span>
                  </div>
                  {alert.alert_description ? (
                    <p className="text-xs text-zinc-400">{alert.alert_description}</p>
                  ) : (
                    <p className="text-xs text-zinc-400">
                      {alert.target_price != null ? `Target $${alert.target_price.toLocaleString()}` : ''}
                      {alert.target_price != null && alert.price_change_percent_threshold != null ? ' · ' : ''}
                      {alert.price_change_percent_threshold != null
                        ? `Change ${alert.price_change_percent_threshold.toFixed(2)}%`
                        : ''}
                      {alert.target_price == null && alert.price_change_percent_threshold == null ? 'No conditions set' : ''}
                    </p>
                  )}
                  <p className="text-[11px] uppercase tracking-[0.12em] text-zinc-500">via {alert.delivery_channel}</p>
                </div>
              </div>

              <button
                onClick={(e) => {
                  void handleDelete(alert.id, e)
                }}
                className="ml-2 flex-shrink-0 rounded-lg border border-line p-2 text-zinc-500 hover:border-rose-400/50 hover:bg-rose-500/10 hover:text-rose-300"
                title="Delete alert"
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

export default AlertsView
