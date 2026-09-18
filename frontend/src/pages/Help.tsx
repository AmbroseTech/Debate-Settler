// Help — plain-English answers to common questions (§29, §74, §99).
import { useState } from 'react'
import { WALLET_EXPLAIN } from '../utils/format'

const FAQ: { q: string; a: string }[] = [
  { q: 'What is a Local Debate?', a: 'A debate where real people watch and vote to decide the winner. Use it when no external source can settle the outcome — like "which presentation was better?". Both sides agree on the number of voters, the start and end time, and the voting rules before it locks.' },
  { q: 'What is an Online Result Debate?', a: 'A debate settled by a verifiable external result — like an official match result or a published price. You must agree the settlement source and rule before the debate locks. The system never searches the internet after the fact or guesses a winner; if the source is unavailable it goes Under Review.' },
  { q: 'Can I change my vote?', a: 'By default, no — once submitted your vote is final. A vote can only be changed if both sides explicitly agreed to allow it before the debate started.' },
  { q: 'What is the platform fee?', a: 'A percentage taken from the total stake pool when a financial debate settles. It is always shown before you commit, recorded in the ledger, and configurable (for example 5%). It is never hidden as a "discount".' },
  { q: 'What happens on a draw?', a: 'If both sides are equal, the result is a Draw. If the agreed rules say stakes are returned, eligible funds go back to the participants. The draw rule is shown before the debate locks.' },
  { q: 'What if one side never funds the stake?', a: 'The debate moves into Funding Timeout. After the waiting period it is cancelled and any funded stake is returned, with a notification and a full transaction record. Funds are never held indefinitely.' },
  { q: 'How do I dispute a result?', a: 'Open the debate and choose Dispute Result. Add your reason and evidence. While a financial dispute is open, the payout is placed On Hold until a moderator completes the review. Every action is logged.' },
  { q: 'Is my money real?', a: 'Financial features are only enabled where legally permitted and properly configured. In demo mode, transactions are clearly marked as simulated and no real money moves. Real payouts always go through configured, verified payment providers — a request is never marked complete just because it was submitted.' },
]

function Item({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <button className="row-between" style={{ width: '100%', padding: 16, background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', textAlign: 'left' }}
        onClick={() => setOpen(!open)} aria-expanded={open}>
        <strong>{q}</strong>
        <span className="dim">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="muted" style={{ padding: '0 16px 16px', lineHeight: 1.7 }}>{a}</div>}
    </div>
  )
}

export default function Help() {
  return (
    <div className="col" style={{ gap: 20, maxWidth: 720, margin: '0 auto', width: '100%' }}>
      <div>
        <h1>Help centre</h1>
        <p className="muted">Plain answers about debates, voting, money and disputes.</p>
      </div>

      <section className="card col" style={{ gap: 6 }}>
        <h2 style={{ fontSize: '1.05rem', margin: 0 }}>Your wallet balances</h2>
        {Object.entries(WALLET_EXPLAIN).map(([k, v]) => (
          <div key={k}><strong style={{ textTransform: 'capitalize' }}>{k}</strong> — <span className="muted">{v}</span></div>
        ))}
      </section>

      <div className="col" style={{ gap: 8 }}>
        {FAQ.map((f) => <Item key={f.q} q={f.q} a={f.a} />)}
      </div>
    </div>
  )
}
