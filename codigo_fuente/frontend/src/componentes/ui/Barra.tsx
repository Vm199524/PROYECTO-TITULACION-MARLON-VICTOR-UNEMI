/** src/componentes/ui/Barra.tsx — barra de progreso para coberturas y proporciones (0–100). */
import { cn } from '../../lib/cn'

const TONOS = { accent: 'bg-accent', danger: 'bg-danger', warning: 'bg-warning', success: 'bg-success', neutral: 'bg-subtle-foreground' }

export function Barra({ valor, tono = 'accent', etiqueta, className }: { valor: number; tono?: keyof typeof TONOS; etiqueta: string; className?: string }) {
  const v = Math.max(0, Math.min(100, valor))
  return (
    <div
      role="progressbar"
      aria-label={etiqueta}
      aria-valuenow={Math.round(v)}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn('h-2 w-full overflow-hidden rounded-full bg-surface-hover', className)}
    >
      <div className={cn('h-full rounded-full transition-[width] duration-500', TONOS[tono])} style={{ width: `${v}%` }} />
    </div>
  )
}
