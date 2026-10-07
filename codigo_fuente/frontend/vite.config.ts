/**
 * vite.config.ts — servidor de desarrollo (puerto 3000) y compilación del frontend.
 *
 * El frontend llama siempre a rutas relativas `/api/...`; en desarrollo este proxy
 * las envía al backend FastAPI (puerto 8090). Se usa 127.0.0.1 y no "localhost"
 * porque en Windows "localhost" puede resolver primero a IPv6 (::1).
 *
 * Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
 */
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': { target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8090', changeOrigin: true },
    },
    // Un .docx o .pptx abierto en Office queda bloqueado (EBUSY) y detendría el watcher.
    watch: { ignored: ['**/*.pptx', '**/*.docx', '**/*.xlsx', '**/~$*'] },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: { manualChunks: { graficos: ['recharts'], react: ['react', 'react-dom', 'react-router-dom'] } },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/pruebas/configuracion.ts'],
    css: false,
  },
})
