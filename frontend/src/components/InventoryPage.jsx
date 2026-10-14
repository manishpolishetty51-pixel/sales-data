import { useEffect, useState } from 'react'
import { api, number, rupees, STATUS_LABEL } from '../api.js'
import ItemForm from './ItemForm.jsx'
import ConfirmDialog from './ConfirmDialog.jsx'

const PAGE_SIZE = 15
const SORTABLE = { name: 'Product', sku: 'SKU', category: 'Category', totalStock: 'Units', price: 'Price' }

export default function InventoryPage({ initialStatus, options, refreshKey, onChanged, notify }) {
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [department, setDepartment] = useState('')
  const [status, setStatus] = useState(initialStatus)
  const [sort, setSort] = useState('name')
  const [order, setOrder] = useState('asc')
  const [page, setPage] = useState(0)

  const [data, setData] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [editing, setEditing] = useState(null) // null | 'new' | item
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
      .list({ q, category, department, status, sort, order, skip: page * PAGE_SIZE, limit: PAGE_SIZE })
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [q, category, department, status, sort, order, page, refreshKey])

  const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))
  const hasFilters = q || category || department || status

  const toggleSort = (field) => {
    if (sort === field) setOrder(order === 'asc' ? 'desc' : 'asc')
    else {
      setSort(field)
      setOrder('asc')
    }
    setPage(0)
  }

  const reset = () => {
    setSearch('')
    setQ('')
    setCategory('')
    setDepartment('')
    setStatus('')
    setPage(0)
  }

  const save = async (payload) => {
    setBusy(true)
    try {
      if (editing === 'new') {
        const created = await api.create(payload)
        notify('success', `Created "${created.name}" (SKU ${created.sku}).`)
      } else {
        await api.update(editing.id, payload)
        notify('success', `Updated "${payload.name || editing.name}".`)
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
      notify('success', `Deleted "${deleting.name}".`)
      setDeleting(null)
      if (data.items.length === 1 && page > 0) setPage(page - 1)
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
        <h1>Inventory</h1>
        <button className="btn primary" onClick={() => setEditing('new')}>
          + Add item
        </button>
      </div>

      <div className="filters">
        <input
          type="search"
          placeholder="Search name, SKU, category, colour…"
          value={search}
          maxLength={100}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={category} onChange={(e) => { setCategory(e.target.value); setPage(0) }}>
          <option value="">All categories</option>
          {(options?.categories || []).map((c) => <option key={c}>{c}</option>)}
        </select>
        <select value={department} onChange={(e) => { setDepartment(e.target.value); setPage(0) }}>
          <option value="">All departments</option>
          {(options?.departments || []).map((c) => <option key={c}>{c}</option>)}
        </select>
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(0) }}>
          <option value="">Any stock status</option>
          {Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
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
                  className={`sortable ${field === 'price' || field === 'totalStock' ? 'num' : ''}`}
                  onClick={() => toggleSort(field)}
                  aria-sort={sort === field ? (order === 'asc' ? 'ascending' : 'descending') : 'none'}
                >
                  {label} {sort === field ? (order === 'asc' ? '▲' : '▼') : ''}
                </th>
              ))}
              <th>Status</th>
              <th>Suppliers</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.items.map((i) => (
              <tr key={i.id}>
                <td>
                  <strong>{i.name ?? '—'}</strong>
                  <div className="sub">{[i.department, i.colour].filter(Boolean).join(' · ')}</div>
                </td>
                <td>{i.sku ?? '—'}</td>
                <td>{i.category ?? '—'}</td>
                <td className="num" title={Object.entries(i.stock).map(([s, n]) => `${s}: ${n}`).join('\n')}>
                  {number(i.totalStock)}
                </td>
                <td className="num">{rupees(i.price)}</td>
                <td><span className={`badge ${i.stockStatus}`}>{STATUS_LABEL[i.stockStatus]}</span></td>
                <td>{i.suppliers.map((s) => s.name ?? `#${s.id}`).join(', ') || '—'}</td>
                <td className="actions">
                  <button className="btn small" onClick={() => setEditing(i)}>Edit</button>
                  <button className="btn small danger" onClick={() => setDeleting(i)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <p className="muted pad">Loading…</p>}
        {!loading && !error && data.items.length === 0 && (
          <p className="muted pad">
            {hasFilters ? 'No items match your search or filters.' : 'The inventory collection is empty.'}
          </p>
        )}
      </div>

      <div className="pager">
        <span className="muted">{number(data.total)} items</span>
        <button className="btn small" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Page {page + 1} of {pages}</span>
        <button className="btn small" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button>
      </div>

      {editing && (
        <ItemForm
          item={editing === 'new' ? null : editing}
          options={options}
          busy={busy}
          onSave={save}
          onCancel={() => setEditing(null)}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title="Delete item?"
          busy={busy}
          confirmLabel="Delete"
          onConfirm={confirmDelete}
          onCancel={() => setDeleting(null)}
        >
          <p>
            Permanently delete <strong>{deleting.name}</strong> ({deleting.sku}) from the database?
            This cannot be undone.
          </p>
          <p className="muted">
            Past sales, transfers and orders may still refer to this item&apos;s id.
          </p>
        </ConfirmDialog>
      )}
    </section>
  )
}
