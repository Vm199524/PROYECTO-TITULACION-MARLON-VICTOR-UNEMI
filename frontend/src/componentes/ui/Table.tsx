/**
 * src/componentes/ui/Table.tsx — piezas de tabla: encabezado hundido, números a la
 * derecha con cifras tabulares (`<Td numero>`) y desplazamiento horizontal propio.
 */
import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-x-auto">
      <table className={cn('w-full border-collapse text-left text-sm', className)} {...props} />
    </div>
  )
}

export function TableHead({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn('border-y border-border bg-surface-sunken', className)} {...props} />
}

export function TableBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn('divide-y divide-border', className)} {...props} />
}

export function TableRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn('transition-colors hover:bg-surface-hover/60', className)} {...props} />
}

export function Th({ className, numero, ...props }: ThHTMLAttributes<HTMLTableCellElement> & { numero?: boolean }) {
  return (
    <th
      scope="col"
      className={cn(
        'whitespace-nowrap px-4 py-2.5 text-2xs font-semibold uppercase tracking-[0.06em] text-muted-foreground first:pl-5 last:pr-5 sm:first:pl-6 sm:last:pr-6',
        numero && 'text-right',
        className
      )}
      {...props}
    />
  )
}

export function Td({ className, numero, ...props }: TdHTMLAttributes<HTMLTableCellElement> & { numero?: boolean }) {
  return (
    <td
      className={cn('px-4 py-3.5 text-foreground first:pl-5 last:pr-5 sm:first:pl-6 sm:last:pr-6', numero && 'tabular whitespace-nowrap text-right', className)}
      {...props}
    />
  )
}
