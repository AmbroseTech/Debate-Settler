// Main dashboard (§83): greeting, wallet, stats, trending, active debates.
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../store/auth'
import { debatesApi, walletApi } from '../api/client'
import DebateCard from '../components/DebateCard'
import { EmptyState, Spinner } from '../components/ui'
import { formatMoney } from '../utils/format'

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
}

export default function Dashboard() {
  const { user } = useAuth()
  const { data: wallet } = useQuery({ queryKey: ['wallet'], queryFn: walletApi.get })
  const { data: trending, isLoading: tLoading } = useQuery({ queryKey: ['trending'], queryFn: debatesApi.trending })
  const { data: active } = useQuery({
    queryKey: ['debates', 'active'],
    queryFn: () => debatesApi.list({ status: 'active', page_size: 6 }),
  })

  const name = user?.profile?.display_name || user?.username || 'there'

  return (
    <div className="col" style={{ gap: 24 }}>
      <div>
        <h1 style={{ marginBottom: 4 }}>{greeting()}, {name} 👋</h1>
        <p className="muted" style={{ margin: 0 }}>Here's what's happening across your debates.</p>
      </div>

      <div className="grid grid-auto">
        <div className="stat">
          <div className="stat-label">Wallet</div>
          <div className="stat-value">{wallet ? formatMoney(wallet.available_balance, wallet.currency) : '—'}</div>
          <Link to="/wallet" className="btn btn-ghost btn-sm" style={{ paddingLeft: 0 }}>View wallet →</Link>
        </div>
        <div className="stat">
          <div className="stat-label">Active Debates</div>
          <div className="stat-value">{active?.total ?? 0}</div>
          <Link to="/my-debates" className="btn btn-ghost btn-sm" style={{ paddingLeft: 0 }}>My debates →</Link>
        </div>
        <div className="stat">
          <div className="stat-label">Locked</div>
          <div className="stat-value">{wallet ? formatMoney(wallet.locked_balance, wallet.currency) : '—'}</div>
          <span className="dim" style={{ fontSize: '0.75rem' }}>Committed to active debates</span>
        </div>
        <div className="stat">
          <div className="stat-label">Pending</div>
          <div className="stat-value">{wallet ? formatMoney(wallet.pending_balance, wallet.currency) : '—'}</div>
          <span className="dim" style={{ fontSize: '0.75rem' }}>Awaiting confirmation</span>
        </div>
      </div>

      <section>
        <div className="row-between mb-2">
          <h2 style={{ margin: 0 }}>🔥 Trending Debates</h2>
          <Link to="/trending" className="btn btn-ghost btn-sm">See all →</Link>
        </div>
        {tLoading ? <Spinner /> : (
          trending && trending.length > 0 ? (
            <div className="grid grid-auto">
              {trending.slice(0, 3).map((d) => <DebateCard key={d.id} debate={d} />)}
            </div>
          ) : (
            <EmptyState
              title="No trending debates yet"
              subtitle="Be the first to create one and settle an argument."
              action={<Link to="/create" className="btn btn-primary">Create a Debate</Link>}
            />
          )
        )}
      </section>

      <section>
        <div className="row-between mb-2">
          <h2 style={{ margin: 0 }}>Your Active Debates</h2>
          <Link to="/my-debates" className="btn btn-ghost btn-sm">See all →</Link>
        </div>
        {active && active.items.length > 0 ? (
          <div className="grid grid-auto">
            {active.items.map((d) => <DebateCard key={d.id} debate={d} />)}
          </div>
        ) : (
          <EmptyState title="No active debates" subtitle="Create a debate or join one to get started." action={<Link to="/create" className="btn btn-primary">Create a Debate</Link>} />
        )}
      </section>
    </div>
  )
}
