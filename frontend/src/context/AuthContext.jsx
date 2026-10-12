import { createContext, useContext, useState } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  // Read synchronously so ProtectedRoute sees the user on the first render
  // (a hard refresh would otherwise bounce to /login)
  const [user, setUser] = useState(() => {
    try {
      const storedUser = localStorage.getItem('user')
      return storedUser && localStorage.getItem('token') ? JSON.parse(storedUser) : null
    } catch {
      return null
    }
  })

  const login = async (email, password) => {
    const response = await api.post('/auth/login', { email, password })
    const token = response.data.access_token
    localStorage.setItem('token', token)

    const meRes = await api.get('/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    setUser(meRes.data)
    localStorage.setItem('user', JSON.stringify(meRes.data))
    return meRes.data
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  const register = async (email, password) => {
    const response = await api.post('/auth/register', { email, password })
    if (response.status === 200) {
      await login(email, password)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
