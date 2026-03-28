import { useEffect, useState } from 'react'
import { ArrowRight, ArrowUpRight, PiggyBank, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react'
import { getSubscriptions, getTrends, getPriceAlerts } from '../api/insights'
import CategoryBadge from '../components/ui/CategoryBadge'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'

const fmt = (v) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(v)

const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

function Section({ title, loading, children }) {
  return (
    <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 overflow-hidden">
      <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{title}</h2>
      </div>
      {loading ? <LoadingSpinner className="py-10" /> : children}
    </div>
  )
}

export default function Savings() {
  const [subs, setSubs] = useState([])
  const [trends, setTrends] = useState([])
  const [alerts, setAlerts] = useState([])
  const [loadingSubs, setLoadingSubs] = useState(true)
  const [loadingTrends, setLoadingTrends] = useState(true)
  const [loadingAlerts, setLoadingAlerts] = useState(true)

  useEffect(() => {
    getSubscriptions()
      .then(r => setSubs(r.data))
      .finally(() => setLoadingSubs(false))

    getTrends()
      .then(r => setTrends(r.data))
      .finally(() => setLoadingTrends(false))

    getPriceAlerts()
      .then(r => setAlerts(r.data))
      .finally(() => setLoadingAlerts(false))
  }, [])

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Savings insights</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          Subscriptions, spending shifts, and price changes detected automatically
        </p>
      </div>

      {/* Section 1 — Recurring payments */}
      <Section title="Recurring payments" loading={loadingSubs}>
        {subs.length === 0 ? (
          <EmptyState
            icon={RefreshCw}
            title="No recurring payments detected"
            description="We look for merchants charging similar amounts on a regular schedule."
          />
        ) : (
          <div className="divide-y divide-slate-50 dark:divide-slate-800">
            {subs.map((sub, i) => (
              <div
                key={i}
                className="flex items-center gap-4 px-5 py-4 border-l-2 border-l-[#D85A30]"
              >
                {/* Left */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                      {sub.merchant}
                    </span>
                    <span
                      className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      style={{ backgroundColor: '#FAECE7', color: '#D85A30' }}
                    >
                      {sub.frequency}
                    </span>
                    <CategoryBadge name={sub.category} />
                  </div>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                    {sub.occurrences} charges · last {fmtDate(sub.last_charged)}
                  </p>
                </div>

                {/* Right */}
                <div className="text-right shrink-0">
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {fmt(sub.amount)}
                  </p>
                  <p className="text-xs text-slate-400 dark:text-slate-500">
                    {fmt(sub.total_paid)} total
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Section 2 — Spending trends */}
      <Section title="Spending trends (last 30 days)" loading={loadingTrends}>
        {trends.length === 0 ? (
          <EmptyState
            icon={TrendingUp}
            title="No significant trends detected"
            description="We compare the last 30 days against the prior 30 days per category."
          />
        ) : (
          <div className="divide-y divide-slate-50 dark:divide-slate-800">
            {trends.map((t, i) => {
              const isUp = t.direction === 'up'
              const Icon = isUp ? TrendingUp : TrendingDown
              const color = isUp ? '#D85A30' : '#1D9E75'
              const bg = isUp ? '#FAECE7' : '#E1F5EE'
              return (
                <div key={i} className="flex items-center gap-4 px-5 py-4">
                  {/* Icon */}
                  <div
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                    style={{ backgroundColor: bg }}
                  >
                    <Icon className="h-4 w-4" style={{ color }} />
                  </div>

                  {/* Category + amounts */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <CategoryBadge name={t.category} />
                    </div>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                      {fmt(t.previous)} → {fmt(t.current)}
                    </p>
                  </div>

                  {/* Change % */}
                  <div className="text-right shrink-0">
                    <span
                      className="text-sm font-bold"
                      style={{ color }}
                    >
                      {isUp ? '+' : ''}{t.change_pct}%
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Section>

      {/* Section 3 — Price increases */}
      <Section title="Price increases detected" loading={loadingAlerts}>
        {alerts.length === 0 ? (
          <EmptyState
            icon={ArrowUpRight}
            title="No price increases detected"
            description="We flag recurring merchants whose charges have risen more than 5%."
          />
        ) : (
          <div className="divide-y divide-slate-50 dark:divide-slate-800">
            {alerts.map((a, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-4">
                {/* Merchant + date */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                    {a.merchant}
                  </p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                    Since {fmtDate(a.since)}
                  </p>
                </div>

                {/* Old → New */}
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-sm text-slate-400 dark:text-slate-500 line-through">
                    {fmt(a.old_amount)}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {fmt(a.new_amount)}
                  </span>
                </div>

                {/* Increase badge */}
                <span
                  className="shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold"
                  style={{ backgroundColor: '#FAEEDA', color: '#BA7517' }}
                >
                  +{a.increase_pct}%
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}
