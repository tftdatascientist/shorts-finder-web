import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: {
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  server: {
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/stream': 'http://localhost:8000',
      '/results': 'http://localhost:8000',
      '/history': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
