// Notifications centre (§45). Each notification deep-links to its debate / invitation / match.
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../api/client'
import { EmptyState, Spinner } from '../components/ui'
import { formatDateTime } from '../utils/format'
import type { Notification } from '../types'

export default function Notifications() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({ queryKey: ['notifications'], queryFn: notificationsApi.list })
  const markAll = useMutation({ mutationFn: notificationsApi.markAllRead, onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }) })
  const markRead = useMutation({ mutationFn: notificationsApi.markRead, onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }) })

  function open(n: Notification) {
    if (!n.read) markRead.mutate(n.id)
    if (n.link) navigate(n.link)
  }

  if (isLoading) return <Spinner />
  return (
    <div className="col" style={{ gap: 20, maxWidth: 720, margin: '0 auto', width: '100%' }}>
      <div className="row-between">
        <h1 style={{ margin: 0 }}>🔔 Notifications</h1>
        <button className="btn btn-secondary btn-sm" onClick={() => markAll.mutate()}>Mark all read</button>
      </div>
      {data && data.length > 0 ? (
        <div className="col" style={{ gap: 8 }}>
          {data.map((n) => (
            <div
              key={n.id}
              role={n.link ? 'link' : undefined}
              tabIndex={n.link ? 0 : -1}
              className="card"
              style={{
                opacity: n.read ? 0.7 : 1,
                cursor: n.link ? 'pointer' : 'default',
                borderLeft: n.read ? '3px solid var(--border)' : '3px solid var(--accent)',
              }}
              onClick={() => open(n)}
              onKeyDown={(e) => { if (n.link && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); open(n) } }}
            >
              <div className="row-between">
                <strong>{n.title}</strong>
                <span className="dim" style={{ fontSize: '0.75rem' }}>{formatDateTime(n.created_at)}</span>
              </div>
              <p className="muted" style={{ margin: '4px 0 0' }}>{n.body}</p>
              {n.link && <span className="dim" style={{ fontSize: '0.75rem' }}>Open →</span>}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="No notifications" subtitle="Updates about your debates, votes and reminders appear here." />
      )}
    </div>
  )
}
