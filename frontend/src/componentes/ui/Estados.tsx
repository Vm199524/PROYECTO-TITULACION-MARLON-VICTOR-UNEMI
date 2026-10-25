/**
 * src/componentes/ui/Estados.tsx — estados obligatorios de toda vista con datos:
 * vacío (qué hacer a continuación), error (qué pasó y reintentar) y avisos en línea.
 */
import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { IconoAviso, IconoBaseDatos, IconoInfo, IconoCheck, type Icono } from '../iconos'
import { Button } from './Button'

export function EmptyState({
  title,
  description,
  icon: I = IconoBaseDatos,
  action,
  className,
}: {
  title: string
  description?: ReactNode
  icon?: Icono
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center px-6 py-14 text-center', className)}>
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-surface-hover text-muted-foreground ring-1 ring-border">
        <I className="h-6 w-6" />
      </span>
      <p className="mt-4 text-sm font-semibold text-foreground">{title}</p>
      {description && <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function EstadoError({ error, onReintentar, className }: { error: unknown; onReintentar?: () => void; className?: string }) {
  const mensaje = error instanceof Error ? error.message : 'No se pudieron cargar los datos.'
  return (
    <EmptyState
      className={className}
      icon={IconoAviso}
      title="No se pudieron cargar los datos"
      description={mensaje}
      action={
        onReintentar && (
          <Button variant="secondary" size="sm" onClick={onReintentar}>
            Reintentar
          </Button>
        )
      }
    />
  )
}

const TONOS = {
  info: { clase: 'border-info/25 bg-info-soft text-info', icono: IconoInfo },
  warning: { clase: 'border-warning/30 bg-warning-soft text-warning', icono: IconoAviso },
  danger: { clase: 'border-danger/25 bg-danger-soft text-danger', icono: IconoAviso },
  success: { clase: 'border-success/25 bg-success-soft text-success', icono: IconoCheck },
}

export function Aviso({
  tono = 'info',
  titulo,
  children,
  className,
}: {
  tono?: keyof typeof TONOS
  titulo?: ReactNode
  children?: ReactNode
  className?: string
}) {
  const { clase, icono: I } = TONOS[tono]
  return (
    <div role={tono === 'danger' ? 'alert' : 'status'} className={cn('flex gap-3 rounded-xl border px-4 py-3 text-sm', clase, className)}>
      <I className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0 space-y-0.5">
        {titulo && <p className="font-semibold">{titulo}</p>}
        {children && <div className="text-foreground/80">{children}</div>}
      </div>
    </div>
  )
}

/** Indicador discreto cuando se recargan datos que ya están en pantalla. */
export function Actualizando({ activo }: { activo: boolean }) {
  if (!activo) return null
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground" role="status">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      Actualizando…
    </span>
  )
}
