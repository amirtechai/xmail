import { type FormEvent, useEffect, useRef, useState } from 'react'
import { Download, Plus, RefreshCw, Trash2, Upload } from 'lucide-react'
import clsx from 'clsx'
import { suppressionApi, type SuppressionEntry } from '../lib/api'

const PAGE_SIZE = 50

const REASONS = ['unsubscribed', 'bounced', 'complained', 'manual', 'do_not_contact'] as const
type Reason = (typeof REASONS)[number]

const REASON_BADGE: Record<string, string> = {
  unsubscribed: 'badge-yellow',
  bounced: 'badge-red',
  complained: 'badge-red',
  do_not_contact: 'badge-red',
}

function ReasonBadge({ reason }: { reason: string }) {
  return <span className={`badge ${REASON_BADGE[reason] ?? 'badge-muted'}`}>{reason.replace('_', ' ')}</span>
}

type Tab = 'emails' | 'domains'

export default function SuppressionPage() {
  const [tab, setTab] = useState<Tab>('emails')
  const [items, setItems] = useState<SuppressionEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [reasonFilter, setReasonFilter] = useState<Reason | ''>('')
  const [showAdd, setShowAdd] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newReason, setNewReason] = useState<string>('manual')
  const [newNotes, setNewNotes] = useState('')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState('')
  const [showImport, setShowImport] = useState(false)
  const [importText, setImportText] = useState('')
  const [importReason, setImportReason] = useState('manual')
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<{ added: number; skipped: number } | null>(null)
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const isDomainTab = tab === 'domains'

  const load = async (p = page) => {
    setLoading(true)
    try {
      const searchParam = isDomainTab ? '@' : search || undefined
      const { data } = await suppressionApi.list(p, PAGE_SIZE, reasonFilter || undefined, searchParam)
      // For email tab: exclude domain entries (starting with @)
      // For domain tab: only domain entries
      const filtered = data.items.filter((i) =>
        isDomainTab ? i.email.startsWith('@') : !i.email.startsWith('@'),
      )
      setItems(filtered)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [page, reasonFilter, tab])

  const handleSearchChange = (val: string) => {
    setSearch(val)
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => {
      setPage(1)
      void load(1)
    }, 350)
  }

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault()
    setAddError('')
    setAdding(true)
    const email = isDomainTab ? `@${newEmail.replace(/^@/, '')}` : newEmail
    try {
      await suppressionApi.add(email, newReason, newNotes || undefined)
      setShowAdd(false)
      setNewEmail('')
      setNewReason('manual')
      setNewNotes('')
      setPage(1)
      await load(1)
    } catch {
      setAddError('Failed to add. Entry may already exist.')
    } finally {
      setAdding(false)
    }
  }

  const handleRemove = async (id: string) => {
    await suppressionApi.remove(id)
    await load()
  }

  const handleImport = async () => {
    const emails = importText.split(/[\n,]+/).map((e) => e.trim()).filter(Boolean)
    if (!emails.length) return
    setImporting(true)
    try {
      const { data } = await suppressionApi.bulkImport(emails, importReason)
      setImportResult(data)
      setImportText('')
      setPage(1)
      await load(1)
    } finally {
      setImporting(false)
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">
          Suppression List{' '}
          <span className="text-text-muted text-base font-normal">({total.toLocaleString()})</span>
        </h1>
        <div className="flex gap-2">
          <a
            href={suppressionApi.exportUrl(reasonFilter || undefined)}
            className="btn-secondary flex items-center gap-2 text-sm"
            download="suppression.csv"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </a>
          <button
            className="btn-secondary flex items-center gap-2 text-sm"
            onClick={() => { setShowImport(true); setImportResult(null) }}
          >
            <Upload className="w-4 h-4" />
            Import
          </button>
          <button
            className="btn-secondary p-2"
            onClick={() => { void load() }}
            disabled={loading}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            className="btn-primary flex items-center gap-2 text-sm"
            onClick={() => setShowAdd(true)}
          >
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {(['emails', 'domains'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setPage(1); setSearch('') }}
            className={clsx(
              'px-4 py-2.5 text-sm border-b-2 transition-colors capitalize',
              tab === t
                ? 'border-accent-yellow text-text-primary font-medium'
                : 'border-transparent text-text-secondary hover:text-text-primary',
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 items-center">
        {!isDomainTab && (
          <input
            className="input text-sm w-64"
            placeholder="Search email…"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
          />
        )}
        <select
          className="input text-sm w-44"
          value={reasonFilter}
          onChange={(e) => { setReasonFilter(e.target.value as Reason | ''); setPage(1) }}
        >
          <option value="">All reasons</option>
          {REASONS.map((r) => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
        </select>
      </div>

      {/* Add modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="card w-96 space-y-4">
            <h2 className="text-base font-semibold text-text-primary">
              Add to Suppression — {isDomainTab ? 'Domain' : 'Email'}
            </h2>
            <form onSubmit={(e) => { void handleAdd(e) }} className="space-y-4">
              <div>
                <label className="block text-xs text-text-secondary mb-1.5">
                  {isDomainTab ? 'Domain (without @)' : 'Email'}
                </label>
                <div className="flex items-center gap-1">
                  {isDomainTab && <span className="text-text-muted text-sm">@</span>}
                  <input
                    type={isDomainTab ? 'text' : 'email'}
                    className="input flex-1"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder={isDomainTab ? 'competitor.com' : 'user@domain.com'}
                    required
                    autoFocus
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-text-secondary mb-1.5">Reason</label>
                <select className="input" value={newReason} onChange={(e) => setNewReason(e.target.value)}>
                  {REASONS.map((r) => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-secondary mb-1.5">Notes (optional)</label>
                <input
                  className="input"
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="Details…"
                />
              </div>
              {addError && (
                <p className="text-xs text-accent-red bg-red-900/20 border border-red-800/30 rounded px-3 py-2">
                  {addError}
                </p>
              )}
              <div className="flex gap-2 justify-end">
                <button type="button" className="btn-secondary" onClick={() => { setShowAdd(false); setAddError('') }}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={adding}>{adding ? 'Adding…' : 'Add'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import modal */}
      {showImport && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="card w-[480px] space-y-4">
            <h2 className="text-base font-semibold text-text-primary">Bulk Import</h2>
            <p className="text-xs text-text-muted">Paste one email per line (or comma-separated). Duplicates are skipped.</p>
            <textarea
              className="input w-full font-mono text-xs resize-y"
              rows={8}
              placeholder={"user@a.com\nuser@b.com\n..."}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
            />
            <div className="flex items-center gap-3">
              <label className="text-xs text-text-muted shrink-0">Reason:</label>
              <select className="input text-sm" value={importReason} onChange={(e) => setImportReason(e.target.value)}>
                {REASONS.map((r) => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
              </select>
            </div>
            {importResult && (
              <p className="text-xs text-accent-green">
                Done — {importResult.added} added, {importResult.skipped} skipped (duplicates).
              </p>
            )}
            <div className="flex gap-2 justify-end">
              <button className="btn-secondary" onClick={() => { setShowImport(false); setImportResult(null) }}>Close</button>
              <button className="btn-primary text-sm" disabled={importing || !importText.trim()} onClick={() => void handleImport()}>
                {importing ? 'Importing…' : 'Import'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-border">
              <th className="text-left pb-2 font-medium">{isDomainTab ? 'Domain' : 'Email'}</th>
              <th className="text-left pb-2 font-medium">Reason</th>
              <th className="text-left pb-2 font-medium">Notes</th>
              <th className="text-left pb-2 font-medium">Added</th>
              <th className="text-right pb-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              <tr><td colSpan={5} className="py-6 text-center text-text-muted">Loading…</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={5} className="py-6 text-center text-text-muted">No entries found.</td></tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} className="hover:bg-bg-hover">
                  <td className="py-2 font-mono text-text-primary">{item.email}</td>
                  <td className="py-2"><ReasonBadge reason={item.reason} /></td>
                  <td className="py-2 text-text-muted max-w-[200px] truncate">{item.notes ?? '—'}</td>
                  <td className="py-2 text-text-muted">{new Date(item.added_at).toLocaleDateString()}</td>
                  <td className="py-2 text-right">
                    <button className="text-text-muted hover:text-accent-red transition-colors" onClick={() => { void handleRemove(item.id) }}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
            <span className="text-xs text-text-muted">Page {page} of {totalPages} · {total.toLocaleString()} total</span>
            <div className="flex gap-2">
              <button className="btn-secondary py-1 px-3 text-xs" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
              <button className="btn-secondary py-1 px-3 text-xs" disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
        )}
      </div>

      {isDomainTab && (
        <div className="card bg-bg-secondary text-xs text-text-muted space-y-1">
          <p className="font-medium text-text-secondary">How domain suppression works</p>
          <p>Entries stored as <code className="text-accent-yellow">@domain.com</code>. The sending pipeline checks the recipient's email domain against this list before queuing.</p>
        </div>
      )}
    </div>
  )
}
