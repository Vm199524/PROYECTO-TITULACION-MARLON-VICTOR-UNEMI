/**
 * @file Formateo de valores para tablas, gráficos y exportaciones. Aplica
 * reglas según el nombre de la columna (identificaciones sin separadores,
 * años, meses en letras, fechas) y el formato numérico es-EC; también da
 * formato a encabezados y etiquetas de eje e interpreta números en formato
 * latino o anglosajón.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

const MONTH_NAMES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

/**
 * Da formato de presentación a un valor de celda según su columna.
 * @param {*} val Valor crudo devuelto por la consulta.
 * @param {string} [columnName=''] Nombre de la columna, usado para elegir la regla.
 * @returns {string} Valor listo para mostrar; '-' si está vacío.
 */
export const formatValue = (val, columnName = '') => {
    if (val === null || val === undefined) return '-';
    const strVal = String(val).trim();
    if (strVal === '') return '-';

    // 1. Identificaciones (cédula, RUC, ID): se muestran como texto puro.
    const isIdCol = /cédula|cedula|ruc|identificacion|id|código|codigo/i.test(columnName);
    
    // Sin nombre de columna, un entero de 9 a 11 dígitos es casi seguro una
    // cédula o un RUC, así que no lleva separadores de miles.
    const isLikelyId = !columnName && Number.isInteger(val) && String(val).length >= 9 && String(val).length <= 11;

    if (isIdCol || isLikelyId) {
        // Quita puntos o comas que hayan llegado del backend por un error de conversión.
        return strVal.replace(/[.,]/g, '');
    }

    // 2. Años: sin separador de miles (2024, no 2.024).
    const isYearCol = /año|anio|year|ejercicio/i.test(columnName);
    if (isYearCol && /^\d{4}$/.test(strVal)) {
        return strVal;
    }

    // 3. Meses en letras. Solo aplica a columnas cuyo nombre es el mes (Mes,
    // Month, Periodo, MesNombre, NombreMes); excluye las de código o número
    // (MesNumero, NumMes, MonthNumber, NroMes, MesCodigo, etc.).
    const isNumericIdSuffix = /numero|num|nro|number|code|codigo|id|idx|index/i.test(columnName);
    const isMonthCol = /mes|month|periodo/i.test(columnName) && !isNumericIdSuffix;
    const num = parseInt(strVal, 10);
    if (isMonthCol && num >= 1 && num <= 12 && /^\d+$/.test(strVal)) {
        return MONTH_NAMES[num - 1];
    }

    // 4. Fechas: AAAA.MM.DD (o con - y /) se muestra como AAAA-Mes-DD.
    const datePattern = /^(\d{4})[./-](\d{1,2})[./-](\d{1,2})/;
    const match = strVal.match(datePattern);
    if (match) {
        const year = match[1];
        const monthIndex = parseInt(match[2], 10);
        const day = match[3].padStart(2, '0');
        if (monthIndex >= 1 && monthIndex <= 12) {
            return `${year}-${MONTH_NAMES[monthIndex - 1]}-${day}`;
        }
    }

    // 4b. Columnas de fecha cuyo valor no trae día ni mes (p. ej. solo el
    // año, "2026"): no calzan con el patrón anterior y, sin esta regla,
    // caerían en el formateador numérico y se verían como "2.026", como si
    // fueran una cifra de dinero. Una columna de fecha se muestra tal cual
    // llegó.
    const isDateCol = /fecha|\bdate\b/i.test(columnName);
    if (isDateCol) {
        return strVal;
    }

    // Completa el cero inicial de las cédulas ecuatorianas de 9 dígitos.
    if (/^\d+$/.test(strVal) && strVal.length >= 9 && strVal.length <= 15 && isIdCol) {
        return strVal.length === 9 ? '0' + strVal : strVal;
    }

    const hasLetters = /[a-zA-Z\u00C0-\u024F]/.test(strVal);
    
    if (!hasLetters) {
        const numericValue = typeof val === 'number' ? val : parseNum(strVal);
        if (typeof val !== 'boolean' && isFinite(numericValue)) {
            // Un código que empieza con cero no se formatea como número.
            if (typeof val !== 'number' && /^0\d+$/.test(strVal)) {
                return strVal;
            }
            if (Number.isInteger(numericValue)) {
                return numericValue.toLocaleString('es-EC', { maximumFractionDigits: 0 });
            }
            return numericValue.toLocaleString('es-EC', { 
                minimumFractionDigits: 2, 
                maximumFractionDigits: 2 
                });
            }
        }
        
        return strVal;
    };

/**
 * Convierte el nombre técnico de una columna en un encabezado legible
 * (separa camelCase y guiones bajos y capitaliza cada palabra).
 * @param {string} header Nombre de la columna.
 * @returns {string} Encabezado para mostrar.
 */
export const formatHeader = (header) => {
    const normalized = String(header || '').trim().toLowerCase();
    if (normalized === 'anio' || normalized === 'ano') return 'Año';
    if (normalized === 'periodoanio' || normalized === 'periodo anio') return 'Período Año';
    const splitCamel = header.replace(/([A-Z])/g, ' $1').trim();
    return splitCamel.replace(/_/g, ' ').split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ').trim();
};

/**
 * Acorta una etiqueta de eje de gráfico: números 1 a 12 como meses, nombres
 * largos como primera palabra más inicial y textos largos recortados.
 * @param {*} name Etiqueta original.
 * @returns {string} Etiqueta corta para el eje.
 */
export const formatAxisName = (name) => {
    if (!name) return '';
    // Quita el marcador invisible de duplicados (\u200B) que agrega
    // DataVisualizer y los espacios sobrantes.
    const str = String(name).replace(/[\u200B]/g, '').trim();
    
    // 1. Meses
    const num = parseInt(str, 10);
    if (/^\d+$/.test(str) && num >= 1 && num <= 12) {
        return MONTH_NAMES[num - 1];
    }

    // 2. Nombres de personas largos: primera palabra e inicial de la segunda
    // (p. ej. "PEÑAFIEL RUIZ JORGE" -> "PEÑAFIEL R.").
    if (str.length > 12 && str.includes(' ')) {
        const words = str.split(' ').filter(w => w.length > 2);
        if (words.length >= 2) {
            // No se distingue el orden APELLIDO NOMBRE: por simplicidad se usa
            // la primera palabra y la inicial de la segunda.
            return `${words[0]} ${words[1][0]}.`;
        }
    }

    // 3. Recorte simple si sigue siendo largo.
    if (str.length > 15) {
        return str.slice(0, 12) + '...';
    }

    return str;
};

/**
 * Interpreta un número escrito en formato latino ("1.234,56") o anglosajón
 * ("1,234.56"), resolviendo la ambigüedad de un solo punto por la cantidad de
 * dígitos que le siguen.
 * @param {*} val Valor numérico o texto.
 * @returns {number} El número; 0 si está vacío o no es finito, NaN si el
 *   texto no se puede interpretar.
 */
export const parseNum = (val) => {
    if (val === null || val === undefined || val === '') return 0;
    if (typeof val === 'number') return isFinite(val) ? val : 0;
    
    let str = String(val).trim();
    
    // Formato latino "1.234,56": si tiene punto y coma, y la coma está
    // después, el punto es separador de miles.
    const hasComma = str.includes(',');
    const hasDot = str.includes('.');
    
    if (hasComma && hasDot) {
        if (str.indexOf(',') > str.indexOf('.')) {
            // Caso 1.234,56 -> miles: punto, decimal: coma
            str = str.replace(/\./g, '').replace(',', '.');
        } else {
            // Caso 1,234.56 -> miles: coma, decimal: punto
            str = str.replace(/,/g, '');
        }
    } else if (hasComma) {
        // Caso 1234,56 -> solo coma -> tratar coma como decimal
        str = str.replace(',', '.');
    } else if (hasDot) {
        const dots = (str.match(/\./g) || []).length;
        if (dots > 1) {
            // Múltiples puntos -> definitivamente separadores de miles
            str = str.replace(/\./g, '');
        } else {
            // Un solo punto: resolver ambigüedad por el patrón
            // "61.541" -> 3 dígitos después del punto -> separador de miles europeo
            // "73.64"  -> 2 dígitos después del punto -> decimal
            // "3.5"    -> 1 dígito después del punto  -> decimal
            const afterDot = str.split('.')[1] || '';
            if (afterDot.length === 3 && /^\d{3}$/.test(afterDot)) {
                // Patrón X.XXX -> miles europeo (eliminar punto)
                str = str.replace(/\./g, '');
            }
            // Con otra cantidad de dígitos, el punto se trata como decimal.
        }
    }

    const cleaned = str.replace(/[^\d.-]/g, '');
    const n = parseFloat(cleaned);
    return isFinite(n) ? n : NaN;
};

