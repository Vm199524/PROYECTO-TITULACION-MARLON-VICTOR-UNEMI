/** src/componentes/ui/Paginacion.tsx — paginación al pie de las tablas. */
import { entero } from '../../lib/formato'
import { Button } from './Button'

export function Paginacion({ pagina, tamano, total, onCambio }: { pagina: number; tamano: number; total: number; onCambio: (p: number) => void }) {
  const paginas = Math.max(1, Math.ceil(total / tamano))
  const desde = total ? (pagina - 1) * tamano + 1 : 0
  const hasta = Math.min(total, pagina * tamano)
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-5 py-3 text-sm text-muted-foreground sm:px-6">
      <span className="tabular">
        {entero(desde)}–{entero(hasta)} de {entero(total)}
      </span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" disabled={pagina <= 1} onClick={() => onCambio(pagina - 1)}>
          Anterior
        </Button>
        <span className="tabular px-1">
          Página {entero(pagina)} de {entero(paginas)}
        </span>
        <Button variant="secondary" size="sm" disabled={pagina >= paginas} onClick={() => onCambio(pagina + 1)}>
          Siguiente
        </Button>
      </div>
    </div>
  )
}
