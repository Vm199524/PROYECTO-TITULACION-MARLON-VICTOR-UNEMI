/**
 * @file Componente raíz del frontend y centro del estado global. Gestiona el
 * inicio de sesión con JWT, la conexión a SQL Server por empresa, el chat con
 * respuestas en streaming (/api/query/stream) y análisis de imágenes, el
 * historial de sesiones (caché local por usuario sincronizada con
 * /api/sessions), el cierre de sesión por inactividad y la elección entre el
 * diseño móvil y el de escritorio según el ancho de pantalla. Lo monta main.jsx.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React, { useState, useEffect, useRef, useMemo } from 'react';
import * as Sentry from "@sentry/react";
import { Box, GraduationCap, Layout, TrendingUp, Users } from 'lucide-react';

import { useAutoCorrect } from './hooks/useAutoCorrect';
import { apiGet, apiPost, apiPut } from './services/api';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LoginView } from './pages/Login';
import { API_BASE, dbToBusinessName, getDbModules, getDbProfile, mergeDbCatalog, clearDbCatalog } from './constants/appConfig';
import { normalizeQueryResult } from './utils/queryResult';
import { normalizeSqlServerHost } from './utils/sqlServer';

// Importación directa de los tableros móvil y de escritorio, sin React.lazy():
// el import dinámico, combinado con el Service Worker y los hashes variables
// de Vite, provoca «Failed to fetch dynamically imported module» en Chrome y
// Edge en modo --app.
import { DashboardMobile } from './mobile/DashboardMobile';
import { DashboardView as DashboardDesktop } from './pages/DashboardDesktop';

// Vista activa según el hash de la URL: '#/quantum-core' o el tablero.
const readAppView = () => {
    if (typeof window === 'undefined') return 'dashboard';
    return (window.location.hash || '').trim().toLowerCase() === '#/quantum-core'
        ? 'quantum-core'
        : 'dashboard';
};

const resetAppViewToDashboard = () => {
    if (typeof window === 'undefined') return;
    window.location.hash = '';
};

// Tiempos de sesión y de conexión (ms): cierre por inactividad a los 30 min,
// revisión cada 15 s, espera de la primera conexión y pausas entre reintentos.
const SESSION_IDLE_TIMEOUT_MS = 30 * 60 * 1000;
const SESSION_CHECK_INTERVAL_MS = 15 * 1000;
const SESSION_ACTIVITY_KEY = 'quantum_last_activity';
const INITIAL_CONNECT_TIMEOUT_MS = 30000;
const BACKGROUND_CONNECT_RETRY_DELAY_MS = 1500;
const LOGIN_RETRY_DELAY_MS = 650;
// Margen total que el login espera a que el backend termine de arrancar antes
// de darse por vencido (ver handleAuthLogin). Uvicorn tarda bastante más que
// Vite en estar listo, y el lanzador abre la ventana apenas Vite responde.
// Debe superar el timeout de un solo intento (15 s): la primera llamada tras
// arrancar uvicorn carga dependencias pesadas (langchain) y puede tardar más
// de un minuto. Con 120 s el bucle reintenta hasta que el backend contesta:
// una contraseña incorrecta recibe su 401 ("Usuario o contraseña
// incorrectos.") y el panel «El sistema no responde» queda reservado para un
// backend que de verdad no responde.
const LOGIN_BOOT_WAIT_MS = 120000;

// Caché local del historial, separada por usuario. Con una clave por usuario
// (quantum_sessions::<usuario>) cada quien ve su propio historial al instante,
// sin esperar a /api/sessions, y nadie ve el de otro usuario del mismo
// navegador. La clave compartida 'quantum_sessions' solo se lee para migrarla.
const SESSIONS_CACHE_PREFIX = 'quantum_sessions::';
const LEGACY_SESSIONS_KEY = 'quantum_sessions';

// Identificador del usuario para la clave de caché (username, sub, id o email).
const userCacheId = (user) => {
    if (!user) return '';
    const raw = user.username || user.sub || user.id || user.email || '';
    return String(raw).trim().toLowerCase();
};

// Usuario guardado en localStorage por el último inicio de sesión, o null.
const readStoredUser = () => {
    try { return JSON.parse(localStorage.getItem('quantum_user')) || null; }
    catch (_e) { return null; }
};

const sessionsCacheKey = (user) => {
    const id = userCacheId(user);
    return id ? `${SESSIONS_CACHE_PREFIX}${id}` : '';
};

const readSessionsCache = (user) => {
    const key = sessionsCacheKey(user);
    if (!key) return [];
    try {
        const cached = JSON.parse(localStorage.getItem(key));
        if (Array.isArray(cached)) return cached;
        // Migración desde la clave antigua compartida: se adopta una sola vez
        // para que el usuario actual no pierda el historial que ya tenía.
        const legacy = JSON.parse(localStorage.getItem(LEGACY_SESSIONS_KEY));
        if (Array.isArray(legacy) && legacy.length > 0) {
            localStorage.setItem(key, JSON.stringify(legacy));
            localStorage.removeItem(LEGACY_SESSIONS_KEY);
            return legacy;
        }
    } catch (_e) { /* caché corrupta: se ignora */ }
    return [];
};

const writeSessionsCache = (user, sessions) => {
    const key = sessionsCacheKey(user);
    if (!key) return;
    try { localStorage.setItem(key, JSON.stringify(sessions || [])); }
    catch (_e) { /* cuota llena: no es crítico, el backend es la fuente de verdad */ }
};

// Lee el campo `exp` del JWT y lo devuelve en ms; 0 si no se puede leer.
const parseJwtExpiryMs = (token) => {
    if (!token) return 0;
    try {
        const payload = JSON.parse(window.atob(token.split('.')[1] || ''));
        return Number(payload?.exp || 0) * 1000;
    } catch (_err) {
        return 0;
    }
};

// URL del endpoint de salud del backend vista desde el navegador. Debe pasar
// por el mismo camino que el resto de la API ("/api/health") y no por la raíz
// del frontend: "/health" caería en el servidor de Vite (local) o en Firebase
// (producción), porque el proxy y el rewrite solo reenvían "/api/*". Con
// "/api/health" el proxy de Vite lo envía al backend y Firebase lo reescribe
// hacia Cloud Run.
const resolveHealthUrl = () => {
    const base = String(API_BASE || '/api').trim();
    return `${base.replace(/\/$/, '')}/health`;
};

// Consulta /api/health con un límite de 1,2 s; devuelve el JSON o null.
const probeBackendHealth = async () => {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1200);

        const response = await fetch(resolveHealthUrl(), {
            method: 'GET',
            signal: controller.signal
        });

        clearTimeout(timeoutId);
        if (!response.ok) return null;
        return await response.json();
    } catch (_err) {
        return null;
    }
};

const delay = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

// Umbrales habituales (Tailwind, Material e iOS HIG coinciden en este rango):
// <768 px teléfono, 768-1023 px tableta, >=1024 px escritorio.
const clasificarDeviceType = (ancho) => {
    if (ancho < 768) return 'mobile';
    if (ancho < 1024) return 'tablet';
    return 'desktop';
};

/**
 * Componente principal: concentra el estado global (sesión, conexión, chat e
 * historial) y renderiza el login o el tablero móvil o de escritorio.
 * @returns {JSX.Element} Login o tablero, según el estado de la sesión.
 */
function AppInner() {
    // Estado global: conexión, sesiones, chat y permisos del usuario.
    const [biPulse, setBiPulse] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [loading, setLoading] = useState(false);
    // El clic en "Ingresar al sistema" no usa `loading` (que muestra la
    // pantalla de carga completa en Login.jsx). `authPending` solo controla el
    // indicador dentro del botón mientras /login verifica las credenciales; el
    // tablero no se abre hasta que /login confirma el token (ver
    // `handleAuthLogin`).
    const [authPending, setAuthPending] = useState(false);
    const [error, setError] = useState(null);
    // Indica si el error es del sistema (el servidor no responde, la conexión
    // SQL se cayó) o algo que el usuario puede corregir (credenciales
    // incorrectas). El login solo ofrece «Refrescar Sistema» en el primer caso:
    // recargar no corrige una contraseña equivocada y el mismo error
    // aparecería dos veces en pantalla.
    const [errorDeSistema, setErrorDeSistema] = useState(false);
    const [schema, setSchema] = useState({});
    const [prompt, setPrompt] = useState('');
    // Selector manual de motor de IA. '' usa Flash por defecto; otro motor
    // solo si el usuario lo elige. El servidor lo revalida contra los modelos
    // permitidos para ese usuario: este valor es solo una preferencia, no la
    // fuente de verdad de lo que puede usar.
    const [motorIA, setMotorIA] = useState('');
    const [chatHistory, setChatHistory] = useState([]);
    // Imágenes adjuntas pendientes de enviar al modelo de visión. Cada
    // elemento: { id, dataUrl, name }. Se limpia después de enviar.
    const [attachedImages, setAttachedImages] = useState([]);
    const [currentResult, setCurrentResult] = useState(null);
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [activeModule, setActiveModule] = useState(null);
    const [correctionHint, setCorrectionHint] = useState(null);
    const [expandedTables, setExpandedTables] = useState({});
    const [availableDBs, setAvailableDBs] = useState([]);
    const [fetchingDBs, setFetchingDBs] = useState(false);
    const [activeSessionId, setActiveSessionId] = useState(null);
    const [menuOpenId, setMenuOpenId] = useState(null);
    const [editingId, setEditingId] = useState(null);
    const [tempSessionName, setTempSessionName] = useState('');
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [devClicks, setDevClicks] = useState(0);
    const [showDevOptions, setShowDevOptions] = useState(false);
    // Mensaje que se está recibiendo por streaming (efecto de escritura).
    const [streamingMsgId, setStreamingMsgId] = useState(null);

    // Cinco clics en el título del login muestran las opciones de infraestructura.
    const handleTitleClick = () => {
        setDevClicks(prev => {
            const next = prev + 1;
            if (next >= 5) {
                setShowDevOptions(true);
                return 0;
            }
            return next;
        });
    };
    const [showHost, setShowHost] = useState(false);
    const [discoveryData, setDiscoveryData] = useState(null);
    const [isScanning, setIsScanning] = useState(false);
    const [isSwitchingDB, setIsSwitchingDB] = useState(false);
    const [activeView, setActiveView] = useState(readAppView);

    // Seguridad, restauración de sesión y permisos visibles en la interfaz.
    const [isVerifying, setIsVerifying] = useState(false);
    const [isRestoringSession, setIsRestoringSession] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [userAuth, setUserAuth] = useState(null);
    const [tempCreds, setTempCreds] = useState({ username: '', password: '' });
    const [isConnectionReady, setIsConnectionReady] = useState(false);
    const defaultConnInfo = {
        host: '',
        database: '',
        selected_company_code: '',
        auth_type: 'SQL Server Authentication',
        driver: 'SQL Server',
        user: 'sa',
        password: '',
        api_key: '',
        isDemo: false
    };

    // Borra la sesión guardada en localStorage (token, usuario, conexión y esquema).
    const clearPersistedSession = () => {
        localStorage.removeItem('quantum_token');
        localStorage.removeItem('quantum_user');
        localStorage.removeItem('quantum_conninfo');
        localStorage.removeItem('quantum_schema');
        localStorage.removeItem(SESSION_ACTIVITY_KEY);
        localStorage.removeItem(LEGACY_SESSIONS_KEY);
        // El historial de chat vive en el backend, aislado por usuario vía JWT.
        // La copia local usa una clave propia de cada usuario
        // (quantum_sessions::<usuario>), así que no se borra al cerrar sesión:
        // otro usuario del mismo navegador tiene otra clave y no la ve ni la
        // sobrescribe, y al volver a entrar el historial aparece desde el
        // primer instante, sin esperar a /api/sessions.
        sessionsHydratedRef.current = false;
        setSavedSessions([]);
        setSessionsLoading(true);
    };

    // Abre el tablero con un mensaje de bienvenida y una conversación nueva.
    function openConnectedShell(dataToUse) {
        const effectiveData = dataToUse || connInfo;
        const displayDbCode = effectiveData.selected_company_code || effectiveData.database;
        setIsConnected(true);
        setIsConnectionReady(true);
        setIsVerifying(false);
        resetAppViewToDashboard();
        setActiveView('dashboard');
        setActiveModule(null);
        setCurrentResult(null);
        // Se suelta `activeSessionId` porque empieza una conversación nueva.
        // El efecto de autoguardado (más abajo, depende de [chatHistory,
        // currentResult]) usa activeSessionId para decidir si crea una sesión
        // o actualiza una existente; sin este reinicio, el primer mensaje en la
        // empresa nueva sobrescribiría la conversación anterior en lugar de
        // crear otra entrada en el historial.
        setActiveSessionId(null);
        setChatHistory([{
            id: `welcome-${Date.now()}`,
            type: 'ai',
            isWelcome: true,
            dbName: (!displayDbCode || displayDbCode.toUpperCase() === 'MASTER')
                ? 'Ninguna'
                : (effectiveData.database === 'LOCAL_FILE' ? 'quantum_data.db' : dbToBusinessName(displayDbCode)),
            content: `¡Hola! Soy **VicMar Data AI**, tu asistente estratégica en IA para VicMar Data AI. 
Estoy lista para ayudarte a explorar tus datos una vez que elijas una empresa en el selector superior. 
¿En qué puedo ayudarte hoy?`,
            quickQuestions: [],
            timestamp: new Date().toLocaleTimeString()
        }]);
    }

    // Registra la última actividad del usuario para el cierre por inactividad.
    const registerActivity = () => {
        const now = Date.now();
        lastActivityRef.current = now;
        if (localStorage.getItem('quantum_token')) {
            localStorage.setItem(SESSION_ACTIVITY_KEY, String(now));
        }
    };

    // Inicia sesión con /login y, solo si las credenciales son válidas, abre el tablero.
    const handleAuthLogin = async (e) => {
        if (e) e.preventDefault();
        if (!tempCreds.username || !tempCreds.password) return;

        setError(null);
        setErrorDeSistema(false);
        setAuthPending(true);

        // Validación antes de entrar: el tablero se abre solo después de que
        // /login confirma credenciales y token (ver `openConnectedShell`,
        // dentro del try). Abrirlo antes, de forma optimista, haría que el
        // tablero apareciera un instante con credenciales incorrectas. Con
        // credenciales malas, el usuario se queda en el formulario y ve el error.
        //
        // `authPending` mantiene el indicador dentro del botón mientras /login
        // reintenta y uvicorn termina de arrancar (LOGIN_BOOT_WAIT_MS).
        const targetData = { ...connInfo, database: connInfo.database || '' };

        try {
            const loginPayload = {
                username: tempCreds.username,
                password: tempCreds.password
            };
            // Espera activa mientras el backend termina de arrancar. El
            // lanzador (VicMarDataAI_Silenzo.vbs) abre la ventana en cuanto Vite
            // escucha, pero uvicorn tarda más (carga FastAPI, SQLAlchemy, pyodbc
            // y la base de conocimiento). Un solo clic reintenta cada
            // LOGIN_RETRY_DELAY_MS hasta agotar LOGIN_BOOT_WAIT_MS, pero solo
            // mientras el fallo sea de conexión (el servidor aún no contesta).
            // Una contraseña incorrecta responde 401, con `err.response`, y sale
            // de inmediato.
            let res = null;
            const inicioIntentos = Date.now();
            for (;;) {
                try {
                    res = await apiPost('/login', loginPayload, { timeout: 15000 });
                    break;
                } catch (intentoErr) {
                    const backendSinResponder = intentoErr?.code === 'ECONNABORTED' || !intentoErr?.response;
                    const quedaMargen = (Date.now() - inicioIntentos) < LOGIN_BOOT_WAIT_MS;
                    if (!backendSinResponder || !quedaMargen) throw intentoErr;
                    await delay(LOGIN_RETRY_DELAY_MS);
                }
            }

            const token = res.data.access_token;
            const userData = res.data.user;

            if (token) {
                localStorage.setItem('quantum_token', token);
            }
            registerActivity();

            setUserAuth(userData);
            localStorage.setItem('quantum_user', JSON.stringify(userData));
            // Credenciales válidas y token recibido: solo aquí se abre el
            // tablero. Con credenciales malas no se llega a esta línea: el
            // catch deja el error visible en el formulario.
            openConnectedShell(targetData);
            // Se muestra de inmediato el historial que este navegador guardó
            // para este usuario; la llamada siguiente lo refresca contra el
            // backend sin dejar el panel vacío mientras tanto.
            const cachedSessions = readSessionsCache(userData);
            if (cachedSessions.length > 0) {
                setSavedSessions(cachedSessions);
                setSessionsLoading(false);
            }
            void hydrateSessionHistory();

            // Si el usuario ya tiene una base configurada (p. ej. guardada de una
            // sesión anterior), se conecta en segundo plano; si no, se cargan
            // las bases para que elija.
            if (targetData.database && targetData.database !== 'PROYECTO') {
                void handleConnect(null, targetData, {
                    background: true,
                    timeoutMs: INITIAL_CONNECT_TIMEOUT_MS
                }).catch((connErr) => {
                    console.warn("Conexión persistente fallida:", connErr);
                });
            } else {
                void loadDatabases(targetData);
            }
        } catch (err) {
            // /login falló (credenciales, tiempo de espera o red). Como el
            // tablero no se abre antes de validar, no hay transición que
            // revertir: el usuario permanece en el formulario con el error
            // visible. Las líneas siguientes limpian cualquier sesión residual.
            localStorage.removeItem('quantum_token');
            localStorage.removeItem('quantum_user');
            setUserAuth(null);
            setIsConnected(false);
            setIsConnectionReady(false);
            setIsVerifying(true);
            const statusLogin = err.response?.status;
            if (!err.response) {
                // El servidor no llegó a contestar (caído, arrancando o sin
                // red): aquí sí tiene sentido ofrecer refrescar.
                setError('El sistema no responde. Verifica que el servicio esté encendido e intenta de nuevo.');
                setErrorDeSistema(true);
            } else if (statusLogin === 401 || statusLogin === 403) {
                // El servidor respondió y rechazó las credenciales. El mensaje
                // es propio y no depende del `detail` del backend. Nunca se
                // ofrece refrescar: recargar no corrige una contraseña mal
                // escrita y duplicaría el error en pantalla.
                setError('Usuario o contraseña incorrectos.');
                setErrorDeSistema(false);
            } else {
                // Otra respuesta del servidor (400, 500...): se muestra su
                // detail si lo trae, para diagnóstico.
                setError(err.response?.data?.detail || 'No se pudo iniciar sesión. Intenta de nuevo.');
                setErrorDeSistema(false);
            }
        } finally {
            setAuthPending(false);
        }
    };

    // Conecta a la base o empresa elegida con /connect. Opciones: `background`
    // (sin pantalla de carga), `dbSwitch` (cambio de empresa con actualización
    // optimista), `openShellOnSuccess` y `timeoutMs`.
    const handleConnect = async (e, overrideData = null, options = {}) => {
        if (e && e.preventDefault) e.preventDefault();
        // "El último clic gana": si ya hay una conexión en curso, la nueva no
        // se descarta. El mecanismo de `generation` (más abajo) hace que la
        // respuesta de la conexión anterior, que llega tarde, se ignore y no
        // pise a la nueva. En un selector, la última intención del usuario es
        // la que vale.
        const mergedConnInfo = overrideData ? { ...connInfo, ...overrideData } : connInfo;
        const targetCompanyCode = overrideData && ('selected_company_code' in overrideData)
            ? overrideData.selected_company_code
            : (overrideData?.database && overrideData.database.toUpperCase() !== 'CHAT'
                ? overrideData.database
                : mergedConnInfo.selected_company_code);
        const dataToUse = {
            ...mergedConnInfo,
            host: normalizeSqlServerHost(mergedConnInfo.host),
            database: String(mergedConnInfo.database || '').trim(),
            selected_company_code: String(targetCompanyCode || mergedConnInfo.database || '').trim().toUpperCase(),
        };
        const previousConnInfo = connInfo;
        const background = !!options.background;
        const openShellOnSuccess = !!options.openShellOnSuccess;
        const dbSwitch = !!options.dbSwitch;
        const timeoutMs = Number(options.timeoutMs) > 0
            ? Number(options.timeoutMs)
            : (background ? INITIAL_CONNECT_TIMEOUT_MS : 45000);
        const retryOnBootstrapFailure = background && !dbSwitch && options.retryOnBootstrapFailure !== false;
        // La generación se reserva de inmediato, ANTES de esperar: así queda
        // registrado el orden real en que el usuario hizo clic.
        const requestGeneration = connectGenerationRef.current + 1;
        connectGenerationRef.current = requestGeneration;

        // Serialización: nunca dos /connect en paralelo. /connect reconfigura
        // la sesión del usuario en el backend; si dos corrieran a la vez, la
        // última en terminar dejaría al backend apuntando a una empresa
        // distinta de la que muestra la pantalla. Se espera a que la anterior
        // termine; si mientras tanto el usuario eligió otra empresa, esta
        // petición se abandona porque la más nueva hará el trabajo.
        const MAX_ESPERA_CONEXION_MS = 60000;
        const inicioEspera = Date.now();
        while (isConnectingRef.current && (Date.now() - inicioEspera) < MAX_ESPERA_CONEXION_MS) {
            await new Promise((resolve) => setTimeout(resolve, 120));
            if (requestGeneration !== connectGenerationRef.current) {
                return { status: 'superseded' };
            }
        }

        isConnectingRef.current = true;
        if (dbSwitch) {
            setIsSwitchingDB(true);
            // El área de chat no se bloquea (no se llama a
            // setIsConnectionReady(false)) para permitir saludos inmediatos.
            //
            // `business_name` se actualiza junto con la empresa, no después: si
            // conservara el de la empresa anterior hasta la respuesta del
            // servidor, el encabezado mostraría una empresa mientras las
            // consultas se envían a otra. El nombre en pantalla debe ser siempre
            // el de la empresa que realmente se consulta.
            const perfilDestino = getDbProfile(
                dataToUse.selected_company_code || dataToUse.database
            );
            setConnInfo(prev => ({
                ...prev,
                ...dataToUse,
                business_name: perfilDestino?.business_name
                    || dataToUse.selected_company_code
                    || dataToUse.database
                    || '',
            }));
        } else if (!background) {
            setLoading(true);
        }
        if (!background) {
            setError(null);
            setErrorDeSistema(false);
        }
        try {
            const res = await apiPost('/connect', dataToUse, { timeout: timeoutMs });
            if (requestGeneration !== connectGenerationRef.current) {
                return res.data;
            }
            const resolvedHost = normalizeSqlServerHost(res.data?.host || dataToUse.host);
            const resolvedCompanyCode = String(
                res.data?.selected_company_code || dataToUse.selected_company_code || res.data?.database || dataToUse.database || ''
            ).trim().toUpperCase();
            const resolvedConnInfo = { 
                ...dataToUse, 
                host: resolvedHost,
                selected_company_code: resolvedCompanyCode,
                business_name: res.data?.business_name || res.data?.database || dataToUse.database,
                databases: res.data?.databases || []
            };
            if (res.data?.company_profile) {
                mergeDbCatalog([res.data.company_profile]);
            }
            setSchema(res.data.schema_dict);
            setConnInfo(prev => ({ ...prev, ...resolvedConnInfo }));
            localStorage.setItem('quantum_conninfo', JSON.stringify({ ...resolvedConnInfo }));
            localStorage.setItem('quantum_schema', JSON.stringify(res.data.schema_dict || {}));
            registerActivity();
            setIsConnected(true);
            setIsConnectionReady(true);
            setIsVerifying(false);
            if (dbSwitch) {
                setCurrentResult(null);
            } else if (!background || openShellOnSuccess) {
                openConnectedShell(resolvedConnInfo);
            }
            fetchBiPulse(resolvedConnInfo.selected_company_code || resolvedConnInfo.database);
            return res.data;
        } catch (err) {
            if (requestGeneration !== connectGenerationRef.current) {
                return null;
            }
            const shouldRetryBootstrap =
                retryOnBootstrapFailure
                && !options._bootstrapRetry
                && (err.code === 'ECONNABORTED' || !err.response);
            if (shouldRetryBootstrap) {
                await delay(BACKGROUND_CONNECT_RETRY_DELAY_MS);
                if (requestGeneration !== connectGenerationRef.current) {
                    return null;
                }
                isConnectingRef.current = false;
                return handleConnect(e, dataToUse, {
                    ...options,
                    timeoutMs: Math.max(timeoutMs, INITIAL_CONNECT_TIMEOUT_MS),
                    _bootstrapRetry: true,
                });
            }
            if (dbSwitch) {
                setConnInfo(previousConnInfo);
            }
            setIsConnectionReady(false);

            let msg = 'Error en el enlace de datos';
            if (err.code === 'ECONNABORTED') {
                msg = 'TIEMPO DE ESPERA AGOTADO: El servidor SQL es demasiado lento o el Host no responde.';
            } else {
                msg = err.response?.data?.message || err.response?.data?.detail || err.message || 'Fallo de conexión';
            }

            // Un fallo de /connect siempre es del sistema (host inalcanzable,
            // SQL lento, credenciales del servidor mal configuradas): refrescar
            // es una salida razonable.
            if (!background) {
                setError(msg);
                setErrorDeSistema(true);
            }
            throw err;
        } finally {
            // La bandera se libera siempre, sin depender de la generación: si
            // un cierre de sesión o una restauración cambia la generación a
            // mitad de una conexión, condicionarla dejaría la bandera trabada
            // en `true` y bloquearía toda conexión posterior hasta recargar.
            isConnectingRef.current = false;

            // Los estados visuales sí siguen condicionados: solo la petición más
            // reciente tiene derecho a apagar el indicador de carga, para que una
            // respuesta vieja que llega tarde no oculte el indicador de la nueva.
            if (requestGeneration === connectGenerationRef.current) {
                if (dbSwitch) {
                    setIsSwitchingDB(false);
                } else if (!background) {
                    setLoading(false);
                }
            }
        }
    };

    // Cancela la restauración de la sesión guardada y vuelve al login manual.
    const cancelSessionRestore = () => {
        connectGenerationRef.current += 1;
        isConnectingRef.current = false;
        clearPersistedSession();
        setLoading(false);
        setError(null);
        setErrorDeSistema(false);
        setIsRestoringSession(false);
        setIsVerifying(false);
        setIsConnected(false);
        setIsConnectionReady(false);
        setUserAuth(null);
        setSchema({});
        setConnInfo(defaultConnInfo);
    };

    // Cierra la sesión: avisa al backend, limpia el estado local y vuelve al
    // login mostrando el motivo, si lo hay.
    const handleLogout = async (reason = '') => {
        connectGenerationRef.current += 1;
        isConnectingRef.current = false;
        queryLock.current = false;
        setLoading(false);
        setIsRestoringSession(false);

        void apiPost('/disconnect', {}, { timeout: 800 }).catch((e) => {
            console.warn("Fallo en notificacion de logout al servidor:", e);
        });

        clearPersistedSession();
        clearDbCatalog();

        setIsConnected(false);
        setIsConnectionReady(false);
        setIsVerifying(false);
        setChatHistory([]);
        setCurrentResult(null);
        setSchema({});
        setActiveModule(null);
        setActiveSessionId(null);
        setTempCreds({ username: '', password: '' });
        setUserAuth(null);
        setConnInfo(defaultConnInfo);
        setAvailableDBs([]);

        const errorReason = (typeof reason === 'string') ? reason : null;
        setError(errorReason);
        // Cierre de sesión (voluntario o por sesión revocada). No es una avería
        // del sistema: refrescar no cambiaría nada, hay que volver a entrar.
        setErrorDeSistema(false);
        resetAppViewToDashboard();
        setActiveView('dashboard');
    };

    const [connInfo, setConnInfo] = useState(defaultConnInfo);
    const maskedHost = connInfo.host ? (showHost ? connInfo.host : '****************') : '';
    const [savedSessions, setSavedSessions] = useState(() => {
        // El historial debe estar en pantalla desde el primer render, no
        // aparecer segundos después cuando responde /api/sessions; por eso se
        // lee de forma síncrona la copia local del último usuario conocido.
        try {
            return readSessionsCache(readStoredUser()) || [];
        } catch (e) { return []; }
    });
    // Bandera para no sincronizar hacia el backend hasta haber intentado
    // hidratar primero (evita que un arreglo local vacío o desactualizado
    // sobrescriba el historial ya guardado en el servidor para este usuario).
    const sessionsHydratedRef = useRef(false);
    // Mientras es true y aún no hay sesiones locales, la barra lateral muestra
    // un esqueleto en lugar de una lista vacía, para indicar que el historial
    // se está cargando (p. ej. en el primer arranque o si el backend tarda).
    const [sessionsLoading, setSessionsLoading] = useState(true);
    // Descarga el historial desde /api/sessions, con un reintento si el
    // backend todavía está arrancando.
    const hydrateSessionHistory = async () => {
        // Diagnóstico: mide dónde se va el tiempo del historial. Visible en la
        // consola del navegador (F12 > Console, filtrar por "[Historial]").
        const t0 = performance.now();
        const cached = readSessionsCache(userAuth || readStoredUser());
        // Solo se marca "cargando" si no hay nada que mostrar todavía. Si la
        // copia local ya tiene sesiones, esta hidratación es un refresco en
        // segundo plano y el usuario no ve ningún cambio de estado.
        if (cached.length === 0) {
            setSessionsLoading(true);
        }
        console.log(`[Historial] inicio hidratacion. Cache local de este usuario: ${cached.length} sesion(es)`);
        const attemptFetch = () => apiGet('/sessions', { timeout: 8000 });
        try {
            let res;
            try {
                res = await attemptFetch();
                console.log(`[Historial] primer intento OK en ${Math.round(performance.now() - t0)}ms`);
            } catch (firstErr) {
                // El lanzador arranca backend y frontend a la vez: si la
                // aplicación se abre cuando el backend todavía está arrancando,
                // este primer intento puede fallar por conexión, no por falta de
                // datos. Un solo reintento corto (como en el login) cubre ese
                // arranque en frío sin reintentar indefinidamente.
                console.warn(`[Historial] primer intento FALLO a los ${Math.round(performance.now() - t0)}ms:`, firstErr?.message || firstErr);
                const transientFailure = firstErr?.code === 'ECONNABORTED' || !firstErr?.response;
                if (!transientFailure) throw firstErr;
                await delay(LOGIN_RETRY_DELAY_MS);
                res = await attemptFetch();
                console.log(`[Historial] reintento OK en ${Math.round(performance.now() - t0)}ms`);
            }
            const remoteSessions = Array.isArray(res.data?.sessions) ? res.data.sessions : [];
            console.log(`[Historial] respuesta del backend: ${remoteSessions.length} sesion(es), total ${Math.round(performance.now() - t0)}ms`);
            // Si el backend ya tiene historial, es la fuente de verdad. Si está
            // vacío pero el navegador tenía algo (localStorage), se conserva la
            // copia local: el siguiente efecto de guardado la sube al backend.
            if (remoteSessions.length > 0) {
                setSavedSessions(remoteSessions);
            }
        } catch (e) {
            console.warn(`[Historial] hidratacion abandonada a los ${Math.round(performance.now() - t0)}ms. Usando copia local.`, e);
        } finally {
            sessionsHydratedRef.current = true;
            setSessionsLoading(false);
        }
    };
    // Tres categorías de dispositivo (mobile, tablet, desktop). Una tableta
    // de 768-1024 px reutiliza DashboardDesktop con la barra lateral
    // colapsada por defecto, en lugar de recibir el diseño de escritorio
    // completo (barra fija de 260 px pensada para ratón) o de duplicar todo
    // el diseño.
    const [deviceType, setDeviceType] = useState(clasificarDeviceType(window.innerWidth));
    const { correct } = useAutoCorrect();

    useEffect(() => {
        const handleResize = () => setDeviceType(clasificarDeviceType(window.innerWidth));
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // En tableta, el riel lateral empieza colapsado a 64 px porque la barra
    // fija de 260 px ocupa demasiado espacio en 768-1024 px. Solo se fuerza al
    // entrar en el rango de tableta: si el usuario vuelve a abrirla, este
    // efecto no lo revierte.
    useEffect(() => {
        if (deviceType === 'tablet') setIsSidebarOpen(false);
    }, [deviceType]);
    // Sincroniza la vista activa con el hash de la URL.
    useEffect(() => {
        const handleHashChange = () => setActiveView(readAppView());
        window.addEventListener('hashchange', handleHashChange);
        return () => window.removeEventListener('hashchange', handleHashChange);
    }, []);
    const chatEndRef = useRef(null);
    const textareaRef = useRef(null);
    const queryLock = useRef(false);
    const abortoConsultaRef = useRef(null);
    const motivoCorteRef = useRef(null);
    const isConnectingRef = useRef(false);
    const connectGenerationRef = useRef(0);
    const lastActivityRef = useRef(Date.now());
    const autoLogoutRef = useRef(false);
    const fileInputRef = useRef(null);
    // Referencia para deduplicar fetchBiPulse: evita una doble petición cuando
    // handleConnect y el useEffect lo invocan casi a la vez para la misma base.
    const biPulseFetchingRef = useRef('');

    // Obtiene el pulso del tablero BI (/bi/pulse) para la base indicada o la activa.
    const fetchBiPulse = async (targetDb = '') => {
        const normalizedTargetDb = String(targetDb || connInfo.selected_company_code || connInfo.database || '').trim().toUpperCase();
        if (!normalizedTargetDb) return;
        // Deduplicación: si ya hay una petición en curso para esta base, no se lanza otra.
        if (biPulseFetchingRef.current === normalizedTargetDb) return;
        biPulseFetchingRef.current = normalizedTargetDb;
        try {
            const suffix = `?target_db=${encodeURIComponent(normalizedTargetDb)}`;
            const res = await apiGet(`/bi/pulse${suffix}`);
            if (res.data?.status === 'ok') {
                setBiPulse(res.data);
                console.log("[BI] Pulso sincronizado:", normalizedTargetDb);
            }
        } catch (e) {
            console.warn("[BI] No se pudo sincronizar el pulso:", e);
            biPulseFetchingRef.current = ''; // se libera en error para permitir el reintento
        } finally {
            // Se limpia solo si nadie cambió la referencia durante la espera.
            if (biPulseFetchingRef.current === normalizedTargetDb) {
                biPulseFetchingRef.current = '';
            }
        }
    };

    // Precalentamiento: sondea /api/health cada segundo hasta que el backend
    // responde "online".
    useEffect(() => {
        let cancelled = false;
        let timerId = null;

        const pollBackendReadiness = async () => {
            const health = await probeBackendHealth();
            if (cancelled) return;

            const ready = health?.status === 'online';
            if (!ready) {
                timerId = window.setTimeout(pollBackendReadiness, 1000);
            }
        };

        void pollBackendReadiness();

        return () => {
            cancelled = true;
            if (timerId) window.clearTimeout(timerId);
        };
    }, []);

    // Restaura la sesión guardada al cargar la página, salvo que haya expirado
    // por inactividad o por el vencimiento del JWT.
    useEffect(() => {
        const token = localStorage.getItem('quantum_token');
        const savedUser = localStorage.getItem('quantum_user');
        const savedConn = localStorage.getItem('quantum_conninfo');
        const savedSchema = localStorage.getItem('quantum_schema');

        if (!token || !savedUser || !savedConn) return;

        const now = Date.now();
        const storedActivity = Number(localStorage.getItem(SESSION_ACTIVITY_KEY) || '0');
        const tokenExpiryMs = parseJwtExpiryMs(token);
        if ((storedActivity && now - storedActivity >= SESSION_IDLE_TIMEOUT_MS) || (tokenExpiryMs > 0 && now >= tokenExpiryMs)) {
            clearPersistedSession();
            setUserAuth(null);
            setConnInfo(defaultConnInfo);
            setSchema({});
            setIsConnected(false);
            setIsConnectionReady(false);
            return;
        }
        if (storedActivity > 0) {
            lastActivityRef.current = storedActivity;
        }

        try {
            const parsedUser = JSON.parse(savedUser);
            const parsedConn = JSON.parse(savedConn);
            const parsedSchema = savedSchema ? JSON.parse(savedSchema) : {};

            setUserAuth(parsedUser);
            setConnInfo(prev => ({ ...prev, ...parsedConn }));
            setSchema(parsedSchema || {});
            openConnectedShell(parsedConn);
            void hydrateSessionHistory();
            void handleConnect(null, parsedConn, {
                background: true,
                openShellOnSuccess: false,
                timeoutMs: INITIAL_CONNECT_TIMEOUT_MS
            }).catch((err) => {
                console.warn("Restauración de sesión persistente expirada o fallida.", err);
                setIsConnectionReady(false);
                setIsVerifying(false);
                setLoading(false);
                setError('No se pudo restaurar la conexion SQL. Ajusta el servidor desde Origenes de Datos.');
                setErrorDeSistema(true);
            });
        } catch (err) {
            console.warn("No se pudo reconstruir la sesión local:", err);
            clearPersistedSession();
            setUserAuth(null);
            setConnInfo(defaultConnInfo);
            setSchema({});
            setIsRestoringSession(false);
            setIsVerifying(false);
        }
    }, []);

    // Cualquier interacción del usuario renueva el registro de actividad.
    useEffect(() => {
        const syncActivity = () => {
            const token = localStorage.getItem('quantum_token');
            if (!token) return;
            registerActivity();
        };

        const events = ['mousedown', 'keydown', 'touchstart', 'scroll'];
        events.forEach((eventName) => window.addEventListener(eventName, syncActivity, { passive: true }));
        return () => {
            events.forEach((eventName) => window.removeEventListener(eventName, syncActivity));
        };
    }, []);

    // Cada 15 s revisa si la sesión expiró por inactividad o por el JWT y, si
    // es así, la cierra con el motivo correspondiente.
    useEffect(() => {
        const checkSessionFreshness = () => {
            const token = localStorage.getItem('quantum_token');
            if (!token || autoLogoutRef.current) return;

            const storedActivity = Number(localStorage.getItem(SESSION_ACTIVITY_KEY) || '0');
            if (storedActivity > 0) {
                lastActivityRef.current = Math.max(lastActivityRef.current, storedActivity);
            }

            const now = Date.now();
            const tokenExpiryMs = parseJwtExpiryMs(token);
            const idleExpired = now - lastActivityRef.current >= SESSION_IDLE_TIMEOUT_MS;
            const tokenExpired = tokenExpiryMs > 0 && now >= tokenExpiryMs;

            if (!idleExpired && !tokenExpired) return;

            autoLogoutRef.current = true;
            const reason = tokenExpired
                ? 'Sesion expirada. Vuelve a ingresar.'
                : 'Sesion cerrada por inactividad. Vuelve a ingresar.';
            void handleLogout(reason).finally(() => {
                autoLogoutRef.current = false;
            });
        };

        const intervalId = window.setInterval(checkSessionFreshness, SESSION_CHECK_INTERVAL_MS);
        return () => {
            window.clearInterval(intervalId);
        };
    }, []);

    useEffect(() => {
        writeSessionsCache(userAuth || readStoredUser(), savedSessions);
        // La copia local es la caché sin conexión. La fuente de verdad es el
        // backend, pero solo se sincroniza después de un intento de hidratación
        // (ver hydrateSessionHistory) para no sobrescribir el historial del
        // servidor con un arreglo local vacío o desactualizado.
        if (sessionsHydratedRef.current) {
            void apiPut('/sessions', { sessions: savedSessions }).catch((e) => {
                console.warn('No se pudo sincronizar el historial de sesiones con el backend. Se mantiene solo local.', e);
            });
        }
    }, [savedSessions]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory]);

    // El textarea no se redimensiona solo: tiene altura fija (rows="1") y se
    // desplaza internamente, sea cual sea el motor de IA seleccionado.

    useEffect(() => {
        // `userAuth` es la guarda: evita llamar a /databases sin un token
        // válido si `isConnected` e `isConnectionReady` llegan a true antes de
        // que exista el usuario verificado.
        if (isConnected && isConnectionReady && userAuth && connInfo.host) loadDatabases();
    }, [isConnected, isConnectionReady, userAuth, connInfo.host]);

    useEffect(() => {
        if (!isConnected || !isConnectionReady || !userAuth) return;
        const targetDb = String(connInfo.selected_company_code || connInfo.database || '').trim().toUpperCase();
        if (!targetDb) return;
        // Si handleConnect ya pidió esta misma base, la deduplicación evita la segunda petición.
        fetchBiPulse(targetDb);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isConnected, isConnectionReady, userAuth, connInfo.database, connInfo.selected_company_code]);

    // Cierra el menú de una sesión al hacer clic fuera de él.
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuOpenId && !event.target.closest('.session-menu-trigger')) {
                setMenuOpenId(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [menuOpenId]);

    // Prefijo "MONT - ", "DAUN - "... en el título del historial reciente.
    // Se toma el código de empresa vigente EN EL MOMENTO de crear la sesión y
    // se guarda dentro del propio objeto (`companyCode`), no se relee de
    // connInfo en cada render: si el título dependiera del connInfo actual,
    // una conversación de MONT pasaría a mostrar "DAUN - ..." en cuanto el
    // usuario cambiara de empresa, aunque esa conversación siga siendo la de
    // MONT. El código queda fijo desde su creación, como el resto del historial.
    const prefijoEmpresa = (texto) => {
        const codigo = String(connInfo?.selected_company_code || '').trim().toUpperCase();
        return codigo ? `${codigo} - ${texto}` : texto;
    };

    // Autoguardado: actualiza la sesión activa o, si no hay, crea una nueva
    // con el primer mensaje del usuario (se conservan las 20 más recientes).
    useEffect(() => {
        const hasUserMessage = chatHistory.some(m => m.type === 'user');
        if (!hasUserMessage) return;
        if (activeSessionId) {
            setSavedSessions(prev => prev.map(s => {
                if (s.id === activeSessionId) {
                    const firstUserMsg = chatHistory.find(m => m.type === 'user')?.content?.slice(0, 30);
                    // companyCode ya fijado al crear la sesión: se respeta tal
                    // cual aunque el usuario haya cambiado de empresa después.
                    const codigo = s.companyCode || '';
                    const nombrePrefijado = firstUserMsg
                        ? (codigo ? `${codigo} - ${firstUserMsg}` : firstUserMsg)
                        : null;
                    const newName = (s.name === "Consulta de Datos" && nombrePrefijado) ? nombrePrefijado : s.name;
                    return { ...s, history: chatHistory, result: currentResult, name: newName };
                }
                return s;
            }));
        } else {
            const firstUserMsg = chatHistory.find(m => m.type === 'user')?.content?.slice(0, 30);
            const newSessionId = Date.now();
            const companyCode = String(connInfo?.selected_company_code || '').trim().toUpperCase();
            const newSession = {
                id: newSessionId,
                name: firstUserMsg ? prefijoEmpresa(firstUserMsg) : firstUserMsg,
                companyCode,
                history: chatHistory,
                result: currentResult,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                pinned: false
            };
            setSavedSessions(prev => [newSession, ...prev.slice(0, 19)]);
            setActiveSessionId(newSessionId);
        }
    }, [chatHistory, currentResult]);

    // Empieza una conversación vacía en la base actual.
    const startNewChat = () => {
        setChatHistory([{
            id: `welcome-${Date.now()}`,
            type: 'ai',
            isWelcome: true,
            dbName: connInfo.database === 'LOCAL_FILE' ? 'quantum_data.db' : dbToBusinessName(connInfo.database),
            content: ``,
            quickQuestions: [],
            timestamp: new Date().toLocaleTimeString()
        }]);
        setCurrentResult(null);
        setActiveModule(null);
        setPrompt('');
        setActiveSessionId(null);
        setMenuOpenId(null);
    };

    // Abre la vista Quantum Core (#/quantum-core) en la misma pestaña o en una nueva.
    const openQuantumCore = (newTab = false) => {
        if (typeof window === 'undefined') return;
        const targetUrl = `${window.location.pathname}${window.location.search}#/quantum-core`;
        if (newTab) {
            window.open(targetUrl, '_blank', 'noopener,noreferrer');
            return;
        }
        window.location.hash = '/quantum-core';
        setActiveView('quantum-core');
    };

    const returnToDashboard = () => {
        if (typeof window === 'undefined') return;
        window.location.hash = '';
        setActiveView('dashboard');
    };

    // Carga una sesión guardada: primero vacía el chat y espera dos cuadros de
    // animación para que el historial se vuelva a montar desde cero.
    const loadSession = (session) => {
        setChatHistory([]);
        setCurrentResult(null);
        setActiveSessionId(null);
        setMenuOpenId(null);
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                setChatHistory(session.history || []);
                setCurrentResult(session.result || null);
                setActiveSessionId(session.id);
            });
        });
    };

    // Acciones del menú de cada sesión: fijar, eliminar, renombrar y guardar el nombre.
    const togglePinSession = (e, sessionId) => {
        e.stopPropagation();
        setSavedSessions(savedSessions.map(s => s.id === sessionId ? { ...s, pinned: !s.pinned } : s));
        setMenuOpenId(null);
    };

    const deleteSession = (e, sessionId) => {
        e.stopPropagation();
        setSavedSessions(prev => prev.filter(s => s.id !== sessionId));
        if (activeSessionId === sessionId) {
            setActiveSessionId(null);
            setChatHistory([]);
            setCurrentResult(null);
            setActiveModule(null);
            setPrompt('');
        }
        setMenuOpenId(null);
    };

    const renameSession = (e, sessionId) => {
        e.stopPropagation();
        setEditingId(sessionId);
        const session = savedSessions.find(s => s.id === sessionId);
        setTempSessionName(session.name);
        setMenuOpenId(null);
    };

    const saveNewName = (e, sessionId) => {
        e.stopPropagation();
        setSavedSessions(savedSessions.map(s => s.id === sessionId ? { ...s, name: tempSessionName } : s));
        setEditingId(null);
    };

    // Las sesiones fijadas van primero.
    const sortedSessions = useMemo(() => {
        return [...savedSessions].sort((a, b) => {
            if (a.pinned === b.pinned) return 0;
            return a.pinned ? -1 : 1;
        });
    }, [savedSessions]);

    // Módulos de análisis; cada base habilita algunos según su perfil (getDbModules).
    const capabilities = [
        { id: "VENTAS", label: "Área Comercial", desc: "Ventas y Facturación", icon: TrendingUp },
        { id: "OPERACIONES", label: "Gestión de Abastecimiento", desc: "Gestión de Proveedores", icon: Box },
        { id: "RRHH", label: "Capital Humano", desc: "Fichas de Personal & Roles", icon: Users },
        { id: "FINANZAS", label: "Contabilidad", desc: "Balances y Auditoría", icon: Layout },
        { id: "ACADEMICO", label: "Analitica Academica", desc: "Alumnos, Matriculas y Cursos", icon: GraduationCap }
    ];

    // Módulos visibles: los de la base activa; GERENTE_GENERAL y ADMINISTRADOR
    // ven todos, el resto solo los asignados a su usuario.
    const activeCapabilities = useMemo(() => {
        if (!userAuth) return [];
        const displayDbCode = connInfo.selected_company_code || connInfo.database;
        const dbModuleSet = new Set(getDbModules(displayDbCode));
        const byDb = capabilities.filter(cap => dbModuleSet.has(cap.id));
        if (['GERENTE_GENERAL', 'ADMINISTRADOR'].includes(userAuth.role)) return byDb;
        return byDb.filter(cap => userAuth.modules?.includes(cap.id));
    }, [userAuth, connInfo.database, connInfo.selected_company_code]);

    // Si la base activa no ofrece el módulo seleccionado, se deselecciona.
    useEffect(() => {
        if (!activeModule) return;
        const displayDbCode = connInfo.selected_company_code || connInfo.database;
        const dbModuleSet = new Set(getDbModules(displayDbCode));
        if (!dbModuleSet.has(activeModule)) {
            setActiveModule(null);
        }
    }, [activeModule, connInfo.database, connInfo.selected_company_code]);

    // Lista las bases del servidor SQL (/databases) y actualiza el catálogo local.
    const loadDatabases = async (overrideConnInfo = null) => {
        const sourceConnInfo = overrideConnInfo ? { ...connInfo, ...overrideConnInfo } : connInfo;
        const normalizedConnInfo = {
            ...sourceConnInfo,
            host: normalizeSqlServerHost(sourceConnInfo.host),
            database: String(sourceConnInfo.database || '').trim(),
        };
        if (!normalizedConnInfo.host) return;
        setFetchingDBs(true);
        try {
            const res = await apiPost('/databases', {
                host: normalizedConnInfo.host,
                auth_type: normalizedConnInfo.auth_type,
                driver: normalizedConnInfo.driver,
                user: normalizedConnInfo.user,
                password: normalizedConnInfo.password
            });
            if (Array.isArray(res.data?.database_catalog) && res.data.database_catalog.length > 0) {
                mergeDbCatalog(res.data.database_catalog);
            }
            const dbs = Array.isArray(res.data?.database_catalog) && res.data.database_catalog.length > 0
                ? Array.from(new Set(
                    res.data.database_catalog
                        .map((entry) => String(entry.database || '').trim().toUpperCase())
                        .filter(Boolean)
                ))
                : (res.data.databases || []);
            setAvailableDBs(dbs);

        } catch (e) {
            console.error(e);
        } finally {
            setFetchingDBs(false);
        }
    };

    // Envía la pregunta del usuario: con imágenes adjuntas va a /query/vision;
    // si no, a /query/stream, con respuesta en streaming (SSE).
    // `options.skipUserBubble`: usado por "Regenerar respuesta" (ChatMessage.jsx)
    // para reenviar la misma pregunta al backend sin duplicar la burbuja de
    // usuario que ya está en pantalla — solo se reemplaza la respuesta.
    const handleQuery = async (e, forcedPrompt = null, options = {}) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        if (queryLock.current) return;

        const { skipUserBubble = false } = options;
        const finalInput = forcedPrompt || prompt;
        // Con imágenes adjuntas se puede enviar sin texto (el backend usa una
        // pregunta genérica de análisis si el prompt viene vacío).
        const tieneImagenesAdjuntas = Array.isArray(attachedImages) && attachedImages.length > 0;
        if (!finalInput.trim() && !tieneImagenesAdjuntas) return;

        const isGreeting = (text) => {
            const cleaned = (text || "").toLowerCase().trim().replace(/[!?.,¿]/g, "");
            const words = cleaned.split(/\s+/).filter(Boolean);
            const greetingWords = ["hola", "buenos", "dias", "tardes", "noches", "hi", "hello", "ey", "saludos", "que", "tal", "como", "estas", "aura"];
            if (words.length <= 5 && words.some(w => greetingWords.includes(w))) return true;
            return false;
        };

        // Si la conexión no está lista y el texto no es un saludo corto, se
        // bloquea la consulta para evitar errores de SQL sin esquema.
        if (!isConnectionReady && !isGreeting(finalInput)) {
            setChatHistory(prev => [...prev, {
                id: `ai-sync-${Date.now()}`,
                type: 'ai',
                content: 'Sigo sincronizando la base activa para procesar datos complejos. Espera unos segundos e intenta de nuevo.',
                isError: true,
                timestamp: new Date().toLocaleTimeString()
            }]);
            return;
        }

        queryLock.current = true;

        // Al regenerar no se vuelve a pasar por el autocorrector ni se toca
        // el input: el texto ya fue aceptado la primera vez que se envió.
        const { text: finalPrompt } = skipUserBubble ? { text: finalInput } : correct(finalInput);
        registerActivity();

        // Se capturan antes de limpiar el estado: `attachedImages` se vacía
        // más abajo para que la miniatura desaparezca del input en cuanto se
        // envía, pero la petición necesita las imágenes que había en ese momento.
        const imagenesAEnviar = tieneImagenesAdjuntas ? [...attachedImages] : [];

        if (!skipUserBubble) {
            const userMsg = {
                id: `user-${Date.now()}`,
                type: 'user',
                content: finalPrompt,
                originalContent: finalInput !== finalPrompt ? finalInput : null,
                images: imagenesAEnviar.length > 0 ? imagenesAEnviar.map(img => img.dataUrl) : undefined,
                timestamp: new Date().toLocaleTimeString()
            };
            setChatHistory(prev => [...prev, userMsg]);
            setPrompt('');
            setCorrectionHint(null);
        }
        if (imagenesAEnviar.length > 0) setAttachedImages([]);
        setLoading(true);

        // ID de la burbuja de respuesta (se crea antes de recibir datos).
        const aiMsgId = `ai-res-${Date.now()}`;

        // Burbuja de "escribiendo..." mientras responde el modelo.
        setChatHistory(prev => [...prev, {
            id: aiMsgId,
            type: 'ai',
            content: '',
            isStreaming: true,
            result: null,
            motor: motorIA || 'flash',
            timestamp: new Date().toLocaleTimeString(),
        }]);
        setStreamingMsgId(aiMsgId);

        // Rama de visión: con imágenes adjuntas, la pregunta no pasa por
        // /query/stream (SQL, esquema, caché semántica, control de alcance):
        // va directo al modelo de visión por un endpoint propio, sin streaming,
        // porque la respuesta suele ser un párrafo.
        if (imagenesAEnviar.length > 0) {
            try {
                const token = localStorage.getItem('quantum_token');
                const selectedCompanyCode = String(connInfo.selected_company_code || '').trim().toUpperCase();
                const selectedCompanyProfile = selectedCompanyCode ? getDbProfile(selectedCompanyCode) : null;

                const resp = await fetch(`${API_BASE}/query/vision`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    },
                    body: JSON.stringify({
                        prompt: finalPrompt,
                        images: imagenesAEnviar.map(img => img.dataUrl),
                        selected_company_code: selectedCompanyCode,
                        selected_company_name: selectedCompanyProfile?.business_name || '',
                    }),
                });

                if (!resp.ok) {
                    let detalle = '';
                    try { detalle = (await resp.json())?.detail || ''; } catch (_) { /* sin body JSON */ }
                    throw new Error(detalle || 'No se pudo analizar la imagen. Intenta de nuevo.');
                }

                const data = await resp.json();
                setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                    ...m,
                    content: data.explanation || 'No pude extraer información útil de la imagen.',
                    agent_log: data.agent_log,
                    isStreaming: false,
                    isError: data.status === 'error',
                } : m));
            } catch (err) {
                console.error('Vision error:', err);
                setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                    ...m,
                    content: err.message || 'No pude analizar la imagen. Intenta de nuevo.',
                    isStreaming: false,
                    isError: true,
                } : m));
            } finally {
                setStreamingMsgId(null);
                setLoading(false);
                queryLock.current = false;
            }
            return;
        }

        try {
            const recentHistory = chatHistory.slice(-4).map(msg => ({ type: msg.type, content: msg.content }));
            const selectedCompanyCode = String(connInfo.selected_company_code || '').trim().toUpperCase();
            const selectedCompanyProfile = selectedCompanyCode ? getDbProfile(selectedCompanyCode) : null;

            const token = localStorage.getItem('quantum_token');
            const streamUrl = `${API_BASE}/query/stream`;

            // Vigilancia de tiempo: sin límite, si el servidor SQL o el motor de
            // IA se quedan colgados, la pantalla giraría indefinidamente. Se
            // aplican dos cortes:
            //   · inactividad: no llega nada nuevo en 150 s. El rewrite de
            //     Firebase Hosting retiene la respuesta SSE completa, así que
            //     una pregunta que DeepSeek (Flash/Pro) tarda en responder
            //     (40-125 s en frío) no envía ni un byte hasta terminar; un
            //     corte más corto haría que esos motores nunca respondieran.
            //   · tope total: 5 minutos, en línea con el timeout del backend
            //     (Cloud Run corta a los 300 s).
            const INACTIVIDAD_MS = 150000;
            const TOPE_TOTAL_MS = 300000;
            const abortoConsulta = new AbortController();
            abortoConsultaRef.current = abortoConsulta;
            motivoCorteRef.current = null;
            let ultimaSenal = Date.now();
            let motivoCorte = null;

            const vigilanteInactividad = setInterval(() => {
                if (Date.now() - ultimaSenal > INACTIVIDAD_MS) {
                    motivoCorte = 'inactividad';
                    abortoConsulta.abort();
                }
            }, 3000);
            const vigilanteTope = setTimeout(() => {
                motivoCorte = 'tope';
                abortoConsulta.abort();
            }, TOPE_TOTAL_MS);
            const limpiarVigilantes = () => {
                clearInterval(vigilanteInactividad);
                clearTimeout(vigilanteTope);
            };

            const response = await fetch(streamUrl, {
                method: 'POST',
                signal: abortoConsulta.signal,
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    prompt: finalPrompt,
                    conn_str: connInfo.host,
                    api_key: connInfo.api_key,
                    module: activeModule,
                    history: recentHistory,
                    selected_company_code: selectedCompanyCode,
                    selected_company_name: selectedCompanyProfile?.business_name || '',
                    selected_company_short_name: selectedCompanyProfile?.short_name || '',
                    bi_context: biPulse,
                    motor_ia: motorIA,
                }),
            });

            if (!response.ok) {
                limpiarVigilantes();
                // Se intenta leer el mensaje del backend, si existe.
                let backendDetail = '';
                try {
                    const errBody = await response.json();
                    backendDetail = errBody?.detail || errBody?.message || '';
                } catch (_) { /* no hay body JSON */ }

                if (response.status === 400) {
                    throw new Error(
                        '⚠️ Este servidor no cuenta con el módulo de inteligencia activado. ' +
                        'Por favor, selecciona un servidor compatible desde **Bases de Datos** e intenta nuevamente.'
                    );
                } else if (response.status === 401 || response.status === 403) {
                    throw new Error('Tu sesión ha expirado. Por favor, vuelve a iniciar sesión.');
                } else if (response.status === 503 || response.status === 502) {
                    throw new Error('El servicio no está disponible en este momento. Intenta nuevamente en unos segundos.');
                } else {
                    throw new Error(
                        backendDetail ||
                        'No fue posible procesar tu consulta. Verifica tu conexión e intenta de nuevo.'
                    );
                }
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let metaPayload = null;
            let explanation = '';

            // Filtro de contenido técnico: si el texto parece un error de base de
            // datos, una traza de Python o SQL, no se muestra al usuario.
            const TECHNICAL_PATTERNS = [
                /pyodbc\./i, /\[Microsoft\]\[ODBC/i, /\[SQL Server\]/i,
                /SQLExecDirectW/i, /ProgrammingError/i, /OperationalError/i,
                /Traceback \(most recent call/i, /File ".*\.py"/i,
                /sqlalchemy\./i, /INNER JOIN.*ON.*=/i, /SELECT.*FROM.*WHERE/i, /WITH.*AS\s*\(/i,
            ];
            const containsTech = (t) => TECHNICAL_PATTERNS.some(p => p.test(t));

            let finalizadoPorServidor = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                // Cada trozo recibido reinicia el reloj de inactividad.
                ultimaSenal = Date.now();

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // se guarda la línea incompleta

                let currentEvent = '';
                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        currentEvent = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6).trim();
                        try {
                            const parsed = JSON.parse(dataStr);

                            if (currentEvent === 'meta') {
                                metaPayload = parsed;
                                const normalized = normalizeQueryResult(parsed);
                                // Los datos (tabla o gráfico) se muestran de inmediato, antes del texto.
                                setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                                    ...m,
                                    content: '',
                                    result: { ...normalized, user_viz_override: null },
                                    dbName: connInfo.database === 'LOCAL_FILE' ? 'quantum_data.db' : dbToBusinessName(connInfo.database),
                                    agent_log: normalized.agent_log,
                                    activeTab: 'Resultados',
                                    isStreaming: true,
                                    quickQuestions: parsed?.quick_questions || [],
                                } : m));

                            } else if (currentEvent === 'token') {
                                // Se agrega el fragmento al texto en curso.
                                explanation += parsed;
                                const sanitized = containsTech(explanation) ? '' : explanation;
                                setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                                    ...m,
                                    content: sanitized,
                                    isStreaming: true,
                                } : m));

                            } else if (currentEvent === 'done') {
                                // Se cierra la burbuja.
                                finalizadoPorServidor = true;
                                setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                                    ...m,
                                    content: explanation && !containsTech(explanation)
                                        ? explanation
                                        : (metaPayload?.explanation || 'Análisis completado.'),
                                    isStreaming: false,
                                    // Preguntas rápidas que el backend adjuntó en el evento
                                    // "meta" (p. ej. las opciones de Invitado: demo, solicitar
                                    // acceso, conectar BD). Se toman de metaPayload para no
                                    // perderlas al cerrar la burbuja.
                                    quickQuestions: metaPayload?.quick_questions || [],
                                } : m));
                                setStreamingMsgId(null);

                            } else if (currentEvent === 'error') {
                                finalizadoPorServidor = true;
                                const errMsg = parsed?.message || 'Error al procesar la consulta.';
                                setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                                    ...m,
                                    content: errMsg,
                                    isStreaming: false,
                                    isError: true,
                                } : m));
                                setStreamingMsgId(null);
                            }
                        } catch (_parseErr) { /* se ignoran las líneas malformadas */ }
                    }
                }
            }

            limpiarVigilantes();

            // El stream terminó sin que el servidor enviara 'done' ni 'error':
            // la burbuja quedaría "escribiendo…" para siempre. Se cierra con un
            // mensaje entendible en vez de dejarla girando.
            if (!finalizadoPorServidor) {
                setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                    ...m,
                    content: explanation && !containsTech(explanation)
                        ? explanation
                        : 'La conexión con el servidor se interrumpió antes de completar la respuesta. Vuelve a intentarlo.',
                    isStreaming: false,
                    isError: !explanation,
                } : m));
                setStreamingMsgId(null);
            }

        } catch (err) {
            console.error('Stream error:', err);
            try { limpiarVigilantes(); } catch (_) { /* ya limpiados */ }

            let backendMessage;
            if (err.name === 'AbortError') {
                // Respuesta de contingencia, no un error técnico plano: si el
                // modelo no responde a tiempo (o el usuario cancela), el propio
                // sistema explica qué pasó y propone una siguiente acción.
                const motivo = motivoCorteRef.current || motivoCorte;
                backendMessage = motivo === 'cancelado'
                    ? 'Consulta cancelada.\n\n'
                      + 'Detuve el análisis en cuanto lo pediste. Puedes escribir una nueva pregunta '
                      + 'o reformular esta con un alcance más concreto.'
                    : motivo === 'tope'
                    ? 'Esta consulta superó los 5 minutos y se detuvo.\n\n'
                      + 'Suele pasar cuando la pregunta abarca demasiada información. '
                      + 'Prueba acotarla, por ejemplo indicando un año o un mes concreto.'
                    : 'No logré completar el análisis en el tiempo esperado (más de 2 minutos sin respuesta del servidor).\n\n'
                      + 'Esto suele pasar cuando la pregunta requiere cruzar mucha información o el motor de IA '
                      + 'está tardando más de lo normal — no significa que no haya datos.\n\n'
                      + 'Prueba acotando el período (por ejemplo un mes o trimestre específico) o vuelve a '
                      + 'intentar la misma pregunta: si el análisis ya quedó calculado, la respuesta puede '
                      + 'llegar de inmediato en el siguiente intento.';
            } else {
                backendMessage = err.message
                    || 'No pude procesar esa consulta. Intenta reformular la pregunta.';
            }

            setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                ...m,
                content: backendMessage,
                isStreaming: false,
                isError: true,
            } : m));
            setStreamingMsgId(null);
        } finally {
            abortoConsultaRef.current = null;
            motivoCorteRef.current = null;
            setLoading(false);
            queryLock.current = false;
        }
    };

    // Cancela la consulta en curso (botón del indicador de carga). Aborta el
    // AbortController activo, lo que dispara el AbortError y cierra la burbuja
    // con un mensaje de "Consulta cancelada" en lugar de dejarla girando.
    const cancelQuery = () => {
        motivoCorteRef.current = 'cancelado';
        if (abortoConsultaRef.current) {
            abortoConsultaRef.current.abort();
        }
    };

    // Sin conexión se muestra el login; con conexión, el tablero móvil o el de
    // escritorio (que también atiende tabletas).
    if (!isConnected) {
        return (
            <LoginView
                isConnected={isConnected}
                loading={loading}
                authPending={authPending}
                isVerifying={isVerifying}
                isRestoringSession={isRestoringSession}
                showAdvanced={showAdvanced}
                showDevOptions={showDevOptions}
                error={error}
                errorDeSistema={errorDeSistema}
                tempCreds={tempCreds}
                setTempCreds={setTempCreds}
                showPassword={showPassword}
                setShowPassword={setShowPassword}
                handleAuthLogin={handleAuthLogin}
                handleConnect={handleConnect}
                cancelSessionRestore={cancelSessionRestore}
                setIsVerifying={setIsVerifying}
                setError={setError}
                setShowAdvanced={setShowAdvanced}
                handleTitleClick={handleTitleClick}
                maskedHost={maskedHost}
                showHost={showHost}
                setShowHost={setShowHost}
                connInfo={connInfo}
                setConnInfo={setConnInfo}
            />
        );
    }

    return (
        <React.Suspense fallback={<div className="h-screen w-screen bg-[#020617] flex items-center justify-center font-black text-cyan-500 uppercase tracking-widest animate-pulse">Sincronizando...</div>}>
            {deviceType === 'mobile' ? (
                <DashboardMobile
                    isSidebarOpen={isSidebarOpen}
                    setIsSidebarOpen={setIsSidebarOpen}
                    chatHistory={chatHistory}
                    setChatHistory={setChatHistory}
                    deviceType={deviceType}
                    userAuth={userAuth}
                    activeModule={activeModule}
                    setActiveModule={setActiveModule}
                    connInfo={connInfo}
                    setConnInfo={setConnInfo}
                    availableDBs={availableDBs}
                    fetchingDBs={fetchingDBs}
                    loadDatabases={loadDatabases}
                    handleConnect={handleConnect}
                    loading={loading}
                    isConnectionReady={isConnectionReady}
                    prompt={prompt}
                    setPrompt={setPrompt}
                    motorIA={motorIA}
                    setMotorIA={setMotorIA}
                    handleQuery={handleQuery}
                    cancelQuery={cancelQuery}
                    correctionHint={correctionHint}
                    correct={correct}
                    setCorrectionHint={setCorrectionHint}
                    textareaRef={textareaRef}
                    chatEndRef={chatEndRef}
                    schema={schema}
                    activeCapabilities={activeCapabilities}
                    activeSessionId={activeSessionId}
                    sortedSessions={sortedSessions}
                    sessionsLoading={sessionsLoading}
                    menuOpenId={menuOpenId}
                    setMenuOpenId={setMenuOpenId}
                    editingId={editingId}
                    setEditingId={setEditingId}
                    tempSessionName={tempSessionName}
                    setTempSessionName={setTempSessionName}
                    startNewChat={startNewChat}
                    loadSession={loadSession}
                    togglePinSession={togglePinSession}
                    renameSession={renameSession}
                    saveNewName={saveNewName}
                    deleteSession={deleteSession}
                    showHost={showHost}
                    setShowHost={setShowHost}
                    maskedHost={maskedHost}
                    setIsConnected={setIsConnected}
                    setSchema={setSchema}
                    setTempCreds={setTempCreds}
                    setUserAuth={setUserAuth}
                    isConnectingRef={isConnectingRef}
                    handleLogout={handleLogout}
                    biPulse={biPulse}
                />
            ) : (
                <DashboardDesktop
                    isSidebarOpen={isSidebarOpen}
                    setIsSidebarOpen={setIsSidebarOpen}
                    chatHistory={chatHistory}
                    setChatHistory={setChatHistory}
                    deviceType={deviceType}
                    userAuth={userAuth}
                    activeModule={activeModule}
                    setActiveModule={setActiveModule}
                    connInfo={connInfo}
                    setConnInfo={setConnInfo}
                    availableDBs={availableDBs}
                    fetchingDBs={fetchingDBs}
                    loadDatabases={loadDatabases}
                    handleConnect={handleConnect}
                    loading={loading}
                    isConnectionReady={isConnectionReady}
                    prompt={prompt}
                    setPrompt={setPrompt}
                    motorIA={motorIA}
                    setMotorIA={setMotorIA}
                    handleQuery={handleQuery}
                    cancelQuery={cancelQuery}
                    correctionHint={correctionHint}
                    correct={correct}
                    setCorrectionHint={setCorrectionHint}
                    textareaRef={textareaRef}
                    chatEndRef={chatEndRef}
                    schema={schema}
                    activeCapabilities={activeCapabilities}
                    activeSessionId={activeSessionId}
                    sortedSessions={sortedSessions}
                    sessionsLoading={sessionsLoading}
                    menuOpenId={menuOpenId}
                    setMenuOpenId={setMenuOpenId}
                    editingId={editingId}
                    setEditingId={setEditingId}
                    tempSessionName={tempSessionName}
                    setTempSessionName={setTempSessionName}
                    startNewChat={startNewChat}
                    loadSession={loadSession}
                    togglePinSession={togglePinSession}
                    renameSession={renameSession}
                    saveNewName={saveNewName}
                    deleteSession={deleteSession}
                    showHost={showHost}
                    setShowHost={setShowHost}
                    maskedHost={maskedHost}
                    setIsConnected={setIsConnected}
                    setSchema={setSchema}
                    setTempCreds={setTempCreds}
                    setUserAuth={setUserAuth}
                    isConnectingRef={isConnectingRef}
                    handleLogout={handleLogout}
                    openQuantumCore={openQuantumCore}
                    biPulse={biPulse}
                    attachedImages={attachedImages}
                    setAttachedImages={setAttachedImages}
                />
            )}
        </React.Suspense>
    );
}

/**
 * Componente raíz de la aplicación: envuelve AppInner en un ErrorBoundary.
 * @returns {JSX.Element} Aplicación completa.
 */
export default function App() {
    return (
        <ErrorBoundary>
            <AppInner />
        </ErrorBoundary>
    );
}
