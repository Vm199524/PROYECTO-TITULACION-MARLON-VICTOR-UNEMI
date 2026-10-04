import React, { useState, useEffect, useRef, useMemo } from 'react';
import * as Sentry from "@sentry/react";
import { Box, GraduationCap, Layout, TrendingUp, Users } from 'lucide-react';

/**
 * Archivo: App.jsx
 * Rol: contenedor principal del frontend y centro de estado global.
 * Recibe desde: main.jsx.
 * Se conecta con: services/api.js, Login.jsx, DashboardDesktop.jsx,
 * DashboardMobile.jsx, appConfig.js y queryResult.js.
 * Responsabilidades: auth, conexion, chat, sesiones y cambio de vistas.
 */

import { useAutoCorrect } from './hooks/useAutoCorrect';
import { apiGet, apiPost, apiPut } from './services/api';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LoginView } from './pages/Login';
import { API_BASE, dbToBusinessName, getDbModules, getDbProfile, mergeDbCatalog, clearDbCatalog } from './constants/appConfig';
import { normalizeQueryResult } from './utils/queryResult';
import { normalizeSqlServerHost } from './utils/sqlServer';

// --- IMPORTACION DIRECTA PARA MOVIL Y DESKTOP (MAXIMA COMPATIBILIDAD) ---
// NOTA: React.lazy() con import dinámico causaba "Failed to fetch dynamically
// imported module" en Chrome/Edge --app mode por incompatibilidad con el SW
// y los hashes variables de Vite. Importación directa = cero ese problema.
import { DashboardMobile } from './mobile/DashboardMobile';
import { DashboardView as DashboardDesktop } from './pages/DashboardDesktop';

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

const SESSION_IDLE_TIMEOUT_MS = 30 * 60 * 1000;
const SESSION_CHECK_INTERVAL_MS = 15 * 1000;
const SESSION_ACTIVITY_KEY = 'quantum_last_activity';
const INITIAL_CONNECT_TIMEOUT_MS = 30000;
const BACKGROUND_CONNECT_RETRY_DELAY_MS = 1500;
const LOGIN_RETRY_DELAY_MS = 650;
// Margen total que el login espera a que el backend termine de arrancar antes
// de darse por vencido (ver handleAuthLogin). Uvicorn tarda bastante más que
// Vite en estar listo, y el lanzador abre la ventana apenas Vite responde.
//
// El 31/08/2026 subió de 12000 a 120000: con 12000 el margen era MENOR que el
// timeout de un solo intento (15000) y el retry se rendía a los 15s con el
// panel azul "El sistema no responde" aunque el fallo fuera solo un arranque
// en frío del backend (la primera llamada tras `uvicorn` paga imports pesados
// de langchain y puede tardar más de un minuto). Con 120s el loop reintenta
// hasta que el backend contesta de verdad: una contraseña incorrecta entonces
// recibe su 401 limpio ("Usuario o contraseña incorrectos.") y el panel azul
// queda reservado para un backend que genuinamente no responde.
const LOGIN_BOOT_WAIT_MS = 120000;

// ── Caché local del historial, separada POR USUARIO ────────────────────────
// Antes existia una sola clave 'quantum_sessions' compartida, y al cerrar
// sesion se borraba entera para que un segundo usuario en el mismo navegador
// no viera el historial del anterior. El efecto secundario era que al volver
// a entrar NO habia nada que mostrar: el historial recien aparecia cuando
// respondia /api/sessions, de ahi los segundos en blanco al abrir el sistema.
// Con una clave por usuario se consigue lo mejor de ambos: cada quien ve su
// propio historial al instante y nadie ve el del otro.
const SESSIONS_CACHE_PREFIX = 'quantum_sessions::';
const LEGACY_SESSIONS_KEY = 'quantum_sessions';

const userCacheId = (user) => {
    if (!user) return '';
    const raw = user.username || user.sub || user.id || user.email || '';
    return String(raw).trim().toLowerCase();
};

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
        // Migracion desde la clave antigua compartida: se adopta una sola vez
        // para que el usuario actual no pierda el historial que ya tenia.
        const legacy = JSON.parse(localStorage.getItem(LEGACY_SESSIONS_KEY));
        if (Array.isArray(legacy) && legacy.length > 0) {
            localStorage.setItem(key, JSON.stringify(legacy));
            localStorage.removeItem(LEGACY_SESSIONS_KEY);
            return legacy;
        }
    } catch (_e) { /* cache corrupta: se ignora */ }
    return [];
};

const writeSessionsCache = (user, sessions) => {
    const key = sessionsCacheKey(user);
    if (!key) return;
    try { localStorage.setItem(key, JSON.stringify(sessions || [])); }
    catch (_e) { /* cuota llena: no es critico, el backend es la fuente de verdad */ }
};

const parseJwtExpiryMs = (token) => {
    if (!token) return 0;
    try {
        const payload = JSON.parse(window.atob(token.split('.')[1] || ''));
        return Number(payload?.exp || 0) * 1000;
    } catch (_err) {
        return 0;
    }
};

// URL del endpoint de salud del BACKEND vista desde el navegador.
//
// Debe atravesar el mismo camino que el resto de la API, nunca apuntar al
// origin del frontend: antes devolvía "/health" (raíz relativa), que en local
// caía en el servidor de Vite y en producción en Firebase — en ningún caso
// llegaba al backend (el proxy y el rewrite solo reenvían "/api/*"), así que
// el pre-calentamiento sondeaba la página en vez del servicio y nunca veía
// "online" (bug real 31/08/2026). Con "/api/health" el proxy de Vite lo
// reenvía al backend correcto y Firebase lo rewrites a Cloud Run.
const resolveHealthUrl = () => {
    const base = String(API_BASE || '/api').trim();
    return `${base.replace(/\/$/, '')}/health`;
};

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

// Umbrales estándar de la industria (Tailwind/Material/iOS HIG coinciden en
// este rango): <768px teléfono, 768-1023px tablet, >=1024px escritorio.
const clasificarDeviceType = (ancho) => {
    if (ancho < 768) return 'mobile';
    if (ancho < 1024) return 'tablet';
    return 'desktop';
};

// Seccion: componente principal y estado global del frontend.
function AppInner() {
    // Bloque: Estado global de la app.
    // Controla conexin, sesiones, chat y permisos del usuario.
    const [biPulse, setBiPulse] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [loading, setLoading] = useState(false);
    // Login (30/08/2026): el clic en "Ingresar al
    // sistema" NO usa `loading` (que dispara la pantalla de carga a pantalla
    // completa en Login.jsx). `authPending` es un estado discreto, solo para
    // el spinner DENTRO del botón mientras /login verifica las credenciales.
    // El shell (dashboard) no se abre hasta que /login confirma el token —
    // ver `handleAuthLogin`.
    const [authPending, setAuthPending] = useState(false);
    const [error, setError] = useState(null);
    // ¿El error de arriba es un problema DEL SISTEMA (el servidor no responde,
    // la conexión SQL se cayó) o algo que el usuario puede corregir escribiendo
    // otra vez (credenciales incorrectas)?
    //
    // Distinguirlo importa porque el login ofrece un panel con el botón
    // "Refrescar Sistema". Recargar la página tiene sentido cuando el sistema
    // no está respondiendo, pero no arregla una contraseña equivocada: hasta el
    // 31/08/2026 ese panel salía SIEMPRE que hubiera un error, así que al
    // escribir mal la clave el mismo texto aparecía dos veces —en la franja
    // roja del formulario y otra vez abajo, en azul, con un botón que no lleva
    // a ninguna parte—. Solo se muestra cuando de verdad hay algo que refrescar.
    const [errorDeSistema, setErrorDeSistema] = useState(false);
    const [schema, setSchema] = useState({});
    const [prompt, setPrompt] = useState('');
    // Selector manual de motor de IA (30/08/2026).
    // '' = Flash por defecto (siempre); otro motor solo si el usuario lo
    // elige a propósito. Se revalida en el servidor contra los modelos que
    // ese usuario tiene permitidos — este valor es solo la preferencia que
    // el usuario indicó, nunca la fuente de verdad de qué puede usar.
    const [motorIA, setMotorIA] = useState('');
    const [chatHistory, setChatHistory] = useState([]);
    // FASE 4 — punto 6: imágenes adjuntas pendientes de enviar al modelo
    // Vision. Cada item: { id, dataUrl, name }. Se limpia después de enviar.
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
    // Estado para el efecto typewriter del streaming
    const [streamingMsgId, setStreamingMsgId] = useState(null);

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

    // Seccion: seguridad, restauracion y permisos visibles en UI.
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

    const clearPersistedSession = () => {
        localStorage.removeItem('quantum_token');
        localStorage.removeItem('quantum_user');
        localStorage.removeItem('quantum_conninfo');
        localStorage.removeItem('quantum_schema');
        localStorage.removeItem(SESSION_ACTIVITY_KEY);
        localStorage.removeItem(LEGACY_SESSIONS_KEY);
        // El historial de chat vive en backend, aislado por usuario via JWT.
        // La copia local se conserva bajo una clave PROPIA DE ESTE USUARIO
        // (quantum_sessions::<usuario>) y por eso ya no hace falta borrarla al
        // cerrar sesion: otro usuario en el mismo navegador tendra otra clave y
        // no vera (ni sobrescribira) este historial. Conservarla es justamente
        // lo que permite que al volver a entrar el historial este en pantalla
        // desde el primer instante, sin esperar a /api/sessions.
        sessionsHydratedRef.current = false;
        setSavedSessions([]);
        setSessionsLoading(true);
    };

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
        // BUG (historial perdido al cambiar de empresa): esta función arranca
        // una conversación nueva pero antes NUNCA soltaba `activeSessionId`.
        // El efecto de autoguardado (ver más abajo, depende de [chatHistory,
        // currentResult]) usa activeSessionId para decidir si CREA una sesión
        // nueva o ACTUALIZA una existente. Sin este reset, el primer mensaje
        // que el usuario mandaba en la empresa nueva se guardaba sobre el
        // `id` de la conversación anterior — la sobrescribía en silencio en
        // vez de crear una entrada nueva, por eso la conversación previa
        // desaparecía del historial reciente en vez de quedar guardada.
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

    const registerActivity = () => {
        const now = Date.now();
        lastActivityRef.current = now;
        if (localStorage.getItem('quantum_token')) {
            localStorage.setItem(SESSION_ACTIVITY_KEY, String(now));
        }
    };

    const handleAuthLogin = async (e) => {
        if (e) e.preventDefault();
        if (!tempCreds.username || !tempCreds.password) return;

        setError(null);
        setErrorDeSistema(false);
        setAuthPending(true);

        // ── Validación real ANTES de entrar (31/08/2026) ─────────────────────
        // Hasta hoy el clic abría el shell DE INMEDIATO (UI optimista, sin
        // esperar a /login). Eso causaba un flasheo del dashboard cuando las
        // credenciales eran incorrectas: se "entraba" visualmente y luego el
        // catch revertía. Ahora el shell se abre SOLO después de que /login
        // confirma credenciales y token (ver `openConnectedShell`, dentro del
        // try). Con credenciales malas el usuario se queda en el formulario y
        // ve el error, sin haber entrado jamás.
        //
        // La espera de arranque se conserva: `authPending` mantiene el spinner
        // dentro del botón mientras /login reintenta mientras uvicorn termina
        // de levantar (LOGIN_BOOT_WAIT_MS).
        const targetData = { ...connInfo, database: connInfo.database || '' };

        try {
            const loginPayload = {
                username: tempCreds.username,
                password: tempCreds.password
            };
            // ── Espera activa mientras el backend termina de levantar ─────────
            // BUG REAL corregido el 30/08/2026 (detectado en pruebas: "hay
            // que dar click como 3 veces al botón de ingresar"). Al optimizar
            // el lanzador (VicMarDataAI_Silenzo.vbs) la ventana pasó a abrirse unos
            // 2.5s antes, pero ahí solo se espera a que VITE esté escuchando —
            // uvicorn tarda más en arrancar (importa FastAPI, SQLAlchemy,
            // pyodbc y toda la base de conocimiento). Resultado: el usuario
            // llega al login y pulsa "Ingresar" cuando el backend todavía no
            // responde; /login fallaba con error de red, la transición
            // optimista se revertía y había que volver a pulsar. Con dos
            // intentos separados por 650ms se cubrían ~0.65s de arranque; por
            // eso hacían falta ~3 clics para cubrir los segundos que de verdad
            // tarda.
            //
            // Ahora un SOLO clic espera hasta 12s reintentando, pero SOLO
            // mientras el fallo sea de conexión (el servidor aún no contesta).
            // Una contraseña incorrecta responde 401 —con `err.response`— y
            // sale de inmediato, sin hacer esperar a nadie por un error real.
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
            // shell (dashboard). Con credenciales malas no se llega a esta
            // línea: el catch de abajo deja el error visible en el formulario.
            openConnectedShell(targetData);
            // Pintar YA el historial que este navegador guardo para ESTE
            // usuario. La llamada de abajo lo refresca contra el backend, pero
            // el usuario no tiene que mirar un panel vacio mientras tanto.
            const cachedSessions = readSessionsCache(userData);
            if (cachedSessions.length > 0) {
                setSavedSessions(cachedSessions);
                setSessionsLoading(false);
            }
            void hydrateSessionHistory();

            // Si el usuario ya tiene una base configurada (ej. por persistencia), conectamos en background.
            // Si no, simplemente cargamos las bases para que el usuario elija.
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
            // /login falló (credenciales, timeout, red). Como el shell ya no se
            // abre antes de validar, no hay transición que revertir: el usuario
            // permanece en el formulario con el error visible. Las líneas de
            // abajo son una salvaguarda que limpia cualquier sesión residual.
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
                // El servidor SÍ respondió y rechazó las credenciales. Mensaje
                // propio y claro, sin depender del detail del backend (que aún
                // usa el lenguaje viejo "identificador y codigo"). Nunca se
                // ofrece refrescar: recargar no arregla una contraseña mal
                // escrita, y hasta el 31/08/2026 ese panel azul duplicaba el
                // error en pantalla.
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

    const handleConnect = async (e, overrideData = null, options = {}) => {
        if (e && e.preventDefault) e.preventDefault();
        // ── "El último clic gana" ────────────────────────────────────────────
        // Antes, si ya había una conexión en curso se devolvía {status:'busy'} y
        // el clic se descartaba EN SILENCIO: el usuario elegía otra empresa, no
        // pasaba nada, y la interfaz quedaba mostrando "CONECTANDO..." o volvía
        // a la anterior. Se sentía como que el sistema "se buguea".
        //
        // Ahora no se rechaza: se deja continuar. El mecanismo de `generation`
        // que ya existía más abajo se encarga de que la respuesta de la conexión
        // vieja (que llegará tarde) se descarte y no pise a la nueva. Es la
        // semántica correcta para un selector: la última intención del usuario
        // es la que vale.
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

        // ── Serialización: nunca dos /connect en paralelo ────────────────────
        // /connect reconfigura la sesión del usuario en el backend. Si dos
        // corrieran a la vez, la que terminara última dejaría al backend
        // apuntando a una empresa distinta de la que muestra la pantalla — que
        // es exactamente el síntoma de "datos de otra empresa".
        // Esperamos a que la anterior termine; si mientras esperábamos el
        // usuario hizo clic en otra empresa, abandonamos: esa más nueva hará
        // el trabajo y conectarse a una empresa que el usuario ya descartó
        // sería tiempo perdido.
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
            // Ya no bloqueamos la chatArea (isConnectionReady(false)) para permitir saludos inmediatos.
            //
            // El `business_name` se actualiza JUNTO con la empresa, no después.
            // Antes solo se actualizaban `database` y `selected_company_code` de
            // forma optimista, mientras `business_name` conservaba el de la
            // empresa anterior hasta que llegara la respuesta del servidor.
            // En esa ventana el encabezado mostraba una empresa y las consultas
            // se enviaban a OTRA — el usuario creía estar viendo DELPYG mientras
            // el chat respondía con datos de ALIM. Un desfase así es
            // inaceptable: el nombre en pantalla debe ser siempre el de la
            // empresa que realmente se está consultando.
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
            // La bandera se libera SIEMPRE, sin condicionar a la generación.
            // Antes solo se liberaba si la generación seguía siendo la actual:
            // bastaba con que un logout o una restauración de sesión cambiara la
            // generación a mitad de una conexión para que quedara trabada en
            // `true` de forma permanente — y a partir de ahí TODA conexión
            // posterior se rechazaba por "busy" hasta recargar la página.
            isConnectingRef.current = false;

            // Los estados visuales sí siguen condicionados: solo la petición más
            // reciente tiene derecho a apagar el indicador de carga, para que una
            // respuesta vieja que llega tarde no oculte el spinner de la nueva.
            if (requestGeneration === connectGenerationRef.current) {
                if (dbSwitch) {
                    setIsSwitchingDB(false);
                } else if (!background) {
                    setLoading(false);
                }
            }
        }
    };

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
        // El historial debe estar EN PANTALLA desde el primer render, no
        // aparecer segundos despues cuando responde /api/sessions. Por eso se
        // lee la copia local del ultimo usuario conocido de forma sincrona,
        // aqui mismo, antes de pintar nada.
        try {
            return readSessionsCache(readStoredUser()) || [];
        } catch (e) { return []; }
    });
    // Bandera para no sincronizar hacia el backend hasta haber intentado
    // hidratar primero (evita que un arreglo local vacio/desactualizado
    // sobrescriba el historial ya guardado en el servidor para este usuario).
    const sessionsHydratedRef = useRef(false);
    // Mientras esto es true y aun no hay sesiones locales, el sidebar muestra
    // un esqueleto en vez de "nada" — antes, con el historial ya cargado en
    // localStorage vacio (ej. primer arranque del dia, o el backend tardando
    // en levantar junto al frontend), el usuario veia "Historial Reciente"
    // completamente vacio por unos segundos hasta que /api/sessions respondia,
    // y la lista aparecia de golpe sin ningun indicio de que se estaba cargando.
    const [sessionsLoading, setSessionsLoading] = useState(true);
    const hydrateSessionHistory = async () => {
        // Diagnostico: mide donde se va el tiempo del historial. Visible en la
        // consola del navegador (F12 -> Console, filtrar por "[Historial]").
        const t0 = performance.now();
        const cached = readSessionsCache(userAuth || readStoredUser());
        // Solo se marca "cargando" si NO hay nada que mostrar todavia. Si la
        // copia local ya tiene sesiones, esta hidratacion es un refresco en
        // segundo plano y el usuario no debe ver ningun cambio de estado.
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
                // El lanzador arranca backend y frontend a la vez: si el usuario
                // abre la app justo cuando el backend todavia esta levantando,
                // este primer intento puede fallar por conexion, no por datos
                // faltantes. Un solo reintento corto (mismo patron que el login)
                // cubre ese arranque en frio sin quedarse reintentando para siempre.
                console.warn(`[Historial] primer intento FALLO a los ${Math.round(performance.now() - t0)}ms:`, firstErr?.message || firstErr);
                const transientFailure = firstErr?.code === 'ECONNABORTED' || !firstErr?.response;
                if (!transientFailure) throw firstErr;
                await delay(LOGIN_RETRY_DELAY_MS);
                res = await attemptFetch();
                console.log(`[Historial] reintento OK en ${Math.round(performance.now() - t0)}ms`);
            }
            const remoteSessions = Array.isArray(res.data?.sessions) ? res.data.sessions : [];
            console.log(`[Historial] respuesta del backend: ${remoteSessions.length} sesion(es), total ${Math.round(performance.now() - t0)}ms`);
            // Si el backend ya tiene historial, es la fuente de verdad.
            // Si esta vacio pero el navegador tenia algo (localStorage), se
            // conserva la copia local: el proximo efecto de guardado la subira
            // al backend, migrando naturalmente al usuario a la nube.
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
    // Rediseño móvil/tablet (29/08/2026): antes solo
    // existían dos categorías (mobile <768px, todo lo demás "desktop"), así
    // que una tablet de 768-1024px (iPad, Android grande) recibía el layout
    // de escritorio completo — sidebar fija de 260px + grillas pensadas para
    // mouse — en vez de un layout intermedio pensado para dedo. Con 3
    // categorías, "tablet" puede reusar DashboardDesktop pero con la barra
    // lateral colapsada por defecto (ver DashboardDesktop) en vez de
    // duplicar todo el layout.
    const [deviceType, setDeviceType] = useState(clasificarDeviceType(window.innerWidth));
    const { correct } = useAutoCorrect();

    useEffect(() => {
        const handleResize = () => setDeviceType(clasificarDeviceType(window.innerWidth));
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Tablet reusa DashboardDesktop (mismas vistas, mismo código) pero con
    // el riel lateral colapsado a 64px por defecto en vez de la barra fija
    // de 260px: en un ancho de 768-1024px esa barra fija se comía demasiado
    // espacio relativo. Solo se fuerza al ENTRAR a rango tablet — si el
    // usuario la vuelve a abrir a mano, este efecto no se lo revierte.
    useEffect(() => {
        if (deviceType === 'tablet') setIsSidebarOpen(false);
    }, [deviceType]);
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
    // Ref para deduplicar fetchBiPulse: evita doble-fetch cuando handleConnect
    // y el useEffect lo invocan casi al mismo tiempo para la misma BD.
    const biPulseFetchingRef = useRef('');

    const fetchBiPulse = async (targetDb = '') => {
        const normalizedTargetDb = String(targetDb || connInfo.selected_company_code || connInfo.database || '').trim().toUpperCase();
        if (!normalizedTargetDb) return;
        // Deduplicacion: si ya hay un fetch en vuelo para esta misma BD, no lanzar otro
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
            biPulseFetchingRef.current = ''; // liberar en error para permitir reintento
        } finally {
            // Limpiar SOLO si nadie cambio el ref mientras esperabamos
            if (biPulseFetchingRef.current === normalizedTargetDb) {
                biPulseFetchingRef.current = '';
            }
        }
    };

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
        // Copia local = cache offline. La fuente de verdad es el backend, pero
        // solo se sincroniza despues de un intento de hidratacion (ver
        // hydrateSessionHistory) para no pisar el historial ya guardado en el
        // servidor con un arreglo local vacio o desactualizado.
        if (sessionsHydratedRef.current) {
            void apiPut('/sessions', { sessions: savedSessions }).catch((e) => {
                console.warn('No se pudo sincronizar el historial de sesiones con el backend. Se mantiene solo local.', e);
            });
        }
    }, [savedSessions]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory]);

    // NOTA: el auto-resize del textarea se eliminó deliberadamente (bug de
    // altura): el textarea tiene altura FIJA (rows="1") y scrollea internamente,
    // así nunca crece solo, independientemente del motor de IA seleccionado.

    useEffect(() => {
        // `userAuth` es la guarda: con el login instantáneo (30/08/2026),
        // `isConnected`/`isConnectionReady` pueden ya estar en `true` de forma
        // OPTIMISTA mientras /login todavía verifica en segundo plano y el
        // token real todavía no existe. Sin este guard, este efecto dispararía
        // /databases sin Authorization válido apenas se abriera el shell.
        if (isConnected && isConnectionReady && userAuth && connInfo.host) loadDatabases();
    }, [isConnected, isConnectionReady, userAuth, connInfo.host]);

    useEffect(() => {
        if (!isConnected || !isConnectionReady || !userAuth) return;
        const targetDb = String(connInfo.selected_company_code || connInfo.database || '').trim().toUpperCase();
        if (!targetDb) return;
        // Guard: si handleConnect ya fetcheo este mismo DB, el ref de deduplicacion lo absorbe
        fetchBiPulse(targetDb);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isConnected, isConnectionReady, userAuth, connInfo.database, connInfo.selected_company_code]);

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

    const sortedSessions = useMemo(() => {
        return [...savedSessions].sort((a, b) => {
            if (a.pinned === b.pinned) return 0;
            return a.pinned ? -1 : 1;
        });
    }, [savedSessions]);

    const capabilities = [
        { id: "VENTAS", label: "Área Comercial", desc: "Ventas y Facturación", icon: TrendingUp },
        { id: "OPERACIONES", label: "Gestión de Abastecimiento", desc: "Gestión de Proveedores", icon: Box },
        { id: "RRHH", label: "Capital Humano", desc: "Fichas de Personal & Roles", icon: Users },
        { id: "FINANZAS", label: "Contabilidad", desc: "Balances y Auditoría", icon: Layout },
        { id: "ACADEMICO", label: "Analitica Academica", desc: "Alumnos, Matriculas y Cursos", icon: GraduationCap }
    ];

    const activeCapabilities = useMemo(() => {
        if (!userAuth) return [];
        const displayDbCode = connInfo.selected_company_code || connInfo.database;
        const dbModuleSet = new Set(getDbModules(displayDbCode));
        const byDb = capabilities.filter(cap => dbModuleSet.has(cap.id));
        if (['GERENTE_GENERAL', 'ADMINISTRADOR'].includes(userAuth.role)) return byDb;
        return byDb.filter(cap => userAuth.modules?.includes(cap.id));
    }, [userAuth, connInfo.database, connInfo.selected_company_code]);

    useEffect(() => {
        if (!activeModule) return;
        const displayDbCode = connInfo.selected_company_code || connInfo.database;
        const dbModuleSet = new Set(getDbModules(displayDbCode));
        if (!dbModuleSet.has(activeModule)) {
            setActiveModule(null);
        }
    }, [activeModule, connInfo.database, connInfo.selected_company_code]);

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

        // Si no estamos listos y NO es un saludo, bloqueamos para evitar errores de SQL sin esquema.
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

        // Se capturan ANTES de limpiar el estado: `attachedImages` se vacía
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

        // ── ID de burbuja de respuesta (se crea antes de recibir datos) ──────────
        const aiMsgId = `ai-res-${Date.now()}`;

        // ── Burbuja de "escribiendo..." mientras espera el LLM ───────────────────
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

        // ── FASE 4 — punto 6: rama Vision ─────────────────────────────────
        // Con imágenes adjuntas, la pregunta NO pasa por /query/stream (SQL,
        // esquema, caché semántico, guardarraíl de alcance): va directo al
        // modelo Vision con un endpoint propio, más simple, sin streaming
        // (la respuesta suele ser un párrafo, no vale la pena trocearla).
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

            // ── Vigilancia de tiempo ─────────────────────────────────────────
            // El fetch no tenía ningún límite: si el servidor SQL o el motor de
            // IA se quedaban colgados, la pantalla giraba indefinidamente sin
            // que el usuario supiera qué pasaba ni pudiera hacer nada.
            // Se aplican dos cortes:
            //   · inactividad: no llega NADA nuevo en 150 s. El rewrite de
            //     Firebase Hosting retiene la respuesta SSE completa, así que
            //     una pregunta que DeepSeek (Flash/Pro) tarda en responder
            //     (40-125 s en frío) no envía NI UN byte hasta que termina;
            //     abortar a 25 s hacía que Flash y Pro "nunca respondieran".
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
                // Intentar leer el mensaje del backend si existe
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

            // Filtro de contenido técnico (mismo que antes)
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
                buffer = lines.pop(); // guardar línea incompleta

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
                                // Mostrar datos (tabla/gráfico) INMEDIATAMENTE
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
                                // Agregar chunk al texto en curso
                                explanation += parsed;
                                const sanitized = containsTech(explanation) ? '' : explanation;
                                setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                                    ...m,
                                    content: sanitized,
                                    isStreaming: true,
                                } : m));

                            } else if (currentEvent === 'done') {
                                // Finalizar burbuja
                                finalizadoPorServidor = true;
                                setChatHistory(prev => prev.map(m => m.id === aiMsgId ? {
                                    ...m,
                                    content: explanation && !containsTech(explanation)
                                        ? explanation
                                        : (metaPayload?.explanation || 'Análisis completado.'),
                                    isStreaming: false,
                                    // Preguntas rápidas que el backend adjuntó en el evento
                                    // "meta" (ej. las opciones de Invitado: demo / solicitar
                                    // acceso / conectar BD). Bug real (30/08/2026): este
                                    // handler las pisaba con [] sin condición, así que nunca
                                    // se veían botones aunque el backend los mandara.
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
                        } catch (_parseErr) { /* ignorar líneas malformadas */ }
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
                // RESPUESTA DE CONTINGENCIA (no un error técnico plano): el
                // usuario nunca debe quedarse solo con los tres puntitos ni con
                // un mensaje que no explique nada. Siempre responde alguien —
                // si no llegó la IA a tiempo, responde el propio sistema con
                // una explicación entendible y una siguiente acción concreta.
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

    // Cancela la consulta en curso (botón de la ruedita de carga). Aborta el
    // AbortController activo, lo que dispara el AbortError y cierra la burbuja
    // con un mensaje de "Consulta cancelada" en lugar de dejarla girando.
    const cancelQuery = () => {
        motivoCorteRef.current = 'cancelado';
        if (abortoConsultaRef.current) {
            abortoConsultaRef.current.abort();
        }
    };

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

export default function App() {
    return (
        <ErrorBoundary>
            <AppInner />
        </ErrorBoundary>
    );
}
