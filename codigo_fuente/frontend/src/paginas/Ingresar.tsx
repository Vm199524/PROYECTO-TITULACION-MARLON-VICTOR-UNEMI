/**
 * src/paginas/Ingresar.tsx — acceso al sistema (RF-01 autenticación).
 *
 * Pantalla de apertura propia del proyecto («órbita de detección»):
 *   - Fondo: trayectorias de estudiantes semestre a semestre que se dibujan al abrir;
 *     algunas se cortan y terminan en un punto naranja, el abandono que el sistema
 *     busca anticipar.
 *   - Centro: la tarjeta de credenciales.
 *   - Costados: seis nodos con lo que hace el sistema (predice, explica, simula,
 *     pregunta, protege y acompaña), unidos a la tarjeta por trazas por las que viajan
 *     pulsos de datos hacia el centro.
 * La secuencia de apertura ocurre una sola vez y se desactiva con movimiento reducido.
 * Un solo envío por clic y el error se muestra una vez.
 */
import { useMemo, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { IconoChispa, IconoConsulta, IconoModelo, IconoSeguimiento, IconoSimular, IconoTendencia, type Icono } from '../componentes/iconos'
import { Logo, NOMBRE_SISTEMA } from '../componentes/marca/Logo'
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
  { titulo: 'Simula', texto: '¿Qué pasaría si mejora su asistencia o se pone al día con sus pagos?', tecnica: 'Escenarios sobre el mismo modelo', icono: IconoSimular },
]
const DERECHA: Nodo[] = [
  { titulo: 'Responde', texto: 'Preguntas en español con cifras de la base institucional.', tecnica: 'Consulta conversacional', icono: IconoConsulta },
  { titulo: 'Protege', texto: 'Solo lectura, cédulas enmascaradas y cada acceso en la bitácora.', tecnica: 'LOPDP · mínimo privilegio', icono: IconoModelo },
  { titulo: 'Acompaña', texto: 'Registra cada intervención de bienestar y su resultado.', tecnica: 'Seguimiento de alertas', icono: IconoSeguimiento },
]

// Geometría del escenario (en px dentro de un lienzo de 1240 × 600).
const ANCHO = 1240
const ALTO = 600
const TARJETA = { x: 410, ancho: 420 }
const CENTROS_Y = [112, 300, 488]
const ENTRADAS_Y = [200, 300, 400]
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

function Trayectorias({ className }: { className?: string }) {
  const { lineas, cortes } = useMemo(() => {
    const r = azar(20260909)
    const pasos = 10
    const lineas: string[] = []
    const cortes: [number, number, number][] = []
    for (let i = 0; i < 24; i++) {
      let y = 30 + i * 13 + r() * 10
      const abandona = r() < 0.25
      const ultimo = abandona ? 3 + Math.floor(r() * 5) : pasos
      const puntos: string[] = []
      for (let k = 0; k <= ultimo; k++) {
        y += (r() - 0.5) * 14 + (abandona && k >= ultimo - 1 ? 16 : 0)
        puntos.push(`${((k / pasos) * 1200).toFixed(0)},${y.toFixed(1)}`)
      }
      lineas.push(puntos.join(' '))
      if (abandona) {
        const [x, yy] = puntos[puntos.length - 1].split(',').map(Number)
        cortes.push([x, yy, ultimo])
      }
    }
    return { lineas, cortes }
  }, [])
  return (
    <svg viewBox="0 0 1200 380" preserveAspectRatio="none" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="trayectoria" x1="0" x2="1">
          <stop offset="0" stopColor="rgb(var(--accent))" stopOpacity="0" />
          <stop offset="0.25" stopColor="rgb(var(--accent))" stopOpacity="0.3" />
          <stop offset="1" stopColor="rgb(var(--accent))" stopOpacity="0.16" />
        </linearGradient>
      </defs>
      {lineas.map((l, i) => (
        <polyline
          key={i}
          points={l}
          pathLength={1}
          className="apertura-trazo"
          style={{ animationDelay: `${(i % 6) * 80}ms` }}
          fill="none"
          stroke="url(#trayectoria)"
          strokeWidth="1.6"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      ))}
      {cortes.map(([x, y, paso], i) => (
        <g key={i} className="apertura-aparece" style={{ animationDelay: `${600 + paso * 130}ms` }}>
          <circle cx={x} cy={y} r="4" fill="var(--marca-medio)" />
        </g>
      ))}
    </svg>
  )
}

function TarjetaNodo({ nodo, lado, indice, className }: { nodo: Nodo; lado: 'izq' | 'der'; indice: number; className?: string }) {
  const I = nodo.icono
  return (
    <div
      className={cn(
        'apertura-nodo rounded-2xl border border-border bg-surface/80 p-4 shadow-tarjeta backdrop-blur-sm',
        lado === 'izq' ? 'text-right' : 'text-left',
        className
      )}
      style={{ animationDelay: `${900 + indice * 140 + (lado === 'der' ? 70 : 0)}ms` }}
    >
      <div className={cn('flex items-center gap-3', lado === 'izq' && 'flex-row-reverse')}>
        <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-marca/10 text-marca ring-1 ring-inset ring-marca/25">
          <I className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <p className="text-[15px] font-semibold tracking-tight text-foreground">{nodo.titulo}</p>
          <p className="text-xs text-marca">{nodo.tecnica}</p>
        </div>
      </div>
      <p className="mt-2 text-[13px] leading-snug text-muted-foreground">{nodo.texto}</p>
    </div>
  )
}

/** Trazas que unen cada nodo con la tarjeta, con pulsos de datos viajando al centro. */
function Trazas({ movimiento }: { movimiento: boolean }) {
  const trazas: { d: string; desde: [number, number]; hasta: [number, number] }[] = []
  CENTROS_Y.forEach((y, i) => {
    const xi = ANCHO_NODO + SANGRIA[i]
    const xe = TARJETA.x
    const ye = ENTRADAS_Y[i]
    trazas.push({ d: `M ${xi} ${y} C ${xi + 46} ${y}, ${xe - 46} ${ye}, ${xe} ${ye}`, desde: [xi, y], hasta: [xe, ye] })
    const xd = ANCHO - ANCHO_NODO - SANGRIA[i]
    const xc = TARJETA.x + TARJETA.ancho
    trazas.push({ d: `M ${xd} ${y} C ${xd - 46} ${y}, ${xc + 46} ${ye}, ${xc} ${ye}`, desde: [xd, y], hasta: [xc, ye] })
  })
  return (
    <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
      {trazas.map((t, i) => {
        const retraso = { animationDelay: `${1100 + i * 60}ms` }
        const dur = `${2.6 + (i % 3) * 0.5}s`
        const inicio = `${2.2 + i * 0.35}s`
        return (
          <g key={i} className="apertura-aparece" style={retraso}>
            <path id={`traza-${i}`} d={t.d} fill="none" stroke="rgb(var(--border-strong))" strokeWidth="1.4" strokeDasharray="3 4" />
            <circle cx={t.desde[0]} cy={t.desde[1]} r="3" fill="rgb(var(--accent))" />
            <circle cx={t.hasta[0]} cy={t.hasta[1]} r="3.5" fill="var(--marca-medio)" stroke="rgb(var(--surface))" strokeWidth="1.5" />
            {movimiento && (
              <circle r="3" fill="var(--marca-medio)" opacity="0">
                <animateMotion dur={dur} begin={inicio} repeatCount="indefinite" calcMode="linear">
                  <mpath href={`#traza-${i}`} />
                </animateMotion>
                <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.15;0.85;1" dur={dur} begin={inicio} repeatCount="indefinite" />
              </circle>
            )}
          </g>
        )
      })}
    </svg>
  )
}

export default function Ingresar() {
  const { ingresar, avisoSalida } = useSesion()
  const navegar = useNavigate()
  const { state } = useLocation() as { state?: { desde?: string } }
  const [usuario, setUsuario] = useState('')
  const [clave, setClave] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
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
    <section aria-labelledby="titulo-acceso" className="apertura-tarjeta w-full max-w-[420px] rounded-2xl border border-border bg-surface shadow-flotante">
      <div className="h-1 rounded-t-2xl bg-marca" aria-hidden="true" />
      <div className="flex items-center gap-3 border-b border-border px-7 py-5">
        <Logo className="h-11 w-11 drop-shadow-[0_8px_18px_var(--marca-sombra)]" />
        <div className="min-w-0">
          <h2 id="titulo-acceso" className="text-[17px] font-semibold tracking-tight text-foreground">
            Ingreso al sistema
          </h2>
          <p className="text-[13px] text-muted-foreground">Use la cuenta que le asignó Administración de TI.</p>
        </div>
      </div>
      <form onSubmit={enviar} noValidate className="space-y-5 px-7 py-6">
        {avisoSalida && !error && <Aviso tono="info">{avisoSalida}</Aviso>}
        {error && <Aviso tono="danger">{error}</Aviso>}
        <Campo etiqueta="Usuario">
          {(p) => (
            <Input {...p} autoComplete="username" autoFocus value={usuario} onChange={(e) => setUsuario(e.target.value)} placeholder="nombre.apellido" className="h-11 text-[15px]" />
          )}
        </Campo>
        <Campo etiqueta="Contraseña">
          {(p) => <Input {...p} type="password" autoComplete="current-password" value={clave} onChange={(e) => setClave(e.target.value)} className="h-11 text-[15px]" />}
        </Campo>
        <Button type="submit" size="lg" loading={enviando} className="w-full">
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </Button>
      </form>
      <p className="rounded-b-2xl bg-surface-sunken px-7 py-3.5 text-xs leading-relaxed text-muted-foreground">
        Cinco intentos fallidos bloquean la cuenta cinco minutos. Cada ingreso queda en la bitácora de auditoría.
      </p>
    </section>
  )

  return (
    <div className="relative flex min-h-[100dvh] flex-col overflow-hidden bg-background">
      <Trayectorias className="pointer-events-none absolute inset-x-0 bottom-0 h-[62%] w-full" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-marca" aria-hidden="true" />

      <header className="relative flex items-center justify-between gap-4 px-5 py-5 sm:px-10">
        <p className="text-[13px] font-semibold tracking-tight text-foreground">Universidad Estatal de Milagro</p>
        <p className="hidden text-[13px] text-muted-foreground sm:block">Ingeniería en Tecnologías de la Información</p>
      </header>

      <main className="relative flex flex-1 flex-col items-center justify-center px-4 pb-8">
        <div className="apertura-titulo mb-7 text-center">
          <h1 className="text-[34px] font-semibold tracking-tight text-foreground sm:text-[40px]">{NOMBRE_SISTEMA}</h1>
          <p className="mx-auto mt-1 max-w-md text-[15px] leading-relaxed text-muted-foreground">
            Alerta temprana del abandono estudiantil: quién está en riesgo, por qué y qué hacer a tiempo.
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
            {tarjeta}
          </div>
        </div>

        {/* Pantallas menores: tarjeta y, debajo, los nodos en rejilla. */}
        <div className="flex w-full flex-col items-center min-[1320px]:hidden">
          {tarjeta}
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
