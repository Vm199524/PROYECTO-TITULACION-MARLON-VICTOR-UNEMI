/**
 * @file Configuración de Vitest. Ejecuta las pruebas del frontend en un DOM
 * simulado (jsdom) con el plugin de React, carga `src/test/setup.js` antes de
 * cada archivo de pruebas y habilita las funciones globales (`describe`, `it`,
 * `expect`).
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    css: true,
    globals: true,
  },
});
