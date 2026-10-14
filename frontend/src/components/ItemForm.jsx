import { useState } from 'react'

const TEXT_FIELDS = [
  ['name', 'Product name', true],
  ['sku', 'SKU', true],
  ['category', 'Category', true],
  ['department', 'Department', true],
  ['subCategory', 'Sub-category'],
  ['type', 'Type'],
  ['style', 'Style'],
  ['fabric', 'Fabric'],
  ['occasion', 'Occasion'],
  ['colour', 'Colour'],
  ['sizes', 'Sizes'],
]

const isWhole = (v) => /^\d+$/.test(String(v).trim())

export default function ItemForm({ item, options, busy, onSave, onCancel }) {
  const stores = options?.stores || []
  const [form, setForm] = useState(() => {
    const f = { price: item?.price ?? '', cost: item?.cost ?? '' }
    TEXT_FIELDS.forEach(([k]) => (f[k] = item?.[k] ?? ''))
    f.stock = Object.fromEntries(stores.map((s) => [s, item?.stock?.[s] ?? (item ? '' : 0)]))
    f.suppliers = (item?.suppliers || []).map((s) => s.id)
    return f
  })
  const [errors, setErrors] = useState({})

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const validate = () => {
    const e = {}
    TEXT_FIELDS.forEach(([k, label, required]) => {
      if (required && !String(form[k]).trim()) e[k] = `${label} is required.`
    })
    if (!isWhole(form.price)) e.price = 'Price must be a whole number, 0 or more.'
    if (!isWhole(form.cost)) e.cost = 'Cost must be a whole number, 0 or more.'
    Object.entries(form.stock).forEach(([s, v]) => {
      if (!isWhole(v)) e[`stock.${s}`] = 'Whole number, 0 or more.'
    })
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const submit = (ev) => {
    ev.preventDefault()
    if (!validate()) return
    const payload = { price: Number(form.price), cost: Number(form.cost) }
    TEXT_FIELDS.forEach(([k]) => {
      const v = String(form[k]).trim()
      if (v) payload[k] = v // blank fields are omitted, so existing values are never erased
    })
    payload.stock = Object.fromEntries(Object.entries(form.stock).map(([s, v]) => [s, Number(v)]))
    payload.suppliers = form.suppliers
    onSave(payload)
  }

  const toggleSupplier = (id) =>
    set('suppliers', form.suppliers.includes(id) ? form.suppliers.filter((x) => x !== id) : [...form.suppliers, id])

  return (
    <div className="overlay">
      <form className="modal" onSubmit={submit} noValidate>
        <h2>{item ? `Edit ${item.name}` : 'Add inventory item'}</h2>

        <div className="grid">
          {TEXT_FIELDS.map(([k, label, required]) => (
            <label key={k}>
              {label}{required && ' *'}
              <input
                value={form[k]}
                maxLength={120}
                list={k === 'category' ? 'cats' : k === 'department' ? 'depts' : undefined}
                onChange={(e) => set(k, e.target.value)}
              />
              {errors[k] && <span className="err">{errors[k]}</span>}
            </label>
          ))}
          <label>
            Price (₹) *
            <input inputMode="numeric" value={form.price} onChange={(e) => set('price', e.target.value)} />
            {errors.price && <span className="err">{errors.price}</span>}
          </label>
          <label>
            Cost (₹) *
            <input inputMode="numeric" value={form.cost} onChange={(e) => set('cost', e.target.value)} />
            {errors.cost && <span className="err">{errors.cost}</span>}
          </label>
        </div>
        <datalist id="cats">{(options?.categories || []).map((c) => <option key={c} value={c} />)}</datalist>
        <datalist id="depts">{(options?.departments || []).map((c) => <option key={c} value={c} />)}</datalist>

        <h3>Stock by store</h3>
        <div className="grid">
          {stores.map((s) => (
            <label key={s}>
              {s}
              <input
                inputMode="numeric"
                value={form.stock[s]}
                onChange={(e) => set('stock', { ...form.stock, [s]: e.target.value })}
              />
              {errors[`stock.${s}`] && <span className="err">{errors[`stock.${s}`]}</span>}
            </label>
          ))}
        </div>

        <h3>Suppliers</h3>
        <div className="checks">
          {(options?.suppliers || []).map((s) => (
            <label key={s.id} className="check">
              <input type="checkbox" checked={form.suppliers.includes(s.id)} onChange={() => toggleSupplier(s.id)} />
              {s.name}
            </label>
          ))}
        </div>

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="submit" className="btn primary" disabled={busy}>
            {busy ? 'Saving…' : item ? 'Save changes' : 'Create item'}
          </button>
        </div>
      </form>
    </div>
  )
}
