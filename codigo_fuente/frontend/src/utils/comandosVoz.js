/**
 * @file Intérprete de comandos de voz. Reconoce órdenes habladas (cambiar de
 * empresa, salir) antes de tratarlas como preguntas de datos. Una orden como
 * «conéctate a Montessori» no tiene tabla que la responda en el motor SQL, así
 * que se resuelve aquí, en el navegador, sin llamar al servidor ni al modelo.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

/**
 * Quita acentos y signos para comparar lo dicho con lo escrito en el catálogo.
 * @param {string} texto Texto reconocido o nombre del catálogo.
 * @returns {string} Texto en minúsculas, sin tildes, signos ni espacios repetidos.
 */
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
 * @param {string} mencion Nombre o código de empresa extraído de la frase.
 * @param {Array<{database?: string, company_code?: string, business_name?: string}>} [empresas=[]]
 *   Catálogo de empresas disponibles.
 * @returns {object|null} La empresa con la coincidencia más larga, o null si
 *   la mención tiene menos de 3 caracteres o no coincide con ninguna.
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
 * @param {string} texto Frase reconocida por el dictado.
 * @param {Array<object>} [empresas=[]] Catálogo de empresas disponibles.
 * @returns {{tipo: string, empresa?: object, mencion?: string}|null} La orden
 *   reconocida (`salir`, `cambiar_empresa` o `empresa_no_encontrada`), o null
 *   si el texto debe ir al motor de consultas.
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
