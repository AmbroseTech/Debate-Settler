// Debate creation wizard (§10-§21). Guided steps with plain-English help.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { categoriesApi, debatesApi, friendlyError } from '../api/client'
import { Explain, Field } from '../components/ui'
import type { DebateMode } from '../types'

type Step = 0 | 1 | 2 | 3 | 4 | 5 | 6
const STEP_COUNT = 7

export default function CreateDebate() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>(0)
  const [error, setError] = useState('')

  const [mode, setMode] = useState<DebateMode | ''>('')
  const [question, setQuestion] = useState('')
  const [sideA, setSideA] = useState('')
  const [sideB, setSideB] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [startAt, setStartAt] = useState('')
  const [endAt, setEndAt] = useState('')
  const [requiredVoters, setRequiredVoters] = useState(30)
  const [votesPublic, setVotesPublic] = useState(true)
  const [allowDraw, setAllowDraw] = useState(true)
  const [venue, setVenue] = useState('')
  const [city, setCity] = useState('')
  const [country, setCountry] = useState('')
  const [settlementSource, setSettlementSource] = useState('')
  const [settlementRule, setSettlementRule] = useState('')
  const [stake, setStake] = useState('0')
  const [isPublic, setIsPublic] = useState(true)

  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: categoriesApi.list })

  const createMutation = useMutation({
    mutationFn: debatesApi.create,
    onSuccess: (debate) => navigate(`/debates/${debate.id}`),
    onError: (err) => setError(friendlyError(err)),
  })

  function next() { setError(''); setStep((s) => Math.min(s + 1, STEP_COUNT - 1) as Step) }
  function back() { setError(''); setStep((s) => Math.max(s - 1, 0) as Step) }

  function validateStep(): boolean {
    if (step === 0 && !mode) { setError('Choose a debate type to continue.'); return false }
    if (step === 1) {
      if (question.trim().length < 3) { setError('Write a clear debate question.'); return false }
      if (!sideA.trim() || !sideB.trim()) { setError('Both sides need a label.'); return false }
    }
    if (step === 3 && mode === 'online' && !settlementSource.trim()) {
      setError('An Online Result Debate needs an agreed settlement source.'); return false
    }
    return true
  }

  function submit() {
    const rules: Record<string, unknown> = {
      required_voters: mode === 'local' ? requiredVoters : 0,
      votes_public: votesPublic,
      allow_draw: allowDraw,
      venue: venue || null, city: city || null, country: country || null,
      settlement_source: settlementSource || null,
      settlement_rule: settlementRule || null,
      event_date: mode === 'online' && endAt ? new Date(endAt).toISOString() : null,
    }
    createMutation.mutate({
      mode,
      question,
      side_a_label: sideA,
      side_b_label: sideB,
      category_id: categoryId || null,
      is_public: isPublic,
      start_at: startAt ? new Date(startAt).toISOString() : null,
      end_at: endAt ? new Date(endAt).toISOString() : null,
      stake_amount: stake,
      currency: 'UGX',
      rules,
    })
  }

  return (
    <div className="col" style={{ gap: 20, maxWidth: 720, margin: '0 auto', width: '100%' }}>
      <div>
        <h1>Create a Debate</h1>
        <p className="muted">Follow the steps. You can review everything before locking it in.</p>
      </div>

      <div className="wizard-steps" aria-label={`Step ${step + 1} of ${STEP_COUNT}`}>
        {Array.from({ length: STEP_COUNT }).map((_, i) => (
          <div key={i} className={`wizard-step ${i <= step ? 'done' : ''}`} />
        ))}
      </div>

      {error && <div className="error-text" role="alert">{error}</div>}

      {/* Step 0: choose type (§11) */}
      {step === 0 && (
        <div className="grid grid-2">
          <div className={`card type-card card-hover ${mode === 'local' ? 'card-active' : ''}`} onClick={() => setMode('local')} role="button" tabIndex={0} style={{ outline: mode === 'local' ? '2px solid var(--accent)' : 'none' }}>
            <div className="type-emoji">🧑‍🤝‍🧑</div>
            <h3>LOCAL DEBATE</h3>
            <p className="muted">Let real people decide.</p>
            <p className="dim" style={{ fontSize: '0.85rem' }}>Use this when people need to watch, evaluate and vote.</p>
            <div className="explain" style={{ textAlign: 'left' }}>Example: You and a friend disagree about which presentation was better. Invite 30 people to watch and vote.</div>
          </div>
          <div className={`card type-card card-hover`} onClick={() => setMode('online')} role="button" tabIndex={0} style={{ outline: mode === 'online' ? '2px solid var(--accent)' : 'none' }}>
            <div className="type-emoji">🌍</div>
            <h3>ONLINE RESULT DEBATE</h3>
            <p className="muted">Let a verifiable result decide.</p>
            <p className="dim" style={{ fontSize: '0.85rem' }}>Use this when an agreed external result can settle the debate.</p>
            <div className="explain" style={{ textAlign: 'left' }}>Example: You disagree about who will win a future match. Agree on the official result source and let it settle the debate.</div>
          </div>
        </div>
      )}

      {/* Step 1: question + sides (§12, §21) */}
      {step === 1 && (
        <div className="card">
          <h3>Write Your Debate</h3>
          <Explain>State exactly what's being debated. Keep it clear so voters and the settlement source match it.</Explain>
          <Field label="Debate question" hint={mode === 'online' ? 'e.g. Manchester United will beat Arsenal in the next match.' : 'e.g. Which presentation was better?'}>
            <input className="input" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="What are you settling?" />
          </Field>
          <div className="grid grid-2">
            <Field label={mode === 'online' ? 'Side A (YES)' : 'Side A'}>
              <input className="input" value={sideA} onChange={(e) => setSideA(e.target.value)} placeholder={mode === 'online' ? 'YES' : 'Team Alpha'} />
            </Field>
            <Field label={mode === 'online' ? 'Side B (NO)' : 'Side B'}>
              <input className="input" value={sideB} onChange={(e) => setSideB(e.target.value)} placeholder={mode === 'online' ? 'NO' : 'Team Beta'} />
            </Field>
          </div>
          <Field label="Category">
            <select className="select" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
              <option value="">Select a category (optional)</option>
              {categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
        </div>
      )}

      {/* Step 2: time (§14) */}
      {step === 2 && (
        <div className="card">
          <h3>Set Time</h3>
          <Explain>The debate only accepts votes between the agreed start and end times. The server clock is authoritative — never your device.</Explain>
          <div className="grid grid-2">
            <Field label="Starts">
              <input className="input" type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} />
            </Field>
            <Field label="Ends">
              <input className="input" type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} />
            </Field>
          </div>
        </div>
      )}

      {/* Step 3: audience / settlement rule (§13, §15, §21) */}
      {step === 3 && (
        <div className="card">
          <h3>{mode === 'local' ? 'Set Audience & Rules' : 'Set Settlement Rule'}</h3>
          {mode === 'local' ? (
            <>
              <Explain>Both sides must agree on the number of voters before the debate can be locked. After agreement it can't be secretly changed.</Explain>
              <Field label="Number of voters / judges">
                <select className="select" value={requiredVoters} onChange={(e) => setRequiredVoters(Number(e.target.value))}>
                  {[10, 20, 30, 50, 100].map((n) => <option key={n} value={n}>{n} voters</option>)}
                  <option value={5}>5 (custom small)</option>
                </select>
              </Field>
              <Field label="Vote count visibility">
                <select className="select" value={votesPublic ? 'public' : 'hidden'} onChange={(e) => setVotesPublic(e.target.value === 'public')}>
                  <option value="public">Public vote count</option>
                  <option value="hidden">Hidden until debate closes</option>
                </select>
              </Field>
              <label className="row" style={{ gap: 8, marginBottom: 12 }}>
                <input type="checkbox" checked={allowDraw} onChange={(e) => setAllowDraw(e.target.checked)} />
                <span>Allow a draw (tie)</span>
              </label>
              <div className="grid grid-2">
                <Field label="Venue (optional)"><input className="input" value={venue} onChange={(e) => setVenue(e.target.value)} placeholder="Bushenyi Community Hall" /></Field>
                <Field label="City"><input className="input" value={city} onChange={(e) => setCity(e.target.value)} placeholder="Bushenyi" /></Field>
              </div>
              <Field label="Country"><input className="input" value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Uganda" /></Field>
            </>
          ) : (
            <>
              <Explain>The settlement source and rule must be agreed before locking. The system never randomly searches the internet after the debate ends.</Explain>
              <Field label="Settlement source" hint="e.g. Official match result, official competition result, recognized public data.">
                <input className="input" value={settlementSource} onChange={(e) => setSettlementSource(e.target.value)} placeholder="Official match result" />
              </Field>
              <Field label="Settlement rule" hint="Describe exactly how the result maps to a winner.">
                <textarea className="textarea" value={settlementRule} onChange={(e) => setSettlementRule(e.target.value)} placeholder="YES wins if the official result records Manchester United as the winner." />
              </Field>
            </>
          )}
        </div>
      )}

      {/* Step 4: stake (§24, §25) */}
      {step === 4 && (
        <div className="card">
          <h3>Set Stake</h3>
          <Explain>Financial stakes are only enabled where legally permitted and configured. Set 0 for a free/social debate.</Explain>
          <Field label="Stake per side (UGX)" hint="Each side locks this amount. Total pool = 2 × stake.">
            <input className="input" type="number" min="0" step="100" value={stake} onChange={(e) => setStake(e.target.value)} />
          </Field>
          {parseFloat(stake) > 0 && (
            <div className="card" style={{ background: 'var(--bg-elevated)' }}>
              <div className="row-between"><span className="muted">Total pool</span><strong>UGX {(parseFloat(stake) * 2).toLocaleString()}</strong></div>
              <div className="row-between"><span className="muted">Platform fee (5%)</span><strong>UGX {(parseFloat(stake) * 2 * 0.05).toLocaleString()}</strong></div>
              <div className="row-between"><span className="muted">Estimated winner settlement</span><strong style={{ color: 'var(--success)' }}>UGX {(parseFloat(stake) * 2 * 0.95).toLocaleString()}</strong></div>
            </div>
          )}
        </div>
      )}

      {/* Step 5: visibility */}
      {step === 5 && (
        <div className="card">
          <h3>Visibility</h3>
          <Explain>Public debates appear in Discover, Trending, Categories and Search. Private debates are only accessible to invited users.</Explain>
          <label className="row" style={{ gap: 8 }}>
            <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
            <span>Make this debate public</span>
          </label>
        </div>
      )}

      {/* Step 6: review (§99) */}
      {step === 6 && (
        <div className="card">
          <h3>Review</h3>
          <Explain>Before you commit, make sure these four answers are clear.</Explain>
          <table className="table">
            <tbody>
              <tr><td className="muted">What's being debated?</td><td><strong>{question}</strong></td></tr>
              <tr><td className="muted">Who decides?</td><td>{mode === 'local' ? `${requiredVoters} invited voters` : `Settlement source: ${settlementSource}`}</td></tr>
              <tr><td className="muted">When does it end?</td><td>{endAt ? new Date(endAt).toLocaleString() : '—'}</td></tr>
              <tr><td className="muted">What happens to money?</td><td>{parseFloat(stake) > 0 ? `Each side locks UGX ${parseFloat(stake).toLocaleString()}; winner gets the pool minus 5% fee.` : 'No financial stake — free debate.'}</td></tr>
              <tr><td className="muted">Type</td><td>{mode === 'local' ? 'Local Debate' : 'Online Result Debate'}</td></tr>
              <tr><td className="muted">Sides</td><td>{sideA} VS {sideB}</td></tr>
            </tbody>
          </table>
        </div>
      )}

      <div className="row-between">
        <button className="btn btn-secondary" onClick={back} disabled={step === 0}>← Back</button>
        {step < STEP_COUNT - 1 ? (
          <button className="btn btn-primary" onClick={() => validateStep() && next()}>Continue →</button>
        ) : (
          <button className="btn btn-primary" onClick={submit} disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creating…' : 'Create Debate'}
          </button>
        )}
      </div>
    </div>
  )
}
