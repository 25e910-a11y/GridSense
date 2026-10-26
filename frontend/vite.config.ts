import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/locations': 'http://127.0.0.1:8000',
      '/devices': 'http://127.0.0.1:8000',
      '/relays': 'http://127.0.0.1:8000',
      '/telemetry': 'http://127.0.0.1:8000',
      '/faults': 'http://127.0.0.1:8000',
      '/dashboard': 'http://127.0.0.1:8000',
      '/maintenance': 'http://127.0.0.1:8000',
      '/notifications': 'http://127.0.0.1:8000',
      '/audit': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
