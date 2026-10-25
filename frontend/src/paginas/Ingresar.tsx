/**
 * src/paginas/Ingresar.tsx — acceso al sistema (RF-01 autenticación).
 *
 * Pantalla de apertura propia del proyecto («órbita de detección»):
 *   - Fondo vivo: dos auroras suaves (azul UNEMI y naranja) que derivan lento, una malla
 *     de puntos y las trayectorias de los estudiantes, que se dibujan al abrir. Por
 *     algunas avanzan estudiantes (pulsos azules); otras se cortan y terminan en un
 *     punto naranja con ondas: el abandono que el sistema busca anticipar.
 *   - Encabezado: el emblema animado (ficha del logo con órbita y satélites) junto al
 *     nombre del sistema.
 *   - Centro: la tarjeta de credenciales; a los costados, seis nodos con lo que hace el
 *     sistema, unidos a la tarjeta por trazas en degradado por las que viajan datos.
 * La secuencia de apertura ocurre una sola vez y se apaga con movimiento reducido.
 * Un solo envío por clic y el error se muestra una vez.
 */
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { IconoChispa, IconoConsulta, IconoLlave, IconoModelo, IconoSeguimiento, IconoSimular, IconoTendencia, type Icono } from '../componentes/iconos'
import { BAJADA_SISTEMA, Emblema, NOMBRE_SISTEMA } from '../componentes/marca/Logo'
import { Button } from '../componentes/ui/Button'
import { Aviso } from '../componentes/ui/Estados'
import { Campo, Input } from '../componentes/ui/Input'
import { cn } from '../lib/cn'
import { useSesion } from '../lib/sesion'

interface Nodo {
  titulo: string
  texto: string
  tecnica: string
  icono: Icono
}

const IZQUIERDA: Nodo[] = [
  { titulo: 'Predice', texto: 'La probabilidad de que cada estudiante activo abandone el próximo periodo.', tecnica: 'LightGBM calibrado', icono: IconoTendencia },
  { titulo: 'Explica', texto: 'Qué datos del estudiante empujan su riesgo hacia arriba o hacia abajo.', tecnica: 'Contribuciones SHAP', icono: IconoChispa },
  { titulo: 'Simula', texto: '¿Qué pasaría si mejora su asistencia o se pone al día con sus pagos?', tecnica: 'Escenarios «¿qué pasaría si…?»', icono: IconoSimular },
]
const DERECHA: Nodo[] = [
  { titulo: 'Responde', texto: 'Preguntas en español con cifras de la base institucional.', tecnica: 'Consulta conversacional', icono: IconoConsulta },
  { titulo: 'Protege', texto: 'Solo lectura, cédulas enmascaradas y cada acceso en la bitácora.', tecnica: 'LOPDP · mínimo privilegio', icono: IconoModelo },
  { titulo: 'Acompaña', texto: 'Registra cada intervención de bienestar y su resultado.', tecnica: 'Seguimiento de alertas', icono: IconoSeguimiento },
]

// Geometría del escenario (px dentro de un lienzo de 1240 × 600).
const ANCHO = 1240
const ALTO = 600
const TARJETA = { x: 410, ancho: 420 }
const CENTROS_Y = [112, 300, 488]
const ENTRADAS_Y = [205, 300, 395]
const SANGRIA = [64, 0, 64] // arco: el nodo del medio queda más afuera
const ANCHO_NODO = 276

/** Generador pseudoaleatorio con semilla: el dibujo es siempre el mismo. */
function azar(semilla: number) {
  let s = semilla
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

function FondoVivo({ movimiento }: { movimiento: boolean }) {
  const { lineas, cortes, completas } = useMemo(() => {
    const r = azar(20260909)
    const pasos = 12
    const lineas: string[] = []
    const cortes: { x: number; y: number; paso: number }[] = []
    const completas: number[] = []
    for (let i = 0; i < 26; i++) {
      let y = 60 + i * 15 + r() * 10
      const abandona = r() < 0.24
      const ultimo = abandona ? 4 + Math.floor(r() * 6) : pasos
      const puntos: string[] = []
      for (let k = 0; k <= ultimo; k++) {
        y += (r() - 0.5) * 16 + (abandona && k >= ultimo - 1 ? 18 : 0)
        puntos.push(`${((k / pasos) * 1600).toFixed(0)},${y.toFixed(1)}`)
      }
      lineas.push(`M ${puntos.join(' L ')}`)
      if (abandona) {
        const [x, yy] = puntos[puntos.length - 1].split(',').map(Number)
        cortes.push({ x, y: yy, paso: ultimo })
      } else if (completas.length < 7 && i % 3 === 0) {
        completas.push(i)
      }
    }
    return { lineas, cortes, completas }
  }, [])

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className="aurora absolute -left-[12%] -top-[18%] h-[60%] w-[55%] rounded-full bg-[rgb(var(--accent)/0.16)]" />
      <div className="aurora aurora-2 absolute -right-[10%] top-[18%] h-[55%] w-[45%] rounded-full bg-[rgb(255_150_80/0.16)]" />
      <div className="malla-puntos absolute inset-0" />
      <svg viewBox="0 0 1600 520" preserveAspectRatio="xMidYMax slice" className="absolute inset-x-0 bottom-0 h-[64%] w-full">
        <defs>
          <linearGradient id="fondo-trayectoria" x1="0" x2="1">
            <stop offset="0" stopColor="rgb(var(--accent))" stopOpacity="0" />
            <stop offset="0.22" stopColor="rgb(var(--accent))" stopOpacity="0.32" />
            <stop offset="1" stopColor="rgb(var(--accent))" stopOpacity="0.14" />
          </linearGradient>
          <linearGradient id="fondo-desvanece" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fff" stopOpacity="0" />
            <stop offset="0.35" stopColor="#fff" stopOpacity="1" />
          </linearGradient>
          <mask id="fondo-mascara">
            <rect width="1600" height="520" fill="url(#fondo-desvanece)" />
          </mask>
        </defs>
        <g mask="url(#fondo-mascara)">
          {lineas.map((d, i) => (
            <path
              key={i}
              id={`fondo-t${i}`}
              d={d}
              pathLength={1}
              className="apertura-trazo"
              style={{ animationDelay: `${(i % 7) * 70}ms` }}
              fill="none"
              stroke="url(#fondo-trayectoria)"
              strokeWidth="1.5"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          ))}
          {movimiento &&
            completas.map((i, n) => (
              <circle key={`p${i}`} r="2.6" fill="rgb(var(--accent))" opacity="0">
                <animateMotion dur={`${9 + n * 1.3}s`} begin={`${1.6 + n * 0.9}s`} repeatCount="indefinite">
                  <mpath href={`#fondo-t${i}`} />
                </animateMotion>
                <animate attributeName="opacity" values="0;0.85;0.85;0" keyTimes="0;0.1;0.9;1" dur={`${9 + n * 1.3}s`} begin={`${1.6 + n * 0.9}s`} repeatCount="indefinite" />
              </circle>
            ))}
          {cortes.map((c, i) => (
            <g key={`c${i}`} className="apertura-aparece" style={{ animationDelay: `${500 + c.paso * 110}ms` }}>
              {movimiento && (
                <circle cx={c.x} cy={c.y} r="4" fill="none" stroke="var(--marca-medio)" strokeWidth="1.2">
                  <animate attributeName="r" values="4;16" dur="2.8s" begin={`${i * 0.45}s`} repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.7;0" dur="2.8s" begin={`${i * 0.45}s`} repeatCount="indefinite" />
                </circle>
              )}
              <circle cx={c.x} cy={c.y} r="4.2" fill="var(--marca-medio)" stroke="#fff" strokeWidth="1.4" />
            </g>
          ))}
        </g>
      </svg>
    </div>
  )
}

function TarjetaNodo({ nodo, lado, indice }: { nodo: Nodo; lado: 'izq' | 'der'; indice: number }) {
  const I = nodo.icono
  return (
    <div
      className={cn(
        'apertura-nodo group rounded-2xl border border-border/80 bg-surface/90 p-4 shadow-tarjeta backdrop-blur',
        'transition-[transform,box-shadow,border-color] duration-300 hover:-translate-y-0.5 hover:border-[rgb(245_148_71/0.45)] hover:shadow-flotante',
        lado === 'izq' ? 'text-right' : 'text-left'
      )}
      style={{ animationDelay: `${950 + indice * 130 + (lado === 'der' ? 65 : 0)}ms` }}
    >
      <div className={cn('flex items-center gap-3', lado === 'izq' && 'flex-row-reverse')}>
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--marca-desde)] to-[var(--marca-hasta)] text-white shadow-[0_6px_14px_-4px_var(--marca-sombra)] transition-transform duration-300 group-hover:scale-105">
          <I className="h-5 w-5" />
        </span>
        <div className={cn('min-w-0', lado === 'izq' && 'flex flex-col items-end')}>
          <p className="text-md font-semibold tracking-tight text-foreground">{nodo.titulo}</p>
          <span className="mt-0.5 inline-block rounded-full bg-accent-soft px-2 py-0.5 text-2xs font-medium text-accent">{nodo.tecnica}</span>
        </div>
      </div>
      <p className="mt-2.5 text-sm leading-snug text-muted-foreground">{nodo.texto}</p>
    </div>
  )
}

/** Trazas en degradado (azul en el nodo, naranja en la tarjeta) con datos viajando al centro. */
function Trazas({ movimiento }: { movimiento: boolean }) {
  const trazas: { d: string; desde: [number, number]; hasta: [number, number] }[] = []
  CENTROS_Y.forEach((y, i) => {
    const xi = ANCHO_NODO + SANGRIA[i]
    const ye = ENTRADAS_Y[i]
    trazas.push({ d: `M ${xi} ${y} C ${xi + 56} ${y}, ${TARJETA.x - 56} ${ye}, ${TARJETA.x} ${ye}`, desde: [xi, y], hasta: [TARJETA.x, ye] })
    const xd = ANCHO - ANCHO_NODO - SANGRIA[i]
    const xc = TARJETA.x + TARJETA.ancho
    trazas.push({ d: `M ${xd} ${y} C ${xd - 56} ${y}, ${xc + 56} ${ye}, ${xc} ${ye}`, desde: [xd, y], hasta: [xc, ye] })
  })
  return (
    <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
      <defs>
        {trazas.map((t, i) => (
          <linearGradient key={i} id={`traza-g${i}`} gradientUnits="userSpaceOnUse" x1={t.desde[0]} y1={t.desde[1]} x2={t.hasta[0]} y2={t.hasta[1]}>
            <stop offset="0" stopColor="rgb(var(--accent))" stopOpacity="0.55" />
            <stop offset="1" stopColor="var(--marca-medio)" stopOpacity="0.9" />
          </linearGradient>
        ))}
        <filter id="traza-brillo" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.2" />
        </filter>
      </defs>
      {trazas.map((t, i) => {
        const dur = `${2.4 + (i % 3) * 0.45}s`
        const inicio = `${2.3 + i * 0.32}s`
        return (
          <g key={i}>
            <path id={`traza-${i}`} d={t.d} pathLength={1} fill="none" stroke={`url(#traza-g${i})`} strokeWidth="1.6" strokeLinecap="round" className="apertura-trazo" style={{ animationDelay: `${1150 + i * 70}ms` }} />
            <g className="apertura-aparece" style={{ animationDelay: `${1150 + i * 70}ms` }}>
              <circle cx={t.desde[0]} cy={t.desde[1]} r="3.2" fill="rgb(var(--surface))" stroke="rgb(var(--accent))" strokeWidth="1.6" />
              <circle cx={t.hasta[0]} cy={t.hasta[1]} r="3.6" fill="var(--marca-medio)" stroke="rgb(var(--surface))" strokeWidth="1.6" />
            </g>
            {movimiento && (
              <g opacity="0">
                <circle r="5" fill="var(--marca-medio)" opacity="0.45" filter="url(#traza-brillo)" />
                <circle r="2.4" fill="var(--marca-medio)" />
                <animateMotion dur={dur} begin={inicio} repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines="0.45 0 0.55 1" keyPoints="0;1">
                  <mpath href={`#traza-${i}`} />
                </animateMotion>
                <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.15;0.8;1" dur={dur} begin={inicio} repeatCount="indefinite" />
              </g>
            )}
          </g>
        )
      })}
    </svg>
  )
}

/** true desde `px` de ancho: la tarjeta se monta una sola vez (un solo formulario en el DOM). */
function useAnchoMinimo(px: number): boolean {
  const consulta = `(min-width: ${px}px)`
  const [cumple, setCumple] = useState(() => {
    try {
      return window.matchMedia(consulta).matches
    } catch {
      return false
    }
  })
  useEffect(() => {
    let mq: MediaQueryList
    try {
      mq = window.matchMedia(consulta)
    } catch {
      return
    }
    const cambio = () => setCumple(mq.matches)
    mq.addEventListener('change', cambio)
    return () => mq.removeEventListener('change', cambio)
  }, [consulta])
  return cumple
}

export default function Ingresar() {
  const { ingresar, avisoSalida } = useSesion()
  const navegar = useNavigate()
  const { state } = useLocation() as { state?: { desde?: string } }
  const [usuario, setUsuario] = useState('')
  const [clave, setClave] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const escenario = useAnchoMinimo(1320)
  const movimiento = useMemo(() => {
    try {
      return !window.matchMedia('(prefers-reduced-motion: reduce)').matches
    } catch {
      return true
    }
  }, [])

  async function enviar(e: FormEvent) {
    e.preventDefault()
    if (enviando) return
    if (!usuario.trim() || !clave) {
      setError('Ingrese su usuario y su contraseña.')
      return
    }
    setEnviando(true)
    setError(null)
    try {
      await ingresar(usuario.trim(), clave)
      navegar(state?.desde && state.desde !== '/ingresar' ? state.desde : '/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo ingresar.')
      setEnviando(false)
    }
  }

  const tarjeta = (
    <section aria-labelledby="titulo-acceso" className="apertura-tarjeta w-full max-w-[420px] overflow-hidden rounded-2xl border border-border/80 bg-surface shadow-[0_24px_60px_-18px_rgba(11,58,82,0.28)]">
      <div className="h-1 bg-gradient-to-r from-[var(--marca-desde)] via-[var(--marca-medio)] to-[var(--marca-hasta)]" aria-hidden="true" />
      <div className="flex items-center gap-3 px-7 pb-1 pt-6">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
          <IconoLlave className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <h2 id="titulo-acceso" className="text-lg font-semibold tracking-tight text-foreground">
            Ingreso al sistema
          </h2>
          <p className="text-sm text-muted-foreground">Use la cuenta que le asignó Administración de TI.</p>
        </div>
      </div>
      <form onSubmit={enviar} noValidate className="space-y-5 px-7 pb-6 pt-5">
        {avisoSalida && !error && <Aviso tono="info">{avisoSalida}</Aviso>}
        {error && <Aviso tono="danger">{error}</Aviso>}
        <Campo etiqueta="Usuario">
          {(p) => <Input {...p} autoComplete="username" autoFocus value={usuario} onChange={(e) => setUsuario(e.target.value)} placeholder="nombre.apellido" className="h-11 text-md" />}
        </Campo>
        <Campo etiqueta="Contraseña">
          {(p) => <Input {...p} type="password" autoComplete="current-password" value={clave} onChange={(e) => setClave(e.target.value)} className="h-11 text-md" />}
        </Campo>
        <Button type="submit" size="lg" loading={enviando} className="w-full bg-gradient-to-r from-[#0b5c7e] to-[#0b3a52] hover:from-[#0e6a91] hover:to-[#0b4663] dark:from-accent dark:to-accent">
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </Button>
      </form>
      <p className="border-t border-border/70 bg-surface-sunken px-7 py-3.5 text-xs leading-relaxed text-muted-foreground">
        Cinco intentos fallidos bloquean la cuenta cinco minutos. Cada ingreso queda en la bitácora de auditoría.
      </p>
    </section>
  )

  return (
    <div className="relative flex min-h-[100dvh] flex-col overflow-hidden bg-background">
      <FondoVivo movimiento={movimiento} />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r from-[var(--marca-desde)] via-[var(--marca-medio)] to-[var(--marca-hasta)]" aria-hidden="true" />

      <header className="relative flex items-center justify-between gap-4 px-5 py-5 sm:px-10">
        <p className="text-sm font-semibold tracking-tight text-foreground">Universidad Estatal de Milagro</p>
        <p className="hidden text-sm text-muted-foreground sm:block">Ingeniería en Tecnologías de la Información</p>
      </header>

      <main className="relative flex flex-1 flex-col items-center justify-center px-4 pb-8">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="flex items-center gap-4">
            <Emblema className="h-[92px] w-[92px]" />
            <div className="apertura-titulo text-left">
              <h1 className="text-[40px] font-semibold leading-none tracking-tight text-foreground sm:text-[46px]">{NOMBRE_SISTEMA}</h1>
              <p className="mt-2 text-sm font-medium uppercase tracking-[0.16em] text-[var(--marca-hasta)]">{BAJADA_SISTEMA}</p>
            </div>
          </div>
          <p className="apertura-titulo mx-auto mt-4 max-w-md text-md leading-relaxed text-muted-foreground">
            Quién está en riesgo de dejar la universidad, por qué y qué hacer a tiempo.
          </p>
        </div>

        {/* Escenario completo desde 1320 px: nodos en órbita y trazas hacia la tarjeta. */}
        <div className="relative hidden min-[1320px]:block" style={{ width: ANCHO, height: ALTO }}>
          <Trazas movimiento={movimiento} />
          {IZQUIERDA.map((n, i) => (
            <div key={n.titulo} className="absolute -translate-y-1/2" style={{ left: SANGRIA[i], top: CENTROS_Y[i], width: ANCHO_NODO }}>
              <TarjetaNodo nodo={n} lado="izq" indice={i} />
            </div>
          ))}
          {DERECHA.map((n, i) => (
            <div key={n.titulo} className="absolute -translate-y-1/2" style={{ right: SANGRIA[i], top: CENTROS_Y[i], width: ANCHO_NODO }}>
              <TarjetaNodo nodo={n} lado="der" indice={i} />
            </div>
          ))}
          <div className="absolute top-1/2 -translate-y-1/2" style={{ left: TARJETA.x, width: TARJETA.ancho }}>
            {escenario && tarjeta}
          </div>
        </div>

        {/* Pantallas menores: tarjeta y, debajo, los nodos en rejilla. */}
        <div className="flex w-full flex-col items-center min-[1320px]:hidden">
          {!escenario && tarjeta}
          <div className="mt-8 grid w-full max-w-3xl gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[...IZQUIERDA, ...DERECHA].map((n, i) => (
              <TarjetaNodo key={n.titulo} nodo={n} lado="der" indice={i} />
            ))}
          </div>
        </div>
      </main>

      <footer className="relative px-5 pb-5 text-center text-xs leading-relaxed text-muted-foreground sm:px-10">
        Proyecto de titulación · Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco · 2026
      </footer>
    </div>
  )
}
