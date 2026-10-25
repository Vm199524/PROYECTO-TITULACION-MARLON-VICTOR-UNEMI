/**
 * src/componentes/ui/Button.tsx — botón base. `primary` es la única variante con el
 * color de acción y se reserva a la acción principal de cada pantalla.
 */
import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { Link, type LinkProps } from 'react-router-dom'
import { cn } from '../../lib/cn'

type Variante = 'primary' | 'secondary' | 'ghost' | 'destructive' | 'outline'
type Tamano = 'sm' | 'md' | 'lg' | 'icon'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variante
  size?: Tamano
  loading?: boolean
}

const VARIANTES: Record<Variante, string> = {
  primary: 'bg-accent text-accent-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.16),0_1px_2px_rgba(0,46,69,0.4)] hover:bg-accent-hover',
  secondary: 'border border-border bg-surface text-foreground shadow-tarjeta hover:border-border-strong hover:bg-surface-hover',
  outline: 'border border-accent/40 bg-transparent text-accent hover:bg-accent-soft',
  ghost: 'bg-transparent text-muted-foreground hover:bg-surface-hover hover:text-foreground',
  destructive: 'bg-danger text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.15)] hover:bg-danger/90',
}

const TAMANOS: Record<Tamano, string> = {
  sm: 'h-9 gap-1.5 px-3 text-sm',
  md: 'h-10 gap-2 px-4 text-sm',
  lg: 'h-11 gap-2 px-5 text-md',
  icon: 'h-10 w-10',
}

const BASE = cn(
  'relative inline-flex shrink-0 select-none items-center justify-center whitespace-nowrap rounded-xl font-medium',
  'transition-[background-color,border-color,color,box-shadow,transform] duration-150 ease-out',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
  '[&>svg]:h-4 [&>svg]:w-4 [&>svg]:shrink-0'
)

/** Enlace con apariencia de botón (navegar no es una acción: semánticamente es un enlace). */
export function BotonEnlace({ variant = 'primary', size = 'md', className, ...props }: LinkProps & { variant?: Variante; size?: Tamano }) {
  return <Link className={cn(BASE, 'active:scale-[0.98]', VARIANTES[variant], TAMANOS[size], className)} {...props} />
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, disabled, children, type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        BASE,
        'enabled:active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-55',
        VARIANTES[variant],
        TAMANOS[size],
        className
      )}
      {...props}
    >
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />}
      {children}
    </button>
  )
)
Button.displayName = 'Button'
