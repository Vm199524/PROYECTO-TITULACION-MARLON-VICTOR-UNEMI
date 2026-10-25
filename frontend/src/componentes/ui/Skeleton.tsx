/** src/componentes/ui/Skeleton.tsx — marcador de carga con la forma del contenido real. */
import { cn } from '../../lib/cn'

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn('skeleton rounded-lg', className)} />
}
