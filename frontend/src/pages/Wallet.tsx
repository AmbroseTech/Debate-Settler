// Wallet: balances, deposit, withdraw, transaction history (§28-§36, §84-§85).
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { friendlyError, walletApi } from '../api/client'
import { Explain, Field, Modal, Spinner, Tooltip } from '../components/ui'
import { formatDateTime, formatMoney, WALLET_EXPLAIN } from '../utils/format'

export default function Wallet() {
  const qc = useQueryClient()
  const [depositOpen, setDepositOpen] = useState(false)
  const [withdrawOpen, setWithdrawOpen] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')

  const { data: wallet, isLoading } = useQuery({ queryKey: ['wallet'], queryFn: walletApi.get })
  const { data: txs } = useQuery({ queryKey: ['transactions'], queryFn: () => walletApi.transactions({ page_size: 30 }) })
  const { data: providers } = useQuery({ queryKey: ['providers'], queryFn: () => walletApi.providers(false) })
  const { data: payoutProviders } = useQuery({ queryKey: ['providers-payout'], queryFn: () => walletApi.providers(true) })

  const refresh = () => { qc.invalidateQueries({ queryKey: ['wallet'] }); qc.invalidateQueries({ queryKey: ['transactions'] }) }

  if (isLoading) return <Spinner />
  if (!wallet) return <div className="card">Wallet unavailable.</div>

  const isDemo = Boolean(providers?.length && providers.every((p) => p.is_demo))

  return (
    <div className="col" style={{ gap: 20, maxWidth: 860, margin: '0 auto', width: '100%' }}>
      <div className="row-between">
        <h1 style={{ margin: 0 }}>💳 Wallet</h1>
        {isDemo && <span className="demo-tag">DEMO FUNDS</span>}
      </div>

      <div className="balance-hero">
        <div className="stat-label">Total Balance</div>
        <div className="balance-amount">{formatMoney(wallet.available_balance, wallet.currency)}</div>
        <div className="row mt-2" style={{ gap: 12, flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={() => { setError(''); setDepositOpen(true) }}>Deposit</button>
          <button className="btn btn-secondary" onClick={() => { setError(''); setWithdrawOpen(true) }}>Withdraw</button>
        </div>
      </div>

      <div className="payment-availability">
        <span className="payment-mark" aria-hidden="true">↗</span>
        <div><strong>Mobile money</strong><p>{providers === undefined ? 'Checking available providers…' : providers.filter((p) => p.code === 'mtn' || p.code === 'airtel').map((p) => p.display_name).join(' · ') || 'No mobile money provider is configured for this account yet.'} <span>{providers?.some((p) => p.code === 'airtel') ? 'Airtel Money enabled' : 'Airtel is coming soon.'}</span></p></div>
      </div>

      {error && <div className="error-text" role="alert">{error}</div>}
      {info && <div className="help-text" style={{ color: 'var(--success)' }} role="status">{info}</div>}

      <div className="grid grid-auto">
        <BalanceTile label="Available" value={wallet.available_balance} currency={wallet.currency} tip={WALLET_EXPLAIN.available} />
        <BalanceTile label="Locked" value={wallet.locked_balance} currency={wallet.currency} tip={WALLET_EXPLAIN.locked} />
        <BalanceTile label="Pending" value={wallet.pending_balance} currency={wallet.currency} tip={WALLET_EXPLAIN.pending} />
        <BalanceTile label="Withdrawable" value={wallet.withdrawable_balance} currency={wallet.currency} tip={WALLET_EXPLAIN.withdrawable} />
      </div>

      <div className="card">
        <h3>Transaction History</h3>
        {txs && txs.items.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead><tr><th>Transaction</th><th>Type</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead>
              <tbody>
                {txs.items.map((t) => (
                  <tr key={t.id}>
                    <td><code style={{ fontSize: '0.8rem' }}>{t.reference}</code>{t.is_demo && <span className="demo-tag" style={{ marginLeft: 6 }}>DEMO</span>}</td>
                    <td style={{ textTransform: 'capitalize' }}>{t.type.replace(/_/g, ' ')}</td>
                    <td>{parseFloat(t.amount) >= 0 ? '+' : '-'} {formatMoney(Math.abs(parseFloat(t.amount)), t.currency)}</td>
                    <td style={{ textTransform: 'capitalize' }}>{t.status.replace(/_/g, ' ')}</td>
                    <td className="dim">{formatDateTime(t.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">No transactions yet.</p>
        )}
      </div>

      <DepositModal open={depositOpen} onClose={() => setDepositOpen(false)} providers={providers ?? []} onDone={(msg: string) => { setInfo(msg); refresh() }} onError={setError} />
      <WithdrawModal open={withdrawOpen} onClose={() => setWithdrawOpen(false)} providers={payoutProviders ?? []} currency={wallet.currency} onDone={(msg: string) => { setInfo(msg); refresh() }} onError={setError} />
    </div>
  )
}

function BalanceTile({ label, value, currency, tip }: { label: string; value: string; currency: string; tip: string }) {
  return (
    <div className="stat">
      <div className="stat-label"><Tooltip text={tip}>{label}</Tooltip></div>
      <div className="stat-value" style={{ fontSize: '1.3rem' }}>{formatMoney(value, currency)}</div>
    </div>
  )
}

function DepositModal({ open, onClose, providers, onDone, onError }: any) {
  const [provider, setProvider] = useState('')
  const [amount, setAmount] = useState('')
  const [destination, setDestination] = useState('')
  const mut = useMutation({
    mutationFn: () => walletApi.deposit({ provider_code: provider || providers[0]?.code, amount, destination: destination || undefined, idempotency_key: crypto.randomUUID() }),
    onSuccess: (res: any) => { onDone(res.is_demo ? 'DEMO FUNDS — simulated deposit added.' : 'Deposit submitted. Awaiting confirmation.'); onClose() },
    onError: (e) => onError(friendlyError(e)),
  })
  return (
    <Modal open={open} onClose={onClose} title="Deposit">
      <Explain>Choose an available method. Your deposit stays pending until the provider confirms it.</Explain>
      {providers.length === 0 && <div className="help-text" role="status">Deposits are not available right now. Airtel is coming soon.</div>}
      <form onSubmit={(e) => { e.preventDefault(); mut.mutate() }}>
        <Field label="Method">
          <select className="select" value={provider || providers[0]?.code || ''} onChange={(e) => setProvider(e.target.value)} disabled={!providers.length}>
            {providers.map((p: any) => <option key={p.code} value={p.code}>{p.display_name}{p.is_demo ? ' (DEMO)' : ''}</option>)}
          </select>
        </Field>
        <Field label="Amount (UGX)">
          <input className="input" type="number" min="100" step="100" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </Field>
        {provider !== 'demo' && (
          <Field label="Mobile number / account" hint="Where the payment request is sent.">
            <input className="input" value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="07XXXXXXXX" />
          </Field>
        )}
        <button className="btn btn-primary btn-block" disabled={mut.isPending || !providers.length}>{mut.isPending ? 'Processing…' : 'Continue'}</button>
      </form>
    </Modal>
  )
}

function WithdrawModal({ open, onClose, providers, currency, onDone, onError }: any) {
  const [provider, setProvider] = useState('')
  const [amount, setAmount] = useState('')
  const [destination, setDestination] = useState('')
  const [quote, setQuote] = useState<any>(null)
  const mut = useMutation({
    mutationFn: () => walletApi.withdraw({ provider_code: provider || providers[0]?.code, amount, destination, idempotency_key: crypto.randomUUID() }),
    onSuccess: (res: any) => { onDone(`Withdrawal ${res.reference} requested — status: ${res.status}.`); onClose() },
    onError: (e) => onError(friendlyError(e)),
  })
  async function loadQuote() {
    if (!amount || parseFloat(amount) <= 0) return
    try { setQuote(await walletApi.withdrawalQuote(parseFloat(amount))) } catch { /* ignore */ }
  }
  return (
    <Modal open={open} onClose={onClose} title="Withdraw">
      <Explain>Withdraw to a supported method. We'll show the fee and what you'll receive before you confirm.</Explain>
      <form onSubmit={(e) => { e.preventDefault(); mut.mutate() }}>
        <Field label="Method">
          <select className="select" value={provider || providers[0]?.code || ''} onChange={(e) => setProvider(e.target.value)} disabled={!providers.length}>
            {providers.map((p: any) => <option key={p.code} value={p.code}>{p.display_name}{p.is_demo ? ' (DEMO)' : ''}</option>)}
          </select>
        </Field>
        <Field label="Destination" hint="Mobile number or bank account.">
          <input className="input" value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="07XXXXXXXX" required />
        </Field>
        <Field label={`Amount (${currency})`}>
          <input className="input" type="number" min="100" step="100" value={amount} onChange={(e) => { setAmount(e.target.value); loadQuote() }} onBlur={loadQuote} required />
        </Field>
        {quote && (
          <div className="card" style={{ background: 'var(--bg-elevated)' }}>
            <div className="row-between"><span className="muted">Amount</span><strong>{formatMoney(quote.amount, currency)}</strong></div>
            <div className="row-between"><span className="muted">Withdrawal fee</span><strong>{formatMoney(quote.fee, currency)}</strong></div>
            <div className="row-between"><span className="muted">You will receive</span><strong style={{ color: 'var(--success)' }}>{formatMoney(quote.net_amount, currency)}</strong></div>
            <div className="help-text">{quote.estimated_processing}</div>
          </div>
        )}
        {!providers.length && <div className="help-text" role="status">Withdrawals are not available right now.</div>}
        <button className="btn btn-primary btn-block mt-2" disabled={mut.isPending || !providers.length}>{mut.isPending ? 'Requesting…' : 'Request Withdrawal'}</button>
      </form>
    </Modal>
  )
}
