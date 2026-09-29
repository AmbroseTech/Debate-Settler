// About — what Debate Settler is and the principles it follows (§74, §99).
import { Explain } from '../components/ui'

export default function About() {
  return (
    <div className="col" style={{ gap: 20, maxWidth: 720, margin: '0 auto', width: '100%' }}>
      <div>
        <h1>About Debate Settler</h1>
        <p className="muted">A free social platform to settle any disagreement — fairly, transparently, and once.</p>
      </div>

      <Explain>
        Debate Settler (DS) combines a social network, a debate platform and a
        competitive challenge arena. It is built to make disagreements
        resolvable instead of endless — and it is completely free. There are no
        wallets, stakes or payments.
      </Explain>

      <section className="card col" style={{ gap: 8 }}>
        <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Four things are always obvious</h2>
        <ul className="muted" style={{ margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
          <li>What exactly is being debated</li>
          <li>Who decides the result</li>
          <li>When it ends</li>
          <li>How the result is reached</li>
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
        <h2 style={{ fontSize: '1.1rem', margin: 0 }}>Results, handled honestly</h2>
        <p className="muted" style={{ margin: 0 }}>
          Every debate makes its rules, decision method and deadline clear before it locks.
          Votes are authenticated, counted and never manipulated by the platform, and the
          winner is derived from the rules the participants agreed to — never decided in
          secret.
        </p>
      </section>

      <p className="dim center" style={{ fontSize: '0.8rem' }}>Powered by VerseTechnologies</p>
    </div>
  )
}
