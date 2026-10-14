import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './components/Dashboard.jsx'
import InventoryPage from './components/InventoryPage.jsx'
import Toasts from './components/Toasts.jsx'

export default function App() {
  const [page, setPage] = useState('dashboard')
  const [initialStatus, setInitialStatus] = useState('')
  const [options, setOptions] = useState(null)
  const [health, setHealth] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [toasts, setToasts] = useState([])

  const notify = useCallback((type, text) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, type, text }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000)
  }, [])

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setHealth({ status: 'down', database: { error: e.message } }))
    api.options().then(setOptions).catch((e) => notify('error', e.message))
  }, [notify, refreshKey])

  const dataChanged = () => setRefreshKey((k) => k + 1)
  const goInventory = (status = '') => {
    setInitialStatus(status)
    setPage('inventory')
  }

  return (
    <div className="layout">
      <Sidebar page={page} onNavigate={(p) => {
          setInitialStatus('')
          setPage(p)
        }} health={health} />
      <main className="content">
        {health && health.status !== 'ok' && (
          <div className="banner error">
            Database problem: {health.database?.error || 'unknown error'}
          </div>
        )}
        {page === 'dashboard' ? (
          <Dashboard refreshKey={refreshKey} onOpenInventory={goInventory} />
        ) : (
          <InventoryPage
            key={initialStatus}
            initialStatus={initialStatus}
            options={options}
            refreshKey={refreshKey}
            onChanged={dataChanged}
            notify={notify}
          />
        )}
      </main>
      <Toasts toasts={toasts} />
    </div>
  )
}
