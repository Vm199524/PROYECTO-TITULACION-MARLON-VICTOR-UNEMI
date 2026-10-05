/**
 * @file Mensaje del chat. Dibuja la pregunta del usuario (con edición y reenvío) o la
 * respuesta de la IA: texto en Markdown, resultados en tabla o gráfico (DataVisualizer,
 * PayslipView), preguntas rápidas, insignia de origen de la respuesta, lectura en voz
 * alta y regeneración. Las pestañas SQL y «Cómo se calculó» solo se muestran al rol
 * ADMINISTRADOR. Lo usan ChatArea y ChatAreaMobile.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */
import React, { useState } from 'react';
import {
    Activity, BarChart3, Brain, Check, ClipboardList, Code, Copy, FileText, Hexagon,
    Pencil, PieChart as PieChartIcon, Pin, RotateCcw, Sparkles, Table as TableIcon, Target,
    TrendingUp, Volume2, VolumeX, Zap,
} from 'lucide-react';

import { useLectura, construirRespuestaHablada } from '../hooks/useLectura';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { DataVisualizer } from './DataVisualizer';
import { PayslipView } from './PayslipView';
import { formatValue, formatHeader, formatAxisName, parseNum } from '../utils/formatters';
import { normalizeQueryResult } from '../utils/queryResult';
import { tokenizeSql, SQL_TOKEN_CLASSNAMES } from '../utils/sqlHighlight';

// ── Bloque de SQL con resaltado de sintaxis + copiar en un clic ──
// Resaltado ligero (sin librería nueva): separa el texto en tokens y les
// aplica color según sean palabra clave, cadena, número o comentario.
const SqlBlock = ({ sql }) => {
    const [copied, setCopied] = useState(false);
    const tokens = React.useMemo(() => tokenizeSql(sql), [sql]);

    const copiarSql = async () => {
        if (!sql) return;
        try {
            await navigator.clipboard.writeText(sql);
        } catch {
            // Alternativa para navegadores o entornos sin permiso de portapapeles.
            const ta = document.createElement('textarea');
            ta.value = sql;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand('copy'); } catch { /* sin acción */ }
            document.body.removeChild(ta);
        }
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    if (!sql) {
        return (
            <pre className="bg-black/40 rounded-lg px-3 py-1.5 font-mono text-[12px] leading-snug text-emerald-400/80 border border-white/5 overflow-x-auto whitespace-pre-wrap break-words">
                No SQL generated for this response.
            </pre>
        );
    }

    return (
        <div className="relative group">
            <button
                onClick={copiarSql}
                aria-label={copied ? 'SQL copiado' : 'Copiar SQL'}
                title={copied ? 'Copiado' : 'Copiar SQL'}
                className={`absolute top-1.5 right-1.5 flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wide border transition-colors ${
                    copied
                        ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                        : 'bg-white/5 text-white/40 border-white/10 hover:text-white/80 hover:border-white/20'
                }`}
            >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? 'Copiado' : 'Copiar'}
            </button>
            <pre className="bg-black/40 rounded-lg px-3 py-1.5 pr-20 font-mono text-[12px] leading-snug border border-white/5 overflow-x-auto whitespace-pre-wrap break-words">
                {tokens.map((tok, i) => (
                    <span key={i} className={SQL_TOKEN_CLASSNAMES[tok.type] || SQL_TOKEN_CLASSNAMES.plain}>
                        {tok.text}
                    </span>
                ))}
            </pre>
        </div>
    );
};

// ── Insignia de origen (modo transparencia) ──
// Muestra de un vistazo si la respuesta vino de una fórmula certificada,
// del caché semántico o fue generada libremente por la IA. Así el usuario
// nunca tiene que adivinar qué tan «oficial» es un número.
const ANSWER_SOURCE_META = {
    metrica_certificada: {
        label: 'Métrica certificada',
        Icon: Pin,
        className: 'bg-[#3B82F6]/15 text-[#93C5FD] border-[#3B82F6]/30',
    },
    cache_semantico: {
        label: 'Memoria semántica',
        Icon: Zap,
        className: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
    },
    ia_generativa: {
        label: 'Generado por IA',
        Icon: Sparkles,
        className: 'bg-white/5 text-white/50 border-white/10',
    },
};

const AnswerSourceBadge = ({ source }) => {
    const meta = ANSWER_SOURCE_META[source];
    if (!meta) return null;
    const { label, Icon, className } = meta;
    return (
        <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[11px] font-bold uppercase tracking-wide ${className}`}
            title="Indica el origen de esta respuesta (modo transparencia)"
        >
            <Icon size={10} />
            {label}
        </span>
    );
};

/**
 * Muestra un mensaje del chat, ya sea del usuario o de la IA.
 *
 * @param {object} props
 * @param {object} props.msg - Mensaje (`type`, `content`, `result`, `quickQuestions`, `isStreaming`, `activeTab`...).
 * @param {Function} props.setChatHistory - Actualiza el historial (pestaña activa, edición, regeneración).
 * @param {object[]} props.chatHistory - Historial completo de la conversación.
 * @param {object} props.userAuth - Usuario autenticado; su rol decide si se ven las pestañas técnicas.
 * @param {boolean} [props.isFixed=false] - Modo barra fija: solo muestra las preguntas rápidas.
 * @param {Function} props.handleQuery - Envía una consulta; recibe `(evento, texto, opciones)`.
 * @param {boolean} [props.isLastMessage=false] - Si es la última respuesta (habilita «Regenerar»).
 * @param {boolean} [props.loading=false] - Si hay una consulta en curso.
 * @returns {JSX.Element} Burbuja del mensaje.
 */
export const ChatMessage = ({
    msg, setChatHistory, chatHistory, idx, deviceType,
    userAuth, activeModule, isFixed = false, handleQuery,
    isLastMessage = false, loading = false,
}) => {
    // Las preguntas rápidas que envía el backend se muestran siempre como
    // botones; por ejemplo, las tres opciones del rol Invitado (demo, solicitar
    // acceso, conectar BD), que de otro modo quedarían como texto Markdown.
    const showQuickQuestions = true;

    // Las pestañas SQL y «Cómo se calculó» exponen nombres reales de vistas y
    // tablas y la lógica interna del pipeline, así que solo las ve el rol
    // ADMINISTRADOR. La defensa principal está en el backend
    // (`_redactar_campos_privados` en api/routes_query.py, que no envía esos
    // campos a otros roles); esta comprobación es una segunda capa para no
    // intentar pintar la pestaña si el campo llegara igual.
    const esAdministrador = String(userAuth?.role || '').trim().toUpperCase() === 'ADMINISTRADOR';

    // Edición de la propia pregunta y estado del texto editado. Se declaran
    // antes de cualquier return condicional para no alterar el orden de los
    // hooks entre mensajes de usuario y de IA (mismo patrón que useLectura
    // más abajo).
    const [editing, setEditing] = useState(false);
    const [editedText, setEditedText] = useState(msg.content || '');

    const puedeEditar = typeof setChatHistory === 'function' && Array.isArray(chatHistory) && !!handleQuery;

    // ── USUARIO (Burbuja azul sólida) ──
    if (msg.type === 'user') {
        // «Editar y reenviar»: corta el historial desde este mensaje en
        // adelante (se descarta la respuesta anterior) y reenvía el texto
        // editado como una pregunta nueva.
        const guardarEdicion = () => {
            const texto = editedText.trim();
            if (!texto) { setEditing(false); return; }
            if (!puedeEditar) { setEditing(false); return; }
            setChatHistory((prev) => {
                const i = prev.findIndex((entry) => entry?.id === msg?.id);
                return i === -1 ? prev : prev.slice(0, i);
            });
            setEditing(false);
            handleQuery(null, texto);
        };

        const cancelarEdicion = () => {
            setEditedText(msg.content || '');
            setEditing(false);
        };

        if (editing) {
            return (
                <div className="flex justify-end mb-0.5 w-full">
                    <div className="w-full sm:w-[520px] max-w-full bg-[#1C2128] border border-[#3B82F6]/40 px-4 py-3 rounded-2xl rounded-tr-none shadow-lg">
                        <textarea
                            autoFocus
                            value={editedText}
                            onChange={(e) => setEditedText(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); guardarEdicion(); }
                                if (e.key === 'Escape') cancelarEdicion();
                            }}
                            rows={2}
                            className="w-full bg-transparent text-[15px] text-white outline-none resize-none"
                        />
                        <div className="flex justify-end gap-2 mt-2">
                            <button type="button" onClick={cancelarEdicion}
                                className="px-3 py-1 rounded-lg text-[11px] font-bold uppercase text-white/50 hover:text-white/80 transition-colors">
                                Cancelar
                            </button>
                            <button type="button" onClick={guardarEdicion} disabled={!editedText.trim()}
                                className="px-3 py-1 rounded-lg text-[11px] font-bold uppercase bg-[#3B82F6] text-white hover:brightness-110 disabled:opacity-40 transition-all">
                                Guardar y reenviar
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return (
            <div className="flex justify-end mb-0.5 w-full group">
                <div className="max-w-[75%] flex items-start gap-2">
                    {puedeEditar && !loading && (
                        <button
                            type="button"
                            onClick={() => { setEditedText(msg.content || ''); setEditing(true); }}
                            aria-label="Editar y reenviar esta pregunta"
                            title="Editar y reenviar"
                            className="opacity-0 group-hover:opacity-100 mt-2 p-1.5 rounded-md text-white/25 hover:text-white/70 hover:bg-white/5 transition-all shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 focus-visible:opacity-100"
                        >
                            <Pencil size={13} aria-hidden="true" />
                        </button>
                    )}
                    <div
                        className="bg-[#3B82F6] px-4 py-2 rounded-2xl rounded-tr-none text-[15.5px] font-medium text-white shadow-lg"
                        style={{ userSelect: 'text', WebkitUserSelect: 'text' }}
                    >
                        {Array.isArray(msg.images) && msg.images.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-2">
                                {msg.images.map((src, i) => (
                                    <img
                                        key={i}
                                        src={src}
                                        alt={`Imagen adjunta ${i + 1}`}
                                        className="w-16 h-16 object-cover rounded-lg border border-white/30 shadow-sm"
                                    />
                                ))}
                            </div>
                        )}
                        {msg.content}
                    </div>
                </div>
            </div>
        );
    }

    // ── Respuesta de la IA de VicMar Data AI (estilo minimalista) ──
    const result = normalizeQueryResult(msg.result);
    const hasStructuredResult = !!msg.result;
    const activeTab = msg.activeTab || 'Resultados';

    const setTab = (t) => {
        if (typeof setChatHistory !== 'function' || !Array.isArray(chatHistory)) return;

        setChatHistory((prevHistory) => {
            const targetIndex = prevHistory.findIndex((entry) => entry?.id === msg?.id);
            if (targetIndex === -1) return prevHistory;

            const nextHistory = [...prevHistory];
            nextHistory[targetIndex] = { ...nextHistory[targetIndex], activeTab: t };
            return nextHistory;
        });
    };

    const activeViz = result?.user_viz_override || result?.render?.type || result?.visualization_type || 'table';

    // Lectura en voz alta con la voz local del sistema: el texto no sale del
    // equipo. Es a petición (botón), nunca automática: una respuesta que se lee
    // sola en una oficina con datos de sueldos sería indiscreta.
    const { hablar, hablando, disponible: lecturaDisponible } = useLectura();
    const leerRespuesta = () => {
        // Se construye desde los datos, no desde el texto: la cifra suele vivir
        // en `rows` y no en la explicación.
        hablar(construirRespuestaHablada({ content: msg.content, result }));
    };

    // «Regenerar» solo se ofrece en la última respuesta del hilo: regenerar una
    // intermedia no tiene sentido porque el historial no admite ramas. Quita
    // solo esta burbuja de IA y reenvía la misma pregunta con skipUserBubble
    // para no duplicarla.
    const puedeRegenerar = isLastMessage && puedeEditar && !msg.isStreaming && !loading;
    const regenerar = () => {
        if (!puedeRegenerar) return;
        const i = chatHistory.findIndex((entry) => entry?.id === msg?.id);
        if (i === -1) return;
        let userIdx = i - 1;
        while (userIdx >= 0 && chatHistory[userIdx]?.type !== 'user') userIdx -= 1;
        if (userIdx < 0) return;
        const userContent = chatHistory[userIdx]?.content;
        if (!userContent) return;
        setChatHistory((prev) => prev.filter((entry) => entry?.id !== msg?.id));
        handleQuery(null, userContent, { skipUserBubble: true });
    };

    return (
        <div className="flex justify-start mb-0.5 w-full">
            <div className="w-full flex gap-3">
                {/* Ícono de avatar discreto */}
                {!isFixed && (
                    <div className="shrink-0 mt-1">
                        <div className="w-8 h-8 rounded-lg bg-[#3B82F6]/10 border border-[#3B82F6]/20 flex items-center justify-center">
                            <Brain size={16} className="text-[#3B82F6]" />
                        </div>
                    </div>
                )}

                <div className="flex-1 flex flex-col min-w-0">
                    {/* Encabezado «IA de VicMar Data AI»; se oculta en el modo barra fija */}
                    {!isFixed && (
                        <div className="flex items-center gap-2 mb-0.5 px-1">
                            <span className="text-[13px] font-bold text-white/50 tracking-tight">IA de VicMar Data AI </span>
                            <AnswerSourceBadge source={result?.answer_source} />

                            {lecturaDisponible && !msg.isStreaming && (msg.content || result?.explanation) && (
                                <button
                                    onClick={leerRespuesta}
                                    aria-label={hablando ? 'Detener lectura' : 'Escuchar esta respuesta'}
                                    aria-pressed={hablando}
                                    title={hablando ? 'Detener' : 'Escuchar respuesta'}
                                    className={`rounded-md p-1 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 ${
                                        hablando ? 'text-cyan-400' : 'text-white/25 hover:text-white/60'
                                    }`}
                                >
                                    {hablando
                                        ? <VolumeX size={14} aria-hidden="true" />
                                        : <Volume2 size={14} aria-hidden="true" />}
                                </button>
                            )}

                            {puedeRegenerar && (
                                <button
                                    onClick={regenerar}
                                    aria-label="Regenerar esta respuesta"
                                    title="Regenerar respuesta"
                                    className="rounded-md p-1 text-white/25 hover:text-white/60 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
                                >
                                    <RotateCcw size={13} aria-hidden="true" />
                                </button>
                            )}

                            {/* Pestañas discretas si hay SQL o trazabilidad que mostrar; solo ADMINISTRADOR */}
                            {esAdministrador && !!(result?.sql?.text || result?.analysis?.steps?.length) && (
                                <div className="ml-auto flex gap-1 p-0.5 bg-white/5 rounded-lg border border-white/10 overflow-x-auto no-scrollbar">
                                    {[
                                        { id: 'Resultados', label: 'Respuesta' },
                                        ...(result?.sql?.text ? [{ id: 'Analisis Tecnico (SQL)', label: 'SQL' }] : []),
                                        ...(result?.analysis?.steps?.length ? [{ id: 'Trazabilidad', label: 'Cómo se calculó' }] : []),
                                    ].map(t => (
                                        <button
                                            key={t.id} onClick={() => setTab(t.id)}
                                            className={`px-3 py-1 rounded-md text-[11px] font-bold uppercase transition-all whitespace-nowrap ${activeTab === t.id ? 'bg-[#3B82F6] text-white' : 'text-white/40 hover:text-white/60'}`}
                                        >
                                            {t.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Cuerpo del mensaje: cambia según sea barra fija o mensaje normal */}
                    {!isFixed ? (
                        <div className="bg-[#1C2128] border border-[#30363D] rounded-xl px-3 py-1.5 shadow-sm" style={{ userSelect: 'text', WebkitUserSelect: 'text' }}>

                            {/* Pestaña Resultados (Markdown o visualización) */}
                            {activeTab === 'Resultados' && (
                                <div className="space-y-1">
                                    {/* Indicador de streaming: puntos parpadeantes mientras la IA piensa */}
                                    {msg.isStreaming && !msg.content && (
                                        <div className="space-y-1.5">
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '2px 0' }}>
                                                <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: '#3B82F6', animation: 'qa-pulse 1.2s ease-in-out infinite' }} />
                                                <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: '#3B82F6', animation: 'qa-pulse 1.2s ease-in-out 0.2s infinite' }} />
                                                <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: '#3B82F6', animation: 'qa-pulse 1.2s ease-in-out 0.4s infinite' }} />
                                                <style>{`@keyframes qa-pulse { 0%,80%,100%{opacity:.2;transform:scale(.8)} 40%{opacity:1;transform:scale(1)} }`}</style>
                                            </div>
                                            {/* Etiqueta del motor mientras piensa: Pro razona antes de responder y así el usuario sabe que no se colgó */}
                                            {msg.motor === 'pro' ? (
                                                <p className="text-[11px] text-amber-300/80 uppercase tracking-[0.18em] font-black animate-pulse">Analizando en profundidad · Experto</p>
                                            ) : null}
                                        </div>
                                    )}
                                    {msg.content && (
                                        <div className="prose prose-invert prose-sm max-w-none text-white/90 leading-snug font-normal qa-prose-compact">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                                            {msg.isStreaming && (
                                                <span style={{ display: 'inline-block', width: 2, height: '1em', background: '#3B82F6', marginLeft: 2, verticalAlign: 'text-bottom', animation: 'qa-blink 0.8s step-end infinite' }} />
                                            )}
                                            <style>{`@keyframes qa-blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
                                            <style>{`
                                                .qa-prose-compact :where(table) { margin-top: 0.2em; margin-bottom: 0.25em; width: 100%; }
                                                .qa-prose-compact :where(th, td) { padding: 2px 6px; line-height: 1.35; }
                                                .qa-prose-compact :where(th) { padding-top: 3px; padding-bottom: 3px; }
                                                .qa-prose-compact :where(p) { margin-top: 0.2em; margin-bottom: 0.2em; line-height: 1.4; }
                                                .qa-prose-compact :where(ul, ol) { margin-top: 0.2em; margin-bottom: 0.2em; }
                                                .qa-prose-compact :where(li) { margin-top: 0.05em; margin-bottom: 0.05em; line-height: 1.4; }
                                                .qa-prose-compact :where(h1, h2, h3, h4, h5, h6) { margin-top: 0.3em; margin-bottom: 0.15em; line-height: 1.3; }
                                                .qa-prose-compact :where(blockquote) { margin-top: 0.2em; margin-bottom: 0.2em; }
                                                .qa-prose-compact > :first-child { margin-top: 0 !important; }
                                                .qa-prose-compact > :last-child { margin-bottom: 0 !important; }
                                            `}</style>
                                        </div>
                                    )}

                                    {showQuickQuestions && msg.quickQuestions?.length > 0 && (
                                        <div className="flex flex-wrap gap-1.5 mt-1">
                                            {msg.quickQuestions.slice(0, 3).map((q, i) => (
                                                <button
                                                    key={i}
                                                    onClick={(e) => {
                                                        if (handleQuery) {
                                                            e.preventDefault();
                                                            e.stopPropagation();
                                                            handleQuery(e, q);
                                                        }
                                                    }}
                                                    className="px-3 py-1 bg-white/5 border border-white/10 hover:border-[#3B82F6]/50 hover:bg-[#3B82F6]/10 rounded-lg text-[12px] text-white/60 hover:text-white transition-all text-left cursor-pointer"
                                                >
                                                    {q}
                                                </button>
                                            ))}
                                        </div>
                                    )}

                                    {hasStructuredResult && (
                                        <div className="mt-1 pt-1 border-t border-white/5">
                                            <DataVisualizer result={result} />
                                        </div>
                                    )}
                                </div>
                            )}


                            {/* Pestaña SQL: resaltado de sintaxis y copia en un clic. Solo ADMINISTRADOR. */}
                            {esAdministrador && activeTab === 'Analisis Tecnico (SQL)' && (
                                <SqlBlock sql={result?.sql?.text} />
                            )}

                            {/* Pestaña Trazabilidad (modo transparencia). Solo ADMINISTRADOR. */}
                            {esAdministrador && activeTab === 'Trazabilidad' && (
                                <div className="space-y-2">
                                    {result?.analysis?.summary && (
                                        <div className="prose prose-invert prose-sm max-w-none text-white/80 leading-normal">
                                            <ReactMarkdown>{result.analysis.summary}</ReactMarkdown>
                                        </div>
                                    )}
                                    {!!result?.analysis?.steps?.length && (
                                        <div>
                                            <p className="text-[12px] font-bold text-white/30 uppercase tracking-widest mb-1">
                                                Pasos ejecutados
                                            </p>
                                            <ul className="space-y-1">
                                                {result.analysis.steps.map((step, i) => (
                                                    <li
                                                        key={i}
                                                        className="text-[12px] text-white/60 font-mono bg-black/20 rounded-md px-2.5 py-1 border border-white/5"
                                                    >
                                                        {step}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ) : (
                        /* Modo barra fija: solo se muestran las preguntas rápidas, sin el contenedor del mensaje */
                        showQuickQuestions && msg.quickQuestions?.length > 0 && (
                            <div className="flex flex-wrap gap-2 pt-1 pb-2">
                                {msg.quickQuestions.slice(0, 3).map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={(e) => {
                                            if (handleQuery) {
                                                e.preventDefault();
                                                e.stopPropagation();
                                                handleQuery(e, q);
                                            }
                                        }}
                                        className="px-4 py-2 bg-white/5 border border-white/10 hover:border-emerald-500/50 hover:bg-emerald-500/10 rounded-xl text-[12px] text-white/60 hover:text-white transition-all text-left cursor-pointer"
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        )
                    )}

                    {/* Pie del mensaje */}
                    <div className="mt-0.5 flex items-center gap-4 px-1 opacity-20 hover:opacity-100 transition-opacity">
                        <span className="text-[12px] font-bold text-white/20 uppercase tracking-widest">VicMar Data AI</span>
                    </div>
                </div>
            </div>
        </div>
    );
};
