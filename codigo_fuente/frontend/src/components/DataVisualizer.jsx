/**
 * @file Visualizador de resultados de consulta. Convierte las filas que devuelve el
 * backend en la vista más adecuada: KPI de valor único, gráfico ApexCharts (barras,
 * línea, área, pastel, radar) con alternador de tipo, tabla con búsqueda, orden,
 * paginación y totales, o roles de pago (PayslipView). Exporta la tabla a Excel
 * (/api/query/exportar-tabla-excel, con CSV de respaldo) y el gráfico con su tabla a
 * PDF. Lo usa ChatMessage cuando la respuesta trae datos estructurados.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React, { useRef, useState } from 'react';
import Chart from 'react-apexcharts';
import {
    AreaChart, ArrowUpDown, BarChart3, ChevronDown, ChevronLeft, ChevronRight,
    ChevronUp, Download, FileText, LineChart, PieChart, Radar as RadarIcon, Search,
} from 'lucide-react';
import { formatValue, formatHeader, formatAxisName, parseNum } from '../utils/formatters';
import { PayslipView } from './PayslipView';
import { downloadRowsAsCsv } from '../utils/csvExport';
import { apiPost } from '../services/api';

const PAGE_SIZE = 15;

// Limpia el marcador invisible que se le agrega a la primera columna para
// que ApexCharts no colapse categorías con el mismo texto (ver más abajo).
// Sin esto, el CSV exportado llevaría caracteres invisibles pegados.
const cleanCellText = (value) => String(value ?? '').replace(/[\u200B]/g, '');

// Limpia un valor para exportar SIN convertirlo a texto: los números deben
// llegar al Excel como números (con formato de miles) y no como cadenas. Solo
// se quita de los textos el marcador invisible de ApexCharts.
const limpiarValorExport = (v) => (typeof v === 'string' ? cleanCellText(v) : v);

// Exportación a Excel: genera un libro .xlsx con el mismo formato profesional
// (cabecera azul, bordes, filas alternadas, autofiltro) que la sección de
// Indicadores, vía /api/query/exportar-tabla-excel. Los datos reales
// (filtrados y ordenados) se envían al backend, que solo les aplica el
// formato. Si el endpoint no responde, se descarga un CSV para que la
// exportación nunca se pierda.
const exportarTablaExcel = async (columns, rows, filaTotales) => {
    const body = {
        columns: columns.map((c) => formatHeader(c)),
        rows: rows.map((row) => columns.map((c) => limpiarValorExport(row[c]))),
        filename: `datos_${Date.now()}`,
    };
    if (filaTotales) body.rows.push(filaTotales.map((v) => limpiarValorExport(v)));
    try {
        const res = await apiPost('/query/exportar-tabla-excel', body, { responseType: 'blob' });
        const disposition = res.headers?.['content-disposition'] || '';
        const match = disposition.match(/filename="?([^"]+)"?/);
        const filename = match ? match[1] : `${body.filename}.xlsx`;
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        console.error('[DataVisualizer] Error exportando Excel, cayendo a CSV:', err);
        const csvHeader = columns.map((c) => formatHeader(c));
        const csvLines = rows.map((row) => columns.map((c) => cleanCellText(row[c])));
        if (filaTotales) csvLines.push(filaTotales.map((v) => cleanCellText(v)));
        downloadRowsAsCsv([csvHeader, ...csvLines], `datos_${Date.now()}`);
    }
};

// Alternador de tipo de gráfico: la IA elige un tipo por defecto (viz_type),
// pero el usuario puede cambiarlo con un clic sin repetir la consulta.
const CHART_TYPE_OPTIONS = [
    { id: 'bar', label: 'Barras', Icon: BarChart3 },
    { id: 'line', label: 'Líneas', Icon: LineChart },
    { id: 'area', label: 'Área', Icon: AreaChart },
    { id: 'pie', label: 'Circular', Icon: PieChart },
    { id: 'radar', label: 'Radar', Icon: RadarIcon },
];

// Botonera para cambiar el tipo de gráfico.
const ChartTypeSwitch = ({ activeType, onChange }) => (
    <div
        className="flex items-center gap-0.5 p-0.5 bg-white/5 rounded-lg border border-white/10"
        role="group"
        aria-label="Cambiar tipo de gráfico"
    >
        {CHART_TYPE_OPTIONS.map(({ id, label, Icon }) => (
            <button
                key={id}
                type="button"
                onClick={() => onChange(id)}
                aria-pressed={activeType === id}
                title={label}
                className={`p-1.5 rounded-md transition-colors ${
                    activeType === id
                        ? 'bg-[#3B82F6] text-white'
                        : 'text-white/35 hover:text-white/70 hover:bg-white/5'
                }`}
            >
                <Icon size={13} />
            </button>
        ))}
    </div>
);

/**
 * Muestra el resultado de una consulta como KPI, gráfico, tabla o roles de pago,
 * según el tipo sugerido y la forma de los datos.
 *
 * @param {object} props
 * @param {object} props.result - Resultado normalizado: `rows`, `columns` y
 *   `visualization_type` ('table', 'bar', 'line', 'pie', 'area', 'radar', 'kpi',
 *   'value' o 'payslip').
 * @returns {JSX.Element|null} La visualización, o null si no hay filas.
 */
export const DataVisualizer = ({ result }) => {
    // El usuario puede sobreescribir localmente el tipo de gráfico sugerido
    // por la IA (visualization_type) sin volver a consultar al backend.
    const [chartOverride, setChartOverride] = useState(null);

    // Data grid de la tabla de resultados: búsqueda, orden por columna y
    // paginación, todo en el cliente (los datos ya llegaron completos).
    const [searchFilter, setSearchFilter] = useState('');
    const [sortConfig, setSortConfig] = useState(null); // { key, direction }
    const [currentPage, setCurrentPage] = useState(1);

    // Exportación a PDF lista para imprimir: imagen del gráfico seleccionado y
    // su tabla de datos en un solo documento. El ref apunta siempre al <Chart>
    // montado en ese momento (solo uno a la vez) y se usa el exportador propio
    // de ApexCharts (dataURI) en vez de html2canvas: ApexCharts rasteriza su
    // propio SVG sin depender de que el navegador entienda cada función de
    // color CSS que usa Tailwind.
    const chartRef = useRef(null);
    const [pdfExporting, setPdfExporting] = useState(false);
    const [pdfError, setPdfError] = useState('');
    const [excelExporting, setExcelExporting] = useState(false);

    if (!result || !result.rows || result.rows.length === 0) return null;
    const { rows, columns, visualization_type: type } = result;

    // Normaliza los datos: convierte el arreglo de arreglos en arreglo de objetos.
    const data = React.useMemo(() => {
        if (!rows || !columns) return [];
        
        return rows.map((row, index) => {
            let obj = {};
            if (Array.isArray(row)) {
                columns.forEach((col, idx) => {
                    obj[col] = row[idx];
                });
            } else {
                obj = { ...row };
            }

            // Convierte a número los valores numéricos (salvo identificadores) para
            // no sumar cadenas.
            Object.keys(obj).forEach(key => {
                const val = obj[key];
                if (val !== null && val !== undefined && typeof val !== 'number') {
                    const strVal = String(val).trim();
                    const n = parseNum(strVal);
                    const isId = /cédula|cedula|ruc|id|código|codigo/i.test(key);
                    if (!isId && !isNaN(n) && !/[a-zA-Z]/.test(strVal)) {
                        obj[key] = n;
                    }
                }
            });

            // Se añade a la primera columna un marcador invisible distinto por fila
            // para que los gráficos no fusionen elementos con nombres idénticos:
            const dataKeyX = columns[0];
            if (obj[dataKeyX]) {
                obj[dataKeyX] = String(obj[dataKeyX]) + '\u200B'.repeat(index);
            }

            return obj;
        });
    }, [rows, columns]);

    if (type === 'payslip') return <PayslipView data={rows} columns={columns} />;

    // --- Valor único (KPI) ---
    const isSingleResult = data.length === 1 && (Array.isArray(data[0]) ? data[0].length <= 2 : Object.keys(data[0] || {}).length <= 2);
    // Se fuerza el KPI si el tipo es 'value' o 'kpi', o si es un resultado único y no se pidió un gráfico específico.
    const chartTypes = ['bar', 'line', 'pie', 'area', 'radar'];
    if (type === 'value' || type === 'kpi' || (isSingleResult && type !== 'table' && !chartTypes.includes(type))) {
        const valToDisplay = Array.isArray(data[0])
            ? (data[0].length > 1 ? data[0][1] : data[0][0])
            : (data[0] ? data[0][columns[1] || columns[0] || Object.keys(data[0])[0]] : null);
        
        const labelToDisplay = Array.isArray(data[0])
            ? (data[0].length > 1 ? columns[1] : columns[0])
            : (columns[1] || columns[0] || (data[0] ? Object.keys(data[0])[0] : 'Total'));

        return (
            <div className="w-full flex flex-col items-center justify-center p-3 bg-[#0f172a]/40 backdrop-blur-md rounded-[32px] border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.3)] animate-in zoom-in slide-in-from-bottom-4 duration-700 my-3 relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/10 via-transparent to-indigo-500/10 opacity-50" />
                <div className="absolute top-[-20%] right-[-10%] w-64 h-64 bg-cyan-400/10 blur-[80px] rounded-full animate-pulse" />
                
                <div className="relative z-10 flex flex-col items-center">
                    <div className="bg-white/5 p-1.5 rounded-full mb-2 border border-white/10 shadow-inner">
                        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-ping" />
                    </div>

                    <div className="text-[12px] font-black text-cyan-400/80 uppercase tracking-[0.5em] mb-1 text-center drop-shadow-sm">
                        {formatHeader(labelToDisplay)}
                    </div>
                    
                    <div className="text-5xl md:text-7xl font-black text-white leading-none tracking-tighter text-center selection:bg-cyan-500/30">
                        <span className="bg-clip-text text-transparent bg-gradient-to-b from-white to-white/70 drop-shadow-[0_0_30px_rgba(255,255,255,0.15)]">
                            {formatValue(valToDisplay, labelToDisplay)}
                        </span>
                    </div>
                    
                    <div className="mt-2 w-12 h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent rounded-full" />
                </div>
            </div>
        );
    }

    if (type === 'text') return null;

    // --- Selección de columnas X/Y + serie de datos para el gráfico ---
    // Se calcula UNA vez fuera de renderChart para poder mostrar el total de
    // la serie junto al título del gráfico (así no hay que sumar las barras
    // manualmente).
    const dataKeyX = columns[0];
    const isIdColumn = (name) => /cédula|cedula|ruc|id|código|codigo|identificación/i.test(name);

    let dataKeyY = columns[1] || columns[0];
    if (columns.length > 2) {
        const numericKey = columns.slice(1).find(col => {
            if (isIdColumn(col)) return false;
            const sample = data[0]?.[col];
            if (typeof sample === 'number') return true;
            const n = parseNum(sample);
            return !isNaN(n) && n !== 0 && String(sample).replace(/[^\d]/g, '').length > 0;
        });
        if (numericKey) dataKeyY = numericKey;
    } else if (isIdColumn(dataKeyY) && columns.length > 1) {
        dataKeyY = columns[1];
    }

    // Datos para ApexCharts.
    const categories = data.map(item => formatAxisName(item[dataKeyX]));
    // parseNum entiende los separadores latinoamericanos, así el pastel o la
    // dona recibe siempre números correctos y no suma valores inflados.
    const seriesData = data.map(item => {
        const raw = item[dataKeyY];
        if (typeof raw === 'number') return isFinite(raw) ? raw : 0;
        const n = parseNum(raw);
        return isNaN(n) ? 0 : n;
    });
    // Suma total de la serie mostrada, para que el usuario no tenga que sumar
    // barra por barra.
    const totalGrafico = seriesData.reduce((acc, v) => acc + v, 0);

    // --- Gráficos (ApexCharts) ---
    const renderChart = () => {
        const chartType = chartOverride || type || 'bar';

        const apexOptions = {
            chart: {
                id: 'apex-chart',
                toolbar: { show: false },
                background: 'transparent',
                foreColor: '#94a3b8',
                fontFamily: 'Inter, sans-serif',
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 1000,
                    animateGradually: { enabled: true, delay: 150 },
                    dynamicAnimation: { enabled: true, speed: 350 }
                },
                dropShadow: {
                    enabled: true,
                    top: 10,
                    left: 0,
                    blur: 10,
                    opacity: 0.1,
                    color: '#22d3ee'
                }
            },
            stroke: {
                curve: 'smooth',
                width: 3,
                lineCap: 'round'
            },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.5,
                    opacityTo: 0,
                    stops: [0, 90, 100],
                    colorStops: [
                        { offset: 0, color: '#22d3ee', opacity: 0.5 },
                        { offset: 100, color: '#818cf8', opacity: 0 }
                    ]
                }
            },
            xaxis: {
                categories: categories,
                axisBorder: { show: false },
                axisTicks: { show: false },
                labels: { style: { fontSize: '10px', fontWeight: 600 } }
            },
            yaxis: {
                labels: {
                    style: { fontSize: '10px', fontWeight: 600 },
                    formatter: (val) => formatValue(val)
                }
            },
            dataLabels: {
                enabled: true,
                style: { fontSize: '10px', fontWeight: 'bold', colors: ['#fff'] },
                background: { enabled: true, foreColor: '#0f172a', padding: 4, borderRadius: 6, borderWidth: 0, opacity: 0.9 },
                formatter: (val) => formatValue(val)
            },
            grid: {
                borderColor: 'rgba(255,255,255,0.03)',
                strokeDashArray: 4,
                padding: { left: 20, right: 20 }
            },
            theme: { mode: 'dark' },
            colors: ['#22d3ee'],
            tooltip: {
                theme: 'dark',
                x: { show: true },
                y: { formatter: (val) => formatValue(val) },
                style: { fontSize: '12px' },
                custom: function({ series, seriesIndex, dataPointIndex, w }) {
                    // Extrae los datos de forma tolerante: la estructura de ApexCharts varía según el tipo de gráfico.
                    let val = 0;
                    let label = 'Dato';
                    
                    try {
                        if (w.config.chart.type === 'donut' || w.config.chart.type === 'pie') {
                            // En dona y pastel, series es un arreglo plano de valores
                            val = series[seriesIndex] ?? w.globals.series[seriesIndex] ?? 0;
                            label = w.globals.labels[seriesIndex] ?? 'Dato';
                        } else {
                            // En barras y líneas, series es un arreglo de objetos con data
                            val = series[seriesIndex][dataPointIndex] ?? 0;
                            label = w.globals.labels[dataPointIndex] ?? 'Dato';
                        }
                    } catch (e) {
                        val = 0;
                        label = 'Dato';
                    }
                    
                    // Quita el marcador invisible de duplicados (\u200B)
                    const cleanLabel = String(label).replace(/[\u200B]/g, '').trim();
                    const formattedVal = formatValue(val);

                    return `
                        <div class="bg-[#0f172a]/95 backdrop-blur-xl border border-white/10 p-4 rounded-2xl shadow-2xl flex items-center gap-4">
                            <div class="w-1.5 h-10 bg-cyan-400 rounded-full shadow-[0_0_10px_rgba(34,211,238,0.5)]"></div>
                            <div>
                                <p class="text-[12px] font-black text-white/40 uppercase tracking-widest mb-1">${cleanLabel || 'Información'}</p>
                                <p class="text-xl font-black text-white tracking-tighter">${formattedVal}</p>
                            </div>
                        </div>
                    `;
                }
            }
        };

        const series = [{
            name: formatHeader(dataKeyY),
            data: seriesData
        }];

        if (chartType === 'line') {
            const lineOptions = {
                ...apexOptions,
                chart: {
                    ...apexOptions.chart,
                    type: 'line',
                    dropShadow: {
                        enabled: true,
                        top: 3,
                        left: 0,
                        blur: 4,
                        opacity: 0.3,
                        color: '#22d3ee'
                    }
                },
                fill: { type: 'solid', opacity: 1 },
                stroke: { curve: 'smooth', width: 4, colors: ['#22d3ee'] },
                markers: { 
                    size: 6, 
                    colors: ['#0f172a'], 
                    strokeColors: '#22d3ee', 
                    strokeWidth: 3,
                    hover: { size: 8 }
                },
                colors: ['#22d3ee']
            };
            return <Chart chartRef={chartRef} options={lineOptions} series={series} type="line" height="100%" />;
        }

        if (chartType === 'area') {
            return <Chart chartRef={chartRef} options={apexOptions} series={series} type="area" height="100%" />;
        }

        if (chartType === 'bar') {
            const barOptions = {
                ...apexOptions,
                plotOptions: {
                    bar: {
                        borderRadius: 8,
                        columnWidth: '40%',
                        distributed: true,
                        dataLabels: { position: 'top' }
                    }
                },
                fill: {
                    type: 'gradient',
                    gradient: {
                        shade: 'dark',
                        type: "vertical",
                        shadeIntensity: 0.5,
                        gradientToColors: ['#818cf8'],
                        inverseColors: true,
                        opacityFrom: 1,
                        opacityTo: 0.8,
                        stops: [0, 100]
                    }
                }
            };
            return <Chart chartRef={chartRef} options={barOptions} series={series} type="bar" height="100%" />;
        }

        if (chartType === 'radar') {
            const radarOptions = {
                ...apexOptions,
                chart: { ...apexOptions.chart, type: 'radar', dropShadow: { enabled: false } },
                stroke: { width: 2 },
                fill: { opacity: 0.4 },
                markers: { size: 4 },
                xaxis: { ...apexOptions.xaxis, labels: { style: { fontSize: '10px', colors: Array(categories.length).fill('#94a3b8') } } },
                yaxis: { show: false }
            };
            return <Chart chartRef={chartRef} options={radarOptions} series={series} type="radar" height="100%" />;
        }

        if (chartType === 'pie') {
            const PIE_COLORS = ['#22d3ee', '#818cf8', '#f472b6', '#fbbf24', '#34d399', '#f87171', '#a78bfa', '#2dd4bf', '#22c55e', '#e879f9'];
            const pieOptions = {
                ...apexOptions,
                chart: { 
                    ...apexOptions.chart, 
                    type: 'donut',
                    dropShadow: { enabled: false }
                },
                labels: categories,
                colors: PIE_COLORS,
                fill: { type: 'solid', opacity: 1 }, 
                stroke: { show: true, colors: ['#0f172a'], width: 2 },
                dataLabels: { 
                    enabled: true, 
                    formatter: (val) => val.toFixed(0) + "%",
                    style: { fontSize: '11px', fontWeight: 'bold', colors: ['#fff'] },
                    dropShadow: { enabled: true, top: 1, left: 1, blur: 1, opacity: 0.8 }
                },
                legend: { 
                    show: true,
                    position: 'bottom', 
                    horizontalAlign: 'center', 
                    fontSize: '10px',
                    markers: { radius: 12 },
                    itemMargin: { horizontal: 8, vertical: 4 },
                    labels: { colors: '#94a3b8' }
                },
                plotOptions: {
                    pie: {
                        donut: {
                            size: '72%',
                            labels: {
                                show: true,
                                name: { show: true, fontSize: '12px', color: '#94a3b8', offsetY: -10 },
                                value: { 
                                    show: true, 
                                    fontSize: '20px', 
                                    fontWeight: 'bold', 
                                    color: '#fff', 
                                    offsetY: 10, 
                                    formatter: (val) => formatValue(val) 
                                },
                                total: {
                                    show: true,
                                    label: 'TOTAL',
                                    color: '#94a3b8',
                                    formatter: (w) => {
                                        // Total tolerante a valores no numéricos
                                        const totals = w.globals.seriesTotals || [];
                                        const total = totals.reduce((a, b) => (parseFloat(a) || 0) + (parseFloat(b) || 0), 0);
                                        return formatValue(total);
                                    }
                                }
                            }
                        }
                    }
                }
            };
            return <Chart chartRef={chartRef} options={pieOptions} series={seriesData} type="donut" height="100%" />;
        }

        return <Chart chartRef={chartRef} options={apexOptions} series={series} type="area" height="100%" />;
    };

    const isChartCompatible = columns.length >= 2 || (type === 'bar' || type === 'line' || type === 'pie');

    // --- Tabla: búsqueda, orden y paginación sobre `data` ---
    const normalizedSearch = searchFilter.trim().toLowerCase();
    const filteredRows = normalizedSearch
        ? data.filter((row) => columns.some((c) => cleanCellText(row[c]).toLowerCase().includes(normalizedSearch)))
        : data;

    const sortedRows = sortConfig
        ? [...filteredRows].sort((a, b) => {
            const va = a[sortConfig.key];
            const vb = b[sortConfig.key];
            const bothNumeric = (typeof va === 'number' || va === '' || va == null)
                && (typeof vb === 'number' || vb === '' || vb == null);
            let cmp;
            if (bothNumeric) {
                cmp = (parseNum(va) || 0) - (parseNum(vb) || 0);
            } else {
                cmp = cleanCellText(va).localeCompare(cleanCellText(vb), 'es', { numeric: true });
            }
            return sortConfig.direction === 'asc' ? cmp : -cmp;
        })
        : filteredRows;

    // Columnas que NUNCA deben sumarse aunque su valor sea numérico: son
    // identificadores o fechas, no cantidades. Sumar «Fecha» (años tratados
    // como número) o «Número Factura» en la fila TOTAL produce cifras sin
    // sentido.
    const NO_SUMABLE_COL = /fecha|numero|número|factura|documento|c[oó]digo|\bid\b|a[ñn]o\b|c[eé]dula|\bruc\b|tel[eé]fono|\bnit\b|\bdni\b/i;

    // Total por columna al pie de la tabla (respeta el filtro de búsqueda
    // activo, igual que haría una hoja de cálculo). La primera columna es la
    // etiqueta ("Total"), no se suma. Una columna solo se suma si TODOS sus
    // valores no vacíos son numéricos Y su nombre no es un identificador/fecha
    // — de lo contrario se muestra "—".
    const totalesPorColumna = React.useMemo(() => {
        const totales = {};
        columns.forEach((c, idx) => {
            if (idx === 0 || NO_SUMABLE_COL.test(String(c))) { totales[c] = null; return; }
            let suma = 0;
            let vistos = 0;
            let numericos = 0;
            sortedRows.forEach((row) => {
                const val = Array.isArray(row) ? row[idx] : row[c];
                if (val === null || val === undefined || val === '') return;
                vistos += 1;
                if (typeof val === 'number' && isFinite(val)) {
                    suma += val;
                    numericos += 1;
                }
            });
            totales[c] = (vistos > 0 && numericos === vistos) ? suma : null;
        });
        return totales;
    }, [sortedRows, columns]);
    const hayTotales = Object.values(totalesPorColumna).some((v) => v !== null);

    const totalPages = Math.max(1, Math.ceil(sortedRows.length / PAGE_SIZE));
    const safePage = Math.min(Math.max(1, currentPage), totalPages);
    const pageRows = sortedRows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

    const handleSort = (col) => {
        setCurrentPage(1);
        setSortConfig((prev) => {
            if (prev?.key !== col) return { key: col, direction: 'asc' };
            if (prev.direction === 'asc') return { key: col, direction: 'desc' };
            return null; // tercer clic: quita el orden
        });
    };

    // Exportación a PDF: la imagen del gráfico seleccionado arriba y su tabla
    // de datos completa abajo, lista para imprimir o adjuntar a un correo.
    // jspdf y jspdf-autotable se cargan bajo demanda (solo si el usuario
    // exporta) para no engordar el paquete inicial del chat.
    const exportarGraficoPdf = async () => {
        if (pdfExporting) return;
        setPdfExporting(true);
        setPdfError('');
        try {
            const chartInstance = chartRef.current;
            if (!chartInstance || typeof chartInstance.dataURI !== 'function') {
                throw new Error('El gráfico todavía no está listo para exportar.');
            }

            // El gráfico usa background: 'transparent' en pantalla (se ve sobre el
            // fondo oscuro de la tarjeta), pero al rasterizar a PNG con dataURI()
            // lo transparente se aplana a BLANCO y el texto gris claro de los ejes
            // queda casi invisible. Antes de capturar se le da un fondo oscuro
            // sólido al propio PNG y, al terminar, se devuelve a transparente para
            // no afectar la vista en pantalla.
            let imgURI;
            try {
                await chartInstance.updateOptions(
                    { chart: { background: '#0f172a' }, foreColor: '#e2e8f0' },
                    false,
                    false,
                );
                await new Promise((r) => setTimeout(r, 120)); // espera a que ApexCharts vuelva a dibujar el SVG antes de rasterizar
                ({ imgURI } = await chartInstance.dataURI({ scale: 2 }));
            } finally {
                await chartInstance.updateOptions(
                    { chart: { background: 'transparent' }, foreColor: '#94a3b8' },
                    false,
                    false,
                );
            }

            const [{ default: JsPDF }] = await Promise.all([
                import('jspdf'),
                import('jspdf-autotable'), // efecto secundario: agrega doc.autoTable(...)
            ]);

            const doc = new JsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();
            const margin = 40;

            // El gráfico usa texto gris claro (foreColor) pensado para el fondo
            // oscuro de la aplicación; sobre una página blanca de PDF, los ejes y
            // valores serían casi invisibles. En vez de cambiar el tema de cada
            // variante de ApexCharts (barras, línea, pastel, radar), la página
            // del PDF se pinta del mismo tono oscuro: el gráfico se ve igual que
            // en pantalla, sin perder legibilidad.
            const bg = [15, 23, 42]; // #0f172a
            doc.setFillColor(...bg);
            doc.rect(0, 0, pageWidth, pageHeight, 'F');

            const titulo = result.viz_config?.title || 'Análisis de Datos';
            doc.setFontSize(16);
            doc.setTextColor(255, 255, 255);
            doc.text(titulo, margin, 42);
            doc.setFontSize(9);
            doc.setTextColor(148, 163, 184);
            doc.text(`VicMar Data AI · Generado ${new Date().toLocaleString('es-EC')}`, margin, 58);

            const imgWidth = pageWidth - margin * 2;
            const imgHeight = imgWidth * 0.42;
            doc.addImage(imgURI, 'PNG', margin, 72, imgWidth, imgHeight);

            const tableColumns = columns.map((c) => formatHeader(c));
            const tableRows = sortedRows.map((row) => columns.map((c) => formatValue(row[c], c)));
            // No se usa `didDrawPage` para repintar el fondo en cada página: ese
            // callback se dispara DESPUÉS de dibujar la página, así que el
            // rectángulo taparía el gráfico y el título. Basta con el fondo
            // pintado arriba, ANTES de dibujar nada; si la tabla ocupara una
            // segunda página, esta quedaría blanca (caso raro con estos datos).
            const autoTableOptions = {
                startY: 72 + imgHeight + 24,
                margin: { left: margin, right: margin },
                head: [tableColumns],
                body: tableRows,
                styles: { fontSize: 8, cellPadding: 4, fillColor: bg, textColor: 255, lineColor: [51, 65, 85] },
                headStyles: {
                    fillColor: [14, 122, 74], // esmeralda
                    textColor: 255,
                    fontStyle: 'bold',
                    cellPadding: { top: 6, right: 4, bottom: 6, left: 4 },
                },
                alternateRowStyles: { fillColor: [23, 33, 54] },
            };
            if (hayTotales) {
                const footCells = ['TOTAL', ...columns.slice(1).map((c) => (totalesPorColumna[c] != null ? formatValue(totalesPorColumna[c], c) : ''))];
                autoTableOptions.foot = [footCells];
                autoTableOptions.footStyles = { fillColor: [14, 122, 74], textColor: 255, fontStyle: 'bold' };
            }
            doc.autoTable(autoTableOptions);

            doc.save(`grafico-${Date.now()}.pdf`);
        } catch (err) {
            console.error('[DataVisualizer] Error exportando PDF del gráfico:', err);
            setPdfError('No se pudo generar el PDF. Intenta de nuevo.');
        } finally {
            setPdfExporting(false);
        }
    };

    return (
        <div className="w-full mt-3 space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-700">
            {/* Gráfico principal, con fondo independiente del contenido */}
            {isChartCompatible && type !== 'table' && type !== 'value' && (
                <div className="w-full relative p-3 group">
                    {/* Fondo redondeado, independiente del contenido */}
                    <div className="absolute inset-0 bg-[#0f172a]/40 rounded-[32px] border border-white/5 backdrop-blur-md shadow-2xl -z-10" />
                    
                    {/* Brillo de borde superior */}
                    <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-500/20 to-transparent pointer-events-none" />
                    
                    <div className="flex items-center justify-between mb-2 gap-3 flex-wrap">
                        <div className="flex flex-col">
                            <span className="text-[11px] font-black text-cyan-400/60 uppercase tracking-[0.5em] mb-1">Business Intelligence</span>
                            <span className="text-lg font-bold text-white tracking-tight leading-tight">{result.viz_config?.title || 'Análisis de Datos'}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            {type !== 'pie' && (
                                <div className="flex flex-col items-end px-2 py-0.5 rounded-lg bg-cyan-400/5 border border-cyan-400/10">
                                    <span className="text-[9px] font-black text-cyan-400/60 uppercase tracking-[0.25em]">Total</span>
                                    <span className="text-[15px] font-black text-white leading-none">{formatValue(totalGrafico, dataKeyY)}</span>
                                </div>
                            )}
                            <ChartTypeSwitch activeType={chartOverride || type || 'bar'} onChange={setChartOverride} />
                            <button
                                type="button"
                                onClick={exportarGraficoPdf}
                                disabled={pdfExporting}
                                title="Exportar gráfico + datos como PDF (listo para imprimir)"
                                className="h-8 flex items-center gap-1.5 px-3 rounded-lg bg-white/5 border border-white/10 text-[11px] font-bold uppercase tracking-wider text-white/60 hover:border-cyan-500/30 hover:text-cyan-300 transition-colors disabled:opacity-40"
                            >
                                <FileText size={12} />
                                {pdfExporting ? 'Generando…' : 'PDF'}
                            </button>
                        </div>
                    </div>
                    {pdfError && (
                        <p role="alert" className="-mt-2 mb-2 text-[12px] font-medium text-rose-400">{pdfError}</p>
                    )}

                    <div className="h-[240px] w-full">
                        {renderChart()}
                    </div>
                </div>
            )}

            {/* Tabla detallada, con fondo independiente del contenido */}
            <div className="relative shadow-2xl">
                {/* Fondo de la tarjeta */}
                <div className="absolute inset-0 bg-black/15 rounded-[32px] border border-white/5 backdrop-blur-sm -z-10" />
                
                <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between gap-3 flex-wrap bg-white/[0.01]">
                    <div className="flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.5)]" />
                        <span className="text-[12px] font-bold text-white/40 uppercase tracking-[0.3em]">Registros Detallados</span>
                    </div>

                    <div className="flex items-center gap-3 flex-wrap">
                        {/* Búsqueda: filtra todas las columnas a la vez */}
                        <div className="relative">
                            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" aria-hidden="true" />
                            <input
                                type="text"
                                value={searchFilter}
                                onChange={(e) => { setSearchFilter(e.target.value); setCurrentPage(1); }}
                                placeholder="Buscar en la tabla…"
                                aria-label="Buscar en los registros"
                                className="h-8 pl-8 pr-3 rounded-lg bg-black/30 border border-white/10 text-[12px] text-white placeholder:text-white/25 outline-none focus:border-cyan-500/40 w-40 sm:w-52"
                            />
                        </div>

                        {/* Exportar a Excel: datos reales (filtrados y ordenados), con
                            el mismo formato profesional de la sección de Indicadores. */}
                        <button
                            type="button"
                            onClick={async () => {
                                if (excelExporting) return;
                                setExcelExporting(true);
                                try {
                                    const filaTotales = hayTotales
                                        ? columns.map((c, i) => (i === 0 ? 'TOTAL' : (totalesPorColumna[c] ?? '')))
                                        : undefined;
                                    await exportarTablaExcel(columns, sortedRows, filaTotales);
                                } finally {
                                    setExcelExporting(false);
                                }
                            }}
                            disabled={excelExporting}
                            title={excelExporting ? 'Generando Excel…' : 'Exportar a Excel (formato profesional con tabla)'}
                            className="h-8 flex items-center gap-1.5 px-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-[11px] font-bold uppercase tracking-wider text-cyan-300 hover:bg-cyan-500/20 transition-colors disabled:opacity-50"
                        >
                            <Download size={12} />
                            {excelExporting ? 'Generando…' : 'Excel'}
                        </button>

                        <span className="text-[12px] font-black text-cyan-400/50 uppercase bg-cyan-400/10 px-2 py-0.5 rounded-lg border border-cyan-400/10 whitespace-nowrap">
                            {sortedRows.length !== data.length ? `${sortedRows.length} de ${data.length}` : `${data.length} items`}
                        </span>
                    </div>
                </div>
                <div className="overflow-x-auto max-h-[400px] overflow-y-auto custom-scrollbar">
                    <table className="w-full border-collapse text-left">
                        <thead className="sticky top-0 bg-[#0b1120] z-10">
                            <tr>
                                {columns.map(c => {
                                    const activeSort = sortConfig?.key === c ? sortConfig.direction : null;
                                    return (
                                        <th key={c} className="px-3 py-1.5 text-[11px] font-black uppercase tracking-[0.3em] text-white/20 border-b border-white/5">
                                            <button
                                                type="button"
                                                onClick={() => handleSort(c)}
                                                className="flex items-center gap-1.5 hover:text-cyan-400 transition-colors"
                                                title="Ordenar por esta columna"
                                            >
                                                {formatHeader(c)}
                                                {activeSort === 'asc' && <ChevronUp size={12} className="text-cyan-400" />}
                                                {activeSort === 'desc' && <ChevronDown size={12} className="text-cyan-400" />}
                                                {!activeSort && <ArrowUpDown size={11} className="opacity-30" />}
                                            </button>
                                        </th>
                                    );
                                })}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {pageRows.map((r, i) => (
                                <tr key={i} className="hover:bg-cyan-500/[0.03] transition-colors group">
                                    {columns.map((c, j) => (
                                        <td key={j} className="px-3 py-1 text-[13px] font-medium text-white/50 group-hover:text-cyan-400 transition-colors">
                                            {formatValue(Array.isArray(r) ? r[j] : r[c], c)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                            {pageRows.length === 0 && (
                                <tr>
                                    <td colSpan={columns.length} className="px-4 py-4 text-center text-[13px] text-white/30">
                                        Ningún registro coincide con «{searchFilter}»
                                    </td>
                                </tr>
                            )}
                        </tbody>
                        {hayTotales && (
                            <tfoot className="sticky bottom-0 bg-[#0b1120]">
                                <tr className="border-t-2 border-cyan-500/20 bg-cyan-500/[0.04]">
                                    {columns.map((c, j) => (
                                        <td key={j} className="px-3 py-1 text-[13px] font-black text-cyan-300 uppercase tracking-wider">
                                            {j === 0
                                                ? `Total${sortedRows.length !== data.length ? ` (${sortedRows.length} filtrados)` : ''}`
                                                : (totalesPorColumna[c] !== null ? formatValue(totalesPorColumna[c], c) : '—')}
                                        </td>
                                    ))}
                                </tr>
                            </tfoot>
                        )}
                    </table>
                </div>

                {/* Paginación: solo se muestra si hay más de una página */}
                {totalPages > 1 && (
                    <div className="px-4 py-2 border-t border-white/5 flex items-center justify-between gap-3">
                        <span className="text-[11px] font-bold text-white/30 uppercase tracking-wider">
                            Página {safePage} de {totalPages}
                        </span>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                                disabled={safePage <= 1}
                                aria-label="Página anterior"
                                className="h-8 w-8 flex items-center justify-center rounded-lg bg-white/5 border border-white/10 text-white/50 hover:text-white hover:border-cyan-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            >
                                <ChevronLeft size={14} />
                            </button>
                            <button
                                type="button"
                                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                                disabled={safePage >= totalPages}
                                aria-label="Página siguiente"
                                className="h-8 w-8 flex items-center justify-center rounded-lg bg-white/5 border border-white/10 text-white/50 hover:text-white hover:border-cyan-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            >
                                <ChevronRight size={14} />
                            </button>
                        </div>
                    </div>
                )}

                {/* Indicador de fin de tabla */}
                <div className="h-3 bg-gradient-to-t from-black/20 to-transparent" />
            </div>
        </div>
    );
};



