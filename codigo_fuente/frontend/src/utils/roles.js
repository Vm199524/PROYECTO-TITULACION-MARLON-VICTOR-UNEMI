/**
 * @file Etiquetas en español de los roles del sistema. El código técnico del
 * rol (el que viaja en el JWT y se guarda en security_config.json: GUEST,
 * ADMINISTRADOR, CONTABILIDAD, RRHH, LOGISTICA, ACADEMICO) no cambia, porque
 * hacerlo afectaría el token, el almacén de usuarios y las comparaciones del
 * backend. Este archivo solo traduce lo que ve el usuario (p. ej. GUEST se
 * muestra como «Invitado») y centraliza esa traducción para que todos los
 * componentes que muestran un rol sean coherentes.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

/** Etiqueta visible de cada código de rol. */
export const ROLE_LABELS = {
    ADMINISTRADOR: 'Administrador',
    CONTABILIDAD: 'Contabilidad',
    RRHH: 'RRHH',
    LOGISTICA: 'Logística',
    ACADEMICO: 'Académico',
    GUEST: 'Invitado',
};

/**
 * Devuelve la etiqueta en español de un código de rol. Si no se reconoce, se
 * muestra tal cual.
 * @param {string|null|undefined} role Código del rol (insensible a mayúsculas).
 * @returns {string} Etiqueta visible, el valor original o cadena vacía.
 */
export function roleLabel(role) {
    const key = String(role || '').trim().toUpperCase();
    return ROLE_LABELS[key] || role || '';
}
