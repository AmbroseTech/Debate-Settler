import type { DebateStatus } from '../types'
import { statusInfo } from '../utils/format'

export default function StatusBadge({ status }: { status: DebateStatus }) {
  const info = statusInfo(status)
  return (
    <span className={`badge ${info.cls}`} title={info.label}>
      <span aria-hidden="true">{info.emoji}</span>
      {info.label}
    </span>
  )
}
