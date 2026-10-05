/**
 * @file Cabecera móvil con la marca VicMar Data AI, el botón que abre o
 * cierra el menú lateral, el indicador de conexión «ON» y el botón de cerrar
 * sesión. La renderiza MobileHeaderSection dentro de DashboardDesktop en
 * pantallas pequeñas.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React from 'react';
import { Menu, LogOut } from 'lucide-react';

/**
 * Renderiza la cabecera móvil.
 * @param {object} props
 * @param {boolean} props.isSidebarOpen Indica si el menú lateral está abierto.
 * @param {function(boolean): void} props.setIsSidebarOpen Abre o cierra el menú lateral.
 * @param {function} props.onLogout Cierra la sesión.
 * @returns {JSX.Element} Cabecera.
 */
export const MobileHeader = ({ isSidebarOpen, setIsSidebarOpen, onLogout }) => {
    return (
        <header className="relative w-full h-[60px] border-b border-white/10 flex items-center justify-between px-4 z-[100] backdrop-blur-3xl bg-[#020617]/98 shadow-[0_10px_30px_rgba(0,0,0,0.5)] shrink-0">
            {/* Lado izquierdo: menú y marca */}
            <div className="flex items-center gap-3">
                <button 
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    className={`p-2.5 md:p-3 bg-cyan-500/20 active:scale-95 transition-all rounded-[14px] md:rounded-[16px] text-cyan-400 border border-cyan-500/30 shadow-lg ${isSidebarOpen ? 'bg-cyan-500 text-white' : ''}`}
                    aria-label="Toggle Sidebar"
                >
                    <Menu size={20} className="md:w-5.5 md:h-5.5" strokeWidth={2.5} />
                </button>
                <div className="flex items-center gap-2.5">
                    <div className="h-9 w-9 p-1 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center">
                        <img src="/logo.png" alt="Logo" className="w-full h-full object-contain drop-shadow-[0_0_8px_rgba(6,182,212,0.4)]" />
                    </div>
                    <div className="flex flex-col min-w-0">
                        <span className="text-[13px] md:text-[15px] font-black text-white uppercase tracking-tight leading-none">
                            VicMar <span className="text-cyan-400">Data AI</span>
                        </span>
                        <span className="text-[7.5px] md:text-[11px] font-bold text-white/30 uppercase tracking-widest mt-0.5 md:mt-1 truncate">
                            Inteligencia de Negocios
                        </span>
                    </div>
                </div>
            </div>
            
            {/* Lado derecho: estado y cierre de sesión */}
            <div className="flex items-center gap-3">
                <div className="hidden xs:flex flex-col items-end mr-1">
                    <div className="flex items-center gap-1 px-2 py-0.5 bg-cyan-500/20 rounded-full border border-cyan-500/30">
                        <div className="h-1.5 w-1.5 rounded-full bg-cyan-500 animate-pulse" />
                        <span className="text-[11px] font-black text-cyan-500 uppercase">ON</span>
                    </div>
                </div>
                
                <button
                    onClick={onLogout}
                    className="flex items-center justify-center h-12 w-12 rounded-[18px] bg-cyan-500/20 active:scale-90 border border-cyan-500/30 text-cyan-500 transition-all shadow-[0_0_20px_rgba(239,68,68,0.2)]"
                    title="Cerrar Sesión"
                >
                    <LogOut size={22} strokeWidth={2.5} />
                </button>
            </div>
        </header>
    );
};






