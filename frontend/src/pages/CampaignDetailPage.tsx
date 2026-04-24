import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Eye,
  Plus,
  RefreshCw,
  Send,
  Trash2,
  X,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { campaignsApi, type CampaignStats, type RecipientRow, type Sequence, type SequenceStep } from '../lib/api'

const STATUS_COLORS: Record<string, string> = {
  queued: 'badge-muted',
  sent: 'badge-blue',
  delivered: 'badge-blue',
  opened: 'badge-green',
  clicked: 'badge-green',
  replied: 'badge-green',
  bounced: 'badge-red',
  unsubscribed: 'badge-yellow',
}

const TABS = ['Overview', 'Recipients', 'A/B Results', 'Sequences'] as const
type Tab = (typeof TABS)[number]

const CHART_BG = '#161B22'
const GRID_COLOR = '#30363D'
const TICK_COLOR = '#8B949E'
const TOOLTIP_STYLE = {
  backgroundColor: '#1C2128',
  border: '1px solid #30363D',
  borderRadius: 6,
  color: '#E6EDF3',
  fontSize: 12,
}

// ── Sequence Builder ──────────────────────────────────────────────────────────

function StepRow({
  campaignId, seqId, step, onDelete, onUpdated,
}: {
  campaignId: string
  seqId: string
  step: SequenceStep
  onDelete: () => void
  onUpdated: (s: SequenceStep) => void
}) {
  const [editing, setEditing] = useState(false)
  const [subject, setSubject] = useState(step.email_subject)
  const [delay, setDelay] = useState(step.delay_days)
  const [body, setBody] = useState(step.email_body_html)
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    try {
      const { data } = await campaignsApi.updateStep(campaignId, seqId, step.id, {
        delay_days: delay, email_subject: subject, email_body_html: body,
      })
      onUpdated(data)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="border border-border rounded-md p-3 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono text-text-muted w-14 shrink-0">Step {step.step_number}</span>
        {editing ? (
          <>
            <input
              className="input text-xs flex-1"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Subject"
            />
            <input
              type="number"
              className="input text-xs w-20"
              value={delay}
              min={1}
              onChange={(e) => setDelay(Number(e.target.value))}
            />
            <span className="text-xs text-text-muted">days after prev</span>
            <button className="btn-primary text-xs py-1 px-2" onClick={() => { void save() }} disabled={saving}>
              {saving ? '…' : 'Save'}
            </button>
            <button className="btn-secondary text-xs py-1 px-2" onClick={() => setEditing(false)}>Cancel</button>
          </>
        ) : (
          <>
            <span className="flex-1 text-sm text-text-primary truncate">{step.email_subject || '(no subject)'}</span>
            <span className="text-xs text-text-muted shrink-0">+{step.delay_days}d</span>
            <button className="text-text-muted hover:text-text-primary text-xs" onClick={() => setEditing(true)}>Edit</button>
            <button className="text-accent-red hover:text-accent-red/70" onClick={onDelete}>
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </>
        )}
      </div>
      {editing && (
        <textarea
          className="input text-xs w-full h-24 font-mono resize-y"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Email body HTML"
        />
      )}
    </div>
  )
}

function AddStepForm({
  campaignId, seqId, nextStepNumber, onAdded,
}: {
  campaignId: string
  seqId: string
  nextStepNumber: number
  onAdded: (s: SequenceStep) => void
}) {
  const [open, setOpen] = useState(false)
  const [subject, setSubject] = useState('')
  const [delay, setDelay] = useState(3)
  const [body, setBody] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!subject.trim()) return
    setSaving(true)
    try {
      const { data } = await campaignsApi.addStep(campaignId, seqId, {
        step_number: nextStepNumber,
        delay_days: delay,
        email_subject: subject,
        email_body_html: body,
      })
      onAdded(data)
      setSubject(''); setBody(''); setDelay(3); setOpen(false)
    } finally {
      setSaving(false)
    }
  }

  if (!open) {
    return (
      <button className="flex items-center gap-1 text-xs text-accent-blue hover:text-accent-blue/80 mt-2" onClick={() => setOpen(true)}>
        <Plus className="w-3.5 h-3.5" /> Add step
      </button>
    )
  }

  return (
    <div className="border border-dashed border-border rounded-md p-3 space-y-2 mt-2">
      <div className="flex gap-2">
        <input className="input text-xs flex-1" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject *" />
        <input type="number" className="input text-xs w-20" value={delay} min={1} onChange={(e) => setDelay(Number(e.target.value))} />
        <span className="text-xs text-text-muted self-center shrink-0">days after prev</span>
      </div>
      <textarea className="input text-xs w-full h-20 font-mono resize-y" value={body} onChange={(e) => setBody(e.target.value)} placeholder="Email body HTML (optional)" />
      <div className="flex gap-2">
        <button className="btn-primary text-xs py-1 px-3" onClick={() => { void submit() }} disabled={saving || !subject.trim()}>
          {saving ? 'Adding…' : 'Add Step'}
        </button>
        <button className="btn-secondary text-xs py-1 px-3" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </div>
  )
}

function SequenceCard({
  campaignId, seq, onDeleted, onChanged,
}: {
  campaignId: string
  seq: Sequence
  onDeleted: () => void
  onChanged: (s: Sequence) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const [steps, setSteps] = useState<SequenceStep[]>(seq.steps)
  const [toggling, setToggling] = useState(false)

  const toggleActive = async () => {
    setToggling(true)
    try {
      const { data } = await campaignsApi.updateSequence(campaignId, seq.id, { is_active: !seq.is_active })
      onChanged(data)
    } finally {
      setToggling(false)
    }
  }

  const handleDeleteStep = async (stepId: string) => {
    await campaignsApi.deleteStep(campaignId, seq.id, stepId)
    setSteps((prev) => prev.filter((s) => s.id !== stepId))
  }

  const handleUpdatedStep = (updated: SequenceStep) => {
    setSteps((prev) => prev.map((s) => s.id === updated.id ? updated : s))
  }

  const handleAddedStep = (step: SequenceStep) => {
    setSteps((prev) => [...prev, step].sort((a, b) => a.step_number - b.step_number))
  }

  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-3">
        <button onClick={() => setExpanded((v) => !v)} className="text-text-muted hover:text-text-primary">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
        <span className="flex-1 text-sm font-medium text-text-primary">{seq.name}</span>
        <button
          onClick={() => { void toggleActive() }}
          disabled={toggling}
          className={`text-xs px-2 py-0.5 rounded-full border font-medium transition-colors ${
            seq.is_active
              ? 'border-accent-green/40 text-accent-green bg-accent-green/10 hover:bg-accent-green/20'
              : 'border-border text-text-muted hover:border-text-muted'
          }`}
        >
          {seq.is_active ? 'Active' : 'Paused'}
        </button>
        {seq.stop_on_reply && (
          <span className="text-xs badge badge-muted">stops on reply</span>
        )}
        <button className="text-accent-red hover:text-accent-red/70" onClick={onDeleted}>
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {expanded && (
        <div className="space-y-2 pl-7">
          {steps.length === 0 && (
            <p className="text-xs text-text-muted">No steps yet. Add the first follow-up below.</p>
          )}
          {steps.map((s) => (
            <StepRow
              key={s.id}
              campaignId={campaignId}
              seqId={seq.id}
              step={s}
              onDelete={() => { void handleDeleteStep(s.id) }}
              onUpdated={handleUpdatedStep}
            />
          ))}
          <AddStepForm
            campaignId={campaignId}
            seqId={seq.id}
            nextStepNumber={steps.length + 1}
            onAdded={handleAddedStep}
          />
        </div>
      )}
    </div>
  )
}

function SequencesTab({ campaignId }: { campaignId: string }) {
  const [sequences, setSequences] = useState<Sequence[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('Follow-up sequence')
  const [stopOnReply, setStopOnReply] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await campaignsApi.listSequences(campaignId)
      setSequences(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [campaignId])

  const createSeq = async () => {
    setCreating(true)
    try {
      const { data } = await campaignsApi.createSequence(campaignId, {
        name: newName || 'Follow-up sequence',
        stop_on_reply: stopOnReply,
      })
      setSequences((prev) => [...prev, data])
      setNewName('Follow-up sequence')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (seqId: string) => {
    await campaignsApi.deleteSequence(campaignId, seqId)
    setSequences((prev) => prev.filter((s) => s.id !== seqId))
  }

  const handleChanged = (updated: Sequence) => {
    setSequences((prev) => prev.map((s) => s.id === updated.id ? { ...updated, steps: s.steps } : s))
  }

  if (loading) return <div className="text-xs text-text-muted p-4">Loading…</div>

  return (
    <div className="space-y-4 max-w-2xl">
      {/* Create new sequence */}
      <div className="card space-y-3">
        <h3 className="text-sm font-semibold text-text-primary">New Sequence</h3>
        <div className="flex gap-3 items-center">
          <input
            className="input text-sm flex-1"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Sequence name"
          />
          <label className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer select-none">
            <input
              type="checkbox"
              checked={stopOnReply}
              onChange={(e) => setStopOnReply(e.target.checked)}
              className="accent-accent-yellow"
            />
            Stop on reply
          </label>
          <button className="btn-primary text-sm" onClick={() => { void createSeq() }} disabled={creating}>
            {creating ? '…' : 'Create'}
          </button>
        </div>
      </div>

      {/* Existing sequences */}
      {sequences.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-text-muted text-sm">No sequences yet. Create one above to start a drip campaign.</p>
        </div>
      ) : (
        sequences.map((seq) => (
          <SequenceCard
            key={seq.id}
            campaignId={campaignId}
            seq={seq}
            onDeleted={() => { void handleDelete(seq.id) }}
            onChanged={handleChanged}
          />
        ))
      )}
    </div>
  )
}

// ── Preview / Test Send Modal ─────────────────────────────────────────────────

function PreviewModal({ campaignId, onClose }: { campaignId: string; onClose: () => void }) {
  const [tab, setTab] = useState<'preview' | 'send'>('preview')
  const [firstName, setFirstName] = useState('Alex')
  const [company, setCompany] = useState('Acme Corp')
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [previewSubject, setPreviewSubject] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [toEmail, setToEmail] = useState('')
  const [subjectOverride, setSubjectOverride] = useState('')
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadPreview = async () => {
    setPreviewLoading(true)
    setError(null)
    try {
      const { data } = await campaignsApi.preview(campaignId, firstName, company)
      setPreviewHtml(data.html)
      setPreviewSubject(data.subject)
      if (!subjectOverride) setSubjectOverride(data.subject)
    } catch {
      setError('Failed to load preview.')
    } finally {
      setPreviewLoading(false)
    }
  }

  useEffect(() => { void loadPreview() }, [])

  const handleSend = async () => {
    if (!toEmail.trim()) return
    setSending(true)
    setSendResult(null)
    setError(null)
    try {
      await campaignsApi.testSend(campaignId, toEmail.trim(), subjectOverride || undefined)
      setSendResult(`Test email sent to ${toEmail.trim()}`)
    } catch {
      setError('Failed to send test email. Check SMTP configuration.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-bg-secondary border border-border rounded-lg w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border shrink-0">
          <div className="flex gap-1">
            <button
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${tab === 'preview' ? 'bg-bg-tertiary text-text-primary' : 'text-text-muted hover:text-text-secondary'}`}
              onClick={() => setTab('preview')}
            >
              <Eye className="w-3.5 h-3.5" /> Preview
            </button>
            <button
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors ${tab === 'send' ? 'bg-bg-tertiary text-text-primary' : 'text-text-muted hover:text-text-secondary'}`}
              onClick={() => setTab('send')}
            >
              <Send className="w-3.5 h-3.5" /> Test Send
            </button>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Preview tab */}
          {tab === 'preview' && (
            <>
              {/* Sample data inputs */}
              <div className="flex gap-3 items-end">
                <label className="flex-1 space-y-1">
                  <span className="text-xs text-text-muted">first_name</span>
                  <input className="input text-sm w-full" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                </label>
                <label className="flex-1 space-y-1">
                  <span className="text-xs text-text-muted">company</span>
                  <input className="input text-sm w-full" value={company} onChange={(e) => setCompany(e.target.value)} />
                </label>
                <button className="btn-secondary text-sm shrink-0" onClick={() => { void loadPreview() }} disabled={previewLoading}>
                  {previewLoading ? 'Loading…' : 'Refresh'}
                </button>
              </div>

              {error && <div className="text-accent-red text-xs">{error}</div>}

              {previewSubject && (
                <div className="bg-bg-tertiary border border-border rounded-md px-3 py-2">
                  <span className="text-xs text-text-muted">Subject: </span>
                  <span className="text-sm text-text-primary">{previewSubject}</span>
                </div>
              )}

              {previewLoading ? (
                <div className="h-64 flex items-center justify-center text-text-muted text-sm">Loading preview…</div>
              ) : previewHtml ? (
                <div className="border border-border rounded-md overflow-hidden bg-white">
                  <iframe
                    srcDoc={previewHtml}
                    className="w-full"
                    style={{ height: '480px', border: 'none' }}
                    sandbox="allow-same-origin"
                    title="Email preview"
                  />
                </div>
              ) : null}
            </>
          )}

          {/* Test Send tab */}
          {tab === 'send' && (
            <div className="space-y-4 max-w-md">
              <p className="text-sm text-text-secondary">
                Send a test email to verify layout and content before launching the campaign.
              </p>
              <label className="block space-y-1">
                <span className="text-xs text-text-muted">Recipient email *</span>
                <input
                  className="input text-sm w-full"
                  type="email"
                  value={toEmail}
                  onChange={(e) => setToEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-xs text-text-muted">Subject override (optional)</span>
                <input
                  className="input text-sm w-full"
                  value={subjectOverride}
                  onChange={(e) => setSubjectOverride(e.target.value)}
                  placeholder="Leave blank to use campaign subject"
                />
              </label>

              {error && <div className="text-accent-red text-xs">{error}</div>}
              {sendResult && <div className="text-accent-green text-xs">{sendResult}</div>}

              <button
                className="btn-primary text-sm flex items-center gap-2"
                onClick={() => { void handleSend() }}
                disabled={sending || !toEmail.trim()}
              >
                <Send className="w-3.5 h-3.5" />
                {sending ? 'Sending…' : 'Send Test Email'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KPI({ label, value, sub, warn }: { label: string; value: string | number; sub?: string; warn?: boolean }) {
  return (
    <div className="card text-center py-3">
      <div className={`text-2xl font-mono font-bold ${warn ? 'text-accent-red' : 'text-text-primary'}`}>
        {value}
      </div>
      <div className="text-xs text-text-muted mt-0.5">{label}</div>
      {sub && <div className="text-xs text-text-secondary mt-0.5">{sub}</div>}
    </div>
  )
}

// ── Funnel ────────────────────────────────────────────────────────────────────

function FunnelChart({ stats }: { stats: CampaignStats }) {
  const data = [
    { stage: 'Sent', value: stats.sent, color: '#58A6FF' },
    { stage: 'Delivered', value: stats.delivered, color: '#3FB950' },
    { stage: 'Opened', value: stats.opened, color: '#F0B429' },
    { stage: 'Clicked', value: stats.clicked, color: '#BC8CFF' },
    { stage: 'Replied', value: stats.replied, color: '#F0B429' },
  ]
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
        <XAxis dataKey="stage" tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          cursor={{ fill: 'rgba(255,255,255,0.04)' }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} background={{ fill: CHART_BG }}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('Overview')
  const [stats, setStats] = useState<CampaignStats | null>(null)
  const [recipients, setRecipients] = useState<RecipientRow[]>([])
  const [recTotal, setRecTotal] = useState(0)
  const [recPage, setRecPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [recLoading, setRecLoading] = useState(false)
  const [showPreview, setShowPreview] = useState(false)

  const loadStats = async () => {
    if (!id) return
    setLoading(true)
    try {
      const { data } = await campaignsApi.stats(id)
      setStats(data)
    } finally {
      setLoading(false)
    }
  }

  const loadRecipients = async (page = 1, sf = statusFilter) => {
    if (!id) return
    setRecLoading(true)
    try {
      const { data } = await campaignsApi.recipients(id, page, 50, sf)
      setRecipients(data.items)
      setRecTotal(data.total)
    } finally {
      setRecLoading(false)
    }
  }

  useEffect(() => { void loadStats() }, [id])

  useEffect(() => {
    if (tab === 'Recipients') void loadRecipients(recPage, statusFilter)
  }, [tab, recPage, statusFilter])

  if (loading || !stats) {
    return <div className="p-6 text-text-secondary text-sm">Loading…</div>
  }

  const recTotalPages = Math.ceil(recTotal / 50)

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-border bg-bg-secondary shrink-0">
        <button onClick={() => navigate('/campaigns')} className="text-text-muted hover:text-text-primary">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1">
          <h1 className="text-base font-semibold text-text-primary">{stats.name}</h1>
          <div className="text-xs text-text-muted">{id?.slice(0, 8)}… · {stats.status}</div>
        </div>
        <button
          className="btn-secondary flex items-center gap-1.5 text-sm px-3 py-1.5"
          onClick={() => setShowPreview(true)}
          title="Preview & Test Send"
        >
          <Eye className="w-3.5 h-3.5" /> Preview
        </button>
        <button
          className="btn-secondary p-2"
          onClick={() => { void loadStats() }}
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
      {showPreview && id && (
        <PreviewModal campaignId={id} onClose={() => setShowPreview(false)} />
      )}

      {/* Alerts */}
      {stats.alerts.length > 0 && (
        <div className="mx-6 mt-4 space-y-2">
          {stats.alerts.map((a, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded-md bg-accent-red/10 border border-accent-red/30 px-3 py-2 text-sm text-accent-red"
            >
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {a.message}
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-0 border-b border-border px-6 mt-4 shrink-0">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t
                ? 'border-accent-yellow text-text-primary'
                : 'border-transparent text-text-muted hover:text-text-secondary'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-6">

        {/* ── Overview ── */}
        {tab === 'Overview' && (
          <div className="space-y-6 max-w-4xl">
            {/* KPI grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <KPI label="Sent" value={stats.sent.toLocaleString()} />
              <KPI label="Open Rate" value={`${stats.open_rate}%`} sub={`${stats.opened} opens`} />
              <KPI label="Click Rate" value={`${stats.click_rate}%`} sub={`${stats.clicked} clicks`} />
              <KPI
                label="Bounce Rate"
                value={`${stats.bounce_rate}%`}
                sub={`${stats.bounced} bounced`}
                warn={stats.bounce_rate > 2}
              />
              <KPI label="Reply Rate" value={`${stats.reply_rate}%`} sub={`${stats.replied} replies`} />
              <KPI label="Unsubscribes" value={stats.unsubscribed.toLocaleString()} warn={stats.unsub_rate > 0.5} />
              <KPI label="Delivered" value={stats.delivered.toLocaleString()} />
              <KPI label="Queued" value={stats.total_queued.toLocaleString()} />
            </div>

            {/* Funnel chart */}
            <div className="card">
              <h2 className="text-sm font-semibold text-text-primary mb-4">Delivery Funnel</h2>
              <FunnelChart stats={stats} />
            </div>
          </div>
        )}

        {/* ── Recipients ── */}
        {tab === 'Recipients' && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setRecPage(1) }}
                className="input text-sm w-40"
              >
                <option value="">All statuses</option>
                {['queued', 'sent', 'delivered', 'opened', 'clicked', 'replied', 'bounced', 'unsubscribed'].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <span className="text-xs text-text-muted">{recTotal.toLocaleString()} total</span>
            </div>

            <div className="card overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-text-muted border-b border-border">
                    <th className="text-left pb-2 font-medium">Recipient</th>
                    <th className="text-left pb-2 font-medium">Subject</th>
                    <th className="text-left pb-2 font-medium">Status</th>
                    <th className="text-left pb-2 font-medium">Sent</th>
                    <th className="text-left pb-2 font-medium">Opened</th>
                    <th className="text-right pb-2 font-medium">Clicks</th>
                    <th className="text-left pb-2 font-medium">Bounce</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {recLoading ? (
                    <tr><td colSpan={7} className="py-6 text-center text-text-muted">Loading…</td></tr>
                  ) : recipients.length === 0 ? (
                    <tr><td colSpan={7} className="py-6 text-center text-text-muted">No recipients yet.</td></tr>
                  ) : (
                    recipients.map((r) => (
                      <tr key={r.id} className="hover:bg-bg-hover">
                        <td className="py-2 text-text-secondary max-w-[180px] truncate">{r.contact}</td>
                        <td className="py-2 text-text-muted max-w-[160px] truncate">{r.subject}</td>
                        <td className="py-2">
                          <span className={`badge ${STATUS_COLORS[r.status] ?? 'badge-muted'}`}>
                            {r.status}
                          </span>
                        </td>
                        <td className="py-2 text-text-muted">
                          {r.sent_at ? new Date(r.sent_at).toLocaleString() : '—'}
                        </td>
                        <td className="py-2 text-text-muted">
                          {r.opened_at ? new Date(r.opened_at).toLocaleString() : '—'}
                        </td>
                        <td className="py-2 text-right font-mono text-text-primary">{r.click_count}</td>
                        <td className="py-2 text-accent-red text-xs max-w-[120px] truncate">
                          {r.bounce_reason ?? '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>

              {recTotalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
                  <span className="text-xs text-text-muted">
                    Page {recPage} of {recTotalPages}
                  </span>
                  <div className="flex gap-1">
                    <button
                      className="btn-secondary py-1 px-3 text-xs"
                      disabled={recPage === 1}
                      onClick={() => setRecPage((p) => p - 1)}
                    >
                      Prev
                    </button>
                    <button
                      className="btn-secondary py-1 px-3 text-xs"
                      disabled={recPage === recTotalPages}
                      onClick={() => setRecPage((p) => p + 1)}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Sequences ── */}
        {tab === 'Sequences' && id && <SequencesTab campaignId={id} />}

        {/* ── A/B Results ── */}
        {tab === 'A/B Results' && (
          <div className="max-w-2xl">
            {!stats.ab_results ? (
              <div className="card text-center py-8">
                <p className="text-text-muted text-sm">A/B testing was not enabled for this campaign.</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  {(['a', 'b'] as const).map((v) => {
                    const ab = stats.ab_results!
                    const sent = v === 'a' ? ab.a_sent : ab.b_sent
                    const opened = v === 'a' ? ab.a_opened : ab.b_opened
                    const openRate = sent > 0 ? ((opened / sent) * 100).toFixed(1) : '0.0'
                    const subject = v === 'a' ? ab.subject_a : ab.subject_b
                    const winner = ab.a_opened / Math.max(ab.a_sent, 1) >= ab.b_opened / Math.max(ab.b_sent, 1) ? 'a' : 'b'
                    return (
                      <div
                        key={v}
                        className={`card space-y-3 ${winner === v ? 'border-accent-yellow/40' : ''}`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-text-muted uppercase">
                            Variant {v.toUpperCase()}
                          </span>
                          {winner === v && (
                            <span className="text-xs badge badge-yellow">Winner</span>
                          )}
                        </div>
                        <div className="text-sm text-text-primary font-medium truncate">{subject}</div>
                        <div className="space-y-1 text-xs">
                          <div className="flex justify-between text-text-secondary">
                            <span>Sent</span>
                            <span className="font-mono text-text-primary">{sent.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between text-text-secondary">
                            <span>Opened</span>
                            <span className="font-mono text-text-primary">{opened.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between text-text-secondary">
                            <span>Open rate</span>
                            <span className={`font-mono font-semibold ${winner === v ? 'text-accent-green' : 'text-text-primary'}`}>
                              {openRate}%
                            </span>
                          </div>
                        </div>
                        {/* Mini bar */}
                        <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
                          <div
                            className={winner === v ? 'bg-accent-green h-full rounded-full' : 'bg-accent-yellow h-full rounded-full'}
                            style={{ width: `${openRate}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Comparison bar chart */}
                <div className="card">
                  <h2 className="text-sm font-semibold text-text-primary mb-4">Open Rate Comparison</h2>
                  <ResponsiveContainer width="100%" height={160}>
                    <BarChart
                      data={[
                        {
                          name: 'Variant A',
                          rate: stats.ab_results.a_sent > 0
                            ? parseFloat(((stats.ab_results.a_opened / stats.ab_results.a_sent) * 100).toFixed(1))
                            : 0,
                        },
                        {
                          name: 'Variant B',
                          rate: stats.ab_results.b_sent > 0
                            ? parseFloat(((stats.ab_results.b_opened / stats.ab_results.b_sent) * 100).toFixed(1))
                            : 0,
                        },
                      ]}
                      margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: TICK_COLOR, fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
                      <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${v}%`, 'Open Rate']} />
                      <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
                        <Cell fill="#F0B429" />
                        <Cell fill="#58A6FF" />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
