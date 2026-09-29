// A single match view: the server owns the board, turns and result (§6, §12).
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { gamesApi, friendlyError } from '../api/client'
import { useAuth } from '../store/auth'
import { Explain, Spinner } from '../components/ui'
import type { MatchState } from '../types'

const GAME_META: Record<string, { emoji: string; label: string }> = {
  tic_tac_toe: { emoji: '⭕', label: 'Tic-Tac-Toe' },
  chess: { emoji: '♟️', label: 'Chess' },
  checkers: { emoji: '🔴', label: 'Checkers' },
  cards: { emoji: '🃏', label: 'Cards' },
  connect_four: { emoji: '🟡', label: 'Connect Four' },
  reversi: { emoji: '⚫', label: 'Reversi' },
}

export default function GameMatch() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const qc = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { data: match, isLoading } = useQuery<MatchState>({
    queryKey: ['match', id],
    queryFn: () => gamesApi.getMatch(id!),
    enabled: !!id,
    refetchInterval: 4000,
  })

  const move = useMutation({
    mutationFn: (cell: number) => gamesApi.move(id!, cell),
    onSuccess: (res) => { setError(null); qc.setQueryData(['match', id], res.match); qc.invalidateQueries({ queryKey: ['games'] }) },
    onError: (e) => setError(friendlyError(e)),
  })

  if (isLoading) return <Spinner />
  if (!match) return <div className="card">Match not found. It may have been cancelled.</div>

  const meta = GAME_META[match.game_type] ?? { emoji: '🎲', label: match.game_type }
  const youWin = match.winner_id && match.winner_id === user?.id
  const draw = match.status === 'finished' && !match.winner_id
  const statusLine =
    match.status === 'finished'
      ? youWin ? '🏆 You won this match!'
        : draw ? '🤝 It ended in a draw.'
        : 'Match complete — better luck next time.'
      : match.status === 'active'
        ? match.can_play ? `Your turn (${(match.your_mark ?? '?').toUpperCase()})` : 'Waiting for your opponent…'
        : match.status === 'waiting' ? 'Waiting for an opponent to accept.'
        : 'This match was cancelled.'

  return (
    <div className="col" style={{ gap: 16, maxWidth: 420, margin: '0 auto', width: '100%' }}>
      <div className="row-between">
        <h1 style={{ margin: 0 }}>{meta.emoji} {meta.label}</h1>
        <Link className="btn btn-ghost btn-sm" to="/games">← Games</Link>
      </div>

      <div className="card col" style={{ gap: 14 }}>
        <div className="center muted" role="status">{statusLine}</div>
        {error && <div className="error-text" role="alert">{error}</div>}

        <div className="ttt-board">
          {(match.board.length ? match.board : Array(9).fill(null)).map((cell, i) => (
            <button
              key={i}
              className={`ttt-cell${cell ? ` ttt-${cell}` : ''}`}
              onClick={() => move.mutate(i)}
              disabled={!match.can_play || cell !== null || move.isPending}
              aria-label={`Square ${i + 1}${cell ? `, ${cell.toUpperCase()}` : ', empty'}`}
            >
              {cell ? cell.toUpperCase() : ''}
            </button>
          ))}
        </div>

        <div className="row-between dim" style={{ fontSize: '0.8rem' }}>
          <span>You play: <strong>{(match.your_mark ?? '—').toUpperCase()}</strong></span>
          <span>Opponent plays: <strong>{match.your_mark === 'x' ? 'O' : match.your_mark === 'o' ? 'X' : '—'}</strong></span>
        </div>
      </div>

      <Explain>The server decides every legal move and the winner — the board can’t be tricked from the browser. Ratings update once per finished match.</Explain>
    </div>
  )
}
