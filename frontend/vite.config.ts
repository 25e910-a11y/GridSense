import { defineConfig, type ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND = 'http://127.0.0.1:8000'

// Some dashboard pages (/faults, /relays, /maintenance, /audit) share a path with
// an API route. When the browser itself opens or refreshes one of those pages it
// asks for HTML, so serve the app instead of forwarding the request to the API.
const api = (): ProxyOptions => ({
  target: BACKEND,
  bypass: (req) => (req.headers.accept?.includes('text/html') ? '/index.html' : undefined),
})

const API_PREFIXES = [
  '/auth',
  '/locations',
  '/devices',
  '/relays',
  '/telemetry',
  '/faults',
  '/dashboard',
  '/maintenance',
  '/notifications',
  '/audit',
  '/health',
]

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: Object.fromEntries(API_PREFIXES.map((prefix) => [prefix, api()])),
  },
})
