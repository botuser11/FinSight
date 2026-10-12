import { useEffect, useState } from 'react'
import api, { onServerWaking } from '../api/client'

export default function ServerWakeNotice() {
  const [waking, setWaking] = useState(false)

  useEffect(() => {
    const unsubscribe = onServerWaking(setWaking)
    // Start waking the backend as soon as the app loads
    api.get('/health').catch(() => {})
    return unsubscribe
  }, [])

  if (!waking) return null

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] max-w-md">
      <div className="flex items-start gap-3 rounded-xl border border-[#534AB7]/20 bg-white dark:bg-[#1A1A1A] shadow-lg px-4 py-3">
        <div className="mt-0.5 h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-slate-200 border-t-[#534AB7] dark:border-slate-700 dark:border-t-[#534AB7]" />
        <div>
          <div className="text-sm font-medium text-slate-900 dark:text-slate-50">
            Waking up the server (free hosting), ~30–60s
          </div>
          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            The backend sleeps when idle. It'll be quick once it's up.
          </div>
        </div>
      </div>
    </div>
  )
}
