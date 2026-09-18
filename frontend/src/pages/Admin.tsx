// Admin dashboard — stats, users, disputes, settlements, audit trail (§43).
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminApi, friendlyError } from '../api/client'
import { useAuth } from '../store/auth'
import { EmptyState, Explain, Field, Spinner } from '../components/ui'
import { formatDateTime, formatMoney } from '../utils/format'

interface Stats { users: number; debates: number; local_debates: number; online_debates: number; votes: number; deposits: string; withdrawals: string; platform_fees: string; open_disputes: number; currency: string }
interface UserRow { id: string; username: string; email: string; role: string; status: string; email_verified: boolean; created_at: string }
interface DisputeRow { id: string; debate_id: string; reason: string; status: string; payout_on_hold: boolean; created_at: string }
interface AuditRow { id: string; action: string; entity_type: string; entity_id: string; actor_id: string | null; created_at: string }

function Stat({ label, value }: { label: string; value: string | number }) {
  return <div className="stat"><div className="stat-value">{value}</div><div className="stat-label">{label}</div></div>
}

export default function Admin() {
  const qc = useQueryClient()
  const { user } = useAuth()
  const [tab, setTab] = useState<'overview' | 'users' | 'disputes' | 'settle' | 'audit'>('overview')
  const [settleForm, setSettleForm] = useState({ debate_id: '', winner_side: 'a', source_verified: true, settlement_source: '', reason: '' })
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)

  const isAdmin = user?.role === 'admin' || user?.role === 'moderator'
  const stats = useQuery({ queryKey: ['admin-stats'], queryFn: adminApi.stats as () => Promise<Stats>, enabled: isAdmin })
  const users = useQuery({ queryKey: ['admin-users'], queryFn: adminApi.users as () => Promise<UserRow[]>, enabled: isAdmin })
  const disputes = useQuery({ queryKey: ['admin-disputes'], queryFn: adminApi.disputes as () => Promise<DisputeRow[]>, enabled: isAdmin })
  const audit = useQuery({ queryKey: ['admin-audit'], queryFn: adminApi.auditLogs as () => Promise<AuditRow[]>, enabled: isAdmin })

  const submitSettlement = useMutation({
    mutationFn: () => adminApi.submitSettlement(settleForm),
    onSuccess: () => { setNote('Settlement recorded.'); setError(null); qc.invalidateQueries() },
    onError: (e) => { setError(friendlyError(e)); setNote(null) },
  })

  if (!isAdmin) {
    return <EmptyState title="Admins only" subtitle="You don't have permission to view this page." />
  }

  const TABS = [
    { id: 'overview', label: 'Overview' },
    { id: 'users', label: 'Users' },
    { id: 'disputes', label: 'Disputes' },
    { id: 'settle', label: 'Settle' },
    { id: 'audit', label: 'Audit log' },
  ] as const

  return (
    <div className="col" style={{ gap: 20 }}>
      <h1>🛡️ Admin</h1>

      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
        {TABS.map((t) => (
          <button key={t.id} className={`btn btn-sm ${tab === t.id ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {error && <div className="error-text" role="alert">{error}</div>}
      {note && <div className="help-text" role="status">{note}</div>}

      {tab === 'overview' && (stats.isLoading ? <Spinner /> : stats.data && (
        <div className="grid grid-auto">
          <Stat label="Users" value={stats.data.users} />
          <Stat label="Debates" value={stats.data.debates} />
          <Stat label="Local" value={stats.data.local_debates} />
          <Stat label="Online" value={stats.data.online_debates} />
          <Stat label="Votes" value={stats.data.votes} />
          <Stat label="Open disputes" value={stats.data.open_disputes} />
          <Stat label="Deposits" value={formatMoney(stats.data.deposits, stats.data.currency)} />
          <Stat label="Withdrawals" value={formatMoney(stats.data.withdrawals, stats.data.currency)} />
          <Stat label="Platform fees" value={formatMoney(stats.data.platform_fees, stats.data.currency)} />
        </div>
      ))}

      {tab === 'users' && (users.isLoading ? <Spinner /> : (
        <div className="card" style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Verified</th><th>Joined</th></tr></thead>
            <tbody>
              {(users.data ?? []).map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td><td className="dim">{u.email}</td>
                  <td><span className="badge badge-active">{u.role}</span></td>
                  <td>{u.status}</td><td>{u.email_verified ? '✓' : '—'}</td>
                  <td className="dim">{formatDateTime(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {tab === 'disputes' && (disputes.isLoading ? <Spinner /> : (disputes.data ?? []).length === 0 ? (
        <EmptyState title="No disputes" subtitle="Open disputes appear here for review." />
      ) : (
        <div className="col" style={{ gap: 8 }}>
          {(disputes.data ?? []).map((d) => (
            <div key={d.id} className="card">
              <div className="row-between">
                <strong>{d.reason.slice(0, 60)}</strong>
                <span className={`badge ${d.status === 'open' ? 'badge-disputed' : 'badge-review'}`}>{d.status}</span>
              </div>
              <div className="dim" style={{ fontSize: '0.8rem', marginTop: 4 }}>
                Payout {d.payout_on_hold ? 'on hold' : 'released'} · {formatDateTime(d.created_at)}
              </div>
            </div>
          ))}
        </div>
      ))}

      {tab === 'settle' && (
        <div className="card col" style={{ gap: 12, maxWidth: 560 }}>
          <Explain>Submit a verified result for an Online Result Debate. Only do this once the agreed settlement source confirms the outcome — the system never guesses.</Explain>
          <Field label="Debate ID">
            <input className="input" value={settleForm.debate_id} onChange={(e) => setSettleForm({ ...settleForm, debate_id: e.target.value })} />
          </Field>
          <Field label="Winning side">
            <select className="input" value={settleForm.winner_side} onChange={(e) => setSettleForm({ ...settleForm, winner_side: e.target.value })}>
              <option value="a">Side A</option><option value="b">Side B</option><option value="draw">Draw</option>
            </select>
          </Field>
          <Field label="Settlement source">
            <input className="input" value={settleForm.settlement_source} placeholder="e.g. Official competition result"
              onChange={(e) => setSettleForm({ ...settleForm, settlement_source: e.target.value })} />
          </Field>
          <label className="row" style={{ gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={settleForm.source_verified}
              onChange={(e) => setSettleForm({ ...settleForm, source_verified: e.target.checked })} />
            Source verified
          </label>
          <button className="btn btn-primary" disabled={!settleForm.debate_id || submitSettlement.isPending} onClick={() => submitSettlement.mutate()}>
            {submitSettlement.isPending ? 'Recording…' : 'Record settlement'}
          </button>
        </div>
      )}

      {tab === 'audit' && (audit.isLoading ? <Spinner /> : (
        <div className="card" style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead><tr><th>When</th><th>Action</th><th>Entity</th><th>Actor</th></tr></thead>
            <tbody>
              {(audit.data ?? []).map((a) => (
                <tr key={a.id}>
                  <td className="dim">{formatDateTime(a.created_at)}</td>
                  <td>{a.action}</td>
                  <td className="dim">{a.entity_type} · {a.entity_id?.slice(0, 8)}</td>
                  <td className="dim">{a.actor_id?.slice(0, 8) ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}
