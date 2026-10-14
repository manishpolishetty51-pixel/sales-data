import { useEffect, useState } from 'react'
import { api, formatDate, formatDay, number, rupees } from '../api.js'

function Card({ label, value, hint, onClick }) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag className={`card ${onClick ? 'clickable' : ''}`} onClick={onClick}>
      <span className="card-label">{label}</span>
      <span className="card-value">{value}</span>
      {hint && <span className="card-hint">{hint}</span>}
    </Tag>
  )
}

function Breakdown({ title, rows, total }) {
  return (
    <div className="panel">
      <h2>{title}</h2>
      <div className="table-wrap">
        <table style={{ minWidth: 0 }}>
          <thead>
            <tr>
              <th>Name</th>
              <th className="num">Sales</th>
              <th className="num">Revenue</th>
              <th className="num">Share</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.name ?? 'unknown'}>
                <td>{r.name ?? 'Unknown'}</td>
                <td className="num">{number(r.count)}</td>
                <td className="num">{rupees(r.revenue)}</td>
                <td className="num">{total ? `${((r.revenue / total) * 100).toFixed(1)}%` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Dashboard({ refreshKey, onOpenSales }) {
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setError('')
    Promise.all([api.stats(), api.list({ sort: 'at', order: 'desc', limit: 8 })])
      .then(([s, l]) => {
        setStats(s)
        setRecent(l.sales)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

  return (
    <section>
      <h1>Dashboard</h1>
      {loading && <p className="muted">Loading statistics…</p>}
      {error && <div className="banner error">{error}</div>}
      {stats && stats.totalSales === 0 && <p className="muted">There are no sales recorded yet.</p>}
      {stats && stats.totalSales > 0 && (
        <>
          <div className="cards">
            <Card label="Total sales" value={number(stats.totalSales)} onClick={onOpenSales}
              hint={`${formatDay(stats.firstSaleAt)} – ${formatDay(stats.lastSaleAt)}`} />
            <Card label="Revenue" value={rupees(stats.totalRevenue)} />
            <Card label="Average sale" value={rupees(stats.averageSale)} />
            <Card label="Units sold" value={number(stats.unitsSold)} />
          </div>

          <div className="two-col">
            <Breakdown title="By payment method" rows={stats.byPayment} total={stats.totalRevenue} />
            <Breakdown title="By store" rows={stats.byStore} total={stats.totalRevenue} />
          </div>

          <h2>Latest sales</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Sale</th>
                  <th>Date</th>
                  <th>Store</th>
                  <th>Staff</th>
                  <th className="num">Total</th>
                  <th>Payment</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((s) => (
                  <tr key={s.id}>
                    <td>#{s.id}</td>
                    <td>{formatDate(s.at)}</td>
                    <td>{s.store ?? '—'}</td>
                    <td>{s.staff ?? '—'}</td>
                    <td className="num">{rupees(s.total)}</td>
                    <td><span className={`badge pay-${(s.payment || '').toLowerCase()}`}>{s.payment ?? '—'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
