// Games — free-play only, never real money (§51).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { gamesApi, friendlyError } from '../api/client'
import { Explain, EmptyState, Spinner } from '../components/ui'
import { useState } from 'react'

const GAME_META: Record<string, { emoji: string; label: string }> = {
  chess: { emoji: '♟️', label: 'Chess' },
  checkers: { emoji: '🔴', label: 'Checkers' },
  cards: { emoji: '🃏', label: 'Cards' },
  connect_four: { emoji: '🟡', label: 'Connect Four' },
  tic_tac_toe: { emoji: '⭕', label: 'Tic-Tac-Toe' },
  reversi: { emoji: '⚫', label: 'Reversi' },
}

interface GameRow { id: string; game_type: string; status: string; is_real_money: boolean }

export default function Games() {
  const qc = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const { data: types, isLoading } = useQuery({ queryKey: ['game-types'], queryFn: gamesApi.types })
  const { data: games } = useQuery({ queryKey: ['games'], queryFn: gamesApi.list })

  const create = useMutation({
    mutationFn: (t: string) => gamesApi.create(t),
    onSuccess: () => { setError(null); qc.invalidateQueries({ queryKey: ['games'] }) },
    onError: (e) => setError(friendlyError(e)),
  })

  if (isLoading) return <Spinner />

  return (
    <div className="col" style={{ gap: 20 }}>
      <div>
        <h1>🎮 Games</h1>
        <p className="muted">Play for fun. Games on Debate_Settler are free — no real money is ever at stake.</p>
      </div>

      <Explain>
        Games are a light way to challenge friends. Unlike debates, they never move
        money and never touch your wallet balance.
      </Explain>

      {error && <div className="error-text" role="alert">{error}</div>}

      <div className="grid grid-auto">
        {(types ?? []).map((t) => {
          const meta = GAME_META[t] ?? { emoji: '🎲', label: t }
          return (
            <button key={t} className="card card-hover" style={{ textAlign: 'center', cursor: 'pointer' }}
              onClick={() => create.mutate(t)} disabled={create.isPending}>
              <div style={{ fontSize: '1.8rem' }}>{meta.emoji}</div>
              <div style={{ fontWeight: 600, marginTop: 8 }}>{meta.label}</div>
              <div className="dim" style={{ fontSize: '0.75rem', marginTop: 4 }}>Start free game</div>
            </button>
          )
        })}
      </div>

      <div>
        <h2 style={{ fontSize: '1.1rem' }}>Your games</h2>
        {games && games.length > 0 ? (
          <div className="col" style={{ gap: 8 }}>
            {(games as GameRow[]).map((g) => (
              <div key={g.id} className="card row-between">
                <span>{GAME_META[g.game_type]?.emoji ?? '🎲'} {GAME_META[g.game_type]?.label ?? g.game_type}</span>
                <span className="badge badge-active">{g.status}</span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No games yet" subtitle="Pick a game above to start playing." />
        )}
      </div>
    </div>
  )
}
