// Small shared UI primitives: ExplainBox, EmptyState, Spinner, Modal, Tooltip, PasswordInput.
import { useState, type InputHTMLAttributes, type ReactNode } from 'react'

export function Explain({ children }: { children: ReactNode }) {
  // "What does this mean?" plain-English helper (§10, §58).
  return <div className="explain">{children}</div>
}

export function EmptyState({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="card center" style={{ padding: 40 }}>
      <h3>{title}</h3>
      {subtitle && <p className="muted">{subtitle}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return <div className="center muted" style={{ padding: 24 }} role="status">{label}</div>
}

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  if (!open) return null
  return (
    <div
      className="backdrop"
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: 20 }}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="card" style={{ maxWidth: 520, width: '100%', maxHeight: '85vh', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
        <div className="row-between mb-2">
          <h3 style={{ margin: 0 }}>{title}</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <span title={text} tabIndex={0} style={{ borderBottom: '1px dotted var(--text-dim)', cursor: 'help' }}>
      {children}
    </span>
  )
}

export function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactNode }) {
  return (
    <div className="field">
      <label className="label">{label}</label>
      {children}
      {hint && !error && <div className="help-text">{hint}</div>}
      {error && <div className="error-text" role="alert">{error}</div>}
    </div>
  )
}

function EyeIcon({ off }: { off: boolean }) {
  return off ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

// Accessible show/hide password field (§2). Each instance keeps its own visibility
// state so revealing one field never reveals another. The toggle is a type="button"
// so it can never submit the form, and toggling never mutates the stored value.
export function PasswordInput({ className = 'input', ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="pw-wrap">
      <input {...rest} className={className} type={visible ? 'text' : 'password'} />
      <button
        type="button"
        className="pw-toggle"
        aria-label={visible ? 'Hide password' : 'Show password'}
        aria-pressed={visible}
        onClick={() => setVisible((v) => !v)}
      >
        <EyeIcon off={visible} />
      </button>
    </div>
  )
}
