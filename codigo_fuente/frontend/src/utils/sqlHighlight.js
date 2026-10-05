/**
 * @file Resaltado ligero de sintaxis SQL, sin dependencias externas, para el
 * bloque de solo lectura de la pestaña «SQL» del chat. Divide la consulta en
 * tokens { text, type } (palabras clave, cadenas, números, comentarios) que el
 * componente renderiza como <span> con una clase de color por tipo.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

const KEYWORDS = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
    'ON', 'AND', 'OR', 'NOT', 'IN', 'AS', 'GROUP', 'BY', 'ORDER', 'HAVING',
    'TOP', 'DISTINCT', 'UNION', 'ALL', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    'IS', 'NULL', 'LIKE', 'BETWEEN', 'EXISTS', 'WITH', 'OVER', 'PARTITION',
    'ASC', 'DESC', 'LIMIT', 'OFFSET', 'CAST', 'CONVERT', 'COUNT', 'SUM',
    'AVG', 'MIN', 'MAX', 'ISNULL', 'COALESCE',
];

const KEYWORD_SET = new Set(KEYWORDS);
// Cadenas 'texto', comentarios -- y /* */, números, palabras y el resto.
const TOKEN_RE = /('(?:[^']|'')*')|(--[^\n]*)|(\/\*[\s\S]*?\*\/)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|(\s+)|(.)/g;

/**
 * Divide una consulta SQL en tokens clasificados para colorearlos.
 * @param {string} sql Texto de la consulta.
 * @returns {Array<{text: string, type: string}>} Tokens en orden, con tipo
 *   keyword, string, number, comment, identifier o plain; arreglo vacío si
 *   `sql` no es una cadena con contenido.
 */
export function tokenizeSql(sql) {
    if (!sql || typeof sql !== 'string') return [];
    const tokens = [];
    let match;
    TOKEN_RE.lastIndex = 0;
    while ((match = TOKEN_RE.exec(sql)) !== null) {
        const [full, str, lineComment, blockComment, number, word, space, other] = match;
        if (str) tokens.push({ text: str, type: 'string' });
        else if (lineComment || blockComment) tokens.push({ text: lineComment || blockComment, type: 'comment' });
        else if (number) tokens.push({ text: number, type: 'number' });
        else if (word) tokens.push({ text: word, type: KEYWORD_SET.has(word.toUpperCase()) ? 'keyword' : 'identifier' });
        else tokens.push({ text: space || other || full, type: 'plain' });
    }
    return tokens;
}

/** Clases de Tailwind que colorean cada tipo de token. */
export const SQL_TOKEN_CLASSNAMES = {
    keyword: 'text-[#7DA6F2] font-semibold',
    string: 'text-emerald-400',
    number: 'text-amber-300',
    comment: 'text-white/30 italic',
    identifier: 'text-white/80',
    plain: 'text-white/80',
};
