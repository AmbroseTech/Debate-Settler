// Formatting helpers: money, dates, status labels (§49, §57).
import type { DebateStatus } from '../types'

export function formatMoney(amount: string | number, currency = 'UGX'): string {
  const n = typeof amount === 'string' ? parseFloat(amount) : amount
  if (Number.isNaN(n)) return `${currency} 0.00`
  return `${currency} ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function timeUntil(iso?: string | null): string {
  if (!iso) return '—'
  const diff = new Date(iso).getTime() - Date.now()
  if (diff <= 0) return 'Closed'
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  if (days === 1) return 'Tomorrow'
  return `${days}d`
}

// Status label + emoji per §49. Never rely on colour alone (§78).
export const STATUS_LABELS: Record<DebateStatus, { label: string; emoji: string; cls: string }> = {
  draft: { label: 'Draft', emoji: '📝', cls: 'badge-closed' },
  open: { label: 'Open', emoji: '🟢', cls: 'badge-open' },
  active: { label: 'Active', emoji: '🔵', cls: 'badge-active' },
  voting: { label: 'Voting', emoji: '🟣', cls: 'badge-voting' },
  closing_soon: { label: 'Closing Soon', emoji: '🟠', cls: 'badge-waiting' },
  closed: { label: 'Closed', emoji: '⚫', cls: 'badge-closed' },
  being_verified: { label: 'Being Verified', emoji: '🔍', cls: 'badge-review' },
  settled: { label: 'Settled', emoji: '🏆', cls: 'badge-settled' },
  draw: { label: 'Draw', emoji: '↔️', cls: 'badge-draw' },
  disputed: { label: 'Disputed', emoji: '🔴', cls: 'badge-disputed' },
  funding_timeout: { label: 'Funding Timeout', emoji: '⏱️', cls: 'badge-waiting' },
  cancelled: { label: 'Cancelled', emoji: '🚫', cls: 'badge-closed' },
  under_review: { label: 'Under Review', emoji: '🔍', cls: 'badge-review' },
  payment_pending: { label: 'Payment Pending', emoji: '🟡', cls: 'badge-waiting' },
}

export function statusInfo(status: DebateStatus) {
  return STATUS_LABELS[status] ?? { label: status, emoji: '•', cls: 'badge-closed' }
}

// Plain-English wallet explanations (§29).
export const WALLET_EXPLAIN: Record<string, string> = {
  available: 'Money you can currently use or withdraw.',
  locked: 'Money temporarily committed to an active debate.',
  pending: 'Money waiting for a transaction or settlement to finish.',
  withdrawable: 'Money currently eligible for withdrawal.',
}

export function truncate(text: string, max = 80): string {
  return text.length > max ? `${text.slice(0, max)}…` : text
}
