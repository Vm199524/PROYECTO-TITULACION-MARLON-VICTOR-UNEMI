/**
 * @file Normalización del host de SQL Server que escribe el usuario en el
 * formulario de conexión. Limpia comillas y espacios y unifica los alias
 * locales en `localhost` antes de enviar el host al backend.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

// Alias locales reconocidos, seguidos opcionalmente de `\instancia` o `,puerto`.
const LOCAL_SQL_HOST_PREFIX_RE = /^(localhost|\.|\(local\)|127\.0\.0\.1|0\.0\.0\.0|::1)([\\,].*)?$/i;

const canonicalizeLocalSqlHostPrefix = (value) => {
    const input = String(value ?? '').trim();
    const match = input.match(LOCAL_SQL_HOST_PREFIX_RE);
    if (!match) return input;
    return `localhost${match[2] || ''}`;
};

/**
 * Normaliza el host de SQL Server: quita comillas externas, elimina los
 * espacios alrededor de los separadores de instancia (`\`) y de puerto (`,`)
 * y convierte los alias locales en `localhost`.
 * @param {string|null|undefined} value Host tal como lo escribió el usuario.
 * @returns {string} Host normalizado, o cadena vacía si no hay valor.
 */
export function normalizeSqlServerHost(value) {
    const raw = String(value ?? '').trim().replace(/^['"]+|['"]+$/g, '');
    if (!raw) return '';

    const normalizedInstance = raw.includes('\\')
        ? raw.split('\\').map((part) => part.trim()).join('\\')
        : raw;

    const normalized = normalizedInstance.includes(',')
        ? normalizedInstance.split(',').map((part) => part.trim()).join(',')
        : normalizedInstance;

    return canonicalizeLocalSqlHostPrefix(normalized);
}
