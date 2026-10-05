/**
 * @file Modo de voz a pantalla completa. Conversa con el usuario mediante la Web Speech
 * API del navegador en un ciclo ESCUCHANDO -> PENSANDO -> HABLANDO sin eco: envía la
 * pregunta al mismo motor del chat (handleQuery), lee en voz alta solo la respuesta a
 * la pregunta recién formulada y atiende órdenes rápidas («cambiar a…», «salir»). La
 * esfera central permite pulsar para hablar o interrumpir, y el micrófono se recupera
 * solo si se pierde la señal. Lo abre DashboardDesktop desde el chat y el panel.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, RefreshCw, Volume2, X } from 'lucide-react';

import { useLectura, construirRespuestaHablada } from '../hooks/useLectura';
import { interpretarComandoVoz } from '../utils/comandosVoz';
import { getDbCatalog } from '../constants/appConfig';

// Constructor de reconocimiento de voz del navegador (estándar o con prefijo webkit).
const ReconocimientoVoz =
    typeof window !== 'undefined'
        ? (window.SpeechRecognition || window.webkitSpeechRecognition)
        : null;

/**
 * Indica si el navegador permite el modo de voz (reconocimiento o síntesis de voz).
 * @type {boolean}
 */
export const modoVozDisponible = Boolean(typeof window !== 'undefined' && (ReconocimientoVoz || window.speechSynthesis));

const ESTADOS = {
    ESCUCHANDO: 'escuchando',
    PENSANDO: 'pensando',
    HABLANDO: 'hablando',
};

const TEXTO_ESTADO = {
    [ESTADOS.ESCUCHANDO]: 'Te escucho… habla con naturalidad',
    [ESTADOS.PENSANDO]: 'Analizando los datos…',
    [ESTADOS.HABLANDO]: 'Respondiendo en voz alta',
};

const COLOR_ESTADO = {
    [ESTADOS.ESCUCHANDO]: '#22D3EE',
    [ESTADOS.PENSANDO]: '#A78BFA',
    [ESTADOS.HABLANDO]: '#34D399',
};

/**
 * Muestra el asistente de voz a pantalla completa y gestiona el ciclo de escucha,
 * consulta y lectura de la respuesta.
 *
 * @param {object} props
 * @param {Function} props.onClose - Cierra el modo de voz.
 * @param {Function} props.handleQuery - Envía la consulta al chat; recibe `(null, texto)`.
 * @param {object[]} [props.chatHistory=[]] - Historial del chat, del que se toma la respuesta.
 * @param {string} [props.empresa=''] - Nombre de la empresa activa que se muestra.
 * @param {Function} [props.onCambiarEmpresa] - Cambia de empresa por orden de voz; recibe el código de la base.
 * @returns {JSX.Element} Interfaz del modo de voz.
 */
export function VoiceMode({ onClose, handleQuery, chatHistory = [], empresa = '', onCambiarEmpresa }) {
    const [estado, setEstado] = useState(ESTADOS.ESCUCHANDO);
    const [transcripcion, setTranscripcion] = useState('');
    const [ultimaPregunta, setUltimaPregunta] = useState('');
    const [error, setError] = useState(null);

    const { hablar, detener: detenerVoz, hablando } = useLectura();

    const reconocimientoRef = useRef(null);
    const estadoRef = useRef(estado);
    const idMensajeEsperadoRef = useRef(null);
    const preguntaLanzadaRef = useRef(null);
    const cerrandoRef = useRef(false);
    const cerrarRef = useRef(null);

    const handleQueryRef = useRef(handleQuery);
    const onCambiarEmpresaRef = useRef(onCambiarEmpresa);
    const hablarRef = useRef(hablar);
    const iniciarEscuchaRef = useRef(null);
    const ultimaSenalRef = useRef(Date.now());

    useEffect(() => { estadoRef.current = estado; }, [estado]);
    useEffect(() => { handleQueryRef.current = handleQuery; }, [handleQuery]);
    useEffect(() => { onCambiarEmpresaRef.current = onCambiarEmpresa; }, [onCambiarEmpresa]);
    useEffect(() => { hablarRef.current = hablar; }, [hablar]);

    // ── Detener escucha de forma segura ──────────────────────────────────────
    const detenerEscucha = useCallback(() => {
        if (reconocimientoRef.current) {
            try { reconocimientoRef.current.abort(); } catch (_) { /* ya detenido */ }
            reconocimientoRef.current = null;
        }
    }, []);

    // ── Enviar consulta al motor del chat ───────────────────────────────────
    const enviarConsulta = useCallback((texto) => {
        const textoLimpio = String(texto || '').trim();
        if (!textoLimpio || textoLimpio.length <= 2) return;

        // Verifica órdenes rápidas del sistema (p. ej. «cambiar a Montessori», «salir»).
        const empresasConocidas = Object.values(getDbCatalog() || {});
        const orden = interpretarComandoVoz(textoLimpio, empresasConocidas);

        if (orden) {
            setTranscripcion('');
            detenerEscucha();

            if (orden.tipo === 'salir') {
                cerrarRef.current?.();
                return;
            }

            if (orden.tipo === 'cambiar_empresa') {
                const nombre = orden.empresa.business_name || orden.empresa.database;
                setUltimaPregunta(`Cambiando a ${nombre}`);
                setEstado(ESTADOS.HABLANDO);
                onCambiarEmpresaRef.current?.(orden.empresa.database);
                hablarRef.current?.(`Listo, conectado a ${nombre}. ¿Qué deseas consultar?`);
                return;
            }

            if (orden.tipo === 'empresa_no_encontrada') {
                setEstado(ESTADOS.HABLANDO);
                hablarRef.current?.(`No encontré ninguna empresa llamada ${orden.mencion}. Puedes decir el código o el nombre comercial.`);
                return;
            }
        }

        // Marca la pregunta como activa y reinicia el mensaje esperado.
        preguntaLanzadaRef.current = { texto: textoLimpio, timestamp: Date.now() };
        idMensajeEsperadoRef.current = null;

        setUltimaPregunta(textoLimpio);
        setTranscripcion('');
        setEstado(ESTADOS.PENSANDO);
        detenerEscucha();

        // Envía la consulta al motor central.
        handleQueryRef.current?.(null, textoLimpio);
    }, [detenerEscucha]);

    // ── Iniciar escucha por voz ──────────────────────────────────────────────
    const iniciarEscucha = useCallback(() => {
        if (!ReconocimientoVoz || cerrandoRef.current) {
            if (!ReconocimientoVoz) {
                setError('Tu navegador no cuenta con Web Speech API activa. Puedes usar Chrome, Edge o Safari.');
            }
            return;
        }

        detenerEscucha();
        setError(null);

        const rec = new ReconocimientoVoz();
        // Idioma flexible: si el navegador está en español usa su configuración, o 'es-419' / 'es-EC'
        const navLang = typeof navigator !== 'undefined' ? navigator.language : 'es-419';
        rec.lang = navLang && navLang.toLowerCase().startsWith('es') ? navLang : 'es-419';
        rec.interimResults = true;
        rec.continuous = false;
        rec.maxAlternatives = 1;

        rec.onaudiostart = () => { ultimaSenalRef.current = Date.now(); };
        rec.onspeechstart = () => { ultimaSenalRef.current = Date.now(); };
        rec.onstart = () => { ultimaSenalRef.current = Date.now(); };

        rec.onresult = (evento) => {
            ultimaSenalRef.current = Date.now();
            let definitivo = '';
            let parcial = '';
            for (let i = evento.resultIndex; i < evento.results.length; i += 1) {
                const trozo = evento.results[i][0].transcript;
                if (evento.results[i].isFinal) definitivo += trozo;
                else parcial += trozo;
            }

            const textoMostrado = parcial || definitivo;
            setTranscripcion(textoMostrado);

            const textoFinal = definitivo.trim();
            if (textoFinal && textoFinal.length > 2) {
                enviarConsulta(textoFinal);
            }
        };

        rec.onerror = (evento) => {
            if (evento.error === 'not-allowed' || evento.error === 'service-not-allowed') {
                setError('Permiso de micrófono no otorgado. Haz clic en el candado del navegador para activarlo.');
                setEstado(ESTADOS.ESCUCHANDO);
                return;
            }
            if (evento.error === 'audio-capture') {
                setError('No se detectó señal de audio. Verifica tu micrófono o auriculares.');
                setEstado(ESTADOS.ESCUCHANDO);
                return;
            }
            if (evento.error === 'network') {
                setError('El reconocimiento por voz del navegador requiere conexión a internet.');
                setEstado(ESTADOS.ESCUCHANDO);
                return;
            }
            // 'no-speech' o 'aborted' son silencios normales, se recuperan en onend
        };

        rec.onend = () => {
            if (estadoRef.current === ESTADOS.ESCUCHANDO && !cerrandoRef.current) {
                setTimeout(() => {
                    if (estadoRef.current === ESTADOS.ESCUCHANDO && !cerrandoRef.current) {
                        iniciarEscuchaRef.current?.();
                    }
                }, 250);
            }
        };

        reconocimientoRef.current = rec;
        try {
            rec.start();
        } catch (_) {
            // start() lanza excepción si ya estaba en curso
        }
    }, [detenerEscucha, enviarConsulta]);

    useEffect(() => { iniciarEscuchaRef.current = iniciarEscucha; }, [iniciarEscucha]);

    // ── Vigilante de actividad del micrófono ────────────────────────────────
    useEffect(() => {
        cerrandoRef.current = false;
        iniciarEscucha();

        const vigilante = setInterval(() => {
            if (cerrandoRef.current) return;
            if (estadoRef.current !== ESTADOS.ESCUCHANDO) return;
            // Si pasan más de 12 segundos sin señal y no hay instancia activa
            if (Date.now() - ultimaSenalRef.current > 12000) {
                ultimaSenalRef.current = Date.now();
                iniciarEscuchaRef.current?.();
            }
        }, 5000);

        return () => {
            cerrandoRef.current = true;
            clearInterval(vigilante);
            detenerEscucha();
            try { window.speechSynthesis?.cancel(); } catch (_) { /* nada */ }
        };
    }, [detenerEscucha, iniciarEscucha]);

    // ── Detección precisa de la respuesta (NO lee mensajes viejos) ───────────
    useEffect(() => {
        if (estado !== ESTADOS.PENSANDO) return;

        // Encontrar el último mensaje de usuario en chatHistory
        let userIdx = -1;
        for (let i = chatHistory.length - 1; i >= 0; i--) {
            if (chatHistory[i]?.type === 'user') {
                userIdx = i;
                break;
            }
        }

        // Si todavía no se ha insertado el mensaje del usuario de esta consulta, esperar
        if (userIdx === -1) return;

        // Buscar el mensaje de IA que se encuentre ESTRICTAMENTE DESPUÉS del último usuario
        const mensajesPosteriores = chatHistory.slice(userIdx + 1);
        const ultimoIA = mensajesPosteriores.find(m => m?.type === 'ai' && !m?.isWelcome);

        if (!ultimoIA) return; // Aún no llega el turno de la IA para esta pregunta

        // Evitar reprocesar el mismo mensaje ya atendido
        if (idMensajeEsperadoRef.current === ultimoIA.id) return;

        // Si hubo un error en la consulta
        if (ultimoIA.isError) {
            idMensajeEsperadoRef.current = ultimoIA.id;
            setEstado(ESTADOS.HABLANDO);
            const errorLimpio = ultimoIA.content
                ? ultimoIA.content.replace(/[⚠️❌*]/g, '').trim()
                : 'No fue posible completar la consulta. Intenta reformularla.';
            hablar(`Disculpa, ${errorLimpio}`);
            return;
        }

        const filas = ultimoIA.result?.rows || [];
        const hayDatos = filas.length > 0;

        // Si todavía está en streaming y no hay datos disponibles aún, seguir esperando
        if (ultimoIA.isStreaming && !hayDatos) return;

        const tieneContenido = hayDatos || Boolean(ultimoIA.content) || Boolean(ultimoIA.result?.explanation);
        if (!tieneContenido && ultimoIA.isStreaming) return;

        if (tieneContenido) {
            idMensajeEsperadoRef.current = ultimoIA.id;
            setEstado(ESTADOS.HABLANDO);
            const respuestaAudio = construirRespuestaHablada(ultimoIA);
            hablar(respuestaAudio);
        }
    }, [chatHistory, estado, hablar]);

    // ── Timeout de seguridad en estado PENSANDO ──────────────────────────────
    useEffect(() => {
        if (estado !== ESTADOS.PENSANDO) return undefined;

        const timer = setTimeout(() => {
            if (estadoRef.current === ESTADOS.PENSANDO) {
                setEstado(ESTADOS.HABLANDO);
                hablar('La consulta está tomando más tiempo del habitual. El resultado se mostrará en el chat cuando esté listo.');
            }
        }, 22000);

        return () => clearTimeout(timer);
    }, [estado, hablar]);

    // ── Regreso automático a ESCUCHANDO cuando termina de hablar ─────────────
    useEffect(() => {
        if (estado === ESTADOS.HABLANDO && !hablando) {
            const id = setTimeout(() => {
                if (cerrandoRef.current) return;
                setEstado(ESTADOS.ESCUCHANDO);
                iniciarEscucha();
            }, 500);
            return () => clearTimeout(id);
        }
        return undefined;
    }, [estado, hablando, iniciarEscucha]);

    // ── Cerrar asistente ────────────────────────────────────────────────────
    const cerrar = useCallback(() => {
        cerrandoRef.current = true;
        detenerEscucha();
        detenerVoz();
        onClose?.();
    }, [detenerEscucha, detenerVoz, onClose]);

    useEffect(() => { cerrarRef.current = cerrar; }, [cerrar]);

    useEffect(() => {
        const alPulsar = (e) => { if (e.key === 'Escape') cerrar(); };
        window.addEventListener('keydown', alPulsar);
        return () => window.removeEventListener('keydown', alPulsar);
    }, [cerrar]);

    // ── Interacción con la esfera central (Touch/Click) ──────────────────────
    const manejarClickEsfera = useCallback(() => {
        if (estado === ESTADOS.HABLANDO) {
            // Interrumpir locución y volver a escuchar inmediatamente
            detenerVoz();
            setEstado(ESTADOS.ESCUCHANDO);
            iniciarEscucha();
            return;
        }

        if (estado === ESTADOS.ESCUCHANDO) {
            // Si hay algo transcrito en pantalla, forzar envío de inmediato
            if (transcripcion && transcripcion.trim().length > 2) {
                enviarConsulta(transcripcion.trim());
                return;
            }
            // Si no, reiniciar el ciclo del micrófono
            setError(null);
            iniciarEscucha();
            return;
        }

        if (estado === ESTADOS.PENSANDO) {
            // Cancelar espera y regresar a modo escucha
            setEstado(ESTADOS.ESCUCHANDO);
            iniciarEscucha();
        }
    }, [estado, transcripcion, detenerVoz, iniciarEscucha, enviarConsulta]);

    const color = COLOR_ESTADO[estado] || '#22D3EE';

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            role="dialog"
            aria-modal="true"
            aria-label="Asistente de voz AURA"
            className="fixed inset-0 z-[100] flex flex-col items-center justify-center select-none"
            style={{
                background: 'radial-gradient(ellipse at center, #0F172A 0%, #030712 85%)',
                backdropFilter: 'blur(10px)',
            }}
        >
            {/* Botón cerrar */}
            <button
                id="btn-voice-close"
                onClick={cerrar}
                aria-label="Cerrar modo de voz"
                className="absolute right-6 top-6 rounded-full border border-white/10 p-3 text-white/50 transition-colors hover:border-white/30 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
            >
                <X size={20} aria-hidden="true" />
            </button>

            {/* Empresa activa */}
            {empresa && (
                <div className="absolute left-6 top-6 flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-semibold tracking-wider text-white/50 uppercase">
                    <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                    {empresa}
                </div>
            )}

            {/* Esfera reactiva e interactiva */}
            <div className="relative flex h-72 w-72 items-center justify-center cursor-pointer" onClick={manejarClickEsfera}>
                {[0, 1, 2].map((i) => (
                    <motion.div
                        key={i}
                        className="absolute rounded-full pointer-events-none"
                        style={{ border: `1px solid ${color}`, opacity: 0.25 }}
                        animate={{
                            width: [140 + i * 45, 195 + i * 45, 140 + i * 45],
                            height: [140 + i * 45, 195 + i * 45, 140 + i * 45],
                            opacity: estado === ESTADOS.ESCUCHANDO ? [0.1, 0.35, 0.1] : [0.05, 0.2, 0.05],
                        }}
                        transition={{
                            duration: estado === ESTADOS.PENSANDO ? 1.2 : 2.2,
                            repeat: Infinity,
                            delay: i * 0.3,
                            ease: 'easeInOut',
                        }}
                    />
                ))}

                <motion.button
                    id="btn-voice-sphere"
                    type="button"
                    aria-label={`Esfera de voz: ${estado}`}
                    className="relative z-10 flex h-32 w-32 items-center justify-center rounded-full transition-all focus:outline-none focus-visible:ring-4 focus-visible:ring-cyan-400"
                    style={{
                        background: `radial-gradient(circle at 35% 35%, ${color}66, ${color}15)`,
                        border: `2px solid ${color}88`,
                        boxShadow: `0 0 70px ${color}55`,
                    }}
                    animate={{
                        scale: estado === ESTADOS.ESCUCHANDO ? [1, 1.08, 1] : estado === ESTADOS.HABLANDO ? [1, 1.05, 1] : [1, 1.02, 1],
                    }}
                    transition={{
                        duration: estado === ESTADOS.PENSANDO ? 0.9 : 1.8,
                        repeat: Infinity,
                        ease: 'easeInOut',
                    }}
                >
                    {estado === ESTADOS.HABLANDO ? (
                        <Volume2 size={38} style={{ color }} aria-hidden="true" className="animate-pulse" />
                    ) : error ? (
                        <MicOff size={36} className="text-rose-400" aria-hidden="true" />
                    ) : (
                        <Mic size={38} style={{ color }} aria-hidden="true" />
                    )}
                </motion.button>
            </div>

            {/* Texto de ayuda bajo la esfera */}
            <p className="mt-2 text-[12px] font-medium text-white/30 tracking-wide">
                {estado === ESTADOS.HABLANDO
                    ? 'Toca la esfera para interrumpir'
                    : estado === ESTADOS.ESCUCHANDO && transcripcion
                        ? 'Toca la esfera para enviar ahora'
                        : 'Toca la esfera para controlar'}
            </p>

            {/* Contenedor de estados y transcripción en vivo */}
            <div aria-live="polite" className="mt-8 flex min-h-[130px] max-w-2xl flex-col items-center px-8 text-center">
                <span className="text-[13px] font-bold uppercase tracking-[0.25em]" style={{ color }}>
                    {error ? 'Aviso del sistema' : TEXTO_ESTADO[estado]}
                </span>

                {error ? (
                    <div className="mt-4 flex flex-col items-center gap-3">
                        <p className="text-[15px] text-rose-300 max-w-lg leading-relaxed">{error}</p>
                        <button
                            id="btn-voice-retry"
                            onClick={(e) => {
                                e.stopPropagation();
                                setError(null);
                                iniciarEscucha();
                            }}
                            className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2 text-xs font-semibold text-white hover:bg-white/20 transition-all border border-white/15"
                        >
                            <RefreshCw size={13} aria-hidden="true" />
                            Reintentar activar micrófono
                        </button>
                    </div>
                ) : (
                    <AnimatePresence mode="wait">
                        {estado !== ESTADOS.HABLANDO && (
                            <motion.p
                                key={transcripcion || ultimaPregunta || estado}
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="mt-4 text-[18px] sm:text-[20px] font-medium leading-relaxed text-white/90 max-w-xl"
                            >
                                {transcripcion
                                    || (estado === ESTADOS.ESCUCHANDO ? '«¿Cuánto vendimos este mes?» o «Compara gastos con el año anterior»' : null)
                                    || (estado === ESTADOS.PENSANDO ? `«${ultimaPregunta}»` : null)}
                            </motion.p>
                        )}
                    </AnimatePresence>
                )}
            </div>

            {/* Pie de página con consejos */}
            <div className="absolute bottom-8 flex flex-col items-center gap-1 text-[12px] text-white/30 text-center px-4">
                <p>Las respuestas y gráficos detallados se guardan automáticamente en tu historial de chat</p>
                <p className="text-white/20 text-[11px]">Pulsa Esc o la X para salir al panel principal</p>
            </div>
        </motion.div>
    );
}
