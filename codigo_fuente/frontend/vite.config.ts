import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [
    tailwindcss(),
    react()
  ],
  server: {
    host: '0.0.0.0',
    port: 3000,
    // El frontend llama siempre a rutas relativas '/api/...' (ver
    // src/constants/appConfig.js); este proxy las envía al backend FastAPI
    // (codigo_fuente/backend, puerto 8090 por defecto).
    //
    // Se usa 127.0.0.1 y no "localhost": en Windows "localhost" puede
    // resolver primero a IPv6 (::1) y, si otro proceso escucha en ese
    // puerto, el proxy le hablaría a él sin mostrar ningún error.
    // El destino se puede cambiar con la variable VITE_BACKEND_URL.
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8090',
        changeOrigin: true,
      },
    },
    watch: {
      // Crash real (10/09/2026): el watcher de Vite vigila TODO el proyecto
      // por defecto. Un .pptx abierto en PowerPoint queda
      // bloqueado por el SO (EBUSY) y Vite no maneja ese error — el proceso
      // entero se cae. Se excluyen los formatos de Office (y
      // sus archivos de bloqueo ~$) para que abrir esos documentos nunca
      // vuelva a tumbar el servidor de desarrollo.
      ignored: [
        '**/*.pptx',
        '**/*.docx',
        '**/*.xlsx',
        '**/~$*',
      ],
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  }
});
