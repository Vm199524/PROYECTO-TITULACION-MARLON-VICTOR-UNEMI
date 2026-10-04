/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-UI-MOBILE-01]
 * ============================================================================
 * ARCHIVO: MobileHeaderSection.jsx
 * MÓDULO: UI / Mobile Bridge
 * 
 * 🎯 PROPÓSITO GERENCIAL:
 * Integrador de funcionalidades para celulares. Asegura que la arquitectura
 * de escritorio se mantenga limpia envolviendo la lógica compleja móvil
 * en un solo "puente" visual.
 * 
 * 📍 PUNTO DE INTERFAZ:
 * Solamente renderizado condicionalmente (`block lg:hidden`) en `DashboardDesktop.jsx`.
 * 
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Evita pasar excesivas 'props' (funciones) directamente al componente visual.
 * - Conecta los métodos globales de `App.jsx` con los requerimientos 
 *   de navegación móvil (`MobileHeader.jsx`).
 * ============================================================================
 */


import React from 'react';
import { MobileHeader } from '../mobile/MobileHeader';

export function MobileHeaderSection({
    isSidebarOpen,
    setIsSidebarOpen,
    setIsConnected,
    setChatHistory,
    setSchema,
    setActiveModule,
    setTempCreds,
    setUserAuth,
    isConnectingRef,
    setPrompt,
    handleLogout,
}) {
    return (
        <div className="block lg:hidden">
            <MobileHeader
                isSidebarOpen={isSidebarOpen}
                setIsSidebarOpen={setIsSidebarOpen}
                onLogout={() => handleLogout()}
            />
        </div>
    );
}


