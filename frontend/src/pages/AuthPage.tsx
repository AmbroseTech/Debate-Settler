// Auth page: Register / Sign In / Forgot / Reset, with Terms popup (§5, §6).
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { authApi, friendlyError } from '../api/client'
import { Field, Modal } from '../components/ui'

type Mode = 'signin' | 'register' | 'forgot' | 'reset'

const TERMS = [
  'You must follow the platform rules and treat other users with respect.',
  'Some debates may involve real financial stakes where legally permitted.',
  'The platform fee is clearly displayed before any financial commitment.',
  'Results and settlements follow the agreed debate rules and settlement source.',
  'You must be eligible to use financial/gaming features in your jurisdiction.',
]

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>('signin')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [termsOpen, setTermsOpen] = useState(false)
  const [pendingRegister, setPendingRegister] = useState<Record<string, unknown> | null>(null)
  const { login, register, loading } = useAuth()
  const navigate = useNavigate()

  // Register form state
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [agreeTerms, setAgreeTerms] = useState(false)
  const [usernameStatus, setUsernameStatus] = useState<'' | 'checking' | 'free' | 'taken'>('')

  // Signin form state
  const [identifier, setIdentifier] = useState('')
  const [signinPassword, setSigninPassword] = useState('')

  // Reset state
  const [resetEmail, setResetEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')

  async function checkUsername(value: string) {
    setUsername(value)
    if (value.length < 3) { setUsernameStatus(''); return }
    setUsernameStatus('checking')
    try {
      const { available } = await authApi.usernameCheck(value)
      setUsernameStatus(available ? 'free' : 'taken')
    } catch {
      setUsernameStatus('')
    }
  }

  function onSubmitRegister(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!agreeTerms) { setTermsOpen(true); return }
    if (password !== confirm) { setError('Passwords do not match.'); return }
    if (usernameStatus === 'taken') { setError('That username is already taken.'); return }
    setPendingRegister({ username, email, password, confirm_password: confirm, accept_terms: true })
    setTermsOpen(true)
  }

  async function doRegister() {
    if (!pendingRegister) return
    setTermsOpen(false)
    try {
      await register(pendingRegister)
      navigate('/welcome')
    } catch (err) {
      setError(friendlyError(err))
    }
  }

  async function onSubmitSignin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await login(identifier, signinPassword)
      navigate('/')
    } catch (err) {
      setError(friendlyError(err, 'Incorrect username/email or password.'))
    }
  }

  async function onSubmitForgot(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const res = await authApi.forgotPassword(resetEmail)
      setInfo(res.message)
      setMode('reset')
    } catch (err) {
      setError(friendlyError(err))
    }
  }

  async function onSubmitReset(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await authApi.resetPassword(resetToken, newPassword)
      setInfo('Password reset. You can now sign in.')
      setMode('signin')
    } catch (err) {
      setError(friendlyError(err))
    }
  }

  return (
    <div className="auth-wrap">
      <div style={{ fontWeight: 800, fontSize: '2rem', letterSpacing: '0.1em', marginBottom: 8 }}>DS</div>
      <div className="card auth-card">
        <h2 style={{ textAlign: 'center' }}>
          {mode === 'signin' && 'Sign in'}
          {mode === 'register' && 'Create your account'}
          {mode === 'forgot' && 'Reset your password'}
          {mode === 'reset' && 'Choose a new password'}
        </h2>

        {error && <div className="error-text" role="alert" style={{ marginBottom: 12 }}>{error}</div>}
        {info && <div className="help-text" style={{ marginBottom: 12, color: 'var(--success)' }}>{info}</div>}

        {mode === 'signin' && (
          <form onSubmit={onSubmitSignin}>
            <Field label="Username or email">
              <input className="input" value={identifier} onChange={(e) => setIdentifier(e.target.value)} required autoComplete="username" />
            </Field>
            <Field label="Password">
              <input className="input" type="password" value={signinPassword} onChange={(e) => setSigninPassword(e.target.value)} required autoComplete="current-password" />
            </Field>
            <button className="btn btn-primary btn-block" disabled={loading}>{loading ? 'Signing in…' : 'Sign In'}</button>
            <div className="row-between mt-2" style={{ fontSize: '0.85rem' }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setMode('forgot'); setError(''); setInfo('') }}>Forgot password?</button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setMode('register'); setError(''); setInfo('') }}>Create account</button>
            </div>
          </form>
        )}

        {mode === 'register' && (
          <form onSubmit={onSubmitRegister}>
            <Field
              label="Username"
              hint="Letters, numbers, dots, dashes and underscores."
              error={usernameStatus === 'taken' ? 'That username is taken.' : ''}
            >
              <input className="input" value={username} onChange={(e) => checkUsername(e.target.value)} required minLength={3} autoComplete="username" />
              {usernameStatus === 'checking' && <div className="help-text">Checking availability…</div>}
              {usernameStatus === 'free' && <div className="help-text" style={{ color: 'var(--success)' }}>✓ Available</div>}
            </Field>
            <Field label="Email">
              <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
            </Field>
            <Field label="Password" hint="At least 8 characters.">
              <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" />
            </Field>
            <Field label="Confirm password">
              <input className="input" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required autoComplete="new-password" />
            </Field>
            <label className="row" style={{ alignItems: 'flex-start', gap: 8, marginBottom: 16, fontSize: '0.85rem' }}>
              <input type="checkbox" checked={agreeTerms} onChange={(e) => setAgreeTerms(e.target.checked)} style={{ marginTop: 3 }} />
              <span>I agree to the <button type="button" className="btn btn-ghost btn-sm" style={{ padding: 0 }} onClick={() => setTermsOpen(true)}>Terms and Conditions</button></span>
            </label>
            <button className="btn btn-primary btn-block" disabled={loading}>{loading ? 'Creating…' : 'Create Account'}</button>
            <div className="center mt-2" style={{ fontSize: '0.85rem' }}>
              Already have an account? <button type="button" className="btn btn-ghost btn-sm" onClick={() => setMode('signin')}>Sign in</button>
            </div>
          </form>
        )}

        {mode === 'forgot' && (
          <form onSubmit={onSubmitForgot}>
            <Field label="Email" hint="We'll send a reset link if this email is registered.">
              <input className="input" type="email" value={resetEmail} onChange={(e) => setResetEmail(e.target.value)} required />
            </Field>
            <button className="btn btn-primary btn-block">Send reset link</button>
            <div className="center mt-2"><button type="button" className="btn btn-ghost btn-sm" onClick={() => setMode('signin')}>Back to sign in</button></div>
          </form>
        )}

        {mode === 'reset' && (
          <form onSubmit={onSubmitReset}>
            <Field label="Reset token" hint="Paste the token from your email.">
              <input className="input" value={resetToken} onChange={(e) => setResetToken(e.target.value)} required />
            </Field>
            <Field label="New password">
              <input className="input" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} />
            </Field>
            <button className="btn btn-primary btn-block">Reset password</button>
          </form>
        )}
      </div>

      <div className="auth-footer">Powered by VerseTechnologies</div>

      <Modal open={termsOpen} onClose={() => setTermsOpen(false)} title="Terms and Conditions">
        <ol style={{ paddingLeft: 20, lineHeight: 1.7, fontSize: '0.9rem' }}>
          {TERMS.map((t) => <li key={t}>{t}</li>)}
        </ol>
        <div className="card" style={{ background: 'var(--bg-elevated)', marginTop: 12 }}>
          <strong>Platform settlement fee: 5%</strong>
          <div className="help-text">Configurable between 5–10% by business/legal settings. The fee is always shown before you commit.</div>
        </div>
        <label className="row mt-2" style={{ gap: 8 }}>
          <input type="checkbox" checked={agreeTerms} onChange={(e) => setAgreeTerms(e.target.checked)} />
          <span style={{ fontSize: '0.9rem' }}>I agree to the Terms and Conditions</span>
        </label>
        {pendingRegister ? (
          <button className="btn btn-primary btn-block mt-2" disabled={!agreeTerms} onClick={doRegister}>
            {agreeTerms ? 'Agree & Create Account' : 'You must agree to continue'}
          </button>
        ) : (
          <button className="btn btn-secondary btn-block mt-2" onClick={() => setTermsOpen(false)}>Close</button>
        )}
      </Modal>
    </div>
  )
}
