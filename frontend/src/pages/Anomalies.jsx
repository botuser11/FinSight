import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { AlertTriangle, X } from 'lucide-react'
import { runDetection, getAnomalies, dismissAnomaly } from '../api/anomalies'
import CategoryBadge from '../components/ui/CategoryBadge'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'

const fmt = (amount) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(amount)

const fmtDate = (ts) =>
  new Date(ts).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

export default function Anomalies() {
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [detecting, setDetecting] = useState(false)

  const load = () => {
    setLoading(true)
    getAnomalies()
      .then(r => setAnomalies(r.data))
      .catch(() => toast.error('Failed to load anomalies.'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const handleDetect = async () => {
    setDetecting(true)
    const tid = toast.loading('Running anomaly detection…')
    try {
      const res = await runDetection()
      const { flagged, by_category } = res.data
      const catCount = Object.keys(by_category).length
      toast.success(
        flagged > 0
          ? `Found ${flagged} anomalies across ${catCount} categor${catCount === 1 ? 'y' : 'ies'}`
          : 'No anomalies found.',
        { id: tid }
      )
      load()
    } catch {
      toast.error('Detection failed.', { id: tid })
    } finally {
      setDetecting(false)
    }
  }

  const handleDismiss = async (id) => {
    try {
      await dismissAnomaly(id)
      setAnomalies(prev => prev.filter(a => a.id !== id))
      toast.success('Anomaly dismissed.')
    } catch {
      toast.error('Failed to dismiss.')
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Anomalies</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Unusual transactions detected by statistical analysis
          </p>
        </div>
        <button
          onClick={handleDetect}
          disabled={detecting}
          className="flex items-center gap-1.5 rounded-lg border border-[#BA7517] text-[#BA7517] text-xs font-medium px-3 py-1.5 hover:bg-[#FAEEDA] dark:hover:bg-[#BA7517]/10 transition-colors disabled:opacity-50"
        >
          <AlertTriangle className={`h-3.5 w-3.5 ${detecting ? 'animate-pulse' : ''}`} />
          Run detection
        </button>
      </div>

      {/* Content */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 overflow-hidden">
        {loading ? (
          <LoadingSpinner size="lg" className="py-16" />
        ) : anomalies.length === 0 ? (
          <EmptyState
            icon={AlertTriangle}
            title="No anomalies detected"
            description="Run detection from the dashboard or use the button above to analyse your transactions."
            action={
              <button
                onClick={handleDetect}
                disabled={detecting}
                className="inline-flex items-center gap-2 rounded-lg bg-[#BA7517] hover:bg-[#9a6113] text-white text-sm font-medium px-4 py-2 transition-colors disabled:opacity-50"
              >
                <AlertTriangle className="h-4 w-4" />
                Run detection now
              </button>
            }
          />
        ) : (
          <>
            {/* Table header */}
            <div className="grid grid-cols-[1fr_160px_180px_110px_80px_36px] gap-2 px-5 py-2.5 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-[#111111]">
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Merchant</span>
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Reason</span>
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Category</span>
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Date</span>
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide text-right">Amount</span>
              <span />
            </div>

            <div className="divide-y divide-slate-50 dark:divide-slate-800">
              {anomalies.map(a => (
                <div
                  key={a.id}
                  className="grid grid-cols-[1fr_160px_180px_110px_80px_36px] gap-2 items-center px-5 py-3.5 border-l-2 border-l-[#BA7517] hover:bg-[#FAEEDA]/10 dark:hover:bg-[#BA7517]/5 transition-colors"
                >
                  {/* Merchant */}
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
                      {a.merchant_name || 'Unknown'}
                    </p>
                    {a.account_display_name && (
                      <p className="text-xs text-slate-400 truncate">{a.account_display_name}</p>
                    )}
                  </div>

                  {/* Reason badge */}
                  <span
                    className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium truncate"
                    style={{ backgroundColor: '#FAEEDA', color: '#BA7517' }}
                    title={a.anomaly_reason}
                  >
                    {a.anomaly_reason || 'Unusual amount'}
                  </span>

                  {/* Category */}
                  <CategoryBadge name={a.category?.name} />

                  {/* Date */}
                  <span className="text-xs text-slate-400 dark:text-slate-500">
                    {fmtDate(a.timestamp)}
                  </span>

                  {/* Amount */}
                  <span className="text-sm font-semibold text-[#D85A30] text-right">
                    {fmt(a.amount)}
                  </span>

                  {/* Dismiss */}
                  <button
                    onClick={() => handleDismiss(a.id)}
                    title="Dismiss anomaly"
                    className="flex items-center justify-center h-7 w-7 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>

            <div className="px-5 py-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-[#111111]">
              <p className="text-xs text-slate-400 dark:text-slate-500">
                {anomalies.length} anomal{anomalies.length === 1 ? 'y' : 'ies'} — transactions more than 2 standard deviations above category average
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
