/**
 * @file Hook de dictado por voz con la Web Speech API del navegador (Chrome y
 * Edge), que es gratuita y no requiere claves. Lo que se dicta es la pregunta,
 * que no contiene cifras de los datos consultados, por lo que el riesgo de
 * privacidad es bajo. Limitación: el reconocimiento no es local, Chrome envía
 * el audio a los servidores de Google; si el audio no debe salir de la red,
 * hay que cambiar a un motor local (p. ej. Whisper autoalojado).
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */
import { useCallback, useEffect, useRef, useState } from 'react';

// Compatibilidad: Chrome/Edge exponen la API con prefijo `webkit`.
const ReconocimientoVoz =
    typeof window !== 'undefined'
        ? (window.SpeechRecognition || window.webkitSpeechRecognition)
        : null;

/** Indica si el navegador ofrece reconocimiento de voz. */
export const dictadoDisponible = Boolean(ReconocimientoVoz);

/**
 * Controla una sesión de dictado: escucha, muestra el texto parcial y entrega
 * el texto definitivo al terminar la frase.
 * @param {object} [opciones]
 * @param {function(string): void} [opciones.onTexto] Recibe el texto definitivo.
 * @param {string} [opciones.idioma] Código BCP 47; por defecto, el idioma del
 *   navegador si es español, o 'es-419'.
 * @returns {{escuchando: boolean, textoParcial: string, error: string|null,
 *   iniciar: function(): void, detener: function(): void, disponible: boolean}}
 *   Estado del dictado y controles; `iniciar` alterna entre iniciar y detener.
 */
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
                // Silencio temporal: no se trata como un error.
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
