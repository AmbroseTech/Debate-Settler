// My Debates: created / participating / won / lost / draws / disputed (§50).
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { debatesApi } from '../api/client'
import DebateCard from '../components/DebateCard'
import { EmptyState, Spinner } from '../components/ui'

const TABS = [
  { key: 'active', label: 'Active' },
  { key: 'voting', label: 'Voting' },
  { key: 'settled', label: 'Settled' },
  { key: 'draw', label: 'Draws' },
  { key: 'disputed', label: 'Disputed' },
  { key: 'all', label: 'All' },
]

export default function MyDebates() {
  const [tab, setTab] = useState('active')
  const { data, isLoading } = useQuery({
    queryKey: ['debates', tab],
    queryFn: () => debatesApi.list(tab === 'all' ? { page_size: 30 } : { status: tab, page_size: 30 }),
  })

  return (
    <div className="col" style={{ gap: 20 }}>
      <div>
        <h1>My Debates</h1>
        <p className="muted">Filter and search the debates you've created or joined.</p>
      </div>

      <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
        {TABS.map((t) => (
          <button key={t.key} className={`btn btn-sm ${tab === t.key ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? <Spinner /> : data && data.items.length > 0 ? (
        <div className="grid grid-auto">{data.items.map((d) => <DebateCard key={d.id} debate={d} />)}</div>
      ) : (
        <EmptyState title="Nothing here yet" subtitle="Debates in this section will appear here." />
      )}
    </div>
  )
}
