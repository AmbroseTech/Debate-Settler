// Comments & reactions — discussion lives here, entirely separate from the
// official vote (§42). Comments never affect a debate's result.
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { commentsApi, friendlyError, type CommentOut } from '../api/client'
import { formatDate } from '../utils/format'

const REACTIONS = ['like', 'love', 'funny', 'interesting', 'strong', 'disagree']
const REACTION_EMOJI: Record<string, string> = {
  like: '👍', love: '❤️', funny: '😂', interesting: '🤔', strong: '💯', disagree: '👎',
}

export default function Comments({ debateId }: { debateId: string }) {
  const qc = useQueryClient()
  const { data: comments } = useQuery({ queryKey: ['comments', debateId], queryFn: () => commentsApi.list(debateId) })
  const [body, setBody] = useState('')
  const [replyTo, setReplyTo] = useState<CommentOut | null>(null)
  const [error, setError] = useState('')

  const refresh = () => qc.invalidateQueries({ queryKey: ['comments', debateId] })

  const post = useMutation({
    mutationFn: () => commentsApi.create(debateId, body.trim(), replyTo?.id ?? null),
    onSuccess: () => { setBody(''); setReplyTo(null); setError(''); refresh() },
    onError: (e) => setError(friendlyError(e)),
  })

  const react = useMutation({
    mutationFn: ({ commentId, reaction }: { commentId: string; reaction: string }) =>
      commentsApi.react(debateId, commentId, reaction),
    onSuccess: () => refresh(),
    onError: (e) => setError(friendlyError(e)),
  })

  const list = comments ?? []

  return (
    <div className="card col" style={{ gap: 12 }}>
      <h3 style={{ margin: 0 }}>💬 Discussion</h3>
      <p className="help-text">Comments and reactions are separate from voting — they never decide the result.</p>

      {error && <div className="error-text" role="alert">{error}</div>}

      {replyTo && (
        <div className="row-between" style={{ background: 'var(--bg-elevated)', padding: '6px 10px', borderRadius: 8 }}>
          <span className="dim" style={{ fontSize: '.8rem' }}>Replying to @{replyTo.username}</span>
          <button className="btn btn-ghost btn-sm" onClick={() => setReplyTo(null)}>Cancel</button>
        </div>
      )}

      <div className="col" style={{ gap: 8 }}>
        <textarea
          className="input textarea" rows={3} maxLength={2000} value={body}
          placeholder={replyTo ? 'Write a reply…' : 'Add a comment to the discussion…'}
          onChange={(e) => setBody(e.target.value)}
        />
        <div>
          <button className="btn btn-primary btn-sm" disabled={post.isPending || body.trim().length === 0} onClick={() => post.mutate()}>
            {post.isPending ? 'Posting…' : replyTo ? 'Post reply' : 'Post comment'}
          </button>
        </div>
      </div>

      {list.length === 0 ? (
        <p className="muted">No comments yet. Start the discussion.</p>
      ) : (
        <div className="col" style={{ gap: 12 }}>
          {list.map((c) => (
            <div key={c.id} style={c.parent_id ? { marginLeft: 24 } : undefined}>
              <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
                <strong style={{ fontSize: '.9rem' }}>@{c.username ?? 'user'}</strong>
                <span className="dim" style={{ fontSize: '.75rem' }}>{formatDate(c.created_at)}</span>
                {c.pinned && <span className="badge">📌</span>}
              </div>
              <p className="muted" style={{ margin: '4px 0' }}>{c.body}</p>
              <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                {REACTIONS.map((r) => (
                  <button
                    key={r}
                    className="btn btn-ghost btn-sm"
                    onClick={() => react.mutate({ commentId: c.id, reaction: r })}
                    disabled={react.isPending}
                    aria-label={`React ${r}`}
                  >
                    {REACTION_EMOJI[r]} {c.reactions?.[r] ? c.reactions[r] : ''}
                  </button>
                ))}
                {!c.parent_id && (
                  <button className="btn btn-ghost btn-sm" onClick={() => setReplyTo(c)}>↩ Reply</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
