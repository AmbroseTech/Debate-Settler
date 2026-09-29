// Debate media upload — images/videos with client-side validation and preview.
// The backend re-validates type/size and serves files behind an auth check (§13).
import { useRef, useState } from 'react'
import { friendlyError, mediaApi } from '../api/client'

const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
const VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']
const MAX_IMAGE_MB = 8
const MAX_VIDEO_MB = 25
const MAX_VIDEO_SECONDS = 120

interface Uploaded { id: string; url: string; kind: 'image' | 'video' }

export default function MediaUpload({ debateId }: { debateId: string }) {
  const imgRef = useRef<HTMLInputElement>(null)
  const vidRef = useRef<HTMLInputElement>(null)
  const [items, setItems] = useState<Uploaded[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleFile(file: File | undefined, kind: 'image' | 'video') {
    setError('')
    if (!file) return
    const allowed = kind === 'image' ? IMAGE_TYPES : VIDEO_TYPES
    if (!allowed.includes(file.type)) {
      setError(kind === 'image' ? 'Choose a JPEG, PNG, WebP or GIF image.' : 'Choose an MP4, WebM or MOV video.');
      return
    }
    const maxMb = kind === 'image' ? MAX_IMAGE_MB : MAX_VIDEO_MB
    if (file.size > maxMb * 1024 * 1024) {
      setError(`File is too large — the limit is ${maxMb} MB.`)
      return
    }
    if (kind === 'video') {
      const seconds = await probeDuration(file)
      if (seconds && seconds > MAX_VIDEO_SECONDS) {
        setError(`Video is ${Math.round(seconds)}s — the limit is ${MAX_VIDEO_SECONDS}s. Trim it first.`)
        return
      }
    }
    setBusy(true)
    try {
      const res = await mediaApi.upload(file, kind, debateId)
      setItems((prev) => [...prev, { id: res.id, url: res.url, kind }])
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setBusy(false)
      if (kind === 'image' && imgRef.current) imgRef.current.value = ''
      if (kind === 'video' && vidRef.current) vidRef.current.value = ''
    }
  }

  return (
    <div className="card col" style={{ gap: 12 }}>
      <h3 style={{ margin: 0 }}>🖼️ Media</h3>
      <p className="help-text">Attach an image or a short clip to make your case. Files are checked and stored securely.</p>

      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
        <label className="btn btn-secondary" style={{ cursor: busy ? 'wait' : 'pointer' }}>
          {busy ? 'Uploading…' : 'Add image'}
          <input ref={imgRef} type="file" accept={IMAGE_TYPES.join(',')} hidden disabled={busy}
            onChange={(e) => handleFile(e.target.files?.[0], 'image')} />
        </label>
        <label className="btn btn-secondary" style={{ cursor: busy ? 'wait' : 'pointer' }}>
          {busy ? 'Uploading…' : 'Add video'}
          <input ref={vidRef} type="file" accept={VIDEO_TYPES.join(',')} hidden disabled={busy}
            onChange={(e) => handleFile(e.target.files?.[0], 'video')} />
        </label>
      </div>

      {error && <div className="error-text" role="alert">{error}</div>}

      {items.length > 0 && (
        <div className="grid grid-auto">
          {items.map((m) => (
            <div key={m.id} className="card" style={{ padding: 6, overflow: 'hidden' }}>
              {m.kind === 'image'
                ? <img src={m.url} alt="Uploaded" style={{ width: '100%', height: 160, objectFit: 'cover', borderRadius: 8 }} />
                : <video src={m.url} controls style={{ width: '100%', maxHeight: 220, borderRadius: 8 }} />}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function probeDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const v = document.createElement('video')
    v.preload = 'metadata'
    v.onloadedmetadata = () => { URL.revokeObjectURL(url); resolve(v.duration) }
    v.onerror = () => { URL.revokeObjectURL(url); resolve(null) }
    v.src = url
  })
}
