/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-UI-VIZ-03]
 * ============================================================================
 * ARCHIVO: ProfessionalPaySlip.jsx
 * MÓDULO: UI / Executive Documents
 * 
 * 🎯 PROPÓSITO GERENCIAL:
 * Es el "Renderizador Final" del Rol de Pagos Individual. 
 * Muestra el documento de un colaborador con un diseño corporativo y claro,
 * separando Haberes de Descuentos y calculando indicadores clave (Neto).
 * 
 * 📍 PUNTO DE INTERFAZ:
 * Elemento hijo de `PayslipView.jsx`. Se instancia una vez por cada empleado.
 * 
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Normalización de glosarios SQL (entiende que 'sueldobase' y 'salario' son lo mismo).
 * - Clasificación automática de sumas vs restas basado en expresiones regulares.
 * - Cálculo al vuelo de proyecciones como "Costo Total Empresa" e "IESS Patronal".
 * ============================================================================
 */

import React, { useRef, useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { formatValue, parseNum } from '../utils/formatters';
import { dbToBusinessName } from '../constants/appConfig';

/** Quita acentos/símbolos para que el nombre de archivo sea seguro en cualquier SO. */
const nombreArchivoSeguro = (texto) =>
    String(texto || '')
        .normalize('NFD')
        .replace(/[̀-ͯ]/g, '')
        .replace(/[^a-zA-Z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '')
        .slice(0, 80);

const normalizeKey = (value) =>
    String(value ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]/gi, '')
        .toLowerCase();

const containsAny = (value, keywords) => {
    const source = normalizeKey(value);
    return keywords.some((k) => source.includes(normalizeKey(k)));
};

const isMeaningfulText = (value) => {
    const text = String(value ?? '').trim();
    if (!text) return false;
    if (/^-?\d+([.,]\d+)?$/.test(text)) return false;
    return text.length >= 3;
};

const createColumnResolver = (columns) => {
    const normalized = (columns || []).map((col) => normalizeKey(col));
    return (...aliases) => {
        for (const alias of aliases) {
            const nAlias = normalizeKey(alias);
            const exact = normalized.findIndex((nCol) => nCol === nAlias);
            if (exact !== -1) return exact;
            const partial = normalized.findIndex((nCol) => nCol.includes(nAlias));
            if (partial !== -1) return partial;
        }
        return -1;
    };
};

const readAt = (row, idx) => (idx >= 0 && Array.isArray(row) ? row[idx] : null);

const sumValues = (rows, predicate) =>
    rows.reduce((acc, row) => (predicate(row) ? acc + row.value : acc), 0);

const hasValue = (value) => {
    if (value === null || value === undefined) return false;
    const text = String(value).trim();
    return text !== '' && text !== '-';
};

const isZeroLike = (value) => /^0(?:[.,]0+)?$/.test(String(value ?? '').trim());

const formatDateValue = (value) => {
    if (!hasValue(value)) return '-';
    const raw = String(value).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        const [year, month, day] = raw.split('-');
        return `${day}/${month}/${year}`;
    }
    if (/^\d{8}$/.test(raw)) {
        const currentYear = new Date().getFullYear();
        const first4 = Number(raw.slice(0, 4));
        if (first4 >= 1900 && first4 <= currentYear + 1) {
            return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)}`;
        }
        return `${raw.slice(0, 2)}/${raw.slice(2, 4)}/${raw.slice(4, 8)}`;
    }
    if (/^\d{1,2}[\/.-]\d{1,2}[\/.-]\d{2,4}$/.test(raw)) {
        return raw.replace(/\./g, '/').replace(/-/g, '/');
    }
    return raw;
};

export function ProfessionalPaySlip({ employee, allRows, columns, dbName, meta = null }) {
    const cardRef = useRef(null);
    const [descargando, setDescargando] = useState(false);
    const [errorDescarga, setErrorDescarga] = useState('');

    const findCol = createColumnResolver(columns);

    const cedulaIdx = findCol('cedula', 'identificacion', 'cedulaid', 'id');
    const nombresIdx = findCol('nombres', 'nombre', 'empleado', 'trabajador');
    const cargoIdx = findCol('cargo', 'puesto');
    const areaIdx = findCol('area', 'departamento', 'unidad');
    const codigoIdx = findCol('codigo', 'codigotrabajador', 'idtrabajador');
    const mesIdx = findCol('mes', 'periodomes');
    const anioIdx = findCol('anio', 'ano', 'periodoanio');
    const fechaIngresoIdx = findCol('fechaingreso', 'ingreso', 'fechacontrato');
    const empresaIdx = findCol('empresa', 'compania', 'organizacion', 'razonsocial', 'negocio');
    const jornadaIdx = findCol('jornada', 'turno');

    const valorIdx = findCol('valor', 'monto', 'importe', 'valorrubro');
    const categoriaIdx = findCol('rubro', 'tipo', 'categoria');
    const detalleIdx = findCol('descripcion', 'detalle', 'concepto', 'nombrerubro');

    const metaIndexes = new Set([
        cedulaIdx,
        nombresIdx,
        cargoIdx,
        areaIdx,
        codigoIdx,
        mesIdx,
        anioIdx,
        fechaIngresoIdx,
        empresaIdx,
        jornadaIdx,
        valorIdx,
        categoriaIdx,
    ]);

    const breakdownRows = Array.isArray(allRows) && allRows.length ? allRows : [employee];
    const sourceRows = [employee, ...breakdownRows];

    const getMainValue = (aliases, options = {}) => {
        const { allowZero = false, preferText = false } = options;
        const idx = findCol(...aliases);
        if (idx < 0) return null;
        for (const row of sourceRows) {
            const candidate = readAt(row, idx);
            if (!hasValue(candidate)) continue;
            const text = String(candidate).trim();
            if (!allowZero && isZeroLike(text)) continue;
            if (preferText && !/[a-zA-Z]/.test(text)) continue;
            return candidate;
        }
        return null;
    };

    const nombres = meta?.nombres || getMainValue(['nombres', 'nombre', 'empleado', 'trabajador'], { preferText: true });
    const cedula = meta?.cedula || getMainValue(['cedula', 'identificacion', 'cedulaid', 'id'], { allowZero: true });
    const cargo = meta?.cargo || getMainValue(['cargo', 'puesto'], { preferText: true });
    const area = meta?.area || getMainValue(['area', 'departamento', 'unidad'], { preferText: true });
    const codigo = getMainValue(['codigo', 'codigotrabajador', 'idtrabajador'], { allowZero: true }) || cedula;
    const empresa = meta?.empresa || getMainValue(['empresa', 'compania', 'organizacion', 'razonsocial', 'negocio'], { preferText: true }) || dbToBusinessName(dbName) || 'EMPRESA';
    const jornada = getMainValue(['jornada', 'turno', 'horario'], { preferText: true });
    const fechaIngreso = getMainValue(['fechaingreso', 'ingreso', 'fechacontrato'], { allowZero: false });

    const mes = meta?.periodo_mes || getMainValue(['mes', 'periodomes'], { allowZero: false });
    const anio = meta?.periodo_anio || getMainValue(['anio', 'ano', 'periodoanio'], { allowZero: false });
    const periodo = [mes, anio].filter(hasValue).join(' ').trim();

    const rawSueldoBase = getMainValue(['sueldobase', 'sueldo', 'salariobase'], { allowZero: false });
    const sueldoBase = parseNum(rawSueldoBase);

    const payrollRows = breakdownRows
        .map((row, index) => {
            const value = parseNum(readAt(row, valorIdx));

            const rawCategory = String(readAt(row, categoriaIdx) ?? '').trim();
            const rawDetail = String(readAt(row, detalleIdx) ?? '').trim();

            let description = rawDetail;
            if (!isMeaningfulText(description)) {
                const fallbackCell = row.find((cell, idx) => {
                    if (metaIndexes.has(idx)) return false;
                    return isMeaningfulText(cell);
                });
                description = String(fallbackCell ?? rawCategory ?? 'RUBRO').trim();
            }

            const categoryNorm = normalizeKey(rawCategory);
            const descriptionNorm = normalizeKey(description);

            let side = 'HABER';
            if (
                value < 0 ||
                categoryNorm.includes('egreso') ||
                categoryNorm.includes('descuento') ||
                categoryNorm.includes('retencion') ||
                descriptionNorm.includes('retencion') ||
                descriptionNorm.includes('descuento')
            ) {
                side = 'DSCTO';
            }

            return {
                index,
                description,
                value: Math.abs(value),
                side,
                normDesc: descriptionNorm,
            };
        })
        .filter((row) => row.value > 0);

    payrollRows.sort((a, b) => {
        if (a.side === b.side) return a.index - b.index;
        return a.side === 'HABER' ? -1 : 1;
    });

    const haberesTotal = sumValues(payrollRows, (row) => row.side === 'HABER');
    const descuentosTotal = sumValues(payrollRows, (row) => row.side === 'DSCTO');

    const netoDirecto = parseNum(
        getMainValue(['netoarecibir', 'liquidoarecibir', 'totalrecibir', 'neto'], { allowZero: false })
    );
    const netoFinal = netoDirecto > 0 ? netoDirecto : haberesTotal - descuentosTotal;

    const aportePersonalIess = sumValues(
        payrollRows,
        (row) =>
            row.side === 'DSCTO' &&
            containsAny(row.normDesc, ['iess']) &&
            containsAny(row.normDesc, ['personal', '9', '945'])
    );

    const aportePatronalIessDirecto = sumValues(
        payrollRows,
        (row) =>
            row.side === 'HABER' &&
            containsAny(row.normDesc, ['iess']) &&
            containsAny(row.normDesc, ['patronal', '1215'])
    );
    const aportePatronalIess =
        aportePatronalIessDirecto > 0 ? aportePatronalIessDirecto : sueldoBase * 0.1215;

    const decimoTercero = sumValues(payrollRows, (row) =>
        containsAny(row.normDesc, ['decimotercero', 'decimo3', 'decimotercer', 'decimo tercer'])
    );
    const decimoCuarto = sumValues(payrollRows, (row) =>
        containsAny(row.normDesc, ['decimocuarto', 'decimo4', 'decimo cuarto'])
    );
    const fondoReserva = sumValues(payrollRows, (row) =>
        containsAny(row.normDesc, ['fondoreserva', 'fondo de reserva'])
    );

    const costoEmpresa = haberesTotal + aportePatronalIess;

    // Descarga en PDF — captura la tarjeta EXACTAMENTE como se ve en pantalla
    // (mismo diseño, "formato original") con html2canvas-pro (ya usado en el
    // proyecto: maneja bien los colores modernos de Tailwind que este
    // componente usa, a diferencia del html2canvas original). El botón vive
    // FUERA del elemento capturado (cardRef), así que nunca sale dentro del
    // PDF que genera.
    const descargarPdf = async () => {
        if (descargando || !cardRef.current) return;
        setDescargando(true);
        setErrorDescarga('');
        try {
            const [{ default: html2canvas }, { default: JsPDF }] = await Promise.all([
                import('html2canvas-pro'),
                import('jspdf'),
            ]);

            const canvas = await html2canvas(cardRef.current, {
                scale: 2,
                backgroundColor: '#ffffff',
                useCORS: true,
            });
            const imgData = canvas.toDataURL('image/png');

            // Página A4 estándar — mismo patrón que ya usa el exportador de
            // gráficos (DataVisualizer.jsx: exportarGraficoPdf). Bug real
            // detectado en pruebas (30/08/2026): la primera versión
            // usaba el tamaño de página = tamaño del canvas en píxeles
            // crudos (con scale:2 eso da una página de ~20+ pulgadas de
            // ancho). Un PDF así de gigante obliga a cualquier visor a
            // achicarlo mucho para que quepa en la ventana, y ese porcentaje
            // de "ajustar a página" varía según el tamaño de la ventana del
            // navegador (por eso el mismo archivo se veía a 40% en una
            // ventana y a 25% en otra) — nunca es un valor fijo que el PDF
            // pueda imponer. Con una página A4 normal, el "ajustar a página"
            // de cualquier visor cae en un porcentaje razonable y estable,
            // como con cualquier documento común.
            const pdf = new JsPDF({
                orientation: canvas.width >= canvas.height ? 'landscape' : 'portrait',
                unit: 'pt',
                format: 'a4',
            });
            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();
            const margin = 24;
            const areaAncho = pageWidth - margin * 2;
            const areaAlto = pageHeight - margin * 2;

            // Escala la imagen para que quepa completa dentro del margen,
            // preservando su proporción real (nunca la deforma).
            const escala = Math.min(areaAncho / canvas.width, areaAlto / canvas.height);
            const imgAncho = canvas.width * escala;
            const imgAlto = canvas.height * escala;
            const x = (pageWidth - imgAncho) / 2;
            const y = margin;
            pdf.addImage(imgData, 'PNG', x, y, imgAncho, imgAlto);

            const archivo = `Rol_de_Pago_${nombreArchivoSeguro(nombres) || 'trabajador'}_${nombreArchivoSeguro(periodo) || 'periodo'}.pdf`;
            pdf.save(archivo);
        } catch (err) {
            setErrorDescarga('No se pudo generar el PDF. Intenta de nuevo.');
            console.error('[ProfessionalPaySlip] Error exportando PDF:', err);
        } finally {
            setDescargando(false);
        }
    };

    return (
        <div className="w-full max-w-5xl mx-auto my-6">
            <div className="flex items-center justify-end gap-3 mb-3 px-1">
                {errorDescarga && (
                    <span className="text-[12px] font-bold text-rose-300">{errorDescarga}</span>
                )}
                <button
                    type="button"
                    onClick={descargarPdf}
                    disabled={descargando}
                    className="inline-flex items-center gap-2 rounded-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-60 disabled:cursor-not-allowed text-white text-[12px] font-black uppercase tracking-[0.16em] px-5 py-2.5 shadow-lg shadow-cyan-900/30 transition-colors"
                >
                    {descargando ? (
                        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                    ) : (
                        <Download size={14} aria-hidden="true" />
                    )}
                    {descargando ? 'Generando PDF…' : 'Descargar PDF'}
                </button>
            </div>

            <div ref={cardRef} className="w-full rounded-[30px] border border-cyan-500/25 bg-[linear-gradient(145deg,#f0fcff_0%,#ddf6ff_40%,#f6fdff_100%)] text-slate-900 shadow-[0_25px_80px_rgba(0,0,0,0.35)] overflow-hidden">
            <div className="h-2 w-full bg-gradient-to-r from-cyan-700 via-cyan-500 to-cyan-700" />

            <div className="px-6 md:px-10 pt-6 md:pt-8 pb-6 border-b border-slate-200/80">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                    <div>
                        <h1 className="text-2xl md:text-3xl font-black tracking-tight text-slate-800">ROL DE PAGO INDIVIDUAL</h1>
                        <p className="text-[12px] md:text-xs font-black uppercase tracking-[0.28em] text-slate-500 mt-1">
                            Comprobante de haberes y descuentos
                        </p>
                    </div>
                    <div className="text-left md:text-right">
                        <div className="inline-flex px-3 py-1 rounded-full bg-cyan-700/10 border border-cyan-700/20 text-[12px] font-black uppercase tracking-[0.2em] text-cyan-800">
                            Original trabajador
                        </div>
                        <p className="text-[12px] font-black uppercase tracking-[0.2em] text-slate-500 mt-2">Periodo de pago</p>
                        <p className="text-2xl font-black text-cyan-700">{periodo || 'Actual'}</p>
                    </div>
                </div>
            </div>

            <div className="px-6 md:px-10 py-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-5 border-b border-slate-200/80">
                <div>
                    <p className="text-[12px] font-black uppercase tracking-[0.16em] text-slate-500">Cedula / ID</p>
                    <p className="text-sm md:text-base font-black text-slate-800 mt-1">{formatValue(cedula, 'cedula')}</p>
                </div>
                <div className="sm:col-span-2">
                    <p className="text-[12px] font-black uppercase tracking-[0.16em] text-slate-500">Nombres completos</p>
                    <p className="text-sm md:text-base font-black text-slate-800 mt-1 uppercase">{formatValue(nombres)}</p>
                </div>
                <div>
                    <p className="text-[12px] font-black uppercase tracking-[0.16em] text-slate-500">Codigo</p>
                    <p className="text-sm md:text-base font-black text-slate-800 mt-1">{formatValue(codigo, 'codigo')}</p>
                </div>
                <div>
                    <p className="text-[12px] font-black uppercase tracking-[0.16em] text-slate-500">Cargo</p>
                    <p className="text-sm font-bold text-slate-800 mt-1 uppercase">{formatValue(cargo, 'cargo')}</p>
                </div>
                <div>
                    <p className="text-[12px] font-black uppercase tracking-[0.16em] text-slate-500">Departamento / Area</p>
                    <p className="text-sm font-bold text-slate-800 mt-1 uppercase">{formatValue(area, 'area')}</p>
                </div>
                <div>
                    <p className="text-[12px] font-black uppercase tracking-[0.16em] text-slate-500">Sueldo base</p>
                    <p className="text-base md:text-lg font-black text-slate-900 mt-1">$ {formatValue(sueldoBase)}</p>
                </div>
                <div>
                    <p className="text-[12px] font-black uppercase tracking-[0.16em] text-slate-500">Empresa</p>
                    <p className="text-sm font-bold text-slate-800 mt-1 uppercase">{formatValue(empresa)}</p>
                </div>
            </div>

            <div className="px-4 md:px-8 py-6">
                <div className="overflow-hidden border border-slate-200 bg-white/65">
                    <div className="grid grid-cols-12 bg-slate-800 text-white text-[12px] font-black uppercase tracking-[0.25em]">
                        <div className="col-span-6 md:col-span-8 px-4 py-3">Descripcion</div>
                        <div className="col-span-3 md:col-span-2 px-4 py-3 text-right">Haberes (+)</div>
                        <div className="col-span-3 md:col-span-2 px-4 py-3 text-right">Dsctos (-)</div>
                    </div>

                    <div className="divide-y divide-slate-200/90">
                        {payrollRows.length > 0 ? (
                            payrollRows.map((row, idx) => (
                                <div key={`${row.description}-${idx}`} className="grid grid-cols-12 items-center text-xs md:text-sm">
                                    <div className="col-span-6 md:col-span-8 px-4 py-2.5 font-bold text-slate-700 uppercase">{row.description}</div>
                                    <div className="col-span-3 md:col-span-2 px-4 py-2.5 text-right font-black text-slate-800">
                                        {row.side === 'HABER' ? `$ ${formatValue(row.value)}` : ''}
                                    </div>
                                    <div className="col-span-3 md:col-span-2 px-4 py-2.5 text-right font-black text-rose-600">
                                        {row.side === 'DSCTO' ? `$ ${formatValue(row.value)}` : ''}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="px-4 py-6 text-center text-sm font-bold text-slate-500">
                                No hay rubros disponibles para este rol.
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="px-6 md:px-10 pb-4 flex justify-end">
                <div className="w-full md:w-[420px] space-y-2">
                    <div className="flex items-center justify-between text-sm font-black text-slate-700">
                        <span className="uppercase tracking-[0.12em]">Suma de haberes</span>
                        <span>$ {formatValue(haberesTotal)}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm font-black text-rose-700">
                        <span className="uppercase tracking-[0.12em]">Total descuentos</span>
                        <span>$ {formatValue(descuentosTotal)}</span>
                    </div>
                    <div className="rounded-[20px] bg-gradient-to-r from-cyan-700 to-cyan-500 text-white px-6 py-3 shadow-lg">
                        <div className="flex items-end justify-between gap-3">
                            <div>
                                <p className="text-[12px] uppercase tracking-[0.26em] font-black opacity-90">Liquido a recibir</p>
                                <p className="text-xs font-bold opacity-85">Neto pagado</p>
                            </div>
                            <p className="text-3xl font-black tracking-tight">$ {formatValue(netoFinal)}</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="px-6 md:px-10 pb-8">
                <div className="rounded-[24px] border border-cyan-700/20 bg-cyan-900/5 px-6 md:px-8 py-5">
                    <h3 className="text-sm md:text-base font-black uppercase tracking-[0.18em] text-cyan-900">
                        Indicadores laborales (uso corporativo)
                    </h3>
                    <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                        <div className="rounded-2xl bg-white/75 border border-slate-200 px-4 py-3">
                            <p className="text-[12px] font-black uppercase tracking-[0.15em] text-slate-500">Aporte personal IESS</p>
                            <p className="text-lg font-black text-slate-800">$ {formatValue(aportePersonalIess)}</p>
                        </div>
                        <div className="rounded-2xl bg-white/75 border border-slate-200 px-4 py-3">
                            <p className="text-[12px] font-black uppercase tracking-[0.15em] text-slate-500">Aporte patronal IESS</p>
                            <p className="text-lg font-black text-slate-800">$ {formatValue(aportePatronalIess)}</p>
                        </div>
                        <div className="rounded-2xl bg-white/75 border border-slate-200 px-4 py-3">
                            <p className="text-[12px] font-black uppercase tracking-[0.15em] text-slate-500">Decimo tercero + cuarto</p>
                            <p className="text-lg font-black text-slate-800">$ {formatValue(decimoTercero + decimoCuarto)}</p>
                        </div>
                        <div className="rounded-2xl bg-white/75 border border-slate-200 px-4 py-3">
                            <p className="text-[12px] font-black uppercase tracking-[0.15em] text-slate-500">Fondo de reserva</p>
                            <p className="text-lg font-black text-slate-800">$ {formatValue(fondoReserva)}</p>
                        </div>
                        <div className="rounded-2xl bg-white/75 border border-slate-200 px-4 py-3">
                            <p className="text-[12px] font-black uppercase tracking-[0.15em] text-slate-500">Jornada laboral</p>
                            <p className="text-sm font-black text-slate-800 uppercase">{formatValue(jornada)}</p>
                        </div>
                        <div className="rounded-2xl bg-white/75 border border-slate-200 px-4 py-3">
                            <p className="text-[12px] font-black uppercase tracking-[0.15em] text-slate-500">Fecha de ingreso</p>
                            <p className="text-sm font-black text-slate-800">{formatDateValue(fechaIngreso)}</p>
                        </div>
                        <div className="rounded-2xl bg-white/75 border border-slate-200 px-4 py-3 sm:col-span-2">
                            <p className="text-[12px] font-black uppercase tracking-[0.15em] text-slate-500">Costo empresa estimado</p>
                            <p className="text-lg font-black text-slate-800">$ {formatValue(costoEmpresa)}</p>
                        </div>
                    </div>
                </div>
            </div>
            </div>
        </div>
    );
};
