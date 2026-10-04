import { describe, expect, it } from 'vitest';
import { interpretarComandoVoz, buscarEmpresa, normalizar } from '../utils/comandosVoz';

// Catálogo con los casos reales del servidor, incluidos los dos que se prestan
// a confusión: ENIG "ENIGMA" y ENPR "ENIGMA PARA PRUEBAS".
const EMPRESAS = [
    { database: 'MONT', business_name: 'UNIDAD EDUCATIVA MONTESSORI' },
    { database: 'GYMJ', business_name: 'AGRINAG S.A.S.' },
    { database: 'ALIM', business_name: 'DELPYG S.A.' },
    { database: 'ENIG', business_name: 'ENIGMA' },
    { database: 'ENPR', business_name: 'ENIGMA PARA PRUEBAS' },
    { database: 'MANA', business_name: 'MANAGESOL GESTION S.A.S.' },
];

describe('interpretarComandoVoz', () => {
    describe('cambio de empresa', () => {
        it.each([
            'conéctate a Montessori',
            'conectate a la empresa Montessori',
            'cambia a Montessori',
            'cámbiate a la base de datos Montessori',
            'abre la empresa Montessori',
            'selecciona la empresa Montessori',
        ])('reconoce «%s»', (frase) => {
            const orden = interpretarComandoVoz(frase, EMPRESAS);
            expect(orden?.tipo).toBe('cambiar_empresa');
            expect(orden.empresa.database).toBe('MONT');
        });

        it('acepta el código de base además del nombre comercial', () => {
            const orden = interpretarComandoVoz('conéctate a GYMJ', EMPRESAS);
            expect(orden?.empresa?.database).toBe('GYMJ');
        });

        it('prefiere la coincidencia más específica', () => {
            // "enigma para pruebas" contiene "enigma": debe ganar ENPR, no ENIG.
            const orden = interpretarComandoVoz('conéctate a enigma para pruebas', EMPRESAS);
            expect(orden?.empresa?.database).toBe('ENPR');
        });

        it('avisa cuando entiende la orden pero no la empresa', () => {
            const orden = interpretarComandoVoz('conéctate a Pepito Perez', EMPRESAS);
            expect(orden?.tipo).toBe('empresa_no_encontrada');
        });
    });

    describe('no captura preguntas legítimas', () => {
        it.each([
            'cuál es el total de empleados',
            'cuánto vendimos este año',
            'muéstrame los 10 productos más vendidos',
            'total de nómina del último mes',
            'cuántos proveedores tenemos registrados',
            'dame las ventas por mes',
        ])('deja pasar «%s» al motor de consultas', (pregunta) => {
            // Es preferible mandar algo de más al motor que secuestrar una
            // pregunta real y dejar al usuario sin respuesta.
            expect(interpretarComandoVoz(pregunta, EMPRESAS)).toBeNull();
        });
    });

    describe('salir', () => {
        it.each(['salir', 'cierra', 'adiós', 'chao'])('reconoce «%s»', (frase) => {
            expect(interpretarComandoVoz(frase, EMPRESAS)?.tipo).toBe('salir');
        });
    });

    it('ignora texto vacío o ruido', () => {
        expect(interpretarComandoVoz('', EMPRESAS)).toBeNull();
        expect(interpretarComandoVoz('   ', EMPRESAS)).toBeNull();
    });
});

describe('buscarEmpresa', () => {
    it('es insensible a acentos y mayúsculas', () => {
        expect(buscarEmpresa('MONTESSORI', EMPRESAS)?.database).toBe('MONT');
        expect(buscarEmpresa('montessori', EMPRESAS)?.database).toBe('MONT');
    });

    it('encuentra por fragmento del nombre comercial', () => {
        expect(buscarEmpresa('unidad educativa montessori', EMPRESAS)?.database).toBe('MONT');
        expect(buscarEmpresa('agrinag', EMPRESAS)?.database).toBe('GYMJ');
    });

    it('no inventa coincidencias con menciones muy cortas', () => {
        expect(buscarEmpresa('a', EMPRESAS)).toBeNull();
        expect(buscarEmpresa('', EMPRESAS)).toBeNull();
    });
});

describe('normalizar', () => {
    it('quita acentos y signos', () => {
        expect(normalizar('¿Conéctate a Montessori?')).toBe('conectate a montessori');
    });
});
