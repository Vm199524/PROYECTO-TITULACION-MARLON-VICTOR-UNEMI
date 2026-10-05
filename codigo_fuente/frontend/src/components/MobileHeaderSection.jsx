/**
 * @file Envoltorio de la cabecera móvil. DashboardDesktop lo renderiza solo en
 * pantallas pequeñas (`block lg:hidden`) y reenvía a MobileHeader el estado del
 * menú lateral y el cierre de sesión, para no cargar la vista de escritorio con
 * la lógica de navegación móvil.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */


import React from 'react';
import { MobileHeader } from '../mobile/MobileHeader';

/**
 * Renderiza la cabecera móvil y le conecta el menú lateral y el cierre de sesión.
 * Acepta además los setters de sesión de App.jsx (`setIsConnected`,
 * `setChatHistory`, `setSchema`, etc.), aunque hoy solo usa los tres indicados.
 *
 * @param {object} props
 * @param {boolean} props.isSidebarOpen - Si el menú lateral móvil está abierto.
 * @param {Function} props.setIsSidebarOpen - Abre o cierra el menú lateral.
 * @param {Function} props.handleLogout - Cierra la sesión del usuario.
 * @returns {JSX.Element} Cabecera visible solo en pantallas pequeñas.
 */
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


