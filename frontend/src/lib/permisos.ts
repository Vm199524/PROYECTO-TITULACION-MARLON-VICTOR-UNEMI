/**
 * src/lib/permisos.ts — capacidades por rol (espejo de backend/core/seguridad.py).
 *
 * Decide qué se MUESTRA. La autorización real la aplica siempre el backend en cada
 * petición; esta matriz solo evita ofrecer opciones que fallarían.
 *
 * Requisitos: RF-01 (acceso por rol).
 */

export type Capacidad =
  | 'ver_panel'
  | 'ver_alumnos'
  | 'ver_ficha'
  | 'simular'
  | 'ver_carreras'
  | 'ver_referentes'
  | 'ver_modelo'
  | 'consultar'
  | 'exportar'
  | 'ver_seguimiento'
  | 'registrar_seguimiento'
  | 'administrar_usuarios'
  | 'ver_auditoria'
  | 'ver_estado'
  | 'ver_sql'

export function puede(capacidades: string[] | undefined, capacidad: Capacidad): boolean {
  return !!capacidades?.includes(capacidad)
}
