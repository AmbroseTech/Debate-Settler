import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { categoriesApi, debatesApi, friendlyError } from '../api/client'
import { Explain, Field } from '../components/ui'
import type { DebateMode } from '../types'

export default function CreateDebate() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<DebateMode>('local')
  const [question, setQuestion] = useState('')
  const [sideA, setSideA] = useState('')
  const [sideB, setSideB] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [startAt, setStartAt] = useState('')
  const [endAt, setEndAt] = useState('')
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC')
  const [requiredVoters, setRequiredVoters] = useState(3)
  const [votesPublic, setVotesPublic] = useState(true)
  const [allowDraw, setAllowDraw] = useState(true)
  const [settlementSource, setSettlementSource] = useState('')
  const [settlementRule, setSettlementRule] = useState('')
  const [isPublic, setIsPublic] = useState(true)
  const [error, setError] = useState('')
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: categoriesApi.list })
  const createMutation = useMutation({
    mutationFn: debatesApi.create,
    onSuccess: (debate) => navigate(`/debates/${debate.id}`),
    onError: (err) => setError(friendlyError(err)),
  })
  function submit() {
    setError('')
    if (question.trim().length < 3 || !sideA.trim() || !sideB.trim()) {
      setError('Add a clear topic and both debate positions.'); return
    }
    if (mode === 'online' && !settlementSource.trim()) {
      setError('Online Result debates need a verifiable result source.'); return
    }
    createMutation.mutate({
      mode, question: question.trim(), side_a_label: sideA.trim(), side_b_label: sideB.trim(),
      category_id: categoryId || null, is_public: isPublic, timezone,
      start_at: startAt ? new Date(startAt).toISOString() : null,
      end_at: endAt ? new Date(endAt).toISOString() : null,
      rules: { required_voters: mode === 'local' ? Math.max(3, requiredVoters) : 3,
        votes_public: votesPublic, allow_draw: allowDraw, venue: null, settlement_source: settlementSource || null,
        settlement_rule: settlementRule || null, event_date: endAt ? new Date(endAt).toISOString() : null },
    })
  }
  return <div className="col" style={{ gap: 20, maxWidth: 780, margin: '0 auto', width: '100%' }}>
    <header><span className="badge">CHALLENGE → AGREE → DEBATE → VOTE</span><h1>Create a debate</h1>
      <p className="muted">Set the topic and positions, then invite an opponent to review and agree on the rules.</p></header>
    <div className="grid grid-2">
      {(['local', 'online'] as DebateMode[]).map((value) => <button key={value} className={`card type-card card-hover ${mode === value ? 'card-active' : ''}`} onClick={() => setMode(value)}>
        <div className="type-emoji">{value === 'local' ? '🌐' : '🔎'}</div><h3>{value === 'local' ? 'COMMUNITY VOTE' : 'ONLINE RESULT'}</h3>
        <p className="muted">{value === 'local' ? 'Invite people to discuss and vote.' : 'Agree on a public source that will decide the result.'}</p>
      </button>)}
    </div>
    <div className="card">
      <Field label="Debate topic"><input className="input" maxLength={500} value={question} onChange={e => setQuestion(e.target.value)} placeholder="Is AI going to replace most software developers?" /></Field>
      <div className="grid grid-2"><Field label="Position A"><input className="input" maxLength={200} value={sideA} onChange={e => setSideA(e.target.value)} placeholder="Yes, most roles will change" /></Field>
        <Field label="Position B"><input className="input" maxLength={200} value={sideB} onChange={e => setSideB(e.target.value)} placeholder="No, developers will adapt" /></Field></div>
      <Field label="Topic category"><select className="select" value={categoryId} onChange={e => setCategoryId(e.target.value)}><option value="">Choose a category (optional)</option>{categories?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
    </div>
    <div className="card"><h3>Agree on a time</h3><div className="grid grid-2"><Field label="Starts"><input className="input" type="datetime-local" value={startAt} onChange={e => setStartAt(e.target.value)} /></Field><Field label="Ends"><input className="input" type="datetime-local" value={endAt} onChange={e => setEndAt(e.target.value)} /></Field></div>
      <Field label="Time zone"><input className="input" value={timezone} onChange={e => setTimezone(e.target.value)} /></Field><Explain>Show this zone to everyone so international participants know exactly when the debate begins.</Explain></div>
    {mode === 'local' ? <div className="card"><h3>Community voting rules</h3><Field label="Minimum voters"><input className="input" type="number" min={3} value={requiredVoters} onChange={e => setRequiredVoters(Math.max(3, Number(e.target.value)))} /></Field>
      <label className="row"><input type="checkbox" checked={votesPublic} onChange={e => setVotesPublic(e.target.checked)} /> Show vote distribution during debate</label><label className="row mt-2"><input type="checkbox" checked={allowDraw} onChange={e => setAllowDraw(e.target.checked)} /> Allow a draw</label>
      <Explain>At least three eligible community members must vote before a result can be finalized. There is no set maximum.</Explain></div> : <div className="card"><h3>Verifiable result rules</h3><Field label="Result source"><input className="input" value={settlementSource} onChange={e => setSettlementSource(e.target.value)} placeholder="Official competition results" /></Field><Field label="How the result decides"><textarea className="textarea" value={settlementRule} onChange={e => setSettlementRule(e.target.value)} /></Field></div>}
    <div className="card"><label className="row"><input type="checkbox" checked={isPublic} onChange={e => setIsPublic(e.target.checked)} /> Make this debate discoverable to the community</label></div>
    {error && <div className="error-text" role="alert">{error}</div>}
    <button className="btn btn-primary" onClick={submit} disabled={createMutation.isPending}>{createMutation.isPending ? 'Creating…' : 'Create debate and invite opponent'}</button>
  </div>
}
