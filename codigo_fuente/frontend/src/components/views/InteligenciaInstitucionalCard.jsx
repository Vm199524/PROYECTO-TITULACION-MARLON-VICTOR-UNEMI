import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Building2, Network, Scale } from 'lucide-react';

import { apiGet } from '../../services/api';

// Módulo 2 del work package (Benchmarking con enfoque en inteligencia
// institucional): dos secciones sobre la MISMA fuente que consulta el chat
// (VIS_CLUSTER_CARRERA / VIS_BENCHMARK_EXTERNO — ver
// documentacion/tecnica/BENCHMARKING_INSTITUCIONAL.md):
//   1. Clustering institucional: segmenta las carreras propias por perfil
//      de riesgo (K-Means sobre tasa de abandono, rendimiento y riesgo
//      actual del modelo predictivo).
//   2. Benchmarking externo: compara la tasa de abandono propia contra
//      referentes publicados en fuentes académicas con DOI, cada uno con su
//      nivel de comparabilidad (Lepori & Bornmann, 2026: pares con pares).
const COMPARABILIDAD_STYLE = {
    ALTA: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    MEDIA: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    BAJA: 'border-white/15 bg-white/5 text-white/50',
};

const CLUSTER_STYLE = {
    'Atencion prioritaria': { text: 'text-rose-400', border: 'border-rose-500/30', bg: 'bg-rose-500/10' },
    'Estable': { text: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
    'Bajo riesgo / alto rendimiento': { text: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' },
};

export function InteligenciaInstitucionalCard({ targetDb, delay = 0 }) {
    const [clusters, setClusters] = useState(null);
    const [benchmark, setBenchmark] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        if (!targetDb) return undefined;

        setLoading(true);
        setError(null);
        Promise.all([
            apiGet(`/ml/clusters-carrera?target_db=${encodeURIComponent(targetDb)}`),
            apiGet(`/benchmarking/comparativo?target_db=${encodeURIComponent(targetDb)}`),
        ])
            .then(([resClusters, resBenchmark]) => {
                if (cancelled) return;
                setClusters(resClusters.data);
                setBenchmark(resBenchmark.data);
            })
            .catch((err) => {
                if (!cancelled) setError(err?.response?.status || 'error');
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => { cancelled = true; };
    }, [targetDb]);

    if (!targetDb || error) return null;
    if (!loading && !clusters?.carreras?.length && !benchmark?.externo?.length) return null;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay }}
            className="rounded-[32px] border border-white/10 p-8 shadow-2xl"
            style={{ background: 'rgba(255,255,255,0.02)' }}
        >
            <div className="mb-5">
                <h3 className="text-[12px] font-black uppercase tracking-[0.2em] text-white/40">ACADEMICO · INTELIGENCIA INSTITUCIONAL</h3>
                <div className="flex items-center gap-2 text-[15px] font-bold text-white">
                    <Network size={16} className="text-indigo-400" />
                    Clustering de carreras y benchmarking externo
                </div>
            </div>

            {loading && (
                <div className="animate-pulse space-y-2">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="h-11 rounded-xl bg-white/[0.04]" />
                    ))}
                </div>
            )}

            {!loading && (
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                    {/* ── Clustering institucional ── */}
                    {clusters?.carreras?.length > 0 && (
                        <div>
                            <div className="mb-2 flex items-center gap-1.5 text-[11px] font-black uppercase tracking-wide text-white/40">
                                <Building2 size={13} /> Segmentación por carrera
                            </div>
                            <div className="overflow-hidden rounded-2xl border border-white/5">
                                <table className="w-full text-left text-[12px]">
                                    <thead>
                                        <tr className="bg-white/[0.03] text-[10px] uppercase tracking-wider text-white/35">
                                            <th className="px-3 py-2 font-bold">Carrera</th>
                                            <th className="px-3 py-2 font-bold text-right">Abandono hist.</th>
                                            <th className="px-3 py-2 font-bold text-right">Segmento</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {clusters.carreras.slice(0, 8).map((c) => (
                                            <tr key={c.carrera} className="border-t border-white/5">
                                                <td className="px-3 py-2 text-white/75 truncate max-w-[180px]">{c.carrera}</td>
                                                <td className="px-3 py-2 text-right text-white/60">{(c.tasa_abandono_hist * 100).toFixed(1)}%</td>
                                                <td className="px-3 py-2 text-right">
                                                    <span className={`rounded-full border px-2 py-0.5 text-[9px] font-black uppercase ${CLUSTER_STYLE[c.cluster_label]?.border} ${CLUSTER_STYLE[c.cluster_label]?.bg} ${CLUSTER_STYLE[c.cluster_label]?.text}`}>
                                                        {c.cluster_label}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            <p className="mt-2 text-[10px] leading-relaxed text-white/30 italic">
                                K-Means sobre tasa de abandono histórica, rendimiento y riesgo actual del modelo predictivo.
                            </p>
                        </div>
                    )}

                    {/* ── Benchmarking externo ── */}
                    {benchmark?.externo?.length > 0 && (
                        <div>
                            <div className="mb-2 flex items-center gap-1.5 text-[11px] font-black uppercase tracking-wide text-white/40">
                                <Scale size={13} /> Benchmarking externo (fuentes académicas)
                            </div>
                            {benchmark.propio?.tasa_abandono_pct !== null && (
                                <div className="mb-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-[12px] text-cyan-200">
                                    <strong>{benchmark.propio.nombre}</strong> (propio): {benchmark.propio.tasa_abandono_pct}% de abandono
                                    <span className="text-white/40"> · {benchmark.propio.alumnos_evaluados} evaluados</span>
                                </div>
                            )}
                            <div className="overflow-hidden rounded-2xl border border-white/5">
                                <table className="w-full text-left text-[12px]">
                                    <thead>
                                        <tr className="bg-white/[0.03] text-[10px] uppercase tracking-wider text-white/35">
                                            <th className="px-3 py-2 font-bold">Referente</th>
                                            <th className="px-3 py-2 font-bold text-right">Abandono</th>
                                            <th className="px-3 py-2 font-bold text-right">Comparable</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {benchmark.externo
                                            .filter((b) => b.indicador_codigo === 'TASA_ABANDONO')
                                            .map((b) => (
                                                <tr key={`${b.institucion_codigo}-${b.indicador_codigo}`} className="border-t border-white/5">
                                                    <td className="px-3 py-2 text-white/75" title={b.definicion_indicador}>
                                                        <div className="truncate max-w-[170px]">{b.pais} · {b.modalidad?.toLowerCase().replace('_', ' ')}</div>
                                                        <a
                                                            href={b.url_fuente || (b.doi ? `https://doi.org/${b.doi}` : undefined)}
                                                            target="_blank"
                                                            rel="noreferrer"
                                                            className="text-[10px] text-cyan-300/70 hover:underline"
                                                        >
                                                            {b.fuente}
                                                        </a>
                                                    </td>
                                                    <td className="px-3 py-2 text-right font-bold text-white/70">{Number(b.valor).toFixed(1)}{b.unidad}</td>
                                                    <td className="px-3 py-2 text-right">
                                                        <span className={`rounded-full border px-2 py-0.5 text-[9px] font-black uppercase ${COMPARABILIDAD_STYLE[b.nivel_comparabilidad] || COMPARABILIDAD_STYLE.BAJA}`}>
                                                            {b.nivel_comparabilidad}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>
                                </table>
                            </div>
                            <p className="mt-2 text-[10px] leading-relaxed text-white/30 italic">
                                Cifras publicadas en artículos con DOI; pasa el cursor sobre cada referente para ver qué mide exactamente.
                                Comparabilidad: alta = mismo país y nivel; media = pregrado en otro país; baja = otra modalidad o unidad de medida.
                            </p>
                        </div>
                    )}
                </div>
            )}
        </motion.div>
    );
}
