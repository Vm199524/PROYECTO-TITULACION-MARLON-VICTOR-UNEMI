/**
 * Archivo: useContextOverview.js
 * Rol: hook para pedir el resumen contextual de la base activa.
 * Recibe desde: ChatArea.jsx.
 * Se conecta con: api.js y el endpoint /api/context-overview.
 * Responsabilidades: cargar overview, reintentar y exponer estado.
 */

import { useEffect, useRef, useState } from 'react';

import { apiGet } from '../services/api';

export function useContextOverview(dbId, enabled = true) {
    const [overview, setOverview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const requestIdRef = useRef(0);
    const retryTimerRef = useRef(null);

    // Seccion: reintento controlado mientras la sesion termina de estabilizarse.
    const scheduleRetry = (forceRefresh, attempt) => {
        if (typeof window === 'undefined' || attempt >= 4) return;
        window.clearTimeout(retryTimerRef.current);
        retryTimerRef.current = window.setTimeout(() => {
            void loadOverview(forceRefresh, attempt + 1);
        }, 1200);
    };

    // Seccion: lectura del overview consumido por las cards del chat.
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
            // El reintento se mide por `quick_questions`, que es lo que de verdad
            // alimenta la interfaz (el botón de Sugerencias del ChatInput).
            //
            // BUG REAL corregido el 30/08/2026 (detectado en pruebas: "el
            // botón de sugerencias solo aparece cuando ya hiciste una consulta y
            // luego cambias a otra base; debería aparecer apenas te conectes"):
            // antes esta condición miraba `kpis.length === 0`, pero /context-overview
            // arma `kpis` como una lista FIJA de 4 elementos (ver
            // routes_quantum_core.py), así que nunca vale 0 — y `payload.database`
            // tampoco viene vacío nunca, porque el backend le pone `target_db` o
            // "ACTIVA". Es decir, el reintento era código muerto: jamás se
            // disparaba. Si la primera respuesta llegaba sin preguntas (lo normal
            // justo al conectar, cuando el backend todavía está resolviendo el
            // esquema de la base recién elegida), se quedaba vacío para siempre y
            // el botón no aparecía hasta que un cambio de base volvía a montar
            // el efecto.
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
            // También hay que reintentar cuando la petición FALLA, no solo cuando
            // vuelve vacía. Al elegir una empresa, el frontend actualiza `connInfo`
            // de forma optimista ANTES de que termine /connect en el servidor
            // (ver handleConnect en App.jsx), así que esta primera llamada puede
            // encontrarse con "No hay una conexion activa" (400) o con la sesión
            // todavía apuntando a la base anterior. Sin reintento, ese fallo de
            // carrera dejaba el contexto vacío de forma permanente.
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
