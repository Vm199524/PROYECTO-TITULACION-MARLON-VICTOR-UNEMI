/**
 * @file Caja de entrada del chat en teléfonos. Muestra el módulo activo,
 * aplica la autocorrección al escribir un espacio o «?» (con el aviso
 * AUTO-CORE), envía con Enter (Shift+Enter agrega una línea) y cambia el
 * botón de enviar por uno de cancelar mientras la consulta está en curso.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React from 'react';
import { Loader2, Send, Square } from 'lucide-react';

/**
 * Renderiza el formulario de pregunta de la vista móvil.
 * @param {object} props
 * @param {string} props.prompt Texto actual.
 * @param {function} props.setPrompt Actualiza el texto.
 * @param {function} props.handleQuery Envía la pregunta (submit o Enter).
 * @param {function} props.cancelQuery Cancela la consulta en curso.
 * @param {boolean} props.loading Indica si hay una consulta en curso.
 * @param {string|null} props.correctionHint Aviso de autocorrección visible.
 * @param {function(string): {text: string, wasCorrected: boolean}} props.correct Autocorrección.
 * @param {function} props.setCorrectionHint Muestra u oculta el aviso.
 * @param {string|null} props.activeModule Módulo activo; si falta, muestra «ADN MAESTRO».
 * @param {object} props.textareaRef Referencia a la caja de texto.
 * @returns {JSX.Element} Formulario de entrada.
 */
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
