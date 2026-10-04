/**
 * DataChannels.jsx — Orquestador de "Orígenes de Datos".
 *
 * Responsabilidades (únicas):
 *   1. Estado compartido: switchingDatabase, isConnecting, connectError,
 *      companies, recentServers, etc.
 *   2. Handlers de negocio: handleConnect, loadCompaniesInternal,
 *      handleSelectDatabase, handleDirectDatabaseConnect, etc.
 *   3. Computed values: discoveredDatabases, companyRows.
 *   4. Renderiza el encabezado + descripción + <ConnectionCard />.
 *
 * Este archivo pasó de ~870 líneas a ~220 delegando todo el JSX de la
 * tarjeta de conexión a ConnectionCard.jsx (extraído el 28/07/2026).
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

// ── Helpers de servidores recientes ──────────────────────────────────
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
    } catch { /* silent */ }
}

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
    // Catálogo de servidores AUTORIZADOS (backend/main.py::SERVERS_CATALOG) —
    // a diferencia de "recientes" (lo que el usuario tecleó antes, por
    // navegador), esto es la lista curada que existe para este despliegue,
    // igual que un registro de conexiones en un banco.
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

    // Limpiar lista de empresas si el host cambia
    useEffect(() => {
        const normalized = normalizeSqlServerHost(connInfo.host);
        if (autoLoadedHostRef.current && normalized !== autoLoadedHostRef.current) {
            setCompanies([]);
            clearDbCatalog();
        }
        autoLoadedHostRef.current = normalized;
    }, [connInfo.host]);

    // ── Handlers de formulario ────────────────────────────────────────
    const updateConnField = (field, value) => {
        if (typeof setConnInfo === 'function') {
            setConnInfo((prev) => ({ ...prev, [field]: value }));
        }
        if (field === 'host') {
            setConnectError('');
            setConnectSuccess(false);
        }
    };

    // Cuando cambia de auth type, limpiar credenciales si se va a Windows Auth
    const handleAuthTypeChange = (value) => {
        if (value === 'Windows Authentication') {
            if (typeof setConnInfo === 'function') {
                setConnInfo(prev => ({ ...prev, auth_type: value, user: '', password: '' }));
            }
        } else {
            updateConnField('auth_type', value);
        }
    };

    // --- CANCEL CONNECT ---
    const handleCancelConnect = () => {
        if (connectAbortRef.current) {
            connectAbortRef.current.abort();
            connectAbortRef.current = null;
        }
        setIsConnecting(false);
        setConnectError('Conexión cancelada. Corrige los datos e intenta nuevamente.');
    };

    // --- CONNECT ---
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

        // Limpiar estado anterior del host previo
        setCompanies([]);
        clearDbCatalog();
        setConnectError('');
        setConnectSuccess(false);
        setIsConnecting(true);

        // Crear AbortController para permitir cancelación
        const abortController = new AbortController();
        connectAbortRef.current = abortController;

        // Para Windows Auth nunca mandamos credenciales SQL
        const connectData = {
            ...connInfo,
            host: normalizedHost,
            database: 'master',          // Conectamos a master para explorar
            selected_company_code: '',   // Limpiamos empresa previa
            ...(connInfo.auth_type === 'Windows Authentication'
                ? { user: '', password: '' }
                : {}),
        };

        try {
            await handleConnect(null, connectData, { background: true, openShellOnSuccess: false, signal: abortController.signal });

            saveRecentServer(normalizedHost);
            setRecentServers(getRecentServers());
            updateConnField('host', normalizedHost);
            // Limpiar empresa activa para que el usuario elija una fresca
            if (typeof setConnInfo === 'function') {
                setConnInfo(prev => ({
                    ...prev,
                    host: normalizedHost,
                    database: '', // No activamos 'master' como base visible
                    selected_company_code: '',
                }));
            }
            setConnectSuccess(true);

            // Auto-explorar bases y cargar catálogo tras conectar
            // IMPORTANTE: pasamos connectData COMPLETO para evitar estado stale de connInfo
            if (typeof loadDatabases === 'function') {
                loadDatabases(connectData).catch(() => { });
            }
            loadCompaniesInternal(normalizedHost, connectData).catch(() => { });
        } catch (err) {
            if (err?.name === 'AbortError' || err?.message?.includes('aborted')) {
                // Cancelado por el usuario — no mostrar error
            } else {
                setConnectError(err?.response?.data?.detail || err?.message || 'No se pudo conectar al servidor.');
            }
        } finally {
            setIsConnecting(false);
            connectAbortRef.current = null;
        }
    };

    // --- EXPLORE DATABASES ---
    const handleRefreshDatabases = async () => {
        if (typeof loadDatabases === 'function') {
            const normalizedHost = normalizeSqlServerHost(connInfo.host);
            clearDbCatalog();
            // Enviar sin credenciales SQL si es Windows Auth
            const safeConnInfo = { ...connInfo, host: normalizedHost };
            if (safeConnInfo.auth_type === 'Windows Authentication') {
                safeConnInfo.user = '';
                safeConnInfo.password = '';
            }
            await loadDatabases(safeConnInfo);
            // Sincronizar automáticamente el catálogo de nombres comerciales al explorar
            loadCompaniesInternal(normalizedHost, safeConnInfo).catch(() => { });
        }
    };

    // --- LOAD COMPANIES (internal) ---
    // overrideParams: pasar el connectData al llamar desde handleConnectButton
    // para evitar usar connInfo stale (React state no se actualizó aún)
    const loadCompaniesInternal = async (hostOverride, overrideParams = null) => {
        const normalizedHost = hostOverride || normalizeSqlServerHost(connInfo.host);
        if (!normalizedHost) return;

        // Si se especifica un host nuevo (cambio de servidor), limpiar empresas de inmediato
        if (hostOverride && hostOverride !== normalizeSqlServerHost(connInfo.host)) {
            setCompanies([]);
        }

        setFetchingCompanies(true);
        try {
            // Usar overrideParams si disponible (evita estado stale), si no, usar connInfo
            const src = overrideParams || connInfo;
            const authType = src.auth_type || 'SQL Server Authentication';
            const payload = {
                host: normalizedHost,
                database: 'PROYECTO',         // Siempre buscar en PROYECTO (catálogo empresas)
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
                // Si falla o retorna vacío, limpiar para no mostrar datos anteriores
                setCompanies([]);
            }
        } catch {
            setCompanies([]);
        } finally {
            setFetchingCompanies(false);
        }
    };

    const loadCompanies = () => loadCompaniesInternal();

    // --- SELECT COMPANY ---
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
            // 'superseded' = el usuario eligió otra empresa mientras esta
            // esperaba su turno; no tocamos el filtro para no interferir.
            if (connectResult?.status === 'superseded') return;
            setDbFilter('');
        } catch (err) {
            console.error('Fallo al cambiar base:', err);
        } finally {
            setSwitchingDatabase((actual) => (actual === marcador ? '' : actual));
            setSwitchingCompanyCode((actual) => (actual === companyCode ? '' : actual));
        }
    };

    // --- DIRECT DB CONNECT (from discovered list) ---
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
        } catch { /* silent */ } finally {
            // Solo limpiamos el indicador si sigue siendo el nuestro.
            setSwitchingDatabase((actual) => (actual === targetDatabase ? '' : actual));
            setSwitchingCompanyCode((actual) => (actual === companyCode ? '' : actual));
        }
    };

    // Auto-load companies when host changes
    useEffect(() => {
        const normalizedHost = normalizeSqlServerHost(connInfo.host);
        if (!normalizedHost || fetchingCompanies) return;
        if (autoLoadedHostRef.current === normalizedHost) return;
        autoLoadedHostRef.current = normalizedHost;
        void loadCompaniesInternal(normalizedHost);
    }, [connInfo.host]);

    // ── Computed values ───────────────────────────────────────────────
    const discoveredDatabases = availableDBs
        .map((db) => (typeof db === 'object' && db !== null ? db.database : String(db || '').trim()))
        .filter(Boolean);

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

        // Inyectar el contexto de la base activa si tiene business_name (prioridad)
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

            // Si el nombre que viene es nulo o igual al ID de la base, intentar el fallback descriptivo
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

        // Asegurar que TODAS las bases físicas descubiertas estén en el índice
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

                {/* Cabecera y contexto fijos (no scrollean); solo el contenido
                    inferior se desplaza, igual que en el panel de auditoría. */}
                <div className="flex shrink-0 flex-col gap-4">
                    <div className="flex items-center gap-3">
                        <Database className="text-cyan-400" size={24} />
                        <h1 className="text-2xl font-bold text-white tracking-wide">Orígenes de Datos</h1>
                    </div>

                    <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-3 text-sm leading-relaxed text-white/65">
                        Selecciona una empresa para activar su contexto de trabajo. VicMar Data AI adapta consultas, módulos y
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
