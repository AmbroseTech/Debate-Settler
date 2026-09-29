// Games hub: challenge a friend, play your matches, and view per-game rankings (§6, §7, §8).
// Free social play only — there is no money anywhere on Debate Settler (§51).
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { gamesApi, friendlyError } from '../api/client'
import { useAuth } from '../store/auth'
import { Explain, EmptyState, Spinner } from '../components/ui'
import type { GameInvitation } from '../types'

const GAME_META: Record<string, { emoji: string; label: string; playable: boolean }> = {
  tic_tac_toe: { emoji: '⭕', label: 'Tic-Tac-Toe', playable: true },
  chess: { emoji: '♟️', label: 'Chess', playable: false },
  checkers: { emoji: '🔴', label: 'Checkers', playable: false },
  cards: { emoji: '🃏', label: 'Cards', playable: false },
  connect_four: { emoji: '🟡', label: 'Connect Four', playable: false },
  reversi: { emoji: '⚫', label: 'Reversi', playable: false },
}

interface GameRow { id: string; game_type: string; status: string }

export default function Games() {
  const qc = useQueryClient()
  const { user } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [opponent, setOpponent] = useState('')
  const [invite, setInvite] = useState<GameInvitation | null>(null)
  const [copied, setCopied] = useState(false)

  const { data: games, isLoading } = useQuery({ queryKey: ['games'], queryFn: gamesApi.list })

  const challenge = useMutation({
    mutationFn: () => gamesApi.challenge('tic_tac_toe', opponent.trim() || undefined),
    onSuccess: (res) => { setError(null); setInvite(res); setCopied(false); qc.invalidateQueries({ queryKey: ['games'] }) },
    onError: (e) => { setError(friendlyError(e)); setInvite(null) },
  })

  async function copyLink() {
    if (!invite) return
    try { await navigator.clipboard.writeText(invite.invite_url); setCopied(true) }
    catch { setError('Copy was blocked by your browser. Select the link and copy it manually.') }
  }

  if (isLoading) return <Spinner />

  const whatsapp = invite
    ? `https://wa.me/?text=${encodeURIComponent(`I challenge you to a free Tic-Tac-Toe match on Debate Settler: ${invite.invite_url}`)}`
    : ''

  return (
    <div className="col" style={{ gap: 20 }}>
      <div>
        <h1>🎮 Games</h1>
        <p className="muted">Challenge friends to free, friendly matches and climb the rankings.</p>
      </div>

      <Explain>Games are free play — there is no money, stake or wallet on Debate Settler. Tic-tac-toe is live; more games arrive with their own rule engines.</Explain>

      {error && <div className="error-text" role="alert">{error}</div>}

      {/* Challenge a friend (§8) */}
      <div className="card col" style={{ gap: 12 }}>
        <h3 style={{ margin: 0 }}>Challenge a friend</h3>
        <p className="muted" style={{ margin: 0 }}>
          Enter a username (optional) to send a private challenge, or leave it blank for an open link anyone can use.
        </p>
        <div className="row" style={{ flexWrap: 'wrap' }}>
          <input
            className="input" placeholder="Opponent username (optional)" value={opponent}
            onChange={(e) => setOpponent(e.target.value)} maxLength={50}
          />
          <button className="btn btn-primary" onClick={() => challenge.mutate()} disabled={challenge.isPending}>
            {challenge.isPending ? 'Creating…' : 'Create challenge'}
          </button>
        </div>
        {invite && (
          <div className="col" style={{ gap: 8 }}>
            <input className="input" readOnly value={invite.invite_url} onFocus={(e) => e.target.select()} />
            <div className="row" style={{ flexWrap: 'wrap' }}>
              <button className="btn btn-secondary" onClick={copyLink}>{copied ? 'Copied ✓' : 'Copy link'}</button>
              <a className="btn btn-primary" href={whatsapp} target="_blank" rel="noopener noreferrer">Send on WhatsApp ↗</a>
            </div>
          </div>
        )}
      </div>

      {/* Your matches (§6) */}
      <div className="card col" style={{ gap: 10 }}>
        <h3 style={{ margin: 0 }}>Your matches</h3>
        {games && (games as GameRow[]).length > 0 ? (
          <div className="col" style={{ gap: 8 }}>
            {(games as GameRow[]).map((g) => {
              const meta = GAME_META[g.game_type] ?? { emoji: '🎲', label: g.game_type, playable: false }
              return (
                <div key={g.id} className="row-between">
                  <span>{meta.emoji} {meta.label}</span>
                  {g.status === 'active' || g.status === 'finished'
                    ? <Link className="btn btn-secondary btn-sm" to={`/games/${g.id}`}>{g.status === 'finished' ? 'Review' : 'Play'} →</Link>
                    : <span className="badge badge-waiting">{g.status}</span>}
                </div>
              )
            })}
          </div>
        ) : (
          <EmptyState title="No matches yet" subtitle="Create a challenge above to start playing." />
        )}
      </div>

      <Leaderboard me={user?.username} onChallenge={(name) => { setOpponent(name); window.scrollTo({ top: 0, behavior: 'smooth' }) }} />
    </div>
  )
}

function Leaderboard({ me, onChallenge }: { me?: string; onChallenge: (name: string) => void }) {
  const [gameType, setGameType] = useState('tic_tac_toe')
  const [period, setPeriod] = useState<'all_time' | 'weekly' | 'monthly'>('all_time')
  const { data } = useQuery({
    queryKey: ['leaderboard', gameType, period],
    queryFn: () => gamesApi.leaderboard(gameType, period),
  })
  const meta = GAME_META[gameType] ?? { emoji: '🎲', label: gameType }

  return (
    <div className="card col" style={{ gap: 12 }}>
      <div className="row-between" style={{ flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>{meta.emoji} {meta.label} rankings</h3>
        <div className="row" style={{ gap: 6 }}>
          {(['all_time', 'weekly', 'monthly'] as const).map((p) => (
            <button key={p} className={`btn btn-sm ${period === p ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setPeriod(p)}>
              {p === 'all_time' ? 'All-time' : p === 'weekly' ? 'Weekly' : 'Monthly'}
            </button>
          ))}
        </div>
      </div>

      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
        {Object.entries(GAME_META).map(([key, m]) => (
          <button key={key} className={`btn btn-sm ${gameType === key ? 'btn-secondary' : 'btn-ghost'}`} onClick={() => setGameType(key)}>
            {m.emoji} {m.label}
          </button>
        ))}
      </div>

      {data && data.entries.length > 0 ? (
        <div>
          {data.entries.map((e) => (
            <div key={e.username} className="rank-row">
              <span className="rank-num">{e.rank}</span>
              <span className="avatar-sm" aria-hidden>{(e.display_name || e.username).slice(0, 1).toUpperCase()}</span>
              <div className="col" style={{ flex: 1 }}>
                <strong>{e.username}{e.username === me ? ' (you)' : ''}</strong>
                <span className="dim" style={{ fontSize: '0.75rem' }}>
                  {e.wins}W · {e.losses}L · {e.draws}D · {e.win_pct}%{e.rating != null ? ` · ${e.rating} rating` : ''}
                </span>
              </div>
              {e.username !== me && (
                <button className="btn btn-ghost btn-sm" onClick={() => onChallenge(e.username)}>Challenge</button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="dim" style={{ margin: 0 }}>No ranked games yet — finish a match to appear here.</p>
      )}
    </div>
  )
}
