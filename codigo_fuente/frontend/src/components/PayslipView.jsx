/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-UI-VIZ-02]
 * ============================================================================
 * ARCHIVO: PayslipView.jsx
 * MÓDULO: UI / Specialized Rendering
 * 
 * 🎯 PROPÓSITO GERENCIAL:
 * Organizador de Nómina. Cuando la IA detecta que la tabla devuelta 
 * contiene datos de roles de pago, este componente toma la tabla plana
 * y agrupa todos los rubros (sueldo, horas extras, iess) por Empleado.
 * 
 * 📍 PUNTO DE INTERFAZ:
 * Renderizado condicionalmente por `DataVisualizer.jsx` cuando el tipo 
 * de datos se identifica como 'payslips'.
 * 
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Algoritmo de "fuzzy matching" para encontrar columnas clave (Cédula, Nombres).
 * - Agrupación de filas de la base de datos en objetos ordenados por trabajador.
 * - Restricción de renderizado (muestra máx 3 fichas para no saturar memoria).
 * ============================================================================
 */

import React from 'react';
import { ProfessionalPaySlip } from './ProfessionalPaySlip';

const normalizeKey = (value) =>
    String(value ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]/gi, '')
        .toLowerCase();

const findColumn = (columns, aliases) => {
    const normalizedCols = (columns || []).map((col) => normalizeKey(col));
    for (const alias of aliases) {
        const nAlias = normalizeKey(alias);
        const exactIdx = normalizedCols.findIndex((col) => col === nAlias);
        if (exactIdx !== -1) return exactIdx;
        const partialIdx = normalizedCols.findIndex((col) => col.includes(nAlias));
        if (partialIdx !== -1) return partialIdx;
    }
    return -1;
};

export const PayslipView = ({ data, columns, dbName, payslipMeta = [] }) => {
    if (!Array.isArray(data) || data.length === 0) return null;

    const cedulaIdx = findColumn(columns, ['cedula', 'identificacion', 'cedulaid', 'id']);
    const nombresIdx = findColumn(columns, ['nombres', 'nombre', 'empleado', 'trabajador']);
    const mesIdx = findColumn(columns, ['mes', 'periodomes']);
    const anioIdx = findColumn(columns, ['anio', 'ano', 'periodoanio']);

    const grouped = new Map();
    data.forEach((row) => {
        const id = (cedulaIdx >= 0 ? row[cedulaIdx] : null) || (nombresIdx >= 0 ? row[nombresIdx] : 'desconocido');
        const mes = mesIdx >= 0 ? row[mesIdx] : '';
        const anio = anioIdx >= 0 ? row[anioIdx] : '';
        const key = `${id}-${mes}-${anio}`;
        if (!grouped.has(key)) grouped.set(key, { main: row, all: [] });
        grouped.get(key).all.push(row);
    });

    const employees = Array.from(grouped.values());

    return (
        <div className="w-full flex flex-col items-center gap-8 mt-6">
            {employees.slice(0, 3).map((emp, idx) => {
                const rowCedula = cedulaIdx >= 0 ? String(emp.main?.[cedulaIdx] ?? '').trim() : '';
                const rowMes = mesIdx >= 0 ? String(emp.main?.[mesIdx] ?? '').trim() : '';
                const rowAnio = anioIdx >= 0 ? String(emp.main?.[anioIdx] ?? '').trim() : '';
                const meta = payslipMeta.find((item) =>
                    String(item?.cedula ?? '').trim() === rowCedula &&
                    String(item?.periodo_mes ?? '').trim() === rowMes &&
                    String(item?.periodo_anio ?? '').trim() === rowAnio
                ) || null;

                return (
                    <ProfessionalPaySlip
                        key={idx}
                        employee={emp.main}
                        allRows={emp.all}
                        columns={columns}
                        dbName={dbName}
                        meta={meta}
                    />
                );
            })}

            {employees.length > 3 && (
                <div className="text-white/70 text-[12px] font-bold uppercase tracking-[0.2em] bg-cyan-500/15 px-6 py-2.5 rounded-full border border-cyan-400/30">
                    Se muestran 3 fichas. {employees.length - 3} empleados adicionales ocultos.
                </div>
            )}
        </div>
    );
};
