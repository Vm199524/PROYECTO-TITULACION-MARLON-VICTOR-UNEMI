/** Formatos únicos es-EC: los mismos que usan los reportes en Excel y PDF. */
import { decimal, entero, fecha, fechaHora, iniciales, moneda, porcentaje, primerNombre, proporcion } from '../lib/formato'

describe('formato', () => {
  it('usa separadores de Ecuador', () => {
    expect(entero(12345)).toBe('12.345')
    expect(decimal(7.5)).toBe('7,50')
    expect(moneda(1234.5)).toBe('$1.234,50')
  })
  it('escribe porcentajes con espacio y signo opcional', () => {
    expect(porcentaje(12.34)).toBe('12,3 %')
    expect(porcentaje(2, true)).toBe('+2,0 %')
    expect(porcentaje(-2, true)).toBe('−2,0 %')
    expect(proporcion(0.256, 0)).toBe('26 %')
  })
  it('muestra un guion largo cuando no hay dato', () => {
    expect(entero(null)).toBe('—')
    expect(porcentaje(undefined)).toBe('—')
    expect(fecha(null)).toBe('—')
  })
  it('no resta un día a las fechas por la zona horaria (UTC-5)', () => {
    expect(fecha('2026-10-07')).toBe('07/10/2026')
    expect(fechaHora('2026-10-07T08:05:00')).toBe('07/10/2026 08:05')
  })
  it('arma iniciales y primer nombre', () => {
    expect(iniciales('Victor Manuel Lluilema Pisco')).toBe('VP')
    expect(primerNombre('Marlon David Pérez Almachi')).toBe('Marlon')
    expect(iniciales('Autoridad académica (demostración)')).toBe('AA')
  })
})
