/**
 * @file Constantes globales y catálogo de bases del frontend. Define la URL
 * base de la API (relativa, a través del proxy de Vite), detecta si la página
 * corre en local o en producción, guarda en localStorage el catálogo de
 * empresas y bases leído de /api/companies y resuelve el nombre comercial y
 * los módulos de cada base; incluye el diccionario de autocorrección de
 * preguntas. Lo usan api.js, App.jsx, ChatArea.jsx, DesktopHeader.jsx y otros
 * componentes.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

const hostname = typeof window !== 'undefined' && window.location ? window.location.hostname : 'localhost';

// Rangos IPv4 privados: 10.x, 192.168.x y 172.16.x a 172.31.x.
const isPrivateIpv4 = (value) => {
    const host = String(value || '').trim();
    if (!host) return false;
    if (/^10\./.test(host)) return true;
    if (/^192\.168\./.test(host)) return true;
    const match = host.match(/^172\.(\d{1,2})\./);
    if (!match) return false;
    const secondOctet = Number(match[1]);
    return secondOctet >= 16 && secondOctet <= 31;
};

// Local: localhost y equivalentes, *.local, IP privadas o nombres sin dominio.
const isLocalHostname = (value) => {
    const host = String(value || '').trim().toLowerCase();
    if (!host) return true;
    if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0' || host === '::1') return true;
    if (host.endsWith('.local')) return true;
    if (isPrivateIpv4(host)) return true;
    return !host.includes('.');
};

/** Indica si la página se sirve desde un host local o de red privada. */
export const isLocal = isLocalHostname(hostname);
/** Indica si la página se sirve desde Firebase Hosting (firebaseapp.com o web.app). */
export const isProduction = hostname.includes('firebaseapp.com') || hostname.includes('web.app');
const PRODUCTION_API_BASE = '/api';

const ENV_API_BASE = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE : '';

/**
 * URL base de la API. Es siempre una ruta relativa, en local y en producción:
 * el proxy de Vite (ver vite.config.ts) reenvía '/api' al backend sin que el
 * navegador cambie de origen. Una URL absoluta con puerto fijo fallaría cuando
 * el frontend o el backend se levantan en otro puerto: el navegador llamaría a
 * un origen distinto y el CORS del backend bloquearía toda la API, incluido el
 * login. `VITE_API_BASE` queda como alternativa para casos excepcionales.
 * @type {string}
 */
export const API_BASE = ENV_API_BASE || PRODUCTION_API_BASE;

/** Paleta de colores para las series de los gráficos. */
export const COLORS = ['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#d946ef', '#6366f1'];
/**
 * Clave de localStorage del catálogo de bases. El sufijo de versión invalida
 * los catálogos de demostración guardados en el navegador: /api/companies y
 * /api/databases descubren las bases reales mediante sys.databases.
 */
export const DB_CATALOG_STORAGE_KEY = 'quantum_db_catalog_v2';
/** Bases internas para las que DesktopHeader no muestra la insignia de empresa (lista vacía). */
export const INTERNAL_DB_IDS = [];

/** Errores de escritura frecuentes y su corrección (los aplica useAutoCorrect). */
export const FRONTEND_CORRECTIONS = {
    "trabajdores": "trabajadores", "trabajdaores": "trabajadores", "trbajadores": "trabajadores",
    "emplados": "empleados", "vendedors": "vendedores", "facutra": "factura",
    "cuanots": "cuantos", "actiovs": "activos", "inactiovs": "inactivos",
    "febreo": "febrero", "mrazo": "marzo", "abirl": "abril", "ocutbre": "octubre", "nomian": "nomina",
    "que menso gana": "que menos gana", "menso sueldo": "menos sueldo"
};

// Perfiles fijos de bases conocidas; el catálogo dinámico los complementa.
const STATIC_DB_PROFILE_MAP = {
    'CHAT': { business_name: 'Mente VicMar Data AI', short_name: 'AI Core' },
    'RRHH': { business_name: 'AGRINAG S.A.S.', short_name: 'AGRINAG' },
    'MASTER': { business_name: 'Sistema Maestro', short_name: 'SQL Master' },
    'PROYECTO': { business_name: 'Configuración Central', short_name: 'Admin' },
};

// Catálogo dinámico guardado después de leer /api/companies.
// `dbId` suele ser un código de texto ("ALIM"), pero /api/databases (antes de
// que exista el catálogo enriquecido) puede devolver objetos
// {database, business_name}. Aceptar ambas formas evita que un objeto crudo
// pase como código de base y termine renderizado como hijo de React (ver
// DesktopHeader.jsx).
const normalizeDbId = (dbId) => {
    if (dbId && typeof dbId === 'object') {
        return String(dbId.database || dbId.code || dbId.short_name || '').trim().toUpperCase();
    }
    return String(dbId || '').trim().toUpperCase();
};

const safeReadCatalog = () => {
    if (typeof window === 'undefined') return {};
    try {
        const raw = JSON.parse(window.localStorage.getItem(DB_CATALOG_STORAGE_KEY) || '{}');
        return raw && typeof raw === 'object' ? raw : {};
    } catch (_err) {
        return {};
    }
};

const safeWriteCatalog = (catalogMap) => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(DB_CATALOG_STORAGE_KEY, JSON.stringify(catalogMap || {}));
};

// Unifica una entrada del backend con los campos que usa la interfaz;
// devuelve null si no se puede deducir el código de base.
const normalizeCatalogEntry = (entry = {}) => {
    const database = normalizeDbId(entry.database || entry.company_code || entry.short_name || entry.business_name);
    if (!database) return null;
    return {
        database,
        company_code: normalizeDbId(entry.company_code || database),
        business_name: entry.business_name || entry.name || entry.short_name || database,
        short_name: entry.short_name || entry.company_code || database,
        modules: Array.isArray(entry.modules) ? entry.modules : [],
        city: entry.city || '',
        country: entry.country || '',
        address: entry.address || '',
        manager: entry.manager || '',
        accountant: entry.accountant || '',
        ruc: entry.ruc || '',
        is_mirror: Boolean(entry.is_mirror),
        is_catalog: Boolean(entry.is_catalog),
        domains: Array.isArray(entry.domains) ? entry.domains : [],
    };
};

/**
 * Reemplaza por completo el catálogo guardado con las entradas recibidas.
 * @param {Array<object>} [entries=[]] Empresas o bases devueltas por el backend.
 * @returns {Object<string, object>} Catálogo nuevo, indexado por código de base.
 */
export const replaceDbCatalog = (entries = []) => {
    const next = {};
    for (const entry of entries) {
        const normalized = normalizeCatalogEntry(entry);
        if (!normalized) continue;
        next[normalized.database] = normalized;
    }
    safeWriteCatalog(next);
    return next;
};

/**
 * Fusiona las entradas recibidas con el catálogo guardado; los campos nuevos
 * sobrescriben a los existentes de la misma base.
 * @param {Array<object>} [entries=[]] Empresas o bases devueltas por el backend.
 * @returns {Object<string, object>} Catálogo resultante.
 */
export const mergeDbCatalog = (entries = []) => {
    const current = safeReadCatalog();
    const next = { ...current };
    for (const entry of entries) {
        const normalized = normalizeCatalogEntry(entry);
        if (!normalized) continue;
        next[normalized.database] = {
            ...(next[normalized.database] || {}),
            ...normalized,
        };
    }
    safeWriteCatalog(next);
    return next;
};

/**
 * Lee el catálogo guardado en localStorage.
 * @returns {Object<string, object>} Catálogo indexado por código de base, o un
 *   objeto vacío si no existe o no se puede leer.
 */
export const getDbCatalog = () => safeReadCatalog();

/**
 * Vacía el catálogo guardado.
 * @returns {Object} Objeto vacío.
 */
export const clearDbCatalog = () => {
    safeWriteCatalog({});
    return {};
};

/**
 * Obtiene el perfil de una base combinando el perfil fijo con el catálogo
 * dinámico (este último tiene prioridad).
 * @param {string|object} dbId Código de base u objeto {database, business_name}.
 * @returns {object|null} Perfil con `database`, `business_name`, `short_name`
 *   y `modules`; null si no hay código.
 */
export const getDbProfile = (dbId) => {
    const database = normalizeDbId(dbId);
    if (!database) return null;
    const dynamicCatalog = safeReadCatalog();
    const dynamicProfile = dynamicCatalog[database];
    const staticProfile = STATIC_DB_PROFILE_MAP[database];
    if (dynamicProfile || staticProfile) {
        return {
            database,
            ...(staticProfile || {}),
            ...(dynamicProfile || {}),
        };
    }
    return {
        database,
        business_name: database,
        short_name: database,
        modules: [],
    };
};

/**
 * Devuelve el nombre comercial de una base para mostrarlo en la interfaz.
 * @param {string|object} dbId Código de base u objeto con `business_name`.
 * @returns {string} Nombre comercial, el código recibido o 'VicMar Data AI'
 *   si no hay ninguno.
 */
export const dbToBusinessName = (dbId) => {
    // Si llega un objeto con nombre comercial propio (p. ej. la respuesta
    // cruda de /api/databases), se usa directamente sin consultar el catálogo.
    if (dbId && typeof dbId === 'object' && dbId.business_name) {
        return String(dbId.business_name);
    }
    const profile = getDbProfile(dbId);
    if (profile?.business_name) return String(profile.business_name);
    return typeof dbId === 'string' && dbId ? dbId : 'VicMar Data AI';
};

/**
 * Devuelve los módulos habilitados de una base.
 * @param {string|object} dbId Código de base.
 * @returns {string[]} Módulos del perfil, o arreglo vacío.
 */
export const getDbModules = (dbId) => {
    const profile = getDbProfile(dbId);
    const modules = Array.isArray(profile?.modules) ? profile.modules : [];
    return modules;
};

/** Perfiles fijos de bases conocidas, indexados por código. */
export const DB_PROFILE_MAP = STATIC_DB_PROFILE_MAP;
