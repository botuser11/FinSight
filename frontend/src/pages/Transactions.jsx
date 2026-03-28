import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { RefreshCw, Search, Tag, X } from 'lucide-react'
import { syncTransactions } from '../api/banking'
import { categoriseAll, getCategories, updateCategory } from '../api/transactions'
import useTransactions from '../hooks/useTransactions'
import CategoryBadge from '../components/ui/CategoryBadge'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'
import { AlertTriangle, ArrowLeftRight } from 'lucide-react'

const fmt = (amount) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(amount)

const fmtDate = (ts) =>
  new Date(ts).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

const FILTERS = [
  { key: 'all',       label: 'All' },
  { key: 'expenses',  label: 'Expenses' },
  { key: 'income',    label: 'Income' },
  { key: 'anomalies', label: 'Anomalies' },
]

function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 px-5 py-3.5 animate-pulse">
      <div className="flex-1 space-y-1.5">
        <div className="h-3.5 w-36 rounded bg-slate-100 dark:bg-slate-800" />
        <div className="h-3 w-24 rounded bg-slate-100 dark:bg-slate-800" />
      </div>
      <div className="h-5 w-20 rounded-full bg-slate-100 dark:bg-slate-800" />
      <div className="h-3 w-16 rounded bg-slate-100 dark:bg-slate-800" />
      <div className="h-4 w-16 rounded bg-slate-100 dark:bg-slate-800 ml-auto" />
    </div>
  )
}

export default function Transactions() {
  const [searchParams] = useSearchParams()
  const now = new Date()
  const month = parseInt(searchParams.get('month') || now.getMonth() + 1)
  const year = parseInt(searchParams.get('year') || now.getFullYear())

  const [activeFilter, setActiveFilter] = useState('all')
  const [activeCategoryId, setActiveCategoryId] = useState(null)
  const [searchRaw, setSearchRaw] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [categories, setCategories] = useState([])
  const [editingTxId, setEditingTxId] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [categorising, setCategorising] = useState(false)
  const dropdownRef = useRef(null)

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setSearch(searchRaw), 300)
    return () => clearTimeout(t)
  }, [searchRaw])

  // Reset page on filter change
  useEffect(() => { setPage(1) }, [activeFilter, activeCategoryId, search, month, year])

  // Fetch categories for dropdown
  useEffect(() => {
    getCategories()
      .then(r => setCategories(r.data))
      .catch(() => {})
  }, [])

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setEditingTxId(null)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Build API params
  const params = { month, year, page, page_size: 20 }
  if (activeFilter === 'anomalies') params.is_anomaly = true
  if (activeCategoryId) params.category_id = activeCategoryId
  if (search) params.search = search

  const { transactions: rawTxs, total, loading } = useTransactions(params)

  // Client-side income/expense filter (no backend param needed for these)
  const transactions = rawTxs.filter(tx => {
    if (activeFilter === 'expenses') return tx.amount < 0
    if (activeFilter === 'income') return tx.amount > 0
    return true
  })

  const totalPages = Math.ceil(total / 20)

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

  const handleCategoryChange = async (tx, categoryId) => {
    const prev = tx.category
    setEditingTxId(null)
    try {
      await updateCategory(tx.id, categoryId)
      toast.success('Category updated.')
      window.location.reload()
    } catch {
      toast.error('Failed to update category.')
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Transactions</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCategorise}
            disabled={categorising}
            className="flex items-center gap-1.5 rounded-lg border border-[#534AB7] text-[#534AB7] text-xs font-medium px-3 py-1.5 hover:bg-[#EEEDFE] dark:hover:bg-[#534AB7]/10 transition-colors disabled:opacity-50"
          >
            <Tag className="h-3.5 w-3.5" />
            Categorise
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

      {/* Search + filters */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 px-4 py-3 space-y-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            value={searchRaw}
            onChange={e => setSearchRaw(e.target.value)}
            placeholder="Search merchant or description…"
            className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-[#111111] pl-8 pr-8 py-2 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#534AB7] focus:border-transparent"
          />
          {searchRaw && (
            <button
              onClick={() => setSearchRaw('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Filter chips */}
        <div className="flex items-center gap-2 flex-wrap">
          {FILTERS.map(f => (
            <button
              key={f.key}
              onClick={() => { setActiveFilter(f.key); setActiveCategoryId(null) }}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                activeFilter === f.key && !activeCategoryId
                  ? 'bg-[#534AB7] text-white'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {f.label}
            </button>
          ))}

          <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 mx-1" />

          {/* Category filter chips */}
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => {
                setActiveFilter('all')
                setActiveCategoryId(activeCategoryId === cat.id ? null : cat.id)
              }}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                activeCategoryId === cat.id
                  ? 'text-white'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
              style={activeCategoryId === cat.id ? { backgroundColor: cat.color_hex || '#534AB7' } : {}}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 overflow-hidden">
        {/* Table header */}
        <div className="grid grid-cols-[1fr_140px_100px_90px] gap-2 px-5 py-2.5 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-[#111111]">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Merchant</span>
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Category</span>
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Date</span>
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide text-right">Amount</span>
        </div>

        {loading ? (
          <div className="divide-y divide-slate-50 dark:divide-slate-800">
            {Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)}
          </div>
        ) : transactions.length === 0 ? (
          <EmptyState
            icon={ArrowLeftRight}
            title="No transactions found"
            description="Try adjusting your filters or syncing your bank account."
          />
        ) : (
          <div className="divide-y divide-slate-50 dark:divide-slate-800" ref={dropdownRef}>
            {transactions.map(tx => (
              <div
                key={tx.id}
                className={`relative grid grid-cols-[1fr_140px_100px_90px] gap-2 items-center px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors ${
                  tx.is_anomaly
                    ? 'border-l-2 border-l-[#BA7517] bg-[#FAEEDA]/10 dark:bg-[#BA7517]/5'
                    : ''
                }`}
              >
                {/* Merchant */}
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
                      {tx.merchant_name || tx.description || 'Unknown'}
                    </span>
                    {tx.is_anomaly && (
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-[#BA7517]" />
                    )}
                  </div>
                  {tx.merchant_name && tx.description && (
                    <p className="text-xs text-slate-400 truncate">{tx.description}</p>
                  )}
                </div>

                {/* Category (clickable) */}
                <div className="relative">
                  <CategoryBadge
                    name={tx.category?.name}
                    onClick={() => setEditingTxId(editingTxId === tx.id ? null : tx.id)}
                  />
                  {editingTxId === tx.id && (
                    <div className="absolute top-full left-0 mt-1 z-50 bg-white dark:bg-[#1A1A1A] border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl py-1 w-44">
                      {categories.map(cat => (
                        <button
                          key={cat.id}
                          onClick={() => handleCategoryChange(tx, cat.id)}
                          className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-left"
                        >
                          <span
                            className="h-2 w-2 rounded-full shrink-0"
                            style={{ backgroundColor: cat.color_hex || '#888780' }}
                          />
                          {cat.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Date */}
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {fmtDate(tx.timestamp)}
                </span>

                {/* Amount */}
                <span
                  className={`text-sm font-semibold text-right ${
                    tx.amount > 0 ? 'text-[#1D9E75]' : 'text-[#D85A30]'
                  }`}
                >
                  {tx.amount > 0 ? '+' : ''}{fmt(tx.amount)}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Page {page} of {totalPages} ({total} total)
            </span>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
