import { useState } from 'react'
import { getApiKey, setApiKey } from '../api.js'

const LINKS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'inventory', label: 'Inventory' },
]

export default function Sidebar({ page, onNavigate, health }) {
  const [key, setKey] = useState(getApiKey())
  const connected = health?.status === 'ok'

  return (
    <aside className="sidebar">
      <div className="brand">Inventory</div>
      <nav>
        {LINKS.map((l) => (
          <button
            key={l.id}
            className={`nav-link ${page === l.id ? 'active' : ''}`}
            onClick={() => onNavigate(l.id)}
          >
            {l.label}
          </button>
        ))}
      </nav>
      <div className="sidebar-foot">
        <div className="conn">
          <span className={`dot ${health ? (connected ? 'ok' : 'bad') : ''}`} />
          {health ? (connected ? 'Database connected' : 'Database unavailable') : 'Checking…'}
        </div>
        <label className="key-label">
          Write access key
          <input
            type="password"
            value={key}
            placeholder="API key (for edits)"
            autoComplete="off"
            onChange={(e) => {
              setKey(e.target.value)
              setApiKey(e.target.value)
            }}
          />
        </label>
      </div>
    </aside>
  )
}
