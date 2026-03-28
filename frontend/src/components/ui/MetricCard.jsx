const ACCENT_COLORS = {
  coral:  { border: '#D85A30', bg: '#FAECE7', text: '#D85A30' },
  teal:   { border: '#1D9E75', bg: '#E1F5EE', text: '#1D9E75' },
  indigo: { border: '#534AB7', bg: '#EEEDFE', text: '#534AB7' },
  amber:  { border: '#BA7517', bg: '#FAEEDA', text: '#BA7517' },
}

export default function MetricCard({ title, value, subtitle, icon: Icon, color = 'indigo', loading }) {
  const accent = ACCENT_COLORS[color]

  return (
    <div
      className="relative bg-white dark:bg-[#1A1A1A] rounded-xl border border-slate-100 dark:border-slate-800 p-5 overflow-hidden"
      style={{ borderLeft: `4px solid ${accent.border}` }}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
            {title}
          </p>
          {loading ? (
            <div className="mt-2 h-7 w-24 rounded bg-slate-100 dark:bg-slate-800 animate-pulse" />
          ) : (
            <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-50 truncate">
              {value}
            </p>
          )}
          {subtitle && (
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ml-3"
            style={{ backgroundColor: accent.bg }}
          >
            <Icon className="h-4 w-4" style={{ color: accent.text }} />
          </div>
        )}
      </div>
    </div>
  )
}
