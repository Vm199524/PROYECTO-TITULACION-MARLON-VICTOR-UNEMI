/**
 * @file Área de conversación del chat en teléfonos. Ocupa el centro de la
 * pantalla entre la cabecera y la barra de navegación de DashboardMobile:
 * muestra una barra de estado con el rol del usuario y el número de mensajes,
 * la lista de mensajes (ChatMessage), el indicador de carga y la caja de
 * entrada ChatInputMobile anclada al fondo.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Database, Loader2 } from 'lucide-react';
import { ChatMessage } from '../components/ChatMessage';
import { ChatInputMobile } from './ChatInputMobile';

/**
 * Renderiza la conversación en la vista móvil.
 * @param {object} props
 * @param {Array<object>} props.chatHistory Mensajes de la sesión activa.
 * @param {function} props.setChatHistory Actualiza el historial.
 * @param {object|null} props.userAuth Usuario autenticado (nombre y rol).
 * @param {boolean} props.loading Indica si hay una consulta en curso.
 * @param {string} props.prompt Texto de la caja de entrada.
 * @param {function} props.setPrompt Actualiza el texto de entrada.
 * @param {function} props.handleQuery Envía la pregunta.
 * @param {function} props.cancelQuery Cancela la consulta en curso.
 * @param {string|null} props.correctionHint Aviso de autocorrección visible.
 * @param {function} props.correct Función de autocorrección (useAutoCorrect).
 * @param {function} props.setCorrectionHint Muestra u oculta el aviso de autocorrección.
 * @param {string|null} props.activeModule Módulo de análisis activo.
 * @param {object} props.textareaRef Referencia a la caja de texto.
 * @param {object} props.chatEndRef Referencia al final de la lista, para el desplazamiento.
 * @returns {JSX.Element} Área de chat móvil.
 */
export function ChatAreaMobile({
    chatHistory,
    setChatHistory,
    userAuth,
    loading,
    prompt,
    setPrompt,
    handleQuery,
    cancelQuery,
    correctionHint,
    correct,
    setCorrectionHint,
    activeModule,
    textareaRef,
    chatEndRef,
}) {
    // Degradado corporativo del fondo del chat.
    const chatBgGradient = "linear-gradient(160deg,rgba(32,58,86,0.88) 0%,rgba(26,50,78,0.92) 45%,rgba(18,36,58,0.96) 100%)";

    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden relative" style={{ background: chatBgGradient }}>
            
            {/* 1. Barra de estado del chat: rol del usuario y número de mensajes. */}
            <div className="shrink-0 px-6 py-2 bg-[#1a3654]/95 border-b border-white/[0.05] flex items-center justify-between text-[7.5px] font-black uppercase tracking-[0.4em] text-white/50 backdrop-blur-3xl z-20">
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
                    <span className="truncate max-w-[120px]">RED: {userAuth?.role || 'GERENCIA'}</span>
                </div>
                <div className="flex items-center gap-2">
                     <span className="whitespace-nowrap">MAESTRO: {chatHistory.length}</span>
                </div>
            </div>

            {/* 2. Lista de mensajes con desplazamiento vertical. */}
            <div className="flex-1 overflow-y-auto custom-scrollbar px-4 pb-2 relative z-10 pt-4">
                <div className="max-w-full mx-auto space-y-12 pb-24 text-left">
                    {chatHistory.length === 0 && (
                        <div className="h-full min-h-[40vh] flex flex-col items-center justify-center opacity-10 py-10 pt-16">
                            <Database className="text-white mb-8" size={80} strokeWidth={0.2} />
                            <h2 className="text-2xl font-black tracking-[1em] uppercase text-white opacity-20">VICMAR</h2>
                        </div>
                    )}
                    {chatHistory.map((msg, idx) => (
                        <motion.div key={msg.id || idx} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} className="w-full">
                            <ChatMessage
                                msg={msg} idx={idx} chatHistory={chatHistory} setChatHistory={setChatHistory}
                                deviceType="mobile" userAuth={userAuth} activeModule={activeModule}
                                handleQuery={handleQuery} isLastMessage={idx === chatHistory.length - 1} loading={loading}
                            />
                        </motion.div>
                    ))}
                    {loading && (
                        <div className="flex items-center gap-3 text-white/40 font-black tracking-widest uppercase text-[11px] ml-4 bg-white/5 px-4 py-2 rounded-full w-fit animate-pulse border border-white/5">
                            <Loader2 size={12} className="animate-spin" /> PROCESANDO ADN...
                        </div>
                    )}
                    <div ref={chatEndRef} className="h-10" />
                </div>
            </div>

            {/* 3. Caja de entrada: `absolute` (no `fixed`) para quedar anclada
                al fondo de este componente, que flexbox ya encaja entre la
                cabecera y la barra de navegación inferior (ver
                DashboardMobile). Con `fixed` se pegaría al borde de la
                pantalla y taparía la barra de navegación. */}
            <div className="absolute bottom-0 left-0 z-[1000] w-full">
                <ChatInputMobile
                    prompt={prompt}
                    setPrompt={setPrompt}
                    handleQuery={handleQuery}
                    cancelQuery={cancelQuery}
                    loading={loading}
                    correctionHint={correctionHint}
                    correct={correct}
                    setCorrectionHint={setCorrectionHint}
                    activeModule={activeModule}
                    textareaRef={textareaRef}
                />
            </div>
        </div>
    );
}
