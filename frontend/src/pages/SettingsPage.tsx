import { useEffect, useRef, useState } from 'react'
import {
  Bot,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Copy,
  KeyRound,
  Mail,
  Plus,
  QrCode,
  RefreshCw,
  Server,
  Shield,
  ShieldCheck,
  Trash2,
  Webhook,
  XCircle,
  Zap,
} from 'lucide-react'
import clsx from 'clsx'
import {
  audienceTypesApi,
  authApi,
  llmApi,
  smtpApi,
  type AudienceCategory,
  type LLMConfig,
  type LLMConfigCreate,
  type SMTPConfig,
  type SMTPConfigCreate,
  type TOTPSetupResponse,
} from '../lib/api'

// ── Shared ───────────────────────────────────────────────────────────────────

type Tab = 'llm' | 'smtp' | 'audience' | 'compliance' | 'security' | 'general' | 'webhooks'

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'llm', label: 'LLM Providers', icon: Bot },
  { id: 'smtp', label: 'SMTP', icon: Mail },
  { id: 'audience', label: 'Audience Types', icon: Zap },
  { id: 'compliance', label: 'Compliance', icon: Shield },
  { id: 'security', label: 'Security', icon: ShieldCheck },
  { id: 'general', label: 'General', icon: Server },
  { id: 'webhooks', label: 'Webhooks', icon: Webhook },
]

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card space-y-4">
      <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
      {children}
    </div>
  )
}

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={clsx('inline-flex items-center gap-1 text-xs', ok ? 'text-accent-green' : 'text-text-muted')}>
      {ok ? <CheckCircle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
      {label}
    </span>
  )
}

// ── LLM Tab ───────────────────────────────────────────────────────────────────

const LLM_PROVIDERS = ['openrouter', 'openai', 'anthropic', 'groq', 'zai', 'custom']

function LLMTab() {
  const [configs, setConfigs] = useState<LLMConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; msg: string }>>({})
  const [form, setForm] = useState<LLMConfigCreate>({
    provider: 'openrouter',
    model_name: '',
    api_key: '',
    base_url: null,
    purpose: 'default',
    is_default: false,
    display_name: null,
  })
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await llmApi.list()
      setConfigs(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const handleCreate = async () => {
    if (!form.model_name || !form.api_key) { setErr('Model name and API key required.'); return }
    setSaving(true); setErr('')
    try {
      await llmApi.create(form)
      setShowAdd(false)
      setForm({ provider: 'openrouter', model_name: '', api_key: '', base_url: null, purpose: 'default', is_default: false, display_name: null })
      await load()
    } catch {
      setErr('Failed to save LLM config.')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this LLM config?')) return
    await llmApi.delete(id)
    await load()
  }

  const handleSetDefault = async (id: string) => {
    await llmApi.setDefault(id)
    await load()
  }

  const handleTest = async (id: string) => {
    setTesting(id)
    try {
      const { data } = await llmApi.test(id)
      setTestResults((r) => ({ ...r, [id]: { ok: data.success, msg: data.success ? (data.content ?? 'OK') : (data.error ?? 'Failed') } }))
    } catch {
      setTestResults((r) => ({ ...r, [id]: { ok: false, msg: 'Request error' } }))
    } finally {
      setTesting(null)
    }
  }

  if (loading) return <p className="text-sm text-text-muted">Loading…</p>

  return (
    <div className="space-y-4">
      <SectionCard title="LLM Providers">
        {configs.length === 0 ? (
          <p className="text-sm text-text-muted">No LLM configs yet.</p>
        ) : (
          <div className="divide-y divide-border">
            {configs.map((c) => (
              <div key={c.id} className="py-3 flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary">
                      {c.display_name ?? `${c.provider}/${c.model_name}`}
                    </span>
                    {c.is_active && <span className="badge badge-green">default</span>}
                    <span className="badge badge-muted">{c.purpose}</span>
                  </div>
                  <div className="text-xs text-text-muted mt-0.5">{c.provider} · {c.model_name}</div>
                  {testResults[c.id] && (
                    <div className={clsx('text-xs mt-1 truncate max-w-sm', testResults[c.id].ok ? 'text-accent-green' : 'text-accent-red')}>
                      {testResults[c.id].msg}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {!c.is_active && (
                    <button className="btn-secondary text-xs px-2 py-1" onClick={() => void handleSetDefault(c.id)}>
                      Set default
                    </button>
                  )}
                  <button
                    className="btn-secondary text-xs px-2 py-1"
                    disabled={testing === c.id}
                    onClick={() => void handleTest(c.id)}
                  >
                    {testing === c.id ? 'Testing…' : 'Test'}
                  </button>
                  <button className="p-1.5 text-text-muted hover:text-accent-red" onClick={() => void handleDelete(c.id)}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <button className="btn-secondary flex items-center gap-2 text-sm" onClick={() => setShowAdd(!showAdd)}>
          <Plus className="w-4 h-4" />
          Add LLM Provider
        </button>

        {showAdd && (
          <div className="border border-border rounded-lg p-4 space-y-3 bg-bg-card">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-text-muted mb-1">Provider</label>
                <select
                  className="input w-full text-sm"
                  value={form.provider}
                  onChange={(e) => setForm({ ...form, provider: e.target.value })}
                >
                  {LLM_PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Model</label>
                <input
                  className="input w-full text-sm"
                  placeholder="e.g. gpt-4o-mini"
                  value={form.model_name}
                  onChange={(e) => setForm({ ...form, model_name: e.target.value })}
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">API Key</label>
              <input
                type="password"
                className="input w-full text-sm font-mono"
                placeholder="sk-…"
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-text-muted mb-1">Display Name (optional)</label>
                <input
                  className="input w-full text-sm"
                  placeholder="My GPT-4o"
                  value={form.display_name ?? ''}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value || null })}
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Purpose</label>
                <select
                  className="input w-full text-sm"
                  value={form.purpose}
                  onChange={(e) => setForm({ ...form, purpose: e.target.value })}
                >
                  {['default', 'planner', 'extractor', 'draft_writer', 'judge'].map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">Base URL (optional, for custom/OpenRouter)</label>
              <input
                className="input w-full text-sm"
                placeholder="https://openrouter.ai/api/v1"
                value={form.base_url ?? ''}
                onChange={(e) => setForm({ ...form, base_url: e.target.value || null })}
              />
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
              <span className="text-text-secondary">Set as default</span>
            </label>
            {err && <p className="text-xs text-accent-red">{err}</p>}
            <div className="flex gap-2">
              <button className="btn-primary text-sm" onClick={() => void handleCreate()} disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button className="btn-secondary text-sm" onClick={() => { setShowAdd(false); setErr('') }}>Cancel</button>
            </div>
          </div>
        )}
      </SectionCard>
    </div>
  )
}

// ── SMTP Tab ──────────────────────────────────────────────────────────────────

function SMTPTab() {
  const [configs, setConfigs] = useState<SMTPConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)
  const [testEmail, setTestEmail] = useState('')
  const [testTarget, setTestTarget] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; msg: string }>>({})
  const [form, setForm] = useState<SMTPConfigCreate>({
    name: '',
    host: '',
    port: 587,
    username: '',
    password: '',
    use_tls: true,
    from_email: '',
    from_name: 'PriceONN Outreach',
    daily_send_limit: 500,
    is_default: false,
  })
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await smtpApi.list()
      setConfigs(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const handleCreate = async () => {
    if (!form.name || !form.host || !form.username || !form.password || !form.from_email) {
      setErr('All required fields must be filled.'); return
    }
    setSaving(true); setErr('')
    try {
      await smtpApi.create(form)
      setShowAdd(false)
      setForm({ name: '', host: '', port: 587, username: '', password: '', use_tls: true, from_email: '', from_name: 'PriceONN Outreach', daily_send_limit: 500, is_default: false })
      await load()
    } catch {
      setErr('Failed to save SMTP config.')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this SMTP config?')) return
    await smtpApi.delete(id)
    await load()
  }

  const handleSetDefault = async (id: string) => {
    await smtpApi.setDefault(id)
    await load()
  }

  const handleTest = async (id: string) => {
    if (!testEmail) { alert('Enter a test email address first.'); return }
    setTesting(id); setTestTarget(id)
    try {
      const { data } = await smtpApi.test(id, testEmail)
      setTestResults((r) => ({ ...r, [id]: { ok: data.success, msg: data.success ? 'Delivered successfully' : (data.error ?? 'Failed') } }))
    } catch {
      setTestResults((r) => ({ ...r, [id]: { ok: false, msg: 'Request error' } }))
    } finally {
      setTesting(null)
    }
  }

  if (loading) return <p className="text-sm text-text-muted">Loading…</p>

  return (
    <div className="space-y-4">
      <SectionCard title="SMTP Accounts">
        <div className="flex items-center gap-2 mb-2">
          <label className="text-xs text-text-muted shrink-0">Test email:</label>
          <input
            className="input text-sm flex-1 max-w-xs"
            placeholder="you@example.com"
            value={testEmail}
            onChange={(e) => setTestEmail(e.target.value)}
          />
        </div>

        {configs.length === 0 ? (
          <p className="text-sm text-text-muted">No SMTP configs yet.</p>
        ) : (
          <div className="divide-y divide-border">
            {configs.map((c) => (
              <div key={c.id} className="py-3 flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary">{c.name}</span>
                    {c.is_default && <span className="badge badge-green">default</span>}
                  </div>
                  <div className="text-xs text-text-muted mt-0.5">
                    {c.from_email} · {c.host}:{c.port} · limit {c.daily_send_limit}/day
                  </div>
                  {testResults[c.id] && testTarget === c.id && (
                    <div className={clsx('text-xs mt-1', testResults[c.id].ok ? 'text-accent-green' : 'text-accent-red')}>
                      {testResults[c.id].msg}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {!c.is_default && (
                    <button className="btn-secondary text-xs px-2 py-1" onClick={() => void handleSetDefault(c.id)}>
                      Set default
                    </button>
                  )}
                  <button
                    className="btn-secondary text-xs px-2 py-1"
                    disabled={testing === c.id}
                    onClick={() => void handleTest(c.id)}
                  >
                    {testing === c.id ? 'Sending…' : 'Test send'}
                  </button>
                  <button className="p-1.5 text-text-muted hover:text-accent-red" onClick={() => void handleDelete(c.id)}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        <button className="btn-secondary flex items-center gap-2 text-sm" onClick={() => setShowAdd(!showAdd)}>
          <Plus className="w-4 h-4" />
          Add SMTP Account
        </button>

        {showAdd && (
          <div className="border border-border rounded-lg p-4 space-y-3 bg-bg-card">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="block text-xs text-text-muted mb-1">Display Name</label>
                <input className="input w-full text-sm" placeholder="Mailgun Production" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">SMTP Host</label>
                <input className="input w-full text-sm" placeholder="smtp.mailgun.org" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Port</label>
                <input type="number" className="input w-full text-sm" value={form.port} onChange={(e) => setForm({ ...form, port: Number(e.target.value) })} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Username</label>
                <input className="input w-full text-sm" placeholder="postmaster@mg.domain.com" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Password</label>
                <input type="password" className="input w-full text-sm" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">From Email</label>
                <input className="input w-full text-sm" placeholder="outreach@domain.com" value={form.from_email} onChange={(e) => setForm({ ...form, from_email: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">From Name</label>
                <input className="input w-full text-sm" value={form.from_name} onChange={(e) => setForm({ ...form, from_name: e.target.value })} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Daily Send Limit</label>
                <input type="number" className="input w-full text-sm" value={form.daily_send_limit} onChange={(e) => setForm({ ...form, daily_send_limit: Number(e.target.value) })} />
              </div>
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.use_tls} onChange={(e) => setForm({ ...form, use_tls: e.target.checked })} />
                <span className="text-text-secondary">Use TLS</span>
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />
                <span className="text-text-secondary">Set as default</span>
              </label>
            </div>
            {err && <p className="text-xs text-accent-red">{err}</p>}
            <div className="flex gap-2">
              <button className="btn-primary text-sm" onClick={() => void handleCreate()} disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button className="btn-secondary text-sm" onClick={() => { setShowAdd(false); setErr('') }}>Cancel</button>
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard title="DNS / Deliverability Checklist">
        <ul className="space-y-1.5 text-xs text-text-secondary">
          <li className="flex items-center gap-2"><StatusPill ok={false} label="SPF record" /> — Add TXT record: <code className="text-accent-yellow ml-1">v=spf1 include:mailgun.org ~all</code></li>
          <li className="flex items-center gap-2"><StatusPill ok={false} label="DKIM record" /> — Enable in your ESP dashboard and add CNAME</li>
          <li className="flex items-center gap-2"><StatusPill ok={false} label="DMARC record" /> — Add TXT record: <code className="text-accent-yellow ml-1">v=DMARC1; p=quarantine; rua=mailto:dmarc@domain.com</code></li>
          <li className="flex items-center gap-2"><StatusPill ok={false} label="Warm-up" /> — Start at 50/day, double weekly for 4 weeks</li>
        </ul>
        <p className="text-xs text-text-muted mt-2">DNS propagation can take up to 48 hours. Use MXToolbox to verify.</p>
      </SectionCard>
    </div>
  )
}

// ── Audience Types Tab ────────────────────────────────────────────────────────

function AudienceTab() {
  const [categories, setCategories] = useState<AudienceCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await audienceTypesApi.list()
      setCategories(data.categories)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const handleToggle = async (key: string, current: boolean) => {
    setToggling(key)
    try {
      await audienceTypesApi.setEnabled(key, !current)
      setCategories((cats) =>
        cats.map((cat) => ({
          ...cat,
          types: cat.types.map((t) => t.key === key ? { ...t, is_enabled_default: !current } : t),
        }))
      )
    } finally {
      setToggling(null)
    }
  }

  const toggleCat = (name: string) => setCollapsed((c) => ({ ...c, [name]: !c[name] }))

  if (loading) return <p className="text-sm text-text-muted">Loading…</p>

  const total = categories.reduce((s, c) => s + c.types.length, 0)
  const enabled = categories.reduce((s, c) => s + c.types.filter((t) => t.is_enabled_default).length, 0)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-text-muted">{enabled}/{total} types enabled</p>
        <button className="p-1.5 text-text-muted hover:text-text-primary" onClick={() => void load()}>
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {categories.map((cat) => {
        const isCollapsed = collapsed[cat.name]
        const catEnabled = cat.types.filter((t) => t.is_enabled_default).length
        return (
          <div key={cat.name} className="card">
            <button
              className="w-full flex items-center justify-between text-left"
              onClick={() => toggleCat(cat.name)}
            >
              <span className="text-sm font-semibold text-text-primary capitalize">{cat.name.replace('_', ' ')}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted">{catEnabled}/{cat.types.length}</span>
                {isCollapsed ? <ChevronRight className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
              </div>
            </button>

            {!isCollapsed && (
              <div className="mt-3 divide-y divide-border">
                {cat.types.map((t) => (
                  <div key={t.key} className="py-2 flex items-center justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-text-primary">{t.label_en}</div>
                      {t.description && <div className="text-xs text-text-muted truncate">{t.description}</div>}
                      <div className="text-xs text-text-muted">{t.contact_count.toLocaleString()} contacts</div>
                    </div>
                    <button
                      disabled={toggling === t.key}
                      onClick={() => void handleToggle(t.key, t.is_enabled_default)}
                      className={clsx(
                        'w-10 h-5 rounded-full transition-colors relative shrink-0',
                        t.is_enabled_default ? 'bg-accent-yellow' : 'bg-bg-hover',
                        toggling === t.key && 'opacity-50',
                      )}
                    >
                      <span className={clsx(
                        'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform',
                        t.is_enabled_default ? 'translate-x-5' : 'translate-x-0.5',
                      )} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Compliance Tab ────────────────────────────────────────────────────────────

interface ComplianceForm {
  company_name: string
  company_address: string
  privacy_policy_url: string
  lia_template: string
  email_footer: string
  gdpr_enabled: boolean
  casl_enabled: boolean
  can_spam_enabled: boolean
}

const DEFAULT_COMPLIANCE: ComplianceForm = {
  company_name: 'PriceONN',
  company_address: '',
  privacy_policy_url: '',
  lia_template: 'We process your data under Legitimate Interest (GDPR Art. 6(1)(f)) to provide relevant financial tools and services. You can object at any time.',
  email_footer: '© PriceONN · {{company_address}} · <a href="{{unsubscribe_url}}">Unsubscribe</a> · <a href="{{privacy_url}}">Privacy Policy</a>',
  gdpr_enabled: true,
  casl_enabled: false,
  can_spam_enabled: true,
}

function ComplianceTab() {
  const [form, setForm] = useState<ComplianceForm>(() => {
    try {
      const saved = localStorage.getItem('xmail_compliance')
      return saved ? (JSON.parse(saved) as ComplianceForm) : DEFAULT_COMPLIANCE
    } catch {
      return DEFAULT_COMPLIANCE
    }
  })
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    localStorage.setItem('xmail_compliance', JSON.stringify(form))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const field = (label: string, key: keyof ComplianceForm, multiline = false, placeholder = '') => (
    <div>
      <label className="block text-xs text-text-muted mb-1">{label}</label>
      {multiline ? (
        <textarea
          className="input w-full text-sm font-mono resize-y"
          rows={3}
          placeholder={placeholder}
          value={form[key] as string}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        />
      ) : (
        <input
          className="input w-full text-sm"
          placeholder={placeholder}
          value={form[key] as string}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        />
      )}
    </div>
  )

  const toggle = (label: string, key: keyof ComplianceForm, description: string) => (
    <label className="flex items-start gap-3 cursor-pointer">
      <input
        type="checkbox"
        className="mt-0.5"
        checked={form[key] as boolean}
        onChange={(e) => setForm({ ...form, [key]: e.target.checked })}
      />
      <div>
        <div className="text-sm text-text-primary">{label}</div>
        <div className="text-xs text-text-muted">{description}</div>
      </div>
    </label>
  )

  return (
    <div className="space-y-4">
      <SectionCard title="Company Information">
        <div className="grid grid-cols-2 gap-3">
          {field('Company Name', 'company_name', false, 'PriceONN')}
          {field('Privacy Policy URL', 'privacy_policy_url', false, 'https://priceonn.com/privacy')}
        </div>
        {field('Company Address (for CAN-SPAM footer)', 'company_address', false, '123 Main St, City, State, ZIP')}
      </SectionCard>

      <SectionCard title="Legitimate Interest Assessment (LIA) Template">
        <p className="text-xs text-text-muted">This template is shown to users before sending campaigns. Minimum 20 characters.</p>
        {field('LIA Statement', 'lia_template', true)}
      </SectionCard>

      <SectionCard title="Email Footer Template">
        <p className="text-xs text-text-muted mb-1">
          Available variables: <code className="text-accent-yellow">{'{{unsubscribe_url}}'}</code>, <code className="text-accent-yellow">{'{{company_address}}'}</code>, <code className="text-accent-yellow">{'{{privacy_url}}'}</code>
        </p>
        {field('Footer HTML', 'email_footer', true)}
      </SectionCard>

      <SectionCard title="Applicable Regulations">
        <div className="space-y-3">
          {toggle('GDPR (EU)', 'gdpr_enabled', 'European General Data Protection Regulation — requires lawful basis, right to erasure, data minimization.')}
          {toggle('CASL (Canada)', 'casl_enabled', 'Canadian Anti-Spam Legislation — requires express or implied consent for commercial email.')}
          {toggle('CAN-SPAM (USA)', 'can_spam_enabled', 'US law requiring physical address, clear opt-out mechanism, and honest subject lines.')}
        </div>
      </SectionCard>

      <button className="btn-primary text-sm" onClick={handleSave}>
        {saved ? 'Saved ✓' : 'Save Compliance Settings'}
      </button>
      <p className="text-xs text-text-muted">Settings are stored locally. Backend compliance endpoint coming in Phase 22.</p>
    </div>
  )
}

// ── Security Tab ─────────────────────────────────────────────────────────────

function SecurityTab() {
  // Password change
  const [pwCurrent, setPwCurrent] = useState('')
  const [pwNew, setPwNew] = useState('')
  const [pwConfirm, setPwConfirm] = useState('')
  const [pwLoading, setPwLoading] = useState(false)
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null)

  // TOTP state: idle | setup | confirming | enabled | disabling
  const [totpPhase, setTotpPhase] = useState<'idle' | 'setup' | 'confirming' | 'enabled' | 'disabling'>('idle')
  const [totpSetup, setTotpSetup] = useState<TOTPSetupResponse | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const [totpLoading, setTotpLoading] = useState(false)
  const [totpMsg, setTotpMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const codeRef = useRef<HTMLInputElement>(null)

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    if (pwNew !== pwConfirm) {
      setPwMsg({ ok: false, text: 'New passwords do not match.' })
      return
    }
    setPwLoading(true)
    setPwMsg(null)
    try {
      await authApi.changePassword(pwCurrent, pwNew)
      setPwMsg({ ok: true, text: 'Password updated successfully.' })
      setPwCurrent(''); setPwNew(''); setPwConfirm('')
    } catch {
      setPwMsg({ ok: false, text: 'Current password is incorrect or request failed.' })
    } finally {
      setPwLoading(false)
    }
  }

  const startTOTPSetup = async () => {
    setTotpLoading(true)
    setTotpMsg(null)
    try {
      const res = await authApi.totpSetup()
      setTotpSetup(res.data)
      setTotpPhase('setup')
      setTimeout(() => codeRef.current?.focus(), 50)
    } catch {
      setTotpMsg({ ok: false, text: 'Failed to start TOTP setup.' })
    } finally {
      setTotpLoading(false)
    }
  }

  const confirmTOTP = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!totpSetup) return
    setTotpLoading(true)
    setTotpMsg(null)
    try {
      await authApi.totpConfirm(totpSetup.secret, totpCode)
      setTotpMsg({ ok: true, text: '2FA enabled. Save your authenticator now.' })
      setTotpPhase('enabled')
      setTotpCode('')
    } catch {
      setTotpMsg({ ok: false, text: 'Invalid code. Try again.' })
      setTotpCode('')
      codeRef.current?.focus()
    } finally {
      setTotpLoading(false)
    }
  }

  const disableTOTP = async (e: React.FormEvent) => {
    e.preventDefault()
    setTotpLoading(true)
    setTotpMsg(null)
    try {
      await authApi.totpDisable('', totpCode)
      setTotpMsg({ ok: true, text: '2FA disabled.' })
      setTotpPhase('idle')
      setTotpSetup(null)
      setTotpCode('')
    } catch {
      setTotpMsg({ ok: false, text: 'Invalid code. Try again.' })
      setTotpCode('')
      codeRef.current?.focus()
    } finally {
      setTotpLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Password */}
      <SectionCard title="Change Password">
        <form onSubmit={(e) => { void handlePasswordChange(e) }} className="space-y-3">
          <div>
            <label className="block text-xs text-text-secondary mb-1.5">Current Password</label>
            <input type="password" className="input" value={pwCurrent}
              onChange={(e) => setPwCurrent(e.target.value)} required />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1.5">New Password</label>
            <input type="password" className="input" value={pwNew}
              onChange={(e) => setPwNew(e.target.value)} required minLength={8} />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1.5">Confirm New Password</label>
            <input type="password" className="input" value={pwConfirm}
              onChange={(e) => setPwConfirm(e.target.value)} required />
          </div>
          {pwMsg && (
            <p className={clsx('text-xs px-3 py-2 rounded border',
              pwMsg.ok
                ? 'text-accent-green bg-green-900/20 border-green-800/30'
                : 'text-accent-red bg-red-900/20 border-red-800/30')}>
              {pwMsg.text}
            </p>
          )}
          <button type="submit" className="btn-primary" disabled={pwLoading}>
            <KeyRound className="w-4 h-4" />
            {pwLoading ? 'Updating…' : 'Update Password'}
          </button>
        </form>
      </SectionCard>

      {/* TOTP */}
      <SectionCard title="Two-Factor Authentication (TOTP)">
        {totpPhase === 'idle' && (
          <div className="space-y-3">
            <p className="text-xs text-text-secondary">
              Use an authenticator app (Google Authenticator, Authy) for an extra layer of security.
            </p>
            {totpMsg && (
              <p className={clsx('text-xs px-3 py-2 rounded border',
                totpMsg.ok
                  ? 'text-accent-green bg-green-900/20 border-green-800/30'
                  : 'text-accent-red bg-red-900/20 border-red-800/30')}>
                {totpMsg.text}
              </p>
            )}
            <button className="btn-secondary flex items-center gap-2" onClick={() => { void startTOTPSetup() }} disabled={totpLoading}>
              <QrCode className="w-4 h-4" />
              {totpLoading ? 'Loading…' : 'Set Up 2FA'}
            </button>
          </div>
        )}

        {totpPhase === 'setup' && totpSetup && (
          <div className="space-y-4">
            <p className="text-xs text-text-secondary">
              Scan this QR code with your authenticator app, then enter the 6-digit code to confirm.
            </p>
            <img src={totpSetup.qr_data_url} alt="TOTP QR code" className="w-40 h-40 border border-border rounded" />
            <p className="text-xs text-text-muted font-mono break-all">{totpSetup.secret}</p>
            <form onSubmit={(e) => { void confirmTOTP(e) }} className="space-y-3">
              <input ref={codeRef} type="text" inputMode="numeric" pattern="[0-9]{6}" maxLength={6}
                className="input text-center text-xl font-mono tracking-widest w-40"
                value={totpCode} onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                placeholder="000000" required autoComplete="one-time-code" />
              {totpMsg && (
                <p className="text-xs text-accent-red bg-red-900/20 border border-red-800/30 rounded px-3 py-2">
                  {totpMsg.text}
                </p>
              )}
              <div className="flex gap-2">
                <button type="submit" className="btn-primary" disabled={totpLoading || totpCode.length !== 6}>
                  {totpLoading ? 'Verifying…' : 'Confirm & Enable'}
                </button>
                <button type="button" className="btn-secondary"
                  onClick={() => { setTotpPhase('idle'); setTotpSetup(null); setTotpCode(''); setTotpMsg(null) }}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {totpPhase === 'enabled' && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-accent-green text-sm">
              <CheckCircle className="w-4 h-4" />
              Two-factor authentication is <strong>enabled</strong>.
            </div>
            {totpMsg && (
              <p className={clsx('text-xs px-3 py-2 rounded border',
                totpMsg.ok
                  ? 'text-accent-green bg-green-900/20 border-green-800/30'
                  : 'text-accent-red bg-red-900/20 border-red-800/30')}>
                {totpMsg.text}
              </p>
            )}
            <button className="btn-secondary flex items-center gap-2 text-accent-red border-accent-red"
              onClick={() => { setTotpPhase('disabling'); setTotpMsg(null) }}>
              <XCircle className="w-4 h-4" />
              Disable 2FA
            </button>
          </div>
        )}

        {totpPhase === 'disabling' && (
          <div className="space-y-3">
            <p className="text-xs text-text-secondary">Enter your authenticator code to disable 2FA.</p>
            <form onSubmit={(e) => { void disableTOTP(e) }} className="space-y-3">
              <input ref={codeRef} type="text" inputMode="numeric" pattern="[0-9]{6}" maxLength={6}
                className="input text-center text-xl font-mono tracking-widest w-40"
                value={totpCode} onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                placeholder="000000" required autoComplete="one-time-code" />
              {totpMsg && (
                <p className="text-xs text-accent-red bg-red-900/20 border border-red-800/30 rounded px-3 py-2">
                  {totpMsg.text}
                </p>
              )}
              <div className="flex gap-2">
                <button type="submit" className="btn-primary bg-accent-red border-accent-red"
                  disabled={totpLoading || totpCode.length !== 6}>
                  {totpLoading ? 'Disabling…' : 'Disable 2FA'}
                </button>
                <button type="button" className="btn-secondary"
                  onClick={() => { setTotpPhase('enabled'); setTotpCode(''); setTotpMsg(null) }}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}
      </SectionCard>
    </div>
  )
}

// ── General Tab ───────────────────────────────────────────────────────────────

function GeneralTab() {
  return (
    <div className="space-y-4">
      <SectionCard title="Application Info">
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-text-muted">Version</span>
            <span className="text-text-primary font-mono">v1.0.0-beta</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Product</span>
            <span className="text-text-primary">Xmail — Agentic Email Outreach</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Built for</span>
            <span className="text-text-primary">PriceONN.com</span>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Upcoming Features">
        <ul className="space-y-1.5 text-xs text-text-secondary list-disc list-inside">
          <li>Phase 21 — Suppression list management &amp; audit logs</li>
          <li>Phase 22 — Security hardening (2FA, rate limiting, CSP)</li>
          <li>Phase 23 — Prometheus metrics &amp; Grafana dashboard</li>
          <li>Phase 24 — Test suite (pytest + Vitest + Playwright E2E)</li>
          <li>Phase 25 — Production deployment (Docker + Traefik + SSL)</li>
        </ul>
      </SectionCard>

      <SectionCard title="Danger Zone">
        <p className="text-xs text-text-muted mb-3">
          These actions are irreversible. Proceed only if you understand the consequences.
        </p>
        <div className="space-y-2">
          <button className="btn-secondary text-sm text-accent-red border-accent-red hover:bg-accent-red hover:text-bg-primary" disabled>
            Purge All Suppressed Contacts — coming Phase 21
          </button>
          <button className="btn-secondary text-sm text-accent-red border-accent-red hover:bg-accent-red hover:text-bg-primary" disabled>
            Delete All Draft Campaigns — coming Phase 21
          </button>
        </div>
      </SectionCard>
    </div>
  )
}

// ── Webhooks tab ─────────────────────────────────────────────────────────────

const WEBHOOK_PROVIDERS = [
  {
    id: 'sendgrid',
    name: 'SendGrid',
    path: '/api/webhooks/sendgrid',
    events: 'bounce, open, click, unsubscribe, spam_report',
    note: 'Use Event Webhook in SendGrid dashboard. Paste the public key from SendGrid into SENDGRID_WEBHOOK_PUBLIC_KEY env var.',
  },
  {
    id: 'postmark',
    name: 'Postmark',
    path: '/api/webhooks/postmark',
    events: 'bounce, open, click, subscription',
    note: 'Set a shared secret in Postmark → Servers → Webhooks and copy it to POSTMARK_WEBHOOK_TOKEN env var.',
  },
  {
    id: 'mailgun',
    name: 'Mailgun',
    path: '/api/webhooks/mailgun',
    events: 'bounce (failed), open, click, unsubscribe, complaint',
    note: 'Copy your HTTP webhook signing key from Mailgun → Sending → Webhooks to MAILGUN_WEBHOOK_SIGNING_KEY env var.',
  },
]

function WebhooksTab() {
  const [copied, setCopied] = useState<string | null>(null)

  const copy = (text: string, id: string) => {
    void navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  const baseUrl = window.location.origin

  return (
    <SectionCard title="Webhook Endpoints">
      <p className="text-xs text-text-muted">
        Point your email provider's webhook to the URL below. Xmail validates signatures using the
        corresponding env var — leave it blank during local development to skip verification.
      </p>
      <div className="space-y-4 mt-2">
        {WEBHOOK_PROVIDERS.map(({ id, name, path, events, note }) => {
          const url = `${baseUrl}${path}`
          return (
            <div key={id} className="border border-border rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-text-primary">{name}</span>
                <span className="text-xs text-text-muted font-mono">{events}</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={url}
                  className="input flex-1 text-xs font-mono bg-bg-tertiary"
                />
                <button
                  className="btn-secondary flex items-center gap-1 px-2 py-1.5 text-xs"
                  onClick={() => copy(url, id)}
                >
                  <Copy className="w-3.5 h-3.5" />
                  {copied === id ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <p className="text-xs text-text-muted">{note}</p>
            </div>
          )
        })}
      </div>
    </SectionCard>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>('llm')

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold text-text-primary">Settings</h1>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 transition-colors',
              tab === id
                ? 'border-accent-yellow text-text-primary font-medium'
                : 'border-transparent text-text-secondary hover:text-text-primary',
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      <div className="max-w-3xl">
        {tab === 'llm' && <LLMTab />}
        {tab === 'smtp' && <SMTPTab />}
        {tab === 'audience' && <AudienceTab />}
        {tab === 'compliance' && <ComplianceTab />}
        {tab === 'security' && <SecurityTab />}
        {tab === 'general' && <GeneralTab />}
        {tab === 'webhooks' && <WebhooksTab />}
      </div>
    </div>
  )
}
