/**
 * src/paginas/Consulta.tsx — consulta conversacional en lenguaje natural (RF-10, HU-06).
 *
 * La autoridad pregunta en español y recibe la cifra, un gráfico o una tabla con un
 * resumen que solo cita valores del resultado. Cada respuesta dice de dónde salió:
 * una métrica certificada (SQL fijo), una consulta generada con IA y validada, o una
 * barrera de seguridad. La lectura con IA es opcional y se verifica contra las cifras.
 */
import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { IconoChispa, IconoCodigo, IconoConsulta, IconoDescargar, IconoEnviar, IconoReloj } from '../componentes/iconos'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { Marca } from '../componentes/marca/Logo'
import { Badge } from '../componentes/ui/Badge'
import { Button } from '../componentes/ui/Button'
import { Card, CardBody, CardHeader } from '../componentes/ui/Card'
import { Aviso } from '../componentes/ui/Estados'
import { useToast } from '../componentes/ui/Toast'
import { descargar, enviar } from '../lib/api'
import { cn } from '../lib/cn'
import { useDatos } from '../lib/consultas'
import { entero } from '../lib/formato'
import { useSesion } from '../lib/sesion'
import type { Interpretacion, RespuestaConsulta } from '../lib/tipos'
import { Resultado, TextoConNegritas } from './consulta/Resultado'

interface Turno {
  pregunta: string
  respuesta?: RespuestaConsulta
  error?: string
}

const ORIGEN: Record<string, { texto: string; variante: 'success' | 'info' | 'warning' | 'neutral' | 'danger'; ayuda: string }> = {
  CERTIFICADA: { texto: 'Métrica certificada', variante: 'success', ayuda: 'Consulta fija revisada por el equipo; la IA no interviene en la cifra.' },
  GENERADA_IA: { texto: 'Generada con IA y validada', variante: 'info', ayuda: 'La IA propuso la consulta; el sistema la validó (solo lectura, vistas autorizadas) antes de ejecutarla.' },
  BARRERA: { texto: 'Barrera de seguridad', variante: 'warning', ayuda: 'La pregunta no se ejecuta contra la base de datos.' },
  SIN_RESPUESTA: { texto: 'Sin respuesta', variante: 'neutral', ayuda: 'No se encontró cómo responder con los datos disponibles.' },
  ERROR: { texto: 'Error', variante: 'danger', ayuda: 'La base de datos rechazó la consulta.' },
}

function Interpretar({ id }: { id: string }) {
  const m = useMutation({ mutationFn: () => enviar<Interpretacion>(`/consulta/${id}/interpretar`) })
  if (!m.data && !m.error) {
    return (
      <Button variant="ghost" size="sm" onClick={() => m.mutate()} loading={m.isPending}>
        <IconoChispa />
        Interpretar con IA
      </Button>
    )
  }
  if (m.error) return <Aviso tono="warning">{m.error.message}</Aviso>
  const d = m.data!
  if (!d.texto) return <Aviso tono="warning">{d.motivo ?? 'La interpretación no está disponible ahora.'}</Aviso>
  return (
    <div className="w-full rounded-xl border border-accent/20 bg-accent-soft px-4 py-3 text-sm leading-relaxed text-foreground">
      <div className="mb-1.5 flex flex-wrap items-center gap-2">
        <IconoChispa className="h-4 w-4 text-accent" />
        <span className="text-xs font-semibold text-accent">Lectura con IA</span>
        {d.verificada ? <Badge variant="success">Cifras verificadas</Badge> : <Badge variant="warning">Sin verificar</Badge>}
      </div>
      {d.texto}
      {d.proveedor && <p className="mt-2 text-2xs text-muted-foreground">{d.proveedor}{d.modelo ? ` · ${d.modelo}` : ''}</p>}
    </div>
  )
}

function Respuesta({ r, onPreguntar }: { r: RespuestaConsulta; onPreguntar: (p: string) => void }) {
  const { puede } = useSesion()
  const toast = useToast()
  const [verSql, setVerSql] = useState(false)
  const o = ORIGEN[r.origen] ?? ORIGEN.SIN_RESPUESTA
  const conDatos = r.columnas.length > 0
  return (
    <div className="space-y-4 rounded-2xl border border-border bg-surface p-5 shadow-tarjeta">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={o.variante} dot title={o.ayuda}>
          {o.texto}
        </Badge>
        {r.titulo && <p className="text-md font-semibold tracking-tight text-foreground">{r.titulo}</p>}
      </div>
      {r.explicacion && (
        <p className="text-md leading-relaxed text-muted-foreground">
          <TextoConNegritas texto={r.explicacion} />
        </p>
      )}
      <Resultado r={r} />
      {r.advertencias.map((a) => (
        <Aviso key={a} tono="warning">
          {a}
        </Aviso>
      ))}
      {r.sugerencias && (
        <div className="flex flex-wrap gap-2">
          {Object.values(r.sugerencias)
            .flat()
            .slice(0, 6)
            .map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onPreguntar(s)}
                className="rounded-full border border-border bg-surface px-3 py-1.5 text-sm text-foreground hover:border-accent/50 hover:bg-accent-soft"
              >
                {s}
              </button>
            ))}
        </div>
      )}
      {conDatos && (
        <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
          <Interpretar id={r.id} />
          {puede('exportar') && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => descargar(`/consulta/${r.id}/excel`, 'consulta.xlsx').catch((e) => toast('error', e.message))}
            >
              <IconoDescargar />
              Excel
            </Button>
          )}
          {r.sql && (
            <Button variant="ghost" size="sm" onClick={() => setVerSql((v) => !v)} aria-expanded={verSql}>
              <IconoCodigo />
              {verSql ? 'Ocultar SQL' : 'Ver SQL'}
            </Button>
          )}
          <span className="ml-auto inline-flex items-center gap-1 text-2xs text-muted-foreground">
            <IconoReloj className="h-3.5 w-3.5" />
            {entero(r.tiempo_ms)} ms{r.proveedor ? ` · ${r.proveedor}` : ''}
          </span>
        </div>
      )}
      {verSql && r.sql && (
        <pre className="overflow-x-auto rounded-xl bg-sidebar p-4 text-xs leading-relaxed text-sidebar-foreground">
          <code>{r.sql}</code>
        </pre>
      )}
    </div>
  )
}

export default function Consulta() {
  const { institucion } = useSesion()
  const { data: sugerencias } = useDatos<Record<string, string[]>>('/consulta/sugerencias')
  const [turnos, setTurnos] = useState<Turno[]>([])
  const [texto, setTexto] = useState('')
  const final = useRef<HTMLDivElement>(null)
  const entrada = useRef<HTMLTextAreaElement>(null)

  // Una conversación pertenece a una institución: al cambiarla se empieza de cero.
  useEffect(() => setTurnos([]), [institucion?.codigo])

  const m = useMutation({
    mutationFn: (pregunta: string) =>
      enviar<RespuestaConsulta>('/consulta', {
        pregunta,
        historial: turnos.filter((t) => t.respuesta).slice(-4).map((t) => ({ pregunta: t.pregunta, titulo: t.respuesta?.titulo })),
      }),
    onSuccess: (r) => setTurnos((ts) => ts.map((t, i) => (i === ts.length - 1 ? { ...t, respuesta: r } : t))),
    onError: (e) => setTurnos((ts) => ts.map((t, i) => (i === ts.length - 1 ? { ...t, error: e.message } : t))),
  })

  useEffect(() => {
    if (turnos.length) final.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [turnos])

  function preguntar(p: string) {
    const limpia = p.trim()
    if (!limpia || m.isPending) return
    setTurnos((ts) => [...ts, { pregunta: limpia }])
    setTexto('')
    m.mutate(limpia)
    entrada.current?.focus({ preventScroll: true })
  }

  function teclado(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      preguntar(texto)
    }
  }

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Consulta conversacional"
        descripcion="Pregunte en español sobre el riesgo, la matrícula, las carreras o el modelo. Las respuestas se calculan con los datos de la institución activa, en modo de solo lectura."
        acciones={
          turnos.length > 0 && (
            <Button variant="secondary" onClick={() => setTurnos([])}>
              Nueva conversación
            </Button>
          )
        }
      />
      <div className="grid gap-6 xl:items-start xl:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="flex min-h-[560px] flex-col">
          <div className="flex-1 space-y-6 p-5 sm:p-6" aria-live="polite">
            {turnos.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center py-12 text-center">
                <Marca tamano="lg" className="justify-center" />
                <p className="mt-6 max-w-md text-sm text-muted-foreground">
                  Por ejemplo: «¿Qué carreras tienen más estudiantes en riesgo?» o «¿Cuántos estudiantes abandonaron cada año?»
                </p>
              </div>
            ) : (
              turnos.map((t, i) => (
                <div key={i} className="space-y-3">
                  <div className="flex justify-end">
                    <p className="max-w-[85%] rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-md text-accent-foreground">{t.pregunta}</p>
                  </div>
                  {t.respuesta ? (
                    <Respuesta r={t.respuesta} onPreguntar={preguntar} />
                  ) : t.error ? (
                    <Aviso tono="danger">{t.error}</Aviso>
                  ) : (
                    <div className="escribiendo flex items-center gap-1.5 px-2 py-3 text-muted-foreground" role="status" aria-label="Consultando">
                      <span className="h-2 w-2 rounded-full bg-current" />
                      <span className="h-2 w-2 rounded-full bg-current" />
                      <span className="h-2 w-2 rounded-full bg-current" />
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={final} />
          </div>
          <form
            className="sticky bottom-0 border-t border-border bg-surface/95 p-4 backdrop-blur sm:p-5"
            onSubmit={(e) => {
              e.preventDefault()
              preguntar(texto)
            }}
          >
            <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface px-3 py-2 focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/15">
              <label htmlFor="pregunta" className="sr-only">
                Escriba su pregunta
              </label>
              <textarea
                id="pregunta"
                ref={entrada}
                rows={1}
                maxLength={500}
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                onKeyDown={teclado}
                placeholder="Escriba su pregunta…"
                className="max-h-40 min-h-[40px] flex-1 resize-none bg-transparent py-2 text-md text-foreground placeholder:text-subtle-foreground focus:outline-none"
              />
              <Button type="submit" size="icon" disabled={!texto.trim()} loading={m.isPending} aria-label="Enviar pregunta">
                {!m.isPending && <IconoEnviar />}
              </Button>
            </div>
            <p className="mt-2 text-2xs text-muted-foreground">Enter envía · Mayúsculas + Enter agrega una línea · Las cédulas se muestran enmascaradas.</p>
          </form>
        </Card>

        <aside className="space-y-6">
          <Card>
            <CardHeader title="Preguntas frecuentes" description="Toque una para enviarla." />
            <CardBody className="space-y-5 pt-4">
              {sugerencias ? (
                Object.entries(sugerencias).map(([tema, lista]) => (
                  <div key={tema}>
                    <p className="mb-2 text-sm font-semibold text-foreground">{tema}</p>
                    <ul className="space-y-1">
                      {lista.map((s) => (
                        <li key={s}>
                          <button
                            type="button"
                            disabled={m.isPending}
                            onClick={() => preguntar(s)}
                            className="w-full rounded-lg px-2.5 py-1.5 text-left text-sm text-muted-foreground hover:bg-surface-hover hover:text-foreground disabled:opacity-50"
                          >
                            {s}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">Cargando…</p>
              )}
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Cómo se responde" />
            <CardBody className="space-y-3 pt-4 text-sm text-muted-foreground">
              {(['CERTIFICADA', 'GENERADA_IA', 'BARRERA'] as const).map((k) => (
                <div key={k} className="flex gap-2.5">
                  <IconoConsulta className={cn('mt-0.5 h-4 w-4 shrink-0', k === 'CERTIFICADA' ? 'text-success' : k === 'GENERADA_IA' ? 'text-info' : 'text-warning')} />
                  <p>
                    <span className="font-medium text-foreground">{ORIGEN[k].texto}.</span> {ORIGEN[k].ayuda}
                  </p>
                </div>
              ))}
            </CardBody>
          </Card>
        </aside>
      </div>
    </div>
  )
}
