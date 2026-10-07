/**
 * src/main.tsx — punto de entrada del frontend.
 *
 * Prototipo de un sistema web para predecir el abandono en estudiantes universitarios
 * mediante aprendizaje automático y consulta conversacional.
 * Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
 * Proyecto de titulación · Universidad Estatal de Milagro · 2026
 */
import '@fontsource-variable/inter'
import './estilos/globales.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import { ErrorApi } from './lib/api'
import { ProveedorSesion } from './lib/sesion'
import { ProveedorToast } from './componentes/ui/Toast'

const cliente = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      // No se reintenta lo que el servidor rechazó a propósito (permiso, validación, sesión).
      retry: (intentos, error) => !(error instanceof ErrorApi && error.estado >= 400 && error.estado < 500) && intentos < 2,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={cliente}>
      <BrowserRouter>
        <ProveedorSesion>
          <ProveedorToast>
            <App />
          </ProveedorToast>
        </ProveedorSesion>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
)
