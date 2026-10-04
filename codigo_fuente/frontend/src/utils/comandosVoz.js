/**
 * utils/comandosVoz.js — Interpreta órdenes habladas antes de tratarlas como preguntas.
 *
 * Sin esto, decir "conéctate a Montessori" viajaba al motor SQL como si fuera
 * una consulta de negocio: no hay ninguna tabla que responda a eso, así que la
 * IA improvisaba o fallaba. Las órdenes de navegación se resuelven aquí, en el
 * navegador, sin gastar una llamada al servidor ni al modelo.
 */

/** Quita acentos y signos para comparar lo dicho con lo escrito en el catálogo. */
export function normalizar(texto) {
    return String(texto || '')
        .normalize('NFD')
        .replace(/[̀-ͯ]/g, '')
        .replace(/[¿?¡!.,;:]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase();
}

// Formas naturales de pedir un cambio de empresa. Se aceptan varias porque
// nadie habla igual: unos dicen "conéctate a", otros "ábreme", otros "cambia".
const PATRONES_CAMBIO_EMPRESA = [
    /(?:conectate|conectarte|conecta|conectame)\s+(?:a|con|en)\s+(?:la\s+)?(?:empresa\s+|base\s+(?:de\s+datos\s+)?)?(.+)/,
    /(?:cambia|cambiate|cambiar|pasa|pasate|muevete)\s+(?:a|hacia|para)\s+(?:la\s+)?(?:empresa\s+|base\s+(?:de\s+datos\s+)?)?(.+)/,
    /(?:abre|abreme|ábreme|entra|ingresa|ve|vete|anda)\s+(?:a|en|al|la)?\s*(?:empresa\s+|base\s+(?:de\s+datos\s+)?)(.+)/,
    /(?:seleccciona|selecciona|elige|escoge)\s+(?:la\s+)?(?:empresa\s+|base\s+(?:de\s+datos\s+)?)?(.+)/,
];

const PATRONES_SALIR = [
    /^(?:sal|salir|cierra|cerrar|termina|terminar|adios|adios vicmar|chao|listo gracias)$/,
];

/**
 * Busca la empresa mencionada dentro del catálogo disponible.
 *
 * El reconocimiento de voz devuelve el nombre comercial hablado
 * ("montessori"), no el código de base ("MONT"), así que se compara contra
 * ambos. Se prefiere la coincidencia más larga: si alguien dice "enigma para
 * pruebas" debe ganar ENPR y no ENIG, que también contiene "enigma".
 */
export function buscarEmpresa(mencion, empresas = []) {
    const objetivo = normalizar(mencion);
    if (!objetivo || objetivo.length < 3) return null;

    let mejor = null;
    let mejorLargo = 0;

    for (const empresa of empresas) {
        const codigo = normalizar(empresa.database || empresa.company_code || '');
        const nombre = normalizar(empresa.business_name || '');

        for (const candidato of [nombre, codigo]) {
            if (!candidato || candidato.length < 2) continue;
            // Coincide si lo dicho contiene al candidato, o al revés: cubre
            // tanto "conéctate a montessori" (nombre corto dentro de frase)
            // como "conéctate a la unidad educativa montessori" (frase larga).
            const coincide = objetivo.includes(candidato) || candidato.includes(objetivo);
            if (coincide && candidato.length > mejorLargo) {
                mejor = empresa;
                mejorLargo = candidato.length;
            }
        }
    }

    return mejor;
}

/**
 * Devuelve la orden reconocida, o null si el texto es una pregunta normal.
 *
 * Ante la duda NO se interpreta como orden: es preferible mandar algo al motor
 * de consultas y que responda, que capturar por error una pregunta legítima y
 * dejar al usuario sin respuesta.
 */
export function interpretarComandoVoz(texto, empresas = []) {
    const limpio = normalizar(texto);
    if (!limpio) return null;

    if (PATRONES_SALIR.some(p => p.test(limpio))) {
        return { tipo: 'salir' };
    }

    for (const patron of PATRONES_CAMBIO_EMPRESA) {
        const coincidencia = limpio.match(patron);
        if (!coincidencia) continue;

        const mencion = coincidencia[1];
        const empresa = buscarEmpresa(mencion, empresas);

        if (empresa) {
            return { tipo: 'cambiar_empresa', empresa };
        }
        // Se entendió la intención pero no la empresa: avisar es más útil que
        // mandar "conéctate a X" al motor SQL, que no sabría qué hacer con eso.
        return { tipo: 'empresa_no_encontrada', mencion: mencion.trim() };
    }

    return null;
}
