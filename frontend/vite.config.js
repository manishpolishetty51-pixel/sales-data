import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In development, /api calls are proxied to the FastAPI backend, so the browser
// never needs the backend address or any credentials.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
})
