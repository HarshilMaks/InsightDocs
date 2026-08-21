import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  AUTH_SESSION_EXPIRED_EVENT,
  clearStoredAuth,
  getStoredAuth,
  googleLogin,
  loginUser,
  persistAuth,
  registerUser,
  type StoredAuth,
} from '@/lib/api'

interface AuthContextValue {
  user: StoredAuth['user'] | null
  accessToken: string | null
  isAuthenticated: boolean
  login: (payload: { email: string; password: string }) => Promise<StoredAuth['user']>
  loginWithGoogle: (credential: string) => Promise<StoredAuth['user']>
  register: (payload: { name: string; email: string; password: string }) => Promise<StoredAuth['user']>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<StoredAuth | null>(() => getStoredAuth())

  useEffect(() => {
    const handleSessionExpired = () => setAuth(null)
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, handleSessionExpired)
    return () => window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, handleSessionExpired)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user: auth?.user ?? null,
      accessToken: auth?.accessToken ?? null,
      isAuthenticated: Boolean(auth?.accessToken),
      login: async (payload) => {
        const response = await loginUser(payload)
        const nextAuth: StoredAuth = {
          accessToken: response.access_token ?? response.token?.access_token,
          user: response.user,
        }
        persistAuth(nextAuth)
        setAuth(nextAuth)
        return response.user
      },
      loginWithGoogle: async (credential) => {
        const response = await googleLogin(credential)
        const nextAuth: StoredAuth = {
          accessToken: response.access_token ?? response.token?.access_token,
          user: response.user,
        }
        persistAuth(nextAuth)
        setAuth(nextAuth)
        return response.user
      },
      register: async (payload) => {
        const user = await registerUser(payload)
        return user
      },
      logout: () => {
        clearStoredAuth()
        setAuth(null)
      },
    }),
    [auth],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
