import { useEffect, useState } from 'react'
import { api, endOfDay, formatDate, number, rupees, startOfDay } from '../api.js'
import SaleForm from './SaleForm.jsx'
import ConfirmDialog from './ConfirmDialog.jsx'

const PAGE_SIZE = 15
const SORTABLE = { id: 'Sale', at: 'Date', store: 'Store', staff: 'Staff', total: 'Total', payment: 'Payment' }

export default function SalesPage({ options, refreshKey, onChanged, notify }) {
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const [store, setStore] = useState('')
  const [payment, setPayment] = useState('')
  const [staff, setStaff] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [sort, setSort] = useState('at')
  const [order, setOrder] = useState('desc')
  const [page, setPage] = useState(0)

  const [data, setData] = useState({ sales: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [editing, setEditing] = useState(null) // null | 'new' | sale
  const [deleting, setDeleting] = useState(null)
  const [busy, setBusy] = useState(false)

  // Debounce the search box so we do not query on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(search.trim())
      setPage(0)
    }, 350)
    return () => clearTimeout(t)
  }, [search])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    api
      .list({
        q, store, payment, staff, sort, order,
        start: from ? startOfDay(from) : '',
        end: to ? endOfDay(to) : '',
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      })
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [q, store, payment, staff, from, to, sort, order, page, refreshKey])

  const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))
  const hasFilters = q || store || payment || staff || from || to
  const change = (setter) => (e) => {
    setter(e.target.value)
    setPage(0)
  }

  const toggleSort = (field) => {
    if (sort === field) setOrder(order === 'asc' ? 'desc' : 'asc')
    else {
      setSort(field)
      setOrder(field === 'at' || field === 'total' ? 'desc' : 'asc')
    }
    setPage(0)
  }

  const reset = () => {
    setSearch('')
    setQ('')
    setStore('')
    setPayment('')
    setStaff('')
    setFrom('')
    setTo('')
    setPage(0)
  }

  const save = async (payload) => {
    setBusy(true)
    try {
      if (editing === 'new') {
        const created = await api.create(payload)
        notify('success', `Created sale #${created.id} (${rupees(created.total)}).`)
      } else {
        const updated = await api.update(editing.id, payload)
        notify('success', `Updated sale #${updated.id}. New total ${rupees(updated.total)}.`)
      }
      setEditing(null)
      onChanged()
    } catch (e) {
      notify('error', e.message)
    } finally {
      setBusy(false)
    }
  }

  const confirmDelete = async () => {
    setBusy(true)
    try {
      await api.remove(deleting.id)
      notify('success', `Deleted sale #${deleting.id}.`)
      setDeleting(null)
      if (data.sales.length === 1 && page > 0) setPage(page - 1)
      onChanged()
    } catch (e) {
      notify('error', e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <div className="page-head">
        <h1>Sales</h1>
        <button className="btn primary" onClick={() => setEditing('new')}>+ Add sale</button>
      </div>

      <div className="filters">
        <input
          type="search"
          placeholder="Search sale #, staff, store, product, SKU…"
          value={search}
          maxLength={100}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={store} onChange={change(setStore)}>
          <option value="">All stores</option>
          {(options?.stores || []).map((c) => <option key={c}>{c}</option>)}
        </select>
        <select value={payment} onChange={change(setPayment)}>
          <option value="">Any payment</option>
          {(options?.payments || []).map((c) => <option key={c}>{c}</option>)}
        </select>
        <select value={staff} onChange={change(setStaff)}>
          <option value="">All staff</option>
          {(options?.staff || []).map((c) => <option key={c}>{c}</option>)}
        </select>
        <label className="date-filter">From <input type="date" value={from} max={to || undefined} onChange={change(setFrom)} /></label>
        <label className="date-filter">To <input type="date" value={to} min={from || undefined} onChange={change(setTo)} /></label>
        {hasFilters && <button className="btn" onClick={reset}>Clear</button>}
      </div>

      {error && <div className="banner error">{error}</div>}

      <div className={`table-wrap ${loading ? 'loading' : ''}`}>
        <table>
          <thead>
            <tr>
              {Object.entries(SORTABLE).map(([field, label]) => (
                <th
                  key={field}
                  className={`sortable ${field === 'total' ? 'num' : ''}`}
                  onClick={() => toggleSort(field)}
                  aria-sort={sort === field ? (order === 'asc' ? 'ascending' : 'descending') : 'none'}
                >
                  {label} {sort === field ? (order === 'asc' ? '▲' : '▼') : ''}
                </th>
              ))}
              <th>Items</th>
              <th className="num">Units</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.sales.map((s) => (
              <tr key={s.id}>
                <td>#{s.id}</td>
                <td>{formatDate(s.at)}</td>
                <td>{s.store ?? '—'}</td>
                <td>{s.staff ?? '—'}</td>
                <td className="num">{rupees(s.total)}</td>
                <td><span className={`badge pay-${(s.payment || '').toLowerCase()}`}>{s.payment ?? '—'}</span></td>
                <td title={s.items.map((i) => `${i.name} × ${i.qty} @ ${rupees(i.price)}`).join('\n')}>
                  {s.items[0]?.name ?? '—'}
                  {s.lineCount > 1 && <span className="sub"> +{s.lineCount - 1} more</span>}
                </td>
                <td className="num">{number(s.unitCount)}</td>
                <td className="actions">
                  <button className="btn small" onClick={() => setEditing(s)}>Edit</button>
                  <button className="btn small danger" onClick={() => setDeleting(s)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <p className="muted pad">Loading…</p>}
        {!loading && !error && data.sales.length === 0 && (
          <p className="muted pad">
            {hasFilters ? 'No sales match your search or filters.' : 'There are no sales recorded yet.'}
          </p>
        )}
      </div>

      <div className="pager">
        <span className="muted">{number(data.total)} sales</span>
        <button className="btn small" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Page {page + 1} of {pages}</span>
        <button className="btn small" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button>
      </div>

      {editing && (
        <SaleForm
          sale={editing === 'new' ? null : editing}
          options={options}
          busy={busy}
          onSave={save}
          onCancel={() => setEditing(null)}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title="Delete sale?"
          busy={busy}
          confirmLabel="Delete"
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        >
          <p>
            Permanently delete sale <strong>#{deleting.id}</strong> ({rupees(deleting.total)}, {deleting.store}) from the
            database? This cannot be undone.
          </p>
          <p className="muted">Deleting a sale does not change inventory stock levels.</p>
        </ConfirmDialog>
      )}
    </section>
  )
}
