import { ChevronLeft, ChevronRight, Moon, Sun } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useTheme } from '../../context/ThemeContext'

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export default function TopBar() {
  const { user } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [searchParams, setSearchParams] = useSearchParams()

  const now = new Date()
  const month = parseInt(searchParams.get('month') || now.getMonth() + 1)
  const year = parseInt(searchParams.get('year') || now.getFullYear())

  const setMonthYear = (newMonth, newYear) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('month', newMonth)
      next.set('year', newYear)
      return next
    })
  }

  const prevMonth = () => {
    if (month === 1) setMonthYear(12, year - 1)
    else setMonthYear(month - 1, year)
  }

  const nextMonth = () => {
    if (month === 12) setMonthYear(1, year + 1)
    else setMonthYear(month + 1, year)
  }

  return (
    <header className="flex items-center justify-between px-6 py-3.5 border-b border-slate-100 dark:border-slate-800 bg-white dark:bg-[#0F0F0F]">
      <div />

      <div className="flex items-center gap-4">
        {/* Month selector */}
        <div className="flex items-center gap-1">
          <button
            onClick={prevMonth}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 min-w-[130px] text-center">
            {MONTH_NAMES[month - 1]} {year}
          </span>
          <button
            onClick={nextMonth}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        {/* Dark mode toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* User */}
        {user && (
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-full bg-[#EEEDFE] dark:bg-[#534AB7]/30 flex items-center justify-center">
              <span className="text-xs font-semibold text-[#534AB7]">
                {user.email[0].toUpperCase()}
              </span>
            </div>
            <span className="text-sm text-slate-600 dark:text-slate-400 max-w-[160px] truncate hidden sm:block">
              {user.email}
            </span>
          </div>
        )}
      </div>
    </header>
  )
}
