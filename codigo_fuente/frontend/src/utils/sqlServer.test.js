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
