// csvExport.js
// Utilidad compartida para exportar datos reales a CSV (no una captura de
// pantalla) desde cualquier vista: tabla de resultados del chat, dashboard
// BI, etc. Sin dependencias externas — un CSV es texto plano, no hace falta
// una librería para generarlo.

const escapeCsvCell = (value) => {
    const clean = String(value ?? '').replace(/[\u200B]/g, '').trim();
    if (/[";\n]/.test(clean)) return '"' + clean.replace(/"/g, '""') + '"';
    return clean;
};

// `rows` es un array de arrays (cada fila ya en el orden final de columnas).
export const buildCsv = (rows) => {
    // Delimitador ';' (no ',') porque Excel en configuracion regional en
    // espanol (es-EC) usa ',' como separador DECIMAL, y por lo tanto asume
    // ';' como separador de columnas al abrir un CSV -- exactamente el bug
    // reportado ("todo aparece junto en la columna A"). Antes probamos la
    // directiva "sep=," para forzar coma igual, pero combinada con el BOM
    // UTF-8 hacia que Excel perdiera la deteccion de codificacion y mostrara
    // tildes/enie como simbolos ("Ã³" en vez de "o con tilde"). Usar ';'
    // (el separador nativo de ese idioma/region) evita el conflicto por completo:
    // no hace falta directiva ni trucos, y el BOM solo sigue funcionando normal.
    const lines = rows.map((row) => row.map(escapeCsvCell).join(';'));
    // BOM al inicio para que Excel detecte UTF-8 y no rompa tildes/ñ.
    return '\uFEFF' + lines.join('\r\n');
};

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

export const downloadRowsAsCsv = (rows, filename) => {
    downloadCsvContent(buildCsv(rows), filename);
};
