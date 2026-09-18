// First-time welcome / how-it-works tour (§55, §56).
import { Link } from 'react-router-dom'
import { Explain } from '../components/ui'

const STEPS = [
  { emoji: '🗣️', title: 'Create a debate', body: 'State the question and the two sides. Pick Local (people vote) or Online Result (a verifiable source decides).' },
  { emoji: '🤝', title: 'Challenge someone', body: 'Invite a friend or another user. Both sides confirm the rules and fund any stake before it locks.' },
  { emoji: '🗳️', title: 'Settle it', body: 'Voters decide, or the agreed settlement source records the result. The winner is calculated automatically.' },
  { emoji: '💰', title: 'Get paid', body: 'Stakes move through a transparent wallet ledger. The platform fee is always shown before you commit.' },
]

export default function Onboarding() {
  return (
    <div className="col" style={{ gap: 24, maxWidth: 720, margin: '0 auto', width: '100%' }}>
      <div className="center">
        <div className="splash-logo" style={{ fontSize: '2.4rem' }}>DS</div>
        <h1 style={{ marginBottom: 4 }}>Welcome to Debate_Settler</h1>
        <p className="muted">Settle any disagreement — fairly, transparently, and once.</p>
      </div>

      <Explain>
        Every debate makes four things obvious: what is being debated, who decides,
        when it ends, and what happens to your money.
      </Explain>

      <div className="col" style={{ gap: 12 }}>
        {STEPS.map((s, i) => (
          <div key={s.title} className="card row" style={{ gap: 16, alignItems: 'flex-start' }}>
            <div style={{ fontSize: '1.8rem' }}>{s.emoji}</div>
            <div>
              <div className="dim" style={{ fontSize: '0.75rem' }}>STEP {i + 1}</div>
              <strong>{s.title}</strong>
              <p className="muted" style={{ margin: '4px 0 0' }}>{s.body}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="row" style={{ gap: 12, justifyContent: 'center' }}>
        <Link className="btn btn-primary" to="/create">Create your first debate</Link>
        <Link className="btn btn-secondary" to="/discover">Browse debates</Link>
      </div>
    </div>
  )
}
