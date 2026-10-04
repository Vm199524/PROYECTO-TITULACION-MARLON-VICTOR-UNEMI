/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-CORE-02]
 * ============================================================================
 * ARCHIVO: main.jsx
 * MÓDULO: CORE / Bootstrap
 *
 * 🎯 PROPÓSITO GERENCIAL:
 * El "Interruptor de Encendido" de la plataforma. Toma todo el código fuente
 * encapsulado en `App.jsx` y lo inyecta en el navegador de los usuarios para
 * que empiece a funcionar visualmente.
 *
 * 📍 PUNTO DE INTERFAZ:
 * Es el primer código en ejecutarse, enlaza React con el archivo HTML principal.
 *
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Montaje de la aplicación React al DOM (Document Object Model).
 * - Inicialización del rastreador de errores remoto Sentry.
 * - Registro del Service Worker para capacidades de Aplicación Web Progresiva (PWA).
 * ============================================================================
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import * as Sentry from "@sentry/react";
import App from './App.jsx'
import './index.css'

// Sentry (captura de errores en producción, FASE 4 — punto 4 Nivel 2).
//
// ANTES este init() usaba un DSN hardcodeado (o4508932454512345 /
// 4508932456123456) que no corresponde a ningún proyecto real de Sentry —
// parece un valor de relleno que quedó de una plantilla y nunca se
// reemplazó. Con un DSN inválido, Sentry.init() no lanza error: simplemente
// intenta mandar los eventos a un proyecto que no existe y los pierde en
// silencio. Es decir, esto APARENTABA estar funcionando pero no capturaba
// nada — el mismo patrón de "residuo que parece activo" que Together AI en
// el backend.
//
// Ahora el DSN se lee de una variable de entorno (VITE_SENTRY_DSN, ver
// frontend/.env.example) y Sentry solo se inicializa si hay un valor real.
// Sin DSN configurado, la app funciona exactamente igual, solo que sin
// reportar errores — nunca se rompe nada por no tener Sentry activo.
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

// ErrorBoundary de Sentry: si un componente de React revienta con una
// excepción no capturada, el usuario ve un mensaje entendible en vez de una
// pantalla en blanco, y (si hay DSN) el error se reporta automáticamente.
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

// PWA: Service Worker — SOLO en producción.
// En desarrollo, Vite sirve módulos con ?v=<hash> dinámico que cambia en cada
// reinicio. Si el SW está activo, puede responder esos requests desde su caché
// con un hash antiguo, provocando "Failed to fetch dynamically imported module".
// En producción los hashes son estables y el SW puede cachear sin problema.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(() => console.log('VicMar Data AI: Service Worker Registrado'))
            .catch(err => console.log('VicMar Data AI: Error SW', err));
    });
}
