import { useEffect, useState } from 'react'
import { api, number, rupees, STATUS_LABEL } from '../api.js'

function Card({ label, value, hint, tone, onClick }) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag className={`card ${tone || ''} ${onClick ? 'clickable' : ''}`} onClick={onClick}>
      <span className="card-label">{label}</span>
      <span className="card-value">{value}</span>
      {hint && <span className="card-hint">{hint}</span>}
    </Tag>
  )
}

export default function Dashboard({ refreshKey, onOpenInventory }) {
  const [stats, setStats] = useState(null)
  const [low, setLow] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setError('')
    Promise.all([api.stats(), api.list({ status: 'low_stock', sort: 'totalStock', limit: 10 })])
      .then(([s, l]) => {
        setStats(s)
        setLow(l.items)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [refreshKey])

  return (
    <section>
      <h1>Dashboard</h1>
      {loading && <p className="muted">Loading statistics…</p>}
      {error && <div className="banner error">{error}</div>}
      {stats && (
        <>
          <div className="cards">
            <Card label="Products" value={number(stats.totalItems)} onClick={() => onOpenInventory('')} />
            <Card label="Units in stock" value={number(stats.totalUnits)} hint="All stores combined" />
            <Card
              label="Low stock"
              value={number(stats.lowStockItems)}
              hint={`${stats.lowStockThreshold} units or fewer`}
              tone="warn"
              onClick={() => onOpenInventory('low_stock')}
            />
            <Card
              label="Out of stock"
              value={number(stats.outOfStockItems)}
              tone="danger"
              onClick={() => onOpenInventory('out_of_stock')}
            />
            <Card label="Value at retail" value={rupees(stats.inventoryValueRetail)} hint="Units × price" />
            <Card label="Value at cost" value={rupees(stats.inventoryValueCost)} hint="Units × cost" />
          </div>

          <h2>Lowest stock</h2>
          {low.length === 0 ? (
            <p className="muted">No items are at or below the low-stock threshold.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU</th>
                    <th className="num">Units</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {low.map((i) => (
                    <tr key={i.id}>
                      <td>{i.name}</td>
                      <td>{i.sku}</td>
                      <td className="num">{i.totalStock}</td>
                      <td>
                        <span className={`badge ${i.stockStatus}`}>{STATUS_LABEL[i.stockStatus]}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}
