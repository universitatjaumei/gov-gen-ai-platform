/**
 * El hook de sesión, en su propio módulo (issue #47).
 *
 * **Falla en vez de devolver vacío** cuando se usa fuera del proveedor, y ésa es la decisión
 * que importa: un `useAuth` que devolviera `{user: null}` sin proveedor haría que la aplicación
 * se pintara como «sin sesión» en vez de decir que está mal montada, y eso se depura mirando el
 * sitio equivocado durante un buen rato.
 */
import { useContext } from 'react'

import { AuthContext, type AuthState } from './authState'

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
