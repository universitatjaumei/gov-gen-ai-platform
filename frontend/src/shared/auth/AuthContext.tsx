/**
 * El proveedor de sesión, y sólo él (issue #47).
 *
 * El contexto, los tipos y el troceado del token están en `authState.ts`, y el hook en
 * `useAuth.ts`. El corte es por Fast Refresh: un fichero que exporta componentes **y otra cosa**
 * remonta el árbol entero en cada cambio, y se pierde el estado de la pantalla. Quien consume
 * esto entra por `@/shared/auth`, así que el reparto no se nota desde fuera.
 */
import { useState, useCallback, type ReactNode } from 'react'

import { AuthContext, TOKEN_KEY, loadStoredUser, parseJwtPayload, type AuthUser } from './authState'

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
