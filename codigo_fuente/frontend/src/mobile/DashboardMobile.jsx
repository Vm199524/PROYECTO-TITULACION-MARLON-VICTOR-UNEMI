/**
 * Archivo: DashboardMobile.jsx
 * Rol: layout principal para teléfono (<768px).
 *
 * Rediseño (29/08/2026): la versión anterior solo
 * exponía el Chat — Indicadores, Bases de Datos y todo el módulo de
 * Administración (Usuarios/Auditoría) no tenían forma de abrirse desde el
 * teléfono en absoluto, aunque ya existían en escritorio. Se agrega una
 * barra de navegación inferior (el patrón estándar de la industria para
 * móvil — Material Design, iOS HIG — porque queda al alcance del pulgar,
 * a diferencia de una barra lateral pensada para mouse) que da paso a las
 * MISMAS vistas que ya usa DashboardDesktop (BentoDashboard, DataChannels,
 * AdminUsuarios, AdminAuditoria) — no una reconstrucción aparte, para no
 * duplicar lógica ni arriesgar que las dos versiones se desincronicen.
 * ("Ecosistema VicMar Data AI" se retiró de todo el sistema el mismo día por
 * no estar a la altura del resto del diseño.)
 */

import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
    Database,
    FileChartColumn,
    LayoutGrid,
    LogOut,
    MessageSquare,
    Shield,
    UserPlus,
    Users,
    X,
} from 'lucide-react';
import { ChatAreaMobile } from './ChatAreaMobile';

// --- COMPONENTES COMPARTIDOS (mismas vistas que escritorio) ---
import { SessionHistory } from '../components/SessionHistory';
import { NewQueryButton } from '../components/NewQueryButton';
import { ContextNodes } from '../components/ContextNodes';
import { DataChannels } from '../components/views/DataChannels';
import { BentoDashboard } from '../components/views/BentoDashboard';
import { AdminUsuarios } from '../components/views/AdminUsuarios';
import { AdminAuditoria } from '../components/views/AdminAuditoria';

const TAB_BAR_HEIGHT = 64;

const TABS = [
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'reportes', icon: FileChartColumn, label: 'Indicadores' },
    { id: 'canales', icon: Database, label: 'Datos' },
    { id: 'mas', icon: LayoutGrid, label: 'Más' },
];

export function DashboardMobile({
    isSidebarOpen, setIsSidebarOpen,
    chatHistory, setChatHistory,
    deviceType, userAuth, activeModule, setActiveModule,
    connInfo, setConnInfo, availableDBs, fetchingDBs, loadDatabases, handleConnect,
    loading, prompt, setPrompt, handleQuery, cancelQuery,
    correctionHint, correct, setCorrectionHint,
    textareaRef, chatEndRef,
    activeCapabilities,
    activeSessionId,
    sortedSessions,
    menuOpenId, setMenuOpenId,
    editingId, setEditingId,
    tempSessionName, setTempSessionName,
    startNewChat, loadSession, togglePinSession, renameSession, saveNewName, deleteSession,
    showHost, setShowHost, maskedHost,
    handleLogout,
    biPulse,
}) {
    const [mobileView, setMobileView] = useState('chat');
    const esAdmin = String(userAuth?.role || '').trim().toUpperCase() === 'ADMINISTRADOR';

    const irA = (vista) => {
        setMobileView(vista);
        setIsSidebarOpen(false);
    };

    const handleOpenSession = (session) => {
        setIsSidebarOpen(false);
        setMobileView('chat');
        loadSession(session);
    };

    const handleDrillDown = (pregunta) => {
        if (!pregunta) return;
        setMobileView('chat');
        handleQuery?.(null, pregunta);
    };

    const tabActiva = mobileView === 'chat' || mobileView === 'reportes' || mobileView === 'canales'
        ? mobileView
        : 'mas'; // todo admin-* vive dentro de "Más"

    return (
        <div className="flex h-[100dvh] w-full flex-col overflow-hidden bg-[#020308] text-slate-200 select-none">
            {/* Cabecera fija, simplificada: la navegación real ya vive abajo */}
            <header className="z-[900] flex h-[58px] shrink-0 items-center justify-between border-b border-white/10 bg-[#020617]/98 px-4 backdrop-blur-3xl">
                <div className="flex items-center gap-2.5">
                    <img src="/logo.png" className="h-8 w-8 rounded-lg border border-white/10 bg-white/5 p-1" alt="" />
                    <span className="text-[13px] font-black uppercase tracking-widest text-white">
                        VicMar<span className="text-cyan-400">DataAI</span>
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleLogout}
                        aria-label="Desconectar"
                        className="flex h-9 w-9 items-center justify-center rounded-xl border border-red-500/15 bg-red-500/5 text-red-400 active:scale-95"
                    >
                        <LogOut size={16} aria-hidden="true" />
                    </button>
                </div>
            </header>

            {/* Contenido principal: una vista a la vez, cada una ya trae su
                propio scroll/padding (mismas vistas que escritorio). Al ser
                flex-1 entre el header y el <nav> (ambos shrink-0), el propio
                flexbox ya la deja exactamente entre los dos — no necesita
                padding extra para "no taparse" con la barra inferior. */}
            <main className="relative min-h-0 flex-1 overflow-hidden">
                <div className="absolute inset-0" style={{ display: mobileView === 'chat' ? 'block' : 'none' }}>
                    <ChatAreaMobile
                        chatHistory={chatHistory} setChatHistory={setChatHistory} userAuth={userAuth} loading={loading}
                        prompt={prompt} setPrompt={setPrompt} handleQuery={handleQuery} cancelQuery={cancelQuery}
                        correctionHint={correctionHint} correct={correct} setCorrectionHint={setCorrectionHint}
                        activeModule={activeModule} textareaRef={textareaRef} chatEndRef={chatEndRef}
                    />
                </div>
                {mobileView === 'reportes' && (
                    <div className="absolute inset-0 overflow-y-auto">
                        <BentoDashboard connInfo={connInfo} userAuth={userAuth} biPulse={biPulse} onDrillDown={handleDrillDown} />
                    </div>
                )}
                {mobileView === 'canales' && (
                    <div className="absolute inset-0 overflow-y-auto">
                        <DataChannels
                            connInfo={connInfo} setConnInfo={setConnInfo} availableDBs={availableDBs}
                            fetchingDBs={fetchingDBs} loadDatabases={loadDatabases} handleConnect={handleConnect}
                        />
                    </div>
                )}
                {esAdmin && (mobileView === 'admin-usuarios' || mobileView === 'admin-nuevo-usuario') && (
                    <div className="absolute inset-0 overflow-y-auto">
                        <AdminUsuarios userAuth={userAuth} initialMode={mobileView === 'admin-nuevo-usuario' ? 'create' : 'list'} />
                    </div>
                )}
                {esAdmin && mobileView === 'admin-auditoria' && (
                    <div className="absolute inset-0 overflow-y-auto">
                        <AdminAuditoria />
                    </div>
                )}
            </main>

            {/* Barra de navegación inferior — al alcance del pulgar, el
                patrón estándar para navegación primaria en móvil. */}
            <nav
                className="z-[950] flex shrink-0 items-stretch border-t border-white/10 bg-[#020617]/98 backdrop-blur-3xl"
                style={{ height: TAB_BAR_HEIGHT, paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
            >
                {TABS.map((tab) => {
                    const activo = tabActiva === tab.id;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => (tab.id === 'mas' ? setIsSidebarOpen(true) : irA(tab.id))}
                            aria-current={activo ? 'page' : undefined}
                            className="flex flex-1 flex-col items-center justify-center gap-1 active:bg-white/5"
                        >
                            <tab.icon size={20} className={activo ? 'text-cyan-400' : 'text-white/40'} aria-hidden="true" />
                            <span className={`text-[10px] font-bold uppercase tracking-wide ${activo ? 'text-cyan-300' : 'text-white/40'}`}>
                                {tab.label}
                            </span>
                        </button>
                    );
                })}
            </nav>

            {/* Hoja "Más": Administración, sesión/historial y
                selector de empresa — todo lo que no cabe en 4 pestañas. */}
            <AnimatePresence>
                {isSidebarOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            onClick={() => setIsSidebarOpen(false)}
                            className="fixed inset-0 z-[2000] bg-black/80 backdrop-blur-sm"
                        />
                        <motion.aside
                            initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
                            transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
                            className="fixed inset-x-0 bottom-0 z-[2001] flex max-h-[85vh] flex-col overflow-hidden rounded-t-[28px] border-t border-white/10 bg-[#0B0F14] shadow-[0_-20px_60px_rgba(0,0,0,0.7)]"
                        >
                            <div className="flex shrink-0 items-center justify-between border-b border-white/[0.06] px-6 py-4">
                                <span className="text-[13px] font-black uppercase tracking-[0.2em] text-white/70">Más opciones</span>
                                <button onClick={() => setIsSidebarOpen(false)} aria-label="Cerrar" className="text-white/30 active:text-white">
                                    <X size={22} aria-hidden="true" />
                                </button>
                            </div>

                            <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar px-6 py-5">
                                {esAdmin && (
                                    <div className="mb-6">
                                        <p className="mb-2 px-1 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Administración</p>
                                        <div className="flex flex-col gap-1.5">
                                            <MasItem icon={Users} label="Usuarios" activo={mobileView === 'admin-usuarios'} onClick={() => irA('admin-usuarios')} />
                                            <MasItem icon={UserPlus} label="Nuevo Usuario" activo={mobileView === 'admin-nuevo-usuario'} onClick={() => irA('admin-nuevo-usuario')} />
                                            <MasItem icon={Shield} label="Auditoría" activo={mobileView === 'admin-auditoria'} onClick={() => irA('admin-auditoria')} />
                                        </div>
                                    </div>
                                )}

                                <div className="mb-6">
                                    <p className="mb-2 px-1 text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Empresa activa</p>
                                    <ContextNodes
                                        availableDBs={availableDBs}
                                        connInfo={connInfo}
                                        handleConnect={handleConnect}
                                        loadDatabases={loadDatabases}
                                        fetchingDBs={fetchingDBs}
                                        compact
                                    />
                                </div>

                                <div className="mb-4">
                                    <NewQueryButton startNewChat={() => { setMobileView('chat'); startNewChat?.(); setIsSidebarOpen(false); }} />
                                </div>

                                <SessionHistory
                                    sortedSessions={sortedSessions} activeSessionId={activeSessionId} editingId={editingId}
                                    tempSessionName={tempSessionName} menuOpenId={menuOpenId} loadSession={handleOpenSession}
                                    setMenuOpenId={setMenuOpenId} togglePinSession={togglePinSession} renameSession={renameSession}
                                    saveNewName={saveNewName} setTempSessionName={setTempSessionName} deleteSession={deleteSession}
                                />
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}

function MasItem({ icon: Icon, label, activo, onClick }) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-3 rounded-2xl border px-4 py-3.5 text-left text-[13px] font-bold transition-colors active:scale-[0.98] ${
                activo ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300' : 'border-white/10 bg-white/[0.03] text-white/70'
            }`}
        >
            <Icon size={18} aria-hidden="true" />
            {label}
        </button>
    );
}
