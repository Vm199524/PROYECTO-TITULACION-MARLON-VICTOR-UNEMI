const LOCAL_SQL_HOST_PREFIX_RE = /^(localhost|\.|\(local\)|127\.0\.0\.1|0\.0\.0\.0|::1)([\\,].*)?$/i;

const canonicalizeLocalSqlHostPrefix = (value) => {
    const input = String(value ?? '').trim();
    const match = input.match(LOCAL_SQL_HOST_PREFIX_RE);
    if (!match) return input;
    return `localhost${match[2] || ''}`;
};

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
