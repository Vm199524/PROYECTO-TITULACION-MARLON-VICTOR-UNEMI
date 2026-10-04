/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-CORE-ERR-01]
 * ============================================================================
 * ARCHIVO: ErrorBoundary.jsx
 * MÓDULO: CORE / Stability
 * 
 * 🎯 PROPÓSITO GERENCIAL:
 * Es el "Paracaídas de Emergencia" de React. Asegura que si una pequeña 
 * parte visual de la página falla (por ejemplo, un gráfico no carga), toda 
 * la aplicación NO se ponga en blanco. Atrapa el error y muestra un reporte.
 * 
 * 📍 PUNTO DE INTERFAZ:
 * Envuelve `AppInner` en `App.jsx`. Solo es visible si ocurre un colapso.
 * 
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Interceptación de errores de ciclo de vida en componentes hijos.
 * - Renderizado de UI de respaldo (Pantalla de "Error de Renderizado").
 * - Previene bloqueos fatales (White screen of death) de React.
 * ============================================================================
 */

import React from 'react';

export class ErrorBoundary extends React.Component {
    constructor(props) { super(props); this.state = { hasError: false, error: null }; }
    static getDerivedStateFromError(error) { return { hasError: true, error }; }
    render() {
        if (this.state.hasError) {
            return (
                <div style={{ background: '#020617', color: '#f87171', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: 'monospace', padding: '40px' }}>
                    <h1 style={{ fontSize: '24px', marginBottom: '16px' }}>? Error de Renderizado</h1>
                    <pre style={{ background: '#0f172a', padding: '20px', borderRadius: '12px', maxWidth: '800px', overflow: 'auto', fontSize: '13px', color: '#fca5a5' }}>
                        {this.state.error?.toString()}{'\n'}{this.state.error?.stack}
                    </pre>
                </div>
            );
        }
        return this.props.children;
    }
}

// --- COMPONENTE PRINCIPAL ---
