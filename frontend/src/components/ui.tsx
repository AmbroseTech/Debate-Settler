// Small shared UI primitives: ExplainBox, EmptyState, Spinner, Modal, Tooltip.
import type { ReactNode } from 'react'

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
