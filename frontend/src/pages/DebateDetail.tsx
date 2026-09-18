// Debate detail: live voting, invitations, funding, locking, disputes (§16-§23).
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { debatesApi, disputesApi, friendlyError } from '../api/client'
import { useAuth } from '../store/auth'
import StatusBadge from '../components/StatusBadge'
import { Explain, Field, Modal, Spinner } from '../components/ui'
import { formatDateTime, formatMoney } from '../utils/format'
import type { VoteChoice } from '../types'

export default function DebateDetail() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const qc = useQueryClient()
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [shareOpen, setShareOpen] = useState(false)
  const [disputeOpen, setDisputeOpen] = useState(false)
  const [shareLinks, setShareLinks] = useState<Record<string, string> | null>(null)
  const [inviteToken, setInviteToken] = useState('')

  const { data: debate, isLoading } = useQuery({
    queryKey: ['debate', id],
    queryFn: () => debatesApi.get(id!),
    enabled: !!id,
    refetchInterval: 10000,
  })

  const refresh = () => qc.invalidateQueries({ queryKey: ['debate', id] })

  const voteMut = useMutation({
    mutationFn: (choice: VoteChoice) => debatesApi.vote(id!, choice),
    onSuccess: (res) => { setInfo(res.message); refresh(); },
    onError: (err) => setError(friendlyError(err)),
  })
  const fundMut = useMutation({ mutationFn: () => debatesApi.fund(id!), onSuccess: () => { setInfo('Stake locked.'); refresh() }, onError: (e) => setError(friendlyError(e)) })
  const lockMut = useMutation({ mutationFn: () => debatesApi.lock(id!), onSuccess: () => { setInfo('Debate locked.'); refresh() }, onError: (e) => setError(friendlyError(e)) })
  const confirmMut = useMutation({ mutationFn: (side: 'a' | 'b') => debatesApi.confirm(id!, side), onSuccess: () => { setInfo('Side confirmed.'); refresh() }, onError: (e) => setError(friendlyError(e)) })
  const inviteMut = useMutation({
    mutationFn: (kind: string) => debatesApi.createInvitation(id!, { kind, max_uses: kind === 'voter' ? 1000 : 1, expires_in_hours: 72 }),
    onSuccess: (res: any) => { setInviteToken(res.token); refresh() },
    onError: (e) => setError(friendlyError(e)),
  })
  const disputeMut = useMutation({
    mutationFn: (body: Record<string, unknown>) => disputesApi.create(body),
    onSuccess: () => { setDisputeOpen(false); setInfo('Dispute submitted. Payout is on hold until review.') },
    onError: (e) => setError(friendlyError(e)),
  })

  if (isLoading) return <Spinner />
  if (!debate) return <div className="card">Debate not found.</div>

  const isLocal = debate.mode === 'local'
  const hasStake = parseFloat(debate.stake_amount) > 0
  const isParticipant = debate.my_role === 'creator' || debate.my_role === 'challenger'
  const canVote = isLocal && debate.my_role === 'voter' && ['active', 'voting', 'closing_soon'].includes(debate.status)
  const votingOpen = isLocal && ['active', 'voting', 'closing_soon'].includes(debate.status)
  const tally = debate.vote_tally

  async function openShare() {
    try {
      const links = await debatesApi.share(id!)
      setShareLinks(links as unknown as Record<string, string>)
      setShareOpen(true)
    } catch (e) { setError(friendlyError(e)) }
  }

  return (
    <div className="col" style={{ gap: 20, maxWidth: 820, margin: '0 auto', width: '100%' }}>
      <div className="row-between">
        <span className="badge">{isLocal ? 'LOCAL DEBATE' : 'ONLINE RESULT DEBATE'}</span>
        <StatusBadge status={debate.status} />
      </div>

      <div className="card">
        {debate.category_name && <div className="dim" style={{ textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.05em' }}>{debate.category_name}</div>}
        <h1 style={{ margin: '8px 0' }}>“{debate.question}”</h1>
        <div className="debate-vs" style={{ margin: '16px 0' }}>
          <span className="debate-side" style={{ fontSize: '1.3rem' }}>{debate.side_a_label}</span>
          <span className="debate-vs-sep">VS</span>
          <span className="debate-side" style={{ fontSize: '1.3rem' }}>{debate.side_b_label}</span>
        </div>

        <div className="debate-meta">
          <span>⏱️ {isLocal ? 'Ends' : 'Event'}: {formatDateTime(debate.end_at)}</span>
          {hasStake && <span>💰 {formatMoney(debate.stake_amount, debate.currency)} each</span>}
          <span>👥 {debate.participants_count} participants</span>
          <span>👁️ {debate.views} views</span>
        </div>

        {/* The four answers must never be hidden (§99) */}
        <div className="card mt-2" style={{ background: 'var(--bg-elevated)' }}>
          <div className="row-between"><span className="muted">What's debated?</span><span>{debate.question}</span></div>
          <div className="row-between"><span className="muted">Who decides?</span><span>{isLocal ? `${debate.required_voters} invited voters` : debate.settlement_source}</span></div>
          <div className="row-between"><span className="muted">When does it end?</span><span>{formatDateTime(debate.end_at)}</span></div>
          <div className="row-between"><span className="muted">Money?</span><span>{hasStake ? `${formatMoney(debate.stake_amount, debate.currency)} locked per side; winner gets pool minus ${debate.platform_fee_percent}% fee.` : 'No stake — free debate.'}</span></div>
        </div>
      </div>

      {error && <div className="error-text" role="alert">{error}</div>}
      {info && <div className="help-text" style={{ color: 'var(--success)' }} role="status">{info}</div>}

      {/* Voting (§18, §19) */}
      {isLocal && (
        <div className="card">
          <h3>{votingOpen ? 'LIVE DEBATE — Cast your vote' : 'Voting'}</h3>
          {canVote ? (
            debate.has_voted ? (
              <Explain>You voted: <strong>{debate.has_voted.replace('_', ' ').toUpperCase()}</strong>. {debate.rules?.allow_vote_change ? 'Vote changes are allowed in this debate.' : 'Votes cannot be changed in this debate.'}</Explain>
            ) : (
              <div className="grid grid-3">
                <button className="btn btn-primary" onClick={() => voteMut.mutate('side_a')} disabled={voteMut.isPending}>{debate.side_a_label}</button>
                <button className="btn btn-secondary" onClick={() => voteMut.mutate('side_b')} disabled={voteMut.isPending}>{debate.side_b_label}</button>
                {debate.rules?.allow_draw && <button className="btn btn-ghost" onClick={() => voteMut.mutate('draw')} disabled={voteMut.isPending}>DRAW</button>}
              </div>
            )
          ) : (
            <Explain>{debate.my_role === 'voter' ? 'Voting is not open right now.' : 'You need a valid voter invitation to vote in this debate.'}</Explain>
          )}

          {tally && (
            <div className="mt-2">
              <div className="row-between"><span className="muted">Votes recorded</span><strong>{tally.total} / {tally.required || '∞'}</strong></div>
              {tally.revealed ? (
                <div className="grid grid-3 mt-2">
                  <div className="stat"><div className="stat-label">{debate.side_a_label}</div><div className="stat-value">{tally.side_a}</div></div>
                  <div className="stat"><div className="stat-label">{debate.side_b_label}</div><div className="stat-value">{tally.side_b}</div></div>
                  <div className="stat"><div className="stat-label">Draw</div><div className="stat-value">{tally.draw}</div></div>
                </div>
              ) : (
                <Explain>Current result: <strong>Hidden until debate closes</strong> (per the agreed rules).</Explain>
              )}
            </div>
          )}
        </div>
      )}

      {/* Online result info (§21, §22) */}
      {!isLocal && debate.rules && (
        <div className="card">
          <h3>Settlement</h3>
          <Explain>Once locked, the settlement source cannot be changed. The result is matched against the agreed rule — never guessed.</Explain>
          <div className="row-between"><span className="muted">Source</span><strong>{debate.rules.settlement_source}</strong></div>
          <div className="row-between"><span className="muted">Rule</span><span>{debate.rules.settlement_rule}</span></div>
          {debate.status === 'being_verified' && <div className="mt-2"><span className="badge badge-review">🔍 Being Verified</span></div>}
          {debate.winner_side && <div className="mt-2"><strong>Result: {debate.winner_side === 'draw' ? 'DRAW' : debate.winner_side.toUpperCase()}</strong> — {debate.result_summary}</div>}
        </div>
      )}

      {/* Participant actions */}
      {isParticipant && !debate.locked_at && (
        <div className="card">
          <h3>Confirm & Fund</h3>
          <Explain>Both sides must confirm the rules. If there's a stake, both sides must fund before the debate can be locked.</Explain>
          <div className="row" style={{ flexWrap: 'wrap' }}>
            <button className="btn btn-secondary" onClick={() => confirmMut.mutate('a')} disabled={confirmMut.isPending}>Confirm as Side A</button>
            <button className="btn btn-secondary" onClick={() => confirmMut.mutate('b')} disabled={confirmMut.isPending}>Confirm as Side B</button>
            {hasStake && <button className="btn btn-primary" onClick={() => fundMut.mutate()} disabled={fundMut.isPending}>Fund my stake ({formatMoney(debate.stake_amount, debate.currency)})</button>}
            <button className="btn btn-primary" onClick={() => lockMut.mutate()} disabled={lockMut.isPending}>🔒 Lock Debate</button>
          </div>
        </div>
      )}

      {/* Invitations & sharing (§16, §54) */}
      <div className="card">
        <h3>Invite & Share</h3>
        <div className="row" style={{ flexWrap: 'wrap' }}>
          {isLocal && <button className="btn btn-secondary" onClick={() => inviteMut.mutate('voter')} disabled={inviteMut.isPending}>Generate voter link</button>}
          {!debate.locked_at && isParticipant && <button className="btn btn-secondary" onClick={() => inviteMut.mutate('opponent')} disabled={inviteMut.isPending}>Invite opponent</button>}
          <button className="btn btn-secondary" onClick={openShare}>Share…</button>
        </div>
        {inviteToken && (
          <div className="mt-2">
            <Field label="Invitation link">
              <input className="input" readOnly value={`${window.location.origin}/join/${inviteToken}`} onFocus={(e) => e.target.select()} />
            </Field>
            <div className="help-text">Share via WhatsApp, Telegram, Facebook, X, email or QR code.</div>
          </div>
        )}
      </div>

      {/* Dispute (§23) */}
      {['settled', 'draw', 'being_verified', 'closed'].includes(debate.status) && (
        <div className="card">
          <h3>Dispute Result</h3>
          <Explain>Disagree with the result? Submit a dispute with evidence. Payouts go ON HOLD until review is complete.</Explain>
          <button className="btn btn-danger" onClick={() => setDisputeOpen(true)}>Dispute Result</button>
        </div>
      )}

      {/* Share modal */}
      <Modal open={shareOpen} onClose={() => setShareOpen(false)} title="Share this debate">
        {shareLinks && (
          <div className="grid grid-2">
            {Object.entries(shareLinks).filter(([k]) => k !== 'qr_code').map(([k, v]) => (
              <a key={k} className="btn btn-secondary" href={v as string} target="_blank" rel="noreferrer" style={{ textTransform: 'capitalize' }}>{k.replace('_', ' ')}</a>
            ))}
          </div>
        )}
        {shareLinks?.qr_code && (
          <div className="center mt-2">
            <a href={shareLinks.qr_code} target="_blank" rel="noreferrer" className="btn btn-ghost">View QR code</a>
          </div>
        )}
      </Modal>

      {/* Dispute modal */}
      <Modal open={disputeOpen} onClose={() => setDisputeOpen(false)} title="Dispute Result">
        <form onSubmit={(e) => { e.preventDefault(); const f = new FormData(e.currentTarget); disputeMut.mutate({ debate_id: id, reason: f.get('reason'), evidence: f.get('evidence') }) }}>
          <Field label="Reason" hint="Explain why you believe the result is incorrect.">
            <textarea className="textarea" name="reason" required minLength={5} />
          </Field>
          <Field label="Evidence (links / description)">
            <textarea className="textarea" name="evidence" />
          </Field>
          <button className="btn btn-danger btn-block" disabled={disputeMut.isPending}>Submit Dispute</button>
        </form>
      </Modal>
    </div>
  )
}
