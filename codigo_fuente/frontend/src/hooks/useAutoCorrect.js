/**
 * @file Hook de autocorrección de la pregunta. Reemplaza palabras mal escritas
 * según el diccionario `FRONTEND_CORRECTIONS` de appConfig.js antes de enviar
 * la consulta al backend.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import { FRONTEND_CORRECTIONS } from '../constants/appConfig';

/**
 * Expone la función de autocorrección del texto escrito por el usuario.
 * @returns {{correct: function(string): {text: string, wasCorrected: boolean}}}
 *   `correct` devuelve el texto corregido (palabras completas, sin distinguir
 *   mayúsculas) e indica si hubo algún reemplazo.
 */
export function useAutoCorrect() {
    const correct = (text) => {
        let result = text;
        let wasCorrected = false;
        Object.entries(FRONTEND_CORRECTIONS).forEach(([wrong, right]) => {
            const regex = new RegExp(`\\b${wrong}\\b`, 'gi');
            if (regex.test(result)) {
                result = result.replace(regex, right);
                wasCorrected = true;
            }
        });
        return { text: result, wasCorrected };
    };
    return { correct };
}

