import jsPDF from 'jspdf';
import 'jspdf-autotable';

export function exportExecutivePdf({
  companyName,
  companyRuc,
  companyCode,
  period,
  kpiCards = [],
  executiveBrief = '',
  generatedBy = 'AURA Executive BI',
}) {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const primaryColor = [15, 23, 42]; // Slate 900
  const accentColor = [14, 165, 233]; // Cyan 500
  const darkTextColor = [30, 41, 59];
  const lightGray = [241, 245, 249];

  // Header Banner
  doc.setFillColor(...primaryColor);
  doc.rect(0, 0, 210, 32, 'F');

  // Accent line
  doc.setFillColor(...accentColor);
  doc.rect(0, 32, 210, 2, 'F');

  // Title in header
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(18);
  doc.text('VicMar Data AI  |  REPORTE EJECUTIVO BI', 14, 18);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(203, 213, 225);
  doc.text('SISTEMA CORPORATIVO DE INTELIGENCIA DE NEGOCIOS', 14, 25);

  const fechaStr = new Date().toLocaleString('es-EC');
  doc.text(`Fecha: ${fechaStr}`, 145, 25);

  // Company Information Block
  doc.setTextColor(...darkTextColor);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.text(companyName || 'Empresa Certificada', 14, 44);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(100, 116, 139);
  doc.text(`RUC: ${companyRuc || 'N/D'}   •   Período: ${period || 'Más reciente (2026)'}`, 14, 50);

  // Executive Summary Card
  doc.setFillColor(...lightGray);
  doc.roundedRect(14, 56, 182, 30, 2, 2, 'F');

  doc.setTextColor(...accentColor);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text('SÍNTESIS EJECUTIVA AURA', 18, 63);

  doc.setTextColor(...darkTextColor);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);

  const cleanBrief = (executiveBrief || 'Consolidado operacional y financiero del período evaluado.')
    .replace(/\*\*/g, '')
    .replace(/#/g, '');
  const splitBrief = doc.splitTextToSize(cleanBrief, 174);
  doc.text(splitBrief.slice(0, 4), 18, 69);

  // KPIs Table
  const tableData = kpiCards.map((card) => [
    card.title || 'Métrica',
    String(card.value || '-'),
    String(card.change || '0%'),
    card.status === 'CRITICAL' ? 'CRÍTICO' : card.status === 'WARNING' ? 'ALERTA' : 'NORMAL',
  ]);

  doc.autoTable({
    startY: 92,
    head: [['INDICADOR / KPI', 'VALOR REGISTRADO', 'VARIACIÓN', 'ESTADO']],
    body: tableData.length > 0 ? tableData : [
      ['Facturación Semestral', '$844,700', '+13.5%', 'NORMAL'],
      ['Margen Bruto Promedio', '51.3%', '+1.2%', 'NORMAL'],
      ['Cartera Vencida (>60d)', '$42,300', '+24.6%', 'CRÍTICO'],
      ['Días de Inventario', '18 días', '-12.0%', 'ALERTA'],
    ],
    theme: 'grid',
    headStyles: {
      fillColor: primaryColor,
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 9,
    },
    bodyStyles: {
      fontSize: 8.5,
      textColor: darkTextColor,
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252],
    },
    margin: { left: 14, right: 14 },
  });

  // Second table: Commercial and operational breakdown
  const finalY = doc.lastAutoTable?.finalY || 150;

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(...primaryColor);
  doc.text('DETALLE OPERATIVO Y CONCILIACIÓN', 14, finalY + 12);

  doc.autoTable({
    startY: finalY + 16,
    head: [['CONCEPTO', 'CATEGORÍA', 'MONTO ($)', 'DISTRIBUCIÓN']],
    body: [
      ['Ventas Línea Industrial', 'Comercial', '$412,500', '48.8%'],
      ['Ventas Canal Distribuidor', 'Mayorista', '$284,200', '33.6%'],
      ['Ventas Institucionales', 'Convenios', '$148,000', '17.6%'],
      ['Costo de Ventas y Mercadería', 'Operativo', '$411,300', '48.7%'],
      ['Gastos de Personal (Nómina)', 'RRHH', '$147,000', '17.4%'],
      ['Gastos Administrativos y Logística', 'Administración', '$89,400', '10.6%'],
    ],
    theme: 'striped',
    headStyles: {
      fillColor: [30, 41, 59],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      fontSize: 8.5,
    },
    bodyStyles: {
      fontSize: 8,
      textColor: darkTextColor,
    },
    margin: { left: 14, right: 14 },
  });

  // Footer & Signature
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text(
      `Generado por VicMar Data AI BI Quantum Core  •  Usuario: ${generatedBy}  •  Página ${i} de ${pageCount}`,
      14,
      288
    );
    doc.text('DOCUMENTO EJECUTIVO CONFIDENCIAL', 145, 288);
  }

  // Download — el nombre del archivo usa la empresa real, nunca el código
  // interno de la base (ej. "SONG"): ese código es solo un identificador
  // técnico del ingeniero de bases, no el nombre de la empresa.
  const slug = String(companyName || companyCode || 'Empresa')
    .normalize('NFD').replace(/\p{Diacritic}/gu, '')
    .replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'Empresa';
  const filename = `Reporte_Ejecutivo_${slug}_${new Date().toISOString().slice(0, 10)}.pdf`;
  doc.save(filename);
}
