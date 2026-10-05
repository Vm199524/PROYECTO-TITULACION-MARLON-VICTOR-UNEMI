/**
 * @file Hook del resumen contextual de la base activa. Pide
 * `/api/context-overview` (perfil, KPI, áreas y preguntas sugeridas), reintenta
 * mientras la conexión se estabiliza y expone el estado de carga. Lo usa
 * ChatArea.jsx para las tarjetas y las sugerencias del chat.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import { useEffect, useRef, useState } from 'react';

import { apiGet } from '../services/api';

/**
 * Carga el resumen contextual de una base de datos.
 * @param {string} dbId Código de la base activa; sin valor no se pide nada.
 * @param {boolean} [enabled=true] Permite desactivar la carga.
 * @returns {{overview: object|null, loading: boolean, error: string,
 *   reloadOverview: function(boolean=, number=): Promise<object|null>}}
 *   Estado del resumen y función para recargarlo (`forceRefresh` omite la
 *   caché del servidor).
 */
export function useContextOverview(dbId, enabled = true) {
    const [overview, setOverview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const requestIdRef = useRef(0);
    const retryTimerRef = useRef(null);

    // Reintento controlado (hasta 4 veces, cada 1,2 s) mientras la sesión
    // termina de estabilizarse.
    const scheduleRetry = (forceRefresh, attempt) => {
        if (typeof window === 'undefined' || attempt >= 4) return;
        window.clearTimeout(retryTimerRef.current);
        retryTimerRef.current = window.setTimeout(() => {
            void loadOverview(forceRefresh, attempt + 1);
        }, 1200);
    };

    // Lee el resumen que consumen las tarjetas del chat. `requestIdRef`
    // descarta las respuestas de peticiones que ya fueron reemplazadas.
    const loadOverview = async (forceRefresh = false, attempt = 0) => {
        if (!dbId || !enabled) {
            window.clearTimeout(retryTimerRef.current);
            setOverview(null);
            setError('');
            setLoading(false);
            return null;
        }
        const requestId = requestIdRef.current + 1;
        requestIdRef.current = requestId;
        setLoading(true);
        setError('');
        try {
            const params = new URLSearchParams();
            if (dbId) params.set('target_db', dbId);
            if (forceRefresh) params.set('force_refresh', 'true');
            const suffix = params.toString() ? `?${params.toString()}` : '';
            const res = await apiGet(`/context-overview${suffix}`, { timeout: 15000 });
            if (requestId !== requestIdRef.current) return null;
            const payload = res.data || null;
            setOverview(payload);
            // El reintento se mide por `quick_questions`, que es lo que alimenta
            // la interfaz (el botón de Sugerencias del ChatInput). No sirve
            // medirlo por `kpis` ni por `payload.database`: /context-overview
            // arma `kpis` como una lista fija de 4 elementos (ver
            // routes_quantum_core.py) y `database` siempre trae `target_db` o
            // "ACTIVA". Justo al conectar, el backend todavía resuelve el
            // esquema de la base recién elegida y la primera respuesta suele
            // llegar sin preguntas; sin reintento, el botón no aparecería hasta
            // un cambio de base.
            const preguntas = Array.isArray(payload?.quick_questions) ? payload.quick_questions : [];
            const shouldRetry = !forceRefresh
                && attempt < 4
                && dbId
                && enabled
                && preguntas.length === 0;
            if (shouldRetry) {
                scheduleRetry(forceRefresh, attempt);
            }
            return payload;
        } catch (err) {
            if (requestId !== requestIdRef.current) return null;
            setError(err.response?.data?.detail || 'No pude cargar el contexto activo.');
            // También se reintenta cuando la petición falla, no solo cuando
            // vuelve vacía. Al elegir una empresa, el frontend actualiza
            // `connInfo` de forma optimista antes de que termine /connect en el
            // servidor (ver handleConnect en App.jsx), así que esta primera
            // llamada puede recibir «No hay una conexión activa» (400) o una
            // sesión que todavía apunta a la base anterior. Sin reintento, esa
            // condición de carrera dejaría el contexto vacío.
            if (!forceRefresh && attempt < 4 && dbId && enabled) {
                scheduleRetry(forceRefresh, attempt);
            }
            return null;
        } finally {
            if (requestId === requestIdRef.current) {
                setLoading(false);
            }
        }
    };

    useEffect(() => {
        void loadOverview(false);
        return () => {
            window.clearTimeout(retryTimerRef.current);
        };
    }, [dbId, enabled]);

    return {
        overview,
        loading,
        error,
        reloadOverview: loadOverview,
    };
}
