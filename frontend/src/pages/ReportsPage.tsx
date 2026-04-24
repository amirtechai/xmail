import { useEffect, useState } from 'react'
import { Download, FileText, RefreshCw } from 'lucide-react'
import { reportsApi, type ReportItem } from '../lib/api'

function today() {
  return new Date().toISOString().slice(0, 10)
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState<string | null>(null)
  const [customDate, setCustomDate] = useState(today())
  const [generateError, setGenerateError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await reportsApi.list()
      setReports(data.items ?? [])
    } catch {
      // silently ignore on refresh
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const generate = async (date: string) => {
    setGenerating(date)
    setGenerateError(null)
    try {
      await reportsApi.generate(date)
      await load()
    } catch {
      setGenerateError(`Failed to generate report for ${date}.`)
    } finally {
      setGenerating(null)
    }
  }

  const existingDates = new Set(reports.map((r) => r.date))

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold text-text-primary">Daily Reports</h1>
        <button
          className="btn-secondary flex items-center gap-2 text-sm"
          onClick={() => { void load() }}
          disabled={loading}
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Generate for custom date */}
      <div className="card">
        <h2 className="text-sm font-semibold text-text-primary mb-3">Generate Report</h2>
        <div className="flex items-center gap-3 flex-wrap">
          <input
            type="date"
            value={customDate}
            max={today()}
            onChange={(e) => setCustomDate(e.target.value)}
            className="input text-sm w-44"
          />
          <button
            className="btn-primary flex items-center gap-2 text-sm"
            disabled={!!generating || !customDate}
            onClick={() => { void generate(customDate) }}
          >
            <FileText className="w-4 h-4" />
            {generating === customDate ? 'Generating…' : 'Generate'}
          </button>
          {existingDates.has(customDate) && (
            <span className="text-xs text-text-muted">
              Report for {customDate} already exists — will regenerate.
            </span>
          )}
        </div>
        {generateError && (
          <p className="text-xs text-accent-red mt-2">{generateError}</p>
        )}
      </div>

      {/* Report list */}
      <div className="card">
        <h2 className="text-sm font-semibold text-text-primary mb-4">
          Available Reports ({reports.length})
        </h2>

        {loading ? (
          <p className="text-sm text-text-muted">Loading…</p>
        ) : reports.length === 0 ? (
          <p className="text-sm text-text-muted">No reports generated yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-text-muted border-b border-border">
                  <th className="text-left pb-2 font-medium">Date</th>
                  <th className="text-left pb-2 font-medium">PDF</th>
                  <th className="text-left pb-2 font-medium">XML</th>
                  <th className="text-left pb-2 font-medium">Size</th>
                  <th className="text-right pb-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {reports.map((r) => (
                  <tr key={r.date} className="hover:bg-bg-hover">
                    <td className="py-2 font-mono text-text-primary">{r.date}</td>
                    <td className="py-2">
                      {r.pdf_available
                        ? <span className="badge badge-green">Ready</span>
                        : <span className="badge badge-muted">—</span>}
                    </td>
                    <td className="py-2">
                      {r.xml_available
                        ? <span className="badge badge-green">Ready</span>
                        : <span className="badge badge-muted">—</span>}
                    </td>
                    <td className="py-2 font-mono text-text-muted">
                      {r.pdf_size > 0
                        ? `${(r.pdf_size / 1024).toFixed(1)} KB`
                        : '—'}
                    </td>
                    <td className="py-2">
                      <div className="flex items-center gap-2 justify-end">
                        {r.pdf_available && (
                          <a
                            href={reportsApi.downloadPdfUrl(r.date)}
                            target="_blank"
                            rel="noreferrer"
                            className="btn-secondary py-1 px-2 flex items-center gap-1"
                          >
                            <Download className="w-3 h-3" />
                            PDF
                          </a>
                        )}
                        {r.xml_available && (
                          <a
                            href={reportsApi.downloadXmlUrl(r.date)}
                            target="_blank"
                            rel="noreferrer"
                            className="btn-secondary py-1 px-2 flex items-center gap-1"
                          >
                            <Download className="w-3 h-3" />
                            XML
                          </a>
                        )}
                        {(!r.pdf_available || !r.xml_available) && (
                          <button
                            className="btn-primary py-1 px-2 flex items-center gap-1"
                            onClick={() => { void generate(r.date) }}
                            disabled={generating === r.date}
                          >
                            <FileText className="w-3 h-3" />
                            {generating === r.date ? 'Generating…' : 'Generate'}
                          </button>
                        )}
                      </div>
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
