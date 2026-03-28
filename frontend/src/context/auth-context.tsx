import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { clearStoredAuth, getStoredAuth, loginUser, persistAuth, registerUser } from '@/lib/api'
import type { LoginPayload, RegisterPayload, StoredAuth, User } from '@/types'

interface AuthContextValue {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  login: (payload: LoginPayload) => Promise<User>
  register: (payload: RegisterPayload) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<StoredAuth | null>(() => getStoredAuth())

  const value = useMemo<AuthContextValue>(
    () => ({
      user: auth?.user ?? null,
      accessToken: auth?.accessToken ?? null,
      isAuthenticated: Boolean(auth?.accessToken),
      login: async (payload: LoginPayload) => {
        const response = await loginUser(payload)
        const nextAuth: StoredAuth = {
          accessToken: response.access_token ?? response.token.access_token,
          refreshToken: response.refresh_token ?? response.token.refresh_token,
          user: response.user,
        }
        persistAuth(nextAuth)
        setAuth(nextAuth)
        return response.user
      },
      register: async (payload: RegisterPayload) => {
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
