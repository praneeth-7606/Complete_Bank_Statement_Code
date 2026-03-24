import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,  // NEW PORT FOR FRESH START
    proxy: {
      '/api': {
        target: 'http://localhost:8080',  // NEW BACKEND PORT
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
