import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'

export function PrivateRoute() {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to={`/login?from=${encodeURIComponent(location.pathname)}`} replace />
  }

  return <Outlet />
}
