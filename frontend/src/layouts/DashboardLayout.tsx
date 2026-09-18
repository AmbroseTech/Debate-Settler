// Dashboard shell: header, sidebar, responsive drawer + bottom nav (§7, §77).
import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../store/auth'
import { notificationsApi, walletApi } from '../api/client'
import { formatMoney } from '../utils/format'

const NAV = [
  { to: '/', label: 'Home', icon: '🏠', end: true },
  { to: '/discover', label: 'Discover Debates', icon: '🔎' },
  { to: '/create', label: 'Create Debate', icon: '➕' },
  { to: '/trending', label: 'Trending', icon: '🔥' },
  { to: '/categories', label: 'Categories', icon: '🗂️' },
  { to: '/my-debates', label: 'My Debates', icon: '📋' },
  { to: '/notifications', label: 'Notifications', icon: '🔔' },
  { to: '/wallet', label: 'Wallet', icon: '💳' },
  { to: '/games', label: 'Games', icon: '🎮' },
]
const FOOTER_NAV = [
  { to: '/profile', label: 'Profile', icon: '👤' },
  { to: '/settings', label: 'Settings', icon: '⚙️' },
  { to: '/about', label: 'About', icon: 'ℹ️' },
  { to: '/contact', label: 'Contact', icon: '✉️' },
  { to: '/help', label: 'Help', icon: '❓' },
]

const MOBILE_NAV = [
  { to: '/', label: 'Home', icon: '🏠' },
  { to: '/discover', label: 'Discover', icon: '🔎' },
  { to: '/create', label: 'Create', icon: '➕' },
  { to: '/wallet', label: 'Wallet', icon: '💳' },
  { to: '/notifications', label: 'Alerts', icon: '🔔' },
]

export default function DashboardLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  const { data: wallet } = useQuery({ queryKey: ['wallet'], queryFn: walletApi.get })
  const { data: notifications } = useQuery({ queryKey: ['notifications'], queryFn: notificationsApi.list })
  const unread = (notifications ?? []).filter((n) => !n.read).length

  useEffect(() => { setDrawerOpen(false) }, [])

  const isAdmin = user?.role === 'admin' || user?.role === 'moderator'

  return (
    <div className="app-shell">
      {drawerOpen && <div className="backdrop" onClick={() => setDrawerOpen(false)} />}
      <aside className={`sidebar ${drawerOpen ? 'open' : ''}`} aria-label="Main navigation">
        <div className="row" style={{ padding: '0 12px 16px' }}>
          <span style={{ fontWeight: 800, fontSize: '1.3rem', letterSpacing: '0.05em' }}>DS</span>
          <span className="dim" style={{ fontSize: '0.8rem' }}>Debate_Settler</span>
        </div>
        <nav>
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span aria-hidden="true">{item.icon}</span> {item.label}
              {item.to === '/notifications' && unread > 0 && (
                <span className="badge" style={{ marginLeft: 'auto', background: 'var(--danger)', color: '#fff', borderColor: 'transparent' }}>{unread}</span>
              )}
            </NavLink>
          ))}
          {isAdmin && (
            <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span aria-hidden="true">🛡️</span> Admin
            </NavLink>
          )}
          <div className="nav-section">Account</div>
          {FOOTER_NAV.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span aria-hidden="true">{item.icon}</span> {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="btn btn-ghost menu-toggle" onClick={() => setDrawerOpen(true)} aria-label="Open menu">☰</button>
          <Link to="/" style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--text)' }}>DS</Link>

          <form
            className="grow"
            style={{ maxWidth: 360 }}
            onSubmit={(e) => {
              e.preventDefault()
              const q = new FormData(e.currentTarget).get('q') as string
              if (q) navigate(`/discover?q=${encodeURIComponent(q)}`)
            }}
            role="search"
          >
            <input className="input" name="q" placeholder="Search debates…" aria-label="Search debates" />
          </form>

          <div className="row" style={{ marginLeft: 'auto' }}>
            {wallet && (
              <Link to="/wallet" className="badge" title="Wallet balance">
                💳 {formatMoney(wallet.available_balance, wallet.currency)}
              </Link>
            )}
            <Link to="/notifications" className="btn btn-ghost btn-sm" aria-label={`Notifications, ${unread} unread`}>
              🔔{unread > 0 && <span className="badge" style={{ background: 'var(--danger)', color: '#fff', borderColor: 'transparent', marginLeft: 4 }}>{unread}</span>}
            </Link>
            <div style={{ position: 'relative' }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setMenuOpen((o) => !o)} aria-haspopup="menu" aria-expanded={menuOpen}>
                👤 {user?.username}
              </button>
              {menuOpen && (
                <div className="card" style={{ position: 'absolute', right: 0, top: '110%', minWidth: 180, padding: 8, zIndex: 30 }} role="menu">
                  <Link className="nav-item" to="/profile" role="menuitem">👤 Profile</Link>
                  <Link className="nav-item" to="/settings" role="menuitem">⚙️ Settings</Link>
                  <Link className="nav-item" to="/help" role="menuitem">❓ Help</Link>
                  <button
                    className="nav-item"
                    role="menuitem"
                    style={{ color: 'var(--danger)' }}
                    onClick={() => { logout(); navigate('/auth') }}
                  >
                    🚪 Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>

        <nav className="mobile-nav" aria-label="Mobile navigation">
          {MOBILE_NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
