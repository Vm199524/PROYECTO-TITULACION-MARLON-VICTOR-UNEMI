/**
 * roles.js — Etiquetas en español para los roles del sistema.
 *
 * El código técnico del rol (el que viaja en el JWT y vive en
 * security_config.json) se queda igual: "GUEST", "ADMINISTRADOR",
 * "CONTABILIDAD", "RRHH", "LOGISTICA". Cambiar esas claves tocaría el token,
 * el almacén de usuarios y las comparaciones del backend — mucho más riesgo
 * del que vale la pena solo para una etiqueta visual.
 *
 * Lo que sí cambia es lo que VE el usuario. El caso real (30/08/2026): un
 * usuario con rol GUEST veía literalmente la palabra "GUEST" en inglés bajo
 * su nombre, en el header — se pidió que se mostrara "Invitado" en su lugar.
 * Este archivo centraliza esa traducción para no repetirla (con el riesgo de
 * que queden inconsistentes) en cada componente que muestre un rol.
 */

export const ROLE_LABELS = {
    ADMINISTRADOR: 'Administrador',
    CONTABILIDAD: 'Contabilidad',
    RRHH: 'RRHH',
    LOGISTICA: 'Logística',
    ACADEMICO: 'Académico',
    GUEST: 'Invitado',
};

/** Etiqueta en español para un código de rol. Si no se reconoce, se muestra tal cual. */
export function roleLabel(role) {
    const key = String(role || '').trim().toUpperCase();
    return ROLE_LABELS[key] || role || '';
}
