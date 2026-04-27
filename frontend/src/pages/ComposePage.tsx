import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AlertTriangle, CheckCircle, Loader, SendHorizonal, Sparkles, X } from 'lucide-react'
import RichEditor from '../components/RichEditor'
import {
  audienceTypesApi,
  campaignsApi,
  llmApi,
  smtpApi,
  type AudienceCategory,
  type Campaign,
  type CampaignCreate,
  type LLMConfig,
  type SMTPConfig,
} from '../lib/api'
import { useAuth } from '../lib/auth'

// ── Spam scorer ───────────────────────────────────────────────────────────────
const SPAM_WORDS = [
  'free', 'guaranteed', 'winner', 'urgent', 'act now', 'click here', 'buy now',
  'limited time', 'no obligation', 'risk free', 'special promotion', '100%', '!!!',
  'earn money', 'cash', 'prize', 'congratulations', 'dear friend', 'make money',
]

function spamScore(subject: string, body: string): number {
  const text = (subject + ' ' + body).toLowerCase()
  const hits = SPAM_WORDS.filter((w) => text.includes(w)).length
  return Math.min(100, hits * 12)
}

// ── Tab helpers ───────────────────────────────────────────────────────────────

const TABS = ['Recipients', 'Content', 'Preview', 'Schedule', 'Send'] as const
type Tab = (typeof TABS)[number]

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <div className="flex gap-0 border-b border-border">
      {TABS.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-5 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
            active === t
              ? 'border-accent-yellow text-text-primary'
              : 'border-transparent text-text-muted hover:text-text-secondary'
          }`}
        >
          {t}
        </button>
      ))}
    </div>
  )
}

// ── LIA modal ─────────────────────────────────────────────────────────────────

function LIAModal({
  reason,
  onChange,
  onConfirm,
  onClose,
  sending,
}: {
  reason: string
  onChange: (v: string) => void
  onConfirm: () => void
  onClose: () => void
  sending: boolean
}) {
  const valid = reason.trim().length >= 20
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-lg">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-base font-semibold text-text-primary">
              Legitimate Interest Assessment
            </h2>
            <p className="text-xs text-text-muted mt-1">Required before sending (GDPR Art. 6(1)(f))</p>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-sm text-text-secondary mb-3">
          Explain why your organisation has a legitimate interest in contacting these recipients
          and why that interest overrides their right to privacy.
        </p>

        <textarea
          rows={5}
          value={reason}
          onChange={(e) => onChange(e.target.value)}
          placeholder="e.g. We are contacting financial professionals who may benefit from our price comparison tool as part of our B2B outreach. Recipients are professionals likely to find this relevant."
          className="input w-full text-sm resize-y"
        />
        <div className="text-xs text-text-muted mt-1">
          {reason.trim().length} / 20 chars minimum
        </div>

        <div className="flex gap-2 justify-end mt-4">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className="btn-primary flex items-center gap-2"
            disabled={!valid || sending}
            onClick={onConfirm}
          >
            {sending ? <Loader className="w-4 h-4 animate-spin" /> : <SendHorizonal className="w-4 h-4" />}
            {sending ? 'Sending…' : 'Confirm & Send'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ComposePage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const user = useAuth((s) => s.user)

  const [tab, setTab] = useState<Tab>('Recipients')
  const [saving, setSaving] = useState(false)
  const [savedId, setSavedId] = useState<string | null>(searchParams.get('id'))
  const [saveError, setSaveError] = useState<string | null>(null)
  const [showLIA, setShowLIA] = useState(false)
  const [sending, setSending] = useState(false)
  const [sendSuccess, setSendSuccess] = useState(false)
  const [testSending, setTestSending] = useState(false)
  const [testSuccess, setTestSuccess] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)

  // Metadata
  const [smtpConfigs, setSmtpConfigs] = useState<SMTPConfig[]>([])
  const [llmConfigs, setLlmConfigs] = useState<LLMConfig[]>([])
  const [categories, setCategories] = useState<AudienceCategory[]>([])

  // Form state
  const [name, setName] = useState('New Campaign')
  const [selectedAudiences, setSelectedAudiences] = useState<string[]>([])
  const [targetCountries, setTargetCountries] = useState('')
  const [minConf, setMinConf] = useState(50)
  const [smtpId, setSmtpId] = useState('')
  const [llmId, setLlmId] = useState('')
  const [subject, setSubject] = useState('')
  const [subjectB, setSubjectB] = useState('')
  const [abEnabled, setAbEnabled] = useState(false)
  const [bodyHtml, setBodyHtml] = useState('')
  const [bodyText, setBodyText] = useState('')
  const [scheduledAt, setScheduledAt] = useState('')
  const [scheduleMode, setScheduleMode] = useState<'now' | 'scheduled' | 'batched'>('now')
  const [batchSize, setBatchSize] = useState(30)
  const [hourlyLimit, setHourlyLimit] = useState(50)
  const [liaReason, setLiaReason] = useState('')
  const [aiContext, setAiContext] = useState('')
  const [aiTone, setAiTone] = useState('professional')

  useEffect(() => {
    const init = async () => {
      const [smtp, llm, aud] = await Promise.all([
        smtpApi.list(),
        llmApi.list(),
        audienceTypesApi.list(),
      ])
      setSmtpConfigs(smtp.data)
      setLlmConfigs(llm.data)
      setCategories(aud.data.categories)
      if (smtp.data.find((s) => s.is_default)) {
        setSmtpId(smtp.data.find((s) => s.is_default)!.id)
      }
      if (llm.data.length > 0) setLlmId(llm.data[0].id)

      if (savedId) {
        const { data } = await campaignsApi.get(savedId)
        loadCampaign(data)
      }
    }
    void init()
  }, [])

  const loadCampaign = (c: Campaign) => {
    setName(c.name)
    setSelectedAudiences(c.target_audience_keys)
    setSmtpId(c.smtp_config_id ?? '')
    setLlmId(c.llm_config_id ?? '')
    setSubject(c.email_subject)
    setSubjectB(c.email_subject_b ?? '')
    setAbEnabled(!!c.email_subject_b)
    setBodyHtml(c.email_body_html)
    setBodyText(c.email_body_text)
    setLiaReason(c.legitimate_interest_reason)
    if (c.scheduled_at) {
      setScheduleMode('scheduled')
      setScheduledAt(c.scheduled_at.slice(0, 16))
    }
    if (c.batch_size_per_hour) {
      setScheduleMode('batched')
      setBatchSize(c.batch_size_per_hour)
    }
    if (c.hourly_limit) setHourlyLimit(c.hourly_limit)
  }

  const buildPayload = (): CampaignCreate => ({
    name,
    target_audience_keys: selectedAudiences,
    target_countries: targetCountries.split(',').map((s) => s.trim()).filter(Boolean),
    min_confidence: minConf,
    smtp_config_id: smtpId || null,
    llm_config_id: llmId || null,
    email_subject: subject,
    email_subject_b: abEnabled && subjectB ? subjectB : null,
    email_body_html: bodyHtml,
    email_body_text: bodyText,
    legitimate_interest_reason: liaReason,
    scheduled_at: scheduleMode === 'scheduled' && scheduledAt ? scheduledAt : null,
    batch_size_per_hour: scheduleMode === 'batched' ? batchSize : null,
    hourly_limit: hourlyLimit,
    dry_run: false,
  })

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      const payload = buildPayload()
      if (savedId) {
        await campaignsApi.update(savedId, payload)
      } else {
        const { data } = await campaignsApi.create(payload)
        setSavedId(data.id)
        navigate(`/compose?id=${data.id}`, { replace: true })
      }
    } catch {
      setSaveError('Failed to save draft.')
    } finally {
      setSaving(false)
    }
  }

  const handleTestSend = async () => {
    if (!savedId || !user?.email) return
    setTestSending(true)
    setTestSuccess(false)
    try {
      await handleSave()
      await campaignsApi.testSend(savedId, user.email, subject)
      setTestSuccess(true)
    } finally {
      setTestSending(false)
    }
  }

  const handleSend = async () => {
    setSending(true)
    try {
      if (!savedId) {
        const { data } = await campaignsApi.create(buildPayload())
        setSavedId(data.id)
        await campaignsApi.send(
          data.id,
          liaReason,
          scheduleMode === 'scheduled' ? scheduledAt : null,
          scheduleMode === 'batched' ? batchSize : null,
        )
      } else {
        await handleSave()
        await campaignsApi.send(
          savedId,
          liaReason,
          scheduleMode === 'scheduled' ? scheduledAt : null,
          scheduleMode === 'batched' ? batchSize : null,
        )
      }
      setSendSuccess(true)
      setShowLIA(false)
    } finally {
      setSending(false)
    }
  }

  const handleAIDraft = async () => {
    if (!aiContext.trim()) return
    setAiLoading(true)
    setAiError(null)
    try {
      const { data } = await campaignsApi.aiDraft({
        audience_key: selectedAudiences[0] ?? 'general',
        product_context: aiContext,
        tone: aiTone,
        language: 'en',
        llm_config_id: llmId || null,
      })
      if (data.subject) setSubject(data.subject)
      if (data.body_html) setBodyHtml(data.body_html)
      if (data.body_text) setBodyText(data.body_text)
    } catch {
      setAiError('AI draft failed. Check your LLM configuration.')
    } finally {
      setAiLoading(false)
    }
  }

  const score = spamScore(subject, bodyText)
  const scoreColor = score < 25 ? 'text-accent-green' : score < 55 ? 'text-accent-yellow' : 'text-accent-red'

  if (sendSuccess) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-12 text-center">
        <CheckCircle className="w-12 h-12 text-accent-green mb-4" />
        <h2 className="text-xl font-semibold text-text-primary mb-2">Campaign Queued!</h2>
        <p className="text-text-secondary text-sm mb-6">
          Your campaign has been queued for sending. Monitor progress in the Bot Control page.
        </p>
        <div className="flex gap-3">
          <button className="btn-secondary" onClick={() => navigate('/bot')}>Bot Control</button>
          <button className="btn-primary" onClick={() => { setSendSuccess(false); setSavedId(null); setSubject(''); setBodyHtml(''); setBodyText('') }}>
            New Campaign
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-bg-secondary shrink-0">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="text-base font-semibold bg-transparent text-text-primary border-0 focus:outline-none focus:ring-0 w-64"
            placeholder="Campaign name"
          />
          {savedId && <span className="text-xs text-text-muted font-mono">{savedId.slice(0, 8)}…</span>}
        </div>
        <div className="flex gap-2 items-center">
          {saveError && <span className="text-xs text-accent-red">{saveError}</span>}
          <button
            className="btn-secondary text-sm"
            onClick={() => { void handleSave() }}
            disabled={saving}
          >
            {saving ? 'Saving…' : 'Save Draft'}
          </button>
          <button
            className="btn-primary flex items-center gap-2 text-sm"
            onClick={() => setShowLIA(true)}
            disabled={!subject || !bodyHtml}
          >
            <SendHorizonal className="w-4 h-4" />
            Send
          </button>
        </div>
      </div>

      <TabBar active={tab} onChange={setTab} />

      <div className="flex-1 overflow-y-auto p-6">

        {/* ── Tab 1: Recipients ── */}
        {tab === 'Recipients' && (
          <div className="space-y-6 max-w-2xl">
            <div className="card space-y-4">
              <h2 className="text-sm font-semibold text-text-primary">Target Audience Types</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {categories.flatMap((cat) =>
                  cat.types.map((t) => (
                    <label key={t.key} className="flex items-center gap-2 text-xs cursor-pointer hover:text-text-primary text-text-secondary">
                      <input
                        type="checkbox"
                        checked={selectedAudiences.includes(t.key)}
                        onChange={() =>
                          setSelectedAudiences((prev) =>
                            prev.includes(t.key)
                              ? prev.filter((k) => k !== t.key)
                              : [...prev, t.key],
                          )
                        }
                        className="accent-accent-yellow"
                      />
                      {t.label_en}
                      {t.contact_count > 0 && (
                        <span className="text-text-muted">({t.contact_count})</span>
                      )}
                    </label>
                  )),
                )}
              </div>
              {selectedAudiences.length === 0 && (
                <p className="text-xs text-text-muted">No audience selected — all contacts will be eligible.</p>
              )}
            </div>

            <div className="card space-y-4">
              <h2 className="text-sm font-semibold text-text-primary">Filters</h2>
              <div>
                <label className="block text-xs text-text-muted mb-1">
                  Min Confidence: {minConf}%
                </label>
                <input
                  type="range" min={0} max={100} value={minConf}
                  onChange={(e) => setMinConf(Number(e.target.value))}
                  className="w-full accent-accent-yellow"
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Target Countries (comma-separated ISO codes)</label>
                <input
                  type="text"
                  value={targetCountries}
                  onChange={(e) => setTargetCountries(e.target.value)}
                  placeholder="US, GB, DE (empty = all)"
                  className="input w-full text-sm"
                />
              </div>
            </div>
          </div>
        )}

        {/* ── Tab 2: Content ── */}
        {tab === 'Content' && (
          <div className="space-y-5 max-w-3xl">
            {/* AI draft panel */}
            <div className="card space-y-3 border-accent-yellow/20">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-accent-yellow" />
                <h2 className="text-sm font-semibold text-text-primary">AI Draft Generator</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs text-text-muted mb-1">Product / context</label>
                  <textarea
                    rows={2}
                    value={aiContext}
                    onChange={(e) => setAiContext(e.target.value)}
                    placeholder="PriceONN.com — B2B price comparison tool for e-commerce managers and traders"
                    className="input w-full text-sm resize-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1">Tone</label>
                  <select value={aiTone} onChange={(e) => setAiTone(e.target.value)} className="input w-full text-sm">
                    <option value="professional">Professional</option>
                    <option value="friendly">Friendly</option>
                    <option value="formal">Formal</option>
                    <option value="concise">Concise</option>
                  </select>
                </div>
              </div>
              {aiError && <p className="text-xs text-accent-red">{aiError}</p>}
              <button
                className="btn-secondary flex items-center gap-2 text-sm"
                onClick={() => { void handleAIDraft() }}
                disabled={aiLoading || !aiContext.trim()}
              >
                {aiLoading ? <Loader className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {aiLoading ? 'Generating…' : 'Generate Draft'}
              </button>
            </div>

            {/* Subject */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs text-text-muted">Subject line (A)</label>
                <label className="flex items-center gap-1.5 text-xs text-text-muted cursor-pointer">
                  <input
                    type="checkbox"
                    checked={abEnabled}
                    onChange={(e) => setAbEnabled(e.target.checked)}
                    className="accent-accent-yellow"
                  />
                  A/B test
                </label>
              </div>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Your email subject…"
                className="input w-full text-sm"
              />
              {abEnabled && (
                <>
                  <label className="text-xs text-text-muted">Subject line (B)</label>
                  <input
                    type="text"
                    value={subjectB}
                    onChange={(e) => setSubjectB(e.target.value)}
                    placeholder="Alternative subject…"
                    className="input w-full text-sm"
                  />
                </>
              )}
            </div>

            {/* Rich editor */}
            <div>
              <label className="block text-xs text-text-muted mb-1.5">Email body</label>
              <RichEditor
                html={bodyHtml}
                onChange={(html, text) => { setBodyHtml(html); setBodyText(text) }}
              />
            </div>

            {/* LLM + SMTP selectors */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-text-muted mb-1">LLM Provider</label>
                <select value={llmId} onChange={(e) => setLlmId(e.target.value)} className="input w-full text-sm">
                  <option value="">— None —</option>
                  {llmConfigs.map((l) => (
                    <option key={l.id} value={l.id}>{l.display_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">SMTP Account</label>
                <select value={smtpId} onChange={(e) => setSmtpId(e.target.value)} className="input w-full text-sm">
                  <option value="">— Select SMTP —</option>
                  {smtpConfigs.map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.from_email})</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* ── Tab 3: Preview ── */}
        {tab === 'Preview' && (
          <div className="space-y-4 max-w-3xl">
            <div className="card">
              <div className="text-xs text-text-muted mb-1">Subject</div>
              <div className="text-sm font-medium text-text-primary mb-3">
                {subject || <span className="text-text-muted italic">No subject</span>}
              </div>
              {abEnabled && subjectB && (
                <div className="text-xs text-text-muted mb-3">
                  B variant: <span className="text-text-secondary">{subjectB}</span>
                </div>
              )}
              <div className="border-t border-border pt-3">
                <div className="text-xs text-text-muted mb-2">Preview (sample variables applied)</div>
                <div
                  className="prose prose-invert prose-sm max-w-none text-text-primary"
                  dangerouslySetInnerHTML={{
                    __html: (bodyHtml || '<p class="text-text-muted italic">No body content yet.</p>')
                      .replace(/\{\{first_name\}\}/g, 'Alex')
                      .replace(/\{\{company\}\}/g, 'Acme Corp')
                      .replace(/\{\{email\}\}/g, 'alex@acme.com')
                      .replace(/\{\{unsubscribe_url\}\}/g, '#unsubscribe'),
                  }}
                />
              </div>
            </div>
            <div className="card">
              <div className="text-xs text-text-muted mb-1">Plain text version</div>
              <pre className="text-xs text-text-secondary whitespace-pre-wrap font-mono leading-relaxed">
                {bodyText || 'No plain text content.'}
              </pre>
            </div>
          </div>
        )}

        {/* ── Tab 4: Schedule ── */}
        {tab === 'Schedule' && (
          <div className="space-y-5 max-w-lg">
            <div className="card space-y-4">
              <h2 className="text-sm font-semibold text-text-primary">Send Timing</h2>
              <div className="space-y-2">
                {(['now', 'scheduled', 'batched'] as const).map((mode) => (
                  <label key={mode} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="radio"
                      name="schedule"
                      value={mode}
                      checked={scheduleMode === mode}
                      onChange={() => setScheduleMode(mode)}
                      className="accent-accent-yellow"
                    />
                    <span className="text-text-primary">
                      {mode === 'now' && 'Send immediately after approval'}
                      {mode === 'scheduled' && 'Schedule for a specific time'}
                      {mode === 'batched' && 'Batched sending (rate-limited)'}
                    </span>
                  </label>
                ))}
              </div>

              {scheduleMode === 'scheduled' && (
                <div>
                  <label className="block text-xs text-text-muted mb-1">Send at</label>
                  <input
                    type="datetime-local"
                    value={scheduledAt}
                    onChange={(e) => setScheduledAt(e.target.value)}
                    className="input w-full text-sm"
                  />
                </div>
              )}

              {scheduleMode === 'batched' && (
                <div>
                  <label className="block text-xs text-text-muted mb-1">
                    Emails per hour: {batchSize}
                  </label>
                  <input
                    type="range" min={1} max={200} value={batchSize}
                    onChange={(e) => setBatchSize(Number(e.target.value))}
                    className="w-full accent-accent-yellow"
                  />
                  <div className="flex justify-between text-xs text-text-muted">
                    <span>1/hr</span>
                    <span>200/hr</span>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs text-text-muted mb-1">
                  Hourly send limit (0 = unlimited, default 50)
                </label>
                <input
                  type="number"
                  min={0}
                  max={9999}
                  value={hourlyLimit}
                  onChange={(e) => setHourlyLimit(Number(e.target.value))}
                  className="input w-32 text-sm"
                />
              </div>
            </div>
          </div>
        )}

        {/* ── Tab 5: Send ── */}
        {tab === 'Send' && (
          <div className="space-y-5 max-w-lg">
            {/* Spam score */}
            <div className="card space-y-3">
              <h2 className="text-sm font-semibold text-text-primary">Spam Score</h2>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-bg-tertiary rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      score < 25 ? 'bg-accent-green' : score < 55 ? 'bg-accent-yellow' : 'bg-accent-red'
                    }`}
                    style={{ width: `${score}%` }}
                  />
                </div>
                <span className={`text-sm font-mono font-semibold ${scoreColor}`}>{score}/100</span>
              </div>
              <p className={`text-xs ${scoreColor}`}>
                {score < 25
                  ? 'Good — low spam risk'
                  : score < 55
                  ? 'Moderate — review highlighted words'
                  : 'High — please revise content before sending'}
              </p>
            </div>

            {/* SMTP summary */}
            <div className="card space-y-2">
              <h2 className="text-sm font-semibold text-text-primary">Sending Account</h2>
              {smtpId ? (
                <div className="text-sm text-text-secondary">
                  {smtpConfigs.find((s) => s.id === smtpId)?.name ?? smtpId}
                  {' — '}
                  {smtpConfigs.find((s) => s.id === smtpId)?.from_email}
                </div>
              ) : (
                <div className="text-xs text-accent-red flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  No SMTP account selected. Go to Content tab.
                </div>
              )}
            </div>

            {/* Checklist */}
            <div className="card space-y-2">
              <h2 className="text-sm font-semibold text-text-primary">Pre-send Checklist</h2>
              {[
                { label: 'Subject line set', ok: !!subject },
                { label: 'Email body written', ok: !!bodyHtml },
                { label: 'SMTP account selected', ok: !!smtpId },
                { label: 'Spam score < 55', ok: score < 55 },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2 text-sm">
                  {item.ok
                    ? <CheckCircle className="w-4 h-4 text-accent-green" />
                    : <AlertTriangle className="w-4 h-4 text-accent-yellow" />}
                  <span className={item.ok ? 'text-text-primary' : 'text-text-muted'}>{item.label}</span>
                </div>
              ))}
            </div>

            {/* Test send */}
            <div className="card space-y-2">
              <h2 className="text-sm font-semibold text-text-primary">Test Send</h2>
              <p className="text-xs text-text-muted">Send a test email to your account: {user?.email}</p>
              {testSuccess && (
                <p className="text-xs text-accent-green">Test email sent!</p>
              )}
              <button
                className="btn-secondary flex items-center gap-2 text-sm"
                onClick={() => { void handleTestSend() }}
                disabled={testSending || !smtpId || !savedId}
              >
                {testSending ? <Loader className="w-4 h-4 animate-spin" /> : <SendHorizonal className="w-4 h-4" />}
                {testSending ? 'Sending…' : 'Send Test'}
              </button>
              {!savedId && (
                <p className="text-xs text-text-muted">Save draft first to enable test send.</p>
              )}
            </div>

            {/* Send button */}
            <button
              className="btn-primary w-full flex items-center justify-center gap-2 py-3"
              onClick={() => setShowLIA(true)}
              disabled={!subject || !bodyHtml || !smtpId}
            >
              <SendHorizonal className="w-4 h-4" />
              Send Campaign
            </button>
          </div>
        )}
      </div>

      {/* LIA Modal */}
      {showLIA && (
        <LIAModal
          reason={liaReason}
          onChange={setLiaReason}
          onConfirm={() => { void handleSend() }}
          onClose={() => setShowLIA(false)}
          sending={sending}
        />
      )}
    </div>
  )
}
