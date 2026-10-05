/**
 * @file Punto de entrada del frontend. Monta `App` en el elemento `#root` de
 * index.html, inicializa Sentry cuando existe `VITE_SENTRY_DSN`, envuelve la
 * interfaz en un ErrorBoundary y registra el Service Worker de la PWA solo en
 * producción.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import * as Sentry from "@sentry/react";
import App from './App.jsx'
import './index.css'

// Sentry captura errores en producción. El DSN se lee de VITE_SENTRY_DSN
// (ver frontend/.env.example) y Sentry solo se inicializa si hay un valor
// real: con un DSN inválido, Sentry.init() no falla y pierde los eventos en
// silencio. Sin DSN, la aplicación funciona igual, solo que sin reportar
// errores.
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN || '';

if (SENTRY_DSN) {
    Sentry.init({
        dsn: SENTRY_DSN,
        environment: import.meta.env.MODE || 'production',
        integrations: [
            Sentry.browserTracingIntegration(),
            Sentry.replayIntegration(),
        ],
        tracesSampleRate: 1.0,
        replaysSessionSampleRate: 0.1,
        replaysOnErrorSampleRate: 1.0,
    });
} else if (import.meta.env.PROD) {
    console.warn(
        'VicMar Data AI: VITE_SENTRY_DSN no está configurado. El sistema funciona ' +
        'con normalidad, pero los errores en producción no se reportarán a Sentry.'
    );
}

// ErrorBoundary de Sentry: si un componente lanza una excepción no capturada,
// el usuario ve un mensaje entendible en lugar de una pantalla en blanco y,
// si hay DSN, el error se reporta automáticamente.
ReactDOM.createRoot(document.getElementById('root')).render(
    <Sentry.ErrorBoundary
        fallback={({ error, resetError }) => (
            <div style={{
                minHeight: '100vh', display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', gap: 16,
                background: '#0b0d12', color: '#e5e7eb', padding: 24, textAlign: 'center',
            }}>
                <h1 style={{ fontSize: 20, fontWeight: 700 }}>Algo salió mal en VicMar Data AI</h1>
                <p style={{ maxWidth: 480, opacity: 0.8, fontSize: 14 }}>
                    Ocurrió un error inesperado en la interfaz. Ya quedó registrado.
                    Intenta recargar la página.
                </p>
                <button
                    onClick={resetError}
                    style={{
                        padding: '8px 20px', borderRadius: 8, border: '1px solid #3b82f6',
                        background: 'transparent', color: '#3b82f6', cursor: 'pointer',
                    }}
                >
                    Reintentar
                </button>
            </div>
        )}
    >
        <App />
    </Sentry.ErrorBoundary>,
)

// PWA: el Service Worker se registra solo en producción. En desarrollo, Vite
// sirve módulos con ?v=<hash> que cambia en cada reinicio; un SW activo podría
// responderlos desde su caché con un hash antiguo y provocar «Failed to fetch
// dynamically imported module». En producción los hashes son estables.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(() => console.log('VicMar Data AI: Service Worker Registrado'))
            .catch(err => console.log('VicMar Data AI: Error SW', err));
    });
}
