import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import apiClient from '../services/apiClient.js'
import authService from '../services/authService.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(apiClient.isAuthenticated())
  const [admin, setAdmin] = useState(apiClient.admin)
  const [authType, setAuthType] = useState(apiClient.getAuthType())
  const [isInitializing, setIsInitializing] = useState(true)

  const handleLogout = useCallback(async () => {
    await authService.logout()
    setIsAuthenticated(false)
    setAdmin(null)
    setAuthType(null)
  }, [])

  useEffect(() => {
    let isMounted = true

    const checkInitialSession = async () => {
      try {
        const valid = await authService.checkSession()
        if (isMounted) {
          setIsAuthenticated(valid)
          setAdmin(apiClient.admin)
          setAuthType(apiClient.getAuthType())
        }
      } catch (_) {
        if (isMounted) {
          setIsAuthenticated(false)
          setAdmin(null)
          setAuthType(null)
        }
      } finally {
        if (isMounted) {
          setIsInitializing(false)
        }
      }
    }

    checkInitialSession()

    // Lắng nghe sự kiện 401 Unauthorized từ apiClient
    const unsubscribe = apiClient.onUnauthorized(() => {
      if (isMounted) {
        setIsAuthenticated(false)
        setAdmin(null)
        setAuthType(null)
      }
    })

    return () => {
      isMounted = false
      unsubscribe()
    }
  }, [])

  const loginWithCredentials = async (username, password) => {
    const data = await authService.login(username, password)
    setIsAuthenticated(true)
    setAdmin(data.admin)
    setAuthType('token')
    return data
  }

  const connectWithApiKey = async (apiKey) => {
    await authService.verifyApiKey(apiKey)
    setIsAuthenticated(true)
    setAdmin({ full_name: 'Developer (API Key)', role: 'dev' })
    setAuthType('key')
    return true
  }

  const updateAdminProfile = async (payload) => {
    const updated = await authService.updateProfile(payload)
    setAdmin(updated)
    return updated
  }

  const role = admin?.role || (authType === 'key' ? 'dev' : null)
  const isSuperAdmin = Boolean(isAuthenticated && (role === 'admin' || role === 'dev' || authType === 'key'))
  const isOperator = Boolean(isAuthenticated && role === 'operator')
  const permissions = useMemo(() => {
    if (Array.isArray(admin?.permissions)) {
      return admin.permissions
    }
    if (isSuperAdmin) return ['*']
    if (isOperator) {
      return [
        'users:read',
        'users:search',
        'embeddings:read',
        'embeddings:create',
        'devices:read',
        'devices:search',
        'sessions:read',
        'sessions:search',
        'logs:read',
        'logs:search',
        'logs:export',
      ]
    }
    return []
  }, [admin?.permissions, isSuperAdmin, isOperator])

  const hasPermission = useCallback(
    (perm) => isSuperAdmin || permissions.includes('*') || permissions.includes(perm),
    [isSuperAdmin, permissions]
  )

  const value = {
    isAuthenticated,
    admin,
    role,
    isSuperAdmin,
    isOperator,
    permissions,
    hasPermission,
    authType,
    isInitializing,
    login: loginWithCredentials,
    connectApiKey: connectWithApiKey,
    updateProfile: updateAdminProfile,
    logout: handleLogout,
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

export default AuthProvider

