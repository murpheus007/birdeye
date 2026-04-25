import { useParams, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ArrowLeft, Minus, TrendingDown, TrendingUp } from 'lucide-react'
import { LoadingPulse } from '../components/terminal/LoadingPulse'
import { terminalApi } from '../services/terminalApi'

interface WhaleDetail {
  address: string
  pnl: number
  volume: number
  tradeCount: number
  buys: number
  sells: number
  neutral: number
  tokensTouched: number
  successCount: number
  failedCount: number
  avgFeeLamports: number
  recentTrades: Array<{
    signature: string
    timestamp: number | null
    type: 'buy' | 'sell' | 'neutral'
    tokenAddress: string
    tokenDelta: number
    feeLamports: number
    status: 'success' | 'failed'
  }>
}

const shortAddr = (value: string) =>
  value.length > 16 ? `${value.slice(0, 8)}...${value.slice(-6)}` : value

const formatUsd = (value: number) => `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`

const formatLamports = (value: number) => {
  const sol = value / 1_000_000_000
  return `${sol.toLocaleString(undefined, { maximumFractionDigits: 6 })} SOL`
}

const formatDelta = (value: number) => {
  if (value === 0) {
    return '0'
  }
  return value > 0 ? `+${value.toLocaleString(undefined, { maximumFractionDigits: 4 })}` : value.toLocaleString(undefined, { maximumFractionDigits: 4 })
}

const formatRelativeTime = (timestamp: number | null) => {
  if (!timestamp) {
    return 'N/A'
  }
  const now = Math.floor(Date.now() / 1000)
  const diff = Math.max(0, now - timestamp)
  if (diff < 60) {
    return `${diff}s ago`
  }
  if (diff < 3600) {
    return `${Math.floor(diff / 60)}m ago`
  }
  if (diff < 86400) {
    return `${Math.floor(diff / 3600)}h ago`
  }
  return `${Math.floor(diff / 86400)}d ago`
}

const sideBadgeClass = (side: 'buy' | 'sell' | 'neutral') => {
  if (side === 'buy') {
    return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
  }
  if (side === 'sell') {
    return 'border-rose-500/40 bg-rose-500/10 text-rose-300'
  }
  return 'border-zinc-500/40 bg-zinc-500/10 text-zinc-300'
}

const statusBadgeClass = (status: 'success' | 'failed') => {
  return status === 'success'
    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
    : 'border-rose-500/30 bg-rose-500/10 text-rose-300'
}

const WhaleDetailView = () => {
  const { address } = useParams<{ address: string }>()
  const [data, setData] = useState<WhaleDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!address) {
      setError('Invalid wallet address')
      setLoading(false)
      return
    }

    let active = true
    const run = async () => {
      setLoading(true)
      setError(null)

      try {
        const detail = await terminalApi.getWhaleWalletDetail(address, 8)

        let whaleRows: Awaited<ReturnType<typeof terminalApi.getWhaleRows>> = []
        try {
          whaleRows = await Promise.race([
            terminalApi.getWhaleRows(10),
            new Promise<never>((_, reject) =>
              setTimeout(() => reject(new Error('whale board timeout')), 4000),
            ),
          ])
        } catch {
          whaleRows = []
        }

        if (!active) {
          return
        }

        const boardEntry = whaleRows.find((row) => row.address === address)
        const recent = detail.recent_activity
        const successCount = recent.filter((tx) => tx.status === 'success').length
        const failedCount = recent.filter((tx) => tx.status === 'failed').length
        const avgFeeLamports = recent.length
          ? recent.reduce((acc, tx) => acc + tx.fee_lamports, 0) / recent.length
          : 0

        setData({
          address,
          pnl: Number(boardEntry?.pnl ?? 0),
          volume: Number(boardEntry?.volume ?? 0),
          tradeCount: Number(detail.summary.total_transactions ?? boardEntry?.trade_count ?? 0),
          buys: Number(detail.summary.buy_count ?? 0),
          sells: Number(detail.summary.sell_count ?? 0),
          neutral: Number(detail.summary.neutral_count ?? 0),
          tokensTouched: Number(detail.summary.tokens_touched ?? 0),
          successCount,
          failedCount,
          avgFeeLamports,
          recentTrades: recent.map((tx) => ({
            signature: tx.signature,
            timestamp: tx.timestamp,
            type: tx.side,
            tokenAddress: tx.token_address,
            tokenDelta: tx.token_delta,
            feeLamports: tx.fee_lamports,
            status: tx.status,
          })),
        })
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unable to load whale wallet detail')
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
  }, [address])

  return (
    <section className="panel h-full p-4 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
      <div className="mb-4 flex items-center gap-3">
        <Link to="/whales" className="p-1 hover:bg-zinc-800 rounded transition">
          <ArrowLeft className="h-4 w-4 text-zinc-400" />
        </Link>
        <div>
          <p className="panel-title">Whale Profile</p>
          <h1 className="font-mono text-sm text-zinc-300">
            {address ? shortAddr(address) : 'Unknown Wallet'}
          </h1>
        </div>
      </div>

      {loading && <LoadingPulse message="Analyzing whale activity" />}
      {error && <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-300">{error}</div>}

      {!loading && !error && data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-line bg-zinc-900/30 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-[10px] uppercase text-zinc-600 tracking-wide">PnL</p>
              <p className={`text-lg font-mono ${data.pnl >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>{formatUsd(data.pnl)}</p>
            </div>
            <div className="rounded-lg border border-line bg-zinc-900/30 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-[10px] uppercase text-zinc-600 tracking-wide">Volume</p>
              <p className="text-lg font-mono text-zinc-200">{formatUsd(data.volume)}</p>
            </div>
            <div className="rounded-lg border border-line bg-zinc-900/30 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-[10px] uppercase text-zinc-600 tracking-wide">Transactions</p>
              <p className="text-lg font-mono text-zinc-200">{data.tradeCount.toLocaleString()}</p>
            </div>
            <div className="rounded-lg border border-line bg-zinc-900/30 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-[10px] uppercase text-zinc-600 tracking-wide">Tokens Touched</p>
              <p className="text-lg font-mono text-zinc-200">{data.tokensTouched.toLocaleString()}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-line/50 bg-black/30 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-zinc-500">Buy Signals</p>
              <p className="text-xl font-mono text-emerald-300 mt-1">{data.buys}</p>
            </div>
            <div className="rounded-lg border border-line/50 bg-black/30 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-zinc-500">Sell Signals</p>
              <p className="text-xl font-mono text-rose-300 mt-1">{data.sells}</p>
            </div>
            <div className="rounded-lg border border-line/50 bg-black/30 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-zinc-500">Neutral Tx</p>
              <p className="text-xl font-mono text-zinc-200 mt-1">{data.neutral}</p>
            </div>
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-emerald-400">Successful Tx</p>
              <p className="text-lg font-mono text-emerald-300 mt-1">{data.successCount}</p>
            </div>
            <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-rose-400">Failed Tx</p>
              <p className="text-lg font-mono text-rose-300 mt-1">{data.failedCount}</p>
            </div>
            <div className="rounded-lg border border-line/50 bg-black/30 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
              <p className="text-xs text-zinc-500">Avg Network Fee</p>
              <p className="text-xs font-mono text-zinc-200 mt-1">{formatLamports(data.avgFeeLamports)}</p>
            </div>
          </div>

          <div className="rounded-lg border border-line bg-zinc-900/20 p-3 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
            <p className="text-xs uppercase text-zinc-600 tracking-wide mb-3">Recent Activity</p>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {data.recentTrades.map((trade) => (
                <div key={trade.signature} className="flex items-center justify-between gap-2 text-xs p-2 rounded bg-black/40 transition hover:bg-black/60 max-md:rounded-none max-md:bg-transparent max-md:p-0">
                  <div className="flex items-center gap-2">
                    {trade.type === 'buy' ? (
                      <TrendingUp className="h-3 w-3 text-emerald-400" />
                    ) : trade.type === 'sell' ? (
                      <TrendingDown className="h-3 w-3 text-rose-400" />
                    ) : (
                      <Minus className="h-3 w-3 text-zinc-400" />
                    )}
                    <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-[0.08em] ${sideBadgeClass(trade.type)}`}>
                      {trade.type}
                    </span>
                    <span className="font-mono text-zinc-300">{shortAddr(trade.tokenAddress)}</span>
                    <span className={`font-mono ${trade.tokenDelta >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                      {formatDelta(trade.tokenDelta)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-right">
                    <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-[0.08em] ${statusBadgeClass(trade.status)}`}>
                      {trade.status}
                    </span>
                    <span className="font-mono text-zinc-400">fee {trade.feeLamports.toLocaleString()} lamports</span>
                    <span className="text-zinc-600 text-[10px]" title={trade.timestamp ? new Date(trade.timestamp * 1000).toLocaleString() : 'N/A'}>
                      {formatRelativeTime(trade.timestamp)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

export default WhaleDetailView
