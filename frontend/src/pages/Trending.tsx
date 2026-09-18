// Trending debates (§46) — traditional engagement ranking, no AI.
import { useQuery } from '@tanstack/react-query'
import { debatesApi } from '../api/client'
import DebateCard from '../components/DebateCard'
import { EmptyState, Spinner, Explain } from '../components/ui'

export default function Trending() {
  const { data, isLoading } = useQuery({ queryKey: ['trending'], queryFn: debatesApi.trending })
  return (
    <div className="col" style={{ gap: 20 }}>
      <div>
        <h1>🔥 Trending</h1>
        <p className="muted">Ranked by engagement, votes, participants, views, shares and freshness.</p>
      </div>
      <Explain>Trending uses traditional activity signals — views, votes, shares, participants and how recent a debate is. No AI involved.</Explain>
      {isLoading ? <Spinner /> : data && data.length > 0 ? (
        <div className="grid grid-auto">{data.map((d) => <DebateCard key={d.id} debate={d} />)}</div>
      ) : (
        <EmptyState title="Nothing trending yet" subtitle="Check back soon or create a debate." />
      )}
    </div>
  )
}
