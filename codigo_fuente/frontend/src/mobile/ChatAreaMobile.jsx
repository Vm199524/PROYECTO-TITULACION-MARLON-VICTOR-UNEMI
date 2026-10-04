/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-UI-MOBILE-02]
 * ============================================================================
 * ARCHIVO: ChatAreaMobile.jsx
 * MÓDULO: UI / Mobile Chat Space
 * 
 * 🎯 PROPÓSITO GERENCIAL:
 * Lienzo principal de conversación exclusivo para smartphones. Garantiza 
 * que la lectura de la IA sea impecable y sin distracciones, maximizando
 * el espacio útil en pantallas reducidas.
 * 
 * 📍 PUNTO DE INTERFAZ:
 * Ocupa todo el centro de la pantalla móvil, encajonado entre el cabezal
 * fijo (`DashboardMobile`) y la caja de texto (`ChatInputMobile`).
 * 
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Renderizado en bucle de `ChatMessage` optimizado para móvil.
 * - Barra de estatus flotante (Red Activa, Sincronización de Sesión).
 * - Auto-desplazamiento suave al fondo cuando la IA responde.
 * ============================================================================
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Database, Loader2 } from 'lucide-react';
import { ChatMessage } from '../components/ChatMessage';
import { ChatInputMobile } from './ChatInputMobile';

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
    // Definimos el estilo del degradado corporativo
    const chatBgGradient = "linear-gradient(160deg,rgba(32,58,86,0.88) 0%,rgba(26,50,78,0.92) 45%,rgba(18,36,58,0.96) 100%)";

    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden relative" style={{ background: chatBgGradient }}>
            
            {/* 1. Status Bar del Chat (Indica que el software está sincronizado) */}
            <div className="shrink-0 px-6 py-2 bg-[#1a3654]/95 border-b border-white/[0.05] flex items-center justify-between text-[7.5px] font-black uppercase tracking-[0.4em] text-white/50 backdrop-blur-3xl z-20">
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
                    <span className="truncate max-w-[120px]">RED: {userAuth?.role || 'GERENCIA'}</span>
                </div>
                <div className="flex items-center gap-2">
                     <span className="whitespace-nowrap">MAESTRO: {chatHistory.length}</span>
                </div>
            </div>

            {/* 2. Zona Dinámica de Mensajes (Scrolleable y limpia para lectura) */}
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

            {/* 3. Footer de Entrada de Datos — `absolute` (no `fixed`) para
                quedar anclado al fondo de ESTE componente, que ya está
                encajonado por flexbox entre el header y la barra de
                navegación inferior (ver DashboardMobile). Con `fixed` se
                pegaba al borde real de la pantalla y tapaba la barra de
                navegación nueva. */}
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
