import { Command, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWallet } from '@solana/wallet-adapter-react'
import ActiveFeedDropdown from './ActiveFeedDropdown'
import { AlertHistoryEntry } from '../../types/types'
import { RadarRow } from '../../services/terminalApi'
import { useAuth } from '../../contexts/AuthContext'
import { useToast } from '../../contexts/ToastContext'
import ConnectWalletButton from './ConnectWalletButton'

type TopCommandBarProps = {
  trending: RadarRow[]
  alerts: AlertHistoryEntry[]
}

const TopCommandBar = ({ trending, alerts }: TopCommandBarProps) => {
  const navigate = useNavigate()
  const { connected } = useWallet()
  const { user, isAuthenticated, isAuthenticating, authenticate, logout, error: authError } = useAuth()
  const { pushToast } = useToast()
  const [openFeed, setOpenFeed] = useState(false)
  const [mobileQuery, setMobileQuery] = useState('')
  const feedRef = useRef<HTMLDivElement | null>(null)
  const mobileFeedRef = useRef<HTMLDivElement | null>(null)
  const prevConnected = useRef(false)

  // Close dropdown when clicking outside
  useEffect(() => {
    const onDocumentPointerDown = (event: MouseEvent) => {
      const target = event.target as Node
      if (feedRef.current?.contains(target) || mobileFeedRef.current?.contains(target)) {
        return
      }
      setOpenFeed(false)
    }

    document.addEventListener('mousedown', onDocumentPointerDown)
    return () => document.removeEventListener('mousedown', onDocumentPointerDown)
  }, [])

  // Auto-trigger authentication the moment the wallet connects
  useEffect(() => {
    if (connected && !prevConnected.current && !isAuthenticated && !isAuthenticating) {
      void authenticate()
    }
    prevConnected.current = connected
  }, [connected, isAuthenticated, isAuthenticating, authenticate])

  // Surface auth errors via Toast so inline error text is not needed
  useEffect(() => {
    if (authError) {
      pushToast(authError, 'error')
    }
  }, [authError, pushToast])

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-[#050505]/95 px-5 py-3 backdrop-blur">
      <div className="flex items-center gap-2 md:hidden">
        <button
          onClick={() => navigate('/')}
          className="shrink-0 transition hover:opacity-90"
          aria-label="Birdeye Radar home"
        >
          <img src="/birdeyeradarlogo.png" alt="Birdeye Radar" className="h-16 w-16 object-contain" />
        </button>

        <form
          className="relative flex min-w-0 flex-1 items-center"
          onSubmit={(event) => {
            event.preventDefault()
            const trimmed = mobileQuery.trim()
            navigate(trimmed ? `/explorer?q=${encodeURIComponent(trimmed)}` : '/explorer')
          }}
        >
          <input
            value={mobileQuery}
            onChange={(event) => setMobileQuery(event.target.value)}
            placeholder="Search"
            className="h-10 w-full rounded-xl border border-line bg-zinc-900/60 pl-3 pr-10 text-sm text-zinc-100 outline-none transition focus:border-neonOrange/60"
          />
          <button
            type="submit"
            className="absolute right-0 top-0 flex h-10 w-10 items-center justify-center text-zinc-500 transition hover:text-neonOrange"
            aria-label="Search"
          >
            <Search className="h-4 w-4" />
          </button>
        </form>

        <div className="flex shrink-0 items-center gap-2">
          <div ref={mobileFeedRef} className="relative">
            <button
              onClick={() => setOpenFeed((previous) => !previous)}
              className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border-2 border-neonOrange/60 bg-neonOrange/10 text-neonOrange shadow-neon transition hover:border-neonOrange/80 hover:bg-neonOrange/15"
              title="Active Feed"
            >
              <Command className="h-4 w-4" />
            </button>
            <ActiveFeedDropdown
              open={openFeed}
              trending={trending}
              alerts={alerts}
              onClose={() => setOpenFeed(false)}
              onTokenClick={(address) => {
                navigate(`/token/${address}`)
                setOpenFeed(false)
              }}
            />
          </div>

          <ConnectWalletButton iconOnly className="!h-10 !w-10 px-0" />
        </div>
      </div>

      <div className="hidden items-center gap-4 md:flex">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-3 text-left transition hover:opacity-90"
          aria-label="Birdeye Radar home"
        >
          <img src="/birdeyeradarlogo.png" alt="Birdeye Radar" className="h-16 w-16 object-contain" />
          <span className="font-display text-lg tracking-[0.14em] text-zinc-100 uppercase">Birdeye Radar</span>
        </button>

        <div className="ml-auto flex items-center gap-3">
          <div ref={feedRef} className="relative">
            <button
              onClick={() => setOpenFeed((previous) => !previous)}
              className="relative flex h-11 items-center gap-2 rounded-xl border-2 border-neonOrange/60 bg-neonOrange/10 px-3 text-sm text-neonOrange shadow-neon transition hover:border-neonOrange/80 hover:bg-neonOrange/15"
            >
              <Command className="h-4 w-4" />
              Active Feed
            </button>
            <ActiveFeedDropdown
              open={openFeed}
              trending={trending}
              alerts={alerts}
              onClose={() => setOpenFeed(false)}
              onTokenClick={(address) => {
                navigate(`/token/${address}`)
                setOpenFeed(false)
              }}
            />
          </div>

          <ConnectWalletButton />

          {connected && !isAuthenticated && (
            <button
              onClick={() => {
                void authenticate()
              }}
              disabled={isAuthenticating}
              className="h-11 rounded-xl border-2 border-neonOrange/60 bg-neonOrange/10 px-3 text-sm text-neonOrange transition hover:border-neonOrange/80 hover:bg-neonOrange/20 disabled:opacity-60"
            >
              {isAuthenticating ? 'Signing...' : 'Sign In'}
            </button>
          )}

          {isAuthenticated && user && (
            <button
              onClick={() => {
                void logout()
              }}
              className="h-11 rounded-xl border-2 border-neonOrange/45 bg-neonOrange/10 px-3 text-xs text-neonOrange transition hover:border-neonOrange/70 hover:bg-neonOrange/20"
              title={user.wallet_address}
            >
              {user.wallet_address.slice(0, 4)}...{user.wallet_address.slice(-4)}
            </button>
          )}
        </div>
      </div>
    </header>
  )
}

export default TopCommandBar
