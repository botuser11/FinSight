import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

// Cold start: the free-tier backend sleeps. The first request gets a generous
// timeout, and if it takes >3s subscribers are told the server is waking up.
let warmedUp = false
let firstRequestPending = false
let wakeTimer = null
const wakeListeners = new Set()

export const onServerWaking = (listener) => {
  wakeListeners.add(listener)
  return () => wakeListeners.delete(listener)
}

const setWaking = (waking) => wakeListeners.forEach((l) => l(waking))

const markWarm = () => {
  if (!firstRequestPending) return
  firstRequestPending = false
  warmedUp = true
  clearTimeout(wakeTimer)
  setWaking(false)
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (!warmedUp && !firstRequestPending) {
    firstRequestPending = true
    config.timeout = 90000
    wakeTimer = setTimeout(() => setWaking(true), 3000)
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    markWarm()
    return response
  },
  (error) => {
    if (error.response) {
      markWarm()
    } else if (firstRequestPending) {
      // Network error/timeout: let the next request retry with the long timeout
      firstRequestPending = false
      clearTimeout(wakeTimer)
      setWaking(false)
    }
    // A failed login is a normal 401: let the login page show its error toast
    const isLoginRequest = error.config?.url === '/auth/login'
    if (error.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
