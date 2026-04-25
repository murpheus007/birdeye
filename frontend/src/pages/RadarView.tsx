import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Flame, TrendingDown, TrendingUp } from 'lucide-react'
import { useMemo, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { RadarRow, terminalApi } from '../services/terminalApi'
import { LoadingPulse } from '../components/terminal/LoadingPulse'

type RadarFilter = 'gainers' | 'losers' | 'volume' | 'hot'

const numberFmt = (value: number) =>
  `$${value.toLocaleString(undefined, { maximumFractionDigits: value > 1 ? 2 : 6 })}`

const RadarView = () => {
  const navigate = useNavigate()
  const [rows, setRows] = useState<RadarRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<RadarFilter>('volume')

  const loadRadarData = async () => {
    try {
      setError(null)
      const payload = await terminalApi.getRadarData(100)
      setRows(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load trending tokens')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    setLoading(true)
    void loadRadarData()

    const interval = setInterval(() => {
      if (active) {
        void loadRadarData()
      }
    }, 60000) // Refresh every minute

    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  const filteredRows = useMemo(() => {
    let base = [...rows]
    if (mode === 'hot') {
      base = base.filter((r) => r.isHot)
      return base.sort((a, b) => b.priceChange24h - a.priceChange24h)
    }
    if (mode === 'gainers') {
      return base.sort((a, b) => b.priceChange24h - a.priceChange24h)
    }
    if (mode === 'losers') {
      return base.sort((a, b) => a.priceChange24h - b.priceChange24h)
    }
    return base.sort((a, b) => b.volume24h - a.volume24h)
  }, [rows, mode])

  const columns = useMemo<ColumnDef<RadarRow>[]>(
    () => [
      {
        header: 'Token',
        accessorKey: 'symbol',
        cell: ({ row }) => {
          const token = row.original
          return (
            <div className="group flex items-center gap-2">
              {token.logoURI ? (
                <img
                  src={token.logoURI}
                  alt={token.symbol}
                  className="h-6 w-6 rounded-full border border-line bg-zinc-900 object-cover flex-shrink-0"
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
                />
              ) : (
                <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-line bg-zinc-800 text-[10px] font-display text-neonOrange">
                  {token.symbol.slice(0, 1)}
                </div>
              )}
              <span className="font-display text-zinc-100 group-hover:text-neonOrange">{token.symbol}</span>
              <span className="hidden text-xs text-zinc-500 xl:inline">{token.name}</span>
              {token.isHot && (
                <span className="rounded-full border border-neonOrange/50 bg-neonOrange/15 px-1.5 py-0.5 text-[10px] text-neonOrange">
                  HOT
                </span>
              )}
            </div>
          )
        },
      },
      {
        header: 'Price',
        accessorKey: 'price',
        cell: ({ row }) => <span className="font-mono text-xs text-zinc-200">{numberFmt(row.original.price)}</span>,
      },
      {
        header: '24h %',
        accessorKey: 'priceChange24h',
        cell: ({ row }) => {
          const value = row.original.priceChange24h
          const positive = value >= 0
          return <span className={`font-mono text-xs ${positive ? 'text-emerald-300' : 'text-rose-300'}`}>{value.toFixed(2)}%</span>
        },
      },
      {
        header: 'Volume',
        accessorKey: 'volume24h',
        cell: ({ row }) => <span className="font-mono text-xs text-zinc-300">{numberFmt(row.original.volume24h)}</span>,
      },
      {
        header: 'Liquidity',
        accessorKey: 'liquidity',
        cell: ({ row }) => <span className="font-mono text-xs text-zinc-300">{numberFmt(row.original.liquidity)}</span>,
      },
      {
        header: 'FDV',
        accessorKey: 'fdv',
        cell: ({ row }) => <span className="font-mono text-xs text-zinc-300">{numberFmt(row.original.fdv)}</span>,
      },
      {
        header: 'Buy/Sell',
        accessorKey: 'buySellRatio',
        cell: ({ row }) => {
          const ratio = row.original.buySellRatio
          const color = ratio >= 1 ? 'text-emerald-300' : 'text-rose-300'
          return <span className={`font-mono text-xs ${color}`}>{ratio.toFixed(2)}x</span>
        },
      },
    ],
    [],
  )

  const table = useReactTable({
    data: filteredRows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 12 } },
  })

  return (
    <section className="panel h-full p-4 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="panel-title">Radar</p>
          <h1 className="font-display text-2xl text-zinc-100">Meme & Trending Matrix</h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setMode('hot')}
            className={`rounded-lg border px-3 py-1.5 text-xs ${mode === 'hot' ? 'border-neonOrange/70 bg-neonOrange/15 text-neonOrange' : 'border-line text-zinc-400'}`}
          >
            <Flame className="mr-1 inline h-3 w-3" />
            Trending Hot
          </button>
          <button
            onClick={() => setMode('gainers')}
            className={`rounded-lg border px-3 py-1.5 text-xs ${mode === 'gainers' ? 'border-emerald-500/60 bg-emerald-500/15 text-emerald-300' : 'border-line text-zinc-400'}`}
          >
            <TrendingUp className="mr-1 inline h-3 w-3" />
            Highest Gainers
          </button>
          <button
            onClick={() => setMode('losers')}
            className={`rounded-lg border px-3 py-1.5 text-xs ${mode === 'losers' ? 'border-rose-500/60 bg-rose-500/15 text-rose-300' : 'border-line text-zinc-400'}`}
          >
            <TrendingDown className="mr-1 inline h-3 w-3" />
            Biggest Losers
          </button>
          <button
            onClick={() => setMode('volume')}
            className={`rounded-lg border px-3 py-1.5 text-xs ${mode === 'volume' ? 'border-neonOrange/70 bg-neonOrange/15 text-neonOrange' : 'border-line text-zinc-400'}`}
          >
            <Flame className="mr-1 inline h-3 w-3" />
            Volume Leaders
          </button>
        </div>
      </div>

      {loading && <LoadingPulse message="Loading trending tokens" />}
      {error && <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-300">{error}</div>}

      {!loading && !error && (
        <>
          <div className="space-y-2 md:hidden">
            {filteredRows.slice(0, 40).map((token) => {
              const positive = token.priceChange24h >= 0
              return (
                <button
                  key={token.address}
                  onClick={() => navigate(`/token/${token.address}`, { state: { from: 'radar' } })}
                  className="w-full rounded-2xl border border-line/70 bg-zinc-900/35 p-3 text-left transition hover:border-neonOrange/50 hover:bg-neonOrange/8"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0 flex items-center gap-2">
                      {token.logoURI ? (
                        <img
                          src={token.logoURI}
                          alt={token.symbol}
                          className="h-8 w-8 rounded-full border border-line bg-zinc-900 object-cover"
                          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
                        />
                      ) : (
                        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-line bg-zinc-800 text-[10px] font-display text-neonOrange">
                          {token.symbol.slice(0, 1)}
                        </div>
                      )}
                      <div className="min-w-0">
                        <p className="truncate font-display text-zinc-100">{token.symbol}</p>
                        <p className="truncate text-[11px] text-zinc-500">{token.name}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-xs text-zinc-200">{numberFmt(token.price)}</p>
                      <p className={`font-mono text-xs ${positive ? 'text-emerald-300' : 'text-rose-300'}`}>
                        {token.priceChange24h.toFixed(2)}%
                      </p>
                    </div>
                  </div>

                  <div className="mt-2 grid grid-cols-3 gap-2 text-[10px]">
                    <div className="rounded-lg border border-line/60 bg-black/35 px-2 py-1">
                      <p className="text-zinc-500">Vol</p>
                      <p className="font-mono text-zinc-200">{numberFmt(token.volume24h)}</p>
                    </div>
                    <div className="rounded-lg border border-line/60 bg-black/35 px-2 py-1">
                      <p className="text-zinc-500">Liq</p>
                      <p className="font-mono text-zinc-200">{numberFmt(token.liquidity)}</p>
                    </div>
                    <div className="rounded-lg border border-line/60 bg-black/35 px-2 py-1">
                      <p className="text-zinc-500">Buy/Sell</p>
                      <p className={`font-mono ${token.buySellRatio >= 1 ? 'text-emerald-300' : 'text-rose-300'}`}>
                        {token.buySellRatio.toFixed(2)}x
                      </p>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>

          <div className="hidden overflow-hidden rounded-xl border border-line md:block">
            <table className="w-full border-collapse">
              <thead className="bg-zinc-900/70">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="px-3 py-2 text-left text-[11px] uppercase tracking-[0.12em] text-zinc-500">
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    role="link"
                    tabIndex={0}
                    onClick={() => navigate(`/token/${row.original.address}`, { state: { from: 'radar' } })}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        navigate(`/token/${row.original.address}`, { state: { from: 'radar' } })
                      }
                    }}
                    className="cursor-pointer border-t border-line/70 bg-black/20 transition-colors hover:bg-neonOrange/5"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-3 py-2 text-sm">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 hidden items-center justify-between text-xs text-zinc-500 md:flex">
            <span>
              Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount() || 1}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="rounded-md border border-line px-2 py-1 disabled:opacity-40"
              >
                Prev
              </button>
              <button
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="rounded-md border border-line px-2 py-1 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  )
}

export default RadarView
