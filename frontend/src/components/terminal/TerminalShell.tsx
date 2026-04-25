import { AnimatePresence, motion } from 'framer-motion'
import { Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import SidebarNav from './SidebarNav'
import TopCommandBar from './TopCommandBar'
import BottomNav from './BottomNav'
import ConnectWalletButton from './ConnectWalletButton'
import { terminalApi, RadarRow } from '../../services/terminalApi'
import { AlertHistoryEntry } from '../../types/types'

const TerminalShell = () => {
  const location = useLocation()
  const [trending, setTrending] = useState<RadarRow[]>([])
  const [alerts, setAlerts] = useState<AlertHistoryEntry[]>([])

  useEffect(() => {
    let active = true
    const run = async () => {
      try {
        const payload = await terminalApi.getActiveFeed()
        if (active) {
          setTrending(payload.trending)
          setAlerts(payload.alerts)
        }
      } catch {
        if (active) {
          setTrending([])
          setAlerts([])
        }
      }
    }

    void run()
  }, [location.pathname])

  return (
    <div className="flex min-h-screen bg-[#050505] text-zinc-100">
      <div className="hidden md:flex">
        <SidebarNav />
      </div>

      <div className="flex min-h-screen flex-1 flex-col">
        <TopCommandBar trending={trending} alerts={alerts} />

        <AnimatePresence mode="wait">
          <motion.main
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
            className="flex-1 overflow-auto p-4 pb-20 md:p-5 md:pb-5"
          >
            <Outlet />
          </motion.main>
        </AnimatePresence>

        <div className="fixed bottom-[calc(4.75rem+env(safe-area-inset-bottom))] right-4 z-40 md:hidden">
          <ConnectWalletButton iconOnly className="h-12 w-12 rounded-2xl shadow-neon" />
        </div>

        <BottomNav />
      </div>
    </div>
  )
}

export default TerminalShell
