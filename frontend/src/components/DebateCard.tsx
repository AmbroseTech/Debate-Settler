// Debate card — immediately shows what's debated, who decides, and when it ends
// (§48, §86, §87, §99). Debate Settler is free — there is no money involved.
import { Link } from 'react-router-dom'
import type { DebateBrief } from '../types'
import { timeUntil } from '../utils/format'
import StatusBadge from './StatusBadge'

export default function DebateCard({ debate }: { debate: DebateBrief }) {
  const isLocal = debate.mode === 'local'

  return (
    <article className="card card-hover debate-card">
      <div className="row-between">
        <span className="badge">{isLocal ? 'LOCAL DEBATE' : 'ONLINE RESULT DEBATE'}</span>
        <StatusBadge status={debate.status} />
      </div>

      {debate.category_name && <span className="dim" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{debate.category_name}</span>}

      <div className="debate-vs">
        <span className="debate-side">{debate.side_a_label}</span>
        <span className="debate-vs-sep">VS</span>
        <span className="debate-side">{debate.side_b_label}</span>
      </div>

      <p className="muted" style={{ margin: 0, fontSize: '0.9rem' }}>“{debate.question}”</p>

      <div className="debate-meta">
        {isLocal ? (
          <>
            <span>🗳️ {debate.votes_count}/{debate.required_voters || '∞'} voters</span>
            {debate.venue_city && <span>📍 {debate.venue_city}</span>}
          </>
        ) : (
          <>
            {debate.settlement_source && <span>🌍 {debate.settlement_source}</span>}
          </>
        )}
        <span>⏱️ {isLocal ? 'Ends' : 'Event'}: {timeUntil(debate.end_at)}</span>
        <span>👥 {debate.participants_count}</span>
      </div>

      <Link to={`/debates/${debate.id}`} className="btn btn-secondary btn-block">
        {isLocal ? 'View / Join Debate' : 'View Debate'}
      </Link>
    </article>
  )
}
