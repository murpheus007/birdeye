import { Activity, Radar, Search, Settings, Bookmark, Bell } from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'

const navItems = [
  { to: '/radar', label: 'Radar', icon: Radar },
  { to: '/whales', label: 'Whales', icon: Activity },
  { to: '/explorer', label: 'Explorer', icon: Search },
  { to: '/watchlist', label: 'Watchlist', icon: Bookmark },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/settings', label: 'Settings', icon: Settings },
]

const SidebarNav = () => {
  return (
    <aside className="flex h-screen w-[84px] shrink-0 flex-col border-r border-line bg-black/50 px-2 py-4 md:w-[220px] md:px-3">
      <Link to="/" className="mb-6 flex h-14 items-center justify-center gap-2 md:justify-start md:px-3">
        <img src="/birdeyeradarlogo.png" alt="Birdeye Radar" className="h-16 w-16 object-contain" />
        <span className="hidden font-display text-sm tracking-[0.12em] text-neonOrange md:inline">Birdeye Radar</span>
      </Link>

      <nav className="flex flex-1 flex-col gap-2">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `group flex h-11 w-11 items-center justify-center rounded-xl border transition md:w-full md:justify-start md:gap-3 md:px-3 ${
                isActive
                  ? 'border-neonOrange/70 bg-neonOrange/20 text-neonOrange'
                  : 'border-transparent bg-zinc-900/40 text-zinc-500 hover:border-line hover:text-zinc-200'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            <span className="hidden text-sm md:inline">
              {label}
            </span>
          </NavLink>
        ))}
      </nav>

      <div className="text-center font-mono text-[10px] text-zinc-600 md:text-left md:pl-3">v1</div>
    </aside>
  )
}

export default SidebarNav
