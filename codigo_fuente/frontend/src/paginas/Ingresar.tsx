/**
 * src/paginas/Ingresar.tsx — acceso al sistema (RF-01 autenticación).
 *
 * Dos columnas desde 1024 px: a la izquierda la marca y lo que el sistema resuelve;
 * a la derecha el formulario. Un solo envío por clic y el error se muestra una vez.
 */
import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { IconoCheck } from '../componentes/iconos'
import { Marca } from '../componentes/marca/Logo'
import { Button } from '../componentes/ui/Button'
import { Aviso } from '../componentes/ui/Estados'
import { Campo, Input } from '../componentes/ui/Input'
import { useSesion } from '../lib/sesion'

const BENEFICIOS = [
  'Riesgo de abandono de cada estudiante activo, con las razones que lo explican.',
  'Preguntas en español respondidas con cifras de la base institucional.',
  'Datos protegidos: solo lectura, cédulas enmascaradas y bitácora de accesos.',
]

export default function Ingresar() {
  const { ingresar, avisoSalida } = useSesion()
  const navegar = useNavigate()
  const { state } = useLocation() as { state?: { desde?: string } }
  const [usuario, setUsuario] = useState('')
  const [clave, setClave] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

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

  return (
    <div className="grid min-h-[100dvh] lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <section className="relative hidden overflow-hidden bg-sidebar px-12 py-12 text-sidebar-foreground lg:flex lg:flex-col xl:px-16">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            backgroundImage:
              'radial-gradient(36rem 26rem at 0% 0%, rgba(27,139,187,0.28), transparent 60%), radial-gradient(30rem 22rem at 110% 105%, rgba(255,122,26,0.14), transparent 60%)',
          }}
        />
        <div className="relative">
          <Marca tono="claro" tamano="md" />
        </div>
        <div className="relative my-auto max-w-lg py-12">
          <h1 className="text-[34px] font-semibold leading-[1.15] tracking-tight xl:text-[40px]">
            Detecte a tiempo a quien está por dejar la universidad.{' '}
            <span className="text-sidebar-active-foreground">Y acompáñelo antes de que se vaya.</span>
          </h1>
          <ul className="mt-10 space-y-4">
            {BENEFICIOS.map((b) => (
              <li key={b} className="flex gap-3 text-[15px] leading-relaxed text-sidebar-muted">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sidebar-active text-sidebar-active-foreground">
                  <IconoCheck className="h-3.5 w-3.5" />
                </span>
                {b}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs leading-relaxed text-sidebar-muted">
          Proyecto de titulación · Ingeniería en Tecnologías de la Información
          <br />
          Universidad Estatal de Milagro · Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco · 2026
        </p>
      </section>

      <section className="fondo-corporativo flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="entrada w-full max-w-[400px]">
          <div className="mb-8 lg:hidden">
            <Marca tamano="md" />
          </div>
          <h2 className="text-2xl font-semibold tracking-tight text-foreground">Ingresar</h2>
          <p className="mt-1 text-sm text-muted-foreground">Use la cuenta que le asignó el área de Administración de TI.</p>

          <form onSubmit={enviar} noValidate className="mt-8 space-y-5">
            {avisoSalida && !error && <Aviso tono="info">{avisoSalida}</Aviso>}
            {error && <Aviso tono="danger">{error}</Aviso>}
            <Campo etiqueta="Usuario">
              {(p) => (
                <Input
                  {...p}
                  autoComplete="username"
                  autoFocus
                  value={usuario}
                  onChange={(e) => setUsuario(e.target.value)}
                  placeholder="nombre.apellido"
                  className="h-11 text-[15px]"
                />
              )}
            </Campo>
            <Campo etiqueta="Contraseña">
              {(p) => (
                <Input
                  {...p}
                  type="password"
                  autoComplete="current-password"
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  className="h-11 text-[15px]"
                />
              )}
            </Campo>
            <Button type="submit" size="lg" loading={enviando} className="w-full">
              {enviando ? 'Ingresando…' : 'Ingresar'}
            </Button>
          </form>
          <p className="mt-8 text-xs leading-relaxed text-muted-foreground">
            Tras cinco intentos fallidos la cuenta se bloquea cinco minutos. Cada ingreso queda registrado en la bitácora de auditoría.
          </p>
        </div>
      </section>
    </div>
  )
}
