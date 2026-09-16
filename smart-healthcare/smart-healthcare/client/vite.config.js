import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth': 'http://localhost:8000',
      '/assessments': 'http://localhost:8000',
      '/documents': 'http://localhost:8000',
      '/alerts': 'http://localhost:8000',
      '/vitals': 'http://localhost:8000',
      '/risk': 'http://localhost:8000',
      '/uploads': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})