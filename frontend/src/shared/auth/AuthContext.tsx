import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export interface AuthUser {
  user_id: string
  email: string
  role: string
}

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  login: (token: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

const TOKEN_KEY = 'access_token'

function parseJwtPayload(token: string): AuthUser | null {
  try {
    const base64 = token.split('.')[1]
    const json = atob(base64.replace(/-/g, '+').replace(/_/g, '/'))
    const payload = JSON.parse(json) as Record<string, unknown>
    const { user_id, email, role } = payload
    if (typeof user_id !== 'string' || typeof email !== 'string' || typeof role !== 'string') {
      return null
    }
    return { user_id, email, role }
  } catch {
    return null
  }
}

function loadStoredUser(): AuthUser | null {
  const token = localStorage.getItem(TOKEN_KEY)
  return token ? parseJwtPayload(token) : null
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(loadStoredUser)

  const login = useCallback((token: string) => {
    const parsed = parseJwtPayload(token)
    if (parsed) {
      localStorage.setItem(TOKEN_KEY, token)
      setUser(parsed)
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: user !== null, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
