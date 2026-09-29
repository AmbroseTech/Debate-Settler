// Profile — your public identity and debate record (§52).
import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { usersApi, mediaApi, friendlyError } from '../api/client'
import { useAuth } from '../store/auth'
import { Explain, Field, Spinner } from '../components/ui'
import type { User } from '../types'

const AVATAR_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_AVATAR_MB = 8

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

export default function Profile() {
  const qc = useQueryClient()
  const { user, loadUser } = useAuth()
  const { data: me, isLoading } = useQuery({ queryKey: ['me'], queryFn: usersApi.me as () => Promise<User> })
  const [form, setForm] = useState({ display_name: '', bio: '', avatar_url: '' })
  const [dirty, setDirty] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const profile = me?.profile
  const displayName = form.display_name || profile?.display_name || user?.username || ''

  const save = useMutation({
    mutationFn: () => usersApi.updateProfile({
      display_name: form.display_name || null,
      bio: form.bio || null,
      avatar_url: form.avatar_url || null,
    }),
    onSuccess: () => { setMsg({ ok: true, text: 'Profile saved.' }); qc.invalidateQueries({ queryKey: ['me'] }); loadUser() },
    onError: (e) => setMsg({ ok: false, text: friendlyError(e) }),
  })

  if (isLoading || !me) return <Spinner />

  const update = (k: keyof typeof form, v: string) => { setForm({ ...form, [k]: v }); setDirty(true) }

  const avatarInput = useRef<HTMLInputElement>(null)

  const uploadAvatar = useMutation({
    mutationFn: (file: File) => mediaApi.uploadAvatar(file),
    onSuccess: (res) => {
      setForm((f) => ({ ...f, avatar_url: res.url }))
      qc.invalidateQueries({ queryKey: ['me'] }); loadUser()
      setMsg({ ok: true, text: 'Profile picture updated.' })
      if (avatarInput.current) avatarInput.current.value = ''
    },
    onError: (e) => setMsg({ ok: false, text: friendlyError(e) }),
  })

  function pickAvatar(file: File | undefined) {
    setMsg(null)
    if (!file) return
    if (!AVATAR_TYPES.includes(file.type)) { setMsg({ ok: false, text: 'Choose a JPEG, PNG or WebP image.' }); return }
    if (file.size > MAX_AVATAR_MB * 1024 * 1024) { setMsg({ ok: false, text: `Image is too large — the limit is ${MAX_AVATAR_MB} MB.` }); return }
    uploadAvatar.mutate(file)
  }

  return (
    <div className="col" style={{ gap: 24, maxWidth: 720, margin: '0 auto', width: '100%' }}>
      <div className="card row" style={{ gap: 16, alignItems: 'center' }}>
        {(profile?.avatar_url || form.avatar_url) ? (
          <img src={form.avatar_url || profile?.avatar_url || ''} alt="Your profile picture"
            style={{ width: 64, height: 64, borderRadius: '50%', objectFit: 'cover', border: '1px solid var(--border)' }} />
        ) : (
          <div className="splash-logo" style={{ width: 64, height: 64, fontSize: '1.4rem', borderRadius: '50%' }}>
            {displayName.slice(0, 2).toUpperCase()}
          </div>
        )}
        <div className="grow">
          <h1 style={{ margin: 0 }}>{profile?.display_name || me.username}</h1>
          <div className="muted">@{me.username} · <span className="badge badge-active">{me.role}</span></div>
          {!me.email_verified && <div className="help-text" style={{ marginTop: 6 }}>Email not verified yet.</div>}
        </div>
      </div>

      <div className="grid grid-auto">
        <Stat label="Created" value={profile?.debates_created ?? 0} />
        <Stat label="Participated" value={profile?.debates_participated ?? 0} />
        <Stat label="Wins" value={profile?.wins ?? 0} />
        <Stat label="Losses" value={profile?.losses ?? 0} />
        <Stat label="Draws" value={profile?.draws ?? 0} />
      </div>

      <section className="col" style={{ gap: 12 }}>
        <h2 style={{ fontSize: '1.1rem' }}>Edit profile</h2>
        <Explain>This is what other people see when you challenge or invite them.</Explain>
        <Field label="Display name">
          <input className="input" value={form.display_name || profile?.display_name || ''} placeholder={me.username}
            onChange={(e) => update('display_name', e.target.value)} maxLength={100} />
        </Field>
        <Field label="Bio" hint="A short line about you.">
          <textarea className="input textarea" rows={3} maxLength={1000}
            value={form.bio || profile?.bio || ''} onChange={(e) => update('bio', e.target.value)} />
        </Field>
        <Field label="Profile picture" hint="JPEG, PNG or WebP up to 8 MB.">
          <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
            <label className="btn btn-secondary" style={{ cursor: uploadAvatar.isPending ? 'wait' : 'pointer' }}>
              {uploadAvatar.isPending ? 'Uploading…' : 'Upload picture'}
              <input ref={avatarInput} type="file" accept={AVATAR_TYPES.join(',')} hidden disabled={uploadAvatar.isPending}
                onChange={(e) => pickAvatar(e.target.files?.[0])} />
            </label>
          </div>
        </Field>
        {msg && <div className={msg.ok ? 'help-text' : 'error-text'} role="status">{msg.text}</div>}
        <div>
          <button className="btn btn-primary" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
            {save.isPending ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </section>
    </div>
  )
}
