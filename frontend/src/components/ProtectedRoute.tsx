// Route guard: redirects unauthenticated users to /auth (§5).
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../store/auth'

export default function ProtectedRoute() {
  const { user } = useAuth()
  const location = useLocation()
  if (!user) return <Navigate to="/auth" state={{ from: location }} replace />
  return <Outlet />
}
