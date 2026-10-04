/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-UI-MOBILE-03]
 * ============================================================================
 * ARCHIVO: ChatInputMobile.jsx
 * MÓDULO: UI / Mobile Interactions
 * 
 * 🎯 PROPÓSITO GERENCIAL:
 * Interfaz de entrada táctil. Permite a los gerentes dictar u escribir
 * órdenes a la IA desde su celular de forma rápida, fluida y sin
 * perder el foco de los datos que están mirando.
 * 
 * 📍 PUNTO DE INTERFAZ:
 * Pegado obligatoriamente a la base de la pantalla táctil (`bottom-0`).
 * 
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Componente `textarea` que auto-expande su altura según el texto.
 * - Indicador superior flotante mostrando qué "Módulo de IA" está pensando.
 * - Corrección ortográfica al vuelo (Auto-Core) integrada silenciosamente.
 * ============================================================================
 */

import React from 'react';
import { Loader2, Send, Square } from 'lucide-react';

export const ChatInputMobile = ({ prompt, setPrompt, handleQuery, cancelQuery, loading, correctionHint, correct, setCorrectionHint, activeModule, textareaRef }) => {
    return (
        <div className="px-2 pb-0 w-full relative z-20">
            <div className="max-w-full mx-auto">
                <div className="flex justify-center mb-2">
                    <div className="flex items-center gap-1.5 bg-white/[0.03] backdrop-blur-3xl px-3 py-1 rounded-full border border-white/5 shadow-md">
                        <div className={`h-1.5 w-1.5 rounded-full ${loading ? 'bg-cyan-400 animate-pulse' : 'bg-cyan-500'}`} />
                        <span className="text-[6.5px] font-black text-white/30 uppercase tracking-[0.2em] whitespace-nowrap">
                            {activeModule ? activeModule : 'ADN MAESTRO'}
                        </span>
                    </div>
                </div>

                <div className="glass-panel p-0.5 rounded-[22px] border border-white/5 shadow-2xl relative bg-black/40 backdrop-blur-3xl overflow-hidden mb-1">
                    <form onSubmit={handleQuery} className="relative bg-[#020617]/90 rounded-[20px] border border-white/5 shadow-inner overflow-hidden">
                        <div className="flex gap-2 px-3 py-1.5 w-full items-center min-h-[48px]">
                            {correctionHint && (
                                <div className="absolute -top-8 left-1/2 -translate-x-1/2 text-[11px] font-black text-cyan-400 uppercase tracking-widest animate-pulse z-30 bg-black/95 px-2 py-0.5 rounded-full border border-cyan-500/10">
                                    {correctionHint}
                                </div>
                            )}
                            <textarea
                                ref={textareaRef}
                                value={prompt}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    if (val.slice(-1) === ' ' || val.slice(-1) === '?') {
                                        const { text, wasCorrected } = correct(val);
                                        setPrompt(text);
                                        if (wasCorrected) {
                                            setCorrectionHint("AUTO-CORE");
                                            setTimeout(() => setCorrectionHint(null), 1500);
                                        }
                                    } else {
                                        setPrompt(val);
                                    }
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleQuery(e);
                                    }
                                }}
                                disabled={loading}
                                spellCheck="true"
                                lang="es"
                                placeholder="QUE DESEAS CONSULTAR?"
                                className={`flex-1 bg-transparent border-none outline-none text-[14px] text-white text-center placeholder:text-white/20 placeholder:font-black placeholder:uppercase placeholder:tracking-[0.02em] resize-none font-medium leading-relaxed tracking-tight self-center ${loading ? 'opacity-30' : 'opacity-100'} transition-all`}
                                rows="1"
                                style={{ maxHeight: '80px', overflowY: 'auto' }}
                            />
                            <div className="flex items-center shrink-0">
                                {loading ? (
                                    <button type="button" onClick={cancelQuery}
                                        className="h-9 w-9 rounded-[12px] bg-rose-600/80 flex items-center justify-center shadow-lg active:scale-90 transition-all shrink-0 border border-white/10">
                                        <Square className="text-white" size={13} fill="white" />
                                    </button>
                                ) : (
                                    <button type="submit" disabled={!prompt.trim()}
                                        className="h-9 w-9 rounded-[12px] bg-gradient-to-tr from-cyan-600 to-blue-800 flex items-center justify-center shadow-lg active:scale-90 transition-all disabled:opacity-30 shrink-0 border border-white/10">
                                        <Send className="text-white" size={14} />
                                    </button>
                                )}
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};
