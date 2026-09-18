// About — what Debate_Settler is and the principles it follows (§74, §99).
import { Explain } from '../components/ui'

export default function About() {
  return (
    <div className="col" style={{ gap: 20, maxWidth: 720, margin: '0 auto', width: '100%' }}>
      <div>
        <h1>About Debate_Settler</h1>
        <p className="muted">A social platform to settle any disagreement — fairly, transparently, and once.</p>
      </div>

      <Explain>
        Debate_Settler (DS) combines a social network, a debate platform, a competitive
        challenge arena and a transparent wallet. It is built to make disagreements
        resolvable instead of endless.
      </Explain>

      <section className="card col" style={{ gap: 8 }}>
        <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Four things are always obvious</h2>
        <ul className="muted" style={{ margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
          <li>What exactly is being debated</li>
          <li>Who decides the result</li>
          <li>When it ends</li>
          <li>What happens to your money</li>
        </ul>
      </section>

      <section className="card col" style={{ gap: 8 }}>
        <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Two ways to settle</h2>
        <p className="muted" style={{ margin: 0 }}>
          <strong>Local Debate</strong> — let real people watch and vote. Use it when no
          external source can decide, like "which presentation was better?".
        </p>
        <p className="muted" style={{ margin: 0 }}>
          <strong>Online Result Debate</strong> — let a verifiable result decide. Use it when
          an agreed source settles the outcome, like an official match result. The settlement
          source and rule are locked before the debate starts; the system never guesses.
        </p>
      </section>

      <section className="card col" style={{ gap: 8 }}>
        <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Money, handled honestly</h2>
        <p className="muted" style={{ margin: 0 }}>
          Where financial stakes are used, they are only enabled where legally permitted and
          properly configured. The platform fee is always shown before you commit, every
          movement is recorded in an auditable ledger, and money is never kept without a
          clear status or rule.
        </p>
      </section>

      <p className="dim center" style={{ fontSize: '0.8rem' }}>Powered by VerseTechnologies</p>
    </div>
  )
}
