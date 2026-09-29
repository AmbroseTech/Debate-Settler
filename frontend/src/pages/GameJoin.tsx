// Accept / decline a game challenge reached through its invitation link (§6).
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { gamesApi, friendlyError } from '../api/client'
import { useAuth } from '../store/auth'
import { Explain, Spinner } from '../components/ui'

const GAME_META: Record<string, string> = {
  tic_tac_toe: '⭕ Tic-Tac-Toe', chess: '♟️ Chess', checkers: '🔴 Checkers',
  cards: '🃏 Cards', connect_four: '🟡 Connect Four', reversi: '⚫ Reversi',
}

export default function GameJoin() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const { user, initialized } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const { data: preview, isLoading } = useQuery({
    queryKey: ['game-invite', token],
    queryFn: () => gamesApi.previewInvitation(token!),
    enabled: !!token,
  })

  const accept = useMutation({
    mutationFn: () => gamesApi.acceptInvitation(token!),
    onSuccess: (match) => navigate(`/games/${match.id}`),
    onError: (e) => setError(friendlyError(e)),
  })
  const decline = useMutation({
    mutationFn: () => gamesApi.declineInvitation(token!),
    onSuccess: () => navigate('/games'),
    onError: (e) => setError(friendlyError(e)),
  })

  if (!initialized) return <Spinner />

  if (!user) {
    return (
      <div className="card col" style={{ gap: 12, maxWidth: 460, margin: '40px auto', width: '100%' }}>
        <h1>🎮 A friend challenged you</h1>
        <p className="muted">Sign in or create a free account to see the challenge and play.</p>
        <button className="btn btn-primary" onClick={() => navigate('/auth', { state: { next: `/games/join/${token}` } })}>Sign in to continue</button>
      </div>
    )
  }

  if (isLoading) return <Spinner />
  if (!preview) return <div className="card">This challenge link is not valid.</div>

  const label = GAME_META[preview.game_type] ?? preview.game_type
  const addressedToYou = !preview.to_username || preview.to_username === user.username
  const alreadyAnswered = preview.invitation_status !== 'pending'
  const blocked = preview.expired || alreadyAnswered || !addressedToYou

  const note = preview.expired
    ? 'This challenge has expired.'
    : alreadyAnswered
      ? `This challenge was already ${preview.invitation_status}.`
      : !addressedToYou
        ? `This challenge was meant for ${preview.to_username}, not for you.`
        : null

  return (
    <div className="col" style={{ gap: 16, maxWidth: 460, margin: '0 auto', width: '100%' }}>
      <div className="card col" style={{ gap: 12 }}>
        <h1 style={{ margin: 0 }}>{label}</h1>
        <p className="muted" style={{ margin: 0 }}>
          <strong>{preview.inviter_username}</strong> challenged you to a friendly, free match of {label}.
        </p>
        {blocked && note && <Explain>{note}</Explain>}
        {error && <div className="error-text" role="alert">{error}</div>}
        {!blocked && (
          <div className="row" style={{ flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={() => accept.mutate()} disabled={accept.isPending}>
              {accept.isPending ? 'Opening match…' : 'Accept & play'}
            </button>
            <button className="btn btn-secondary" onClick={() => decline.mutate()} disabled={decline.isPending}>Decline</button>
          </div>
        )}
        <div className="row-between">
          <span className="dim" style={{ fontSize: '0.75rem' }}>Games are always free — no money on Debate Settler.</span>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/games')}>Back</button>
        </div>
      </div>
    </div>
  )
}
