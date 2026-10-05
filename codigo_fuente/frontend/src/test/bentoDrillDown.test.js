/**
 * @file Pruebas de `buildCardDrillQuestion` (BentoDashboard). Verifican que
 * las tarjetas «Este Mes», «Acumulado <año>», «Clientes», «Productos» y
 * «Balance Comercial» generen una pregunta concreta para el detalle. El
 * fallback genérico («Muéstrame el detalle detrás de: …») es ambiguo y hace
 * que el modelo tarde demasiado o no responda.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import { describe, it, expect } from 'vitest';
import { buildCardDrillQuestion } from '../components/views/BentoDashboard';

describe('buildCardDrillQuestion — tarjetas del Balance Comercial', () => {
    it('genera una pregunta concreta para "Este Mes"', () => {
        expect(buildCardDrillQuestion({ title: 'Este Mes' })).toBe('Muéstrame el detalle de ventas de este mes');
    });

    it('genera una pregunta concreta para "Acumulado <año>"', () => {
        expect(buildCardDrillQuestion({ title: 'Acumulado 2026' })).toBe('Muéstrame el detalle de ventas acumuladas del año actual');
    });

    it('genera una pregunta concreta para "Clientes"', () => {
        expect(buildCardDrillQuestion({ title: 'Clientes' })).toBe('Muéstrame el listado de clientes con facturas registradas');
    });

    it('genera una pregunta concreta para "Productos"', () => {
        expect(buildCardDrillQuestion({ title: 'Productos' })).toBe('Muéstrame el listado de productos facturados');
    });

    it('mantiene el comportamiento ya existente para Balance Comercial', () => {
        expect(buildCardDrillQuestion({ title: 'Balance Comercial' }))
            .toBe('Muéstrame el detalle de ventas y compras del período más reciente');
    });
});
