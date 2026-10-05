/**
 * @file Configuración de Vite para el frontend. Registra los plugins de React
 * y Tailwind, expone el servidor de desarrollo en el puerto 3000 con un proxy
 * de `/api` hacia el backend FastAPI, excluye del watcher los documentos de
 * Office y genera el build en `dist` con sourcemaps.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

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
      // El watcher de Vite vigila todo el proyecto por defecto. Un .pptx
      // abierto en PowerPoint queda bloqueado por el sistema operativo
      // (EBUSY) y Vite no maneja ese error, por lo que el proceso entero se
      // detiene. Se excluyen los formatos de Office y sus archivos de
      // bloqueo (~$) para que abrir esos documentos no detenga el servidor
      // de desarrollo.
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
