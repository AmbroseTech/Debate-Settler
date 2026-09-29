// Invitation landing page for /join/:token (§16).
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { debatesApi, friendlyError } from '../api/client'
import { useAuth } from '../store/auth'
import { Explain, Spinner } from '../components/ui'
import { useState } from 'react'

export default function JoinDebate() {
  const { token = '' } = useParams()
  const { user, initialized } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  const accept = useMutation({
    mutationFn: () => debatesApi.acceptInvitation(token),
    onSuccess: (data: { debate_id?: string }) => {
      if (data?.debate_id) navigate(`/debates/${data.debate_id}`)
      else navigate('/discover')
    },
    onError: (e) => setError(friendlyError(e, 'This invitation is not valid or has expired.')),
  })

  const decline = useMutation({
    mutationFn: () => debatesApi.declineInvitation(token),
    onSuccess: () => navigate('/discover'),
    onError: (e) => setError(friendlyError(e, 'This invitation is not valid or has expired.')),
  })

  const pending = accept.isPending || decline.isPending

  const { data: invite } = useQuery({
    queryKey: ['invitation', token],
    queryFn: () => debatesApi.invitationDetails(token),
    enabled: !!token,
    retry: false,
  })
  const isOpponent = invite?.kind === 'opponent'

  if (!initialized) return <Spinner />

  return (
    <div className="center" style={{ minHeight: '70vh', padding: 20 }}>
      <div className="card" style={{ maxWidth: 480, width: '100%', textAlign: 'center' }}>
        <div className="splash-logo" style={{ fontSize: '2rem' }}>DS</div>
        <h2>You've been invited to a debate</h2>
        <Explain>
          An invitation link lets you join as a voter or as the opposing side. You
          must be signed in so we can record your vote once and keep it secure.
        </Explain>

        {error && <div className="error-text" role="alert" style={{ margin: '12px 0' }}>{error}</div>}

        {!user ? (
          <div className="col" style={{ gap: 8, marginTop: 16 }}>
            <Link className="btn btn-primary btn-block" to="/auth">Sign in to join</Link>
            <Link className="btn btn-secondary btn-block" to="/auth">Create an account</Link>
          </div>
        ) : pending ? (
          <Spinner label="Working…" />
        ) : (
          <div className="col" style={{ gap: 8, marginTop: 16 }}>
            <button className="btn btn-primary btn-block" onClick={() => accept.mutate()}>
              {isOpponent ? 'Accept & debate' : 'Accept & join'}
            </button>
            {isOpponent && (
              <button className="btn btn-secondary btn-block" onClick={() => decline.mutate()}>
                Decline challenge
              </button>
            )}
            <Link className="btn btn-ghost btn-block" to="/">Back to home</Link>
          </div>
        )}
      </div>
    </div>
  )
}
