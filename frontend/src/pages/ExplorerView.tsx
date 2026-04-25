import { Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { terminalApi } from '../services/terminalApi'
import { SearchHit } from '../types/types'
import LoadingPulse from '../components/terminal/LoadingPulse'

const ExplorerView = () => {
  const [searchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') ?? ''
  const [query, setQuery] = useState(initialQuery)
  const [activeQuery, setActiveQuery] = useState(initialQuery.trim())
  const [rows, setRows] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery)
      setActiveQuery(initialQuery.trim())
    }
  }, [initialQuery])

  useEffect(() => {
    if (!activeQuery || activeQuery.length < 2) {
      setRows([])
      setLoading(false)
      return
    }

    let active = true

    const run = async () => {
      setLoading(true)
      try {
        const payload = await terminalApi.searchTokens(activeQuery)
        if (active) {
          setRows(payload)
        }
      } catch {
        if (active) {
          setRows([])
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
  }, [activeQuery])

  const handleSearch = (event?: React.FormEvent) => {
    if (event) {
      event.preventDefault()
    }
    setActiveQuery(query.trim())
  }

  return (
    <section className="panel h-full p-4 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="panel-title">Explorer</p>
          <h1 className="font-display text-2xl text-zinc-100">Global Token Search</h1>
        </div>
      </div>

      <form onSubmit={handleSearch} className="relative mb-4 flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search token name, symbol, or address"
            className="h-11 w-full rounded-xl border border-line bg-zinc-900/60 pl-10 pr-3 text-sm text-zinc-100 outline-none transition focus:border-neonOrange/60"
          />
        </div>
        <button
          type="submit"
          className="flex h-11 shrink-0 items-center gap-2 rounded-xl border border-neonOrange/45 bg-neonOrange/15 px-4 text-sm font-medium text-neonOrange transition hover:border-neonOrange/70 hover:bg-neonOrange/20 shadow-neon"
          aria-label="Search"
        >
          <Search className="h-4 w-4" />
          <span className="hidden sm:inline">Search</span>
        </button>
      </form>

      {loading && (
        <div className="flex min-h-[24rem] items-center justify-center rounded-2xl border border-line bg-zinc-900/20 max-md:rounded-none max-md:border-0 max-md:bg-transparent">
          <LoadingPulse message="Searching Birdeye" />
        </div>
      )}

      {!loading && (
        <div className="space-y-2">
          {rows.map((row) => (
            <Link
              key={row.address}
              to={`/token/${row.address}`}
              state={{ from: 'explorer' }}
              className="block rounded-xl border border-line bg-zinc-900/30 p-3 transition hover:border-neonOrange/50 hover:bg-neonOrange/5 max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {row.logoURI ? (
                    <img
                      src={row.logoURI}
                      alt={row.symbol}
                      className="h-8 w-8 rounded-full border border-line bg-zinc-900 object-cover flex-shrink-0"
                      onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
                    />
                  ) : (
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-line bg-zinc-800 text-xs font-display text-neonOrange">
                      {row.symbol.slice(0, 2)}
                    </div>
                  )}
                  <div>
                    <p className="font-display text-zinc-100">{row.symbol}</p>
                    <p className="text-xs text-zinc-500">{row.name}</p>
                  </div>
                </div>
                <div className="text-right text-xs text-zinc-500">
                  <p className="font-mono">FDV ${row.fdv?.toLocaleString(undefined, { maximumFractionDigits: 0 }) ?? '0'}</p>
                  <p className="font-mono">Liq ${row.liquidity?.toLocaleString(undefined, { maximumFractionDigits: 0 }) ?? '0'}</p>
                </div>
              </div>
              <p className="mt-2 font-mono text-[11px] text-zinc-500">{row.address}</p>
            </Link>
          ))}

          {!rows.length && <p className="text-sm text-zinc-500">{query ? 'No results.' : 'Type at least 2 characters to search.'}</p>}
        </div>
      )}
    </section>
  )
}

export default ExplorerView
