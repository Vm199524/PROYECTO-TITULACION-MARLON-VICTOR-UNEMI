/** src/componentes/ui/Input.tsx — campos (texto, selección, área) y el envoltorio `Campo`. */
import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

export const estiloCampo = cn(
  'w-full rounded-xl border border-border bg-surface px-3 text-base text-foreground sm:text-sm shadow-[inset_0_1px_1px_rgba(15,23,42,0.03)]',
  'placeholder:text-subtle-foreground transition-[border-color,box-shadow]',
  'hover:border-border-strong focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/15',
  'disabled:cursor-not-allowed disabled:opacity-60 aria-[invalid=true]:border-danger aria-[invalid=true]:focus:ring-danger/15'
)

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn(estiloCampo, 'h-10', className)} {...props} />
))
Input.displayName = 'Input'

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(({ className, children, ...props }, ref) => (
  <select ref={ref} className={cn(estiloCampo, 'h-10 cursor-pointer pr-8', className)} {...props}>
    {children}
  </select>
))
Select.displayName = 'Select'

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(estiloCampo, 'min-h-[84px] py-2.5', className)} {...props} />
))
Textarea.displayName = 'Textarea'

/** Etiqueta + control + ayuda + error, enlazados por id para lectores de pantalla. */
export function Campo({
  etiqueta,
  ayuda,
  error,
  children,
  className,
}: {
  etiqueta: string
  ayuda?: ReactNode
  error?: string | null
  children: (props: { id: string; 'aria-invalid'?: boolean; 'aria-describedby'?: string }) => ReactNode
  className?: string
}) {
  const id = useId()
  const descripcion = error ? `${id}-error` : ayuda ? `${id}-ayuda` : undefined
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="block text-sm font-medium text-foreground">
        {etiqueta}
      </label>
      {children({ id, 'aria-invalid': error ? true : undefined, 'aria-describedby': descripcion })}
      {error ? (
        <p id={`${id}-error`} className="text-xs text-danger">
          {error}
        </p>
      ) : ayuda ? (
        <p id={`${id}-ayuda`} className="text-xs text-muted-foreground">
          {ayuda}
        </p>
      ) : null}
    </div>
  )
}
