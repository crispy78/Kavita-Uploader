import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getCurrentUser, login as apiLogin, logout as apiLogout } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authEnabled, setAuthEnabled] = useState(false)
  const [requireAuth, setRequireAuth] = useState(false)

  const checkAuth = useCallback(async () => {
    try {
      const response = await getCurrentUser()
      if (response.authenticated) {
        setUser(response.user)
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error('Failed to check auth:', error)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  // Load current session on mount
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = async (username, password) => {
    try {
      const response = await apiLogin(username, password)
      if (response.success) {
        setUser(response.user)
        return { success: true, user: response.user }
      }
      return { success: false, error: response.message || 'Login failed' }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || 'Login failed'
      return { success: false, error: errorMsg }
    }
  }

  const logout = async () => {
    try {
      await apiLogout()
      setUser(null)
      return { success: true }
    } catch (error) {
      console.error('Logout error:', error)
      // Clear user even if API call fails
      setUser(null)
      return { success: true }
    }
  }

  const value = {
    user,
    loading,
    authEnabled,
    requireAuth,
    setAuthEnabled,
    setRequireAuth,
    login,
    logout,
    checkAuth,
    isAuthenticated: !!user,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

