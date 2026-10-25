/**
 * src/componentes/layout/EncabezadoPagina.tsx — encabezado idéntico en todas las
 * pantallas: enlace "volver" opcional, título, descripción breve, acciones a la derecha
 * y, debajo, los filtros (`extra`).
 */
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { IconoVolver } from '../iconos'

export function EncabezadoPagina({
  titulo,
  descripcion,
  acciones,
  volver,
  extra,
}: {
  titulo: ReactNode
  descripcion?: ReactNode
  acciones?: ReactNode
  volver?: { href: string; texto: string }
  extra?: ReactNode
}) {
  return (
    <header className="mb-6 space-y-4">
      {volver && (
        <Link to={volver.href} className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground">
          <IconoVolver className="h-4 w-4" />
          {volver.texto}
        </Link>
      )}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">{titulo}</h1>
          {descripcion && <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{descripcion}</p>}
        </div>
        {acciones && <div className="flex flex-wrap items-center gap-2">{acciones}</div>}
      </div>
      {extra}
    </header>
  )
}
