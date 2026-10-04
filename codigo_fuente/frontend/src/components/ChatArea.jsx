/**
 * Archivo: ChatArea.jsx
 * Rol: superficie central del chat en escritorio.
 * Recibe desde: DashboardDesktop.jsx.
 * Se conecta con: ChatMessage.jsx, ChatInput.jsx, useContextOverview.js
 * y appConfig.js para mostrar contexto, KPIs y mensajes.
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Building2,
    Database,
    DollarSign,
    GraduationCap,
    TrendingUp,
    Users,
    Zap,
    MessageSquare,
} from 'lucide-react';

import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { dbToBusinessName, getDbProfile } from '../constants/appConfig';
import { useContextOverview } from '../hooks/useContextOverview';

const KPI_ICON_MAP = {
    users: Users,
    'dollar-sign': DollarSign,
    'trending-up': TrendingUp,
    'graduation-cap': GraduationCap,
    database: Database,
};

// Seccion: tarjeta KPI reutilizable para la franja superior.
function BentoCard({ icon: Icon, label, value, valueColor, accent, hint = '', delay = 0 }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay }}
            className="flex-1 min-w-[160px] flex flex-col justify-between"
            style={{
                background: 'rgba(255, 255, 255, 0.03)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: 10,
                padding: '8px 14px',
                minHeight: 62,
                transition: 'all 0.2s ease',
                position: 'relative',
            }}
        >
            <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                <div style={{
                    width: 24, height: 24, borderRadius: 5,
                    background: 'rgba(255, 255, 255, 0.04)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                }}>
                    <Icon size={12} style={{ color: valueColor || 'rgba(255,255,255,0.4)' }} />
                </div>
                {accent && (
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"
                        style={{ boxShadow: '0 0 5px rgba(34, 211, 238, 0.3)' }} />
                )}
            </div>

            <div className="flex flex-col">
                <span style={{
                    fontSize: 7.5, fontWeight: 800, color: 'rgba(255,255,255,0.25)',
                    letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 0
                }}>
                    {label}
                </span>
                <span className="truncate" style={{
                    fontSize: 15, fontWeight: 700, lineHeight: 1,
                    color: valueColor || '#fff',
                    letterSpacing: '-0.01em',
                }}>
                    {value || '—'}
                </span>
            </div>

            {hint ? (
                <span style={{ fontSize: 7.5, color: 'rgba(255,255,255,0.15)', marginTop: 3, fontWeight: 500 }}>
                    {hint}
                </span>
            ) : null}
        </motion.div>
    );
}

export function ChatArea({
    chatHistory, setChatHistory,
    deviceType, userAuth, loading,
    prompt, setPrompt, motorIA, setMotorIA, handleQuery, cancelQuery,
    correctionHint, correct, setCorrectionHint,
    activeModule, textareaRef, chatEndRef,
    isSidebarOpen, connInfo, isConnectionReady,
    attachedImages, setAttachedImages,
}) {
    // Seccion: resolucion del contexto visible de empresa/base activa.
    const dbProfile = getDbProfile(connInfo?.database || '');
    const companyName = dbProfile?.business_name || dbToBusinessName(connInfo?.database || '');
    const shortName = dbProfile?.short_name || connInfo?.database || '';

    const showKpis = deviceType !== 'mobile' && connInfo?.database;

    // Determinar si estamos en CHAT con una empresa seleccionada de forma explicita.
    const isChatDB = connInfo?.database?.toUpperCase() === 'CHAT';
    const selectedCompanyCode = String(connInfo?.selected_company_code || '').trim().toUpperCase();
    const overviewTargetDb = selectedCompanyCode || connInfo?.database || '';
    const { overview } = useContextOverview(overviewTargetDb, Boolean(isConnectionReady));
    const adaptiveKpis = (overview?.kpis || []).slice(0, 3);
    const selectedCompany = selectedCompanyCode ? getDbProfile(selectedCompanyCode) : null;
    // Sugerencias contextuales según las áreas realmente detectadas en la empresa.
    const suggestedQuestions = (overview?.quick_questions || []).slice(0, 4);

    // Recomendación aplicada (28/08/2026): las sugerencias
    // solo vivían en el estado vacío del chat — en cuanto se enviaba el primer
    // mensaje, desaparecían para siempre y no había forma de volver a verlas sin
    // abrir una conversación nueva. Este botón las deja SIEMPRE accesibles, sin
    // ocupar espacio permanente en pantalla (popover bajo demanda, no un panel
    // fijo): un acceso discreto y constante, no un bloque que compite por
    // espacio con la conversación real.
    const [mostrarSugerencias, setMostrarSugerencias] = useState(false);

    // Mostrar informacion correcta segun el contexto
    const displayCompanyName = (isChatDB ? 'Mente VicMar Data AI' : (connInfo?.business_name || companyName));

    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden" style={{ background: 'var(--bg-main)' }}>
            <div className="flex-1 flex flex-col min-h-0 pt-4">
                <div className="w-full max-w-5xl px-6 mb-2 flex items-center gap-3 mx-auto">
                    <p style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
                        Área de Consulta Inteligente
                    </p>
                    <div className="flex-1 h-[1px]" style={{ background: 'var(--border)', opacity: 0.3 }} />
                </div>

                <div className="flex-1 w-full min-h-0 overflow-y-auto overflow-x-hidden chat-scrollbar px-4 sm:px-6 py-3 flex flex-col items-center">
                    <div className="max-w-[900px] w-full space-y-0.5">
                        {chatHistory.filter((message) => !message.isWelcome).length === 0 && !loading && (
                            <div className="flex flex-col items-center justify-center min-h-[35vh] space-y-4">
                                <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <div style={{
                                        position: 'absolute',
                                        inset: -40,
                                        background: 'radial-gradient(circle, rgba(59,130,246,0.1) 0%, transparent 70%)',
                                        borderRadius: '50%',
                                        filter: 'blur(20px)',
                                    }} />
                                    <img
                                        src="/logo.png"
                                        alt="Logo"
                                        style={{
                                            width: 160,
                                            height: 160,
                                            objectFit: 'contain',
                                            opacity: 0.18,
                                            filter: 'brightness(1.3) contrast(1.1) drop-shadow(0 0 30px rgba(59,130,246,0.2))',
                                            transition: 'all 0.5s ease',
                                        }}
                                    />
                                </div>
                                <span style={{
                                    fontSize: 11,
                                    fontWeight: 700,
                                    color: 'var(--text-faint)',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.25em',
                                    opacity: 0.4,
                                }}>
                                    VicMar Data AI Intelligent System
                                </span>

                                {/* Sugerencias de arranque: viven aquí, pegadas al input donde
                                    realmente se usan (patrón habitual de las interfaces de chat), en vez
                                    de en una tarjeta del dashboard que obligaba al usuario a
                                    memorizarlas y caminar hasta el chat. */}
                                {suggestedQuestions.length > 0 && (
                                    <div className="w-full max-w-2xl pt-4">
                                        <p className="mb-3 text-center text-[13px] text-white/35">
                                            Prueba preguntando:
                                        </p>
                                        <div className="flex flex-wrap justify-center gap-2">
                                            {suggestedQuestions.map((question, i) => (
                                                <button
                                                    key={i}
                                                    type="button"
                                                    onClick={(e) => handleQuery && handleQuery(e, question)}
                                                    className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-[13px] text-white/60 transition-colors hover:border-cyan-500/40 hover:bg-cyan-500/5 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
                                                >
                                                    {question}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {(() => {
                            const visibleMessages = chatHistory.filter((message) => !message.isWelcome);
                            return visibleMessages.map((msg, idx) => (
                                <motion.div key={msg.id || idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
                                    <ChatMessage
                                        msg={msg}
                                        idx={idx}
                                        chatHistory={chatHistory}
                                        setChatHistory={setChatHistory}
                                        deviceType={deviceType}
                                        userAuth={userAuth}
                                        activeModule={activeModule}
                                        handleQuery={handleQuery}
                                        isLastMessage={idx === visibleMessages.length - 1}
                                        loading={loading}
                                    />
                                </motion.div>
                            ));
                        })()}

                        <div ref={chatEndRef} style={{ height: 6 }} />
                    </div>
                </div>
            </div>

            {/* zIndex 50: la zona del input (y con ella la ficha de sugerencias,
                que se posiciona respecto a este contenedor) tiene que quedar
                SIEMPRE por encima de lo que se muestre en el área de respuesta.
                Defecto detectado en pruebas (30/08/2026): el encabezado de
                las tablas de resultados es `sticky top-0 ... z-10` (ver
                DataVisualizer.jsx), y como este bloque no declaraba ningún
                z-index, esa cabecera se dibujaba ENCIMA de las sugerencias y las
                tapaba. Con 50 queda por delante de cualquier contenido del chat
                sin llegar al nivel de los modales (z-[100]). */}
            <div className="shrink-0 w-full flex justify-center relative pt-1" style={{ zIndex: 50 }}>
                {/* La ficha de sugerencias ahora vive pegada a la MISMA tarjeta
                    del textarea (mismo fondo/borde que ChatInput, ver
                    --bg-main/--border), no como una caja oscura suelta y
                    aparte — corregido (29/08/2026). El
                    botón que la abre/cierra se movió adentro de ChatInput. */}
                <AnimatePresence>
                    {mostrarSugerencias && suggestedQuestions.length > 0 && (
                        <motion.div
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 8 }}
                            transition={{ duration: 0.15 }}
                            className="absolute bottom-full mb-2 w-full max-w-[1000px] mx-4 sm:mx-10 rounded-2xl p-3 shadow-2xl"
                            style={{ background: 'var(--bg-main)', border: '1px solid var(--border)', zIndex: 2 }}
                        >
                            <p className="mb-2 px-1 text-[11px] font-bold uppercase tracking-wide text-white/35">
                                Sugerencias para {shortName || 'esta empresa'}
                            </p>
                            <div className="flex flex-col gap-1">
                                {suggestedQuestions.map((question, i) => (
                                    <button
                                        key={i}
                                        type="button"
                                        onClick={(e) => {
                                            setMostrarSugerencias(false);
                                            handleQuery && handleQuery(e, question);
                                        }}
                                        className="rounded-lg px-3 py-2 text-left text-[13px] text-white/70 transition-colors hover:bg-white/[0.06] hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
                                    >
                                        {question}
                                    </button>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                <ChatInput
                    prompt={prompt}
                    setPrompt={setPrompt}
                    userAuth={userAuth}
                    motorIA={motorIA}
                    setMotorIA={setMotorIA}
                    handleQuery={handleQuery}
                    cancelQuery={cancelQuery}
                    loading={loading}
                    correctionHint={correctionHint}
                    correct={correct}
                    setCorrectionHint={setCorrectionHint}
                    activeModule={activeModule}
                    textareaRef={textareaRef}
                    isSidebarOpen={isSidebarOpen}
                    attachedImages={attachedImages}
                    setAttachedImages={setAttachedImages}
                    hasSugerencias={suggestedQuestions.length > 0}
                    mostrarSugerencias={mostrarSugerencias}
                    onToggleSugerencias={() => setMostrarSugerencias((v) => !v)}
                />
            </div>
        </div>
    );
}
