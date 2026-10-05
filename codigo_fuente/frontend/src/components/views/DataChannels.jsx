/**
 * @file Vista «Orígenes de Datos». Orquesta la conexión a un servidor SQL Server:
 * guarda el estado compartido (conexión en curso, errores, empresas, servidores
 * recientes y autorizados), resuelve la conexión, la exploración de bases y la carga
 * del catálogo de empresas (/api/servers, /api/companies) y delega el formulario y la
 * lista de bases en ConnectionCard.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Database } from 'lucide-react';

import { ConnectionCard } from './ConnectionCard';
import {
    dbToBusinessName,
    getDbCatalog,
    mergeDbCatalog,
    clearDbCatalog,
    replaceDbCatalog,
} from '../../constants/appConfig';
import { apiGet, apiPost } from '../../services/api';
import { normalizeSqlServerHost } from '../../utils/sqlServer';

// ── Servidores recientes (localStorage, máximo 8) ────────────────────
const RECENT_SERVERS_KEY = 'quantum_recent_servers';

function getRecentServers() {
    try {
        return JSON.parse(localStorage.getItem(RECENT_SERVERS_KEY) || '[]');
    } catch {
        return [];
    }
}

function saveRecentServer(host) {
    if (!host) return;
    try {
        const prev = getRecentServers();
        const updated = [host, ...prev.filter(h => h !== host)].slice(0, 8);
        localStorage.setItem(RECENT_SERVERS_KEY, JSON.stringify(updated));
    } catch { /* silencioso */ }
}

/**
 * Muestra la vista de orígenes de datos y coordina la conexión, la exploración de
 * bases y la selección de empresa.
 *
 * @param {object} props
 * @param {object} [props.connInfo={}] - Datos de conexión (`host`, `auth_type`, `user`, `password`, `driver`, `database`...).
 * @param {Function} props.setConnInfo - Actualiza los datos de conexión.
 * @param {Array<string|object>} [props.availableDBs=[]] - Bases descubiertas en el servidor.
 * @param {boolean} [props.fetchingDBs=false] - Si la exploración de bases está en curso.
 * @param {Function} props.loadDatabases - Explora las bases del servidor con los parámetros recibidos.
 * @param {Function} props.handleConnect - Abre la conexión; recibe `(evento, datos, opciones)`.
 * @returns {JSX.Element} Vista de orígenes de datos.
 */
export function DataChannels({
    connInfo = {},
    setConnInfo,
    availableDBs = [],
    fetchingDBs = false,
    loadDatabases,
    handleConnect,
}) {
    // ── Estado de negocio (orquestador) ──────────────────────────────
    const [dbFilter, setDbFilter] = useState('');
    const [openPanel, setOpenPanel] = useState(null);
    const [switchingDatabase, setSwitchingDatabase] = useState('');
    const [switchingCompanyCode, setSwitchingCompanyCode] = useState('');
    const [companies, setCompanies] = useState(() => {
        const catalog = getDbCatalog();
        return Object.values(catalog || {}).filter((entry) => entry?.database);
    });
    const [fetchingCompanies, setFetchingCompanies] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [connectError, setConnectError] = useState('');
    const [connectSuccess, setConnectSuccess] = useState(false);
    const [recentServers, setRecentServers] = useState(getRecentServers);
    // Catálogo de servidores AUTORIZADOS (backend/main.py::SERVERS_CATALOG). A
    // diferencia de los recientes (lo que el usuario escribió antes en este
    // navegador), es la lista curada para este despliegue, como un registro de
    // conexiones.
    const [knownServers, setKnownServers] = useState([]);

    const autoLoadedHostRef = useRef('');
    const connectAbortRef = useRef(null);

    useEffect(() => {
        let cancelado = false;
        apiGet('/servers')
            .then((res) => {
                if (!cancelado) setKnownServers(res.data?.servers || []);
            })
            .catch(() => { /* silencioso: el campo sigue funcionando en texto libre */ });
        return () => { cancelado = true; };
    }, []);

    // Limpia la lista de empresas si cambia el host.
    useEffect(() => {
        const normalized = normalizeSqlServerHost(connInfo.host);
        if (autoLoadedHostRef.current && normalized !== autoLoadedHostRef.current) {
            setCompanies([]);
            clearDbCatalog();
        }
        autoLoadedHostRef.current = normalized;
    }, [connInfo.host]);

    // ── Manejadores del formulario ────────────────────────────────────
    const updateConnField = (field, value) => {
        if (typeof setConnInfo === 'function') {
            setConnInfo((prev) => ({ ...prev, [field]: value }));
        }
        if (field === 'host') {
            setConnectError('');
            setConnectSuccess(false);
        }
    };

    // Al pasar a Windows Authentication se limpian las credenciales SQL.
    const handleAuthTypeChange = (value) => {
        if (value === 'Windows Authentication') {
            if (typeof setConnInfo === 'function') {
                setConnInfo(prev => ({ ...prev, auth_type: value, user: '', password: '' }));
            }
        } else {
            updateConnField('auth_type', value);
        }
    };

    // Cancela la conexión en curso.
    const handleCancelConnect = () => {
        if (connectAbortRef.current) {
            connectAbortRef.current.abort();
            connectAbortRef.current = null;
        }
        setIsConnecting(false);
        setConnectError('Conexión cancelada. Corrige los datos e intenta nuevamente.');
    };

    // Conecta al servidor (base master) y luego explora sus bases y el catálogo
    // de empresas.
    const handleConnectButton = async () => {
        const isLocalHostRequested = (host) => {
            const h = host?.toLowerCase() || '';
            return h.includes('localhost') || h.includes('127.0.0.1') || h === '.' || h.includes('(local)');
        };
        const isProdWeb = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';

        const normalizedHost = normalizeSqlServerHost(connInfo.host);
        if (!normalizedHost) {
            setConnectError('Ingresa el nombre del servidor.');
            return;
        }

        if (isProdWeb && isLocalHostRequested(normalizedHost)) {
            setConnectError('🚧 Estás en la versión WEB Cloud. Para conectar a tu PC local (localhost), debes usar un túnel (ngrok/Cloudflare) o utilizar la IP pública de tu red con el puerto 1433 abierto.');
            return;
        }

        // Limpia el estado del host anterior.
        setCompanies([]);
        clearDbCatalog();
        setConnectError('');
        setConnectSuccess(false);
        setIsConnecting(true);

        // AbortController para permitir la cancelación.
        const abortController = new AbortController();
        connectAbortRef.current = abortController;

        // Con Windows Authentication nunca se envían credenciales SQL.
        const connectData = {
            ...connInfo,
            host: normalizedHost,
            database: 'master',          // Se conecta a master para explorar
            selected_company_code: '',   // Se limpia la empresa previa
            ...(connInfo.auth_type === 'Windows Authentication'
                ? { user: '', password: '' }
                : {}),
        };

        try {
            await handleConnect(null, connectData, { background: true, openShellOnSuccess: false, signal: abortController.signal });

            saveRecentServer(normalizedHost);
            setRecentServers(getRecentServers());
            updateConnField('host', normalizedHost);
            // Se limpia la empresa activa para que el usuario elija una nueva.
            if (typeof setConnInfo === 'function') {
                setConnInfo(prev => ({
                    ...prev,
                    host: normalizedHost,
                    database: '', // 'master' no se activa como base visible
                    selected_company_code: '',
                }));
            }
            setConnectSuccess(true);

            // Tras conectar, explora las bases y carga el catálogo. Se pasa
            // connectData COMPLETO porque connInfo aún no refleja el estado nuevo.
            if (typeof loadDatabases === 'function') {
                loadDatabases(connectData).catch(() => { });
            }
            loadCompaniesInternal(normalizedHost, connectData).catch(() => { });
        } catch (err) {
            if (err?.name === 'AbortError' || err?.message?.includes('aborted')) {
                // Cancelado por el usuario: no se muestra error.
            } else {
                setConnectError(err?.response?.data?.detail || err?.message || 'No se pudo conectar al servidor.');
            }
        } finally {
            setIsConnecting(false);
            connectAbortRef.current = null;
        }
    };

    // Vuelve a explorar las bases del servidor y sincroniza el catálogo de empresas.
    const handleRefreshDatabases = async () => {
        if (typeof loadDatabases === 'function') {
            const normalizedHost = normalizeSqlServerHost(connInfo.host);
            clearDbCatalog();
            // Sin credenciales SQL si es Windows Authentication.
            const safeConnInfo = { ...connInfo, host: normalizedHost };
            if (safeConnInfo.auth_type === 'Windows Authentication') {
                safeConnInfo.user = '';
                safeConnInfo.password = '';
            }
            await loadDatabases(safeConnInfo);
            // Sincroniza el catálogo de nombres comerciales al explorar.
            loadCompaniesInternal(normalizedHost, safeConnInfo).catch(() => { });
        }
    };

    // Carga el catálogo de empresas desde la base PROYECTO (/api/companies).
    // overrideParams recibe connectData cuando se llama desde handleConnectButton,
    // porque el estado connInfo de React todavía no se ha actualizado.
    const loadCompaniesInternal = async (hostOverride, overrideParams = null) => {
        const normalizedHost = hostOverride || normalizeSqlServerHost(connInfo.host);
        if (!normalizedHost) return;

        // Con un host nuevo (cambio de servidor), se limpian las empresas de inmediato.
        if (hostOverride && hostOverride !== normalizeSqlServerHost(connInfo.host)) {
            setCompanies([]);
        }

        setFetchingCompanies(true);
        try {
            // Usa overrideParams si existe (evita estado desactualizado); si no, connInfo.
            const src = overrideParams || connInfo;
            const authType = src.auth_type || 'SQL Server Authentication';
            const payload = {
                host: normalizedHost,
                database: 'PROYECTO',         // El catálogo de empresas siempre está en PROYECTO
                auth_type: authType,
                user: authType === 'Windows Authentication' ? '' : (src.user || ''),
                password: authType === 'Windows Authentication' ? '' : (src.password || ''),
                driver: src.driver || 'ODBC Driver 17 for SQL Server',
            };
            const response = await apiPost('/companies', payload);
            if (response.data?.status === 'success' && response.data?.companies?.length) {
                setCompanies(response.data.companies);
                replaceDbCatalog(response.data.companies);
            } else {
                // Si falla o viene vacío, se limpia para no mostrar datos anteriores.
                setCompanies([]);
            }
        } catch {
            setCompanies([]);
        } finally {
            setFetchingCompanies(false);
        }
    };

    const loadCompanies = () => loadCompaniesInternal();

    // Activa una empresa (o CHAT/PROYECTO) como base de trabajo.
    const handleSelectDatabase = async (database) => {
        if (typeof handleConnect !== 'function') return;
        const dbUpper = database.toUpperCase().trim();
        const isCompanyContext = dbUpper !== 'CHAT' && dbUpper !== 'PROYECTO';
        const targetDatabase = dbUpper;
        const companyCode = isCompanyContext ? dbUpper : '';
        const normalizedHost = normalizeSqlServerHost(connInfo.host);

        if (companyCode) {
            const company = companyRows.find(c => c.database === companyCode);
            if (company) mergeDbCatalog([company]);
        }

        const marcador = companyCode || targetDatabase;
        setSwitchingDatabase(marcador);
        setSwitchingCompanyCode(companyCode);
        try {
            const connectResult = await handleConnect(null, {
                ...connInfo,
                host: normalizedHost || connInfo.host,
                database: targetDatabase,
                selected_company_code: companyCode,
            }, { dbSwitch: true });
            // 'superseded': el usuario eligió otra empresa mientras esta
            // esperaba su turno; no se toca el filtro para no interferir.
            if (connectResult?.status === 'superseded') return;
            setDbFilter('');
        } catch (err) {
            console.error('Fallo al cambiar base:', err);
        } finally {
            setSwitchingDatabase((actual) => (actual === marcador ? '' : actual));
            setSwitchingCompanyCode((actual) => (actual === companyCode ? '' : actual));
        }
    };

    // Conecta directamente a una base de la lista descubierta.
    const handleDirectDatabaseConnect = async (databaseName) => {
        if (typeof handleConnect !== 'function') return;
        const normalizedHost = normalizeSqlServerHost(connInfo.host);
        const targetDatabase = String(databaseName || connInfo.database || '').trim();
        if (!normalizedHost || !targetDatabase) return;

        const company = companyRows.find(c => c.database === targetDatabase.toUpperCase());
        const companyCode = company?.database || '';

        setSwitchingDatabase(targetDatabase);
        setSwitchingCompanyCode(companyCode);
        try {
            await handleConnect(null, {
                ...connInfo,
                host: normalizedHost,
                database: targetDatabase,
                selected_company_code: companyCode,
            }, { dbSwitch: true });
        } catch { /* silencioso */ } finally {
            // Solo se limpia el indicador si sigue siendo el de esta conexión.
            setSwitchingDatabase((actual) => (actual === targetDatabase ? '' : actual));
            setSwitchingCompanyCode((actual) => (actual === companyCode ? '' : actual));
        }
    };

    // Carga automáticamente las empresas cuando cambia el host.
    useEffect(() => {
        const normalizedHost = normalizeSqlServerHost(connInfo.host);
        if (!normalizedHost || fetchingCompanies) return;
        if (autoLoadedHostRef.current === normalizedHost) return;
        autoLoadedHostRef.current = normalizedHost;
        void loadCompaniesInternal(normalizedHost);
    }, [connInfo.host]);

    // ── Valores derivados ─────────────────────────────────────────────
    const discoveredDatabases = availableDBs
        .map((db) => (typeof db === 'object' && db !== null ? db.database : String(db || '').trim()))
        .filter(Boolean);

    // Une catálogo guardado, empresas cargadas, base activa, bases de la conexión
    // y bases descubiertas en una lista única por código, ordenada por nombre.
    const companyRows = useMemo(() => {
        if (!connInfo.host) return [];
        const index = new Map();

        Object.values(getDbCatalog() || {}).forEach((entry) => {
            const db = String(entry?.database || '').trim().toUpperCase();
            if (!db) return;
            index.set(db, { ...entry, database: db });
        });

        companies.forEach((entry) => {
            const db = String(entry?.database || '').trim().toUpperCase();
            if (!db) return;
            index.set(db, { ...(index.get(db) || {}), ...entry, database: db });
        });

        // La base activa con business_name tiene prioridad.
        if (connInfo.database && connInfo.business_name) {
            const activeDb = String(connInfo.database).trim().toUpperCase();
            index.set(activeDb, {
                ...(index.get(activeDb) || {}),
                database: activeDb,
                business_name: connInfo.business_name,
            });
        }

        (connInfo?.databases || []).forEach((dbObj) => {
            const dbName = typeof dbObj === 'object' ? dbObj.database : dbObj;
            const db = String(dbName || '').trim().toUpperCase();
            if (!db) return;

            const bizName = typeof dbObj === 'object' ? dbObj.business_name : null;
            const existingBiz = index.get(db)?.business_name;

            // Si el nombre es nulo o igual al código de la base, se usa el nombre descriptivo de respaldo.
            const finalBizName = (bizName && bizName !== db)
                ? bizName
                : (existingBiz && existingBiz !== db)
                    ? existingBiz
                    : dbToBusinessName(db);

            index.set(db, {
                ...(index.get(db) || {}),
                database: db,
                company_code: db,
                business_name: finalBizName,
                short_name: index.get(db)?.short_name || db,
            });
        });

        // Asegura que TODAS las bases físicas descubiertas estén en el índice.
        discoveredDatabases.forEach((dbName) => {
            const db = String(dbName || '').trim().toUpperCase();
            if (!db || index.has(db)) return;
            index.set(db, {
                database: db,
                company_code: db,
                business_name: dbToBusinessName(db),
                short_name: db,
            });
        });

        return Array.from(index.values()).sort((a, b) => {
            const aName = String(a.business_name || a.database || '').toLowerCase();
            const bName = String(b.business_name || b.database || '').toLowerCase();
            return aName.localeCompare(bName);
        });
    }, [companies, discoveredDatabases, connInfo.host, connInfo.database, connInfo.business_name]);

    // ── Render (orquestador puro) ─────────────────────────────────────
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex h-full w-full flex-col overflow-hidden p-4 md:p-6"
        >
            <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 overflow-hidden">

                {/* Cabecera y contexto fijos (no se desplazan); solo el contenido
                    inferior hace scroll, igual que en el panel de auditoría. */}
                <div className="flex shrink-0 flex-col gap-4">
                    <div className="flex items-center gap-3">
                        <Database className="text-cyan-400" size={24} />
                        <h1 className="text-2xl font-bold text-white tracking-wide">Orígenes de Datos</h1>
                    </div>

                    <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-3 text-sm leading-relaxed text-white/65">
                        Selecciona una institución para activar su contexto de trabajo. VicMar Data AI adapta consultas, módulos y
                        respuestas según la estructura de datos detectada en la base elegida.
                    </div>
                </div>

                {/* Tarjeta de conexión + panel de bases (ver ConnectionCard.jsx) */}
                <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar" style={{ paddingBottom: '80px' }}>
                    <ConnectionCard
                        connInfo={connInfo}
                        recentServers={recentServers}
                        knownServers={knownServers}
                        onSelectKnownServer={(srv) => {
                            if (typeof setConnInfo !== 'function') return;
                            setConnInfo((prev) => ({
                                ...prev,
                                host: srv.host,
                                driver: srv.driver || prev.driver,
                                auth_type: srv.auth_type || prev.auth_type,
                                user: srv.auth_type === 'Windows Authentication' ? '' : (srv.default_user || ''),
                                password: '',
                            }));
                            setConnectError('');
                            setConnectSuccess(false);
                        }}
                        isConnecting={isConnecting}
                        connectError={connectError}
                        connectSuccess={connectSuccess}
                        fetchingDBs={fetchingDBs}
                        fetchingCompanies={fetchingCompanies}
                        discoveredDatabases={discoveredDatabases}
                        companyRows={companyRows}
                        switchingDatabase={switchingDatabase}
                        onFieldChange={updateConnField}
                        onAuthTypeChange={handleAuthTypeChange}
                        onConnect={handleConnectButton}
                        onCancel={handleCancelConnect}
                        onExplore={handleRefreshDatabases}
                        onLoadCatalog={loadCompanies}
                        onSelectDatabase={handleDirectDatabaseConnect}
                    />
                </div>

            </div>
        </motion.div>
    );
}
