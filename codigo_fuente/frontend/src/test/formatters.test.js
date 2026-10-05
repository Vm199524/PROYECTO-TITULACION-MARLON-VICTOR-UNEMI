/**
 * @file Pruebas de `formatValue` con columnas de fecha. Verifican que un año
 * suelto («2026») en una columna «Fecha» no pase por el formateador numérico
 * (que lo mostraría como «2.026», con separador de miles), que las fechas
 * completas AAAA-MM-DD se sigan formateando y que las columnas numéricas
 * conserven el separador de miles.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import { describe, it, expect } from 'vitest';
import { formatValue } from '../utils/formatters';

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
