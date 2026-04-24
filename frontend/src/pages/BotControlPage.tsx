import { useEffect, useRef, useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  Pause,
  Play,
  RefreshCw,
  Square,
} from 'lucide-react'
import {
  audienceTypesApi,
  botApi,
  botConfigApi,
  llmApi,
  type AgentRun,
  type AudienceCategory,
  type BotConfig,
  type BotStatus,
  type LLMConfig,
} from '../lib/api'

// ── Sub-components ────────────────────────────────────────────────────────────

function RunBadge({ status }: { status: string }) {
  const cls: Record<string, string> = {
    completed: 'badge-green',
    failed: 'badge-red',
    running: 'badge-blue',
    paused: 'badge-yellow',
  }
  return <span className={`badge ${cls[status] ?? 'badge-muted'}`}>{status}</span>
}

function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  description?: string
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <div className="text-sm font-medium text-text-primary">{label}</div>
        {description && (
          <div className="text-xs text-text-muted mt-0.5">{description}</div>
        )}
      </div>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
          checked ? 'bg-accent-yellow' : 'bg-bg-tertiary'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform ${
            checked ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function BotControlPage() {
  const [status, setStatus] = useState<BotStatus | null>(null)
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [config, setConfig] = useState<BotConfig | null>(null)
  const [categories, setCategories] = useState<AudienceCategory[]>([])
  const [llmConfigs, setLlmConfigs] = useState<LLMConfig[]>([])

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [confirm, setConfirm] = useState<'pause' | 'stop' | 'run' | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  const [expandedCats, setExpandedCats] = useState<Record<string, boolean>>({})
  const [excludeDomainsText, setExcludeDomainsText] = useState('')
  const [countriesText, setCountriesText] = useState('')
  const [languagesText, setLanguagesText] = useState('')

  const configRef = useRef<BotConfig | null>(null)
  configRef.current = config

  const load = async () => {
    try {
      const [s, r, cfg, aud, llm] = await Promise.all([
        botApi.status(),
        botApi.runs(),
        botConfigApi.get(),
        audienceTypesApi.list(),
        llmApi.list(),
      ])
      setStatus(s.data)
      setRuns(r.data)
      setConfig(cfg.data)
      setCategories(aud.data.categories)
      setLlmConfigs(llm.data)
      // Expand all categories by default
      const expanded: Record<string, boolean> = {}
      aud.data.categories.forEach((c) => { expanded[c.name] = true })
      setExpandedCats(expanded)
      // Sync text areas
      setExcludeDomainsText(cfg.data.exclude_domains.join('\n'))
      setCountriesText(cfg.data.target_countries.join(', '))
      setLanguagesText(cfg.data.target_languages.join(', '))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const handleAction = async (action: 'pause' | 'stop') => {
    setActionLoading(true)
    try {
      if (action === 'pause') await botApi.pause()
      else await botApi.stop()
      await load()
    } finally {
      setActionLoading(false)
      setConfirm(null)
    }
  }

  const handleRun = async (dryRun: boolean) => {
    setActionLoading(true)
    setRunError(null)
    try {
      await botApi.run(dryRun, 'discovery')
      await load()
    } catch (e: unknown) {
      const msg =
        e instanceof Error ? e.message : 'Failed to start bot'
      setRunError(msg)
    } finally {
      setActionLoading(false)
      setConfirm(null)
    }
  }

  const handleSaveConfig = async () => {
    if (!config) return
    setSaving(true)
    setSaveError(null)
    try {
      const patch: Partial<BotConfig> = {
        ...config,
        exclude_domains: excludeDomainsText
          .split('\n')
          .map((d) => d.trim())
          .filter(Boolean),
        target_countries: countriesText
          .split(',')
          .map((c) => c.trim())
          .filter(Boolean),
        target_languages: languagesText
          .split(',')
          .map((l) => l.trim())
          .filter(Boolean),
      }
      const res = await botConfigApi.update(patch)
      setConfig(res.data)
      setExcludeDomainsText(res.data.exclude_domains.join('\n'))
      setCountriesText(res.data.target_countries.join(', '))
      setLanguagesText(res.data.target_languages.join(', '))
    } catch {
      setSaveError('Failed to save configuration.')
    } finally {
      setSaving(false)
    }
  }

  const toggleAudienceKey = (key: string) => {
    if (!config) return
    const current = config.enabled_audience_keys
    const next = current.includes(key)
      ? current.filter((k) => k !== key)
      : [...current, key]
    setConfig({ ...config, enabled_audience_keys: next })
  }

  const toggleCat = (name: string) => {
    setExpandedCats((prev) => ({ ...prev, [name]: !prev[name] }))
  }

  const selectAllInCat = (cat: AudienceCategory) => {
    if (!config) return
    const keys = cat.types.map((t) => t.key)
    const allSelected = keys.every((k) => config.enabled_audience_keys.includes(k))
    if (allSelected) {
      setConfig({
        ...config,
        enabled_audience_keys: config.enabled_audience_keys.filter(
          (k) => !keys.includes(k),
        ),
      })
    } else {
      const merged = Array.from(new Set([...config.enabled_audience_keys, ...keys]))
      setConfig({ ...config, enabled_audience_keys: merged })
    }
  }

  if (loading) return <div className="p-6 text-text-secondary text-sm">Loading…</div>

  const isRunning = status?.state === 'running' || status?.state === 'discovering'
  const isPaused = status?.state === 'paused'
  const canStop = isRunning || isPaused
  const canRun = !isRunning && !isPaused

  const totalAudienceTypes = categories.reduce((n, c) => n + c.types.length, 0)
  const selectedCount = config?.enabled_audience_keys.length ?? 0

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Bot Control</h1>
        <button
          className="btn-secondary p-2"
          onClick={() => { void load() }}
          disabled={loading}
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* ── Status bar ── */}
      <div className="card flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="text-sm font-medium text-text-primary">
            State:{' '}
            <span
              className={
                isRunning
                  ? 'text-accent-green'
                  : isPaused
                  ? 'text-accent-yellow'
                  : 'text-text-muted'
              }
            >
              {status?.state ?? 'idle'}
            </span>
          </div>
          {status?.last_activity_at && (
            <div className="text-xs text-text-muted">
              Last activity: {new Date(status.last_activity_at).toLocaleString()}
            </div>
          )}
          <div className="text-xs text-text-muted">
            Today: {status?.daily_email_count ?? 0} emails · Total:{' '}
            {status?.total_emails_sent ?? 0}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {canRun && (
            <>
              <button
                className="btn-primary flex items-center gap-2 text-sm"
                onClick={() => setConfirm('run')}
                disabled={actionLoading}
              >
                <Play className="w-4 h-4" />
                Run Now
              </button>
              <button
                className="btn-secondary flex items-center gap-2 text-sm"
                onClick={() => { void handleRun(true) }}
                disabled={actionLoading}
              >
                Dry Run
              </button>
            </>
          )}
          {isRunning && (
            <button
              className="btn-secondary flex items-center gap-2 text-sm"
              onClick={() => setConfirm('pause')}
              disabled={actionLoading}
            >
              <Pause className="w-4 h-4" />
              Pause
            </button>
          )}
          <button
            className="btn-danger flex items-center gap-2 text-sm"
            onClick={() => setConfirm('stop')}
            disabled={actionLoading || !canStop}
          >
            <Square className="w-4 h-4" />
            Stop
          </button>
        </div>
      </div>

      {runError && (
        <div className="rounded-md bg-accent-red/10 border border-accent-red/30 p-3 text-sm text-accent-red">
          {runError}
        </div>
      )}

      {/* ── Config section ── */}
      {config && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Left col: audience selector */}
          <div className="xl:col-span-2 space-y-4">
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-text-primary">
                  Audience Types
                  <span className="ml-2 text-text-muted font-normal">
                    {selectedCount === 0
                      ? `All ${totalAudienceTypes} enabled`
                      : `${selectedCount} / ${totalAudienceTypes} selected`}
                  </span>
                </h2>
                <button
                  className="text-xs text-accent-yellow hover:underline"
                  onClick={() =>
                    setConfig({ ...config, enabled_audience_keys: [] })
                  }
                >
                  Enable all
                </button>
              </div>

              <div className="space-y-3">
                {categories.map((cat) => {
                  const catKeys = cat.types.map((t) => t.key)
                  const allChecked = catKeys.every((k) =>
                    config.enabled_audience_keys.includes(k),
                  )
                  const someChecked =
                    !allChecked &&
                    catKeys.some((k) => config.enabled_audience_keys.includes(k))
                  const expanded = expandedCats[cat.name] ?? true

                  return (
                    <div
                      key={cat.name}
                      className="border border-border rounded-md overflow-hidden"
                    >
                      <div className="flex items-center justify-between px-3 py-2 bg-bg-secondary">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={allChecked}
                            ref={(el) => {
                              if (el) el.indeterminate = someChecked
                            }}
                            onChange={() => selectAllInCat(cat)}
                            className="accent-accent-yellow"
                          />
                          <span className="text-xs font-semibold text-text-primary uppercase tracking-wide">
                            {cat.name}
                          </span>
                          <span className="text-xs text-text-muted">
                            ({cat.types.length})
                          </span>
                        </div>
                        <button
                          onClick={() => toggleCat(cat.name)}
                          className="text-text-muted hover:text-text-primary"
                        >
                          {expanded ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </button>
                      </div>

                      {expanded && (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-px bg-border p-px">
                          {cat.types.map((t) => {
                            const isSelected =
                              config.enabled_audience_keys.length === 0 ||
                              config.enabled_audience_keys.includes(t.key)
                            const isExplicit =
                              config.enabled_audience_keys.includes(t.key)
                            return (
                              <label
                                key={t.key}
                                className={`flex items-start gap-2 p-2 cursor-pointer bg-bg-primary hover:bg-bg-hover ${
                                  isSelected && isExplicit
                                    ? 'bg-accent-yellow/5'
                                    : ''
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isExplicit}
                                  onChange={() => toggleAudienceKey(t.key)}
                                  className="mt-0.5 accent-accent-yellow"
                                />
                                <div className="min-w-0">
                                  <div className="text-xs font-medium text-text-primary truncate">
                                    {t.label_en}
                                  </div>
                                  {t.contact_count > 0 && (
                                    <div className="text-xs text-text-muted">
                                      {t.contact_count.toLocaleString()}
                                    </div>
                                  )}
                                </div>
                              </label>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Right col: settings */}
          <div className="space-y-4">
            {/* Targeting */}
            <div className="card space-y-4">
              <h2 className="text-sm font-semibold text-text-primary">Targeting</h2>

              <div>
                <label className="block text-xs text-text-muted mb-1">
                  Min Confidence: {config.min_confidence}%
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={config.min_confidence}
                  onChange={(e) =>
                    setConfig({ ...config, min_confidence: Number(e.target.value) })
                  }
                  className="w-full accent-accent-yellow"
                />
                <div className="flex justify-between text-xs text-text-muted mt-0.5">
                  <span>0%</span>
                  <span>100%</span>
                </div>
              </div>

              <div>
                <label className="block text-xs text-text-muted mb-1">
                  Target Countries (comma-separated ISO codes)
                </label>
                <input
                  type="text"
                  value={countriesText}
                  onChange={(e) => setCountriesText(e.target.value)}
                  placeholder="US, GB, DE"
                  className="input w-full text-xs"
                />
              </div>

              <div>
                <label className="block text-xs text-text-muted mb-1">
                  Target Languages (comma-separated)
                </label>
                <input
                  type="text"
                  value={languagesText}
                  onChange={(e) => setLanguagesText(e.target.value)}
                  placeholder="en, de, fr"
                  className="input w-full text-xs"
                />
              </div>

              <div>
                <label className="block text-xs text-text-muted mb-1">
                  Exclude Domains (one per line)
                </label>
                <textarea
                  rows={4}
                  value={excludeDomainsText}
                  onChange={(e) => setExcludeDomainsText(e.target.value)}
                  placeholder="gmail.com&#10;yahoo.com"
                  className="input w-full text-xs font-mono resize-y"
                />
              </div>
            </div>

            {/* LLM */}
            <div className="card space-y-3">
              <h2 className="text-sm font-semibold text-text-primary">LLM Provider</h2>
              <select
                value={config.llm_config_id ?? ''}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    llm_config_id: e.target.value || null,
                  })
                }
                className="input w-full text-xs"
              >
                <option value="">— Select provider —</option>
                {llmConfigs.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.display_name} ({l.provider} / {l.model_name})
                  </option>
                ))}
              </select>
              {llmConfigs.length === 0 && (
                <p className="text-xs text-text-muted">
                  No LLM configs yet. Add one in Settings → LLM.
                </p>
              )}
            </div>

            {/* Schedule */}
            <div className="card space-y-4">
              <h2 className="text-sm font-semibold text-text-primary">Schedule</h2>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-text-muted mb-1">
                    Active from (hour)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={23}
                    value={config.active_hours_start}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        active_hours_start: Number(e.target.value),
                      })
                    }
                    className="input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1">
                    Active until (hour)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={23}
                    value={config.active_hours_end}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        active_hours_end: Number(e.target.value),
                      })
                    }
                    className="input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1">
                    Max emails/day
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={config.max_emails_per_day}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        max_emails_per_day: Number(e.target.value),
                      })
                    }
                    className="input w-full text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs text-text-muted mb-1">
                    Max emails/hour
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={config.max_emails_per_hour}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        max_emails_per_hour: Number(e.target.value),
                      })
                    }
                    className="input w-full text-xs"
                  />
                </div>
              </div>

              <Toggle
                checked={config.run_on_weekends}
                onChange={(v) => setConfig({ ...config, run_on_weekends: v })}
                label="Run on weekends"
              />
            </div>

            {/* Behavior */}
            <div className="card space-y-4">
              <h2 className="text-sm font-semibold text-text-primary">Behavior</h2>

              <Toggle
                checked={config.human_in_the_loop}
                onChange={(v) =>
                  setConfig({ ...config, human_in_the_loop: v })
                }
                label="Human-in-the-loop"
                description="Require approval before sending each email"
              />

              <Toggle
                checked={config.dry_run}
                onChange={(v) => setConfig({ ...config, dry_run: v })}
                label="Dry Run mode"
                description="Discover contacts but never send emails"
              />
            </div>

            {/* Cost estimate */}
            <div className="card bg-bg-secondary border-dashed">
              <div className="text-xs text-text-muted mb-1">Estimated daily cost</div>
              <div className="text-lg font-mono font-semibold text-accent-yellow">
                ~{Math.round(config.max_emails_per_day * 0.003 * 100) / 100} USD
              </div>
              <div className="text-xs text-text-muted mt-1">
                Based on {config.max_emails_per_day} emails/day at ~$0.003/email
              </div>
            </div>

            {/* Save */}
            {saveError && (
              <div className="rounded-md bg-accent-red/10 border border-accent-red/30 p-2 text-xs text-accent-red">
                {saveError}
              </div>
            )}
            <button
              className="btn-primary w-full"
              onClick={() => { void handleSaveConfig() }}
              disabled={saving}
            >
              {saving ? 'Saving…' : 'Save Configuration'}
            </button>
          </div>
        </div>
      )}

      {/* ── Confirm modal ── */}
      {confirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="card w-96">
            <h2 className="text-base font-semibold text-text-primary mb-2">
              {confirm === 'run'
                ? 'Start bot run?'
                : `Confirm ${confirm === 'pause' ? 'Pause' : 'Stop'}`}
            </h2>
            <p className="text-sm text-text-secondary mb-4">
              {confirm === 'run'
                ? `This will start a live discovery run${config?.dry_run ? ' (dry run mode is ON — no emails will be sent)' : ''}.`
                : confirm === 'pause'
                ? 'Pause the bot? It can be resumed later.'
                : 'Stop the bot? The current run will be cancelled.'}
            </p>
            <div className="flex gap-2 justify-end">
              <button className="btn-secondary" onClick={() => setConfirm(null)}>
                Cancel
              </button>
              <button
                className={confirm === 'stop' ? 'btn-danger' : 'btn-primary'}
                disabled={actionLoading}
                onClick={() => {
                  if (confirm === 'run') void handleRun(config?.dry_run ?? false)
                  else void handleAction(confirm)
                }}
              >
                {actionLoading
                  ? 'Working…'
                  : confirm === 'run'
                  ? 'Start'
                  : `Yes, ${confirm}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Run history ── */}
      <div className="card">
        <h2 className="text-sm font-semibold text-text-primary mb-4">
          Run History ({runs.length})
        </h2>
        {runs.length === 0 ? (
          <p className="text-sm text-text-muted">No runs yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-text-muted border-b border-border">
                  <th className="text-left pb-2 font-medium">ID</th>
                  <th className="text-left pb-2 font-medium">Type</th>
                  <th className="text-left pb-2 font-medium">Status</th>
                  <th className="text-right pb-2 font-medium">Found</th>
                  <th className="text-left pb-2 font-medium">Started</th>
                  <th className="text-left pb-2 font-medium">Finished</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-bg-hover">
                    <td className="py-2 font-mono text-text-muted pr-3">
                      {run.id.slice(0, 8)}…
                    </td>
                    <td className="py-2 text-text-secondary">{run.run_type}</td>
                    <td className="py-2">
                      <RunBadge status={run.status} />
                    </td>
                    <td className="py-2 text-right font-mono text-text-primary">
                      {run.contacts_found ?? 0}
                    </td>
                    <td className="py-2 text-text-muted">
                      {new Date(run.started_at).toLocaleString()}
                    </td>
                    <td className="py-2 text-text-muted">
                      {run.finished_at
                        ? new Date(run.finished_at).toLocaleString()
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
