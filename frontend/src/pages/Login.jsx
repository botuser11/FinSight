import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'

const DEMO_EMAIL = 'demo@finsight.app'
const DEMO_PASSWORD = 'demo1234'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch {
      toast.error('Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  const handleDemo = async () => {
    setDemoLoading(true)
    try {
      await login(DEMO_EMAIL, DEMO_PASSWORD)
      navigate('/dashboard')
    } catch {
      toast.error('Could not sign in to the demo. Please try again.')
    } finally {
      setDemoLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#EEEDFE] via-white to-white dark:from-[#0F0F0F] dark:via-[#111111] dark:to-[#0F0F0F] p-6">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="h-9 w-9 rounded-xl bg-[#534AB7] flex items-center justify-center">
            <span className="text-white text-sm font-bold">F</span>
          </div>
          <div>
            <div className="text-lg font-bold text-slate-900 dark:text-slate-50 leading-none">FinSight</div>
            <div className="text-xs text-slate-400 leading-none mt-0.5">Your finances, understood.</div>
          </div>
        </div>

        <div className="bg-white dark:bg-[#1A1A1A] rounded-2xl shadow-lg border border-slate-100 dark:border-slate-800 p-8">
          <div className="flex items-center gap-2.5 mb-1">
            <div className="h-7 w-7 rounded-lg bg-[#534AB7] flex items-center justify-center shrink-0">
              <span className="text-white text-xs font-bold">F</span>
            </div>
            <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Sign in</h1>
          </div>
          <p className="text-sm text-slate-400 dark:text-slate-500 mb-6">Your finances, understood.</p>

          <button
            type="button"
            onClick={handleDemo}
            disabled={demoLoading || loading}
            className="w-full rounded-lg bg-[#1D9E75] hover:bg-[#17805f] text-white text-sm font-semibold py-2.5 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {demoLoading ? 'Opening demo…' : 'Try the demo'}
          </button>
          <p className="mt-2 text-center text-xs text-slate-400 dark:text-slate-500">
            One click, no sign-up. Uses 12 months of sample data.
          </p>

          <div className="flex items-center gap-3 my-5">
            <div className="h-px flex-1 bg-slate-100 dark:bg-slate-800" />
            <span className="text-xs text-slate-400 dark:text-slate-500">or sign in</span>
            <div className="h-px flex-1 bg-slate-100 dark:bg-slate-800" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#111111] px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#534AB7] focus:border-transparent transition"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#111111] px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#534AB7] focus:border-transparent transition"
              />
            </div>

            <button
              type="submit"
              disabled={loading || demoLoading}
              className="mt-2 w-full rounded-lg bg-[#534AB7] hover:bg-[#3C3489] text-white text-sm font-semibold py-2.5 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="mt-5 text-center text-sm text-slate-500 dark:text-slate-400">
            No account?{' '}
            <Link to="/register" className="font-medium text-[#534AB7] hover:text-[#3C3489]">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
