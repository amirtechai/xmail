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
  UserCog,
  BarChart2,
} from 'lucide-react'
import { useAuth } from '../lib/auth'
import { botApi, type BotStatus } from '../lib/api'
import { useEffect, useState } from 'react'
import clsx from 'clsx'

type NavRole = 'all' | 'operator' | 'admin'

const NAV: { to: string; icon: React.FC<{ className?: string }>; label: string; key: string; minRole: NavRole }[] = [
  { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard',   key: 'DASH', minRole: 'all'      },
  { to: '/bot',         icon: Bot,             label: 'Bot Control', key: 'BOT',  minRole: 'operator' },
  { to: '/campaigns',      icon: Megaphone,   label: 'Campaigns',     key: 'CAMP', minRole: 'all'      },
  { to: '/campaign-stats', icon: BarChart2,   label: 'Stats',         key: 'STAT', minRole: 'all'      },
  { to: '/compose',     icon: PenLine,         label: 'Compose',     key: 'COMP', minRole: 'operator' },
  { to: '/contacts',    icon: Users,           label: 'Contacts',    key: 'CTCT', minRole: 'all'      },
  { to: '/reports',     icon: FileText,        label: 'Reports',     key: 'RPTS', minRole: 'all'      },
  { to: '/suppression', icon: Ban,             label: 'Suppression', key: 'SUPR', minRole: 'operator' },
  { to: '/logs',        icon: ScrollText,      label: 'Logs',        key: 'LOGS', minRole: 'all'      },
  { to: '/settings',    icon: Settings,        label: 'Settings',    key: 'CFG',  minRole: 'operator' },
  { to: '/admin/users', icon: UserCog,         label: 'Users',       key: 'USR',  minRole: 'admin'    },
]

const ROLE_ORDER: Record<string, number> = { admin: 3, operator: 2, viewer: 1 }

function canSeeNav(userRole: string | undefined, minRole: NavRole): boolean {
  if (minRole === 'all') return true
  const rank = ROLE_ORDER[userRole ?? 'viewer'] ?? 1
  return rank >= (ROLE_ORDER[minRole] ?? 1)
}

const ROLE_BADGE: Record<string, string> = {
  admin:    'bg-accent-red/10 text-accent-red border-accent-red',
  operator: 'bg-accent-yellow/10 text-accent-yellow border-accent-yellow',
  viewer:   'bg-border text-text-muted border-border',
}

function Clock() {
  const [time, setTime] = useState(() => new Date().toUTCString().slice(17, 25))
  useEffect(() => {
    const t = setInterval(() => setTime(new Date().toUTCString().slice(17, 25)), 1000)
    return () => clearInterval(t)
  }, [])
  return <span className="font-mono text-[11px] text-text-secondary">{time} UTC</span>
}

export default function Layout() {
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null)

  useEffect(() => {
    botApi.status().then((r) => setBotStatus(r.data)).catch(() => null)
    const t = setInterval(() => {
      botApi.status().then((r) => setBotStatus(r.data)).catch(() => null)
    }, 15000)
    return () => clearInterval(t)
  }, [])

  const running = botStatus?.is_running === true

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-bg-primary">
      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 h-10 bg-bg-secondary border-b border-border flex items-center px-4 gap-4">
        <div className="flex items-center gap-2 min-w-max">
          <Mail className="w-4 h-4 text-accent-yellow flex-shrink-0" />
          <span className="font-mono font-bold text-sm tracking-widest text-text-primary uppercase">
            X<span className="text-accent-yellow">MAIL</span>
          </span>
        </div>

        <div className="h-4 w-px bg-border" />

        <div className="flex items-center gap-2 text-[10px] font-mono">
          <span
            className={clsx(
              'px-2 py-0.5 rounded border font-bold tracking-widest',
              running
                ? 'bg-accent-green/10 text-accent-green border-accent-green'
                : 'bg-border text-text-muted border-border',
            )}
          >
            {running ? '● LIVE' : '○ IDLE'}
          </span>
          <span className="px-2 py-0.5 rounded border bg-accent-yellow/10 text-accent-yellow border-accent-yellow tracking-widest">
            OUTREACH
          </span>
        </div>

        <div className="flex-1" />

        <Clock />

        <div className="h-4 w-px bg-border" />

        <span className="font-mono text-[11px] text-text-muted truncate max-w-[180px]">
          {user?.email}
        </span>

        <button
          onClick={logout}
          title="Sign out"
          className="flex items-center gap-1 text-[11px] text-text-muted hover:text-accent-red transition-colors font-mono"
        >
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* ── Sidebar ───────────────────────────────────────────────────── */}
        <aside className="w-48 flex-shrink-0 bg-bg-secondary border-r border-border flex flex-col overflow-y-auto">
          <div className="px-3 py-2 border-b border-border">
            <span className="font-mono text-[9px] text-text-muted tracking-widest uppercase">
              Navigation
            </span>
          </div>

          <nav className="flex-1 py-1">
            {NAV.filter(({ minRole }) => canSeeNav(user?.role, minRole)).map(({ to, icon: Icon, label, key }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-2.5 px-3 py-2 text-xs transition-all duration-100 group',
                    isActive
                      ? 'bg-bg-card text-text-primary border-l-2 border-accent-yellow'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-card border-l-2 border-transparent',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="font-mono text-[9px] text-text-muted w-8 flex-shrink-0 group-hover:text-accent-yellow transition-colors">
                      {key}
                    </span>
                    <Icon
                      className={clsx(
                        'w-3.5 h-3.5 flex-shrink-0',
                        isActive ? 'text-accent-yellow' : 'text-text-secondary group-hover:text-text-primary',
                      )}
                    />
                    <span>{label}</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-border px-3 py-2 space-y-1">
            <div className="font-mono text-[9px] text-text-muted truncate">{user?.email}</div>
            {user?.role && (
              <span className={clsx(
                'inline-block font-mono text-[9px] px-1.5 py-0.5 rounded border tracking-widest uppercase',
                ROLE_BADGE[user.role] ?? ROLE_BADGE.viewer,
              )}>
                {user.role}
              </span>
            )}
          </div>
        </aside>

        {/* ── Main content ──────────────────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto bg-bg-primary">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
