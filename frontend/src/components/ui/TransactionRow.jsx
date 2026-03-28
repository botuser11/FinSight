import { AlertTriangle } from 'lucide-react'
import CategoryBadge from './CategoryBadge'

const fmt = (amount) =>
  new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(amount)

const fmtDate = (ts) =>
  new Date(ts).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })

export default function TransactionRow({ tx, onCategoryClick }) {
  const isPositive = tx.amount > 0

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors ${
        tx.is_anomaly ? 'border-l-2 border-l-[#BA7517] bg-[#FAEEDA]/20 dark:bg-[#BA7517]/5' : ''
      }`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
            {tx.merchant_name || tx.description || 'Unknown'}
          </span>
          {tx.is_anomaly && (
            <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-[#BA7517]" />
          )}
        </div>
        <p className="text-xs text-slate-400 dark:text-slate-500 truncate mt-0.5">
          {tx.description && tx.merchant_name ? tx.description : ''}
        </p>
      </div>

      <CategoryBadge
        name={tx.category?.name}
        onClick={onCategoryClick ? () => onCategoryClick(tx) : undefined}
      />

      <span className="text-xs text-slate-400 dark:text-slate-500 w-16 text-right shrink-0">
        {fmtDate(tx.timestamp)}
      </span>

      <span
        className={`text-sm font-semibold w-20 text-right shrink-0 ${
          isPositive ? 'text-[#1D9E75]' : 'text-[#D85A30]'
        }`}
      >
        {isPositive ? '+' : ''}{fmt(tx.amount)}
      </span>
    </div>
  )
}
