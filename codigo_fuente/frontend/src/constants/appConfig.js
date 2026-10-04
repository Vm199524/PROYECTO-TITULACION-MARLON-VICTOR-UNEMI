/**
 * Archivo: appConfig.js
 * Rol: constantes globales y catalogo funcional del frontend.
 * Recibe desde: App.jsx, ChatArea.jsx, DesktopHeader.jsx y otros componentes.
 * Se conecta con: api.js para API_BASE y con /api/companies para el catalogo.
 * Responsabilidades: URL base, empresas, modulos y preguntas sugeridas.
 */

const hostname = typeof window !== 'undefined' && window.location ? window.location.hostname : 'localhost';

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

const isLocalHostname = (value) => {
    const host = String(value || '').trim().toLowerCase();
    if (!host) return true;
    if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0' || host === '::1') return true;
    if (host.endsWith('.local')) return true;
    if (isPrivateIpv4(host)) return true;
    return !host.includes('.');
};

export const isLocal = isLocalHostname(hostname);
export const isProduction = hostname.includes('firebaseapp.com') || hostname.includes('web.app');
const PRODUCTION_API_BASE = '/api';

const ENV_API_BASE = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE : '';

// Ruta relativa SIEMPRE, tanto en local como en produccion: el proxy de Vite
// (ver vite.config.js, ya usa VICMAR_BACKEND_PORT) reenvia "/api" al backend
// correcto sin que el navegador cruce de origen. Antes, en local, se armaba
// una URL absoluta fija a ":8000" -- cuando el lanzador (VicMarDataAI_Silenzo.vbs)
// elegia otro puerto por tener 5173/8000 ocupados (ej. 5174/8001, porque hay
// varios proyectos corriendo en paralelo en esta maquina), el navegador
// terminaba llamando a un origen distinto al que sirvio la pagina, y el CORS
// del backend (que solo permite localhost:5173) bloqueaba TODA la API,
// incluido el login -- la pantalla cargaba pero nada funcionaba (bug real,
// 29/08/2026). ENV_API_BASE se conserva como valvula de escape para casos
// excepcionales, pero ya no se necesita para el flujo normal de puertos
// dinamicos.
export const API_BASE = ENV_API_BASE || PRODUCTION_API_BASE;

// Seccion: conocimiento estatico y ayudas de negocio consumidas por la UI.
export const COLORS = ['#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#d946ef', '#6366f1'];
// v2 (bump deliberado): /api/companies y /api/databases dejaron de devolver
// el catálogo demo hardcodeado (ALIM, DAUN...) y ahora descubren bases reales
// vía sys.databases. Cambiar la clave invalida cualquier catálogo demo que
// haya quedado cacheado en el navegador de una sesión anterior al arreglo.
export const DB_CATALOG_STORAGE_KEY = 'quantum_db_catalog_v2';
export const INTERNAL_DB_IDS = [];

export const FRONTEND_CORRECTIONS = {
    "trabajdores": "trabajadores", "trabajdaores": "trabajadores", "trbajadores": "trabajadores",
    "emplados": "empleados", "vendedors": "vendedores", "facutra": "factura",
    "cuanots": "cuantos", "actiovs": "activos", "inactiovs": "inactivos",
    "febreo": "febrero", "mrazo": "marzo", "abirl": "abril", "ocutbre": "octubre", "nomian": "nomina",
    "que menso gana": "que menos gana", "menso sueldo": "menos sueldo"
};

const STATIC_DB_PROFILE_MAP = {
    'CHAT': { business_name: 'Mente VicMar Data AI', short_name: 'AI Core' },
    'RRHH': { business_name: 'AGRINAG S.A.S.', short_name: 'AGRINAG' },
    'MASTER': { business_name: 'Sistema Maestro', short_name: 'SQL Master' },
    'PROYECTO': { business_name: 'Configuración Central', short_name: 'Admin' },
};

// Seccion: catalogo dinamico persistido despues de leer /api/companies.
// `dbId` normalmente es un código de texto ("ALIM"), pero /api/databases
// (antes de que exista el catálogo enriquecido) puede devolver directamente
// objetos {database, business_name}. Aceptar ambas formas aquí evita que un
// objeto crudo se cuele como "código de base" y termine renderizándose como
// hijo de React más adelante (bug real: ver DesktopHeader.jsx).
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

export const getDbCatalog = () => safeReadCatalog();

export const clearDbCatalog = () => {
    safeWriteCatalog({});
    return {};
};

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

export const dbToBusinessName = (dbId) => {
    // Si ya nos pasan un objeto con nombre comercial propio (p. ej. la
    // respuesta cruda de /api/databases), úsalo directo antes de intentar
    // resolverlo contra el catálogo.
    if (dbId && typeof dbId === 'object' && dbId.business_name) {
        return String(dbId.business_name);
    }
    const profile = getDbProfile(dbId);
    if (profile?.business_name) return String(profile.business_name);
    return typeof dbId === 'string' && dbId ? dbId : 'VicMar Data AI';
};

export const getDbModules = (dbId) => {
    const profile = getDbProfile(dbId);
    const modules = Array.isArray(profile?.modules) ? profile.modules : [];
    return modules;
};

export const DB_PROFILE_MAP = STATIC_DB_PROFILE_MAP;
