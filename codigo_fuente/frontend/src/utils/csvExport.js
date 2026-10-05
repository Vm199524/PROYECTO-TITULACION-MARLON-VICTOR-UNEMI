/**
 * @file Exportación de datos a CSV. Genera el archivo con los datos reales (no
 * una captura de pantalla) desde cualquier vista: tabla de resultados del chat,
 * tablero BI, etc. No usa dependencias externas porque un CSV es texto plano.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

// Quita el marcador invisible de duplicados (\u200B) y entrecomilla la celda
// si contiene ';', comillas o saltos de línea.
const escapeCsvCell = (value) => {
    const clean = String(value ?? '').replace(/[\u200B]/g, '').trim();
    if (/[";\n]/.test(clean)) return '"' + clean.replace(/"/g, '""') + '"';
    return clean;
};

/**
 * Construye el contenido CSV, con BOM UTF-8 y filas separadas por CRLF.
 * @param {Array<Array<*>>} rows Filas, cada una ya en el orden final de columnas.
 * @returns {string} Texto CSV listo para descargar.
 */
export const buildCsv = (rows) => {
    // Delimitador ';' (no ',') porque Excel con configuración regional en
    // español (es-EC) usa ',' como separador decimal y asume ';' como
    // separador de columnas; con ',' todo aparece junto en la columna A. La
    // directiva "sep=," combinada con el BOM UTF-8 hace que Excel pierda la
    // detección de codificación y muestre mal las tildes y la ñ. Con ';', el
    // separador nativo de esa región, no hace falta directiva y el BOM
    // funciona con normalidad.
    const lines = rows.map((row) => row.map(escapeCsvCell).join(';'));
    // BOM al inicio para que Excel detecte UTF-8 y no rompa tildes/ñ.
    return '\uFEFF' + lines.join('\r\n');
};

/**
 * Descarga un texto CSV en el navegador mediante un enlace temporal.
 * @param {string} csvContent Contenido CSV.
 * @param {string} filename Nombre del archivo; se agrega `.csv` si falta.
 * @returns {void}
 */
export const downloadCsvContent = (csvContent, filename) => {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
};

/**
 * Construye el CSV a partir de las filas y lo descarga.
 * @param {Array<Array<*>>} rows Filas en el orden final de columnas.
 * @param {string} filename Nombre del archivo.
 * @returns {void}
 */
export const downloadRowsAsCsv = (rows, filename) => {
    downloadCsvContent(buildCsv(rows), filename);
};
