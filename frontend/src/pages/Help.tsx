// Help — plain-English answers to common questions (§29, §74, §99).
import { useState } from 'react'

const FAQ: { q: string; a: string }[] = [
  { q: 'What is a Local Debate?', a: 'A debate where real people watch and vote to decide the winner. Use it when no external source can settle the outcome — like "which presentation was better?". Both sides agree on the number of voters, the start and end time, and the voting rules before it locks.' },
  { q: 'What is an Online Result Debate?', a: 'A debate settled by a verifiable external result — like an official match result. You must agree the settlement source and rule before the debate locks. The system never searches the internet after the fact or guesses a winner; if the source is unavailable it goes Under Review.' },
  { q: 'Can I change my vote?', a: 'By default, no — once submitted your vote is final. A vote can only be changed if both sides explicitly agreed to allow it before the debate started.' },
  { q: 'Is Debate Settler free?', a: 'Yes — completely. There are no wallets, stakes, entry fees, platform fees or payments of any kind. You create debates, invite people and settle results at no cost.' },
  { q: 'What happens on a draw?', a: 'If both sides receive equal votes, the result is a Draw. Whether a draw is allowed is decided by the rules both sides agreed before the debate locked.' },
  { q: 'When can I invite voters?', a: 'Voter invitations are only created after the debate is locked — that is, after both sides have agreed the rules. Before locking you can only invite the opponent to join your side.' },
  { q: 'How many voters do I need?', a: 'You set a required number of voters when you create the debate. A minimum of three valid votes is enforced so a single person can never decide an outcome.' },
  { q: 'How do I dispute a result?', a: 'Open the debate and choose Dispute Result. Add your reason and evidence. A moderator reviews it, and every action is logged. Comments and discussion stay separate from the official vote.' },
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
        <p className="muted">Plain answers about debates, voting and disputes.</p>
      </div>

      <div className="col" style={{ gap: 8 }}>
        {FAQ.map((f) => <Item key={f.q} q={f.q} a={f.a} />)}
      </div>
    </div>
  )
}
