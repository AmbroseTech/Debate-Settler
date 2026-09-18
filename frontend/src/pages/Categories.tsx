// Categories browser (§8).
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { categoriesApi } from '../api/client'
import { Spinner, EmptyState } from '../components/ui'

export default function Categories() {
  const { data, isLoading } = useQuery({ queryKey: ['categories'], queryFn: categoriesApi.list })
  return (
    <div className="col" style={{ gap: 20 }}>
      <div>
        <h1>🗂️ Categories</h1>
        <p className="muted">Pick a category to see debates people are settling right now.</p>
      </div>
      {isLoading ? <Spinner /> : data && data.length > 0 ? (
        <div className="grid grid-auto">
          {data.map((c) => (
            <Link key={c.id} to={`/discover?category=${c.id}`} className="card card-hover" style={{ textAlign: 'center', textDecoration: 'none', color: 'inherit' }}>
              <div style={{ fontSize: '1.6rem' }}>{c.icon ?? '🏷️'}</div>
              <div style={{ fontWeight: 600, marginTop: 8 }}>{c.name}</div>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="No categories yet" subtitle="Categories appear once the platform is seeded." />
      )}
    </div>
  )
}
