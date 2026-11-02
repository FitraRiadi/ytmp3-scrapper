import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const srcDir = fileURLToPath(new URL('./src', import.meta.url))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': srcDir,
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5233,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8137',
        changeOrigin: true,
      },
    },
  },
  preview: { port: 5233, strictPort: true },
})
