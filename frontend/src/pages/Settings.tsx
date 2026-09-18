// Settings — notification preferences, privacy and password (§75).
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { authApi, usersApi, friendlyError } from '../api/client'
import { useAuth } from '../store/auth'
import { Explain, Field, Spinner } from '../components/ui'

interface Prefs {
  notify_in_app: boolean; notify_email: boolean; notify_push: boolean; notify_sms: boolean
  profile_public: boolean; allow_invitations: boolean; show_tutorial: boolean; theme: string
}

const TOGGLES: { key: keyof Prefs; label: string; hint: string }[] = [
  { key: 'notify_in_app', label: 'In-app notifications', hint: 'Show updates inside Debate_Settler.' },
  { key: 'notify_email', label: 'Email notifications', hint: 'Email me about debate activity.' },
  { key: 'notify_push', label: 'Push notifications', hint: 'Browser push alerts where supported.' },
  { key: 'notify_sms', label: 'SMS notifications', hint: 'Text messages where configured.' },
  { key: 'profile_public', label: 'Public profile', hint: 'Let others see your profile and stats.' },
  { key: 'allow_invitations', label: 'Allow invitations', hint: 'Let people invite you to debates.' },
  { key: 'show_tutorial', label: 'Show tutorial', hint: 'Display the welcome tour on new features.' },
]

function Toggle({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint: string }) {
  return (
    <div className="card row-between" style={{ gap: 12 }}>
      <div>
        <div style={{ fontWeight: 600 }}>{label}</div>
        <div className="help-text">{hint}</div>
      </div>
      <button
        className={`btn btn-sm ${checked ? 'btn-primary' : 'btn-secondary'}`}
        role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
      >
        {checked ? 'On' : 'Off'}
      </button>
    </div>
  )
}

export default function Settings() {
  const qc = useQueryClient()
  const { logout } = useAuth()
  const { data: prefs, isLoading } = useQuery({ queryKey: ['preferences'], queryFn: usersApi.getPreferences as () => Promise<Prefs> })
  const [form, setForm] = useState<Prefs | null>(null)
  const [saved, setSaved] = useState(false)
  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => { if (prefs && !form) setForm(prefs) }, [prefs, form])

  const savePrefs = useMutation({
    mutationFn: (body: Partial<Prefs>) => usersApi.updatePreferences(body),
    onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000); qc.invalidateQueries({ queryKey: ['preferences'] }) },
  })

  const changePw = useMutation({
    mutationFn: () => authApi.changePassword(pw.current_password, pw.new_password),
    onSuccess: () => { setPwMsg({ ok: true, text: 'Password updated. Please sign in again.' }); setPw({ current_password: '', new_password: '', confirm: '' }); setTimeout(() => logout(), 1200) },
    onError: (e) => setPwMsg({ ok: false, text: friendlyError(e) }),
  })

  if (isLoading || !form) return <Spinner />

  const set = (key: keyof Prefs, value: boolean) => {
    const next = { ...form, [key]: value }
    setForm(next)
    savePrefs.mutate({ [key]: value } as Partial<Prefs>)
  }

  const pwValid = pw.new_password.length >= 8 && pw.new_password === pw.confirm && pw.current_password.length > 0

  return (
    <div className="col" style={{ gap: 24, maxWidth: 720, margin: '0 auto', width: '100%' }}>
      <div className="row-between">
        <h1 style={{ margin: 0 }}>⚙️ Settings</h1>
        {saved && <span className="badge badge-settled">Saved ✓</span>}
      </div>

      <section className="col" style={{ gap: 10 }}>
        <h2 style={{ fontSize: '1.1rem' }}>Notifications & privacy</h2>
        {TOGGLES.map((t) => (
          <Toggle key={t.key} label={t.label} hint={t.hint}
            checked={Boolean(form[t.key])} onChange={(v) => set(t.key, v)} />
        ))}
      </section>

      <section className="col" style={{ gap: 12 }}>
        <h2 style={{ fontSize: '1.1rem' }}>Change password</h2>
        <Explain>Choose a strong password you don't use elsewhere. You'll be signed out after changing it.</Explain>
        <Field label="Current password">
          <input className="input" type="password" value={pw.current_password} autoComplete="current-password"
            onChange={(e) => setPw({ ...pw, current_password: e.target.value })} />
        </Field>
        <Field label="New password" hint="At least 8 characters.">
          <input className="input" type="password" value={pw.new_password} autoComplete="new-password"
            onChange={(e) => setPw({ ...pw, new_password: e.target.value })} />
        </Field>
        <Field label="Confirm new password" error={pw.confirm && pw.confirm !== pw.new_password ? 'Passwords do not match.' : undefined}>
          <input className="input" type="password" value={pw.confirm} autoComplete="new-password"
            onChange={(e) => setPw({ ...pw, confirm: e.target.value })} />
        </Field>
        {pwMsg && <div className={pwMsg.ok ? 'help-text' : 'error-text'} role="status">{pwMsg.text}</div>}
        <button className="btn btn-primary" disabled={!pwValid || changePw.isPending} onClick={() => changePw.mutate()}>
          {changePw.isPending ? 'Updating…' : 'Update password'}
        </button>
      </section>

      <section className="col" style={{ gap: 12 }}>
        <h2 style={{ fontSize: '1.1rem' }}>Session</h2>
        <button className="btn btn-danger" onClick={() => logout()}>Sign out</button>
      </section>
    </div>
  )
}
