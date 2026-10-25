/**
 * src/lib/formato.ts — formatos únicos de la aplicación (es-EC), los mismos que usan los
 * reportes en Excel y PDF: enteros `1.234`, porcentaje `12,4 %`, moneda `$1.234,50`,
 * fechas `dd/mm/aaaa` y vacío `—`.
 *
 * Las fechas `AAAA-MM-DD` se arman por componentes: `new Date('2026-10-07')` se lee
 * como UTC y en Ecuador (UTC-5) mostraría el día anterior.
 */
const VACIO = '—'
const nf = (min: number, max: number) => new Intl.NumberFormat('es-EC', { minimumFractionDigits: min, maximumFractionDigits: max })
const ENTERO = nf(0, 0)
const DECIMALES = new Map<number, Intl.NumberFormat>()
const conDecimales = (n: number) => {
  if (!DECIMALES.has(n)) DECIMALES.set(n, nf(n, n))
  return DECIMALES.get(n) as Intl.NumberFormat
}
const UNO = conDecimales(1)
const DOS = conDecimales(2)

const vacio = (v: unknown) => v === null || v === undefined || (typeof v === 'number' && !Number.isFinite(v))

export function entero(v: number | null | undefined): string {
  return vacio(v) ? VACIO : ENTERO.format(v as number)
}

export function decimal(v: number | null | undefined, decimales = 2): string {
  if (vacio(v)) return VACIO
  return conDecimales(Math.max(0, Math.min(6, Math.round(decimales)))).format(v as number)
}

/** Porcentaje a partir de un valor ya expresado en 0–100. */
export function porcentaje(v: number | null | undefined, conSigno = false, decimales = 1): string {
  if (vacio(v)) return VACIO
  const n = v as number
  const texto = (decimales === 0 ? ENTERO : decimales === 2 ? DOS : UNO).format(Math.abs(n))
  const signo = conSigno ? (n > 0 ? '+' : n < 0 ? '−' : '') : n < 0 ? '−' : ''
  return `${signo}${texto} %`
}

/** Diferencia en puntos porcentuales ("+1,2 pts"). */
export function puntos(v: number | null | undefined): string {
  if (vacio(v)) return VACIO
  const n = v as number
  return `${n > 0 ? '+' : n < 0 ? '−' : ''}${UNO.format(Math.abs(n))} pts`
}

/** Porcentaje a partir de una proporción 0–1. */
export function proporcion(v: number | null | undefined, decimales = 1): string {
  return vacio(v) ? VACIO : porcentaje((v as number) * 100, false, decimales)
}

export function moneda(v: number | null | undefined): string {
  return vacio(v) ? VACIO : `$${DOS.format(v as number)}`
}

function partes(valor: string): [number, number, number, string] | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/.exec(valor)
  if (!m) return null
  return [Number(m[1]), Number(m[2]), Number(m[3]), m[4] ? `${m[4]}:${m[5]}` : '']
}

export function fecha(valor: string | null | undefined): string {
  if (!valor) return VACIO
  const p = partes(valor)
  if (!p) return valor
  return `${String(p[2]).padStart(2, '0')}/${String(p[1]).padStart(2, '0')}/${p[0]}`
}

export function fechaHora(valor: string | null | undefined): string {
  if (!valor) return VACIO
  const p = partes(valor)
  if (!p) return valor
  return p[3] ? `${fecha(valor)} ${p[3]}` : fecha(valor)
}

export function texto(v: unknown): string {
  if (vacio(v) || v === '') return VACIO
  return String(v)
}

/** "Buenos días" / "Buenas tardes" / "Buenas noches" según la hora local. */
export function saludo(ahora = new Date()): string {
  const h = ahora.getHours()
  return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches'
}

export function iniciales(nombre: string | null | undefined): string {
  if (!nombre) return '?'
  const p = nombre.trim().split(/\s+/).filter((x) => /^\p{L}/u.test(x))
  if (!p.length) return '?'
  return ((p[0][0] ?? '') + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase()
}

/** Primer nombre para el saludo ("Victor Manuel Lluilema" → "Victor"). */
export function primerNombre(nombre: string | null | undefined): string {
  return nombre?.trim().split(/\s+/)[0] ?? ''
}

/** Primera letra en mayúscula ("promedio del periodo" → "Promedio del periodo"). */
export function capital(t: string | null | undefined): string {
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : ''
}
