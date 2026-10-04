import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import Chart from 'react-apexcharts';
import {
    AlertCircle,
    ArrowDownRight,
    ArrowUpRight,
    BarChart3,
    ChevronDown,
    Database,
    Download,
    FileText,
    GraduationCap,
    MousePointerClick,
    Package,
    ShieldAlert,
    ShoppingBag,
    Sliders,
    Sparkles,
    Star,
    TrendingUp,
    Users,
} from 'lucide-react';

import { apiGet, apiPost } from '../../services/api';
import { getDbProfile, mergeDbCatalog } from '../../constants/appConfig';
import { useContextOverview } from '../../hooks/useContextOverview';
import { exportExecutivePdf } from '../../utils/pdfExport';
import { RiesgoAbandonoCard } from './RiesgoAbandonoCard';
import { InteligenciaInstitucionalCard } from './InteligenciaInstitucionalCard';

const MESES_ES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

const _pad2 = (n) => String(n).padStart(2, '0');

// Traduce el filtro de Período (mismo selector que usan las tarjetas/gráficos)
// a un rango de fechas start/end para el Excel.
//
// Defecto detectado en pruebas (28/08/2026): el botón Excel ignoraba
// por completo el período seleccionado y siempre traía TODA la data
// histórica con solo darle clic — sin acotar ni siquiera al año. La regla
// que pidió: sin tocar el selector (queda en "Período más reciente") debe
// bajar solo el MES más reciente con datos, igual que el resto del
// dashboard; para bajar el año completo hay que elegir explícitamente el
// año y dejar el mes en "Todo <año>".
function rangoParaExportarExcel(selectedYear, selectedMonth, availablePeriods) {
    let year = selectedYear;
    let month = selectedYear ? selectedMonth : null;

    if (!year) {
        const masReciente = availablePeriods?.[0];
        if (!masReciente) return { start: null, end: null };
        year = masReciente.year;
        const meses = masReciente.months || [];
        month = meses.length ? meses[meses.length - 1] : null;
    }

    if (!month) {
        return { start: `${year}-01-01`, end: `${year}-12-31` };
    }

    const ultimoDia = new Date(year, month, 0).getDate();
    return { start: `${year}-${_pad2(month)}-01`, end: `${year}-${_pad2(month)}-${_pad2(ultimoDia)}` };
}

export function BentoDashboard({ connInfo = {}, biPulse = null, onDrillDown = null, userAuth = null }) {
    const targetDb = String(connInfo.selected_company_code || connInfo.database || '').trim().toUpperCase();
    const hasTargetDb = Boolean(targetDb) && !['PROYECTO'].includes(targetDb);
    const profile = getDbProfile(targetDb);

    const [loading, setLoading] = useState(Boolean(hasTargetDb));
    const [pulseData, setPulseData] = useState(
        biPulse && String(biPulse?.db || '').trim().toUpperCase() === targetDb ? biPulse : null
    );
    const [error, setError] = useState(null);
    const { overview, loading: overviewLoading } = useContextOverview(targetDb, Boolean(targetDb));
    const [exportImgError, setExportImgError] = useState('');


    // Exportación a Excel estructurado (Fase 4 — 28/08/2026):
    // reemplaza el CSV plano de arriba (una sola tabla ambigua
    // mezclando tarjetas, gráficos y tablas en columnas genéricas) por un
    // libro de Excel real con hojas separadas y con formato — Facturas,
    // Detalle Items, Productos, Clientes y, si la empresa es educativa,
    // Cartera por rubro. Portado del proyecto hermano TripleA_VentasIA
    // (core/excel_exporter.py trae el detalle de ese origen).
    //
    // Es una descarga autenticada (JWT), así que no puede ser un <a href>
    // simple: se pide como blob vía axios y se dispara la descarga a mano
    // con un enlace temporal.
    const [exportandoExcel, setExportandoExcel] = useState(false);
    const [exportandoPdf, setExportandoPdf] = useState(false);

    // Persistence of pinned metrics for personalized user experience
    const [pinnedCards, setPinnedCards] = useState(() => {
        try {
            return JSON.parse(localStorage.getItem(`pinned_kpis_${targetDb}`) || '[]');
        } catch {
            return [];
        }
    });

    const togglePinCard = (e, cardId) => {
        e.stopPropagation();
        setPinnedCards((prev) => {
            const next = prev.includes(cardId) ? prev.filter((id) => id !== cardId) : [...prev, cardId];
            try {
                localStorage.setItem(`pinned_kpis_${targetDb}`, JSON.stringify(next));
                apiPost('/user/pinned-metrics', { metricId: cardId, pinned: next.includes(cardId) }).catch(() => {});
            } catch {}
            return next;
        });
    };

    const handleExportarPdf = () => {
        setExportandoPdf(true);
        try {
            exportExecutivePdf({
                companyName: companyLabel,
                companyRuc: profile?.ruc,
                companyCode: targetDb,
                period: selectedYear ? (selectedMonth ? `${selectedMonth}/${selectedYear}` : `Año ${selectedYear}`) : 'Más reciente (2026)',
                kpiCards: cards,
                executiveBrief: processedExecutiveBrief,
                generatedBy: userAuth?.name || 'Gerencia General',
            });
        } catch (e) {
            console.error('Error exportando PDF:', e);
            setExportImgError('No se pudo generar el reporte en PDF.');
        } finally {
            setExportandoPdf(false);
        }
    };

    const exportarComoExcel = async () => {
        if (!targetDb || exportandoExcel) return;
        setExportandoExcel(true);
        try {
            const { start, end } = rangoParaExportarExcel(selectedYear, selectedMonth, availablePeriods);
            const params = new URLSearchParams({ target_db: targetDb });
            if (start) params.set('start', start);
            if (end) params.set('end', end);
            const res = await apiGet(
                `/reportes/exportar-excel?${params.toString()}`,
                { responseType: 'blob' }
            );
            const disposition = res.headers?.['content-disposition'] || '';
            const match = disposition.match(/filename="?([^"]+)"?/);
            const fecha = new Date().toISOString().slice(0, 10);
            const filename = match ? match[1] : `reporte_${targetDb}_${fecha}.xlsx`;

            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (_err) {
            console.error('[Indicadores] Error exportando Excel:', _err);
            setExportImgError('No se pudo generar el Excel. Intenta de nuevo.');
        } finally {
            setExportandoExcel(false);
        }
    };

    useEffect(() => {
        if (!targetDb || !overview?.profile?.modules?.length) return;
        mergeDbCatalog([
            {
                database: targetDb,
                company_code: targetDb,
                business_name: overview?.profile?.business_name || profile?.business_name || targetDb,
                short_name: profile?.short_name || targetDb,
                modules: overview.profile.modules || [],
            },
        ]);
    }, [targetDb, overview, profile?.business_name, profile?.short_name]);

    // Filtro de mes/año explícito (por defecto: "más reciente con datos" =
    // null, igual que el chat cuando no se menciona un período). Afecta las
    // métricas del catálogo que usan {year} (ventas/compras), Balance
    // Comercial, Ingresos por Línea de Negocio y Top 5 Productos; el resto
    // sigue mostrando su propio "período más reciente" (nómina, antigüedad).
    const [selectedYear, setSelectedYear] = useState(null);
    const [selectedMonth, setSelectedMonth] = useState(null);
    const pulseUrl = (db) => {
        const params = new URLSearchParams({ target_db: db });
        if (selectedYear) params.set('year', String(selectedYear));
        if (selectedYear && selectedMonth) params.set('month', String(selectedMonth));
        return `/bi/pulse?${params.toString()}`;
    };

    // Quick Win — adoptar el pulso que App.jsx ya trajo (fetchBiPulse lanzado en
    // cada conexión) en vez de lanzar un GET /bi/pulse duplicado para la misma
    // base. App pide SIN filtros (sin year/month), así que ese snapshot solo
    // sirve cuando aquí tampoco hay período elegido ("más reciente con datos");
    // con año/mes seleccionados el dato filtrado se pide aparte, como antes.
    const biPulseAplica = Boolean(
        biPulse
        && biPulse.status === 'ok'
        && String(biPulse.db || '').trim().toUpperCase() === targetDb
    );
    const adoptarBiPulse = Boolean(hasTargetDb && !selectedYear && biPulseAplica);

    // Años/meses con datos REALES en la base activa (Fase 4 — antes el
    // selector ofrecía [año actual, -1, -2, -3] fijos, que podían no existir
    // en la base o dejar fuera años más viejos que sí tenía). Se recalcula
    // solo al cambiar de empresa, no en cada cambio de filtro.
    const [availablePeriods, setAvailablePeriods] = useState([]);
    useEffect(() => {
        let cancelled = false;
        if (!hasTargetDb) {
            setAvailablePeriods([]);
            return undefined;
        }
        (async () => {
            try {
                const res = await apiGet(`/bi/available-periods?target_db=${encodeURIComponent(targetDb)}`);
                if (!cancelled && res.data?.status === 'ok') {
                    setAvailablePeriods(Array.isArray(res.data.years) ? res.data.years : []);
                }
            } catch (_err) {
                if (!cancelled) setAvailablePeriods([]);
            }
        })();
        return () => { cancelled = true; };
    }, [hasTargetDb, targetDb]);

    // Guard anti-solape: las vistas de CHAT son compartidas en el servidor
    // (no por sesión). Si dos peticiones a /bi/pulse de empresas distintas
    // corren al mismo tiempo (ej. cambias de empresa mientras el refresco
    // automático de la anterior todavía está corriendo), el servidor puede
    // reconfigurar CHAT a mitad de camino y mezclar datos entre empresas.
    // Esta ref asegura que nunca haya dos peticiones en vuelo a la vez desde
    // este panel — la más nueva espera a que la anterior termine.
    const fetchEnCursoRef = useRef(false);

    // Guard anti-empresa-cruzada: si `targetDb` cambia sin desmontar el panel
    // (cambio de empresa en caliente), limpiar pulso y error al instante para
    // que nunca se pinten las tarjetas de la empresa A bajo el encabezado de B.
    // useLayoutEffect corre antes del paint, así ni un solo frame muestra datos
    // cruzados; mientras llega el nuevo pulso el skeleton (isTrulyLoading) cubre.
    const targetDbPreviaRef = useRef(targetDb);
    useLayoutEffect(() => {
        if (targetDbPreviaRef.current !== targetDb) {
            targetDbPreviaRef.current = targetDb;
            setPulseData(null);
            setError(null);
        }
    }, [targetDb]);

    useEffect(() => {
        let cancelled = false;

        const fetchPulse = async () => {
            if (!hasTargetDb) {
                setPulseData(null);
                setLoading(false);
                setError('Selecciona una empresa/base operativa para activar Indicadores.');
                return;
            }

            // Si App ya trajo un pulso válido para ESTA base y sin filtros de
            // período, ya tenemos el dato en `biPulse`: se adopta y este fetch
            // propio se omite (cero GET duplicado contra las vistas de CHAT).
            if (adoptarBiPulse) return;

            // Espera a que termine la petición anterior antes de lanzar la nueva,
            // en vez de dispararlas en paralelo contra las vistas compartidas.
            // Con tope máximo: si algo dejara la bandera trabada, preferimos
            // seguir adelante antes que dejar la pantalla colgada para siempre.
            const MAX_ESPERA_MS = 8000;
            const inicioEspera = Date.now();
            while (fetchEnCursoRef.current && (Date.now() - inicioEspera) < MAX_ESPERA_MS) {
                await new Promise((resolve) => setTimeout(resolve, 150));
                if (cancelled) return;
            }
            fetchEnCursoRef.current = true;

            setLoading(true);
            setError(null);
            try {
                const res = await apiGet(pulseUrl(targetDb));
                if (cancelled) return;
                if (res.data?.status === 'ok') {
                    setPulseData(res.data);
                    return;
                }
                setPulseData(null);
                setError(res.data?.message || 'No pude sincronizar el pulso BI.');
            } catch (_err) {
                if (cancelled) return;
                setPulseData(null);
                setError('No se pudo conectar con el motor BI.');
            } finally {
                fetchEnCursoRef.current = false;
                if (!cancelled) setLoading(false);
            }
        };

        void fetchPulse();
        return () => {
            cancelled = true;
        };
    }, [adoptarBiPulse, hasTargetDb, targetDb, selectedYear, selectedMonth]);

    // Refleja en pantalla un `biPulse` nuevo/actualizado de App (otra conexión)
    // SIN refetch: al ser adoptable se pinta tal cual. Cuando el usuario eligió
    // año/mes esto no aplica y el fetch con filtros de arriba es el que manda.
    useEffect(() => {
        if (adoptarBiPulse && biPulse) {
            setPulseData(biPulse);
            setError(null);
            setLoading(false);
        }
    }, [adoptarBiPulse, biPulse]);

    // ── Auto-refresh (Fase 2 — "dashboards vivos") ──────────────────────────
    // Cada refresco cuesta ~16 consultas SQL contra la base CHAT, que es un
    // recurso COMPARTIDO por todo el sistema (el chat usa las mismas vistas).
    // Refrescar cada 5 minutos con la pestaña abierta en segundo plano era una
    // carga constante e innecesaria que ralentizaba al resto. Ahora:
    //   · intervalo de 15 minutos (no 5)
    //   · solo si la pestaña está visible — si el usuario no la está mirando,
    //     no tiene sentido gastar consultas en actualizar lo que nadie ve.
    const REFRESH_MS = 15 * 60 * 1000;

    useEffect(() => {
        if (!hasTargetDb) return undefined;

        const refrescarEnSilencio = async () => {
            if (document.visibilityState !== 'visible') return;
            // Si ya hay una carga en curso (ej. el usuario acaba de cambiar de
            // empresa), este tick se salta en vez de disparar una segunda
            // petición en paralelo contra las vistas compartidas de CHAT.
            if (fetchEnCursoRef.current) return;
            fetchEnCursoRef.current = true;
            try {
                const res = await apiGet(pulseUrl(targetDb));
                if (res.data?.status === 'ok') {
                    setPulseData(res.data);
                }
            } catch (_err) {
                // Falla silenciosa: si el refresco automático no funciona, se
                // mantienen los últimos datos válidos en pantalla.
            } finally {
                fetchEnCursoRef.current = false;
            }
        };

        const intervalId = setInterval(refrescarEnSilencio, REFRESH_MS);
        return () => clearInterval(intervalId);
    }, [hasTargetDb, targetDb, selectedYear, selectedMonth]);

    // ── Filtro por módulos permitidos del rol (defensa extra) ─────────────────
    // El backend ya filtra /bi/pulse y /context-overview por los módulos del
    // JWT, pero un `biPulse` cacheado en memoria (App.jsx) pudo generarse con
    // otro rol. Como BentoDashboard ya recibe `userAuth`, se aplica también
    // aquí un filtro visual: si el rol no tiene habilitado un módulo, sus
    // tarjetas/gráficos/tablas no se renderizan. Si `userAuth` no trae
    // módulos (admin/guest/restauraciones viejas) no se filtra nada.
    const allowedModules = useMemo(() => {
        const mods = userAuth?.modules;
        return Array.isArray(mods) && mods.length
            ? mods.map((m) => String(m).trim().toUpperCase())
            : [];
    }, [userAuth]);
    const moduleAllowed = (module, strict = false) => {
        if (!allowedModules.length) return !strict;
        const mod = String(module || 'GENERAL').trim().toUpperCase();
        return mod === 'GENERAL' || allowedModules.includes(mod);
    };
    const filterByModule = (items) => (Array.isArray(items) ? items.filter((it) => moduleAllowed(it?.module)) : []);

    const cards = filterByModule(pulseData?.cards);
    const charts = filterByModule(pulseData?.charts);
    const tables = filterByModule(pulseData?.tables);
    const alerts = filterByModule(pulseData?.alerts);
    const focusAreas = filterByModule(pulseData?.focus_areas);
    // Las áreas del overview tienen id = clave del módulo en minúsculas
    // (academico → ACADEMICO); moduleAllowed lo normaliza a mayúsculas.
    const overviewAreas = (Array.isArray(overview?.areas) ? overview.areas : [])
        .filter((a) => moduleAllowed(a?.id));
    const readyAreas = overviewAreas.filter((area) => area?.status === 'ready');
    // Nota: las preguntas sugeridas (quick_questions) ya no se muestran aquí —
    // se movieron al chat, junto al input, que es donde el usuario las usa.
    const companyLabel = pulseData?.profile?.business_name
        || overview?.profile?.business_name
        || profile?.business_name
        || targetDb
        || 'Sin contexto';

    // Sello de antigüedad del snapshot (Capa 2): SOLO cuando el backend dice que
    // la respuesta salió de un snapshot persistente y trae capture_age_seconds.
    // En respuestas en vivo/caché de 90 s esos campos vienen ausentes y aquí no
    // se renderiza nada (mismo comportamiento que antes).
    const edadSnapshotSeg = pulseData?.capture_age_seconds;
    const selloActualizacion = pulseData?.served_from === 'snapshot' && Number.isFinite(edadSnapshotSeg)
        ? textoActualizacionDesdeSegundos(Number(edadSnapshotSeg))
        : null;

    const executiveBrief = pulseData?.summary || overview?.summary || 'El motor BI no ha publicado un sumario ejecutivo para esta base.';

    // Personalización del sumario con el nombre real de la empresa
    const processedExecutiveBrief = useMemo(() => {
        let text = executiveBrief;
        if (targetDb && companyLabel && companyLabel !== targetDb) {
            // Reemplazar el código de la base por el nombre de la empresa
            const dbRegex = new RegExp(`\\b${targetDb}\\b`, 'gi');
            text = text.replace(dbRegex, companyLabel);
        }
        // Asegurar que use VicMar Data AI en lugar de Aura en cualquier sumario que venga del backend
        return text.replace(/Aura/gi, 'VicMar Data AI');
    }, [executiveBrief, targetDb, companyLabel]);

    const stats = useMemo(() => buildStats(pulseData, overview, cards.length), [pulseData, overview, cards.length]);
    const displayAreas = focusAreas.length > 0 ? focusAreas : readyAreas.map((area) => ({
        id: area.id,
        title: area.name,
        description: area.desc,
        recommendation: 'VicMarDataAI puede orientar consultas validas segun este dominio detectado.',
        module: 'GENERAL',
        period_label: '',
    }));

    // Mostrar el esqueleto SOLO si NO tenemos ningun dato de ninguna fuente.
    // En cuanto llega overview O pulseData, renderizamos aunque la otra fuente siga cargando.
    const isTrulyLoading = !pulseData && !overview && (loading || overviewLoading);

    if (isTrulyLoading) {
        return <DashboardSkeleton />;
    }

    if (!hasTargetDb) {
        return (
            <div className="flex h-full w-full items-center justify-center p-6 lg:p-12">
                <div className="max-w-[540px] rounded-[32px] border border-white/10 bg-white/[0.03] p-10 relative overflow-hidden">
                    <div className="flex flex-col items-center text-center">
                        <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-black/40 shadow-xl">
                            <Database size={28} className="text-cyan-400" />
                        </div>
                        <h2 className="text-xl font-black tracking-[0.20] text-white uppercase">
                            Indicadores espera una base operativa
                        </h2>
                        <p className="mt-5 text-[15px] leading-relaxed text-white/50 px-4">
                            Al seleccionar una empresa o base, este panel se sincroniza automáticamente y levanta las tarjetas y dominios.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    // Auditoría 11/09/2026: `error` se calculaba pero nunca se pintaba —
    // si /bi/pulse fallaba (backend caído, motor BI sin responder), el
    // panel caía silenciosamente a cards=[]/charts=[]/tables=[] y se veía
    // igual que "esta empresa no tiene datos", en vez de avisar que el
    // motor de BI no respondió. Se muestra un error explícito solo cuando
    // de verdad no hay ningún dato que mostrar (si `overview` sí llegó por
    // su propio hook, seguimos mostrando lo que haya en vez de bloquear).
    if (error && !pulseData && !overview) {
        return (
            <div className="flex h-full w-full items-center justify-center p-6 lg:p-12">
                <div className="max-w-[540px] rounded-[32px] border border-rose-500/30 bg-rose-500/[0.06] p-10 relative overflow-hidden">
                    <div className="flex flex-col items-center text-center">
                        <div className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl border border-rose-500/30 bg-black/40 shadow-xl">
                            <AlertCircle size={28} className="text-rose-400" />
                        </div>
                        <h2 className="text-xl font-black tracking-[0.20] text-white uppercase">
                            No se pudo conectar con el motor de BI
                        </h2>
                        <p className="mt-5 text-[15px] leading-relaxed text-white/50 px-4">
                            {error} Verifica que el backend esté corriendo y vuelve a intentar — esto
                            no significa que "{companyLabel}" no tenga datos.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex h-full w-full flex-col overflow-hidden p-4 lg:p-6"
        >
            <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 overflow-hidden">
                {/* Cabecera fija (no scrollea): el título, el filtro de período y
                    el botón Excel quedan siempre a la vista; solo el contenido de
                    abajo se desplaza, igual que en auditoría y orígenes de datos. */}
                <div className="flex shrink-0 flex-col gap-4">
                <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                    <div className="flex max-w-4xl flex-col gap-2">
                        <h1 className="text-xl font-black uppercase tracking-tight text-white lg:text-2xl">
                            Indicadores <span className="text-white/20">/</span> {companyLabel}
                        </h1>
                        {selloActualizacion && (
                            <p className="text-[11px] font-medium tracking-wide text-white/35" title="Estos datos se sirvieron desde el snapshot precargado del motor BI">
                                {selloActualizacion}
                            </p>
                        )}
                    </div>

                    <div className="flex flex-col items-start gap-3 lg:items-end">
                        <div className="flex flex-wrap items-center justify-end gap-2.5">
                            <PeriodoFiltro
                                availablePeriods={availablePeriods}
                                selectedYear={selectedYear}
                                selectedMonth={selectedMonth}
                                onChangeYear={(y) => { setSelectedYear(y); setSelectedMonth(null); }}
                                onChangeMonth={setSelectedMonth}
                            />

                            {/* Botón Exportar PDF */}
                            <button
                                onClick={handleExportarPdf}
                                disabled={!targetDb || exportandoPdf}
                                aria-label="Exportar reporte ejecutivo en PDF"
                                className="group flex items-center gap-2 rounded-xl border border-cyan-500/30 bg-gradient-to-br from-cyan-500/15 to-cyan-500/5 px-3.5 py-2 text-cyan-200 shadow-[0_0_18px_-8px_rgba(6,182,212,0.4)] transition-all hover:border-cyan-400/60 hover:from-cyan-500/25 hover:to-cyan-500/10 focus:outline-none cursor-pointer"
                                title="Descargar informe ejecutivo corporativo en PDF formal con membrete"
                            >
                                <FileText size={16} className="text-cyan-400" aria-hidden="true" />
                                <span className="text-[12px] font-bold uppercase tracking-wider">PDF</span>
                            </button>

                            {/* Botón Exportar Excel Estructurado */}
                            <button
                                onClick={exportarComoExcel}
                                disabled={!targetDb || exportandoExcel}
                                aria-label={exportandoExcel ? 'Generando Excel…' : 'Exportar reporte estructurado a Excel'}
                                className="group flex items-center gap-2 rounded-xl border border-emerald-400/30 bg-gradient-to-br from-emerald-500/15 to-emerald-500/5 px-3.5 py-2 text-emerald-200 shadow-[0_0_22px_-8px_rgba(16,185,129,0.5)] transition-all hover:border-emerald-400/60 hover:from-emerald-500/25 hover:to-emerald-500/10 hover:shadow-[0_0_28px_-6px_rgba(16,185,129,0.7)] disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60 cursor-pointer"
                                title="Exportar Facturas, Detalle Items, Productos, Clientes y Cartera en un libro de Excel con formato (respeta el período elegido arriba)"
                            >
                                <Download size={16} className="transition-transform group-hover:-translate-y-0.5 text-emerald-400" aria-hidden="true" />
                                <span className="text-[12px] font-bold uppercase tracking-wider">Excel</span>
                            </button>
                        </div>
                        {exportImgError && (
                            <p role="alert" className="max-w-xs text-right text-[11px] font-medium leading-snug text-rose-400">
                                {exportImgError}
                            </p>
                        )}
                    </div>
                </header>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar">
                <div className="flex flex-col gap-4">

                {/* Alertas automáticas (Fase 2): solo aparecen si una métrica certificada
                    varió 15% o más vs. el mes anterior — no es una opinión de la IA, es
                    una comparación matemática directa sobre los mismos datos del gráfico. */}
                {alerts.length > 0 && (
                    <div className="flex flex-col gap-2" role="region" aria-label="Alertas de variación de métricas">
                        {alerts.map((alert) => (
                            <div
                                key={alert.id}
                                role="status"
                                className={`flex items-center gap-3 rounded-2xl border px-5 py-3 text-[13px] font-medium ${
                                    alert.severity === 'warning'
                                        ? 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                                        : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                                }`}
                            >
                                <AlertCircle size={16} className="shrink-0" aria-hidden="true" />
                                {alert.message}
                            </div>
                        ))}
                    </div>
                )}

                {/* ── TARJETAS KPI ────────────────────────────────────────────────────── */}
                {(() => {
                    // Filtrar tarjetas con valor 0 que no sean el Balance Comercial
                    // (ya que el Balance tiene primary+secondary y puede ser útil aunque sea 0)
                    const filteredCards = cards.filter(card => {
                        const isBalance = card.title?.toLowerCase().includes('balance');
                        const val = Number(card.value ?? 0);
                        const secVal = Number(card.secondary_value ?? 0);
                        // Ocultar si el valor ES 0 y NO hay secondary_value relevante y NO es Balance
                        if (!isBalance && val === 0 && secVal === 0) return false;
                        return true;
                    });
                    // Sort pinned cards first to respect user personalization
                    const sortedCards = [...filteredCards].sort((a, b) => {
                        const aPinned = pinnedCards.includes(a.id);
                        const bPinned = pinnedCards.includes(b.id);
                        if (aPinned && !bPinned) return -1;
                        if (!aPinned && bPinned) return 1;
                        return 0;
                    });

                    // Determinar número de columnas óptimo para el número de tarjetas
                    const n = sortedCards.length;
                    const xlCols = n <= 2 ? 'xl:grid-cols-2'
                                 : n === 3 ? 'xl:grid-cols-3'
                                 : n === 4 ? 'xl:grid-cols-4'
                                 : n <= 6 ? 'xl:grid-cols-3'
                                 : 'xl:grid-cols-4';

                    return (
                    <section className={`grid grid-cols-1 gap-3 md:grid-cols-2 ${xlCols}`}>

                    {/* Renderizado de tarjetas dinámicas */}
                    {sortedCards.map((card, idx) => {
                        const theme = getCardTheme(card.module, card.accent);
                        const valueFormatted = formatCardValue(card.value, card.unit);

                        // secondary_unit es independiente de unit: antes el conteo de
                        // "Facturas" (un número plano, ej. 484) heredaba el "$" de la
                        // tarjeta y se mostraba como "$484,00". Sin secondary_unit
                        // explícito (la mayoría de tarjetas, ej. Balance Comercial con
                        // Ventas/Compras en dólares), se sigue usando `unit` como antes.
                        const secValueFormatted = card.secondary_value !== undefined && card.secondary_value !== null
                            ? formatCardValue(card.secondary_value, card.secondary_unit ?? card.unit)
                            : null;

                        // "Ver detalle" en las tarjetas de indicadores
                        // ELIMINADO por solicitud del usuario (29/08/2026): las
                        // tarjetas KPI ya no lanzan pregunta de detalle al chat.
                        // `buildCardDrillQuestion` se conserva (se sigue usando
                        // en tests y por si se reactiva el drill-down).
                        const drillQuestion = null;

                        return (
                            <motion.div
                                key={card.id}
                                initial={{ opacity: 0, scale: 0.96 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: idx * 0.04 }}
                                onClick={drillQuestion ? () => onDrillDown(drillQuestion) : undefined}
                                role={drillQuestion ? 'button' : undefined}
                                tabIndex={drillQuestion ? 0 : undefined}
                                onKeyDown={drillQuestion ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onDrillDown(drillQuestion); } } : undefined}
                                title={drillQuestion ? 'Ver el detalle en el chat' : undefined}
                                className={`group relative flex flex-col overflow-hidden rounded-2xl border transition-all duration-300 ${drillQuestion ? 'cursor-pointer hover:border-cyan-500/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50' : ''}`}
                                style={{
                                    background: theme.bg,
                                    borderColor: pinnedCards.includes(card.id) ? 'rgba(251, 191, 36, 0.4)' : theme.border,
                                    boxShadow: pinnedCards.includes(card.id) ? '0 8px 32px -12px rgba(251,191,36,0.15)' : '0 8px 32px -12px rgba(0,0,0,0.5)',
                                    padding: '18px 20px',
                                }}
                            >
                                <div
                                    className="absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
                                    style={{ background: theme.hoverGradient }}
                                />
                                {drillQuestion && (
                                    <div className="absolute bottom-4 right-4 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-white/0 group-hover:text-white/35 transition-colors pointer-events-none">
                                        <MousePointerClick size={11} />
                                        Ver detalle
                                    </div>
                                )}

                                <div className="relative z-10 flex w-full flex-col gap-2.5">
                                    <div className="flex items-center justify-between gap-3">
                                        {/* Icono Principal (Top Left) */}
                                        <div className={`rounded-lg border p-2 ${theme.iconBg} ${theme.iconBorder} shrink-0`}>
                                            {getCardIcon(card.module, theme.iconColor)}
                                        </div>

                                        {/* Acciones & Badge de Estado (Top Right) */}
                                        <div className="flex items-center gap-1.5">
                                            {/* Pin Star Button */}
                                            <button
                                                type="button"
                                                onClick={(e) => togglePinCard(e, card.id)}
                                                title={pinnedCards.includes(card.id) ? 'Desfijar KPI prioritario' : 'Fijar KPI como prioritario'}
                                                aria-label={pinnedCards.includes(card.id) ? 'Desfijar KPI' : 'Fijar KPI'}
                                                className={`p-1.5 rounded-lg transition-all cursor-pointer ${
                                                    pinnedCards.includes(card.id)
                                                        ? 'text-amber-400 bg-amber-400/20 shadow-sm'
                                                        : 'text-white/20 hover:text-white/70 hover:bg-white/10'
                                                }`}
                                            >
                                                <Star size={13} fill={pinnedCards.includes(card.id) ? 'currentColor' : 'none'} />
                                            </button>

                                            {/* Badge de Estado con Efecto Live */}
                                            <div className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 backdrop-blur-md transition-all duration-500 shrink-0 ${
                                                (card.period_label?.toLowerCase().includes('activo') || card.period_label?.toLowerCase().includes('live'))
                                                ? 'border-emerald-500/40 bg-emerald-500/10 shadow-[0_0_12px_rgba(16,185,129,0.2)]'
                                                : 'border-white/10 bg-black/40'
                                            }`}>
                                                {(card.period_label?.toLowerCase().includes('activo') || card.period_label?.toLowerCase().includes('live')) ? (
                                                    <span className="relative flex h-1.5 w-1.5">
                                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                                        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                                                    </span>
                                                ) : (
                                                    card.trend === 'down'
                                                    ? <ArrowDownRight size={12} className="text-rose-400" />
                                                    : <ArrowUpRight size={12} className="text-emerald-400" />
                                                )}
                                                <span className={`text-[11px] font-black uppercase tracking-[0.14em] truncate ${
                                                    (card.period_label?.toLowerCase().includes('activo') || card.period_label?.toLowerCase().includes('live'))
                                                    ? 'text-emerald-400'
                                                    : 'text-white/60'
                                                }`}>
                                                    {card.period_label || `LIVE • ${new Date().getFullYear()}`}
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    <div>
                                        <div className={`text-[11px] font-black uppercase tracking-[0.18em] mb-1.5 ${card.title?.toLowerCase().includes('balance') ? 'text-cyan-400' : 'text-white/40'}`}>
                                            {card.title}
                                        </div>
                                        <div className="mt-1.5 flex flex-wrap items-baseline gap-4">
                                            <div className="flex flex-col min-w-0">
                                                {card.secondary_value !== undefined && card.secondary_value !== null && (
                                                    <span className="text-[11px] font-black uppercase text-emerald-400/90 mb-1">
                                                        {card.primary_label || "Ventas"}
                                                    </span>
                                                )}
                                                <div className="flex items-baseline gap-2 min-w-0">
                                                    <span className="max-w-full break-words text-3xl font-black leading-none tracking-tight text-white">
                                                        {valueFormatted}
                                                    </span>
                                                </div>
                                            </div>

                                            {secValueFormatted !== null && (
                                                <div className="flex flex-col border-l border-white/15 pl-4 min-w-0">
                                                    <span className="text-[11px] font-black uppercase text-cyan-400/90 mb-1">
                                                        {card.secondary_label || "Cursos"}
                                                    </span>
                                                    <div className="flex items-baseline gap-2 min-w-0">
                                                        <span className="max-w-full break-words text-2xl font-black leading-none tracking-tight text-white/70">
                                                            {secValueFormatted}
                                                        </span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                        {card.hint ? (
                                            <div className="mt-2 text-[11px] leading-snug text-white/50">
                                                {card.hint}
                                            </div>
                                        ) : null}
                                    </div>
                                </div>

                                <div className={`absolute -bottom-4 -right-4 h-16 w-16 rounded-full blur-3xl opacity-20 ${theme.glowColor}`} />
                            </motion.div>
                        );
                    })}

                    </section>
                    );
                })()}


                {/* Gráficos reales (Fase 2 — dashboards vivos). Cada uno viene de una
                    métrica certificada del catálogo con varias filas (ej. total por mes),
                    no de datos inventados. */}
                {charts.length > 0 && (
                    <section className="grid items-start grid-flow-row-dense grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {charts.map((chart, idx) => (
                            <ChartCard key={chart.id} chart={chart} delay={idx * 0.05} onDrillDown={onDrillDown} />
                        ))}
                    </section>
                )}

                {/* Tablas reales (Fase 4 — 28/08/2026): "Ingresos por Línea de
                    Negocio" y "Top 5 Productos". Igual que los gráficos, vienen de
                    SQL certificado contra la vista de ventas real de la empresa, no
                    de datos inventados — se omiten solas si esa vista no existe o no
                    tiene la columna necesaria para esta empresa en particular. */}
                {tables.length > 0 && (
                    <section className="grid items-start grid-flow-row-dense grid-cols-1 gap-4 xl:grid-cols-2">
                        {tables.map((table, idx) => (
                            <TableCard key={table.id} table={table} delay={idx * 0.05} />
                        ))}
                    </section>
                )}

                {/* Comparación por período: pide dos rangos de fecha y compara
                    ventas/compras entre ambos. Independiente del filtro global de
                    mes/año de arriba (ese filtra las tarjetas; esto es una consulta
                    aparte, a demanda). */}
                {hasTargetDb && moduleAllowed('VENTAS', true) && <ComparacionPorPeriodo targetDb={targetDb} />}

                {/* Riesgo de abandono estudiantil (IA predictiva): solo para bases
                    con el modulo ACADEMICO habilitado. Se oculta en silencio si la
                    empresa aun no tiene predicciones calculadas (ver backend/ml/). */}
                {hasTargetDb && moduleAllowed('ACADEMICO', true) && <RiesgoAbandonoCard targetDb={targetDb} />}

                {/* Módulo 2 (benchmarking institucional): clustering de carreras +
                    comparación contra fuentes externas reales. */}
                {hasTargetDb && moduleAllowed('ACADEMICO', true) && <InteligenciaInstitucionalCard targetDb={targetDb} />}

                {/* Contexto de la empresa: plegado por defecto tras la primera visita.
                    Divulgación progresiva — la info sigue disponible, pero no compite
                    con los datos por el espacio de pantalla. */}
                <ContextoEmpresaPanel
                    resumen={processedExecutiveBrief}
                    areas={displayAreas}
                    stats={stats}
                />

                </div>
                </div>

            </div>

        </motion.div>
    );
}

/**
 * Esqueleto de carga: imita la forma real del dashboard (tarjetas + gráficos)
 * en lugar de un spinner girando.
 *
 * Un spinner no informa nada: el usuario no sabe si viene una tarjeta o veinte.
 * El esqueleto anticipa la estructura, y por eso la espera se percibe más
 * corta aunque el tiempo real sea idéntico.
 */
function DashboardSkeleton() {
    return (
        <div
            className="h-full w-full overflow-hidden p-4 lg:p-6 pt-3 lg:pt-4"
            role="status"
            aria-live="polite"
            aria-label="Cargando Indicadores"
        >
            <div className="mx-auto flex max-w-7xl animate-pulse flex-col gap-4">
                <div className="h-10 w-2/5 rounded-2xl bg-white/[0.06]" />
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <div key={i} className="h-40 rounded-[32px] border border-white/5 bg-white/[0.03]" />
                    ))}
                </div>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <div key={i} className="h-64 rounded-[32px] border border-white/5 bg-white/[0.03]" />
                    ))}
                </div>
            </div>
            <span className="sr-only">Cargando Indicadores…</span>
        </div>
    );
}

/**
 * Panel plegable con el contexto de la empresa (resumen ejecutivo + áreas
 * detectadas + estadísticas del esquema).
 *
 * Antes esto ocupaba tres tarjetas grandes ARRIBA de los datos: el usuario
 * recurrente tenía que hacer scroll sobre ~2 pantallas de texto que ya había
 * leído para llegar a sus números. Ahora va al final y recuerda si lo cerraste.
 */
function ContextoEmpresaPanel({ resumen, areas = [], stats = [] }) {
    const STORAGE_KEY = 'vicmar_bi_contexto_abierto';
    const [abierto, setAbierto] = useState(() => {
        if (typeof window === 'undefined') return false;
        // Primera visita: se muestra abierto para que el usuario sepa que existe.
        // Después respeta lo que haya elegido.
        return window.localStorage.getItem(STORAGE_KEY) !== 'cerrado';
    });

    const alternar = () => {
        const siguiente = !abierto;
        setAbierto(siguiente);
        try {
            window.localStorage.setItem(STORAGE_KEY, siguiente ? 'abierto' : 'cerrado');
        } catch (_err) {
            // Si localStorage no está disponible, el panel sigue funcionando,
            // solo que no recuerda la preferencia entre sesiones.
        }
    };

    return (
        <section className="rounded-3xl border border-white/10 bg-white/[0.02]">
            <button
                onClick={alternar}
                aria-expanded={abierto}
                aria-controls="panel-contexto-empresa"
                className="flex w-full items-center justify-between gap-3 rounded-3xl px-6 py-4 text-left transition-colors hover:bg-white/[0.03] focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
            >
                <span className="flex items-center gap-2.5">
                    <Sparkles size={15} className="text-cyan-300" aria-hidden="true" />
                    <span className="text-[13px] font-bold text-white/70">
                        Contexto de esta empresa
                    </span>
                </span>
                <ChevronDown
                    size={16}
                    className={`text-white/40 transition-transform ${abierto ? 'rotate-180' : ''}`}
                    aria-hidden="true"
                />
            </button>

            {abierto && (
                <div id="panel-contexto-empresa" className="border-t border-white/5 px-6 py-5">
                    <p className="text-[14px] leading-7 text-white/70">{resumen}</p>

                    {stats.length > 0 && (
                        <div className="mt-5 flex flex-wrap gap-3">
                            {stats.map((item) => (
                                <div key={item.id} className="rounded-xl border border-white/10 bg-black/20 px-4 py-2.5">
                                    <span className="text-[12px] text-white/40">{item.label}: </span>
                                    <span className="text-[14px] font-bold text-white">{item.value}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {areas.length > 0 && (
                        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
                            {areas.slice(0, 3).map((area) => (
                                <div key={area.id} className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
                                    <div className="text-[13px] font-bold text-white/75">{area.title}</div>
                                    <div className="mt-1 text-[12px] leading-5 text-white/45">{area.description}</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </section>
    );
}

const ACCENT_HEX = {
    cyan: '#22D3EE',
    amber: '#F59E0B',
    emerald: '#10B981',
    violet: '#6366F1',
    indigo: '#6366F1',
};

const PIE_PALETTE = ['#22D3EE', '#6366F1', '#10B981', '#F59E0B', '#F43F5E', '#A78BFA', '#38BDF8'];

/**
 * Filtro global de mes/año de Indicadores (Fase 4).
 *
 * Reemplaza el <select> viejo, que ofrecía [año actual, -1, -2, -3] fijos
 * sin importar si la empresa realmente tenía datos en esos años (o le
 * faltaban años más antiguos que sí tenía). Ahora las opciones de año salen
 * de /api/bi/available-periods — inteligente en el sentido que pedía el
 * usuario: se recalcula solo según los años que la base activa realmente
 * tiene facturados, así que nunca ofrece un año vacío ni omite uno real.
 *
 * El mes solo aparece una vez elegido un año, y solo lista los meses que ESE
 * año concreto tiene con datos.
 */
function PeriodoFiltro({ availablePeriods, selectedYear, selectedMonth, onChangeYear, onChangeMonth }) {
    const mesesDelAnio = selectedYear
        ? (availablePeriods.find((p) => p.year === selectedYear)?.months || [])
        : [];

    return (
        <div className="flex items-center gap-1.5">
            <select
                value={selectedYear || ''}
                onChange={(e) => onChangeYear(e.target.value ? Number(e.target.value) : null)}
                aria-label="Filtrar por año"
                className="rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 text-[12px] font-bold uppercase tracking-wide text-white/60 focus:border-cyan-500/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
                title="Filtrar por año (solo se listan los años con datos reales en esta base)"
            >
                <option value="">Período más reciente</option>
                {availablePeriods.map((p) => (
                    <option key={p.year} value={p.year}>{p.year}</option>
                ))}
            </select>
            {selectedYear && mesesDelAnio.length > 0 && (
                <select
                    value={selectedMonth || ''}
                    onChange={(e) => onChangeMonth(e.target.value ? Number(e.target.value) : null)}
                    aria-label="Filtrar por mes"
                    className="rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 text-[12px] font-bold uppercase tracking-wide text-white/60 focus:border-cyan-500/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
                    title={`Filtrar por mes dentro de ${selectedYear}`}
                >
                    <option value="">Todo {selectedYear}</option>
                    {mesesDelAnio.map((m) => (
                        <option key={m} value={m}>{MESES_ES[m - 1]}</option>
                    ))}
                </select>
            )}
        </div>
    );
}

function ChartCard({ chart, delay = 0, onDrillDown = null }) {
    const isPie = chart.chart_type === 'pie';
    const color = ACCENT_HEX[chart.accent] || '#22D3EE';
    const delta = chart.delta_pct;
    const isUp = typeof delta === 'number' && delta >= 0;

    // Fase 3 — C2 (drill-down): clic en una barra o porción de dona envía
    // una pregunta de detalle al chat sobre ESE punto específico (ej. clic
    // en "Marzo" → "detalle de ventas de Marzo"), no sobre el gráfico entero.
    const handleDataPointClick = (_event, _chartContext, config) => {
        if (!onDrillDown) return;
        const idx = config?.dataPointIndex;
        if (idx === undefined || idx === null || idx < 0) return;
        const label = (chart.labels || [])[idx];
        if (!label) return;
        onDrillDown(buildChartDrillQuestion(chart, label));
    };

    const options = isPie
        ? {
            chart: {
                toolbar: { show: false },
                foreColor: 'rgba(255,255,255,0.5)',
                events: onDrillDown ? { dataPointSelection: handleDataPointClick } : undefined,
            },
            labels: chart.labels || [],
            colors: PIE_PALETTE,
            legend: { position: 'bottom', fontSize: '11px', labels: { colors: 'rgba(255,255,255,0.6)' } },
            dataLabels: { enabled: true, style: { fontSize: '10px' } },
            stroke: { colors: ['transparent'] },
            tooltip: { theme: 'dark' },
        }
        : {
            chart: {
                toolbar: { show: false },
                foreColor: 'rgba(255,255,255,0.4)',
                events: onDrillDown ? { dataPointSelection: handleDataPointClick } : undefined,
            },
            plotOptions: { bar: { borderRadius: 6, columnWidth: '55%' } },
            dataLabels: { enabled: false },
            colors: [color],
            grid: { borderColor: 'rgba(255,255,255,0.05)', strokeDashArray: 4 },
            xaxis: {
                categories: chart.labels || [],
                axisBorder: { show: false },
                axisTicks: { show: false },
            },
            yaxis: { labels: { formatter: (v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v) } },
            tooltip: { theme: 'dark' },
        };

    const series = isPie ? (chart.values || []) : [{ name: chart.title, data: chart.values || [] }];

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay }}
            className="rounded-[32px] border border-white/10 p-8 shadow-2xl"
            style={{ background: 'rgba(255,255,255,0.02)' }}
        >
            <div className="mb-4 flex items-start justify-between">
                <div>
                    <h3 className="text-[12px] font-black uppercase tracking-[0.2em] text-white/40">{chart.module}</h3>
                    <div className="text-[15px] font-bold text-white">{chart.title}</div>
                </div>
                {typeof delta === 'number' && (
                    <div className={`flex items-center gap-1 rounded-full border px-3 py-1 text-[12px] font-black ${
                        isUp ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-rose-500/30 bg-rose-500/10 text-rose-400'
                    }`}>
                        {isUp ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                        {Math.abs(delta)}%
                    </div>
                )}
            </div>
            <div className={onDrillDown ? 'cursor-pointer' : ''} title={onDrillDown ? 'Clic en una barra/porción para ver el detalle en el chat' : undefined}>
                <Chart options={options} series={series} type={isPie ? 'donut' : 'bar'} height={isPie ? 260 : 220} />
            </div>
            {chart.hint && (
                <p className="mt-3 text-[12px] leading-relaxed text-white/30 italic">{chart.hint}</p>
            )}
        </motion.div>
    );
}

/**
 * Tarjeta de TABLA (Fase 4 — 28/08/2026): filas con varias columnas
 * (ej. "Ingresos por Línea de Negocio", "Top 5 Productos"), a diferencia de
 * ChartCard (una serie categoría→valor) y las tarjetas KPI (un solo número).
 * `pulseData.tables` es un array nuevo del backend, paralelo a `cards`/`charts`.
 */
function TableCard({ table, delay = 0 }) {
    const columnTypes = table.column_types || [];
    const formatCell = (value, colIdx) => {
        const tipo = columnTypes[colIdx];
        if (tipo === 'currency') return formatCardValue(value, '$');
        if (tipo === 'number') return formatCardValue(value, '');
        return value;
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay }}
            className="rounded-[32px] border border-white/10 p-8 shadow-2xl"
            style={{ background: 'rgba(255,255,255,0.02)' }}
        >
            <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                    <h3 className="text-[12px] font-black uppercase tracking-[0.2em] text-white/40">{table.module}</h3>
                    <div className="text-[15px] font-bold text-white">{table.title}</div>
                </div>
                {table.period_label && (
                    <div className="shrink-0 rounded-full border border-white/10 bg-black/40 px-3 py-1 text-[11px] font-black uppercase tracking-[0.14em] text-white/60">
                        {table.period_label}
                    </div>
                )}
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left text-[13px]">
                    <thead>
                        <tr className="border-b border-white/10 text-[11px] font-black uppercase tracking-wide text-white/40">
                            <th className="w-8 py-2 pr-2"></th>
                            {table.columns.map((col, i) => (
                                <th key={col} className={`py-2 pr-4 ${i > 0 ? 'text-right' : ''}`}>{col}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {(table.rows || []).map((fila, rowIdx) => (
                            <tr key={rowIdx} className="border-b border-white/5 last:border-0">
                                <td className="py-2.5 pr-2 text-white/30 font-bold">{rowIdx + 1}</td>
                                {fila.map((valor, colIdx) => (
                                    <td
                                        key={colIdx}
                                        className={`py-2.5 pr-4 ${colIdx === 0 ? 'font-bold text-white' : 'text-right text-white/70'}`}
                                    >
                                        {formatCell(valor, colIdx)}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {table.hint && (
                <p className="mt-4 text-[12px] leading-relaxed text-white/30 italic">{table.hint}</p>
            )}
        </motion.div>
    );
}

/**
 * Comparación por período (Fase 4 — 28/08/2026): dos rangos de fecha lado a
 * lado, cada uno con su total de ventas/compras/facturas, y la variación %
 * de A sobre B cuando ambos están llenos. Llama a /api/bi/compare-periods,
 * independiente del filtro global de mes/año (ese repinta las tarjetas de
 * arriba; esto es una consulta puntual, a demanda del usuario).
 */
function ComparacionPorPeriodo({ targetDb }) {
    const hoy = new Date().toISOString().slice(0, 10);
    const primerDiaMes = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10);
    const mesAnteriorInicio = new Date(new Date().getFullYear(), new Date().getMonth() - 1, 1).toISOString().slice(0, 10);
    const mesAnteriorFin = new Date(new Date().getFullYear(), new Date().getMonth(), 0).toISOString().slice(0, 10);

    const [abierto, setAbierto] = useState(false);
    const [desdeA, setDesdeA] = useState(primerDiaMes);
    const [hastaA, setHastaA] = useState(hoy);
    const [desdeB, setDesdeB] = useState(mesAnteriorInicio);
    const [hastaB, setHastaB] = useState(mesAnteriorFin);
    const [resultado, setResultado] = useState(null);
    const [cargando, setCargando] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');

    const comparar = async () => {
        setCargando(true);
        setErrorMsg('');
        try {
            const params = new URLSearchParams({ target_db: targetDb, desde_a: desdeA, hasta_a: hastaA });
            if (desdeB && hastaB) {
                params.set('desde_b', desdeB);
                params.set('hasta_b', hastaB);
            }
            const res = await apiGet(`/bi/compare-periods?${params.toString()}`);
            if (res.data?.status === 'ok') {
                setResultado(res.data);
            } else {
                setErrorMsg(res.data?.message || 'No se pudo comparar los períodos.');
                setResultado(null);
            }
        } catch (_err) {
            setErrorMsg('No se pudo conectar con el motor BI.');
            setResultado(null);
        } finally {
            setCargando(false);
        }
    };

    const limpiar = () => {
        setDesdeA(primerDiaMes); setHastaA(hoy);
        setDesdeB(mesAnteriorInicio); setHastaB(mesAnteriorFin);
        setResultado(null); setErrorMsg('');
    };

    const inputClass = "w-full rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 text-[13px] text-white/80 focus:border-cyan-500/40 focus:outline-none [color-scheme:dark]";
    // Defecto detectado en pruebas: el input de fecha no abría el
    // calendario. Causa: sin `color-scheme: dark` (agregado arriba en
    // inputClass), el ícono nativo del calendario queda casi invisible sobre
    // fondo oscuro, y el navegador solo abre el selector si se hace clic
    // justo sobre ese ícono diminuto. `showPicker()` lo abre con un clic en
    // cualquier parte del campo, no soportado en todos los navegadores por
    // eso el try/catch — si falla, el click normal en el ícono sigue
    // funcionando igual que antes.
    const abrirCalendario = (e) => {
        try { e.currentTarget.showPicker?.(); } catch (_err) { /* navegador sin soporte: no pasa nada */ }
    };

    return (
        <section className="rounded-[32px] border border-white/10 p-6 shadow-2xl" style={{ background: 'rgba(255,255,255,0.02)' }}>
            <button
                onClick={() => setAbierto((v) => !v)}
                className="flex w-full items-center justify-between text-left"
                aria-expanded={abierto}
            >
                <div>
                    <h3 className="text-[12px] font-black uppercase tracking-[0.2em] text-white/40">Ventas</h3>
                    <div className="text-[15px] font-bold text-white">Comparación por Período</div>
                </div>
                <ChevronDown size={18} className={`text-white/40 transition-transform ${abierto ? 'rotate-180' : ''}`} />
            </button>

            {abierto && (
                <div className="mt-5 flex flex-col gap-4">
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-4">
                            <div className="mb-2 flex items-center gap-1.5 text-[11px] font-black uppercase tracking-wide text-rose-300">
                                <span className="h-1.5 w-1.5 rounded-full bg-rose-400" /> Período A
                            </div>
                            <div className="flex flex-col gap-2">
                                <label className="text-[11px] font-bold uppercase text-white/40">Desde
                                    <input type="date" value={desdeA} onChange={(e) => setDesdeA(e.target.value)} onClick={abrirCalendario} className={inputClass} />
                                </label>
                                <label className="text-[11px] font-bold uppercase text-white/40">Hasta
                                    <input type="date" value={hastaA} onChange={(e) => setHastaA(e.target.value)} onClick={abrirCalendario} className={inputClass} />
                                </label>
                            </div>
                        </div>
                        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
                            <div className="mb-2 flex items-center gap-1.5 text-[11px] font-black uppercase tracking-wide text-amber-300">
                                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" /> Período B (opcional)
                            </div>
                            <div className="flex flex-col gap-2">
                                <label className="text-[11px] font-bold uppercase text-white/40">Desde
                                    <input type="date" value={desdeB} onChange={(e) => setDesdeB(e.target.value)} onClick={abrirCalendario} className={inputClass} />
                                </label>
                                <label className="text-[11px] font-bold uppercase text-white/40">Hasta
                                    <input type="date" value={hastaB} onChange={(e) => setHastaB(e.target.value)} onClick={abrirCalendario} className={inputClass} />
                                </label>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={comparar}
                            disabled={cargando || !desdeA || !hastaA}
                            className="rounded-lg bg-rose-500/90 px-4 py-2 text-[12px] font-black uppercase tracking-wide text-white hover:bg-rose-500 disabled:opacity-40"
                        >
                            {cargando ? 'Comparando…' : 'Comparar'}
                        </button>
                        <button
                            onClick={limpiar}
                            className="rounded-lg border border-white/10 px-4 py-2 text-[12px] font-black uppercase tracking-wide text-white/60 hover:bg-white/5"
                        >
                            Limpiar
                        </button>
                    </div>

                    {errorMsg && <p className="text-[12px] text-rose-300">{errorMsg}</p>}

                    {resultado && (
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                            {['ventas', 'compras', 'facturas'].map((campo) => {
                                const etiqueta = { ventas: 'Ventas', compras: 'Compras', facturas: 'Facturas' }[campo];
                                const esMoneda = campo !== 'facturas';
                                const valorA = resultado.periodo_a?.[campo] ?? 0;
                                const valorB = resultado.periodo_b?.[campo];
                                const delta = resultado.delta?.[campo];
                                return (
                                    <div key={campo} className="rounded-xl border border-white/10 bg-black/30 p-4">
                                        <div className="text-[11px] font-black uppercase tracking-wide text-white/40">{etiqueta}</div>
                                        <div className="mt-1 text-2xl font-black text-white">
                                            {esMoneda ? formatCardValue(valorA, '$') : formatCardValue(valorA, '')}
                                        </div>
                                        {resultado.periodo_b && (
                                            <div className="mt-1 flex items-center gap-2 text-[12px] text-white/50">
                                                <span>vs {esMoneda ? formatCardValue(valorB, '$') : formatCardValue(valorB, '')}</span>
                                                {typeof delta === 'number' && (
                                                    <span className={`flex items-center gap-0.5 font-black ${delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                        {delta >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                                        {Math.abs(delta)}%
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}
        </section>
    );
}

/**
 * Fase 3 — C2 (drill-down): traduce una tarjeta KPI a una pregunta en
 * lenguaje natural que el propio motor de chat (banco de preguntas,
 * métricas certificadas, IA) ya sabe responder con el detalle completo.
 * En vez de construir un ejecutor de consultas de detalle aparte, se
 * reutiliza el mismo pipeline que ya está probado y endurecido — la
 * tarjeta es solo un atajo hacia una pregunta que el usuario también
 * podría escribir a mano.
 */
export function buildCardDrillQuestion(card) {
    const t = (card?.title || '').toLowerCase();
    if (t.includes('balance comercial')) return 'Muéstrame el detalle de ventas y compras del período más reciente';
    if (t.includes('empleados activos')) return 'Muéstrame la lista de empleados activos';
    if (t.includes('factura')) return 'Muéstrame el listado de facturas del año más reciente';
    if (t.includes('ticket promedio de venta')) return 'Muéstrame las últimas facturas de venta';
    if (t.includes('ticket promedio de compra')) return 'Muéstrame las últimas compras registradas';
    if (t.includes('compra')) return 'Muéstrame el listado de compras del año más reciente';
    if (t.includes('costo n') && t.includes('mina')) return 'Muéstrame el detalle de la nómina del último período';
    if (t.includes('alumno')) return 'Muéstrame el listado de alumnos matriculados';
    if (t.includes('curso')) return 'Muéstrame el listado de cursos ofertados';
    if (t.includes('nivel')) return 'Muéstrame los niveles educativos y cuántos alumnos tiene cada uno';
    if (t.includes('margen')) return 'Muéstrame el detalle de ventas y compras que forman el margen bruto';
    // Estas 4 tarjetas (mirror_manager.get_bi_pulse: "Ventas Hoy/Este Mes/
    // Acumulado del año/Clientes/Productos") tienen datos reales pero caían
    // en el fallback genérico de abajo, cuya redacción ambigua ("detalle
    // detrás de: Productos") hacía que el motor de IA tardara mucho o se
    // quedara sin responder (bug real reportado 29/08/2026). Con una pregunta
    // concreta, igual que ya tienen las demás tarjetas, responden igual de
    // rápido y confiable.
    if (t.includes('este mes')) return 'Muéstrame el detalle de ventas de este mes';
    if (t.startsWith('acumulado')) return 'Muéstrame el detalle de ventas acumuladas del año actual';
    if (t.includes('cliente')) return 'Muéstrame el listado de clientes con facturas registradas';
    if (t.includes('producto')) return 'Muéstrame el listado de productos facturados';
    // Fallback genérico: el motor NL2SQL interpreta el título de la tarjeta.
    return `Muéstrame el detalle detrás de: ${card?.title || ''}`;
}

/**
 * Fase 3 — C2 (drill-down): igual que buildCardDrillQuestion pero para un
 * punto específico de un gráfico (una barra, una porción de dona) — incluye
 * la etiqueta exacta que el usuario clickeó (ej. "Marzo", "Ventas") para
 * que la pregunta generada apunte a ESE dato, no al gráfico completo.
 */
function buildChartDrillQuestion(chart, label) {
    const t = (chart?.title || '').toLowerCase();
    const etiqueta = String(label || '').trim();
    if (!etiqueta) return `Muéstrame el detalle de: ${chart?.title || ''}`;
    if (t.includes('venta')) return `Muéstrame el detalle de ventas de ${etiqueta}`;
    if (t.includes('proveedor')) return `Muéstrame el detalle de compras al proveedor ${etiqueta}`;
    if (t.includes('compra')) return `Muéstrame el detalle de compras de ${etiqueta}`;
    if (t.includes('n') && t.includes('mina')) return `Muéstrame el detalle de nómina de ${etiqueta}`;
    if (t.includes('área') || t.includes('area')) return `Muéstrame los empleados del área ${etiqueta}`;
    if (t.includes('cargo')) return `Muéstrame los empleados con cargo ${etiqueta}`;
    return `Muéstrame el detalle de "${chart?.title || ''}" para ${etiqueta}`;
}

// Etiqueta del sello "Actualizado hace…" que se muestra cuando el pulso BI se
// sirvió desde un snapshot persistente (Capa 2). El backend ya entrega la edad
// en segundos (capture_age_seconds); aquí solo se le da formato legible.
function textoActualizacionDesdeSegundos(segundos) {
    const total = Math.round(segundos);
    if (total < 60) return `Actualizado hace ${total}s`;
    const min = Math.round(total / 60);
    if (min < 60) return `Actualizado hace ${min}m`;
    const h = Math.floor(min / 60);
    const m = min % 60;
    return m === 0 ? `Actualizado hace ${h}h` : `Actualizado hace ${h}h ${m}m`;
}

function formatCardValue(value, unit) {
    const numericValue = Number(value || 0);
    const formatted = new Intl.NumberFormat('es-EC', {
        minimumFractionDigits: unit === '$' ? 2 : 0,
        maximumFractionDigits: unit === '$' ? 2 : 0,
    }).format(numericValue);
    return unit === '$' ? `$${formatted}` : formatted;
}

function buildStats(pulseData, overview, cardCount) {
    const pulseMetrics = pulseData?.metrics || {};
    const overviewKpis = Array.isArray(overview?.kpis) ? overview.kpis : [];

    const stats = [
        {
            id: 'domains',
            label: 'Áreas detectadas',
            value: pulseMetrics.ready_domains ?? overview?.ready_area_count ?? 0,
        },
        {
            id: 'entities',
            label: 'Tablas disponibles',
            value: pulseMetrics.entities_count ?? findOverviewKpi(overviewKpis, 'entities'),
        },
        {
            id: 'views',
            label: 'Datos maestros',
            value: pulseMetrics.master_data_count ?? pulseMetrics.virtual_view_count ?? findOverviewKpi(overviewKpis, 'virtual-views'),
        },
    ];

    // Un "0" no le dice nada al usuario final: si una estadística no tiene
    // valor real, es ruido visual y se omite en vez de mostrarse en cero.
    return stats.filter((s) => Number(s.value) > 0);
}

function findOverviewKpi(kpis, id) {
    const match = kpis.find((item) => item?.id === id);
    return match?.display_value || 0;
}

function getCardIcon(module, colorClass) {
    if (module === 'RRHH') return <Users size={18} className={colorClass} />;
    if (module === 'VENTAS') return <TrendingUp size={18} className={colorClass} />;
    if (module === 'OPERACIONES') return <ShoppingBag size={18} className={colorClass} />;
    if (module === 'ACADEMICO') return <GraduationCap size={18} className={colorClass} />;
    if (module === 'FINANZAS') return <BarChart3 size={18} className={colorClass} />;
    if (module === 'GENERAL') return <Database size={18} className={colorClass} />;
    return <Package size={18} className={colorClass} />;
}

function getCardTheme(module, accent) {
    if (module === 'RRHH' || accent === 'emerald') {
        return {
            bg: 'rgba(16, 185, 129, 0.04)',
            border: 'rgba(16, 185, 129, 0.16)',
            iconBg: 'bg-emerald-500/10',
            iconBorder: 'border-emerald-500/20',
            iconColor: 'text-emerald-400',
            glowColor: 'bg-emerald-500',
            hoverGradient: 'radial-gradient(circle at top right, rgba(16,185,129,0.12), transparent 50%)',
        };
    }
    if (module === 'VENTAS' || accent === 'cyan') {
        return {
            bg: 'rgba(6, 182, 212, 0.04)',
            border: 'rgba(6, 182, 212, 0.16)',
            iconBg: 'bg-cyan-500/10',
            iconBorder: 'border-cyan-500/20',
            iconColor: 'text-cyan-400',
            glowColor: 'bg-cyan-500',
            hoverGradient: 'radial-gradient(circle at top right, rgba(6,182,212,0.12), transparent 50%)',
        };
    }
    if (module === 'OPERACIONES' || accent === 'indigo' || accent === 'violet') {
        return {
            bg: 'rgba(99, 102, 241, 0.04)',
            border: 'rgba(99, 102, 241, 0.16)',
            iconBg: 'bg-indigo-500/10',
            iconBorder: 'border-indigo-500/20',
            iconColor: 'text-indigo-400',
            glowColor: 'bg-indigo-500',
            hoverGradient: 'radial-gradient(circle at top right, rgba(99,102,241,0.12), transparent 50%)',
        };
    }
    if (module === 'ACADEMICO' || accent === 'amber') {
        return {
            bg: 'rgba(245, 158, 11, 0.04)',
            border: 'rgba(245, 158, 11, 0.16)',
            iconBg: 'bg-amber-500/10',
            iconBorder: 'border-amber-500/20',
            iconColor: 'text-amber-400',
            glowColor: 'bg-amber-500',
            hoverGradient: 'radial-gradient(circle at top right, rgba(245,158,11,0.12), transparent 50%)',
        };
    }
    if (module === 'FINANZAS' || accent === 'rose') {
        return {
            bg: 'rgba(244, 63, 94, 0.04)',
            border: 'rgba(244, 63, 94, 0.16)',
            iconBg: 'bg-rose-500/10',
            iconBorder: 'border-rose-500/20',
            iconColor: 'text-rose-400',
            glowColor: 'bg-rose-500',
            hoverGradient: 'radial-gradient(circle at top right, rgba(244,63,94,0.12), transparent 50%)',
        };
    }
    return {
        bg: 'rgba(255, 255, 255, 0.03)',
        border: 'rgba(255, 255, 255, 0.1)',
        iconBg: 'bg-white/5',
        iconBorder: 'border-white/10',
        iconColor: 'text-white/45',
        glowColor: 'bg-white',
        hoverGradient: 'radial-gradient(circle at top right, rgba(255,255,255,0.08), transparent 50%)',
    };
}
