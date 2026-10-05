/**
 * @file Registro de auditoría del sistema. Muestra los eventos que el backend escribe
 * en core/audit_log.py (inicios de sesión, creación, edición y eliminación de usuarios,
 * cambios de perfil) con cuatro tarjetas de estadística, filtros por texto, acción,
 * entidad y fechas, y exportación a Excel. Lee /api/admin/audit y
 * /api/admin/audit/export; solo lo ve el rol ADMINISTRADOR.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React, { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Ban, Download, FilePlus, Pencil, Search, Shield, Trash2, X,
} from 'lucide-react';
import { apiGet } from '../../services/api';

// Ícono y color de la etiqueta de cada tipo de acción registrada.
const ICONO_ACCION = {
    crear: FilePlus,
    editar: Pencil,
    eliminar: Trash2,
    login: Shield,
    logout: Shield,
    activar: Shield,
    desactivar: Ban,
};

const COLOR_ACCION = {
    crear: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    editar: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
    eliminar: 'border-red-500/30 bg-red-500/10 text-red-400',
    login: 'border-blue-500/30 bg-blue-500/10 text-blue-300',
    logout: 'border-white/20 bg-white/5 text-white/50',
    activar: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    desactivar: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
};

// Formatea una fecha ISO en formato corto de Ecuador; si no es válida, la devuelve tal cual.
function formatFecha(iso) {
    if (!iso) return '—';
    try {
        return new Date(iso).toLocaleString('es-EC', { dateStyle: 'short', timeStyle: 'medium' });
    } catch {
        return iso;
    }
}

// Igual que en el campo de fecha de «Comparación por Período» (Indicadores):
// `[color-scheme:dark]` hace legible el calendario nativo en tema oscuro y
// `showPicker` lo abre al hacer clic en cualquier parte del campo.
const inputDateClass = "rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-[13px] text-white/80 outline-none focus:border-cyan-500/40 [color-scheme:dark]";
const abrirCalendario = (e) => {
    try { e.currentTarget.showPicker?.(); } catch (_err) { /* navegador sin soporte */ }
};

/**
 * Muestra el registro de auditoría con sus estadísticas, filtros y exportación.
 * Carga todos los eventos al montar y vuelve a consultar al aplicar los filtros.
 *
 * @returns {JSX.Element} Vista de auditoría.
 */
export function AdminAuditoria() {
    const [eventos, setEventos] = useState([]);
    const [stats, setStats] = useState({ total: 0, creaciones: 0, ediciones: 0, eliminaciones: 0, logins: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [exportando, setExportando] = useState(false);

    const [q, setQ] = useState('');
    const [accion, setAccion] = useState('');
    const [entidad, setEntidad] = useState('');
    const [desde, setDesde] = useState('');
    const [hasta, setHasta] = useState('');

    const cargar = useCallback(async (filtros) => {
        setLoading(true);
        setError('');
        try {
            const params = new URLSearchParams();
            if (filtros.q) params.set('q', filtros.q);
            if (filtros.accion) params.set('action', filtros.accion);
            if (filtros.entidad) params.set('entity', filtros.entidad);
            if (filtros.desde) params.set('date_from', filtros.desde);
            if (filtros.hasta) params.set('date_to', filtros.hasta);
            const res = await apiGet(`/admin/audit?${params.toString()}`);
            setEventos(res.data?.events || []);
            setStats(res.data?.stats || { total: 0, creaciones: 0, ediciones: 0, eliminaciones: 0, logins: 0 });
        } catch (err) {
            setError(err?.response?.data?.detail || 'No se pudo cargar el registro de auditoría.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { cargar({ q: '', accion: '', entidad: '', desde: '', hasta: '' }); }, [cargar]);

    const buscar = (e) => {
        e.preventDefault();
        cargar({ q, accion, entidad, desde, hasta });
    };

    const limpiar = () => {
        setQ(''); setAccion(''); setEntidad(''); setDesde(''); setHasta('');
        cargar({ q: '', accion: '', entidad: '', desde: '', hasta: '' });
    };

    const exportar = async () => {
        setExportando(true);
        try {
            const res = await apiGet('/admin/audit/export', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.download = `auditoria_${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (_err) {
            setError('No se pudo exportar el registro de auditoría.');
        } finally {
            setExportando(false);
        }
    };

    const accionesDisponibles = Array.from(new Set(eventos.map((e) => e.accion))).sort();
    const entidadesDisponibles = Array.from(new Set(eventos.map((e) => e.entidad))).sort();

    return (
        <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex h-full w-full flex-col overflow-hidden p-4 lg:p-6"
        >
            <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 overflow-hidden">
                {/* Cabecera, tarjetas y filtros no se desplazan: solo la tabla
                    de abajo hace scroll, así el título y los filtros quedan
                    siempre a la vista. */}
                <div className="flex shrink-0 flex-col gap-4">
                    <header className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                        <h1 className="flex items-center gap-2 text-xl font-black uppercase tracking-tight text-white lg:text-2xl">
                            <Shield size={28} className="text-cyan-400" aria-hidden="true" /> Registro de Auditoría
                        </h1>
                        <button
                            type="button"
                            onClick={exportar}
                            disabled={exportando}
                            className="flex items-center gap-2 self-start rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-[13px] font-bold uppercase tracking-wide text-emerald-300 transition-colors hover:bg-emerald-500/20 disabled:opacity-40"
                        >
                            <Download size={15} aria-hidden="true" /> {exportando ? 'Exportando…' : 'Exportar Excel'}
                        </button>
                    </header>

                    {error && (
                        <div role="alert" className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-5 py-3 text-[13px] text-rose-300">
                            {error}
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                        <Tarjeta label="Total eventos" value={stats.total} color="text-cyan-300" />
                        <Tarjeta label="Creaciones" value={stats.creaciones} color="text-emerald-300" />
                        <Tarjeta label="Ediciones" value={stats.ediciones} color="text-blue-300" />
                        <Tarjeta label="Inicios de sesión" value={stats.logins} color="text-amber-300" />
                    </div>

                    <form onSubmit={buscar} className="flex flex-wrap items-end gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                        <Campo label="Buscar">
                            <div className="relative">
                                <Search size={13} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/30" aria-hidden="true" />
                                <input
                                    value={q}
                                    onChange={(e) => setQ(e.target.value)}
                                    placeholder="Usuario, descripción…"
                                    className="w-56 rounded-lg border border-white/10 bg-black/40 py-2 pl-8 pr-3 text-[13px] text-white outline-none focus:border-cyan-500/40"
                                />
                            </div>
                        </Campo>
                        <Campo label="Acción">
                            <select value={accion} onChange={(e) => setAccion(e.target.value)} className="rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-[13px] text-white outline-none focus:border-cyan-500/40">
                                <option value="">Todas</option>
                                {accionesDisponibles.map((a) => <option key={a} value={a}>{a}</option>)}
                            </select>
                        </Campo>
                        <Campo label="Entidad">
                            <select value={entidad} onChange={(e) => setEntidad(e.target.value)} className="rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-[13px] text-white outline-none focus:border-cyan-500/40">
                                <option value="">Todas</option>
                                {entidadesDisponibles.map((en) => <option key={en} value={en}>{en}</option>)}
                            </select>
                        </Campo>
                        <Campo label="Desde">
                            <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} onClick={abrirCalendario} className={inputDateClass} />
                        </Campo>
                        <Campo label="Hasta">
                            <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} onClick={abrirCalendario} className={inputDateClass} />
                        </Campo>
                        <div className="flex gap-2">
                            <button type="submit" className="flex items-center gap-1.5 rounded-lg bg-cyan-500 px-4 py-2 text-[12px] font-bold uppercase tracking-wide text-black transition-colors hover:bg-cyan-400">
                                <Search size={13} aria-hidden="true" /> Buscar
                            </button>
                            <button type="button" onClick={limpiar} className="flex items-center gap-1.5 rounded-lg border border-white/10 px-4 py-2 text-[12px] font-bold uppercase tracking-wide text-white/50 hover:text-white">
                                <X size={13} aria-hidden="true" /> Limpiar
                            </button>
                        </div>
                    </form>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar">
                    {loading ? (
                        <div className="rounded-[32px] border border-white/10 p-10 text-center text-white/40 shadow-2xl" style={{ background: 'rgba(255,255,255,0.02)' }}>Cargando auditoría…</div>
                    ) : !eventos.length ? (
                        <div className="rounded-[32px] border border-white/10 p-10 text-center text-white/40 shadow-2xl" style={{ background: 'rgba(255,255,255,0.02)' }}>No hay eventos registrados con estos filtros.</div>
                    ) : (
                        <div className="rounded-[32px] border border-white/10 p-6 shadow-2xl sm:p-8" style={{ background: 'rgba(255,255,255,0.02)' }}>
                        <div className="overflow-x-auto">
                            <table className="w-full min-w-[820px] text-left text-[13px]">
                                <thead>
                                    <tr className="border-b border-white/10 text-[11px] font-bold uppercase tracking-wider text-white/40">
                                        <th className="px-4 py-3">Fecha / Hora</th>
                                        <th className="px-4 py-3">Usuario</th>
                                        <th className="px-4 py-3">Acción</th>
                                        <th className="px-4 py-3">Entidad</th>
                                        <th className="px-4 py-3">Descripción</th>
                                        <th className="px-4 py-3">Detalle</th>
                                        <th className="px-4 py-3">IP</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {eventos.map((ev) => {
                                        const Icono = ICONO_ACCION[ev.accion] || Shield;
                                        const color = COLOR_ACCION[ev.accion] || 'border-white/20 bg-white/5 text-white/60';
                                        return (
                                            <tr key={ev.id} className="border-b border-white/5 text-white/80 last:border-0 hover:bg-white/[0.03]">
                                                <td className="whitespace-nowrap px-4 py-3 text-white/50">{formatFecha(ev.fecha)}</td>
                                                <td className="px-4 py-3">
                                                    <div className="font-bold text-white">{ev.nombre}</div>
                                                    <div className="text-[11px] text-white/40">@{ev.username}</div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide ${color}`}>
                                                        <Icono size={11} aria-hidden="true" /> {ev.accion}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-white/60">{ev.entidad}</td>
                                                <td className="px-4 py-3 text-white/70">{ev.entidad_desc || '—'}</td>
                                                <td className="max-w-[260px] truncate px-4 py-3 text-white/50" title={ev.detalle || ''}>{ev.detalle || '—'}</td>
                                                <td className="whitespace-nowrap px-4 py-3 font-mono text-[12px] text-white/40">{ev.ip || '—'}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );
}

// Tarjeta de estadística: valor grande con su etiqueta.
function Tarjeta({ label, value, color }) {
    return (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03]" style={{ padding: '18px 20px' }}>
            <div className={`text-2xl font-black ${color}`}>{value}</div>
            <div className="text-[11px] font-bold uppercase tracking-wide text-white/40">{label}</div>
        </div>
    );
}

// Campo del formulario de filtros: etiqueta sobre el control.
function Campo({ label, children }) {
    return (
        <div className="flex flex-col gap-1.5">
            <label className="text-[10px] font-bold uppercase tracking-wide text-white/40">{label}</label>
            {children}
        </div>
    );
}
