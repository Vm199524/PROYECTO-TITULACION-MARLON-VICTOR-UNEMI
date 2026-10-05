/**
 * @file Vista de roles de pago. Cuando el resultado de una consulta corresponde a
 * nómina, agrupa las filas planas por empleado y periodo (cédula o nombres, mes y
 * año) y dibuja una ficha ProfessionalPaySlip por grupo, con un máximo de tres
 * para no saturar la vista. Lo usan ChatMessage y DataVisualizer.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React from 'react';
import { ProfessionalPaySlip } from './ProfessionalPaySlip';

// Normaliza un nombre de columna: sin tildes, sin signos y en minúsculas.
const normalizeKey = (value) =>
    String(value ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9]/gi, '')
        .toLowerCase();

// Devuelve el índice de la primera columna que coincide con algún alias, primero
// por igualdad exacta y luego por inclusión; -1 si ninguna coincide.
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

/**
 * Agrupa las filas de nómina por empleado y periodo y muestra hasta tres fichas.
 *
 * @param {object} props
 * @param {Array<Array>} props.data - Filas del resultado, como arreglos de valores.
 * @param {string[]} props.columns - Nombres de las columnas, en el mismo orden.
 * @param {string} [props.dbName] - Nombre de la base, que se muestra en cada ficha.
 * @param {object[]} [props.payslipMeta=[]] - Metadatos por cédula, mes y año que
 *   acompañan a cada ficha.
 * @returns {JSX.Element|null} Las fichas, o null si no hay filas.
 */
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
