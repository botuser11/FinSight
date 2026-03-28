import { useEffect, useState } from 'react'
import { NavLink, useNavigate, useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeftRight,
  LayoutDashboard,
  LogOut,
  PieChart,
  PiggyBank,
  TrendingUp,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { getAccounts } from '../../api/banking'

const NAV_ITEMS = [
  { to: '/dashboard',     label: 'Dashboard',     Icon: LayoutDashboard },
  { to: '/transactions',  label: 'Transactions',  Icon: ArrowLeftRight },
  { to: '/categories',    label: 'Categories',    Icon: PieChart },
  { to: '/forecast',      label: 'Forecast',      Icon: TrendingUp },
  { to: '/anomalies',     label: 'Anomalies',     Icon: AlertTriangle },
  { to: '/savings',       label: 'Savings',       Icon: PiggyBank },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [accounts, setAccounts] = useState([])

  useEffect(() => {
    getAccounts()
      .then(r => setAccounts(r.data))
      .catch(() => {})
  }, [])

  const monthYearQuery = searchParams.toString() ? `?${searchParams.toString()}` : ''

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="fixed left-0 top-0 h-full w-[220px] bg-white dark:bg-[#111111] border-r border-slate-100 dark:border-slate-800 flex flex-col z-30">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-slate-100 dark:border-slate-800">
        <div className="h-7 w-7 rounded-lg bg-[#534AB7] flex items-center justify-center shrink-0">
          <span className="text-white text-xs font-bold">F</span>
        </div>
        <span className="text-base font-semibold text-slate-900 dark:text-slate-50">FinSight</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={`${to}${monthYearQuery}`}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-[#EEEDFE] dark:bg-[#534AB7]/20 text-[#534AB7] dark:text-[#534AB7] border-l-2 border-[#534AB7] -ml-px pl-[11px]'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Bank status */}
      <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800">
        {accounts.length > 0 ? (
          <div
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#E1F5EE] dark:bg-[#1D9E75]/10"
            title={accounts[0].display_name || 'Bank connected'}
          >
            <span className="h-2 w-2 rounded-full bg-[#1D9E75] shrink-0" />
            <span className="text-xs font-medium text-[#1D9E75] truncate flex-1 min-w-0">
              {accounts[0].display_name || 'Bank connected'}
            </span>
            <Wifi className="h-3 w-3 text-[#1D9E75] shrink-0" />
          </div>
        ) : (
          <NavLink
            to="/dashboard"
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-[#EEEDFE] dark:hover:bg-[#534AB7]/20 hover:text-[#534AB7] transition-all"
          >
            <WifiOff className="h-3.5 w-3.5 shrink-0" />
            <span className="text-xs font-medium">Connect bank</span>
          </NavLink>
        )}
      </div>

      {/* Logout */}
      <div className="px-4 pb-4">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-500 dark:text-slate-400 hover:bg-red-50 dark:hover:bg-red-900/10 hover:text-red-600 dark:hover:text-red-400 transition-all"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Logout
        </button>
      </div>
    </aside>
  )
}
