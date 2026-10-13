import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// FastAPI backend (backend/main.py). The assignment runs it on port 8000;
// set BACKEND_PORT to point somewhere else, e.g. if 8000 is busy.
const backend = `http://127.0.0.1:${process.env.BACKEND_PORT ?? '8000'}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Not 5173/5174, so this can run next to the Lecture 7 projects.
    port: 5180,
    strictPort: true,
    // Forward API and image requests to the backend so the browser sees one origin.
    proxy: {
      '/api': backend,
      '/images': backend,
    },
  },
})
