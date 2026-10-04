function stripGenericRowCountMessage(message, rows) {
    const text = String(message || '').trim();
    if (!text) return '';

    const boilerplatePatterns = [
        /^se recuperaron\s+\d+\s+registros?\s+para\s+su\s+consulta\.?$/i,
        /^se encontraron\s+\d+\s+registros?(?:\s+para\s+su\s+consulta)?\.?$/i,
        /^consulta ejecutada\s+correctamente\.?$/i,
    ];

    const cleanedLines = text
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter((line) => line && !boilerplatePatterns.some((pattern) => pattern.test(line)));

    if (cleanedLines.length > 0) {
        return cleanedLines.join('\n').trim();
    }

    if (Array.isArray(rows) && rows.length > 0) {
        return '';
    }

    return text;
}

export function normalizeQueryResult(raw) {
    const source = raw || {};
    const rows = source?.data?.rows || source?.rows || [];
    const columns = source?.data?.columns || source?.columns || [];
    const renderType = source?.render?.type || source?.visualization_type || 'text';
    const sqlText = typeof source?.sql === 'object'
        ? (source?.sql?.text || '')
        : (source?.sql_query || source?.sql || '');
    const analysisSteps = source?.analysis?.steps || source?.agent_log || [];
    const analysisSummary = source?.analysis?.summary || source?.business_analysis || '';
    const rawMessage = source?.message || source?.explanation || '';
    // Solo eliminar mensajes boilerplate si hay filas Y hay otro contenido (business_analysis o analysisSummary)
    // Si el mensaje es el ÚNICO contenido disponible, conservarlo siempre.
    const hasRicherContext = !!(source?.business_analysis || source?.analysis?.summary);
    const message = (hasRicherContext && rows.length > 0)
        ? stripGenericRowCountMessage(rawMessage, rows)
        : rawMessage.trim();
    const status = source?.status || (rows?.length ? 'success' : 'conversation');
    const payslipMeta = source?.data?.payslip_meta || source?.payslip_meta || source?.meta?.payslip_meta || [];

    return {
        ...source,
        status,
        message,
        // Antes: `message || rawMessage.trim()` — cuando message se vacía
        // intencionalmente (boilerplate limpiado), el `||` revertía al texto
        // sin limpiar, deshaciendo la limpieza solo en este campo. Corregido.
        explanation: message,
        rows,
        columns,
        render: {
            type: renderType,
            title: source?.render?.title || source?.viz_config?.title || '',
            subtitle: source?.render?.subtitle || source?.viz_config?.subtitle || '',
        },
        render_type: renderType,
        visualization_type: renderType,
        sql: {
            text: sqlText,
            executed: typeof source?.sql === 'object' ? !!source?.sql?.executed : !!sqlText,
            corrected: typeof source?.sql === 'object' ? !!source?.sql?.corrected : !!source?.auto_corrected,
            dialect: typeof source?.sql === 'object' ? (source?.sql?.dialect || '') : '',
        },
        sql_query: sqlText,
        analysis: {
            summary: analysisSummary,
            steps: Array.isArray(analysisSteps) ? analysisSteps : [String(analysisSteps)],
            confidence: source?.analysis?.confidence || 0,
            source: source?.analysis?.source || '',
        },
        business_analysis: analysisSummary,
        agent_log: Array.isArray(analysisSteps) ? analysisSteps : [String(analysisSteps)],
        payslip_meta: payslipMeta,
    };
}
