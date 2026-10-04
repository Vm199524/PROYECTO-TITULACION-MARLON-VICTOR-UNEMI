/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-UI-SIDEBAR-02]
 * ============================================================================
 * ARCHIVO: ContextNodes.jsx
 * MÓDULO: UI / Sidebar Navigation
 * 
 * 🎯 PROPÓSITO GERENCIAL:
 * Panel de navegación rápida en el menú izquierdo que permite al usuario 
 * visualizar con qué base de datos está operando o volver al chat general.
 * 
 * 📍 PUNTO DE INTERFAZ:
 * Ubicado en la parte superior del menú lateral del DashboardDesktop y Mobile.
 * 
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Menú Desplegable con buscador para elegir la base de datos SQL objetivo.
 * - Renderización del Indicador del origen de los datos activos.
 * - Acceso directo a la "Pasarela Chat".
 * ============================================================================
 */

import React, { useMemo, useState } from 'react';
import { Check, Database, Loader2, MessageSquare, Search, Link2 } from 'lucide-react';
import { dbToBusinessName } from '../constants/appConfig';

export function ContextNodes({
    availableDBs = [],
    connInfo = {},
    handleConnect,
    loadDatabases,
    fetchingDBs = false,
    // Este componente nació para el sidebar ancho de escritorio (ver ficha
    // técnica arriba) y se reutiliza tal cual en la hoja "Más" del móvil,
    // mucho más angosta. Su interletrado (`tracking-[0.2em]`/`0.25em`) sobre
    // textos en mayúsculas ahí ocupa casi todo el ancho disponible y se ve
    // desproporcionado (reportado 29/08/2026). `compact` reduce tamaño y
    // tracking solo quien lo pida, sin tocar el aspecto ya aprobado en
    // escritorio.
    compact = false,
}) {
    const [isDbSelectorOpen, setIsDbSelectorOpen] = useState(false);
    const [dbFilter, setDbFilter] = useState('');

    const filteredDBs = useMemo(() => {
        const q = dbFilter.trim().toLowerCase();
        if (!q) return availableDBs;
        return availableDBs.filter((db) => {
            const dbId = String(db).toLowerCase();
            const businessName = dbToBusinessName(db).toLowerCase();
            return dbId.includes(q) || businessName.includes(q);
        });
    }, [availableDBs, dbFilter]);

    const toggleDbSelector = () => {
        const nextOpen = !isDbSelectorOpen;
        setIsDbSelectorOpen(nextOpen);
        if (nextOpen && typeof loadDatabases === 'function') loadDatabases();
    };

    const selectDatabase = (db) => {
        if (typeof handleConnect === 'function') {
            handleConnect(null, { ...connInfo, database: db, selected_company_code: db });
        }
        setIsDbSelectorOpen(false);
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between px-2">
                <div className={`flex items-center rounded-full border border-amber-800/20 bg-amber-900/10 hover:bg-amber-900/20 transition-all cursor-default group ${compact ? 'gap-1.5 px-3 py-1.5' : 'gap-2.5 px-4 py-2'}`}>
                    <Link2 size={compact ? 10 : 12} className="text-amber-700/60 group-hover:text-amber-600 transition-colors shrink-0" />
                    <span className={`font-black text-amber-600 uppercase ${compact ? 'text-[10px] tracking-[0.08em]' : 'text-[12px] tracking-[0.25em]'}`}>Canales de Conexion</span>
                </div>
                <div className="h-[1px] flex-1 bg-amber-500/10 ml-4 rounded-full" />
            </div>
            <button className={`w-full flex items-center justify-between rounded-3xl border border-white/15 bg-black/25 text-white/80 hover:text-white hover:bg-white/[0.06] hover:border-cyan-400/25 transition-all duration-300 ${compact ? 'p-3' : 'p-4'}`}>
                <div className={`flex items-center min-w-0 ${compact ? 'gap-3' : 'gap-4'}`}>
                    <MessageSquare size={compact ? 16 : 18} className="text-cyan-300/70 shrink-0" />
                    <span className={`font-black uppercase truncate text-slate-300 ${compact ? 'text-[11px] tracking-[0.06em]' : 'text-[12px] tracking-[0.2em]'}`}>Pasarela Chat</span>
                </div>
                <div className="h-1.5 w-1.5 rounded-full bg-cyan-300/70 shrink-0" />
            </button>

            <div className="space-y-2">
                <button
                    type="button"
                    onClick={toggleDbSelector}
                    className={`w-full flex items-center justify-between rounded-3xl border transition-all ${compact ? 'p-3' : 'p-4'} ${isDbSelectorOpen ? 'text-cyan-100 bg-cyan-500/10 border-cyan-400/35 shadow-[0_0_18px_rgba(6,182,212,0.12)]' : 'text-white/75 hover:text-white hover:bg-white/[0.06] border-white/15 bg-black/25 hover:border-cyan-400/25'}`}
                >
                    <div className={`flex items-center min-w-0 ${compact ? 'gap-3' : 'gap-4'}`}>
                        <Database size={compact ? 16 : 18} className="shrink-0 text-cyan-300/85" />
                        <span className={`font-black uppercase truncate text-slate-300 ${compact ? 'text-[11px] tracking-[0.04em]' : 'text-[12px] tracking-[0.18em]'}`}>Bases del Servidor Central</span>
                    </div>
                    {fetchingDBs ? (
                        <Loader2 size={14} className="animate-spin shrink-0 text-cyan-400" />
                    ) : (
                        <span className="text-[11px] font-black text-cyan-400 uppercase tracking-wider shrink-0">{isDbSelectorOpen ? 'Cerrar' : 'Elegir'}</span>
                    )}
                </button>

                {isDbSelectorOpen && (
                    <div className="rounded-2xl border border-white/15 bg-[#040b1a]/85 backdrop-blur-2xl p-3 space-y-2">
                        <div className="relative">
                            <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/45" />
                            <input
                                type="text"
                                value={dbFilter}
                                onChange={(e) => setDbFilter(e.target.value)}
                                placeholder="Filtrar base..."
                                className="w-full h-9 pl-8 pr-3 rounded-xl bg-[#020617]/95 border border-white/15 text-[12px] font-bold uppercase tracking-wider text-white placeholder:text-white/45 outline-none focus:border-cyan-500/45"
                            />
                        </div>

                        <div className="max-h-40 overflow-y-auto custom-scrollbar space-y-1 pr-1">
                            {filteredDBs.length > 0 ? (
                                filteredDBs.map((db) => {
                                    const isActive = connInfo?.database === db;
                                    return (
                                        <button
                                            key={db}
                                            type="button"
                                            onClick={() => selectDatabase(db)}
                                            className={`w-full flex items-center justify-between rounded-xl px-3 py-2 text-left border transition-all ${isActive ? 'bg-cyan-500/12 border-cyan-400/45 text-cyan-200' : 'bg-white/[0.04] border-white/15 text-white/80 hover:text-white hover:border-cyan-500/35'}`}
                                        >
                                            <div className="min-w-0">
                                                <span className="block text-[12px] font-black uppercase tracking-[0.12em] truncate">{dbToBusinessName(db)}</span>
                                                <span className="block text-[11px] font-bold uppercase tracking-[0.14em] text-white/45 truncate">{db}</span>
                                            </div>
                                            {isActive && <Check size={12} className="shrink-0" />}
                                        </button>
                                    );
                                })
                            ) : (
                                <div className="px-3 py-3 text-[11px] font-black text-white/45 uppercase tracking-[0.16em] text-center border border-white/10 rounded-xl bg-white/[0.02]">
                                    {fetchingDBs ? 'Cargando bases...' : 'Sin coincidencias'}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}


