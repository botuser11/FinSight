import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  AlertTriangle,
  ArrowUpRight,
  PiggyBank,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getAccounts, getConnectUrl, syncTransactions } from '../api/banking'
import { categoriseAll } from '../api/transactions'
import { runDetection } from '../api/anomalies'
import useDashboard from '../hooks/useDashboard'
import MetricCard from '../components/ui/MetricCard'
import TransactionRow from '../components/ui/TransactionRow'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'
import { CATEGORY_COLORS } from '../components/ui/CategoryBadge'

const fmt = (amount) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(Math.abs(amount))

const MONTH_NAMES = [
  'Jan','Feb','Mar','Apr','May','Jun',
  'Jul','Aug','Sep','Oct','Nov','Dec',
]

function CustomBarTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-lg text-xs">
        <p className="font-semibold text-slate-700 dark:text-slate-200">Day {label}</p>
        <p className="text-[#D85A30]">£{payload[0].value.toFixed(2)}</p>
      </div>
    )
  }
  return null
}

function CustomPieTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-lg text-xs">
        <p className="font-semibold text-slate-700 dark:text-slate-200">{payload[0].name}</p>
        <p style={{ color: payload[0].payload.fill }}>£{Math.abs(payload[0].value).toFixed(2)}</p>
      </div>
    )
  }
  return null
}

export default function Dashboard() {
  const [searchParams] = useSearchParams()
  const now = new Date()
  const month = parseInt(searchParams.get('month') || now.getMonth() + 1)
  const year = parseInt(searchParams.get('year') || now.getFullYear())

  const { accounts, summary, dailyData, recent, metrics, loading, error } = useDashboard(month, year)

  const [syncing, setSyncing] = useState(false)
  const [categorising, setCategorising] = useState(false)
  const [detecting, setDetecting] = useState(false)

  // Handle ?connected=true redirect from OAuth
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('connected') === 'true') {
      toast.success('Bank connected successfully!')
      window.history.replaceState({}, '', '/dashboard')
    }
    if (params.get('error') === 'true') {
      toast.error('Failed to connect bank. Please try again.')
      window.history.replaceState({}, '', '/dashboard')
    }
  }, [])

  const handleConnect = async () => {
    try {
      const res = await getConnectUrl()
      window.location.href = res.data.auth_url
    } catch {
      toast.error('Could not get connection URL.')
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      const res = await syncTransactions()
      toast.success(`Synced ${res.data.synced || 0} new transactions.`)
      window.location.reload()
    } catch {
      toast.error('Sync failed.')
    } finally {
      setSyncing(false)
    }
  }

  const handleCategorise = async () => {
    setCategorising(true)
    const tid = toast.loading('Categorising transactions…')
    try {
      const res = await categoriseAll()
      toast.success(`Categorised ${res.data.categorised} transactions.`, { id: tid })
      window.location.reload()
    } catch {
      toast.error('Categorisation failed.', { id: tid })
    } finally {
      setCategorising(false)
    }
  }

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
      window.location.reload()
    } catch {
      toast.error('Detection failed.', { id: tid })
    } finally {
      setDetecting(false)
    }
  }

  // Pie chart data — only expenses from summary
  const pieData = summary
    .filter(s => s.total < 0)
    .map(s => ({ name: s.category, value: Math.abs(s.total), fill: CATEGORY_COLORS[s.category] || '#888780' }))
  const pieTotal = pieData.reduce((s, d) => s + d.value, 0)

  const pendingCount = recent.filter(t => t.categorisation_source === 'pending').length

  if (loading) {
    return <LoadingSpinner size="lg" className="h-[60vh]" />
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <p className="text-sm text-slate-500 dark:text-slate-400">Failed to load dashboard data.</p>
      </div>
    )
  }

  // No bank connected
  if (accounts.length === 0) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <div className="text-center max-w-sm">
          <div className="mx-auto mb-5 h-20 w-20 rounded-2xl bg-[#EEEDFE] dark:bg-[#534AB7]/20 flex items-center justify-center">
            <Wallet className="h-10 w-10 text-[#534AB7]" />
          </div>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Connect your bank</h2>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Link your bank account to start tracking your finances automatically.
          </p>
          <button
            onClick={handleConnect}
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-[#534AB7] hover:bg-[#3C3489] text-white text-sm font-semibold px-5 py-2.5 transition-colors"
          >
            Connect Bank
            <ArrowUpRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">
            {MONTH_NAMES[month - 1]} {year}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Financial overview</p>
        </div>
        <div className="flex items-center gap-2">
          {pendingCount > 0 && (
            <button
              onClick={handleCategorise}
              disabled={categorising}
              className="flex items-center gap-1.5 rounded-lg border border-[#534AB7] text-[#534AB7] text-xs font-medium px-3 py-1.5 hover:bg-[#EEEDFE] dark:hover:bg-[#534AB7]/10 transition-colors disabled:opacity-50"
            >
              <span>Categorise ({pendingCount})</span>
            </button>
          )}
          <button
            onClick={handleDetect}
            disabled={detecting}
            className="flex items-center gap-1.5 rounded-lg border border-[#BA7517] text-[#BA7517] text-xs font-medium px-3 py-1.5 hover:bg-[#FAEEDA] dark:hover:bg-[#BA7517]/10 transition-colors disabled:opacity-50"
          >
            <AlertTriangle className={`h-3.5 w-3.5 ${detecting ? 'animate-pulse' : ''}`} />
            Run detection
          </button>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-1.5 rounded-lg bg-[#534AB7] hover:bg-[#3C3489] text-white text-xs font-medium px-3 py-1.5 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
            Sync
          </button>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          title="Total spent"
          value={fmt(metrics.totalSpent)}
          subtitle={`${MONTH_NAMES[month - 1]} ${year}`}
          icon={TrendingDown}
          color="coral"
        />
        <MetricCard
          title="Total income"
          value={fmt(metrics.totalIncome)}
          subtitle={`${MONTH_NAMES[month - 1]} ${year}`}
          icon={TrendingUp}
          color="teal"
        />
        <MetricCard
          title="Saved"
          value={fmt(metrics.saved)}
          subtitle={metrics.saved >= 0 ? 'Positive balance' : 'Overspent'}
          icon={PiggyBank}
          color={metrics.saved >= 0 ? 'indigo' : 'coral'}
        />
        <MetricCard
          title="Anomalies"
          value={metrics.anomalyCount.toString()}
          subtitle="Unusual transactions"
          icon={AlertTriangle}
          color="amber"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Daily spending bar chart */}
        <div className="xl:col-span-2 bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 p-5">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-4">
            Daily Spending
          </h2>
          {dailyData.every(d => d.amount === 0) ? (
            <div className="flex items-center justify-center h-48 text-sm text-slate-400">
              No spending data for this month
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={dailyData} barSize={8}>
                <CartesianGrid strokeDasharray="0" horizontal={true} vertical={false} stroke="#e2e8f0" />
                <XAxis
                  dataKey="day"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11, fill: '#9CA3AF' }}
                  interval={4}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11, fill: '#9CA3AF' }}
                  tickFormatter={v => `£${v}`}
                  width={45}
                />
                <Tooltip content={<CustomBarTooltip />} cursor={{ fill: '#f1f5f9', opacity: 0.6 }} />
                <Bar dataKey="amount" radius={[3, 3, 0, 0]}>
                  {dailyData.map((entry, i) => (
                    <Cell key={i} fill={entry.isFuture ? '#378ADD' : '#D85A30'} fillOpacity={entry.isFuture ? 0.4 : 0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Category donut chart */}
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 p-5">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-4">
            By Category
          </h2>
          {pieData.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-sm text-slate-400">
              No category data
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={88}
                    dataKey="value"
                    paddingAngle={2}
                  >
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomPieTooltip />} />
                </PieChart>
              </ResponsiveContainer>

              {/* Custom legend below chart */}
              <div className="flex flex-wrap gap-x-4 gap-y-2 mt-3">
                {pieData.map((entry) => {
                  const pct = pieTotal > 0 ? ((entry.value / pieTotal) * 100).toFixed(0) : 0
                  return (
                    <div key={entry.name} className="flex items-center gap-1.5">
                      <span
                        className="h-2 w-2 rounded-full shrink-0"
                        style={{ backgroundColor: entry.fill }}
                      />
                      <span className="text-xs text-slate-600 dark:text-slate-400">
                        {entry.name}
                      </span>
                      <span className="text-xs text-slate-400 dark:text-slate-500">
                        {pct}%
                      </span>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Recent transactions */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-800">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Recent Transactions</h2>
          <Link
            to={`/transactions?month=${month}&year=${year}`}
            className="text-xs font-medium text-[#534AB7] hover:text-[#3C3489] transition-colors"
          >
            View all →
          </Link>
        </div>

        {recent.length === 0 ? (
          <EmptyState
            title="No transactions"
            description="Sync your bank to see recent transactions here."
          />
        ) : (
          <div className="divide-y divide-slate-50 dark:divide-slate-800">
            {recent.map(tx => (
              <TransactionRow key={tx.id} tx={tx} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
