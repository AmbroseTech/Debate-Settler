// Discover: browse/search public debates with filters (§47, §88).
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { debatesApi } from '../api/client'
import DebateCard from '../components/DebateCard'
import { EmptyState, Spinner } from '../components/ui'
import type { DebateMode, DebateStatus } from '../types'

export default function Discover() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const mode = (params.get('mode') as DebateMode | null) ?? undefined
  const status = (params.get('status') as DebateStatus | null) ?? undefined
  const page = parseInt(params.get('page') ?? '1', 10)

  const [searchInput, setSearchInput] = useState(q)

  const { data, isLoading } = useQuery({
    queryKey: ['discover', q, mode, status, page],
    queryFn: () =>
      q
        ? debatesApi.search(q, { mode, status, page, page_size: 12 })
        : debatesApi.list({ mode, status, page, page_size: 12 }),
  })

  function update(next: Record<string, string | undefined>) {
    const p = new URLSearchParams(params)
    Object.entries(next).forEach(([k, v]) => (v ? p.set(k, v) : p.delete(k)))
    if (!next.page) p.set('page', '1')
    setParams(p)
  }

  return (
    <div className="col" style={{ gap: 20 }}>
      <div>
        <h1>Discover Debates</h1>
        <p className="muted">Browse public debates, filter by mode or status, and join the ones that interest you.</p>
      </div>

      <form
        className="row"
        onSubmit={(e) => { e.preventDefault(); update({ q: searchInput || undefined }) }}
        role="search"
        style={{ flexWrap: 'wrap' }}
      >
        <input
          className="input grow"
          placeholder="Search by question or side…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          aria-label="Search debates"
          style={{ minWidth: 200 }}
        />
        <select className="select" style={{ width: 'auto' }} value={mode ?? ''} onChange={(e) => update({ mode: e.target.value || undefined })} aria-label="Filter by mode">
          <option value="">All modes</option>
          <option value="local">Local Debate</option>
          <option value="online">Online Result</option>
        </select>
        <select className="select" style={{ width: 'auto' }} value={status ?? ''} onChange={(e) => update({ status: e.target.value || undefined })} aria-label="Filter by status">
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="active">Active</option>
          <option value="voting">Voting</option>
          <option value="settled">Settled</option>
        </select>
        <button className="btn btn-primary">Search</button>
      </form>

      {isLoading ? <Spinner /> : data && data.items.length > 0 ? (
        <>
          <div className="grid grid-auto">
            {data.items.map((d) => <DebateCard key={d.id} debate={d} />)}
          </div>
          {data.pages > 1 && (
            <div className="row center" style={{ justifyContent: 'center', gap: 8 }}>
              <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => update({ page: String(page - 1) })}>← Prev</button>
              <span className="muted">Page {data.page} of {data.pages}</span>
              <button className="btn btn-secondary btn-sm" disabled={page >= data.pages} onClick={() => update({ page: String(page + 1) })}>Next →</button>
            </div>
          )}
        </>
      ) : (
        <EmptyState title="No debates found" subtitle="Try a different search, or create the first debate." />
      )}
    </div>
  )
}
