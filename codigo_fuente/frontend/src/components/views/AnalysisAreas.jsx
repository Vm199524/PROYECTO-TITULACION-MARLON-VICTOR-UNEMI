/**
 * @file Vista «Áreas de Análisis». Muestra en tarjetas las áreas temáticas
 * (académico, finanzas, RR. HH., etc.) que el backend detecta en el esquema de la
 * base activa, marcando cuáles están disponibles y cuáles bloqueadas. Lee los datos
 * de /api/context-overview mediante el hook useContextOverview.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */
import React from 'react';
import { motion } from 'framer-motion';
import { BarChart2, Briefcase, Database, FileSpreadsheet, GraduationCap, Lock, RefreshCw } from 'lucide-react';

import { useContextOverview } from '../../hooks/useContextOverview';

// Ícono por identificador de área; las áreas desconocidas usan Database.
const AREA_ICONS = {
    rrhh: FileSpreadsheet,
    ventas: Briefcase,
    operaciones: Database,
    finanzas: BarChart2,
    academico: GraduationCap,
    general: Database,
};

// Tarjeta de un área: ícono, nombre, descripción y estado (disponible o bloqueada).
function AreaCard({ area }) {
    const Icon = AREA_ICONS[area?.id] || Database;
    const locked = area?.status === 'locked';
    return (
        <div
            className={`relative rounded-2xl p-6 border transition-all ${
                locked
                    ? 'bg-black/40 border-white/5 opacity-60 cursor-not-allowed'
                    : 'bg-white/5 border-white/10 hover:border-cyan-500/50 hover:bg-gradient-to-br hover:from-cyan-900/10 hover:to-transparent'
            }`}
        >
            {locked && (
                <div className="absolute top-4 right-4">
                    <Lock size={16} className="text-white/30" />
                </div>
            )}
            <div className={`p-3 rounded-xl inline-flex mb-4 transition-colors ${
                locked ? 'bg-white/5 text-white/30' : 'bg-black/50 border border-white/5 text-cyan-400'
            }`}>
                <Icon size={24} />
            </div>
            <h3 className="text-white font-bold text-lg mb-2">{area?.name}</h3>
            <p className="text-xs text-white/50 leading-relaxed mb-4">{area?.desc}</p>
            <div className={`inline-flex rounded-full px-3 py-1 text-[12px] font-black uppercase tracking-[0.18em] ${
                locked ? 'bg-white/5 text-white/35' : 'bg-cyan-500/10 text-cyan-300'
            }`}>
                {locked ? 'Bloqueado' : 'Disponible'}
            </div>
        </div>
    );
}

/**
 * Muestra la cuadrícula de áreas de análisis de la base activa con un botón para
 * refrescarla.
 *
 * @param {object} props
 * @param {string} props.dbId - Identificador de la base cuyas áreas se consultan.
 * @param {boolean} [props.enabled=true] - Si es false, no se consulta el backend.
 * @returns {JSX.Element} Vista de áreas de análisis.
 */
export function AnalysisAreas({ dbId, enabled = true }) {
    const { overview, loading, error, reloadOverview } = useContextOverview(dbId, enabled);
    const areas = overview?.areas || [];

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full h-full p-8 overflow-y-auto custom-scrollbar flex flex-col items-center"
        >
            <div className="w-full max-w-5xl flex flex-col gap-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-3">
                        <BarChart2 className="text-cyan-400" size={24} />
                        <h1 className="text-2xl font-bold text-white tracking-wide">Áreas de Análisis</h1>
                    </div>
                    <button
                        type="button"
                        onClick={() => reloadOverview(true)}
                        className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-[12px] font-black uppercase tracking-[0.18em] text-white/70 transition-colors hover:border-cyan-400/35 hover:text-cyan-300"
                    >
                        <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
                        Refrescar
                    </button>
                </div>

                <p className="text-white/60 text-sm leading-relaxed max-w-3xl">
                    Esta vista ahora se arma según el esquema detectado en la base activa. VicMar Data AI ya no debería ofrecer
                    siempre Finanzas, Ventas y RRHH si el origen seleccionado es académico, operativo o mixto.
                </p>

                {error && (
                    <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
                        {error}
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
                    {areas.length ? areas.map((area) => (
                        <AreaCard key={area.id} area={area} />
                    )) : (
                        <div className="lg:col-span-3 rounded-2xl border border-dashed border-white/12 bg-white/[0.03] px-5 py-6 text-sm leading-6 text-white/45">
                            {loading ? 'Detectando áreas de análisis para la base activa...' : 'Aún no hay áreas contextuales detectadas para este origen.'}
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );
}
