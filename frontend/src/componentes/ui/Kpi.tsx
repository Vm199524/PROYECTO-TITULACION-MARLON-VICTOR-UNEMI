/**
 * src/componentes/ui/Kpi.tsx — indicador del panel: etiqueta, icono en pastilla según
 * el tono, valor grande con cifras tabulares, variación opcional y línea de contexto.
 */
import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { puntos } from '../../lib/formato'
import { IconoBajada, IconoSubida, type Icono } from '../iconos'
import { Card } from './Card'
import { Skeleton } from './Skeleton'

const TONO_ICONO = {
  neutral: 'bg-surface-hover text-muted-foreground',
  accent: 'bg-accent-soft text-accent',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
  success: 'bg-success-soft text-success',
}

export function Kpi({
  etiqueta,
  valor,
  icono: I,
  variacion,
  invertir,
  contexto,
  tono = 'neutral',
  cargando,
  className,
}: {
  etiqueta: string
  valor: ReactNode
  icono?: Icono
  /** Variación en puntos porcentuales frente al periodo anterior. */
  variacion?: number | null
  /** true cuando subir es malo (p. ej. la tasa de abandono). */
  invertir?: boolean
  contexto?: ReactNode
  tono?: keyof typeof TONO_ICONO
  cargando?: boolean
  className?: string
}) {
  const hay = typeof variacion === 'number' && Number.isFinite(variacion)
  const neutra = hay && Math.abs(variacion!) < 0.05
  const buena = hay && (invertir ? variacion! < 0 : variacion! > 0)
  return (
    <Card className={cn('p-5', className)}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-muted-foreground">{etiqueta}</p>
        {I && (
          <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg', TONO_ICONO[tono])}>
            <I className="h-4 w-4" />
          </span>
        )}
      </div>
      {cargando ? (
        <Skeleton className="mt-3 h-8 w-2/3" />
      ) : (
        <p className="tabular mt-2 truncate text-cifra font-semibold leading-tight tracking-tight text-foreground">{valor}</p>
      )}
      <div className="mt-2 flex min-h-[20px] flex-wrap items-center gap-x-2 gap-y-1 text-xs">
        {hay && !cargando && (
          <span
            className={cn(
              'tabular inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 font-semibold',
              neutra ? 'bg-surface-hover text-muted-foreground' : buena ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'
            )}
          >
            {!neutra && (variacion! > 0 ? <IconoSubida className="h-3.5 w-3.5" /> : <IconoBajada className="h-3.5 w-3.5" />)}
            {puntos(variacion)}
          </span>
        )}
        {contexto && !cargando && <span className="text-muted-foreground">{contexto}</span>}
      </div>
    </Card>
  )
}
