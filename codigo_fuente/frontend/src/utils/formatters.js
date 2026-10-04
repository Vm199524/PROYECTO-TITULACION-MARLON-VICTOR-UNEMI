const MONTH_NAMES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

export const formatValue = (val, columnName = '') => {
    if (val === null || val === undefined) return '-';
    const strVal = String(val).trim();
    if (strVal === '') return '-';

    // 1. Regla para Identificaciones (Cédula, RUC, ID) - DEBE SER TEXTO PURO
    const isIdCol = /cédula|cedula|ruc|identificacion|id|código|codigo/i.test(columnName);
    
    // Heurística de Seguridad: Si el valor es un entero largo (9-11 dígitos) y no hay nombre de columna,
    // es casi seguro que es una Cédula o RUC. No debemos ponerle puntos.
    const isLikelyId = !columnName && Number.isInteger(val) && String(val).length >= 9 && String(val).length <= 11;

    if (isIdCol || isLikelyId) {
        // Limpiar cualquier punto o coma que haya venido del backend por error de casteo
        return strVal.replace(/[.,]/g, '');
    }

    // 2. Regla para Años (Evitar puntos en 2024, 2025, etc)
    const isYearCol = /año|anio|year|ejercicio/i.test(columnName);
    if (isYearCol && /^\d{4}$/.test(strVal)) {
        return strVal;
    }

    // 3. Regla de Meses en Letras
    // Solo aplica a columnas cuyo nombre SEA el mes (Mes, Month, Periodo, MesNombre, NombreMes)
    // EXCLUYE columnas de código/número: MesNumero, NumMes, MonthNumber, NroMes, MesCodigo, etc.
    const isNumericIdSuffix = /numero|num|nro|number|code|codigo|id|idx|index/i.test(columnName);
    const isMonthCol = /mes|month|periodo/i.test(columnName) && !isNumericIdSuffix;
    const num = parseInt(strVal, 10);
    if (isMonthCol && num >= 1 && num <= 12 && /^\d+$/.test(strVal)) {
        return MONTH_NAMES[num - 1];
    }

    // 4. Regla de Fechas (YYYY.MM.DD -> YYYY-Mes-DD)
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

    // 4b. Salvaguarda para columnas de fecha con un valor que NO trae
    // día/mes (ej. el backend devolvió solo el año, "2026"). Bug real
    // detectado en pruebas (29/08/2026): al no calzar con el patrón de
    // fecha de arriba, ese "2026" caía en la regla numérica de más abajo y
    // se mostraba como "2.026" (con separador de miles), como si fuera una
    // cifra de dinero. Una columna de fecha nunca debe pasar por el
    // formateador de números — se muestra tal cual llegó.
    const isDateCol = /fecha|\bdate\b/i.test(columnName);
    if (isDateCol) {
        return strVal;
    }

    // Autocompletar ceros a la izquierda para cédulas cortas (Ecuador)
    if (/^\d+$/.test(strVal) && strVal.length >= 9 && strVal.length <= 15 && isIdCol) {
        return strVal.length === 9 ? '0' + strVal : strVal;
    }

    const hasLetters = /[a-zA-Z\u00C0-\u024F]/.test(strVal);
    
    if (!hasLetters) {
        const numericValue = typeof val === 'number' ? val : parseNum(strVal);
        if (typeof val !== 'boolean' && isFinite(numericValue)) {
            // Si es un código que empieza con cero, no formatear como número
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

export const formatHeader = (header) => {
    const normalized = String(header || '').trim().toLowerCase();
    if (normalized === 'anio' || normalized === 'ano') return 'Año';
    if (normalized === 'periodoanio' || normalized === 'periodo anio') return 'Período Año';
    const splitCamel = header.replace(/([A-Z])/g, ' $1').trim();
    return splitCamel.replace(/_/g, ' ').split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ').trim();
};

export const formatAxisName = (name) => {
    if (!name) return '';
    // Limpiar caracteres invisibles del hack de duplicados y espacios extras
    const str = String(name).replace(/[\u200B]/g, '').trim();
    
    // 1. Regla de Meses
    const num = parseInt(str, 10);
    if (/^\d+$/.test(str) && num >= 1 && num <= 12) {
        return MONTH_NAMES[num - 1];
    }

    // 2. Regla de Nombres de Personas (Ej: "PEÑAFIEL RUIZ JORGE" -> "JORGE P.")
    // Si parece ser un nombre largo, mostrar primer nombre e inicial de apellido
    if (str.length > 12 && str.includes(' ')) {
        const words = str.split(' ').filter(w => w.length > 2);
        if (words.length >= 2) {
            // Si el nombre viene en formato APELLIDO NOMBRE, intentamos detectar
            // Para simplicidad, tomamos la primera palabra y la inicial de la segunda
            return `${words[0]} ${words[1][0]}.`;
        }
    }

    // 3. Recorte simple si sigue siendo largo
    if (str.length > 15) {
        return str.slice(0, 12) + '...';
    }

    return str;
};

export const parseNum = (val) => {
    if (val === null || val === undefined || val === '') return 0;
    if (typeof val === 'number') return isFinite(val) ? val : 0;
    
    let str = String(val).trim();
    
    // Detectar formato latino: "1.234,56"
    // Si tiene punto Y coma, y la coma está después, el punto es de miles.
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
            // Si afterDot.length !== 3 -> tratar como decimal (comportamiento anterior)
        }
    }

    const cleaned = str.replace(/[^\d.-]/g, '');
    const n = parseFloat(cleaned);
    return isFinite(n) ? n : NaN;
};

