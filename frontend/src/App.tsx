import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './store/auth'
import Splash from './components/Splash'
import DashboardLayout from './layouts/DashboardLayout'
import ProtectedRoute from './components/ProtectedRoute'

// Lazy-loaded pages for code splitting (§65).
import { lazy, Suspense } from 'react'

const AuthPage = lazy(() => import('./pages/AuthPage'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Discover = lazy(() => import('./pages/Discover'))
const Trending = lazy(() => import('./pages/Trending'))
const Categories = lazy(() => import('./pages/Categories'))
const CreateDebate = lazy(() => import('./pages/CreateDebate'))
const DebateDetail = lazy(() => import('./pages/DebateDetail'))
const MyDebates = lazy(() => import('./pages/MyDebates'))
const Wallet = lazy(() => import('./pages/Wallet'))
const Notifications = lazy(() => import('./pages/Notifications'))
const Games = lazy(() => import('./pages/Games'))
const Settings = lazy(() => import('./pages/Settings'))
const Profile = lazy(() => import('./pages/Profile'))
const About = lazy(() => import('./pages/About'))
const Contact = lazy(() => import('./pages/Contact'))
const Help = lazy(() => import('./pages/Help'))
const Admin = lazy(() => import('./pages/Admin'))
const JoinDebate = lazy(() => import('./pages/JoinDebate'))
const Onboarding = lazy(() => import('./pages/Onboarding'))

function Loading() {
  return <div className="center muted" style={{ padding: 40 }}>Loading…</div>
}

export default function App() {
  const { initialized, loadUser } = useAuth()
  const [showSplash, setShowSplash] = useState(true)

  useEffect(() => {
    // Splash: DS blinks three times then transitions (§4).
    const t = setTimeout(() => setShowSplash(false), 1900)
    loadUser()
    return () => clearTimeout(t)
  }, [loadUser])

  if (showSplash) return <Splash />
  if (!initialized) return <Loading />

  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/join/:token" element={<JoinDebate />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<DashboardLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/discover" element={<Discover />} />
            <Route path="/trending" element={<Trending />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/create" element={<CreateDebate />} />
            <Route path="/debates/:id" element={<DebateDetail />} />
            <Route path="/my-debates" element={<MyDebates />} />
            <Route path="/wallet" element={<Wallet />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/games" element={<Games />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/help" element={<Help />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/welcome" element={<Onboarding />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
