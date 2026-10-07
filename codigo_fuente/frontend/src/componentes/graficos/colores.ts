/**
 * src/componentes/graficos/colores.ts — colores de los gráficos leídos de los tokens.
 *
 * Los atributos SVG que usa Recharts no resuelven var(--token), así que se leen los
 * valores calculados y se vuelven a leer al cambiar de tema.
 */
import { useEffect, useState } from 'react'

const TOKENS = ['chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5', 'danger', 'warning', 'success', 'info', 'accent',
  'border', 'muted-foreground', 'subtle-foreground', 'foreground', 'surface'] as const
export type Colores = Record<(typeof TOKENS)[number], string>

function leer(): Colores {
  const estilo = getComputedStyle(document.documentElement)
  const salida = {} as Colores
  for (const t of TOKENS) {
    const v = estilo.getPropertyValue(`--${t}`).trim().replace(/\s*\/\s*[\d.]+$/, '')
    salida[t] = v ? `rgb(${v.split(/\s+/).join(', ')})` : '#888'
  }
  return salida
}

export function useColores(): Colores {
  const [c, setC] = useState<Colores>(leer)
  useEffect(() => {
    const actualizar = () => setC(leer())
    window.addEventListener('vicmar:tema', actualizar)
    return () => window.removeEventListener('vicmar:tema', actualizar)
  }, [])
  return c
}
