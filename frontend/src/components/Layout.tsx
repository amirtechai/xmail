import { Outlet, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Bot,
  Users,
  FileText,
  Ban,
  Settings,
  LogOut,
  Mail,
  PenLine,
  Megaphone,
  ScrollText,
} from 'lucide-react'
import { useAuth } from '../lib/auth'
import clsx from 'clsx'

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/bot', icon: Bot, label: 'Bot Control' },
  { to: '/campaigns', icon: Megaphone, label: 'Campaigns' },
  { to: '/compose', icon: PenLine, label: 'Compose' },
  { to: '/contacts', icon: Users, label: 'Contacts' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/suppression', icon: Ban, label: 'Suppression' },
  { to: '/logs', icon: ScrollText, label: 'Logs' },
  { to: '/settings', icon: Settings, label: 'Settings' },
] as const

export default function Layout() {
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)

  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary">
      <aside className="w-56 flex-shrink-0 bg-bg-secondary border-r border-border flex flex-col">
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-4 border-b border-border">
          <Mail className="w-5 h-5 text-accent-yellow flex-shrink-0" />
          <span className="font-bold text-text-primary tracking-wide">Xmail</span>
          <span className="text-xs text-text-muted ml-auto">v1</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-4 py-2.5 text-sm transition-colors',
                  isActive
                    ? 'bg-bg-card text-text-primary font-medium border-r-2 border-accent-yellow'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover',
                )
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="border-t border-border px-4 py-3">
          <div className="text-xs text-text-muted truncate">{user?.email}</div>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-xs text-text-secondary hover:text-accent-red mt-2 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
