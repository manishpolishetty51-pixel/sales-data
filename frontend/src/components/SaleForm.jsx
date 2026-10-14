import { useState } from 'react'
import { rupees, toLocalInput } from '../api.js'

const isWhole = (v, min) => /^\d+$/.test(String(v).trim()) && Number(v) >= min
const blankLine = () => ({ id: '', sku: '', name: '', category: '', qty: 1, price: '' })

export default function SaleForm({ sale, options, busy, onSave, onCancel }) {
  const [form, setForm] = useState(() => ({
    store: sale?.store ?? '',
    staff: sale?.staff ?? '',
    payment: sale?.payment ?? '',
    at: toLocalInput(sale?.at ?? Date.now()),
    items: sale?.items?.length
      ? sale.items.map((i) => ({ id: i.id, sku: i.sku, name: i.name, category: i.category, qty: i.qty, price: i.price }))
      : [blankLine()],
  }))
  const [errors, setErrors] = useState({})

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))
  const setLine = (idx, k, v) =>
    set('items', form.items.map((line, i) => (i === idx ? { ...line, [k]: v } : line)))

  const total = form.items.reduce((sum, l) => {
    const q = Number(l.qty)
    const p = Number(l.price)
    return sum + (Number.isFinite(q) && Number.isFinite(p) ? q * p : 0)
  }, 0)

  const validate = () => {
    const e = {}
    if (!form.store.trim()) e.store = 'Store is required.'
    if (!form.staff.trim()) e.staff = 'Staff is required.'
    if (!form.payment) e.payment = 'Choose a payment method.'
    if (!form.at || Number.isNaN(new Date(form.at).getTime())) e.at = 'Enter a valid date and time.'
    if (form.items.length === 0) e.items = 'Add at least one line item.'
    form.items.forEach((l, i) => {
      if (!isWhole(l.id, 1)) e[`id.${i}`] = 'Item id: whole number ≥ 1.'
      ;['sku', 'name', 'category'].forEach((k) => {
        if (!String(l[k]).trim()) e[`${k}.${i}`] = 'Required.'
      })
      if (!isWhole(l.qty, 1)) e[`qty.${i}`] = 'Whole number ≥ 1.'
      if (!isWhole(l.price, 0)) e[`price.${i}`] = 'Whole number ≥ 0.'
    })
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const submit = (ev) => {
    ev.preventDefault()
    if (!validate()) return
    onSave({
      store: form.store.trim(),
      staff: form.staff.trim(),
      payment: form.payment,
      at: new Date(form.at).getTime(),
      items: form.items.map((l) => ({
        id: Number(l.id),
        sku: String(l.sku).trim(),
        name: String(l.name).trim(),
        category: String(l.category).trim(),
        qty: Number(l.qty),
        price: Number(l.price),
      })),
    })
  }

  return (
    <div className="overlay">
      <form className="modal wide" onSubmit={submit} noValidate>
        <h2>{sale ? `Edit sale #${sale.id}` : 'Add sale'}</h2>

        <div className="grid">
          <label>
            Store *
            <select value={form.store} onChange={(e) => set('store', e.target.value)}>
              <option value="">Select…</option>
              {(options?.stores || []).map((s) => <option key={s}>{s}</option>)}
            </select>
            {errors.store && <span className="err">{errors.store}</span>}
          </label>
          <label>
            Staff *
            <input value={form.staff} maxLength={120} list="staff-list" onChange={(e) => set('staff', e.target.value)} />
            <datalist id="staff-list">{(options?.staff || []).map((s) => <option key={s} value={s} />)}</datalist>
            {errors.staff && <span className="err">{errors.staff}</span>}
          </label>
          <label>
            Payment *
            <select value={form.payment} onChange={(e) => set('payment', e.target.value)}>
              <option value="">Select…</option>
              {(options?.payments || []).map((s) => <option key={s}>{s}</option>)}
            </select>
            {errors.payment && <span className="err">{errors.payment}</span>}
          </label>
          <label>
            Date and time *
            <input type="datetime-local" value={form.at} onChange={(e) => set('at', e.target.value)} />
            {errors.at && <span className="err">{errors.at}</span>}
          </label>
        </div>

        <h3>Line items</h3>
        {errors.items && <span className="err">{errors.items}</span>}
        {form.items.map((l, i) => (
          <div className="line" key={i}>
            {[['id', 'Item id'], ['sku', 'SKU'], ['name', 'Product name'], ['category', 'Category'],
              ['qty', 'Qty'], ['price', 'Unit price (₹)']].map(([k, label]) => (
              <label key={k} className={`line-${k}`}>
                {label}
                <input
                  value={l[k]}
                  inputMode={['id', 'qty', 'price'].includes(k) ? 'numeric' : undefined}
                  maxLength={120}
                  onChange={(e) => setLine(i, k, e.target.value)}
                />
                {errors[`${k}.${i}`] && <span className="err">{errors[`${k}.${i}`]}</span>}
              </label>
            ))}
            <button
              type="button"
              className="btn small danger"
              disabled={form.items.length === 1}
              onClick={() => set('items', form.items.filter((_, idx) => idx !== i))}
              aria-label={`Remove line ${i + 1}`}
            >
              Remove
            </button>
          </div>
        ))}
        <button type="button" className="btn small" onClick={() => set('items', [...form.items, blankLine()])}>
          + Add line
        </button>

        <p className="total-line">
          Total (calculated): <strong>{rupees(total)}</strong>
        </p>

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="submit" className="btn primary" disabled={busy}>
            {busy ? 'Saving…' : sale ? 'Save changes' : 'Create sale'}
          </button>
        </div>
      </form>
    </div>
  )
}
