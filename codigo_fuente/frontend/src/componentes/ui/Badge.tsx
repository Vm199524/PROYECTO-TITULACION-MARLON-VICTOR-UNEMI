/**
 * src/componentes/ui/Badge.tsx — etiqueta de estado con colores semánticos. `BadgeRiesgo`
 * traduce el nivel del modelo: ALTO (peligro), MEDIO (aviso), BAJO (éxito). El texto
 * siempre acompaña al color: el color nunca es la única señal.
 */
import type { HTMLAttributes } from 'react'
import { cn } from '../../lib/cn'
import type { Riesgo } from '../../lib/tipos'

export type VarianteBadge = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'accent'

const ESTILOS: Record<VarianteBadge, string> = {
  success: 'bg-success-soft text-success ring-success/20',
  warning: 'bg-warning-soft text-warning ring-warning/25',
  danger: 'bg-danger-soft text-danger ring-danger/20',
  info: 'bg-info-soft text-info ring-info/20',
  neutral: 'bg-surface-hover text-muted-foreground ring-border',
  accent: 'bg-accent-soft text-accent ring-accent/25',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: VarianteBadge
  dot?: boolean
}

export function Badge({ className, variant = 'neutral', dot, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        ESTILOS[variant],
        className
      )}
      {...props}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />}
      {children}
    </span>
  )
}

export const VARIANTE_RIESGO: Record<Riesgo, VarianteBadge> = { ALTO: 'danger', MEDIO: 'warning', BAJO: 'success' }
export const TEXTO_RIESGO: Record<Riesgo, string> = { ALTO: 'Riesgo alto', MEDIO: 'Riesgo medio', BAJO: 'Riesgo bajo' }

export function BadgeRiesgo({ riesgo, corto, className }: { riesgo: Riesgo; corto?: boolean; className?: string }) {
  return (
    <Badge variant={VARIANTE_RIESGO[riesgo]} dot className={className}>
      {corto ? riesgo.charAt(0) + riesgo.slice(1).toLowerCase() : TEXTO_RIESGO[riesgo]}
    </Badge>
  )
}

/** Distintivo del tipo de datos de la institución: la honestidad sobre el origen de las cifras. */
export function BadgeDatos({ tipo }: { tipo: string | null | undefined }) {
  if (!tipo) return null
  return tipo === 'SINTETICO' ? (
    <Badge variant="warning">Datos sintéticos</Badge>
  ) : (
    <Badge variant="info">Datos reales anonimizados</Badge>
  )
}
