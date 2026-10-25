/** src/componentes/ui/Segmentado.tsx — selector de opciones excluyentes (filtros rápidos). */
import { cn } from '../../lib/cn'

export function Segmentado<T extends string>({
  opciones,
  valor,
  onCambio,
  etiqueta,
  className,
}: {
  opciones: { valor: T; texto: string }[]
  valor: T
  onCambio: (v: T) => void
  etiqueta: string
  className?: string
}) {
  return (
    <div role="radiogroup" aria-label={etiqueta} className={cn('inline-flex rounded-xl border border-border bg-surface-sunken p-0.5', className)}>
      {opciones.map((o) => (
        <button
          key={o.valor}
          type="button"
          role="radio"
          aria-checked={valor === o.valor}
          onClick={() => onCambio(o.valor)}
          className={cn(
            'h-9 rounded-[10px] px-3 sm:h-8 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60',
            valor === o.valor ? 'bg-surface text-foreground shadow-tarjeta' : 'text-muted-foreground hover:text-foreground'
          )}
        >
          {o.texto}
        </button>
      ))}
    </div>
  )
}
