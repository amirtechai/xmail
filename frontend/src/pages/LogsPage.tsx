import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { auditApi, botApi, type AgentRun, type AuditLogEntry } from '../lib/api'

type Tab = 'audit' | 'runs'

const PAGE_SIZE = 50

// ── Audit Log ─────────────────────────────────────────────────────────────────

const ACTION_COLORS: Record<string, string> = {
  login: 'badge-blue',
  logout: 'badge-muted',
  campaign_sent: 'badge-yellow',
  campaign_paused: 'badge-yellow',
  bot_started: 'badge-green',
  bot_stopped: 'badge-muted',
  contact_deleted: 'badge-red',
  suppression_added: 'badge-red',
  suppression_removed: 'badge-muted',
  config_updated: 'badge-blue',
}

function AuditTab() {
  const [items, setItems] = useState<AuditLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [actionFilter, setActionFilter] = useState('')
  const [actorTypeFilter, setActorTypeFilter] = useState('')

  const load = async (p = page) => {
    setLoading(true)
    try {
      const { data } = await auditApi.list(p, PAGE_SIZE, actionFilter || undefined, actorTypeFilter || undefined)
      setItems(data.items)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [page, actorTypeFilter])

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-3">
      <div className="flex gap-3 items-center">
        <input
          className="input text-sm w-48"
          placeholder="Filter action…"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { setPage(1); void load(1) } }}
        />
        <select
          className="input text-sm w-36"
          value={actorTypeFilter}
          onChange={(e) => { setActorTypeFilter(e.target.value); setPage(1) }}
        >
          <option value="">All actors</option>
          <option value="user">User</option>
          <option value="system">System</option>
          <option value="agent">Agent</option>
        </select>
        <button className="btn-secondary p-2" onClick={() => { setPage(1); void load(1) }} disabled={loading}>
          <RefreshCw className="w-4 h-4" />
        </button>
        <span className="text-xs text-text-muted ml-auto">{total.toLocaleString()} entries</span>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-border">
              <th className="text-left pb-2 font-medium">Timestamp</th>
              <th className="text-left pb-2 font-medium">Actor</th>
              <th className="text-left pb-2 font-medium">Action</th>
              <th className="text-left pb-2 font-medium">Resource</th>
              <th className="text-left pb-2 font-medium">IP</th>
              <th className="text-left pb-2 font-medium">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              <tr><td colSpan={6} className="py-6 text-center text-text-muted">Loading…</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={6} className="py-6 text-center text-text-muted">No audit log entries yet.</td></tr>
            ) : items.map((entry) => (
              <tr key={entry.id} className="hover:bg-bg-hover">
                <td className="py-2 text-text-muted font-mono whitespace-nowrap">
                  {new Date(entry.created_at).toLocaleString()}
                </td>
                <td className="py-2">
                  <span className={`badge ${entry.actor_type === 'user' ? 'badge-blue' : entry.actor_type === 'agent' ? 'badge-yellow' : 'badge-muted'}`}>
                    {entry.actor_type}
                  </span>
                </td>
                <td className="py-2">
                  <span className={`badge ${ACTION_COLORS[entry.action] ?? 'badge-muted'}`}>
                    {entry.action}
                  </span>
                </td>
                <td className="py-2 text-text-muted">
                  {entry.resource_type ? (
                    <span>{entry.resource_type}{entry.resource_id ? <span className="text-text-muted font-mono"> #{entry.resource_id.slice(0, 8)}</span> : null}</span>
                  ) : '—'}
                </td>
                <td className="py-2 text-text-muted font-mono">{entry.ip_address ?? '—'}</td>
                <td className="py-2 text-text-muted max-w-[200px] truncate">
                  {entry.details ? JSON.stringify(entry.details) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
            <span className="text-xs text-text-muted">Page {page} of {totalPages}</span>
            <div className="flex gap-2">
              <button className="btn-secondary py-1 px-3 text-xs" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
              <button className="btn-secondary py-1 px-3 text-xs" disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Agent Runs ────────────────────────────────────────────────────────────────

const RUN_STATUS_BADGE: Record<string, string> = {
  running: 'badge-blue',
  completed: 'badge-green',
  failed: 'badge-red',
  cancelled: 'badge-muted',
}

function RunsTab() {
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await botApi.runs()
      setRuns(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const duration = (start: string, end: string | null) => {
    if (!end) return '—'
    const ms = new Date(end).getTime() - new Date(start).getTime()
    if (ms < 60000) return `${Math.round(ms / 1000)}s`
    return `${Math.round(ms / 60000)}m`
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button className="btn-secondary p-2" onClick={() => void load()} disabled={loading}>
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-border">
              <th className="text-left pb-2 font-medium">Started</th>
              <th className="text-left pb-2 font-medium">Type</th>
              <th className="text-left pb-2 font-medium">Status</th>
              <th className="text-right pb-2 font-medium">Duration</th>
              <th className="text-right pb-2 font-medium">Contacts found</th>
              <th className="text-left pb-2 font-medium">Error</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              <tr><td colSpan={6} className="py-6 text-center text-text-muted">Loading…</td></tr>
            ) : runs.length === 0 ? (
              <tr><td colSpan={6} className="py-6 text-center text-text-muted">No agent runs yet.</td></tr>
            ) : runs.map((r) => (
              <tr key={r.id} className="hover:bg-bg-hover">
                <td className="py-2 text-text-muted font-mono whitespace-nowrap">
                  {new Date(r.started_at).toLocaleString()}
                </td>
                <td className="py-2">
                  <span className="badge badge-muted">{r.run_type}</span>
                </td>
                <td className="py-2">
                  <span className={`badge ${RUN_STATUS_BADGE[r.status] ?? 'badge-muted'}`}>{r.status}</span>
                </td>
                <td className="py-2 text-right font-mono text-text-primary">
                  {duration(r.started_at, r.finished_at)}
                </td>
                <td className="py-2 text-right font-mono text-text-primary">
                  {r.contacts_found.toLocaleString()}
                </td>
                <td className="py-2 text-text-muted max-w-[220px] truncate">
                  {r.error_message ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function LogsPage() {
  const [tab, setTab] = useState<Tab>('audit')

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold text-text-primary">Logs</h1>

      <div className="flex gap-1 border-b border-border">
        {([
          { id: 'audit' as Tab, label: 'Audit Log' },
          { id: 'runs' as Tab, label: 'Agent Runs' },
        ]).map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              'px-4 py-2.5 text-sm border-b-2 transition-colors',
              tab === id
                ? 'border-accent-yellow text-text-primary font-medium'
                : 'border-transparent text-text-secondary hover:text-text-primary',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'audit' && <AuditTab />}
      {tab === 'runs' && <RunsTab />}
    </div>
  )
}
