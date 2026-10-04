import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, GraduationCap, TrendingDown } from 'lucide-react';

import { apiGet } from '../../services/api';

// Panel de riesgo de abandono estudiantil: lee /ml/prediccion-abandono, que
// sirve exactamente la misma vista (VIS_PREDICCION_ABANDONO) que el chat
// NL2SQL consulta cuando se le pregunta en lenguaje natural — panel y chat
// nunca pueden mostrar numeros distintos porque comparten la fuente.
// El modelo (backend/ml/entrenar_abandono.py) se entrena sobre el panel
// alumno-periodo: con los datos hasta el periodo actual estima el riesgo de
// abandonar en el PRÓXIMO periodo. Cada alumno trae sus tres factores
// principales (SHAP) y la tarjeta muestra las métricas reales de validación
// (VIS_EVALUACION_MODELO) para que la autoridad sepa cuánto confiar.
const AVISO_DATOS = {
    UNEMI_PRUEBAS: 'Datos de prueba sintéticos y anonimizados: las métricas muestran que la arquitectura funciona, no el desempeño esperado con datos reales.',
    OULAD_UK: 'Datos reales anonimizados del Open University Learning Analytics Dataset (Kuzilek et al., 2017).',
};

const RIESGO_STYLE = {
    ALTO: { text: 'text-rose-400', border: 'border-rose-500/30', bg: 'bg-rose-500/10' },
    MEDIO: { text: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
    BAJO: { text: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' },
};

function metricaTemporal(metricas, nombre) {
    const fila = (metricas || []).find(
        (m) => m.componente === 'PREDICCION' && m.esquema_validacion === 'TEMPORAL' && m.metrica === nombre,
    );
    return fila ? Number(fila.valor) : null;
}

export function RiesgoAbandonoCard({ targetDb, delay = 0 }) {
    const [data, setData] = useState(null);
    const [metricas, setMetricas] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        if (!targetDb) return undefined;

        setLoading(true);
        setError(null);
        // Las métricas son un complemento: si fallan, el panel de riesgo se muestra igual.
        apiGet(`/ml/evaluacion-modelo?target_db=${encodeURIComponent(targetDb)}`)
            .then((res) => { if (!cancelled) setMetricas(res.data?.metricas || []); })
            .catch(() => { if (!cancelled) setMetricas([]); });
        apiGet(`/ml/prediccion-abandono?target_db=${encodeURIComponent(targetDb)}&limit=8`)
            .then((res) => {
                if (!cancelled) setData(res.data);
            })
            .catch((err) => {
                if (cancelled) return;
                // 400/503: la vista aun no tiene predicciones calculadas para esta
                // empresa (nadie ha corrido `python -m ml.predecir_abandono` todavia)
                // o no hay base conectada — el panel se oculta en silencio, no es un
                // error del usuario.
                setError(err?.response?.status || 'error');
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => { cancelled = true; };
    }, [targetDb]);

    if (!targetDb || error || (!loading && !data?.total_evaluados)) return null;

    const auc = metricaTemporal(metricas, 'ROC_AUC');
    const recall = metricaTemporal(metricas, 'RECALL');
    const aviso = AVISO_DATOS[String(targetDb).toUpperCase()]
        || 'Resultados del modelo sobre los datos de la institución conectada.';

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay }}
            className="rounded-[32px] border border-white/10 p-8 shadow-2xl"
            style={{ background: 'rgba(255,255,255,0.02)' }}
        >
            <div className="mb-5 flex items-start justify-between">
                <div>
                    <h3 className="text-[12px] font-black uppercase tracking-[0.2em] text-white/40">ACADEMICO · IA PREDICTIVA</h3>
                    <div className="flex items-center gap-2 text-[15px] font-bold text-white">
                        <TrendingDown size={16} className="text-rose-400" />
                        Riesgo de abandono estudiantil
                    </div>
                </div>
                {data && (
                    <div className="flex items-center gap-1.5 rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-[12px] font-black text-rose-300">
                        <AlertTriangle size={12} />
                        {data.resumen?.ALTO ?? 0} en riesgo alto
                    </div>
                )}
            </div>

            {loading && (
                <div className="animate-pulse space-y-2">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={i} className="h-11 rounded-xl bg-white/[0.04]" />
                    ))}
                </div>
            )}

            {!loading && data && (
                <>
                    <div className="mb-4 flex flex-wrap gap-2">
                        {['ALTO', 'MEDIO', 'BAJO'].map((cat) => (
                            <span
                                key={cat}
                                className={`rounded-lg border px-2.5 py-1 text-[11px] font-black uppercase tracking-wide ${RIESGO_STYLE[cat].border} ${RIESGO_STYLE[cat].bg} ${RIESGO_STYLE[cat].text}`}
                            >
                                {cat}: {data.resumen?.[cat] ?? 0}
                            </span>
                        ))}
                        <span className="rounded-lg border border-white/10 bg-black/20 px-2.5 py-1 text-[11px] font-bold text-white/40">
                            de {data.total_evaluados} activos evaluados · riesgo para el próximo periodo
                        </span>
                        {auc !== null && (
                            <span
                                className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-[11px] font-bold text-cyan-200"
                                title="Validación temporal: el modelo se evaluó sobre los periodos más recientes, que no vio al entrenar."
                            >
                                Confiabilidad: ROC-AUC {auc.toFixed(2)}{recall !== null ? ` · detecta ${(recall * 100).toFixed(0)} % de los abandonos` : ''}
                            </span>
                        )}
                    </div>

                    <div className="overflow-hidden rounded-2xl border border-white/5">
                        <table className="w-full text-left text-[13px]">
                            <thead>
                                <tr className="bg-white/[0.03] text-[10px] uppercase tracking-wider text-white/35">
                                    <th className="px-4 py-2 font-bold">Alumno</th>
                                    <th className="px-4 py-2 font-bold">Carrera</th>
                                    <th className="px-4 py-2 font-bold text-right">Probabilidad</th>
                                    <th className="px-4 py-2 font-bold text-right">Riesgo</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(data.alumnos || []).map((a) => (
                                    <tr key={a.cedula} className="border-t border-white/5">
                                        <td className="px-4 py-2.5 text-white/80">
                                            <div className="flex items-center gap-2">
                                                <GraduationCap size={13} className="shrink-0 text-white/25" />
                                                <span className="truncate">{a.apellidos} {a.nombres}</span>
                                                <span className="shrink-0 text-[10px] text-white/30">{a.cedula}</span>
                                            </div>
                                            {a.factores?.length > 0 && (
                                                <ul className="mt-1 space-y-0.5 pl-5 text-[10.5px] leading-snug text-white/45">
                                                    {a.factores.map((f) => <li key={f}>· {f}</li>)}
                                                </ul>
                                            )}
                                        </td>
                                        <td className="px-4 py-2.5 text-white/50">{a.carrera}</td>
                                        <td className="px-4 py-2.5 text-right font-bold text-white/70">
                                            {(a.probabilidad * 100).toFixed(0)}%
                                        </td>
                                        <td className="px-4 py-2.5 text-right">
                                            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-black uppercase ${RIESGO_STYLE[a.riesgo_categoria]?.border} ${RIESGO_STYLE[a.riesgo_categoria]?.bg} ${RIESGO_STYLE[a.riesgo_categoria]?.text}`}>
                                                {a.riesgo_categoria}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <p className="mt-3 text-[11px] leading-relaxed text-white/30 italic">
                        Con los datos de cada alumno hasta su periodo actual, el modelo estima el riesgo de que abandone
                        en el próximo; bajo cada nombre, las tres razones que más pesan en su caso. {aviso} Pregunta en
                        el chat para ver el listado completo.
                    </p>
                </>
            )}
        </motion.div>
    );
}
