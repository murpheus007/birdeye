import { Activity, Radar, Bookmark, Bell, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/radar', label: 'Radar', icon: Radar },
  { to: '/whales', label: 'Whales', icon: Activity },
  { to: '/watchlist', label: 'Watchlist', icon: Bookmark },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/settings', label: 'Settings', icon: Settings },
]

const BottomNav = () => {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-30 flex items-center justify-around border-t md:hidden"
      style={{
        background: '#0A0A0A',
        borderColor: '#1A1A1A',
        backdropFilter: 'blur(15px)',
        WebkitBackdropFilter: 'blur(15px)',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
    >
      {navItems.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `m-1 flex flex-1 flex-col items-center gap-1 rounded-lg border px-1 py-3 text-[10px] font-medium transition-colors ${
              isActive
                ? 'text-zinc-100'
                : 'border-transparent text-zinc-500 hover:bg-[rgb(var(--accent-rgb)/0.2)] hover:text-zinc-100'
            }`
          }
          style={({ isActive }) =>
            isActive
              ? {
                  borderColor: 'rgb(var(--accent-rgb) / 0.7)',
                  background: 'rgb(var(--accent-rgb) / 0.16)',
                }
              : undefined
          }
        >
          {({ isActive }) => (
            <>
              <Icon
                className="h-5 w-5"
                style={
                  isActive
                    ? {
                        color: 'rgb(var(--accent-rgb) / 1)',
                        filter: 'drop-shadow(0 0 6px rgb(var(--accent-rgb) / 0.5))',
                      }
                    : undefined
                }
              />
              <span>{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

export default BottomNav
