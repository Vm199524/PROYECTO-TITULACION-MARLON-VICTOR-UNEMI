/**
 * src/componentes/layout/navegacion.ts — mapa de navegación agrupado por proceso
 * académico (no por tabla): Inicio, Alerta temprana, Análisis institucional,
 * Confianza en el modelo, Reportes y Administración. Lo leen la barra lateral y las
 * migas de pan; una pantalla nueva se registra solo aquí, con la capacidad que exige.
 */
import type { Capacidad } from '../../lib/permisos'
import {
  IconoAuditoria,
  IconoCarreras,
  IconoConsulta,
  IconoEstado,
  IconoEstudiantes,
  IconoModelo,
  IconoPanel,
  IconoReferentes,
  IconoReportes,
  IconoSeguimiento,
  IconoUsuarios,
  type Icono,
} from '../iconos'

export interface ItemNav {
  href: string
  etiqueta: string
  icono: Icono
  exacto?: boolean
  requiere: Capacidad
}

export interface GrupoNav {
  titulo: string
  items: ItemNav[]
}

export const NAVEGACION: GrupoNav[] = [
  { titulo: 'Inicio', items: [{ href: '/panel', etiqueta: 'Panel ejecutivo', icono: IconoPanel, requiere: 'ver_panel' }] },
  {
    titulo: 'Alerta temprana',
    items: [
      { href: '/estudiantes', etiqueta: 'Estudiantes en riesgo', icono: IconoEstudiantes, requiere: 'ver_alumnos' },
      { href: '/seguimiento', etiqueta: 'Seguimiento', icono: IconoSeguimiento, requiere: 'ver_seguimiento' },
    ],
  },
  {
    titulo: 'Análisis institucional',
    items: [
      { href: '/consulta', etiqueta: 'Consulta conversacional', icono: IconoConsulta, requiere: 'consultar' },
      { href: '/carreras', etiqueta: 'Carreras', icono: IconoCarreras, requiere: 'ver_carreras' },
      { href: '/referentes', etiqueta: 'Referentes externos', icono: IconoReferentes, requiere: 'ver_referentes' },
    ],
  },
  { titulo: 'Confianza', items: [{ href: '/modelo', etiqueta: 'Calidad del modelo', icono: IconoModelo, requiere: 'ver_modelo' }] },
  { titulo: 'Reportes', items: [{ href: '/reportes', etiqueta: 'Reportes ejecutivos', icono: IconoReportes, requiere: 'exportar' }] },
  {
    titulo: 'Administración',
    items: [
      { href: '/admin/usuarios', etiqueta: 'Usuarios y roles', icono: IconoUsuarios, requiere: 'administrar_usuarios' },
      { href: '/admin/auditoria', etiqueta: 'Auditoría', icono: IconoAuditoria, requiere: 'ver_auditoria' },
      { href: '/admin/estado', etiqueta: 'Estado del sistema', icono: IconoEstado, requiere: 'ver_estado' },
    ],
  },
]

export function esActivo(item: ItemNav, ruta: string): boolean {
  return ruta === item.href || (!item.exacto && ruta.startsWith(`${item.href}/`))
}

/** Grupo e ítem de la ruta actual, para las migas de pan. */
export function ubicar(ruta: string): { grupo?: GrupoNav; item?: ItemNav } {
  let mejor: { grupo?: GrupoNav; item?: ItemNav } = {}
  for (const grupo of NAVEGACION) {
    for (const item of grupo.items) {
      if ((ruta === item.href || ruta.startsWith(`${item.href}/`)) && (!mejor.item || item.href.length > mejor.item.href.length)) {
        mejor = { grupo, item }
      }
    }
  }
  return mejor
}

/** Primera pantalla que el rol puede ver (destino tras ingresar). */
export function inicioPara(puede: (c: Capacidad) => boolean): string {
  for (const g of NAVEGACION) for (const i of g.items) if (puede(i.requiere)) return i.href
  return '/perfil'
}
