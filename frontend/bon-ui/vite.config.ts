import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = process.env.NATUREDESK_BACKEND_URL ?? 'http://127.0.0.1:8001'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  cacheDir: '/tmp/naturedesk-bon-ui-vite-cache-forge-20260616',
  server: {
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
})
