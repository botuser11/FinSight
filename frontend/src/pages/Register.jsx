import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await register(email, password)
      navigate('/dashboard')
    } catch {
      toast.error('Registration failed. That email may already be in use.')
    } finally {
      setLoading(false)
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
            <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-50">Create account</h1>
          </div>
          <p className="text-sm text-slate-400 dark:text-slate-500 mb-6">Your finances, understood.</p>

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
                minLength={6}
                className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#111111] px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#534AB7] focus:border-transparent transition"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full rounded-lg bg-[#534AB7] hover:bg-[#3C3489] text-white text-sm font-semibold py-2.5 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="mt-5 text-center text-sm text-slate-500 dark:text-slate-400">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-[#534AB7] hover:text-[#3C3489]">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
