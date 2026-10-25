/**
 * src/lib/permisos.ts — capacidades por rol (espejo de backend/core/seguridad.py).
 *
 * Decide qué se MUESTRA. La autorización real la aplica siempre el backend en cada
 * petición; esta matriz solo evita ofrecer opciones que fallarían.
 */
import type { Rol } from './tipos'

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

export const DESCRIPCION_ROL: Record<Rol, string> = {
  AUTORIDAD: 'Autoridad académica',
  BIENESTAR: 'Bienestar estudiantil',
  ADMIN_TI: 'Administración de TI',
}

export function puede(capacidades: string[] | undefined, capacidad: Capacidad): boolean {
  return !!capacidades?.includes(capacidad)
}
