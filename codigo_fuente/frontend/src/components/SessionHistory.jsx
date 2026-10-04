/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-UI-SIDEBAR-04]
 * ============================================================================
 * ARCHIVO: SessionHistory.jsx
 * MÓDULO: UI / Content Management
 *
 * 🎯 PROPÓSITO GERENCIAL:
 * Archivero de Retención. Permite al usuario consultar su pasado,
 * recuperar conversaciones valiosas previas, o mantener su espacio
 * limpio borrando consultas que ya no necesita.
 *
 * 📍 PUNTO DE INTERFAZ:
 * Ocupa la mitad inferior del menú lateral (Sidebar) con scroll independiente.
 *
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Listado de hilos de chat previos (Memoria a Largo Plazo).
 * - Menú contextual de opciones ('rename', 'delete') en cada ítem.
 * - Modo de selección múltiple (Fase 5, 28/08/2026:
 *   mismo patrón que los paneles de historial de las IA en la web) para
 *   fijar/eliminar varias conversaciones a la vez.
 * - Uso avanzado de animaciones (Framer Motion) para micro-interacciones suaves.
 * ============================================================================
 */

import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Check, CheckCircle2, Circle, Edit3, History, ListChecks, MessageSquare,
    MoreHorizontal, Pin, Trash, X,
} from 'lucide-react';

// Ancho fijo del menú contextual — se usa tanto para pintarlo como para
// calcular dónde ubicarlo (ver abrirMenu). Antes se posicionaba con
// `right-[110%]` relativo a un contenedor angosto (el sidebar colapsado),
// y el contenedor de la lista tiene `overflow-y-auto`: por la forma en que
// CSS calcula overflow, eso vuelve automático TAMBIÉN el eje X, así que el
// menú quedaba recortado a la mitad — de ahí que los íconos de Fijar/
// Renombrar/Eliminar se vieran "saliéndose de la burbuja". La solución es
// sacar el menú de ese contenedor por completo con un portal a <body> y
// posicionarlo con coordenadas de pantalla reales.
const MENU_WIDTH = 168;

export function SessionHistory({
    sortedSessions,
    activeSessionId,
    editingId,
    tempSessionName,
    menuOpenId,
    loadSession,
    setMenuOpenId,
    togglePinSession,
    renameSession,
    saveNewName,
    setTempSessionName,
    deleteSession,
    hideHeader, // Nueva prop
}) {
    const [menuPos, setMenuPos] = useState(null);
    const [selectMode, setSelectMode] = useState(false);
    const [selectedIds, setSelectedIds] = useState(() => new Set());

    // Salir del modo selección si la lista cambia por completo (ej. se borró
    // todo) para no dejar ids seleccionados que ya no existen.
    useEffect(() => {
        if (!selectMode) return;
        setSelectedIds((prev) => {
            const validos = new Set(sortedSessions.map((s) => s.id));
            const siguiente = new Set([...prev].filter((id) => validos.has(id)));
            return siguiente.size === prev.size ? prev : siguiente;
        });
    }, [sortedSessions, selectMode]);

    if (!sortedSessions || sortedSessions.length === 0) return null;

    const abrirMenu = (e, sessionId) => {
        e.stopPropagation();
        if (menuOpenId === sessionId) {
            setMenuOpenId(null);
            return;
        }
        const rect = e.currentTarget.getBoundingClientRect();
        const left = Math.max(8, Math.min(rect.right - MENU_WIDTH, window.innerWidth - MENU_WIDTH - 8));
        setMenuPos({ top: rect.bottom + 6, left });
        setMenuOpenId(sessionId);
    };

    const cerrarMenuAlDesplazar = () => {
        if (menuOpenId) setMenuOpenId(null);
    };

    const toggleSelectMode = () => {
        setSelectMode((v) => !v);
        setSelectedIds(new Set());
        setMenuOpenId(null);
    };

    const toggleSeleccionado = (id) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    };

    // deleteSession/togglePinSession solo aceptan un id a la vez (así ya
    // funcionaban antes de esta selección múltiple), así que la acción en
    // lote los llama uno por uno con un evento sintético inofensivo — sin
    // tocar App.jsx para nada.
    const eventoNulo = { stopPropagation: () => {} };

    const eliminarSeleccionadas = () => {
        selectedIds.forEach((id) => deleteSession(eventoNulo, id));
        setSelectMode(false);
        setSelectedIds(new Set());
    };

    const fijarSeleccionadas = () => {
        // "Fijar" en lote debe dejar TODAS las seleccionadas fijadas, no
        // alternar el estado de cada una — por eso solo se llama sobre las
        // que todavía no están fijadas (togglePinSession alterna, no fija).
        selectedIds.forEach((id) => {
            const sesion = sortedSessions.find((s) => s.id === id);
            if (sesion && !sesion.pinned) togglePinSession(eventoNulo, id);
        });
        setSelectMode(false);
        setSelectedIds(new Set());
    };

    return (
        <div className="h-full min-h-0 flex flex-col gap-2 pb-4">
            {!hideHeader && (
                <div className="shrink-0 z-[50] bg-transparent py-2 mb-1 border-b border-white/10 flex items-center justify-between">
                    <div className="flex items-center gap-2.5 px-4 py-2 rounded-full border border-amber-800/20 bg-amber-900/10 hover:bg-amber-900/20 transition-all cursor-default group">
                        <History size={12} className="text-amber-700/60 group-hover:text-amber-600 transition-colors" />
                        <span className="text-[12px] font-black text-amber-600 uppercase tracking-[0.25em]">Historial de Consultas</span>
                    </div>
                    <div className="h-[1px] flex-1 bg-amber-500/10 ml-4 rounded-full" />
                </div>
            )}

            <div className="shrink-0 flex flex-wrap items-center gap-y-1.5 px-1">
                {selectMode && (
                    <span className="text-[10px] font-bold uppercase tracking-wider text-white/35">
                        {selectedIds.size} seleccionada{selectedIds.size === 1 ? '' : 's'}
                    </span>
                )}
                <div className="ml-auto flex flex-wrap items-center justify-end gap-1.5">
                    {selectMode && (
                        <button
                            type="button"
                            onClick={fijarSeleccionadas}
                            disabled={selectedIds.size === 0}
                            aria-label="Fijar seleccionadas"
                            title="Fijar seleccionadas"
                            className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-white/70 transition-all hover:border-cyan-500/40 hover:text-cyan-300 disabled:opacity-30"
                        >
                            <Pin size={12} aria-hidden="true" /> Fijar
                        </button>
                    )}
                    {selectMode && (
                        <button
                            type="button"
                            onClick={eliminarSeleccionadas}
                            disabled={selectedIds.size === 0}
                            aria-label="Eliminar seleccionadas"
                            title="Eliminar seleccionadas"
                            className="flex items-center gap-1.5 rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-red-400 transition-all hover:bg-red-500/20 disabled:opacity-30"
                        >
                            <Trash size={12} aria-hidden="true" /> Eliminar
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={toggleSelectMode}
                        aria-pressed={selectMode}
                        aria-label={selectMode ? 'Cancelar selección' : 'Seleccionar conversaciones'}
                        title={selectMode ? 'Cancelar selección' : 'Seleccionar conversaciones'}
                        className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider transition-all ${
                            selectMode
                                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                                : 'text-white/35 hover:text-white/70 hover:bg-white/5 border border-transparent'
                        }`}
                    >
                        {selectMode ? <X size={12} aria-hidden="true" /> : <ListChecks size={12} aria-hidden="true" />}
                        {selectMode ? 'Cancelar' : 'Seleccionar'}
                    </button>
                </div>
            </div>

            <div
                onScroll={cerrarMenuAlDesplazar}
                className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-1 relative z-30 pt-1"
            >
                {sortedSessions.map((session) => {
                    const seleccionada = selectedIds.has(session.id);
                    return (
                        <div
                            key={session.id}
                            onClick={() => (selectMode ? toggleSeleccionado(session.id) : loadSession(session))}
                            className={`group w-full flex items-center gap-3 p-3 rounded-2xl border transition-all cursor-pointer relative mb-2 ${
                                seleccionada
                                    ? 'bg-cyan-500/10 border-cyan-400/50'
                                    : activeSessionId === session.id
                                        ? 'bg-gradient-to-r from-cyan-500/14 to-blue-500/10 border-cyan-300/45 text-white shadow-[0_0_18px_rgba(6,182,212,0.14)]'
                                        : 'border-white/12 bg-black/30 hover:bg-white/[0.06] hover:border-cyan-500/30'
                            }`}
                        >
                            <div className="shrink-0 relative">
                                {selectMode ? (
                                    seleccionada
                                        ? <CheckCircle2 size={16} className="text-cyan-400" />
                                        : <Circle size={16} className="text-white/25" />
                                ) : (
                                    <>
                                        <MessageSquare size={13} className={activeSessionId === session.id ? 'text-cyan-300' : 'text-white/45 group-hover:text-cyan-300/70'} />
                                        {session.pinned && (
                                            <div className="absolute -top-1.5 -left-1.5 text-cyan-500"><Pin size={8} fill="currentColor" /></div>
                                        )}
                                    </>
                                )}
                            </div>
                            <div className="flex flex-col min-w-0 flex-1">
                                {editingId === session.id ? (
                                    <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                                        <input autoFocus
                                            className="bg-black/40 border border-white/20 rounded px-2 py-0.5 text-[12px] text-white w-full outline-none focus:border-cyan-500/60"
                                            value={tempSessionName}
                                            onChange={e => setTempSessionName(e.target.value)}
                                            onKeyDown={e => e.key === 'Enter' && saveNewName(e, session.id)}
                                        />
                                        <button onClick={e => saveNewName(e, session.id)} className="text-cyan-400 hover:text-cyan-300"><Check size={12} /></button>
                                    </div>
                                ) : (
                                    <span title={session.name} className={`text-[12px] font-bold truncate pr-3 tracking-[0.02em] transition-colors ${activeSessionId === session.id ? 'text-white' : 'text-slate-200/90 group-hover:text-white'}`}>
                                        {session.name}
                                    </span>
                                )}
                                <span className="text-[10px] text-slate-400/90 mt-0.5 tracking-wide">{session.timestamp}</span>
                            </div>
                            {!selectMode && (
                                <div className="relative shrink-0 flex items-center gap-1 session-menu-trigger" onClick={e => e.stopPropagation()}>
                                    <button onClick={(e) => abrirMenu(e, session.id)}
                                        className={`p-1.5 rounded-lg transition-all ${menuOpenId === session.id ? 'bg-cyan-500 text-white' : 'text-white/40 group-hover:text-white hover:bg-white/10'}`}>
                                        <MoreHorizontal size={14} />
                                    </button>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Menú contextual por ítem — portal a <body> para no quedar
                recortado por el scroll del contenedor de arriba (ver nota de
                MENU_WIDTH). Una sola instancia compartida, posicionada con
                las coordenadas calculadas en abrirMenu(). */}
            {typeof document !== 'undefined' && createPortal(
                <AnimatePresence>
                    {menuOpenId && menuPos && (() => {
                        const session = sortedSessions.find((s) => s.id === menuOpenId);
                        if (!session) return null;
                        return (
                            <motion.div
                                key="session-menu"
                                initial={{ opacity: 0, scale: 0.95, y: -6 }}
                                animate={{ opacity: 1, scale: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95, y: -6 }}
                                style={{ position: 'fixed', top: menuPos.top, left: menuPos.left, width: MENU_WIDTH }}
                                className="session-menu-trigger bg-[#0f172a] border border-white/20 rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.95)] z-[100000] py-2 pointer-events-auto backdrop-blur-3xl"
                                onClick={(e) => e.stopPropagation()}
                            >
                                <button onClick={(e) => togglePinSession(e, session.id)} className="w-full flex items-center gap-3 px-4 py-2.5 text-[12px] text-white/70 hover:bg-white/5 hover:text-white transition-all group/item">
                                    <Pin size={14} className={`shrink-0 ${session.pinned ? 'text-cyan-400' : 'text-white/20 group-hover/item:text-cyan-400'}`} />
                                    <span className="font-bold">{session.pinned ? 'Desfijar' : 'Fijar'}</span>
                                </button>
                                <button onClick={(e) => renameSession(e, session.id)} className="w-full flex items-center gap-3 px-4 py-2.5 text-[12px] text-white/70 hover:bg-white/5 hover:text-white transition-all group/item">
                                    <Edit3 size={14} className="shrink-0 text-white/20 group-hover/item:text-cyan-400" />
                                    <span className="font-bold">Renombrar</span>
                                </button>
                                <div className="h-[1px] bg-white/5 my-1.5 mx-2" />
                                <button onClick={(e) => deleteSession(e, session.id)} className="w-full flex items-center gap-3 px-4 py-2.5 text-[12px] text-red-400 hover:bg-red-500/10 transition-all group/item">
                                    <Trash size={14} className="shrink-0 text-red-400/60 group-hover/item:text-red-300" />
                                    <span className="font-bold">Eliminar</span>
                                </button>
                            </motion.div>
                        );
                    })()}
                </AnimatePresence>,
                document.body
            )}
        </div>
    );
}
