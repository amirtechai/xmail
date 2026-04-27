import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { AlertTriangle, ExternalLink } from 'lucide-react'
import { campaignsApi, type CampaignStatsOverview, type CampaignStatRow } from '../lib/api'

const CHART_COLORS = ['#F0B429', '#58A6FF', '#3FB950', '#F85149', '#BC8CFF', '#79C0FF']
const GRID_COLOR = '#30363D'
const TICK_COLOR = '#8B949E'
const TOOLTIP_STYLE = { backgroundColor: '#1C2128', border: '1px solid #30363D', borderRadius: 6 }

function KpiCard({ label, value, sub, colorClass }: { label: string; value: string; sub?: string; colorClass: string }) {
  return (
    <div className="card flex flex-col gap-1">
      <div className={`text-2xl font-bold font-mono ${colorClass}`}>{value}</div>
      <div className="text-xs text-text-secondary">{label}</div>
      {sub && <div className="text-xs text-text-muted">{sub}</div>}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    completed: 'text-accent-green bg-green-900/30',
    sending: 'text-accent-yellow bg-yellow-900/30',
    paused: 'text-accent-yellow bg-yellow-900/20',
    draft: 'text-text-muted bg-surface-2',
    archived: 'text-text-muted bg-surface-2',
    ready_to_send: 'text-accent-blue bg-blue-900/30',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded font-mono ${map[status] ?? 'text-text-muted'}`}>
      {status}
    </span>
  )
}

function PercentBar({ value, max = 100, color }: { value: number; max?: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-surface-2 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono text-text-secondary w-10 text-right">{value}%</span>
    </div>
  )
}

const PERIOD_OPTIONS = [7, 14, 30, 60, 90] as const

export default function CampaignStatsPage() {
  const [data, setData] = useState<CampaignStatsOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState<number>(30)
  const [sortKey, setSortKey] = useState<keyof CampaignStatRow>('open_rate')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    setLoading(true)
    campaignsApi.statsOverview(days)
      .then((r: { data: CampaignStatsOverview }) => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days])

  const sortedCampaigns = data
    ? [...data.campaigns].sort((a, b) => {
        const av = a[sortKey] as number
        const bv = b[sortKey] as number
        return sortDir === 'desc' ? bv - av : av - bv
      })
    : []

  function toggleSort(key: keyof CampaignStatRow) {
    if (key === sortKey) setSortDir(d => (d === 'desc' ? 'asc' : 'desc'))
    else { setSortKey(key); setSortDir('desc') }
  }

  if (loading && !data) {
    return <div className="p-6 text-text-secondary text-sm">Loading stats…</div>
  }

  const t = data?.totals

  // A/B chart data: campaigns with ab_enabled and >0 sent
  const abCampaigns = sortedCampaigns.filter(c => c.ab_enabled && c.sent > 0).slice(0, 6)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold text-text-primary">Campaign Stats</h1>
        <div className="flex items-center gap-2">
          {PERIOD_OPTIONS.map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`text-xs px-3 py-1.5 rounded border transition-colors ${
                days === d
                  ? 'border-accent-blue text-accent-blue bg-blue-900/20'
                  : 'border-border text-text-muted hover:text-text-secondary'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* KPI row */}
      {t && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label={`Sent (${days}d)`}
            value={t.sent.toLocaleString()}
            sub={`${t.delivered.toLocaleString()} delivered`}
            colorClass="text-accent-blue"
          />
          <KpiCard
            label="Open Rate"
            value={`${t.open_rate}%`}
            sub={`${t.opened.toLocaleString()} opens`}
            colorClass="text-accent-green"
          />
          <KpiCard
            label="Click Rate"
            value={`${t.click_rate}%`}
            sub={`${t.clicked.toLocaleString()} clicks`}
            colorClass="text-accent-yellow"
          />
          <KpiCard
            label="Bounce Rate"
            value={`${t.bounce_rate}%`}
            sub={`${t.bounced.toLocaleString()} bounced`}
            colorClass={t.bounce_rate > 2 ? 'text-accent-red' : 'text-text-primary'}
          />
        </div>
      )}

      {/* Time-series chart */}
      {data && data.trend.length > 0 && (
        <div className="card">
          <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
            Rate Trend — Last {days} Days
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.trend} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
              <XAxis
                dataKey="date"
                tick={{ fill: TICK_COLOR, fontSize: 11 }}
                tickFormatter={(v: string) => v.slice(5)}
              />
              <YAxis tick={{ fill: TICK_COLOR, fontSize: 11 }} unit="%" domain={[0, 'auto']} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelStyle={{ color: '#E6EDF3' }}
                formatter={(v: number) => [`${v}%`]}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: TICK_COLOR }} />
              <Line type="monotone" dataKey="open_rate" stroke="#3FB950" strokeWidth={2} dot={false} name="Open %" />
              <Line type="monotone" dataKey="click_rate" stroke="#F0B429" strokeWidth={2} dot={false} name="Click %" />
              <Line type="monotone" dataKey="bounce_rate" stroke="#F85149" strokeWidth={2} dot={false} name="Bounce %" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Volume chart + A/B bar chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data && data.trend.length > 0 && (
          <div className="card">
            <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
              Volume — Sent / Opened / Clicked
            </h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={data.trend} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
                <XAxis
                  dataKey="date"
                  tick={{ fill: TICK_COLOR, fontSize: 10 }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis tick={{ fill: TICK_COLOR, fontSize: 10 }} />
                <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#E6EDF3' }} />
                <Legend wrapperStyle={{ fontSize: 11, color: TICK_COLOR }} />
                <Bar dataKey="sent" fill="#58A6FF" name="Sent" radius={[2, 2, 0, 0]} />
                <Bar dataKey="opened" fill="#3FB950" name="Opened" radius={[2, 2, 0, 0]} />
                <Bar dataKey="clicked" fill="#F0B429" name="Clicked" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {abCampaigns.length > 0 ? (
          <div className="card">
            <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
              A/B Campaigns — Open Rate Comparison
            </h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={abCampaigns}
                margin={{ top: 0, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: TICK_COLOR, fontSize: 10 }}
                  tickFormatter={(v: string) => v.slice(0, 12)}
                />
                <YAxis tick={{ fill: TICK_COLOR, fontSize: 10 }} unit="%" />
                <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: '#E6EDF3' }} />
                <Bar dataKey="open_rate" name="Open %" radius={[3, 3, 0, 0]}>
                  {abCampaigns.map((_c, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="card flex items-center justify-center text-text-muted text-sm">
            No A/B campaigns in this period
          </div>
        )}
      </div>

      {/* Top performing campaigns table */}
      <div className="card overflow-hidden">
        <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          Top Campaigns
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="pb-2 text-xs text-text-muted font-medium pr-4 min-w-[180px]">Campaign</th>
                <th className="pb-2 text-xs text-text-muted font-medium pr-3">Status</th>
                <th
                  className="pb-2 text-xs text-text-muted font-medium pr-3 cursor-pointer hover:text-text-secondary"
                  onClick={() => toggleSort('sent')}
                >
                  Sent {sortKey === 'sent' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                </th>
                <th
                  className="pb-2 text-xs text-text-muted font-medium pr-4 cursor-pointer hover:text-text-secondary min-w-[100px]"
                  onClick={() => toggleSort('open_rate')}
                >
                  Open % {sortKey === 'open_rate' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                </th>
                <th
                  className="pb-2 text-xs text-text-muted font-medium pr-4 cursor-pointer hover:text-text-secondary min-w-[100px]"
                  onClick={() => toggleSort('click_rate')}
                >
                  Click % {sortKey === 'click_rate' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                </th>
                <th
                  className="pb-2 text-xs text-text-muted font-medium pr-3 cursor-pointer hover:text-text-secondary min-w-[100px]"
                  onClick={() => toggleSort('bounce_rate')}
                >
                  Bounce % {sortKey === 'bounce_rate' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                </th>
                <th className="pb-2 text-xs text-text-muted font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sortedCampaigns.map(c => (
                <tr key={c.id} className="hover:bg-surface-2/50 transition-colors">
                  <td className="py-2 pr-4">
                    <div className="flex items-center gap-1.5">
                      <span className="text-text-primary truncate max-w-[160px]" title={c.name}>{c.name}</span>
                      {c.ab_enabled && (
                        <span className="text-[10px] px-1 py-0.5 bg-purple-900/30 text-purple-300 rounded">A/B</span>
                      )}
                    </div>
                  </td>
                  <td className="py-2 pr-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="py-2 pr-3 font-mono text-text-secondary">{c.sent.toLocaleString()}</td>
                  <td className="py-2 pr-4">
                    <PercentBar value={c.open_rate} color="#3FB950" />
                  </td>
                  <td className="py-2 pr-4">
                    <PercentBar value={c.click_rate} color="#F0B429" />
                  </td>
                  <td className="py-2 pr-3">
                    <div className="flex items-center gap-1.5">
                      {c.bounce_rate > 2 && (
                        <AlertTriangle className="w-3 h-3 text-accent-red flex-shrink-0" />
                      )}
                      <span className={`text-xs font-mono ${c.bounce_rate > 2 ? 'text-accent-red' : 'text-text-secondary'}`}>
                        {c.bounce_rate}%
                      </span>
                    </div>
                  </td>
                  <td className="py-2">
                    <Link
                      to={`/campaigns/${c.id}`}
                      className="text-text-muted hover:text-accent-blue transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
              {sortedCampaigns.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-text-muted text-sm">
                    No campaigns found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
