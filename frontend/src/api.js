// Thin client for the FastAPI backend. The API key (for writes only) is entered by the
// user and kept in this browser's localStorage; it is never part of the built bundle.
const KEY_STORAGE = 'inventory_api_key'

export function getApiKey() {
  try {
    return localStorage.getItem(KEY_STORAGE) || ''
  } catch {
    return ''
  }
}

export function setApiKey(value) {
  try {
    if (value) localStorage.setItem(KEY_STORAGE, value)
    else localStorage.removeItem(KEY_STORAGE)
  } catch {
    /* storage unavailable: key lasts for this session only */
  }
}

function messageFromDetail(detail, status) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${(d.loc || []).slice(1).join('.') || 'input'}: ${d.msg}`)
      .join('; ')
  }
  return `Request failed (${status}).`
}

async function request(path, { method = 'GET', body, params, write = false } = {}) {
  const query = new URLSearchParams()
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') query.set(k, v)
  })
  const url = `/api${path}${query.toString() ? `?${query}` : ''}`
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  if (write) headers['X-API-Key'] = getApiKey()

  let res
  try {
    res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined })
  } catch {
    throw new Error('Cannot reach the server. Is the backend running on port 8000?')
  }
  if (res.status === 204) return null
  let data = null
  try {
    data = await res.json()
  } catch {
    /* non-JSON error body */
  }
  if (!res.ok) throw new Error(messageFromDetail(data?.detail, res.status))
  return data
}

export const api = {
  health: () => request('/health'),
  stats: () => request('/inventory/stats'),
  options: () => request('/inventory/options'),
  list: (params) => request('/inventory', { params }),
  create: (body) => request('/inventory', { method: 'POST', body, write: true }),
  update: (id, body) => request(`/inventory/${id}`, { method: 'PUT', body, write: true }),
  remove: (id) => request(`/inventory/${id}`, { method: 'DELETE', write: true }),
}

export const STATUS_LABEL = {
  in_stock: 'In stock',
  low_stock: 'Low stock',
  out_of_stock: 'Out of stock',
}

export const rupees = (n) =>
  n == null ? '—' : new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)

export const number = (n) => (n == null ? '—' : new Intl.NumberFormat('en-IN').format(n))
