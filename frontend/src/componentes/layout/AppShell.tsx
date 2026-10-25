/**
 * src/componentes/layout/AppShell.tsx — estructura de la aplicación autenticada.
 *
 * Barra lateral fija desde 1024 px y cajón deslizante en pantallas menores (Escape y
 * cambio de ruta lo cierran). Solo <main> se desplaza: la navegación nunca se mueve.
 * La barra superior lleva las migas de pan, el selector de institución (con el tipo de
 * datos a la vista), el cambio de tema y el menú del usuario.
 */
import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { cn } from '../../lib/cn'
import { iniciales } from '../../lib/formato'
import { useSesion } from '../../lib/sesion'
import { aplicarTema, temaActual, type Tema } from '../../lib/tema'
import { IconoAbajo, IconoCerrar, IconoCheck, IconoDerecha, IconoInstitucion, IconoLateral, IconoLlave, IconoLuna, IconoMenu, IconoSalir, IconoSol } from '../iconos'
import { Marca } from '../marca/Logo'
import { BadgeDatos } from '../ui/Badge'
import { NAVEGACION, esActivo, ubicar } from './navegacion'

function BarraLateral({ onNavegar }: { onNavegar?: () => void }) {
  const { puede, institucion } = useSesion()
  const { pathname } = useLocation()
  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="px-5 pb-4 pt-5">
        <Link to="/" onClick={onNavegar} className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-active-foreground/60">
          <Marca tono="claro" tamano="sm" bajada="Alerta temprana" />
        </Link>
      </div>
      <nav aria-label="Navegación principal" className="flex-1 space-y-5 overflow-y-auto px-3 pb-4 pt-1">
        {NAVEGACION.map((grupo, g) => {
          const items = grupo.items.filter((i) => puede(i.requiere))
          if (!items.length) return null
          return (
            <div key={grupo.titulo} role="group" aria-labelledby={`grupo-nav-${g}`}>
              {/* Rótulo de sección: más tenue, espaciado y con filete, para que no se confunda con un enlace. */}
              <p id={`grupo-nav-${g}`} className="flex select-none items-center gap-2.5 px-3 pb-2 text-2xs font-semibold uppercase tracking-[0.14em] text-sidebar-muted/60">
                <span className="shrink-0">{grupo.titulo}</span>
                <span className="h-px flex-1 bg-sidebar-border" aria-hidden="true" />
              </p>
              <ul className="space-y-0.5">
                {items.map((item) => {
                  const activo = esActivo(item, pathname)
                  const I = item.icono
                  return (
                    <li key={item.href}>
                      <NavLink
                        to={item.href}
                        onClick={onNavegar}
                        aria-current={activo ? 'page' : undefined}
                        className={cn(
                          'relative flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-active-foreground/60',
                          activo ? 'bg-sidebar-active text-sidebar-active-foreground' : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-foreground'
                        )}
                      >
                        {activo && <span className="absolute left-0 top-2 h-6 w-[3px] rounded-r-full bg-marca" aria-hidden="true" />}
                        <I className="h-[18px] w-[18px] shrink-0" />
                        <span className="truncate">{item.etiqueta}</span>
                      </NavLink>
                    </li>
                  )
                })}
              </ul>
            </div>
          )
        })}
      </nav>
      <div className="border-t border-sidebar-border px-5 py-4 text-2xs leading-relaxed text-sidebar-muted">
        <p className="font-medium text-sidebar-foreground/90">Universidad Estatal de Milagro</p>
        <p className="truncate">{institucion?.nombre ?? 'Sin institución asignada'}</p>
      </div>
    </div>
  )
}

function useClicFuera(ref: React.RefObject<HTMLElement>, abierto: boolean, cerrar: () => void) {
  useEffect(() => {
    if (!abierto) return
    const fuera = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && cerrar()
    const escape = (e: KeyboardEvent) => e.key === 'Escape' && cerrar()
    document.addEventListener('mousedown', fuera)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('mousedown', fuera)
      document.removeEventListener('keydown', escape)
    }
  }, [ref, abierto, cerrar])
}

function SelectorInstitucion() {
  const { instituciones, institucion, cambiarInstitucion, perfil } = useSesion()
  const [abierto, setAbierto] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useClicFuera(ref, abierto, () => setAbierto(false))
  if (!institucion) return null
  const varias = (perfil?.instituciones.length ?? 0) > 1
  const contenido = (
    <>
      <IconoInstitucion className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="hidden max-w-[220px] truncate text-sm font-medium text-foreground md:inline">{institucion.nombre}</span>
      <span className="hidden lg:inline-flex">
        <BadgeDatos tipo={institucion.tipo_datos} />
      </span>
      {varias && <IconoAbajo className="h-3.5 w-3.5 text-muted-foreground" />}
    </>
  )
  if (!varias) {
    return (
      <div className="flex h-9 items-center gap-2 rounded-xl px-2" title={institucion.nombre}>
        {contenido}
      </div>
    )
  }
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-label={`Institución activa: ${institucion.nombre}. Cambiar institución`}
        onClick={() => setAbierto((v) => !v)}
        className="flex h-10 items-center gap-2 rounded-xl border border-border bg-surface px-2.5 sm:h-9 hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        {contenido}
      </button>
      {abierto && (
        <ul role="listbox" aria-label="Instituciones" className="entrada absolute right-0 z-40 mt-2 w-80 rounded-xl border border-border bg-surface p-1.5 shadow-flotante">
          {instituciones.map((i) => (
            <li key={i.codigo}>
              <button
                type="button"
                role="option"
                aria-selected={i.codigo === institucion.codigo}
                onClick={() => {
                  cambiarInstitucion(i.codigo)
                  setAbierto(false)
                }}
                className="flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left hover:bg-surface-hover"
              >
                <span className="mt-0.5 h-4 w-4 shrink-0 text-accent">{i.codigo === institucion.codigo && <IconoCheck className="h-4 w-4" />}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-foreground">{i.nombre}</span>
                  <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <BadgeDatos tipo={i.tipo_datos} />
                    {i.pais}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function CambioTema() {
  const [tema, setTema] = useState<Tema>(temaActual())
  useEffect(() => {
    const oir = (e: Event) => setTema((e as CustomEvent<Tema>).detail)
    window.addEventListener('vicmar:tema', oir)
    return () => window.removeEventListener('vicmar:tema', oir)
  }, [])
  const oscuro = tema === 'dark'
  return (
    <button
      type="button"
      onClick={() => aplicarTema(oscuro ? 'light' : 'dark')}
      aria-label={oscuro ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
      title={oscuro ? 'Tema claro' : 'Tema oscuro'}
      className="flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 sm:h-9 sm:w-9"
    >
      {oscuro ? <IconoSol className="h-[18px] w-[18px]" /> : <IconoLuna className="h-[18px] w-[18px]" />}
    </button>
  )
}

function MenuUsuario() {
  const { perfil, salir } = useSesion()
  const [abierto, setAbierto] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useClicFuera(ref, abierto, () => setAbierto(false))
  if (!perfil) return null
  const nombre = perfil.nombre || perfil.usuario
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={abierto}
        onClick={() => setAbierto((v) => !v)}
        className="flex items-center gap-2.5 rounded-xl p-1 pr-2 hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">{iniciales(nombre)}</span>
        <span className="hidden text-left leading-tight xl:block">
          <span className="block max-w-[160px] truncate text-sm font-medium text-foreground">{nombre}</span>
          <span className="block text-2xs text-muted-foreground">{perfil.rol_descripcion}</span>
        </span>
        <IconoAbajo className="hidden h-3.5 w-3.5 text-muted-foreground xl:block" />
      </button>
      {abierto && (
        <div role="menu" className="entrada absolute right-0 z-40 mt-2 w-64 rounded-xl border border-border bg-surface p-1.5 shadow-flotante">
          <div className="px-3 py-2.5">
            <p className="truncate text-sm font-semibold text-foreground">{nombre}</p>
            <p className="truncate text-xs text-muted-foreground">{perfil.correo || perfil.usuario}</p>
            <p className="mt-1 text-xs text-muted-foreground">{perfil.rol_descripcion}</p>
          </div>
          <div className="my-1 border-t border-border" />
          <Link role="menuitem" to="/perfil" onClick={() => setAbierto(false)} className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-foreground hover:bg-surface-hover">
            <IconoLlave className="h-4 w-4 text-muted-foreground" />
            Cambiar contraseña
          </Link>
          <button
            role="menuitem"
            type="button"
            onClick={() => salir()}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-danger hover:bg-danger-soft"
          >
            <IconoSalir className="h-4 w-4" />
            Cerrar sesión
          </button>
        </div>
      )}
    </div>
  )
}

function Migas() {
  const { pathname } = useLocation()
  const { grupo, item } = ubicar(pathname)
  if (!item) return null
  const profunda = pathname !== item.href
  return (
    <nav aria-label="Ruta" className="hidden min-w-0 items-center gap-1.5 text-sm sm:flex">
      <span className="text-muted-foreground">{grupo?.titulo}</span>
      <IconoDerecha className="h-3.5 w-3.5 text-subtle-foreground" />
      {profunda ? (
        <>
          <Link to={item.href} className="truncate text-muted-foreground hover:text-foreground">
            {item.etiqueta}
          </Link>
          <IconoDerecha className="h-3.5 w-3.5 text-subtle-foreground" />
          <span className="truncate font-medium text-foreground">Detalle</span>
        </>
      ) : (
        <span aria-current="page" className="truncate font-medium text-foreground">
          {item.etiqueta}
        </span>
      )}
    </nav>
  )
}

const CLAVE_LATERAL = 'vicmar.lateral-oculta'

function leerLateralOculta(): boolean {
  try {
    return localStorage.getItem(CLAVE_LATERAL) === '1'
  } catch {
    return false
  }
}

export function AppShell() {
  const [cajon, setCajon] = useState(false)
  // Preferencia del usuario en escritorio: la barra lateral puede ocultarse para ganar ancho.
  const [lateralOculta, setLateralOculta] = useState(leerLateralOculta)
  const alternarLateral = () =>
    setLateralOculta((v) => {
      try {
        localStorage.setItem(CLAVE_LATERAL, v ? '0' : '1')
      } catch {
        /* sin almacenamiento: la preferencia dura solo esta visita */
      }
      return !v
    })
  const { pathname } = useLocation()
  const principal = useRef<HTMLElement>(null)

  useEffect(() => {
    setCajon(false)
    principal.current?.scrollTo({ top: 0 })
  }, [pathname])

  useEffect(() => {
    if (!cajon) return
    const escape = (e: KeyboardEvent) => e.key === 'Escape' && setCajon(false)
    document.addEventListener('keydown', escape)
    return () => document.removeEventListener('keydown', escape)
  }, [cajon])

  return (
    // overflow-clip (no overflow-hidden): un contenedor "hidden" sigue siendo desplazable por
    // código (scrollIntoView, focus) y eso empujaba la barra superior fuera de la vista.
    <div className="flex h-[100dvh] overflow-clip bg-background">
      <a href="#contenido" className="sr-only z-50 rounded-lg bg-accent px-3 py-2 text-accent-foreground focus:not-sr-only focus:fixed focus:left-3 focus:top-3">
        Saltar al contenido
      </a>
      <aside
        id="barra-lateral"
        className={cn(
          'hidden shrink-0 overflow-clip transition-[width,visibility] duration-200 ease-out motion-reduce:transition-none lg:block',
          // invisible saca los enlaces del orden de tabulación mientras está oculta.
          lateralOculta ? 'invisible w-0' : 'w-72'
        )}
      >
        <div className="h-full w-72">
          <BarraLateral />
        </div>
      </aside>

      {cajon && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menú">
          <div className="absolute inset-0 bg-[rgb(2_12_22/0.55)] backdrop-blur-[2px]" onClick={() => setCajon(false)} />
          <div className="entrada absolute inset-y-0 left-0 w-[288px] max-w-[85vw] shadow-flotante">
            <BarraLateral onNavegar={() => setCajon(false)} />
            <button
              type="button"
              onClick={() => setCajon(false)}
              aria-label="Cerrar menú"
              className="absolute right-3 top-5 rounded-lg p-1.5 text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-foreground"
            >
              <IconoCerrar className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {/* z-30: el desenfoque crea un contexto de apilamiento; sin z-index los menús
            desplegables quedaban debajo del contenido de la página. */}
        <header className="relative z-30 flex h-16 shrink-0 items-center gap-3 border-b border-border bg-surface/80 px-4 backdrop-blur sm:px-6 lg:px-8">
          <button
            type="button"
            onClick={() => setCajon(true)}
            aria-label="Abrir menú"
            className="-ml-1 flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 lg:hidden"
          >
            <IconoMenu className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={alternarLateral}
            aria-controls="barra-lateral"
            aria-expanded={!lateralOculta}
            aria-label={lateralOculta ? 'Mostrar barra lateral' : 'Ocultar barra lateral'}
            title={lateralOculta ? 'Mostrar barra lateral' : 'Ocultar barra lateral'}
            className="-ml-2 hidden h-9 w-9 items-center justify-center rounded-xl text-muted-foreground hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 lg:flex"
          >
            <IconoLateral className={cn('h-[18px] w-[18px] transition-transform duration-200', lateralOculta && 'rotate-180')} />
          </button>
          <Migas />
          <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
            <SelectorInstitucion />
            <CambioTema />
            <MenuUsuario />
          </div>
        </header>
        <main id="contenido" ref={principal} tabIndex={-1} className="flex-1 overflow-y-auto focus:outline-none">
          <div className="mx-auto w-full max-w-contenido px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
