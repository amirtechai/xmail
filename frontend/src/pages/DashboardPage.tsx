import { type ElementType, useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Users, Mail, ShieldOff, CheckCircle, Activity, Wifi, WifiOff } from 'lucide-react'
import {
  statsApi,
  healthApi,
  botApi,
  type DashboardStats,
  type HealthStatus,
  type BotStatus,
  type BotSSEEvent,
} from '../lib/api'
import { useSSE } from '../hooks/useSSE'

// ── Bloomberg chart tokens ──────────────────────────────────────────────────

const CHART_COLORS = ['#F0B429', '#58A6FF', '#3FB950', '#F85149', '#BC8CFF', '#79C0FF', '#56D364', '#FF7B72', '#D2A8FF', '#FFA657', '#E3B341', '#89DDFF']
const GRID_COLOR = '#30363D'
const TICK_COLOR = '#8B949E'
const TOOLTIP_STYLE = { backgroundColor: '#1C2128', border: '1px solid #30363D', borderRadius: 6 }

// ── Sub-components ──────────────────────────────────────────────────────────

interface KpiProps {
  label: string
  value: string | number
  sub?: string
  icon: ElementType
  colorClass: string
}

function KpiCard({ label, value, sub, icon: Icon, colorClass }: KpiProps) {
  return (
    <div className="card flex items-start gap-4">
      <div className={`p-2 rounded-lg ${colorClass}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <div className="text-2xl font-bold font-mono text-text-primary">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        <div className="text-xs text-text-secondary mt-0.5 truncate">{label}</div>
        {sub && <div className="text-xs text-text-muted mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
      {children}
    </h2>
  )
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${ok ? 'bg-accent-green' : 'bg-accent-red'}`}
    />
  )
}

// ── SSE Status Bar ──────────────────────────────────────────────────────────

function SSEStatusBar({ botStatus }: { botStatus: BotStatus | null }) {
  const sse = useSSE<BotSSEEvent>('/bot/stream')
  const liveState = sse.data?.state ?? botStatus?.state ?? 'unknown'
  const dailyCount = sse.data?.daily_email_count ?? botStatus?.daily_email_count ?? 0

  const stateColor =
    liveState === 'discovering' || liveState === 'sending' || liveState === 'verifying'
      ? 'text-accent-green'
      : liveState === 'paused'
        ? 'text-accent-yellow'
        : liveState === 'error'
          ? 'text-accent-red'
          : 'text-text-muted'

  return (
    <div className="card flex items-center gap-4 py-3">
      {sse.connected ? (
        <Wifi className="w-4 h-4 text-accent-green flex-shrink-0" />
      ) : (
        <WifiOff className="w-4 h-4 text-text-muted flex-shrink-0" />
      )}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-text-secondary">Bot:</span>
        <span className={`font-mono font-medium ${stateColor}`}>{liveState}</span>
      </div>
      <div className="text-xs text-text-muted">
        Emails today: <span className="font-mono text-text-primary">{dailyCount.toLocaleString()}</span>
      </div>
      {sse.connected && (
        <span className="ml-auto flex items-center gap-1.5 text-xs text-accent-green">
          <Activity className="w-3 h-3" />
          Live
        </span>
      )}
      {sse.error && (
        <span className="ml-auto text-xs text-text-muted">{sse.error}</span>
      )}
    </div>
  )
}

// ── System Health Panel ─────────────────────────────────────────────────────

function HealthPanel({ health }: { health: HealthStatus | null }) {
  if (!health) {
    return (
      <div className="card h-full flex items-center justify-center text-text-muted text-sm">
        Loading health…
      </div>
    )
  }

  return (
    <div className="card">
      <SectionTitle>System Health</SectionTitle>
      <div className="space-y-2">
        {Object.entries(health.checks).map(([name, status]) => (
          <div key={name} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <StatusDot ok={status === 'ok'} />
              <span className="text-text-secondary capitalize">{name}</span>
            </div>
            <span
              className={`text-xs font-mono ${status === 'ok' ? 'text-accent-green' : 'text-accent-red'}`}
            >
              {status}
            </span>
          </div>
        ))}
        <div className="flex items-center justify-between text-sm pt-2 border-t border-border">
          <div className="flex items-center gap-2">
            <StatusDot ok={health.status === 'ok'} />
            <span className="text-text-primary font-medium">Overall</span>
          </div>
          <span
            className={`text-xs font-mono font-semibold ${health.status === 'ok' ? 'text-accent-green' : 'text-accent-yellow'}`}
          >
            {health.status}
          </span>
        </div>
      </div>
    </div>
  )
}

// ── Main Page ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, healthRes, botRes] = await Promise.all([
          statsApi.dashboard(),
          healthApi.detailed(),
          botApi.status(),
        ])
        setStats(statsRes.data)
        setHealth(healthRes.data)
        setBotStatus(botRes.data)
        setLastRefresh(new Date())
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    void load()
    const id = setInterval(() => { void load() }, 60_000)
    return () => clearInterval(id)
  }, [])

  if (loading) {
    return <div className="p-6 text-text-secondary text-sm">Loading dashboard…</div>
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Dashboard</h1>
        {lastRefresh && (
          <span className="text-xs text-text-muted">
            Updated {lastRefresh.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* SSE Status Bar */}
      <SSEStatusBar botStatus={botStatus} />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Contacts Today"
          value={stats?.contacts_today ?? 0}
          sub={`${stats?.contacts_week ?? 0} this week`}
          icon={Users}
          colorClass="bg-blue-900/40 text-accent-blue"
        />
        <KpiCard
          label="Total Contacts"
          value={stats?.contacts_total ?? 0}
          sub={`${stats?.verified_total ?? 0} verified`}
          icon={CheckCircle}
          colorClass="bg-green-900/40 text-accent-green"
        />
        <KpiCard
          label="Emails Sent Total"
          value={botStatus?.total_emails_sent ?? 0}
          sub={`${botStatus?.daily_email_count ?? 0} today`}
          icon={Mail}
          colorClass="bg-yellow-900/40 text-accent-yellow"
        />
        <KpiCard
          label="Suppressed"
          value={stats?.suppression_total ?? 0}
          icon={ShieldOff}
          colorClass="bg-red-900/40 text-accent-red"
        />
      </div>

      {/* 30-Day Trend Chart */}
      {stats && stats.trend.length > 0 && (
        <div className="card">
          <SectionTitle>30-Day Trend</SectionTitle>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={stats.trend} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
              <XAxis
                dataKey="date"
                tick={{ fill: TICK_COLOR, fontSize: 11 }}
                tickFormatter={(v: string) => v.slice(5)}
              />
              <YAxis tick={{ fill: TICK_COLOR, fontSize: 11 }} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#E6EDF3' }} />
              <Legend wrapperStyle={{ fontSize: 11, color: TICK_COLOR }} />
              <Line
                type="monotone"
                dataKey="contacts"
                stroke="#58A6FF"
                strokeWidth={2}
                dot={false}
                name="Contacts"
              />
              <Line
                type="monotone"
                dataKey="sent"
                stroke="#F0B429"
                strokeWidth={2}
                dot={false}
                name="Sent"
              />
              <Line
                type="monotone"
                dataKey="opened"
                stroke="#3FB950"
                strokeWidth={2}
                dot={false}
                name="Opened"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Bottom row: Top Domains + Audience Pie + Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Top Domains BarChart */}
        {stats && stats.top_domains.length > 0 && (
          <div className="card lg:col-span-1">
            <SectionTitle>Top Domains</SectionTitle>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={stats.top_domains}
                layout="vertical"
                margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} horizontal={false} />
                <XAxis type="number" tick={{ fill: TICK_COLOR, fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="domain"
                  tick={{ fill: TICK_COLOR, fontSize: 10 }}
                  width={100}
                />
                <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#E6EDF3' }} />
                <Bar dataKey="count" fill="#58A6FF" radius={[0, 3, 3, 0]} name="Contacts" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Audience Breakdown PieChart */}
        {stats && stats.audience_breakdown.length > 0 && (
          <div className="card lg:col-span-1">
            <SectionTitle>Audience Breakdown</SectionTitle>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={stats.audience_breakdown}
                  dataKey="count"
                  nameKey="key"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ key, percent }: { key: string; percent: number }) =>
                    `${key.replace(/_/g, ' ')} ${(percent * 100).toFixed(0)}%`
                  }
                  labelLine={false}
                >
                  {stats.audience_breakdown.map((_entry, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#E6EDF3' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* System Health */}
        <div className="lg:col-span-1">
          <HealthPanel health={health} />
        </div>
      </div>
    </div>
  )
}
