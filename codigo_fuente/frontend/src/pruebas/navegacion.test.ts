/** El menú se arma por capacidades: cada rol ve solo lo que puede usar. */
import { NAVEGACION, inicioPara, ubicar } from '../componentes/layout/navegacion'
import { puede, type Capacidad } from '../lib/permisos'

const AUTORIDAD = ['ver_panel', 'ver_alumnos', 'ver_ficha', 'ver_carreras', 'ver_referentes', 'ver_modelo', 'consultar', 'exportar', 'ver_seguimiento']
const visibles = (caps: string[]) => NAVEGACION.flatMap((g) => g.items).filter((i) => puede(caps, i.requiere)).map((i) => i.href)

describe('navegación por rol', () => {
  it('la autoridad no ve administración', () => {
    const v = visibles(AUTORIDAD)
    expect(v).toContain('/panel')
    expect(v).toContain('/consulta')
    expect(v.some((h) => h.startsWith('/admin'))).toBe(false)
  })
  it('cada pantalla exige una capacidad', () => {
    for (const i of NAVEGACION.flatMap((g) => g.items)) expect(i.requiere).toBeTruthy()
  })
  it('lleva a la primera pantalla permitida', () => {
    expect(inicioPara((c: Capacidad) => AUTORIDAD.includes(c))).toBe('/panel')
    expect(inicioPara(() => false)).toBe('/perfil')
  })
  it('ubica la ruta de una ficha dentro de Estudiantes en riesgo', () => {
    expect(ubicar('/estudiantes/abc').item?.href).toBe('/estudiantes')
  })
})
