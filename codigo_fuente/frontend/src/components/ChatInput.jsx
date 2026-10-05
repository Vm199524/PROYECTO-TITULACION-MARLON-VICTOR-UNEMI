/**
 * @file Campo de consulta del chat. Captura la pregunta en lenguaje natural y la envía
 * con handleQuery (que llama a /api/query), muestra la autocorrección sugerida y reúne
 * las herramientas de la consulta: dictado por voz, imágenes adjuntas para el modelo
 * de visión, selector de motor de IA (según los modelos permitidos del usuario) y el
 * botón de sugerencias. Lo usa ChatArea.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React, { useCallback, useLayoutEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowUp, Brain, ChevronDown, Cpu, Eye, Gauge, Layers, Lightbulb, Loader2, Mic, MicOff, Paperclip, Rocket, Sparkles, Square, TrendingUp, X, Zap } from 'lucide-react';

import { useDictado } from '../hooks/useDictado';

const FIXED_PLACEHOLDER = '¿Qué analizamos hoy?';

// Máximo de imágenes por consulta al modelo de visión: más de esto degrada
// mucho la latencia de DeepSeek sin aportar demasiado.
const MAX_IMAGENES = 4;

// Selector manual de motor de IA. Flash responde SIEMPRE por defecto; los
// demás motores solo entran si el usuario los elige a propósito para una
// consulta puntual. Es un catálogo aparte del sistema de roles porque cada
// usuario puede tener sus propios modelos permitidos, ajustables desde
// Gestión de Usuarios.
const MOTORES_IA = {
    flash: { label: 'Flash', icon: Zap, desc: 'Rápido — consultas directas' },
    pro: { label: 'Pro', icon: TrendingUp, desc: 'Comparativas y finanzas avanzadas' },
    // Cascada gratuita (backend, core/nl2sql_engine.py): «Flash» ya prueba
    // Gemini→Groq→NVIDIA→(DeepSeek si hay llave) en cascada automática. Estos
    // motores sirven para PROBAR un proveedor o modelo puntual; si ese falla,
    // el backend recurre por sí solo al resto de los gratuitos.
    gemini: { label: 'Gemini 3.8 Flash', icon: Sparkles, desc: 'Google · 1M tokens de contexto · principal de la cascada' },
    groq: { label: 'GPT-OSS 120B', icon: Gauge, desc: 'Groq · velocidad extrema · respaldo #2' },
    nvidia_deepseek_pro: { label: 'DeepSeek V4 Pro', icon: Brain, desc: 'NVIDIA NIM · razonamiento complejo, contexto hasta 1M' },
    nvidia_deepseek_flash: { label: 'DeepSeek V4 Flash', icon: Rocket, desc: 'NVIDIA NIM · MoE 284B, chat y agentes ágiles' },
    nvidia_kimi: { label: 'Kimi K3', icon: Layers, desc: 'NVIDIA NIM · Moonshot AI · ~2.8T, codificación y agentes de largo horizonte' },
    nvidia_nemotron: { label: 'Nemotron 3.5 Lightning', icon: Cpu, desc: 'NVIDIA NIM · MoE 30B extremadamente rápido para agentes' },
    nvidia_muse: { label: 'Muse Glimmer 30B', icon: Eye, desc: 'NVIDIA NIM · Meta · razonamiento multimodal + tool calling' },
};

/**
 * Muestra el formulario de consulta con sus herramientas.
 *
 * @param {object} props
 * @param {string} props.prompt - Texto actual de la consulta.
 * @param {Function} props.setPrompt - Actualiza el texto (también recibe lo dictado).
 * @param {object} props.userAuth - Usuario autenticado; `modelos_permitidos` define los motores del selector.
 * @param {string} [props.motorIA=''] - Motor elegido; si no está permitido se usa Flash.
 * @param {Function} props.setMotorIA - Cambia el motor de IA.
 * @param {Function} props.handleQuery - Envía la consulta (submit del formulario).
 * @param {boolean} props.loading - Si hay una consulta en curso.
 * @param {Function} props.cancelQuery - Detiene la consulta en curso.
 * @param {string} props.correctionHint - Corrección sugerida que se muestra sobre el campo.
 * @param {object} props.textareaRef - Referencia al textarea.
 * @param {Array} [props.attachedImages=[]] - Imágenes adjuntas como data URL.
 * @param {Function} props.setAttachedImages - Actualiza las imágenes adjuntas.
 * @param {boolean} [props.hasSugerencias=false] - Si hay sugerencias que mostrar.
 * @param {boolean} [props.mostrarSugerencias=false] - Si la ficha de sugerencias está abierta.
 * @param {Function} props.onToggleSugerencias - Abre o cierra la ficha de sugerencias.
 * @returns {JSX.Element} Campo de consulta.
 */
export const ChatInput = ({
    prompt, setPrompt, userAuth, motorIA = '', setMotorIA, handleQuery, loading,
    cancelQuery,
    correctionHint, correct, setCorrectionHint,
    textareaRef, isSidebarOpen,
    attachedImages = [], setAttachedImages,
    hasSugerencias = false, mostrarSugerencias = false, onToggleSugerencias,
}) => {
    // Solo se muestra el selector si el usuario tiene MÁS de un motor
    // disponible: con uno solo (el caso normal de RRHH o Logística, solo
    // Flash) un selector sin opciones reales no aporta nada.
    const [selectorAbierto, setSelectorAbierto] = useState(false);
    // El motor Pro está desactivado y no aparece en el selector; Flash queda
    // por defecto. Para reactivarlo, basta con quitar `&& m !== 'pro'`.
    const modelosDisponibles = (userAuth?.modelos_permitidos || ['flash']).filter((m) => MOTORES_IA[m] && m !== 'pro');
    const mostrarSelectorMotor = typeof setMotorIA === 'function' && modelosDisponibles.length > 1;
    const motorActivo = MOTORES_IA[motorIA] && modelosDisponibles.includes(motorIA) ? motorIA : 'flash';
    const IconoMotorActivo = MOTORES_IA[motorActivo].icon;

    // ── Dictado por voz ──────────────────────────────────────────────────
    // Lo dictado se AÑADE al texto existente en vez de reemplazarlo: así el
    // usuario puede escribir una parte, dictar otra, o corregir a mano lo que
    // el reconocimiento entendió mal. No se envía solo: el usuario revisa y
    // pulsa enviar, porque una transcripción errónea que dispara una consulta
    // sin confirmación es peor que escribirla.
    const recibirTextoDictado = useCallback((texto) => {
        setPrompt((actual) => {
            const previo = String(actual || '').trim();
            return previo ? `${previo} ${texto}` : texto;
        });
        textareaRef?.current?.focus();
    }, [setPrompt, textareaRef]);

    const { escuchando, textoParcial, error: errorDictado, iniciar: alternarDictado, disponible: dictadoDisponible } =
        useDictado({ onTexto: recibirTextoDictado });

    // ── Adjuntar imágenes (modelo de visión) ─────────────────────────────
    // Cada imagen se guarda como data URL completa (FileReader.readAsDataURL)
    // porque así el backend la recibe lista para mandarla directo a DeepSeek
    // sin que el frontend tenga que separar el mime type del contenido.
    const fileInputRef = useRef(null);
    const puedeAdjuntar = typeof setAttachedImages === 'function';

    // El texto del textarea está centrado (textAlign: 'center'), pero el
    // grupo de íconos vive en un <div> hermano a la derecha, así que el
    // centro real de la caja del textarea no coincide con el centro visual
    // buscado: el punto medio entre el borde izquierdo de TODA la tarjeta y
    // el borde izquierdo del botón de Sugerencias. En vez de asumir paddings
    // y gaps fijos del formulario (que se descuadran cada vez que se agrega
    // un ícono), se mide con getBoundingClientRect la posición REAL
    // del borde de la tarjeta y del borde del botón de Sugerencias (o del
    // grupo completo de íconos si ese botón no existe) y se calcula el
    // paddingLeft exacto que el textarea necesita para que su punto medio
    // visual caiga justo en el punto medio entre esos dos bordes.
    const formRef = useRef(null);
    const iconsRef = useRef(null);
    const sugerenciasBtnRef = useRef(null);
    const [centroPaddingLeft, setCentroPaddingLeft] = useState(0);

    useLayoutEffect(() => {
        const medir = () => {
            const form = formRef.current;
            const textarea = textareaRef?.current;
            const ancla = (hasSugerencias && sugerenciasBtnRef.current) || iconsRef.current;
            if (!form || !textarea || !ancla) return;
            const formRect = form.getBoundingClientRect();
            const anclaRect = ancla.getBoundingClientRect();
            const textRect = textarea.getBoundingClientRect();
            const centroDeseado = (formRect.left + anclaRect.left) / 2;
            const paddingNecesario = Math.max(0, Math.round((2 * centroDeseado) - textRect.left - textRect.right));
            setCentroPaddingLeft(paddingNecesario);
        };

        medir();

        const form = formRef.current;
        if (!form || typeof ResizeObserver === 'undefined') return undefined;
        const observer = new ResizeObserver(medir);
        observer.observe(form);
        if (iconsRef.current) observer.observe(iconsRef.current);
        window.addEventListener('resize', medir);
        return () => {
            observer.disconnect();
            window.removeEventListener('resize', medir);
        };
    }, [hasSugerencias, mostrarSelectorMotor, puedeAdjuntar, dictadoDisponible, loading, isSidebarOpen, textareaRef]);

    // ── Exclusión mutua entre las herramientas del campo ─────────────────
    // Solo UNA herramienta puede estar activa a la vez: sugerencias, dictado,
    // adjuntar y el selector de motor.
    //
    // Se resuelve cerrando lo demás al activar una (no deshabilitando los
    // botones): un botón que no responde se siente roto, mientras que el
    // relevo automático es lo que hace cualquier barra de herramientas.
    //
    // Nota sobre «adjuntar»: abre el diálogo NATIVO del sistema operativo,
    // que no se puede cerrar por código y bloquea la página mientras está
    // abierto. Por eso solo se controla lo que depende de la aplicación:
    // antes de abrirlo, se cierran las sugerencias y se corta el dictado.
    const cerrarSugerenciasSiAbierto = useCallback(() => {
        if (mostrarSugerencias) onToggleSugerencias?.();
    }, [mostrarSugerencias, onToggleSugerencias]);

    const detenerDictadoSiActivo = useCallback(() => {
        if (escuchando) alternarDictado();
    }, [escuchando, alternarDictado]);

    const alternarSugerencias = useCallback(() => {
        detenerDictadoSiActivo();
        setSelectorAbierto(false);
        onToggleSugerencias?.();
    }, [detenerDictadoSiActivo, onToggleSugerencias]);

    // Al ARRANCAR el dictado se cierra lo demás. Si ya estaba escuchando, este
    // clic solo lo detiene: no tiene sentido cerrar nada en ese caso.
    const alternarDictadoExclusivo = useCallback(() => {
        if (!escuchando) {
            cerrarSugerenciasSiAbierto();
            setSelectorAbierto(false);
        }
        alternarDictado();
    }, [escuchando, cerrarSugerenciasSiAbierto, alternarDictado]);

    const abrirSelectorImagenes = useCallback(() => {
        cerrarSugerenciasSiAbierto();
        detenerDictadoSiActivo();
        setSelectorAbierto(false);
        fileInputRef.current?.click();
    }, [cerrarSugerenciasSiAbierto, detenerDictadoSiActivo]);

    const alternarSelectorMotor = useCallback(() => {
        setSelectorAbierto((abierto) => {
            if (!abierto) {
                cerrarSugerenciasSiAbierto();
                detenerDictadoSiActivo();
            }
            return !abierto;
        });
    }, [cerrarSugerenciasSiAbierto, detenerDictadoSiActivo]);

    const manejarSeleccionImagenes = useCallback((e) => {
        const archivos = Array.from(e.target.files || []);
        e.target.value = ''; // permite volver a elegir el mismo archivo después de quitarlo

        if (!archivos.length || !puedeAdjuntar) return;

        const espacioDisponible = MAX_IMAGENES - attachedImages.length;
        const seleccionados = archivos.filter((f) => f.type.startsWith('image/')).slice(0, Math.max(0, espacioDisponible));

        seleccionados.forEach((archivo) => {
            const reader = new FileReader();
            reader.onload = () => {
                setAttachedImages((prev) => {
                    if (prev.length >= MAX_IMAGENES) return prev;
                    return [...prev, { id: `img-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, dataUrl: reader.result, name: archivo.name }];
                });
            };
            reader.readAsDataURL(archivo);
        });
    }, [attachedImages.length, puedeAdjuntar, setAttachedImages]);

    const quitarImagen = useCallback((id) => {
        setAttachedImages?.((prev) => prev.filter((img) => img.id !== id));
    }, [setAttachedImages]);

    return (
        <div
            className="chat-input-area flex justify-center py-1 sm:py-2"
            style={{ width: '100%' }}
        >
            <div className="w-full max-w-[1000px] px-4 sm:px-6">
                {/* Estado del dictado: se muestra lo que se va entendiendo en
                    tiempo real para que el usuario no hable «al vacío» sin saber
                    si el micrófono lo está captando. */}
                <AnimatePresence>
                    {(escuchando || errorDictado) && (
                        <motion.div
                            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                            role="status"
                            aria-live="polite"
                            style={{ marginBottom: 12, textAlign: 'center', width: '100%' }}
                        >
                            {errorDictado ? (
                                <span style={{ fontSize: 13, color: '#f87171' }}>{errorDictado}</span>
                            ) : (
                                <span style={{ fontSize: 13, color: 'var(--accent)' }}>
                                    <span style={{
                                        display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                                        background: '#ef4444', marginRight: 8,
                                        animation: 'qa-pulse 1.2s ease-in-out infinite',
                                    }} />
                                    {textoParcial || 'Escuchando… habla ahora'}
                                </span>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Miniaturas de imágenes adjuntas (modelo de visión) */}
                {puedeAdjuntar && attachedImages.length > 0 && (
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12, justifyContent: 'center' }}>
                        {attachedImages.map((img) => (
                            <div key={img.id} style={{ position: 'relative', width: 56, height: 56, borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border)' }}>
                                <img src={img.dataUrl} alt={img.name || 'Imagen adjunta'} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                <button
                                    type="button"
                                    onClick={() => quitarImagen(img.id)}
                                    aria-label={`Quitar imagen ${img.name || ''}`}
                                    style={{
                                        position: 'absolute', top: 2, right: 2, width: 18, height: 18, borderRadius: '50%',
                                        background: 'rgba(0,0,0,0.65)', border: 'none', color: 'white',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', padding: 0,
                                    }}
                                >
                                    <X size={11} aria-hidden="true" />
                                </button>
                            </div>
                        ))}
                        {attachedImages.length > 0 && (
                            <span style={{ fontSize: 11, color: 'var(--text-faint)', alignSelf: 'center', marginLeft: 4 }}>
                                {attachedImages.length}/{MAX_IMAGENES} · VicMar Data AI analizará estas imágenes con IA Vision
                            </span>
                        )}
                    </div>
                )}

                {/* Corrección sugerida */}
                <AnimatePresence>
                    {correctionHint && (
                        <motion.div
                            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                            style={{
                                fontSize: 10, fontWeight: 600, color: 'var(--accent)',
                                textTransform: 'uppercase', letterSpacing: '0.1em',
                                marginBottom: 12, textAlign: 'center', width: '100%'
                            }}
                        >
                            ✓ {correctionHint}
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Contenedor del campo de consulta */}
                <form
                    ref={formRef}
                    onSubmit={handleQuery}
                    className="flex items-center gap-3 w-full"
                    style={{
                        background: 'var(--bg-main)',
                        border: '1px solid var(--border)',
                        borderRadius: 24,
                        padding: '8px 12px',
                        transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                        boxShadow: '0 8px 30px rgba(0,0,0,0.25)',
                        position: 'relative',
                        // Con el selector abierto, el `transform` del onFocusCapture crea un
                        // contexto de apilamiento que encierra los zIndex 40/41 del popover
                        // dentro del nivel del form. Elevando el form completo (que ya es
                        // position: relative) por encima del chat, backdrop y popover quedan
                        // SIEMPRE por delante de las tablas de respuesta.
                        zIndex: selectorAbierto ? 9999 : undefined,
                    }}
                    onFocusCapture={e => {
                        e.currentTarget.style.borderColor = 'var(--accent)';
                        e.currentTarget.style.boxShadow = '0 0 0 3px rgba(59,130,246,0.2), 0 12px 40px rgba(0,0,0,0.4)';
                        e.currentTarget.style.transform = 'translateY(-2px)';
                    }}
                    onBlurCapture={e => {
                        e.currentTarget.style.borderColor = 'var(--border)';
                        e.currentTarget.style.boxShadow = '0 8px 30px rgba(0,0,0,0.25)';
                        e.currentTarget.style.transform = 'translateY(0)';
                    }}
                >
                    <textarea
                        ref={textareaRef}
                        value={prompt}
                        onChange={(e) => {
                            const val = e.target.value;
                            if (val.endsWith(' ') || val.endsWith('?')) {
                                const { text, wasCorrected } = correct(val);
                                setPrompt(text);
                                if (wasCorrected) {
                                    setCorrectionHint('Sintonía de ADN activa');
                                    setTimeout(() => setCorrectionHint(null), 2500);
                                }
                            } else {
                                setPrompt(val);
                            }
                        }}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                e.currentTarget.form.requestSubmit();
                            }
                        }}
                        disabled={loading}
                        spellCheck="true"
                        lang="es"
                        placeholder={FIXED_PLACEHOLDER}
                        aria-label="Escribe tu consulta de negocio en lenguaje natural"
                        rows="1"
                        style={{
                            flex: 1,
                            minWidth: 0,
                            background: 'transparent',
                            border: 'none',
                            outline: 'none',
                            color: 'var(--text-primary)',
                            fontSize: 16,
                            fontFamily: 'var(--font-main)',
                            resize: 'none',
                            lineHeight: 1.6,
                            // Altura FIJA de una sola línea (16px * 1.6). El textarea
                            // NUNCA se agranda solo: el texto largo scrollea DENTRO
                            // de la caja (overflowY: auto) y el comportamiento es
                            // idéntico para todos los motores de IA.
                            height: 26,
                            overflowY: 'auto',
                            opacity: loading ? 0.3 : 1,
                            // `textAlign: center` centra el texto dentro de la caja del
                            // textarea; `centroPaddingLeft` (medido con getBoundingClientRect,
                            // ver el efecto de arriba) corrige esa caja para que el punto medio
                            // visual quede exactamente entre el borde izquierdo de toda la
                            // tarjeta y el borde izquierdo del botón de Sugerencias.
                            textAlign: 'center',
                            paddingLeft: centroPaddingLeft,
                        }}
                        className="chat-scrollbar"
                    />

                    {/* Botones de acción o estado de la consulta */}
                    <div ref={iconsRef} className="flex items-center gap-3" style={{ minWidth: 0, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                        {loading && (
                            <motion.span
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 700, whiteSpace: 'nowrap', textTransform: 'uppercase', letterSpacing: '0.05em' }}
                            >
                                PROCESANDO DATOS...
                            </motion.span>
                        )}

                        {hasSugerencias && (
                            // El botón de sugerencias vive en el mismo grupo de
                            // íconos que adjuntar, dictar y enviar, dentro de esta
                            // tarjeta, para que se lea como parte del chat y no
                            // como un elemento aparte.
                            <button
                                ref={sugerenciasBtnRef}
                                type="button"
                                onClick={alternarSugerencias}
                                disabled={loading}
                                aria-expanded={mostrarSugerencias}
                                aria-label="Ver preguntas sugeridas para esta empresa"
                                title="Sugerencias para esta empresa"
                                className="chat-icon-btn"
                                style={{
                                    width: 42, height: 42, borderRadius: '50%',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    background: mostrarSugerencias ? 'rgba(34,211,238,0.15)' : 'transparent',
                                    border: `1px solid ${mostrarSugerencias ? 'rgba(34,211,238,0.45)' : 'rgba(255,255,255,0.08)'}`,
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    opacity: loading ? 0.3 : 1,
                                    transition: 'all 0.2s',
                                    flexShrink: 0,
                                }}
                            >
                                <Lightbulb size={17} style={{ color: mostrarSugerencias ? '#22d3ee' : 'var(--text-faint)' }} aria-hidden="true" />
                            </button>
                        )}

                        {puedeAdjuntar && (
                            <>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*"
                                    multiple
                                    onChange={manejarSeleccionImagenes}
                                    style={{ display: 'none' }}
                                    aria-hidden="true"
                                    tabIndex={-1}
                                />
                                <button
                                    type="button"
                                    onClick={abrirSelectorImagenes}
                                    disabled={loading || attachedImages.length >= MAX_IMAGENES}
                                    aria-label={
                                        attachedImages.length >= MAX_IMAGENES
                                            ? `Máximo ${MAX_IMAGENES} imágenes por consulta`
                                            : 'Adjuntar imagen para análisis con IA Vision'
                                    }
                                    title={
                                        attachedImages.length >= MAX_IMAGENES
                                            ? `Máximo ${MAX_IMAGENES} imágenes`
                                            : 'Adjuntar imagen (IA Vision)'
                                    }
                                    className="chat-icon-btn"
                                    style={{
                                        width: 42, height: 42, borderRadius: '50%',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        background: attachedImages.length > 0 ? 'rgba(59,130,246,0.15)' : 'transparent',
                                        border: `1px solid ${attachedImages.length > 0 ? 'rgba(59,130,246,0.45)' : 'rgba(255,255,255,0.08)'}`,
                                        cursor: (loading || attachedImages.length >= MAX_IMAGENES) ? 'not-allowed' : 'pointer',
                                        opacity: (loading || attachedImages.length >= MAX_IMAGENES) ? 0.3 : 1,
                                        transition: 'all 0.2s',
                                        flexShrink: 0,
                                    }}
                                >
                                    <Paperclip size={17} style={{ color: attachedImages.length > 0 ? 'var(--accent)' : 'var(--text-faint)' }} aria-hidden="true" />
                                </button>
                            </>
                        )}

                        {dictadoDisponible && (
                            <button
                                type="button"
                                onClick={alternarDictadoExclusivo}
                                disabled={loading}
                                aria-label={escuchando ? 'Detener dictado' : 'Dictar la pregunta por voz'}
                                aria-pressed={escuchando}
                                title={escuchando ? 'Detener dictado' : 'Dictar por voz'}
                                className="chat-icon-btn"
                                style={{
                                    width: 42, height: 42, borderRadius: '50%',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    background: escuchando ? 'rgba(239,68,68,0.15)' : 'transparent',
                                    border: `1px solid ${escuchando ? 'rgba(239,68,68,0.45)' : 'rgba(255,255,255,0.08)'}`,
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    opacity: loading ? 0.3 : 1,
                                    transition: 'all 0.2s',
                                    flexShrink: 0,
                                }}
                            >
                                {escuchando
                                    ? <MicOff size={17} className="text-rose-400" aria-hidden="true" />
                                    : <Mic size={17} style={{ color: 'var(--text-faint)' }} aria-hidden="true" />
                                }
                            </button>
                        )}

                        {mostrarSelectorMotor && (
                            <div style={{ position: 'relative', flexShrink: 0 }}>
                                <button
                                    type="button"
                                    onClick={alternarSelectorMotor}
                                    disabled={loading}
                                    aria-label={`Motor de IA: ${MOTORES_IA[motorActivo].label}`}
                                    aria-expanded={selectorAbierto}
                                    title="Elegir motor de IA para esta consulta"
                                    className="chat-icon-btn"
                                    style={{
                                        width: 120, height: 42, padding: '0 10px', borderRadius: 21,
                                        display: 'flex', alignItems: 'center', gap: 5,
                                        overflow: 'hidden', flexShrink: 0,
                                        background: motorActivo !== 'flash' ? 'rgba(59,130,246,0.15)' : 'transparent',
                                        border: `1px solid ${motorActivo !== 'flash' ? 'rgba(59,130,246,0.45)' : 'rgba(255,255,255,0.08)'}`,
                                        cursor: loading ? 'not-allowed' : 'pointer',
                                        opacity: loading ? 0.3 : 1,
                                        transition: 'all 0.2s',
                                    }}
                                >
                                    <IconoMotorActivo size={15} style={{ color: motorActivo !== 'flash' ? 'var(--accent)' : 'var(--text-faint)' }} aria-hidden="true" />
                                    <span style={{ flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: 12, fontWeight: 600, color: motorActivo !== 'flash' ? 'var(--accent)' : 'var(--text-faint)' }}>
                                        {MOTORES_IA[motorActivo].label}
                                    </span>
                                    <ChevronDown size={13} style={{ color: 'var(--text-faint)', flexShrink: 0, marginLeft: 'auto' }} aria-hidden="true" />
                                </button>

                                <AnimatePresence>
                                    {selectorAbierto && (
                                        <>
                                            {/* Capa invisible para cerrar el selector al hacer clic afuera. */}
                                            <div
                                                onClick={() => setSelectorAbierto(false)}
                                                style={{ position: 'fixed', inset: 0, zIndex: 40 }}
                                            />
                                            <motion.div
                                                initial={{ opacity: 0, y: 6 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                exit={{ opacity: 0, y: 6 }}
                                                transition={{ duration: 0.15 }}
                                                className="chat-scrollbar"
                                                style={{
                                                    position: 'absolute', bottom: 'calc(100% + 8px)', right: 0,
                                                    minWidth: 260, maxWidth: 300, zIndex: 41,
                                                    maxHeight: 360, overflowY: 'auto',
                                                    background: 'var(--bg-elevated, #171b22)',
                                                    border: '1px solid rgba(255,255,255,0.1)',
                                                    borderRadius: 14, padding: 6,
                                                    boxShadow: '0 12px 32px rgba(0,0,0,0.4)',
                                                }}
                                            >
                                                {modelosDisponibles.map((clave) => {
                                                    const info = MOTORES_IA[clave];
                                                    const Icono = info.icon;
                                                    const activo = clave === motorActivo;
                                                    return (
                                                        <button
                                                            key={clave}
                                                            type="button"
                                                            onClick={() => { setMotorIA(clave); setSelectorAbierto(false); }}
                                                            style={{
                                                                width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                                                                padding: '9px 10px', borderRadius: 9, border: 'none',
                                                                background: activo ? 'rgba(59,130,246,0.15)' : 'transparent',
                                                                cursor: 'pointer', textAlign: 'left',
                                                            }}
                                                        >
                                                            <Icono size={16} style={{ color: activo ? 'var(--accent)' : 'var(--text-faint)', flexShrink: 0 }} aria-hidden="true" />
                                                            <span style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
                                                                <span style={{ fontSize: 13, fontWeight: 700, color: activo ? 'var(--accent)' : 'var(--text-primary, #fff)' }}>
                                                                    {info.label}
                                                                </span>
                                                                <span style={{ fontSize: 11, color: 'var(--text-faint)' }}>{info.desc}</span>
                                                            </span>
                                                        </button>
                                                    );
                                                })}
                                            </motion.div>
                                        </>
                                    )}
                                </AnimatePresence>
                            </div>
                        )}

                        {loading ? (
                            <button
                                type="button"
                                onClick={cancelQuery}
                                className="send-btn"
                                aria-label="Cancelar consulta en curso"
                                title="Cancelar consulta"
                                style={{
                                    width: 42, height: 42,
                                    opacity: 1,
                                    transition: 'all 0.2s',
                                    border: '1px solid rgba(239,68,68,0.45)',
                                    background: 'rgba(239,68,68,0.18)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    cursor: 'pointer',
                                }}
                            >
                                <Square size={16} color="#f87171" fill="#f87171" aria-hidden="true" />
                            </button>
                        ) : (
                            <button
                                type="submit"
                                disabled={!prompt.trim() && attachedImages.length === 0}
                                className="send-btn"
                                aria-label="Enviar consulta"
                                style={{
                                    width: 42, height: 42,
                                    opacity: (!prompt.trim() && attachedImages.length === 0) ? 0.2 : 1,
                                    transition: 'all 0.2s',
                                    border: '1px solid rgba(255,255,255,0.05)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center'
                                }}
                            >
                                <ArrowUp size={18} color="white" aria-hidden="true" />
                            </button>
                        )}
                    </div>
                </form>

                {/* Pie con el nombre y la versión del producto */}
                <p style={{ fontSize: 10, color: 'var(--text-faint)', textAlign: 'center', marginTop: 14, letterSpacing: '0.12em', fontWeight: 700, textTransform: 'uppercase', opacity: 0.6 }}>
                    Inteligencia de Negocios · VicMar Data AI v4.5
                </p>
            </div>
        </div>
    );
};
