/**
 * hooks/useDictado.js — Dictado por voz usando el reconocimiento del navegador.
 *
 * Por qué el navegador y no un servicio pago: para DICTAR la pregunta no hace
 * falta nada externo. La Web Speech API viene en Chrome y Edge, es gratis y no
 * requiere configurar claves. Además, lo que se dicta es la pregunta
 * ("cuánto vendimos en marzo"), que no contiene cifras del negocio — el riesgo
 * de privacidad es bajo comparado con leer en voz alta una respuesta que sí
 * lleva sueldos y totales.
 *
 * Limitación honesta: el reconocimiento del navegador NO es local. Chrome envía
 * el audio a los servidores de Google para transcribirlo. Es gratis, no
 * privado. Si algún día se necesita que el audio no salga de la red, hay que
 * cambiar a un motor local (Whisper autoalojado) — no a otro servicio en la nube.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

// Compatibilidad: Chrome/Edge exponen la API con prefijo `webkit`.
const ReconocimientoVoz =
    typeof window !== 'undefined'
        ? (window.SpeechRecognition || window.webkitSpeechRecognition)
        : null;

export const dictadoDisponible = Boolean(ReconocimientoVoz);

export function useDictado({ onTexto, idioma } = {}) {
    const [escuchando, setEscuchando] = useState(false);
    const [error, setError] = useState(null);
    const [textoParcial, setTextoParcial] = useState('');

    const idiomaEfectivo = idioma || (typeof navigator !== 'undefined' && navigator.language?.startsWith('es') ? navigator.language : 'es-419');

    const reconocimientoRef = useRef(null);
    // Se guarda el callback en una ref para que reiniciar el dictado no
    // dependa de que el componente padre memorice la función.
    const onTextoRef = useRef(onTexto);
    useEffect(() => { onTextoRef.current = onTexto; }, [onTexto]);

    const detener = useCallback(() => {
        try { reconocimientoRef.current?.stop(); } catch (_) { /* ya detenido */ }
        setEscuchando(false);
        setTextoParcial('');
    }, []);

    const iniciar = useCallback(() => {
        if (!ReconocimientoVoz) {
            setError('Tu navegador no admite dictado por voz. Usa Chrome o Edge.');
            return;
        }
        if (escuchando) { detener(); return; }

        setError(null);
        setTextoParcial('');

        const rec = new ReconocimientoVoz();
        rec.lang = idiomaEfectivo;
        // `interimResults` permite mostrar el texto mientras se habla, para que
        // el usuario vea que se le está entendiendo y no hable al vacío.
        rec.interimResults = true;
        rec.continuous = false;
        rec.maxAlternatives = 1;

        rec.onresult = (evento) => {
            let definitivo = '';
            let parcial = '';
            for (let i = evento.resultIndex; i < evento.results.length; i += 1) {
                const trozo = evento.results[i][0].transcript;
                if (evento.results[i].isFinal) definitivo += trozo;
                else parcial += trozo;
            }
            if (parcial) setTextoParcial(parcial);
            if (definitivo) {
                setTextoParcial('');
                onTextoRef.current?.(definitivo.trim());
            }
        };

        rec.onerror = (evento) => {
            if (evento.error === 'no-speech') {
                // Silencio temporal: no tratarlo como fallo fatal alarmante
                setEscuchando(false);
                setTextoParcial('');
                return;
            }
            const mensajes = {
                'audio-capture': 'No se detectó micrófono conectado.',
                'not-allowed': 'Permiso de micrófono denegado. Habilítalo en el navegador.',
                'service-not-allowed': 'Servicio de reconocimiento no permitido en este entorno.',
                'network': 'Sin conexión: el dictado del navegador necesita internet.',
            };
            setError(mensajes[evento.error] || 'No se pudo usar el micrófono.');
            setEscuchando(false);
            setTextoParcial('');
        };

        rec.onend = () => {
            setEscuchando(false);
            setTextoParcial('');
        };

        reconocimientoRef.current = rec;
        try {
            rec.start();
            setEscuchando(true);
        } catch (_err) {
            // start() lanza si ya había una sesión activa; no es un fallo real.
            setEscuchando(false);
        }
    }, [escuchando, idiomaEfectivo, detener]);

    // Si el componente se desmonta mientras escucha, hay que soltar el
    // micrófono: de lo contrario el navegador deja el indicador encendido.
    useEffect(() => () => {
        try { reconocimientoRef.current?.abort(); } catch (_) { /* nada */ }
    }, []);

    return { escuchando, textoParcial, error, iniciar, detener, disponible: dictadoDisponible };
}
