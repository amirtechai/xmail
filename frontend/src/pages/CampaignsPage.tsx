import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, PenLine, PlusCircle, RefreshCw } from 'lucide-react'
import { campaignsApi, type Campaign } from '../lib/api'

const STATUS_COLORS: Record<string, string> = {
  draft: 'badge-muted',
  searching: 'badge-blue',
  ready_to_send: 'badge-yellow',
  sending: 'badge-blue',
  paused: 'badge-yellow',
  completed: 'badge-green',
  archived: 'badge-muted',
}

function Rate({ value, warn }: { value: number; warn?: boolean }) {
  return (
    <span className={warn && value > 0 ? 'text-accent-red font-semibold' : 'text-text-primary'}>
      {value.toFixed(1)}%
    </span>
  )
}

interface CampaignRow extends Campaign {
  open_rate?: number
  click_rate?: number
  bounce_rate?: number
  sent?: number
  alerts?: { type: string; message: string }[]
}

export default function CampaignsPage() {
  const navigate = useNavigate()
  const [campaigns, setCampaigns] = useState<CampaignRow[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await campaignsApi.list()
      // Fetch stats in parallel for non-draft campaigns
      const withStats: CampaignRow[] = await Promise.all(
        data.map(async (c) => {
          if (c.status === 'draft') return c
          try {
            const { data: s } = await campaignsApi.stats(c.id)
            return {
              ...c,
              open_rate: s.open_rate,
              click_rate: s.click_rate,
              bounce_rate: s.bounce_rate,
              sent: s.sent,
              alerts: s.alerts,
            }
          } catch {
            return c
          }
        }),
      )
      setCampaigns(withStats)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Campaigns</h1>
        <div className="flex gap-2">
          <button
            className="btn-secondary p-2"
            onClick={() => { void load() }}
            disabled={loading}
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            className="btn-primary flex items-center gap-2 text-sm"
            onClick={() => navigate('/compose')}
          >
            <PlusCircle className="w-4 h-4" />
            New Campaign
          </button>
        </div>
      </div>

      <div className="card overflow-x-auto">
        {loading ? (
          <p className="text-sm text-text-muted py-4">Loading…</p>
        ) : campaigns.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-text-muted text-sm mb-4">No campaigns yet.</p>
            <button
              className="btn-primary flex items-center gap-2 mx-auto text-sm"
              onClick={() => navigate('/compose')}
            >
              <PlusCircle className="w-4 h-4" />
              Create your first campaign
            </button>
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-text-muted border-b border-border">
                <th className="text-left pb-2 font-medium">Name</th>
                <th className="text-left pb-2 font-medium">Status</th>
                <th className="text-right pb-2 font-medium">Sent</th>
                <th className="text-right pb-2 font-medium">Open %</th>
                <th className="text-right pb-2 font-medium">Click %</th>
                <th className="text-right pb-2 font-medium">Bounce %</th>
                <th className="text-left pb-2 font-medium">Created</th>
                <th className="text-right pb-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {campaigns.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-bg-hover cursor-pointer"
                  onClick={() => navigate(`/campaigns/${c.id}`)}
                >
                  <td className="py-2 text-text-primary font-medium max-w-[200px] truncate">
                    <div className="flex items-center gap-1.5">
                      {(c.alerts?.length ?? 0) > 0 && (
                        <span title={c.alerts![0].message}><AlertTriangle className="w-3.5 h-3.5 text-accent-red shrink-0" /></span>
                      )}
                      {c.name}
                    </div>
                  </td>
                  <td className="py-2">
                    <span className={`badge ${STATUS_COLORS[c.status] ?? 'badge-muted'}`}>
                      {c.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="py-2 text-right font-mono text-text-primary">
                    {c.sent?.toLocaleString() ?? '—'}
                  </td>
                  <td className="py-2 text-right">
                    {c.open_rate != null ? <Rate value={c.open_rate} /> : '—'}
                  </td>
                  <td className="py-2 text-right">
                    {c.click_rate != null ? <Rate value={c.click_rate} /> : '—'}
                  </td>
                  <td className="py-2 text-right">
                    {c.bounce_rate != null ? <Rate value={c.bounce_rate} warn={c.bounce_rate > 2} /> : '—'}
                  </td>
                  <td className="py-2 text-text-muted">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-2 text-right">
                    <button
                      className="p-1 text-text-muted hover:text-text-primary"
                      title="Edit in Compose"
                      onClick={(e) => {
                        e.stopPropagation()
                        navigate(`/compose?id=${c.id}`)
                      }}
                    >
                      <PenLine className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
