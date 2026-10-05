/**
 * @file Área central del chat en escritorio. Muestra el estado vacío con preguntas
 * sugeridas, la lista de mensajes (ChatMessage) y el campo de entrada (ChatInput) con
 * su ficha de sugerencias bajo demanda. Las sugerencias provienen de las áreas
 * detectadas en la empresa activa (/api/context-overview, vía useContextOverview). La
 * renderiza DashboardDesktop.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
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

// Tarjeta KPI compacta (ícono, etiqueta, valor y pista opcional) para la franja superior.
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

/**
 * Muestra la conversación activa y el campo de consulta.
 *
 * @param {object} props
 * @param {object[]} props.chatHistory - Mensajes de la conversación; los de bienvenida (`isWelcome`) no se muestran.
 * @param {Function} props.setChatHistory - Actualiza los mensajes (p. ej. al editar o reintentar).
 * @param {string} props.deviceType - Tipo de dispositivo ('mobile', 'desktop', etc.).
 * @param {object} props.userAuth - Usuario autenticado.
 * @param {boolean} props.loading - Si hay una consulta en curso.
 * @param {string} props.prompt - Texto actual del campo de consulta.
 * @param {Function} props.setPrompt - Actualiza el texto del campo.
 * @param {string} props.motorIA - Motor de IA elegido.
 * @param {Function} props.setMotorIA - Cambia el motor de IA.
 * @param {Function} props.handleQuery - Envía una consulta; recibe `(evento, texto)`.
 * @param {Function} props.cancelQuery - Cancela la consulta en curso.
 * @param {string} props.correctionHint - Corrección sugerida para el texto escrito.
 * @param {Function} props.correct - Aplica la corrección sugerida al texto.
 * @param {object} props.textareaRef - Referencia al textarea de ChatInput.
 * @param {object} props.chatEndRef - Referencia al final de la lista, para desplazarse al último mensaje.
 * @param {object} props.connInfo - Conexión activa (`database`, `selected_company_code`, `business_name`).
 * @param {boolean} props.isConnectionReady - Habilita la consulta de sugerencias al backend.
 * @param {Array} props.attachedImages - Imágenes adjuntas a la consulta.
 * @param {Function} props.setAttachedImages - Actualiza las imágenes adjuntas.
 * @returns {JSX.Element} Área de chat.
 */
export function ChatArea({
    chatHistory, setChatHistory,
    deviceType, userAuth, loading,
    prompt, setPrompt, motorIA, setMotorIA, handleQuery, cancelQuery,
    correctionHint, correct, setCorrectionHint,
    activeModule, textareaRef, chatEndRef,
    isSidebarOpen, connInfo, isConnectionReady,
    attachedImages, setAttachedImages,
}) {
    // Contexto visible de la empresa o base activa.
    const dbProfile = getDbProfile(connInfo?.database || '');
    const companyName = dbProfile?.business_name || dbToBusinessName(connInfo?.database || '');
    const shortName = dbProfile?.short_name || connInfo?.database || '';

    const showKpis = deviceType !== 'mobile' && connInfo?.database;

    // Detecta si la conexión es CHAT con una empresa seleccionada de forma explícita.
    const isChatDB = connInfo?.database?.toUpperCase() === 'CHAT';
    const selectedCompanyCode = String(connInfo?.selected_company_code || '').trim().toUpperCase();
    const overviewTargetDb = selectedCompanyCode || connInfo?.database || '';
    const { overview } = useContextOverview(overviewTargetDb, Boolean(isConnectionReady));
    const adaptiveKpis = (overview?.kpis || []).slice(0, 3);
    const selectedCompany = selectedCompanyCode ? getDbProfile(selectedCompanyCode) : null;
    // Sugerencias contextuales según las áreas realmente detectadas en la empresa.
    const suggestedQuestions = (overview?.quick_questions || []).slice(0, 4);

    // Las sugerencias del estado vacío desaparecen al enviar el primer mensaje.
    // Este interruptor las deja SIEMPRE accesibles mediante un popover bajo
    // demanda: un acceso discreto que no ocupa espacio fijo ni compite con la
    // conversación.
    const [mostrarSugerencias, setMostrarSugerencias] = useState(false);

    // Nombre que se muestra según el contexto (CHAT o empresa).
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

                                {/* Sugerencias de arranque junto al campo donde se usan (patrón
                                    habitual de las interfaces de chat), para que el usuario no
                                    tenga que memorizarlas desde el panel y escribirlas aquí. */}
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

            {/* zIndex 50: la zona del campo (y con ella la ficha de sugerencias,
                que se posiciona respecto a este contenedor) debe quedar SIEMPRE
                por encima del área de respuesta. El encabezado de las tablas de
                resultados es `sticky top-0 ... z-10` (ver DataVisualizer.jsx) y,
                sin un z-index aquí, se dibujaría ENCIMA de las sugerencias. Con
                50 queda por delante de cualquier contenido del chat sin llegar
                al nivel de los modales (z-[100]). */}
            <div className="shrink-0 w-full flex justify-center relative pt-1" style={{ zIndex: 50 }}>
                {/* La ficha de sugerencias va pegada a la MISMA tarjeta del
                    textarea (mismo fondo y borde que ChatInput: --bg-main y
                    --border), no como una caja oscura aparte. El botón que la
                    abre o cierra está dentro de ChatInput. */}
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
                                Sugerencias para {shortName || 'esta institución'}
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
