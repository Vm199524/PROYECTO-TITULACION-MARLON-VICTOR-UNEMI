/**
 * src/componentes/marca/Logo.tsx — identidad visual del sistema (RNF-09).
 *
 * `Logo` es el isotipo y `Marca` el bloque completo (isotipo + nombre + bajada).
 * El isotipo es una ficha con dos caras que gira sobre su propio eje vertical:
 *   - Cara frontal: el birrete (la meta: titularse) sobre la trayectoria del
 *     estudiante, periodo a periodo, que termina en un punto naranja: la alerta
 *     temprana que se enciende antes de que la trayectoria se corte.
 *   - Dorso: ondas concéntricas de detección, simétricas, para que la media vuelta
 *     muestre el reverso de la ficha y no el glifo frontal en espejo.
 *   - Canto: franja perpendicular que da grosor cuando la ficha queda de perfil.
 * La animación vive en globales.css (`.logo-eje`) y se apaga con movimiento reducido.
 */
import { useId, type ReactNode } from 'react'
import { cn } from '../../lib/cn'

export const NOMBRE_SISTEMA = 'VicMar'
export const BAJADA_SISTEMA = 'Alerta temprana de abandono'

function Placa({ id, children }: { id: string; children: ReactNode }) {
  return (
    <svg viewBox="0 0 48 48" className="h-full w-full" aria-hidden="true">
      <defs>
        <linearGradient id={`${id}-fondo`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--marca-desde)" />
          <stop offset="50%" stopColor="var(--marca-medio)" />
          <stop offset="100%" stopColor="var(--marca-hasta)" />
        </linearGradient>
        <linearGradient id={`${id}-brillo`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.32" />
          <stop offset="50%" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <clipPath id={`${id}-recorte`}>
          <rect x="1" y="1" width="46" height="46" rx="13" />
        </clipPath>
      </defs>
      <rect x="1" y="1" width="46" height="46" rx="13" fill={`url(#${id}-fondo)`} />
      <rect x="1" y="1" width="46" height="23" rx="13" fill={`url(#${id}-brillo)`} />
      <rect x="1.6" y="1.6" width="44.8" height="44.8" rx="12.4" fill="none" stroke="#fff" strokeOpacity="0.26" strokeWidth="1.2" />
      <g clipPath={`url(#${id}-recorte)`}>{children}</g>
    </svg>
  )
}

export function Logo({ className, animado = true }: { className?: string; animado?: boolean }) {
  // useId: varios logos en pantalla no deben compartir ids de <defs>.
  const id = `logo${useId().replace(/:/g, '')}`

  const frente = (
    <Placa id={`${id}f`}>
      {/* Birrete */}
      <path d="M24 8.5 38 14 24 19.5 10 14Z" fill="#fff" />
      <path d="M16 16.6v4.2c0 2.3 16 2.3 16 0v-4.2L24 19.8Z" fill="#fff" fillOpacity="0.72" />
      <path d="M37.2 14.4v6.4" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
      {/* Trayectoria por periodos */}
      <path d="M8.5 38.5 16 33l7 2.2 8.2-6.4" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="16" cy="33" r="1.7" fill="#fff" />
      <circle cx="23" cy="35.2" r="1.7" fill="#fff" />
      {/* Alerta temprana */}
      <circle cx="36" cy="26.6" r="5" fill="var(--marca-alerta)" opacity="0.28" />
      <circle cx="36" cy="26.6" r="3.2" fill="var(--marca-alerta)" stroke="#fff" strokeWidth="1.3" />
      {animado && (
        <g transform="rotate(20 24 24)">
          <rect className="logo-destello" x="17" y="-12" width="12" height="72" fill="#fff" fillOpacity="0.3" />
        </g>
      )}
    </Placa>
  )

  if (!animado) {
    return (
      <span role="img" aria-label={NOMBRE_SISTEMA} className={cn('inline-block shrink-0', className)}>
        {frente}
      </span>
    )
  }

  return (
    <span role="img" aria-label={NOMBRE_SISTEMA} className={cn('logo-eje inline-block shrink-0', className)}>
      <span className="logo-ficha">
        <span className="logo-canto" />
        <span className="logo-cara">{frente}</span>
        <span className="logo-dorso">
          <Placa id={`${id}d`}>
            <circle cx="24" cy="24" r="4" fill="var(--marca-alerta)" stroke="#fff" strokeWidth="1.4" />
            <circle cx="24" cy="24" r="9.5" fill="none" stroke="#fff" strokeOpacity="0.85" strokeWidth="2" />
            <circle cx="24" cy="24" r="15.5" fill="none" stroke="#fff" strokeOpacity="0.5" strokeWidth="2" />
          </Placa>
        </span>
      </span>
    </span>
  )
}

const TAMANOS = {
  sm: { logo: 'h-9 w-9', nombre: 'text-[15px]', bajada: 'text-2xs' },
  md: { logo: 'h-11 w-11', nombre: 'text-base', bajada: 'text-xs' },
  lg: { logo: 'h-14 w-14', nombre: 'text-xl', bajada: 'text-sm' },
}

export function Marca({
  className,
  tono = 'auto',
  tamano = 'md',
  animado = true,
}: {
  className?: string
  /** `claro` sobre fondos oscuros (barra lateral); `auto` sigue el tema. */
  tono?: 'auto' | 'claro'
  tamano?: keyof typeof TAMANOS
  animado?: boolean
}) {
  const t = TAMANOS[tamano]
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <Logo className={cn(t.logo, 'drop-shadow-[0_6px_14px_var(--marca-sombra)]')} animado={animado} />
      <div className="min-w-0 leading-tight">
        <p className={cn('truncate font-semibold tracking-tight', t.nombre, tono === 'claro' ? 'text-sidebar-foreground' : 'text-foreground')}>
          {NOMBRE_SISTEMA}
        </p>
        <p
          className={cn(
            'truncate font-medium uppercase tracking-[0.12em]',
            t.bajada,
            tono === 'claro' ? 'text-sidebar-muted' : 'text-muted-foreground'
          )}
        >
          {BAJADA_SISTEMA}
        </p>
      </div>
    </div>
  )
}
