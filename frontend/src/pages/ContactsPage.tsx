import { useEffect, useRef, useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  Download,
  ExternalLink,
  Pencil,
  Search,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import { contactsApi, type Contact, type ContactListParams, type ContactUpdate, type ImportResult } from '../lib/api'

const PAGE_SIZE = 50

type SortKey = 'email' | 'full_name' | 'company' | 'title' | 'confidence_score' | 'verified_status' | 'discovered_at' | 'audience_type_key' | 'country'

const VERIFIED_COLORS: Record<string, string> = {
  valid: 'badge-green',
  risky: 'badge-yellow',
  catch_all: 'badge-yellow',
  invalid: 'badge-red',
  unverified: 'badge-muted',
  disposable: 'badge-red',
  role_based: 'badge-muted',
}

function SortIcon({ col, sortBy, dir }: { col: string; sortBy: string; dir: 'asc' | 'desc' }) {
  if (col !== sortBy) return <ChevronsUpDown className="w-3 h-3 opacity-30" />
  return dir === 'asc'
    ? <ChevronUp className="w-3 h-3 text-accent-yellow" />
    : <ChevronDown className="w-3 h-3 text-accent-yellow" />
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-accent-green' : score >= 40 ? 'bg-accent-yellow' : 'bg-accent-red'
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-12 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="font-mono text-text-primary">{score}</span>
    </div>
  )
}

// ── Import modal ─────────────────────────────────────────────────────────────

function ImportModal({
  onDone,
  onClose,
}: {
  onDone: () => void
  onClose: () => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [audienceType, setAudienceType] = useState('imported')
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropRef = useRef<HTMLDivElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  const handleSubmit = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const { data } = await contactsApi.importContacts(file, audienceType)
      setResult(data)
      onDone()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Upload failed'
      setError(msg)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-text-primary">Import Contacts</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            <X className="w-4 h-4" />
          </button>
        </div>

        {!result ? (
          <>
            <div
              ref={dropRef}
              className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-accent-yellow transition-colors"
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <Upload className="w-8 h-8 mx-auto mb-2 text-text-muted" />
              {file ? (
                <p className="text-sm text-text-primary font-medium">{file.name}</p>
              ) : (
                <>
                  <p className="text-sm text-text-secondary">Drag & drop or click to select</p>
                  <p className="text-xs text-text-muted mt-1">CSV or XLSX · max 5,000 rows · 10 MB</p>
                </>
              )}
            </div>
            <input
              ref={inputRef}
              type="file"
              accept=".csv,.xlsx"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
            />

            <div className="mt-3">
              <label className="block text-xs text-text-muted mb-1">Default audience type</label>
              <input
                type="text"
                className="input w-full text-xs"
                value={audienceType}
                onChange={(e) => setAudienceType(e.target.value)}
                placeholder="imported"
              />
              <p className="text-xs text-text-muted mt-1">Applied when the file has no audience_type column</p>
            </div>

            <p className="text-xs text-text-muted mt-3">
              Required column: <code className="font-mono">email</code>. Optional: full_name, first_name, last_name, company, job_title, website, linkedin_url, twitter_handle, country, language, audience_type.
            </p>

            {error && <p className="text-xs text-accent-red mt-2">{error}</p>}

            <div className="flex gap-2 justify-end mt-4">
              <button className="btn-secondary" onClick={onClose}>Cancel</button>
              <button
                className="btn-primary flex items-center gap-1.5"
                disabled={!file || uploading}
                onClick={() => { void handleSubmit() }}
              >
                <Upload className="w-3.5 h-3.5" />
                {uploading ? 'Uploading…' : 'Import'}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-bg-secondary rounded-lg p-3">
                  <div className="text-2xl font-bold text-accent-green">{result.imported}</div>
                  <div className="text-xs text-text-muted mt-0.5">Imported</div>
                </div>
                <div className="bg-bg-secondary rounded-lg p-3">
                  <div className="text-2xl font-bold text-accent-yellow">{result.skipped}</div>
                  <div className="text-xs text-text-muted mt-0.5">Skipped</div>
                </div>
                <div className="bg-bg-secondary rounded-lg p-3">
                  <div className="text-2xl font-bold text-accent-red">{result.errors.length}</div>
                  <div className="text-xs text-text-muted mt-0.5">Errors</div>
                </div>
              </div>

              {result.errors.length > 0 && (
                <div className="max-h-48 overflow-y-auto">
                  <p className="text-xs text-text-muted mb-1">First {result.errors.length} errors:</p>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-text-muted border-b border-border">
                        <th className="pb-1 text-left">Row</th>
                        <th className="pb-1 text-left">Email</th>
                        <th className="pb-1 text-left">Error</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {result.errors.map((e) => (
                        <tr key={e.row}>
                          <td className="py-1 text-text-muted">{e.row}</td>
                          <td className="py-1 font-mono text-text-secondary truncate max-w-[120px]">{e.email || '—'}</td>
                          <td className="py-1 text-accent-red">{e.error}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="flex justify-end mt-4">
              <button className="btn-primary" onClick={onClose}>Done</button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── Inline edit modal ────────────────────────────────────────────────────────

function EditModal({
  contact,
  onSave,
  onClose,
}: {
  contact: Contact
  onSave: (id: string, patch: ContactUpdate) => Promise<void>
  onClose: () => void
}) {
  const [form, setForm] = useState<ContactUpdate>({
    full_name: contact.full_name,
    job_title: contact.job_title,
    company: contact.company,
    website: contact.website,
    linkedin_url: contact.linkedin_url,
    twitter_handle: contact.twitter_handle,
    country: contact.country,
    language: contact.language,
    confidence_score: contact.confidence_score,
  })
  const [saving, setSaving] = useState(false)

  const field = (label: string, key: keyof ContactUpdate, type = 'text') => (
    <div>
      <label className="block text-xs text-text-muted mb-1">{label}</label>
      <input
        type={type}
        value={(form[key] as string | number | null | undefined) ?? ''}
        onChange={(e) =>
          setForm({
            ...form,
            [key]: type === 'number' ? Number(e.target.value) : e.target.value || null,
          })
        }
        className="input w-full text-xs"
      />
    </div>
  )

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-text-primary">Edit Contact</h2>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="text-xs text-text-muted mb-4 font-mono">{contact.email}</div>
        <div className="space-y-3">
          {field('Full Name', 'full_name')}
          {field('Job Title', 'job_title')}
          {field('Company', 'company')}
          {field('Website', 'website')}
          {field('LinkedIn URL', 'linkedin_url')}
          {field('Twitter Handle', 'twitter_handle')}
          {field('Country (ISO)', 'country')}
          {field('Language (BCP 47)', 'language')}
          {field('Confidence Score', 'confidence_score', 'number')}
        </div>
        <div className="flex gap-2 justify-end mt-4">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn-primary"
            disabled={saving}
            onClick={async () => {
              setSaving(true)
              try { await onSave(contact.id, form) } finally { setSaving(false) }
            }}
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Expanded row ─────────────────────────────────────────────────────────────

function ExpandedRow({ c }: { c: Contact }) {
  return (
    <tr className="bg-bg-secondary">
      <td colSpan={9} className="px-4 py-3">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <div className="text-text-muted mb-0.5">Source</div>
            <div className="text-text-secondary truncate">{c.source_type}</div>
            {c.source_url && (
              <a href={c.source_url} target="_blank" rel="noreferrer"
                className="text-accent-blue flex items-center gap-1 truncate hover:underline">
                <ExternalLink className="w-3 h-3" /> {c.source_url}
              </a>
            )}
          </div>
          <div>
            <div className="text-text-muted mb-0.5">Validation</div>
            <div className="space-y-0.5">
              <div>MX: <span className={c.mx_valid ? 'text-accent-green' : 'text-accent-red'}>{c.mx_valid == null ? '—' : c.mx_valid ? 'ok' : 'fail'}</span></div>
              <div>SMTP: <span className={c.smtp_valid ? 'text-accent-green' : 'text-accent-red'}>{c.smtp_valid == null ? '—' : c.smtp_valid ? 'ok' : 'fail'}</span></div>
              {c.is_disposable && <div className="text-accent-red">Disposable</div>}
              {c.is_role_based && <div className="text-accent-yellow">Role-based</div>}
            </div>
          </div>
          <div>
            <div className="text-text-muted mb-0.5">Social</div>
            {c.linkedin_url
              ? <a href={c.linkedin_url} target="_blank" rel="noreferrer" className="text-accent-blue hover:underline truncate block">LinkedIn</a>
              : <span className="text-text-muted">—</span>}
            {c.twitter_handle && <div className="text-text-secondary">@{c.twitter_handle}</div>}
            {c.website && (
              <a href={c.website} target="_blank" rel="noreferrer" className="text-accent-blue hover:underline truncate block">{c.website}</a>
            )}
          </div>
          <div>
            <div className="text-text-muted mb-0.5">Meta</div>
            <div className="text-text-secondary">Country: {c.country ?? '—'}</div>
            <div className="text-text-secondary">Lang: {c.language ?? '—'}</div>
            <div className="text-text-secondary">Relevance: {c.relevance_score.toFixed(2)}</div>
          </div>
        </div>
      </td>
    </tr>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)

  // Filters
  const [search, setSearch] = useState('')
  const [audienceType, setAudienceType] = useState('')
  const [verifiedStatus, setVerifiedStatus] = useState('')
  const [minConf, setMinConf] = useState('')

  // Sort
  const [sortBy, setSortBy] = useState<SortKey>('discovered_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  // Selection
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false)
  const [bulkDeleting, setBulkDeleting] = useState(false)

  // Expanded / edit / import
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [editContact, setEditContact] = useState<Contact | null>(null)
  const [showImport, setShowImport] = useState(false)

  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const buildParams = (): ContactListParams => ({
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    audience_type: audienceType || undefined,
    verified_status: verifiedStatus || undefined,
    min_confidence: minConf ? Number(minConf) : undefined,
    sort_by: sortBy,
    sort_dir: sortDir,
  })

  const load = async (params?: ContactListParams) => {
    setLoading(true)
    try {
      const { data } = await contactsApi.list(params ?? buildParams())
      setContacts(data.items)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [page, sortBy, sortDir, audienceType, verifiedStatus, minConf])

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => {
      setPage(1)
      void load({ ...buildParams(), page: 1, search: search || undefined })
    }, 350)
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current) }
  }, [search])

  const handleSort = (col: SortKey) => {
    if (col === sortBy) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(col)
      setSortDir('desc')
    }
    setPage(1)
  }

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === contacts.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(contacts.map((c) => c.id)))
    }
  }

  const handleBulkDelete = async () => {
    setBulkDeleting(true)
    try {
      await contactsApi.bulkDelete(Array.from(selected))
      setSelected(new Set())
      setConfirmBulkDelete(false)
      await load()
    } finally {
      setBulkDeleting(false)
    }
  }

  const handleSaveEdit = async (id: string, patch: ContactUpdate) => {
    const { data } = await contactsApi.update(id, patch)
    setContacts((prev) => prev.map((c) => (c.id === id ? data : c)))
    setEditContact(null)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const Th = ({ col, label, right }: { col: SortKey; label: string; right?: boolean }) => (
    <th
      className={`pb-2 font-medium cursor-pointer select-none hover:text-text-primary ${right ? 'text-right' : 'text-left'}`}
      onClick={() => handleSort(col)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <SortIcon col={col} sortBy={sortBy} dir={sortDir} />
      </span>
    </th>
  )

  const exportParams = {
    audience_type: audienceType || undefined,
    verified_status: verifiedStatus || undefined,
    min_confidence: minConf ? Number(minConf) : undefined,
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-text-primary">
          Contacts{' '}
          <span className="text-text-muted text-base font-normal">
            ({total.toLocaleString()})
          </span>
        </h1>

        <div className="flex flex-wrap items-center gap-2">
          {selected.size > 0 && (
            <button
              className="btn-danger flex items-center gap-1.5 text-sm"
              onClick={() => setConfirmBulkDelete(true)}
            >
              <Trash2 className="w-4 h-4" />
              Delete {selected.size}
            </button>
          )}
          <button
            className="btn-secondary flex items-center gap-1.5 text-sm"
            onClick={() => setShowImport(true)}
          >
            <Upload className="w-4 h-4" />
            Import
          </button>
          <a
            href={contactsApi.exportUrl('csv', exportParams)}
            className="btn-secondary flex items-center gap-1.5 text-sm"
            download
          >
            <Download className="w-4 h-4" />
            CSV
          </a>
          <a
            href={contactsApi.exportUrl('json', exportParams)}
            className="btn-secondary flex items-center gap-1.5 text-sm"
            download
          >
            <Download className="w-4 h-4" />
            JSON
          </a>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            className="input pl-9 w-56 text-sm"
            placeholder="Search email, company…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input text-sm w-44"
          value={verifiedStatus}
          onChange={(e) => { setVerifiedStatus(e.target.value); setPage(1) }}
        >
          <option value="">All statuses</option>
          <option value="valid">Valid</option>
          <option value="risky">Risky</option>
          <option value="catch_all">Catch-all</option>
          <option value="invalid">Invalid</option>
          <option value="unverified">Unverified</option>
          <option value="disposable">Disposable</option>
          <option value="role_based">Role-based</option>
        </select>
        <input
          type="number"
          className="input text-sm w-32"
          placeholder="Min score"
          min={0}
          max={100}
          value={minConf}
          onChange={(e) => { setMinConf(e.target.value); setPage(1) }}
        />
        <input
          type="text"
          className="input text-sm w-32"
          placeholder="Audience key"
          value={audienceType}
          onChange={(e) => { setAudienceType(e.target.value); setPage(1) }}
        />
      </div>

      {/* Table */}
      <div className="card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-text-muted border-b border-border">
              <th className="pb-2 w-6">
                <input
                  type="checkbox"
                  checked={contacts.length > 0 && selected.size === contacts.length}
                  onChange={toggleAll}
                  className="accent-accent-yellow"
                />
              </th>
              <Th col="email" label="Email" />
              <Th col="full_name" label="Name" />
              <Th col="company" label="Company" />
              <Th col="title" label="Title" />
              <Th col="audience_type_key" label="Audience" />
              <Th col="confidence_score" label="Score" right />
              <Th col="verified_status" label="Status" />
              <th className="pb-2 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              <tr>
                <td colSpan={9} className="py-8 text-center text-text-muted">Loading…</td>
              </tr>
            ) : contacts.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-8 text-center text-text-muted">No contacts found.</td>
              </tr>
            ) : (
              contacts.map((c) => (
                <>
                  <tr
                    key={c.id}
                    className={`hover:bg-bg-hover cursor-pointer ${selected.has(c.id) ? 'bg-accent-yellow/5' : ''}`}
                  >
                    <td className="py-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selected.has(c.id)}
                        onChange={() => toggleSelect(c.id)}
                        className="accent-accent-yellow"
                      />
                    </td>
                    <td
                      className="py-2 font-mono text-accent-blue max-w-[180px] truncate"
                      onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                    >
                      {c.email}
                    </td>
                    <td
                      className="py-2 text-text-primary max-w-[120px] truncate"
                      onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                    >
                      {c.full_name ?? '—'}
                    </td>
                    <td
                      className="py-2 text-text-secondary max-w-[120px] truncate"
                      onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                    >
                      {c.company ?? '—'}
                    </td>
                    <td
                      className="py-2 text-text-muted max-w-[100px] truncate"
                      onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                    >
                      {c.job_title ?? '—'}
                    </td>
                    <td
                      className="py-2 text-text-muted max-w-[120px] truncate"
                      onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                    >
                      {c.audience_type}
                    </td>
                    <td
                      className="py-2 text-right"
                      onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                    >
                      <ScoreBar score={c.confidence_score} />
                    </td>
                    <td
                      className="py-2"
                      onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                    >
                      <span className={`badge ${VERIFIED_COLORS[c.verified_status] ?? 'badge-muted'}`}>
                        {c.verified_status}
                      </span>
                    </td>
                    <td className="py-2 text-right">
                      <button
                        className="p-1 text-text-muted hover:text-text-primary"
                        title="Edit"
                        onClick={(e) => { e.stopPropagation(); setEditContact(c) }}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                  {expandedId === c.id && <ExpandedRow key={`${c.id}-exp`} c={c} />}
                </>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
            <span className="text-xs text-text-muted">
              Page {page} of {totalPages} · {total.toLocaleString()} total
            </span>
            <div className="flex items-center gap-1">
              <button
                className="btn-secondary py-1 px-3 text-xs"
                disabled={page === 1}
                onClick={() => setPage(1)}
              >
                «
              </button>
              <button
                className="btn-secondary py-1 px-3 text-xs"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Prev
              </button>
              <span className="px-2 text-xs text-text-muted">{page}</span>
              <button
                className="btn-secondary py-1 px-3 text-xs"
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
              <button
                className="btn-secondary py-1 px-3 text-xs"
                disabled={page === totalPages}
                onClick={() => setPage(totalPages)}
              >
                »
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Import modal */}
      {showImport && (
        <ImportModal
          onDone={() => { void load() }}
          onClose={() => setShowImport(false)}
        />
      )}

      {/* Edit modal */}
      {editContact && (
        <EditModal
          contact={editContact}
          onSave={handleSaveEdit}
          onClose={() => setEditContact(null)}
        />
      )}

      {/* Bulk delete confirm */}
      {confirmBulkDelete && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="card w-96">
            <h2 className="text-base font-semibold text-text-primary mb-2">
              Delete {selected.size} contacts?
            </h2>
            <p className="text-sm text-text-secondary mb-4">
              This will permanently remove the selected contacts. This cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button className="btn-secondary" onClick={() => setConfirmBulkDelete(false)}>
                Cancel
              </button>
              <button
                className="btn-danger"
                disabled={bulkDeleting}
                onClick={() => { void handleBulkDelete() }}
              >
                {bulkDeleting ? 'Deleting…' : `Delete ${selected.size}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
