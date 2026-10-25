/**
 * src/componentes/ui/Dialogo.tsx — diálogo sobre <dialog> nativo: el navegador maneja
 * el foco, la tecla Escape y el fondo.
 */
import { useEffect, useRef, type ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { IconoCerrar } from '../iconos'

export function Dialogo({
  abierto,
  onCerrar,
  titulo,
  descripcion,
  children,
  pie,
  className,
}: {
  abierto: boolean
  onCerrar: () => void
  titulo: string
  descripcion?: ReactNode
  children?: ReactNode
  pie?: ReactNode
  className?: string
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (abierto && !d.open) d.showModal?.()
    if (!abierto && d.open) d.close()
  }, [abierto])
  return (
    <dialog
      ref={ref}
      onClose={onCerrar}
      onCancel={onCerrar}
      className={cn('w-[calc(100%-32px)] max-w-lg rounded-2xl border border-border bg-surface p-0 text-foreground shadow-flotante', className)}
    >
      {abierto && (
        <div className="entrada">
          <div className="flex items-start justify-between gap-4 px-6 pt-5">
            <div>
              <h2 className="text-base font-semibold tracking-tight">{titulo}</h2>
              {descripcion && <p className="mt-1 text-sm text-muted-foreground">{descripcion}</p>}
            </div>
            <button
              type="button"
              onClick={onCerrar}
              aria-label="Cerrar"
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
            >
              <IconoCerrar className="h-4 w-4" />
            </button>
          </div>
          <div className="px-6 py-5">{children}</div>
          {pie && <div className="flex justify-end gap-2 border-t border-border px-6 py-4">{pie}</div>}
        </div>
      )}
    </dialog>
  )
}
