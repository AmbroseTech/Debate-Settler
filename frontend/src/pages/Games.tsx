// Games — free-play only, never real money (§51).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { gamesApi, friendlyError } from '../api/client'
import { Explain, EmptyState, Spinner } from '../components/ui'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

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
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'free' | 'money'>('free')
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
        <p className="muted">Choose how you want to challenge someone.</p>
      </div>

      <div className="game-mode-picker" role="group" aria-label="Choose a game mode">
        <button className={`game-mode-option ${mode === 'free' ? 'selected' : ''}`} onClick={() => setMode('free')} aria-pressed={mode === 'free'}>
          <span className="game-mode-symbol">♟</span><span><strong>Free play</strong><small>Play without a stake or wallet balance.</small></span><span className="game-mode-check">{mode === 'free' ? '●' : '○'}</span>
        </button>
        <button className={`game-mode-option ${mode === 'money' ? 'selected' : ''}`} onClick={() => setMode('money')} aria-pressed={mode === 'money'}>
          <span className="game-mode-symbol">◆</span><span><strong>Money debate</strong><small>Agree on a stake and settle a debate.</small></span><span className="game-mode-check">{mode === 'money' ? '●' : '○'}</span>
        </button>
      </div>

      {error && <div className="error-text" role="alert">{error}</div>}

      {mode === 'free' ? (
        <>
          <Explain>Free games never move money and never touch your wallet balance.</Explain>
          <div className="grid grid-auto">
            {(types ?? []).map((t) => {
              const meta = GAME_META[t] ?? { emoji: '🎲', label: t }
              return (
                <button key={t} className="card card-hover" style={{ textAlign: 'center', cursor: 'pointer' }}
                  onClick={() => create.mutate(t)} disabled={create.isPending}>
                  <div style={{ fontSize: '1.8rem' }}>{meta.emoji}</div>
                  <div style={{ fontWeight: 600, marginTop: 8 }}>{meta.label}</div>
                  <div className="dim" style={{ fontSize: '0.75rem', marginTop: 4 }}>{create.isPending ? 'Starting…' : 'Start free game'}</div>
                </button>
              )
            })}
          </div>
        </>
      ) : (
        <section className="money-mode-panel">
          <div className="money-mode-kicker">DEBATE WITH A STAKE</div>
          <h2>Set the terms before the challenge.</h2>
          <p>Choose a debate topic, agree who decides, and set the amount each side commits. The current money flow uses the debate rules and settlement process.</p>
          <div className="money-mode-note"><span aria-hidden="true">ⓘ</span><span>Money mode is available only when live payments and age verification are configured for your account. No game or wallet charge starts from this screen.</span></div>
          <button className="btn btn-primary" onClick={() => navigate('/create?money=1')}>Set up a money debate <span aria-hidden="true">↗</span></button>
        </section>
      )}

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
