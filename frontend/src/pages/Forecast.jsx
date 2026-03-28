import { useEffect, useState } from 'react'
import { TrendingDown, TrendingUp, Minus } from 'lucide-react'
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getForecast } from '../api/forecast'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'

const fmt = (v) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(v)

const fmtMonth = (ym) => {
  const [y, m] = ym.split('-')
  return new Date(parseInt(y), parseInt(m) - 1).toLocaleDateString('en-GB', {
    month: 'short',
    year: '2-digit',
  })
}

const TREND_CONFIG = {
  increasing: {
    label: 'Your spending is trending upward',
    color: '#D85A30',
    Icon: TrendingUp,
    bg: '#FAECE7',
  },
  decreasing: {
    label: 'Your spending is trending downward',
    color: '#1D9E75',
    Icon: TrendingDown,
    bg: '#E1F5EE',
  },
  stable: {
    label: 'Your spending is stable',
    color: '#6B7280',
    Icon: Minus,
    bg: '#F1F5F9',
  },
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null
  const entry = payload[0]
  const isForecast = entry.dataKey === 'predicted'
  return (
    <div className="bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-lg text-xs">
      <p className="font-semibold text-slate-700 dark:text-slate-200 mb-1">{label}</p>
      <p style={{ color: isForecast ? '#378ADD' : '#D85A30' }}>
        {isForecast ? 'Forecast: ' : 'Actual: '}
        {fmt(entry.value)}
      </p>
    </div>
  )
}

export default function Forecast() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getForecast(3)
      .then(r => setData(r.data))
      .catch(e => setError(e))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner size="lg" className="h-[60vh]" />

  if (error || !data || data.error) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <EmptyState
          icon={TrendingUp}
          title="Not enough data to forecast"
          description="You need at least 3 months of transaction history to generate a forecast."
        />
      </div>
    )
  }

  const trend = TREND_CONFIG[data.trend] || TREND_CONFIG.stable
  const TrendIcon = trend.Icon

  // Merge historical + forecast into one series for the chart
  // Historical entries have `actual`, forecast entries have `predicted`
  const chartData = [
    ...data.historical.map(h => ({ month: fmtMonth(h.month), actual: h.actual, predicted: null })),
    ...data.forecast.map(f => ({ month: fmtMonth(f.month), actual: null, predicted: f.predicted })),
  ]

  // 3-month average from last 3 historical entries
  const last3 = data.historical.slice(-3)
  const avg3 = last3.length > 0
    ? last3.reduce((s, h) => s + h.actual, 0) / last3.length
    : 0

  // Dividing line index (where forecast starts)
  const splitIndex = data.historical.length - 1

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">
            Spending forecast
          </h1>
          <div
            className="mt-2 inline-flex items-center gap-1.5 rounded-full px-3 py-1"
            style={{ backgroundColor: trend.bg }}
          >
            <TrendIcon className="h-3.5 w-3.5 shrink-0" style={{ color: trend.color }} />
            <span className="text-xs font-medium" style={{ color: trend.color }}>
              {trend.label}
            </span>
          </div>
        </div>
      </div>

      {/* Main chart */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 p-5">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-5">
          Monthly spending — actual &amp; forecast
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={chartData} barSize={18}>
            <CartesianGrid strokeDasharray="0" horizontal vertical={false} stroke="#e2e8f0" />
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#9CA3AF' }}
              interval={Math.floor(chartData.length / 8)}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: '#9CA3AF' }}
              tickFormatter={v => `£${(v / 1000).toFixed(0)}k`}
              width={42}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              iconType="circle"
              iconSize={8}
              formatter={(v) => (
                <span className="text-xs text-slate-600 dark:text-slate-400">
                  {v === 'actual' ? 'Actual spending' : 'Forecast'}
                </span>
              )}
            />

            {/* Reference line at the split between actual/forecast */}
            {splitIndex >= 0 && (
              <ReferenceLine
                x={chartData[splitIndex]?.month}
                stroke="#CBD5E1"
                strokeDasharray="4 3"
                label={{ value: 'Today', fill: '#94A3B8', fontSize: 10, position: 'top' }}
              />
            )}

            <Bar dataKey="actual" name="actual" fill="#D85A30" radius={[3, 3, 0, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill="#D85A30" fillOpacity={0.8} />
              ))}
            </Bar>

            <Line
              dataKey="predicted"
              name="predicted"
              stroke="#378ADD"
              strokeWidth={2.5}
              strokeDasharray="6 3"
              dot={{ fill: '#378ADD', r: 4, strokeWidth: 0 }}
              connectNulls={false}
              activeDot={{ r: 6 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Next month forecast */}
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 p-5"
          style={{ borderLeft: '4px solid #378ADD' }}>
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Next month forecast</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">
            {fmt(data.current_month_predicted)}
          </p>
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
            {fmtMonth(data.forecast[0]?.month || '')} · exponential smoothing
          </p>
        </div>

        {/* 3-month average */}
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 p-5"
          style={{ borderLeft: '4px solid #534AB7' }}>
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">3-month average</p>
          <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50">
            {fmt(avg3)}
          </p>
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
            Average of last {last3.length} months actual spend
          </p>
        </div>
      </div>

      {/* Historical breakdown table */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Monthly history</h2>
        </div>
        <div className="divide-y divide-slate-50 dark:divide-slate-800">
          {[...data.historical].reverse().slice(0, 12).map((h) => (
            <div key={h.month} className="flex items-center justify-between px-5 py-3">
              <span className="text-sm text-slate-600 dark:text-slate-400">{fmtMonth(h.month)}</span>
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">{fmt(h.actual)}</span>
            </div>
          ))}
          {data.forecast.map((f) => (
            <div key={f.month} className="flex items-center justify-between px-5 py-3 bg-[#E6F1FB]/30 dark:bg-[#378ADD]/5">
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600 dark:text-slate-400">{fmtMonth(f.month)}</span>
                <span className="rounded-full bg-[#E6F1FB] dark:bg-[#378ADD]/20 text-[#378ADD] text-[10px] font-medium px-2 py-0.5">
                  forecast
                </span>
              </div>
              <span className="text-sm font-semibold text-[#378ADD]">{fmt(f.predicted)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
