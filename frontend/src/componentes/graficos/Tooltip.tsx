/** src/componentes/graficos/Tooltip.tsx — tooltip propio con el estilo de tarjeta flotante. */
import type { ReactNode } from 'react'

interface Entrada {
  name?: string | number
  value?: number | string
  color?: string
  dataKey?: string | number
  payload?: Record<string, unknown>
}

export function TooltipGrafico({
  active,
  payload,
  label,
  formato,
  titulo,
}: {
  active?: boolean
  payload?: Entrada[]
  label?: ReactNode
  formato?: (valor: number, nombre: string) => string
  titulo?: (label: ReactNode, payload: Entrada[]) => ReactNode
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-border bg-surface px-3 py-2.5 text-xs shadow-flotante">
      <p className="mb-1.5 font-semibold text-foreground">{titulo ? titulo(label, payload) : label}</p>
      <ul className="space-y-1">
        {payload.map((p) => (
          <li key={String(p.dataKey ?? p.name)} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} aria-hidden="true" />
            <span className="text-muted-foreground">{p.name}</span>
            <span className="tabular ml-auto pl-3 font-medium text-foreground">
              {formato && typeof p.value === 'number' ? formato(p.value, String(p.name)) : p.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function Leyenda({ items }: { items: { texto: string; color: string; forma?: 'punto' | 'linea' }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
      {items.map((i) => (
        <li key={i.texto} className="flex items-center gap-1.5">
          <span
            className={i.forma === 'linea' ? 'h-0.5 w-3.5 rounded-full' : 'h-2.5 w-2.5 rounded-sm'}
            style={{ background: i.color }}
            aria-hidden="true"
          />
          {i.texto}
        </li>
      ))}
    </ul>
  )
}
