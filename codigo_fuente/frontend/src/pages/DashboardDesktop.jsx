/**
 * Archivo: DashboardDesktop.jsx
 * Rol: layout principal de escritorio para la experiencia autenticada.
 * Recibe desde: App.jsx.
 * Se conecta con: DesktopHeader, SessionHistory, DataChannels, ChatArea,
 * SidebarFooter y otros bloques del dashboard.
 */

import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AudioLines } from 'lucide-react';
import {
    BarChart2, Clock, Database, PanelLeft, PlusCircle, X,
    FileChartColumn, Shield, UserPlus, Users,
} from 'lucide-react';
import { SessionHistory } from '../components/SessionHistory';
import { DataChannels } from '../components/views/DataChannels';
import { AnalysisAreas } from '../components/views/AnalysisAreas';
import { BentoDashboard } from '../components/views/BentoDashboard';
import { AdminUsuarios } from '../components/views/AdminUsuarios';
import { AdminAuditoria } from '../components/views/AdminAuditoria';
import { DesktopHeader } from '../components/DesktopHeader';
import { SidebarFooter } from '../components/SidebarFooter';
import { NewQueryButton } from '../components/NewQueryButton';
import { ContextNodes } from '../components/ContextNodes';
import { ChatArea } from '../components/ChatArea';
import { MobileHeaderSection } from '../components/MobileHeaderSection';
import { VoiceMode, modoVozDisponible } from '../components/VoiceMode';

const NAV_ITEMS = [
    { id: 'canales', icon: Database, label: 'Bases de Datos' },
    { id: 'reportes', icon: FileChartColumn, label: 'Indicadores' },
    { id: 'nueva', icon: PlusCircle, label: 'Nueva Consulta' },
];

// Solo para ADMINISTRADOR (Fase 5, 28/08/2026). El
// backend YA exige este rol en cada endpoint /api/admin/* (_requiere_admin
// en main.py) — ocultar estos ítems aquí es solo para no confundir a
// alguien sin el rol con opciones que igual le devolverían 403; la
// autorización real vive en el servidor, no en este arreglo.
const NAV_ITEMS_ADMIN = [
    { id: 'admin-usuarios', icon: Users, label: 'Usuarios' },
    { id: 'admin-nuevo-usuario', icon: UserPlus, label: 'Nuevo Usuario' },
    { id: 'admin-auditoria', icon: Shield, label: 'Auditoría' },
];

export function DashboardView({
    isSidebarOpen, setIsSidebarOpen,
    chatHistory, setChatHistory,
    deviceType, userAuth, activeModule, setActiveModule,
    connInfo, setConnInfo, availableDBs, fetchingDBs, loadDatabases, handleConnect,
    loading, prompt, setPrompt, motorIA, setMotorIA, handleQuery, cancelQuery,
    correctionHint, correct, setCorrectionHint,
    textareaRef, chatEndRef,
    isConnectionReady,
    schema, activeCapabilities, activeSessionId,
    sortedSessions, menuOpenId, setMenuOpenId,
    editingId, setEditingId, tempSessionName, setTempSessionName,
    startNewChat, loadSession, togglePinSession, renameSession, saveNewName, deleteSession,
    showHost, setShowHost, maskedHost,
    setIsConnected, setSchema, setTempCreds, setUserAuth, isConnectingRef,
    handleLogout, openQuantumCore, biPulse,
    attachedImages, setAttachedImages,
}) {
    const [sidebarView, setSidebarView] = React.useState('chat');
    const [modoVozAbierto, setModoVozAbierto] = useState(false);
    const esAdmin = String(userAuth?.role || '').trim().toUpperCase() === 'ADMINISTRADOR';
    const handleOpenSession = React.useCallback((session) => {
        setSidebarView('chat');
        loadSession(session);
    }, [loadSession]);

    // Fase 3 — C2 (drill-down): un clic en una tarjeta o un punto de un
    // gráfico de Reportes BI cambia al chat y lanza la pregunta de detalle
    // correspondiente, reusando el mismo pipeline de consultas de siempre.
    const handleDrillDown = React.useCallback((pregunta) => {
        if (!pregunta) return;
        setSidebarView('chat');
        handleQuery?.(null, pregunta);
    }, [handleQuery]);
    return (
        <div
            className="flex h-[100dvh] w-full overflow-hidden select-none"
            style={{ background: 'var(--bg-main)', fontFamily: 'var(--font-main)', color: 'var(--text-primary)' }}
        >
            {/* ════════════════════════════════════
                SIDEBAR ÚNICO — Estilo Minimalista Grok
            ════════════════════════════════════ */}
            {/* Seccion: sidebar desktop con navegacion, historial y footer. */}
            <aside
                className="hidden lg:flex flex-col shrink-0 z-30 overflow-hidden"
                style={{
                    width: isSidebarOpen ? 260 : 64,
                    minWidth: isSidebarOpen ? 260 : 64,
                    background: 'var(--bg-main)',
                    borderRight: '1px solid var(--border)',
                    transition: 'width 0.20s ease, min-width 0.20s ease',
                }}
            >
                {/* Header Sidebar: Hamburger perfectamente alineado */}
                <div
                    className="shrink-0 flex items-center"
                    style={{ height: 50, justifyContent: isSidebarOpen ? 'flex-start' : 'center', paddingLeft: isSidebarOpen ? 16 : 0 }}
                >
                    <button
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                        className="sidebar-icon-btn p-1 flex items-center justify-center hover:bg-white/5 rounded-lg transition-colors"
                        style={{ color: 'var(--text-muted)', width: 32, height: 32 }}
                    >
                        <PanelLeft size={18} />
                    </button>
                    {isSidebarOpen && (
                        <span style={{ ...SIDEBAR_SECTION_LABEL_STYLE, marginLeft: 12 }}>
                            Navegación
                        </span>
                    )}
                </div>

                {/* Nav icons: Bajados un poco para equilibrar el espacio vertical */}
                <nav className="flex flex-col pt-3 px-3 gap-0.5">
                    {NAV_ITEMS.map((item) => (
                        <NavButton
                            key={item.id}
                            item={item}
                            active={sidebarView === item.id}
                            isSidebarOpen={isSidebarOpen}
                            onClick={() => {
                                if (item.id === 'nueva') {
                                    setSidebarView('chat');
                                    startNewChat?.();
                                } else {
                                    setSidebarView(sidebarView === item.id ? 'chat' : item.id);
                                }
                            }}
                        />
                    ))}

                    {esAdmin && (
                        <>
                            {isSidebarOpen && <SidebarSectionLabel>Administración</SidebarSectionLabel>}
                            {NAV_ITEMS_ADMIN.map((item) => (
                                <NavButton
                                    key={item.id}
                                    item={item}
                                    active={sidebarView === item.id}
                                    isSidebarOpen={isSidebarOpen}
                                    onClick={() => setSidebarView(sidebarView === item.id ? 'chat' : item.id)}
                                />
                            ))}
                        </>
                    )}
                </nav>

                {/* Contenido expandido sutil */}
                <AnimatePresence>
                    {isSidebarOpen && (
                        <motion.div
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-4 p-4 mt-1 border-t border-white/5"
                        >
                            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                                <div className="mb-3">
                                    <SidebarSectionLabel>Historial Reciente</SidebarSectionLabel>
                                </div>
                                <div className="flex-1 min-h-0">
                                    <SessionHistory
                                        sortedSessions={sortedSessions}
                                        activeSessionId={activeSessionId}
                                        editingId={editingId}
                                        tempSessionName={tempSessionName}
                                        menuOpenId={menuOpenId}
                                        loadSession={handleOpenSession}
                                        setMenuOpenId={setMenuOpenId}
                                        togglePinSession={togglePinSession}
                                        renameSession={renameSession}
                                        saveNewName={saveNewName}
                                        setTempSessionName={setTempSessionName}
                                        deleteSession={deleteSession}
                                        hideHeader={true}
                                    />
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                <div style={{ borderTop: '1px solid var(--border)', background: 'rgba(0,0,0,0.05)' }}>
                    <SidebarFooter maskedHost={maskedHost} showHost={showHost} setShowHost={setShowHost} />
                </div>
            </aside>

            {/* Seccion: layout principal con header y panel central. */}
            <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
                <div className="shrink-0 z-20">
                    <DesktopHeader
                        isSidebarOpen={isSidebarOpen} setIsSidebarOpen={setIsSidebarOpen}
                        userAuth={userAuth} connInfo={connInfo}
                        availableDBs={availableDBs} fetchingDBs={fetchingDBs}
                        loadDatabases={loadDatabases} handleConnect={handleConnect}
                        setIsConnected={setIsConnected} setChatHistory={setChatHistory}
                        setSchema={setSchema} setActiveModule={setActiveModule}
                        setTempCreds={setTempCreds} setUserAuth={setUserAuth}
                        isConnectingRef={isConnectingRef} setPrompt={setPrompt}
                        handleLogout={handleLogout} openQuantumCore={openQuantumCore}
                    />
                </div>

                <div className="flex-1 min-h-0 w-full relative">
                    {sidebarView === 'canales' && (
                        <DataChannels
                            connInfo={connInfo}
                            setConnInfo={setConnInfo}
                            availableDBs={availableDBs}
                            fetchingDBs={fetchingDBs}
                            loadDatabases={loadDatabases}
                            handleConnect={handleConnect}
                        />
                    )}
                    {sidebarView === 'reportes' && (
                        <BentoDashboard
                            connInfo={connInfo}
                            userAuth={userAuth}
                            biPulse={biPulse}
                            onDrillDown={handleDrillDown}
                        />
                    )}
                    {esAdmin && (sidebarView === 'admin-usuarios' || sidebarView === 'admin-nuevo-usuario') && (
                        <AdminUsuarios
                            userAuth={userAuth}
                            initialMode={sidebarView === 'admin-nuevo-usuario' ? 'create' : 'list'}
                        />
                    )}
                    {esAdmin && sidebarView === 'admin-auditoria' && (
                        <AdminAuditoria />
                    )}
                    <div className="absolute inset-0 z-0 flex flex-col" style={{ display: sidebarView === 'chat' ? 'flex' : 'none' }}>
                        <ChatArea
                            chatHistory={chatHistory} setChatHistory={setChatHistory}
                            deviceType={deviceType} userAuth={userAuth} loading={loading}
                            prompt={prompt} setPrompt={setPrompt} motorIA={motorIA} setMotorIA={setMotorIA} handleQuery={handleQuery} cancelQuery={cancelQuery}
                            correctionHint={correctionHint} correct={correct} setCorrectionHint={setCorrectionHint}
                            activeModule={activeModule} textareaRef={textareaRef} chatEndRef={chatEndRef}
                            isSidebarOpen={isSidebarOpen} connInfo={connInfo} isConnectionReady={isConnectionReady}
                            attachedImages={attachedImages} setAttachedImages={setAttachedImages}
                        />
                    </div>

                    {/* Botón flotante de conversación por voz interactiva AURA */}
                    {(sidebarView === 'chat' || sidebarView === 'dashboard') && modoVozDisponible && !modoVozAbierto && (
                        <button
                            id="btn-open-aura-voice"
                            type="button"
                            onClick={() => setModoVozAbierto(true)}
                            aria-label="Abrir asistente de conversación por voz AURA"
                            title="Conversar por voz con AURA (Reconocimiento y síntesis en tiempo real)"
                            className="fixed bottom-10 right-8 z-30 flex h-14 w-14 items-center justify-center rounded-full transition-all duration-300 hover:scale-110 active:scale-95 shadow-2xl cursor-pointer group"
                            style={{
                                background: 'linear-gradient(135deg, #22D3EE, #6366F1)',
                                boxShadow: '0 8px 32px rgba(34,211,238,0.45)',
                            }}
                        >
                            <AudioLines size={24} className="text-white group-hover:animate-pulse" aria-hidden="true" />
                        </button>
                    )}
                </div>

                <div className="lg:hidden absolute top-0 left-0 w-full z-40">
                    <MobileHeaderSection
                        isSidebarOpen={isSidebarOpen} setIsSidebarOpen={setIsSidebarOpen}
                        setIsConnected={setIsConnected} setChatHistory={setChatHistory}
                        setSchema={setSchema} setActiveModule={setActiveModule}
                        setTempCreds={setTempCreds} setUserAuth={setUserAuth}
                        isConnectingRef={isConnectingRef} setPrompt={setPrompt}
                        handleLogout={handleLogout}
                    />
                </div>
            </main>

            {/* Seccion: drawer movil lateral sobre el dashboard. */}
            <AnimatePresence>
                {isSidebarOpen && deviceType === 'mobile' && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            onClick={() => setIsSidebarOpen(false)}
                            className="fixed inset-0 bg-black/70 z-[60]"
                        />
                        <motion.aside
                            initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }}
                            className="fixed top-0 left-0 h-full bg-[#0D1117] z-[70] flex flex-col"
                            style={{ width: 280, borderRight: '1px solid var(--border)' }}
                        >
                            <div className="flex items-center justify-between p-4 border-b border-border">
                                <span className="font-bold">VicMar Data AI</span>
                                <button onClick={() => setIsSidebarOpen(false)}><X size={20} /></button>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>

            {/* Modo conversación por voz, sobre todo lo demás. Recibe el mismo
                handleQuery que el chat escrito: la voz es otra puerta de
                entrada al motor, no un motor aparte, así que las métricas
                certificadas y las advertencias de integridad siguen aplicando. */}
            <AnimatePresence>
                {modoVozAbierto && (
                    <VoiceMode
                        onClose={() => setModoVozAbierto(false)}
                        handleQuery={handleQuery}
                        chatHistory={chatHistory}
                        empresa={connInfo?.business_name || connInfo?.database || ''}
                        onCambiarEmpresa={(codigo) => {
                            // Mismo camino que al elegirla con el ratón: pasa por
                            // handleConnect, así se aplica la serialización que
                            // evita mezclar empresas.
                            const destino = String(codigo || '').trim().toUpperCase();
                            if (!destino) return;
                            handleConnect?.(null, {
                                ...connInfo,
                                database: destino,
                                selected_company_code: destino,
                            }, { dbSwitch: true });
                        }}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

// Regla visual (29/08/2026): todo encabezado de
// sección del sidebar ("Navegación", "Administración", "Historial
// Reciente") comparte exactamente el mismo tamaño, peso y tracking de
// fuente — antes cada uno tenía su propio valor suelto (9px/10px,
// 700/800, 0.1em/0.12em/0.14em) y se notaba a simple vista. Los que son
// divisores independientes (no pegados a un botón, como "Navegación" sí lo
// está al de colapsar el sidebar) van centrados con líneas a los lados.
const SIDEBAR_SECTION_LABEL_STYLE = {
    fontSize: 10,
    fontWeight: 800,
    color: 'var(--text-faint)',
    textTransform: 'uppercase',
    letterSpacing: '0.12em',
};

function SidebarSectionLabel({ children }) {
    return (
        <div className="flex items-center gap-2 px-1 py-1">
            <div className="h-px flex-1 bg-white/10" />
            <span style={SIDEBAR_SECTION_LABEL_STYLE}>{children}</span>
            <div className="h-px flex-1 bg-white/10" />
        </div>
    );
}

function NavButton({ item, active, isSidebarOpen, onClick }) {
    return (
        <button
            className={`sidebar-icon-btn ${active ? 'active' : ''}`}
            style={{
                width: '100%',
                justifyContent: isSidebarOpen ? 'flex-start' : 'center',
                gap: 12,
                paddingLeft: isSidebarOpen ? 12 : 0,
                height: 38,
                borderRadius: 8,
                color: active ? 'var(--accent)' : 'var(--text-muted)',
            }}
            title={!isSidebarOpen ? item.label : undefined}
            onClick={onClick}
        >
            <item.icon size={18} style={{ flexShrink: 0 }} />
            {isSidebarOpen && (
                <motion.span
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    style={{ fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap' }}
                >
                    {item.label}
                </motion.span>
            )}
        </button>
    );
}
