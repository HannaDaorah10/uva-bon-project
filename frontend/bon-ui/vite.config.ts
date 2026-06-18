import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = process.env.NATUREDESK_BACKEND_URL ?? 'http://127.0.0.1:8001'
const cacheOwner = process.env.USER ?? 'local'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  cacheDir: `/tmp/naturedesk-bon-ui-vite-cache-${cacheOwner}`,
  server: {
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
})
