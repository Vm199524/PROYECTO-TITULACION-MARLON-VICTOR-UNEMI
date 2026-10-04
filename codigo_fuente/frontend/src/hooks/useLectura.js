/**
 * hooks/useLectura.js — Lectura en voz alta de las respuestas.
 *
 * DOS MOTORES, UNO DE RESPALDO DEL OTRO:
 *
 * 1. FAL AI (ElevenLabs Multilingual v2) — voz natural y consistente. El
 *    texto SÍ sale de la máquina hacia el backend, que lo reenvía a FAL. Esto
 *    puede incluir datos del negocio (sueldos, totales de ventas, nombres de
 *    proveedores) — el usuario aceptó explícitamente esta contrapartida el
 *    30/08/2026, a cambio de una voz mucho mejor que la de Windows. Cuesta
 *    crédito de FAL: $0.10 cada 1000 caracteres (ver backend/core/voz_fal.py).
 *
 * 2. `speechSynthesis` del navegador — 100% local, el texto nunca sale de la
 *    máquina. Es el respaldo AUTOMÁTICO: si el backend no tiene FAL_KEY
 *    configurada, si no hay red, o si FAL falla por cualquier motivo, se cae
 *    aquí sin que el usuario tenga que hacer nada ni se quede sin voz.
 *
 * El intento con FAL SIEMPRE tiene un límite de tiempo corto (ver
 * `TIMEOUT_FAL_MS` en `hablar()`): la voz es para responder RÁPIDO, no vale
 * la pena hacer esperar al usuario varios segundos por una llamada de red
 * cuando la voz local ya está lista para hablar de inmediato.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { apiPost } from '../services/api';

const sintetizador = typeof window !== 'undefined' ? window.speechSynthesis : null;
export const lecturaDisponible = Boolean(sintetizador);

/**
 * Prepara el texto para ser escuchado, no leído.
 *
 * Una respuesta de BI trae markdown y a veces tablas de 16 filas. Leer eso
 * literalmente sería insoportable: nadie quiere oír "guion guion guion" ni
 * dieciséis nombres de proveedor seguidos. Se limpia el formato y las tablas
 * se anuncian en vez de recitarse.
 */
/** Convierte un valor de la base en algo que suene bien dicho en voz alta. */
function valorHablado(valor) {
    if (valor === null || valor === undefined || valor === '') return 'sin dato';

    const num = Number(String(valor).replace(/[$\s]/g, '').replace(/,/g, '.'));
    if (!Number.isNaN(num) && String(valor).trim() !== '') {
        // Los decimales .00 no aportan nada dichos en voz alta ("ciento
        // ochenta y siete coma cero cero"): se omiten cuando son cero.
        const redondeado = Math.round(num * 100) / 100;
        return Number.isInteger(redondeado)
            ? redondeado.toLocaleString('es-EC')
            : redondeado.toLocaleString('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    return String(valor);
}

/** Limpia el nombre de columna para que se lea natural. */
function etiquetaHablada(columna) {
    return String(columna || '')
        .replace(/[[\]_]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();
}

/**
 * Construye lo que se va a DECIR, priorizando el dato sobre la explicación.
 *
 * PROBLEMA QUE RESUELVE:
 * La IA devuelve por un lado un texto explicativo ("Se presenta el total de
 * empleados registrados en la ficha maestra...") y por otro los datos, que la
 * pantalla dibuja como tarjeta o tabla. Al leer solo el texto, la voz recitaba
 * el contexto y NUNCA pronunciaba la cifra: preguntabas cuántos empleados hay
 * y no te decía el número.
 *
 * Aquí la respuesta se arma desde los datos. Si preguntas un total, lo primero
 * que oyes es el total.
 */
export function construirRespuestaHablada(mensaje = {}) {
    const resultado = mensaje.result || {};
    const filas = Array.isArray(resultado.rows) ? resultado.rows : [];
    const columnas = Array.isArray(resultado.columns) ? resultado.columns : [];
    const texto = mensaje.content || resultado.explanation || '';

    // ¿La respuesta trae la advertencia de integridad? Se conserva en una
    // frase corta, aunque el resto del texto explicativo se descarte.
    const aviso = /dato no verificable por empresa/i.test(texto)
        ? 'Atención: este dato de personal podría no corresponder a esta empresa. '
        : '';

    // ── Caso 1: un solo número. Es la mayoría de preguntas de gerencia
    // ("cuántos empleados", "total de ventas") y la respuesta ES la cifra.
    if (filas.length === 1 && filas[0]?.length === 1) {
        const etiqueta = etiquetaHablada(columnas[0]);
        const valor = valorHablado(filas[0][0]);
        return `${aviso}${etiqueta ? `${etiqueta}: ` : ''}${valor}.`;
    }

    // ── Caso 2: una fila con varias columnas (ej. ventas y compras juntas).
    if (filas.length === 1 && filas[0]?.length > 1) {
        const partes = filas[0].map((v, i) => `${etiquetaHablada(columnas[i])} ${valorHablado(v)}`);
        return `${aviso}${partes.join(', ')}.`;
    }

    // ── Caso 3: tabla. Se dicen los primeros y se anuncia el resto, en vez
    // de recitar dieciséis proveedores seguidos.
    if (filas.length > 1) {
        const cuantos = Math.min(3, filas.length);
        const primeros = filas.slice(0, cuantos).map((fila) => {
            const nombre = String(fila[0] ?? '').trim();
            const dato = fila.length > 1 ? valorHablado(fila[fila.length - 1]) : '';
            return dato ? `${nombre}, ${dato}` : nombre;
        });
        const restantes = filas.length - cuantos;
        const cola = restantes > 0
            ? ` Y ${restantes} ${restantes === 1 ? 'más' : 'más'} en la tabla.`
            : '';
        return `${aviso}${primeros.join('. ')}.${cola}`;
    }

    // ── Caso 4: sin datos (saludos, respuestas conversacionales). Aquí sí se
    // lee el texto, porque es todo lo que hay.
    return prepararTextoParaVoz(texto, filas);
}

export function prepararTextoParaVoz(texto, filas = []) {
    let limpio = String(texto || '');

    // ── Advertencia de integridad ────────────────────────────────────────
    // El aviso completo son ~60 palabras técnicas (nombres de vistas, fechas,
    // el nombre del procedimiento a corregir). Leerlo entero en voz alta antes
    // de cada respuesta lo vuelve insoportable y el usuario terminaría
    // ignorándolo. Pero callarlo del todo sería peor: alguien podría preguntar
    // por voz cuánto personal tiene y recibir una cifra equivocada dicha con
    // total seguridad. Se sustituye por una frase corta, y el texto completo
    // sigue estando en el chat escrito.
    let avisoBreve = '';
    if (/dato no verificable por empresa/i.test(limpio)) {
        avisoBreve = 'Atención: este dato de personal podría no corresponder a esta empresa. ';
        // Se elimina el párrafo del aviso (va desde el emoji hasta el final
        // de esa frase larga) para quedarnos solo con la respuesta real.
        limpio = limpio.replace(/⚠️[\s\S]*?empresa seleccionada\.\s*/i, '');
    }

    limpio = limpio
        .replace(/```[\s\S]*?```/g, ' ')          // bloques de código
        .replace(/\|[^\n]*\|/g, ' ')              // filas de tabla markdown
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')  // enlaces: deja el texto
        .replace(/[#*_`>]/g, ' ')                 // símbolos de markdown
        .replace(/⚠️|📌|✅|🔴|🟢|🟡|⚪|•/g, ' ')     // emojis y viñetas
        .replace(/\s+/g, ' ')
        .trim();

    // Al quitar la tabla suele quedar la frase que la introducía colgando de
    // dos puntos ("A continuación los proveedores:"), que al oírse queda en
    // suspenso. Se recorta esa puntuación huérfana del final.
    limpio = limpio.replace(/[\s:,;.]+$/, '');

    const cantidadFilas = Array.isArray(filas) ? filas.length : 0;
    if (cantidadFilas > 1) {
        limpio += `. Tienes ${cantidadFilas} registros en la tabla.`;
    } else if (limpio) {
        limpio += '.';
    }

    // Pausas naturales: el sintetizador respeta la puntuación, así que un
    // espacio tras cada signo evita que suene como una lista atropellada.
    limpio = limpio.replace(/([.;:])\s*/g, '$1 ').trim();

    return `${avisoBreve}${limpio}`.trim();
}

// Límite de espera por voz externa (ms). Si no responde rápido, se utiliza de inmediato
// el sintetizador nativo del navegador para garantizar una experiencia fluida sin pausas.
const TIMEOUT_FAL_MS = 1000;

export function useLectura({ idioma = 'es' } = {}) {
    const [hablando, setHablando] = useState(false);
    const [vozLocal, setVozLocal] = useState(null);
    const enunciadoRef = useRef(null);
    const audioFalRef = useRef(null);
    const textoActualRef = useRef('');
    const keepAliveTimerRef = useRef(null);

    const limpiarKeepAlive = useCallback(() => {
        if (keepAliveTimerRef.current) {
            clearInterval(keepAliveTimerRef.current);
            keepAliveTimerRef.current = null;
        }
    }, []);

    const elegirMejorVoz = useCallback((voces = []) => {
        if (!voces.length) return null;
        const enEspanol = voces.filter(v => (v.lang || '').toLowerCase().startsWith(idioma));
        if (!enEspanol.length) return voces[0] || null;

        const esNeuronal = (v) => /natural|neural|online|google/i.test(v.name || '');
        const esLatino = (v) => /es-(mx|us|ec|co|ar|cl|pe|419)/i.test(v.lang || '');

        return enEspanol.find(v => esNeuronal(v) && esLatino(v))
            || enEspanol.find(v => esNeuronal(v))
            || enEspanol.find(v => esLatino(v))
            || enEspanol.find(v => v.localService)
            || enEspanol[0];
    }, [idioma]);

    // La lista de voces se carga de forma asíncrona en los navegadores
    useEffect(() => {
        if (!sintetizador) return undefined;

        const refrescarVoces = () => {
            const voces = sintetizador.getVoices();
            if (voces.length > 0) {
                const preferida = elegirMejorVoz(voces);
                setVozLocal(preferida);
            }
        };

        refrescarVoces();
        sintetizador.addEventListener('voiceschanged', refrescarVoces);
        return () => sintetizador.removeEventListener('voiceschanged', refrescarVoces);
    }, [elegirMejorVoz]);

    const detener = useCallback(() => {
        limpiarKeepAlive();
        if (audioFalRef.current) {
            try { audioFalRef.current.pause(); audioFalRef.current.currentTime = 0; } catch (_) { /* nada */ }
            audioFalRef.current = null;
        }
        if (sintetizador) {
            try { sintetizador.cancel(); } catch (_) { /* nada */ }
        }
        textoActualRef.current = '';
        setHablando(false);
    }, [limpiarKeepAlive]);

    const hablarLocal = useCallback((texto) => {
        if (!sintetizador) return;

        limpiarKeepAlive();
        try {
            sintetizador.cancel();
            sintetizador.resume();
        } catch (_) { /* nada */ }

        // Si aún no se asignó vozLocal, intentar resolverla ahora
        const vozActual = vozLocal || elegirMejorVoz(sintetizador.getVoices());
        if (vozActual && !vozLocal) {
            setVozLocal(vozActual);
        }

        const enunciado = new SpeechSynthesisUtterance(texto);
        if (vozActual) enunciado.voice = vozActual;
        enunciado.lang = vozActual?.lang || (navigator.language?.startsWith('es') ? navigator.language : 'es-MX');
        enunciado.rate = 1.05;
        enunciado.pitch = 1.0;
        enunciado.volume = 1;

        enunciado.onend = () => {
            limpiarKeepAlive();
            textoActualRef.current = '';
            setHablando(false);
        };
        enunciado.onerror = (e) => {
            limpiarKeepAlive();
            // Errores comunes que no son fatales (como interrupted al cancelar)
            if (e.error !== 'interrupted' && e.error !== 'canceled') {
                console.warn('SpeechSynthesis error:', e.error);
            }
            textoActualRef.current = '';
            setHablando(false);
        };

        enunciadoRef.current = enunciado;
        textoActualRef.current = texto;
        setHablando(true);

        try {
            sintetizador.speak(enunciado);
            // Workaround para el bug de Chrome donde speechSynthesis se congela tras 14s
            keepAliveTimerRef.current = setInterval(() => {
                if (sintetizador.speaking && !sintetizador.paused) {
                    sintetizador.pause();
                    sintetizador.resume();
                } else {
                    limpiarKeepAlive();
                }
            }, 8000);
        } catch (err) {
            console.error('Error al invocar síntesis:', err);
            setHablando(false);
        }
    }, [vozLocal, elegirMejorVoz, limpiarKeepAlive]);

    const hablar = useCallback((texto) => {
        if (!texto || !String(texto).trim()) return;

        const textoLimpio = String(texto).trim();

        // Si ya estaba hablando EXACTAMENTE el mismo texto, actúa como interruptor
        if (hablando && textoActualRef.current === textoLimpio) {
            detener();
            return;
        }

        // Si estaba hablando otra cosa, se detiene primero para dar paso al nuevo mensaje
        if (hablando || audioFalRef.current || sintetizador?.speaking) {
            detener();
        }

        setHablando(true);
        textoActualRef.current = textoLimpio;

        // Intentar endpoint de síntesis rápida o caer a voz local nativa de inmediato
        apiPost('/query/speak', { text: textoLimpio }, { timeout: TIMEOUT_FAL_MS })
            .then((res) => {
                const audioUrl = res?.data?.audio_url;
                if (!audioUrl || res?.data?.status === 'use_local') {
                    hablarLocal(textoLimpio);
                    return;
                }

                const audio = new Audio(audioUrl);
                audioFalRef.current = audio;
                audio.onended = () => {
                    audioFalRef.current = null;
                    textoActualRef.current = '';
                    setHablando(false);
                };
                audio.onerror = () => {
                    audioFalRef.current = null;
                    hablarLocal(textoLimpio);
                };
                audio.play().catch(() => {
                    audioFalRef.current = null;
                    hablarLocal(textoLimpio);
                });
            })
            .catch(() => {
                hablarLocal(textoLimpio);
            });
    }, [hablando, hablarLocal, detener]);

    // Limpieza al desmontar
    useEffect(() => () => {
        limpiarKeepAlive();
        try { sintetizador?.cancel(); } catch (_) { /* nada */ }
        try { audioFalRef.current?.pause(); } catch (_) { /* nada */ }
    }, [limpiarKeepAlive]);

    return {
        hablar,
        detener,
        hablando,
        disponible: lecturaDisponible,
        // Útil para avisar en la interfaz si la voz elegida no es local.
        vozEsLocal: Boolean(vozLocal?.localService),
        nombreVoz: vozLocal?.name || '',
    };
}
