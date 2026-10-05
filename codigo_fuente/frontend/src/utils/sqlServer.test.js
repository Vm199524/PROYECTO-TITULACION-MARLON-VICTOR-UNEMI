/**
 * @file Pruebas de `normalizeSqlServerHost`. Verifican que los alias locales
 * (`.`, `(local)`) se conviertan en `localhost` conservando la instancia o el
 * puerto, y que se quiten las comillas externas y los espacios alrededor de
 * los separadores `\` y `,`, para que el host escrito por el usuario llegue
 * limpio a la conexión con SQL Server.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import { describe, expect, it } from 'vitest';

import { normalizeSqlServerHost } from './sqlServer';

describe('normalizeSqlServerHost', () => {
    it('normalizes local aliases to localhost while preserving instance/port', () => {
        expect(normalizeSqlServerHost('localhost')).toBe('localhost');
        expect(normalizeSqlServerHost('.')).toBe('localhost');
        expect(normalizeSqlServerHost('.\\SQLEXPRESS')).toBe('localhost\\SQLEXPRESS');
        expect(normalizeSqlServerHost('(local)\\SQLEXPRESS')).toBe('localhost\\SQLEXPRESS');
    });

    it('removes outer quotes and spaces around instance or port separators', () => {
        expect(normalizeSqlServerHost(' " localhost , 1433 " ')).toBe('localhost,1433');
        expect(normalizeSqlServerHost(" ' SERVIDOR \\ sql2022 ' ")).toBe('SERVIDOR\\sql2022');
        expect(normalizeSqlServerHost('203.0.113.10 , 9086 \\ sql2022')).toBe('203.0.113.10,9086\\sql2022');
    });
});
