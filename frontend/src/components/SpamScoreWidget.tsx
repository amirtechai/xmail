import { useState } from 'react'
import { ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react'
import { campaignsApi } from '../lib/api'

interface SpamRule {
  name: string
  description: string
  score: number
}

interface SpamResult {
  score: number
  label: 'good' | 'fair' | 'warning' | 'high_risk'
  rules: SpamRule[]
}

const LABEL_CONFIG = {
  good: { text: 'Good', color: 'text-accent-green', bg: 'bg-accent-green/10 border-accent-green/30', Icon: ShieldCheck },
  fair: { text: 'Fair', color: 'text-accent-yellow', bg: 'bg-accent-yellow/10 border-accent-yellow/30', Icon: ShieldAlert },
  warning: { text: 'Warning', color: 'text-orange-400', bg: 'bg-orange-400/10 border-orange-400/30', Icon: ShieldAlert },
  high_risk: { text: 'High Risk', color: 'text-accent-red', bg: 'bg-accent-red/10 border-accent-red/30', Icon: ShieldX },
}

export function SpamScoreWidget({ campaignId }: { campaignId: string }) {
  const [result, setResult] = useState<SpamResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await campaignsApi.spamCheck(campaignId)
      setResult(data as SpamResult)
    } catch {
      setError('Spam check failed.')
    } finally {
      setLoading(false)
    }
  }

  if (!result) {
    return (
      <button
        className="btn-secondary flex items-center gap-1.5 text-sm px-3 py-1.5"
        onClick={() => { void run() }}
        disabled={loading}
        title="Check spam score"
      >
        <ShieldAlert className="w-3.5 h-3.5" />
        {loading ? 'Checking…' : 'Spam Check'}
        {error && <span className="text-accent-red text-xs ml-1">{error}</span>}
      </button>
    )
  }

  const cfg = LABEL_CONFIG[result.label]
  const { Icon } = cfg

  return (
    <div className="relative">
      <button
        className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md border transition-colors ${cfg.bg} ${cfg.color}`}
        onClick={() => setExpanded((v) => !v)}
        title="Click to see details"
      >
        <Icon className="w-3.5 h-3.5" />
        {cfg.text} ({result.score.toFixed(1)})
      </button>

      {expanded && (
        <div className="absolute right-0 top-full mt-1 z-40 w-80 bg-bg-secondary border border-border rounded-lg shadow-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-text-primary">Spam Analysis</span>
            <div className={`text-2xl font-mono font-bold ${cfg.color}`}>{result.score.toFixed(1)}</div>
          </div>
          <div className="text-xs text-text-muted">SpamAssassin threshold: 5.0. Lower is better.</div>

          {result.rules.length > 0 ? (
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {result.rules.sort((a, b) => b.score - a.score).map((r, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className={`font-mono shrink-0 w-10 text-right ${r.score > 0 ? 'text-accent-red' : 'text-accent-green'}`}>
                    {r.score > 0 ? '+' : ''}{r.score.toFixed(2)}
                  </span>
                  <div>
                    <div className="font-medium text-text-secondary">{r.name}</div>
                    {r.description && <div className="text-text-muted">{r.description}</div>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-text-muted">No triggered rules.</div>
          )}

          <button
            className="text-xs text-accent-blue hover:underline"
            onClick={() => { void run() }}
            disabled={loading}
          >
            {loading ? 'Re-checking…' : 'Re-check'}
          </button>
        </div>
      )}
    </div>
  )
}
