import { describe, it, expect } from 'vitest';
import { formatValue } from '../utils/formatters';

// Regresión (29/08/2026): una columna "Fecha" cuyo
// valor era solo el año ("2026", sin día/mes) no calzaba con el patrón de
// fecha reconocido y caía en el formateador numérico genérico, mostrándose
// como "2.026" — con separador de miles, como si fuera dinero. Una columna
// de fecha nunca debe pasar por ese formateador.
describe('formatValue — columnas de fecha', () => {
    it('no le pone separador de miles a un año suelto en una columna Fecha', () => {
        expect(formatValue(2026, 'Fecha')).toBe('2026');
        expect(formatValue('2026', 'Fecha')).toBe('2026');
    });

    it('sigue formateando fechas completas YYYY-MM-DD como antes', () => {
        expect(formatValue('2026-03-15', 'Fecha')).toBe('2026-Marzo-15');
    });

    it('una columna que NO es de fecha sigue formateando numeros con separador de miles', () => {
        expect(formatValue(2026, 'Total')).toBe('2.026');
    });
});
