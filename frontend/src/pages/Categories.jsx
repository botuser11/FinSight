import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { PieChart } from 'lucide-react'
import { getCategories, getSummary, getTransactions, updateCategory } from '../api/transactions'
import { CATEGORY_COLORS } from '../components/ui/CategoryBadge'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'

const fmt = (amount) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(amount)

const fmtDate = (ts) =>
  new Date(ts).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })

const MONTH_NAMES = [
  'Jan','Feb','Mar','Apr','May','Jun',
  'Jul','Aug','Sep','Oct','Nov','Dec',
]

export default function Categories() {
  const [searchParams] = useSearchParams()
  const now = new Date()
  const month = parseInt(searchParams.get('month') || now.getMonth() + 1)
  const year = parseInt(searchParams.get('year') || now.getFullYear())

  const [summary, setSummary] = useState(null)
  const [categories, setCategories] = useState([])
  const [selected, setSelected] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [txLoading, setTxLoading] = useState(false)

  const loadSummary = useCallback(() => {
    return getSummary(month, year).then(r => setSummary(r.data))
  }, [month, year])

  useEffect(() => {
    setLoading(true)
    setSelected(null)
    Promise.all([loadSummary(), getCategories().then(r => setCategories(r.data))])
      .catch(() => toast.error('Failed to load categories.'))
      .finally(() => setLoading(false))
  }, [loadSummary])

  const loadTransactions = useCallback((categoryName) => {
    const category = categories.find(c => c.name === categoryName)
    if (!category) return
    setTxLoading(true)
    getTransactions({ month, year, category_id: category.id, page_size: 100 })
      .then(r => setTransactions((r.data.transactions || []).filter(t => t.amount < 0)))
      .catch(() => toast.error('Failed to load transactions.'))
      .finally(() => setTxLoading(false))
  }, [categories, month, year])

  useEffect(() => {
    if (selected) loadTransactions(selected)
  }, [selected, loadTransactions])

  const handleReassign = async (tx, categoryId) => {
    try {
      await updateCategory(tx.id, Number(categoryId))
      toast.success('Category updated.')
      await loadSummary()
      loadTransactions(selected)
    } catch {
      toast.error('Failed to update category.')
    }
  }

  if (loading) return <LoadingSpinner size="lg" className="h-[60vh]" />

  const rows = summary?.by_category || []
  const max = Math.max(...rows.map(r => r.total), 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Categories</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          Spending by category, {MONTH_NAMES[month - 1]} {year}. Select a category to review and reassign its transactions.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 p-5">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Spend by category</h2>
            <span className="text-xs text-slate-400">Total {fmt(summary?.spend || 0)}</span>
          </div>
          {rows.length === 0 ? (
            <EmptyState icon={PieChart} title="No spending" description="No expenses recorded for this month." />
          ) : (
            <div className="space-y-1">
              {rows.map(row => {
                const color = CATEGORY_COLORS[row.category] || '#888780'
                const active = selected === row.category
                return (
                  <button
                    key={row.category}
                    onClick={() => setSelected(row.category)}
                    className={`w-full text-left rounded-lg px-3 py-2.5 transition-colors ${
                      active ? 'bg-[#EEEDFE] dark:bg-[#534AB7]/20' : 'hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-700 dark:text-slate-200">{row.category}</span>
                      <span className="text-slate-600 dark:text-slate-300">
                        {fmt(row.total)} <span className="text-xs text-slate-400">· {row.count}</span>
                      </span>
                    </div>
                    <div className="mt-1.5 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-1.5 rounded-full"
                        style={{ width: `${max ? (row.total / max) * 100 : 0}%`, backgroundColor: color }}
                      />
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800">
          <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              {selected ? `${selected} transactions` : 'Transactions'}
            </h2>
          </div>
          {!selected ? (
            <p className="px-5 py-10 text-center text-sm text-slate-400">Select a category to see its transactions.</p>
          ) : txLoading ? (
            <LoadingSpinner className="py-10" />
          ) : transactions.length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-slate-400">No transactions in this category.</p>
          ) : (
            <div className="divide-y divide-slate-50 dark:divide-slate-800 max-h-[520px] overflow-y-auto">
              {transactions.map(tx => (
                <div key={tx.id} className="flex items-center gap-3 px-5 py-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
                      {tx.merchant_name || tx.description}
                    </p>
                    <p className="text-xs text-slate-400">{fmtDate(tx.timestamp)}</p>
                  </div>
                  <select
                    aria-label={`Category for ${tx.merchant_name || 'transaction'}`}
                    value={tx.category?.id ?? ''}
                    onChange={e => handleReassign(tx, e.target.value)}
                    className="rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#111111] px-2 py-1 text-xs text-slate-700 dark:text-slate-200"
                  >
                    {categories.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                  <span className="w-20 text-right text-sm font-medium text-slate-800 dark:text-slate-100">
                    {fmt(Math.abs(tx.amount))}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
