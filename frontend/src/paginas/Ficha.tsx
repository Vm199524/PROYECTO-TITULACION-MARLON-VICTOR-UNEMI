/**
 * src/paginas/Ficha.tsx — ficha del estudiante (RF-07, RF-08, RF-09; HU-03, HU-04).
 *
 * Reúne en una pantalla lo que bienestar estudiantil necesita para decidir una acción:
 * la probabilidad calibrada y su posición frente a los umbrales, las razones (aporte
 * de cada variable al riesgo, SHAP), las acciones sugeridas, un simulador «¿qué pasaría
 * si…?», la trayectoria periodo a periodo y el historial de seguimiento.
 */
import { useMutation } from '@tanstack/react-query'
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { IconoAlerta, IconoCheck, IconoSeguimiento, IconoSimular } from '../componentes/iconos'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { DialogoCerrar, DialogoRegistrar } from '../componentes/seguimiento/Dialogos'
import { Badge, BadgeRiesgo } from '../componentes/ui/Badge'
import { Button } from '../componentes/ui/Button'
import { Card, CardBody, CardHeader } from '../componentes/ui/Card'
import { Aviso, EmptyState, EstadoError } from '../componentes/ui/Estados'
import { Skeleton } from '../componentes/ui/Skeleton'
import { Table, TableBody, TableHead, TableRow, Td, Th } from '../componentes/ui/Table'
import { enviar } from '../lib/api'
import { cn } from '../lib/cn'
import { useDatos } from '../lib/consultas'
import { capital, decimal, entero, fecha, fechaHora, moneda, porcentaje, proporcion, texto } from '../lib/formato'
import { useSesion } from '../lib/sesion'
import type { Contribucion, FichaEstudiante, ResultadoSimulacion, Riesgo, VariableSimulable } from '../lib/tipos'

const GraficoTrayectoria = lazy(() => import('./ficha/GraficoTrayectoria'))

const TIPO_SUGERIDO: Record<string, string> = {
  ASISTENCIA: 'CONTACTO',
  RENDIMIENTO: 'TUTORIA',
  EVALUACIONES: 'TUTORIA',
  REPETICION: 'TUTORIA',
  ECONOMICO: 'APOYO_ECONOMICO',
  AULA_VIRTUAL: 'CONTACTO',
  CARGA: 'CONSEJERIA',
}
const TITULO_RECOMENDACION: Record<string, string> = {
  ASISTENCIA: 'Asistencia',
  RENDIMIENTO: 'Rendimiento académico',
  EVALUACIONES: 'Entregas y evaluaciones',
  REPETICION: 'Repetición de nivel',
  ECONOMICO: 'Situación económica',
  AULA_VIRTUAL: 'Participación en el aula virtual',
  CARGA: 'Carga académica',
  SEGUIMIENTO: 'Seguimiento regular',
}
const COLOR_RIESGO: Record<Riesgo, string> = { ALTO: 'text-danger', MEDIO: 'text-warning', BAJO: 'text-success' }

/** Escala de 0 a 100 % con las zonas de riesgo y el punto del estudiante. */
function EscalaRiesgo({ p, medio, alto }: { p: number; medio: number; alto: number }) {
  const pos = (v: number) => `${Math.min(100, Math.max(0, v * 100))}%`
  return (
    <div className="mt-6">
      <div className="relative h-2.5 rounded-full bg-success/25">
        <div className="absolute inset-y-0 rounded-r-full bg-warning/35" style={{ left: pos(medio), right: 0 }} />
        <div className="absolute inset-y-0 rounded-r-full bg-danger/45" style={{ left: pos(alto), right: 0 }} />
        <div
          className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-surface bg-foreground shadow-tarjeta"
          style={{ left: pos(p) }}
          aria-hidden="true"
        />
      </div>
      <div className="mt-2 flex justify-between text-2xs text-muted-foreground">
        <span>0 %</span>
        <span>100 %</span>
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <li className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-warning" aria-hidden="true" />
          Riesgo medio desde {proporcion(medio)}
        </li>
        <li className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-danger" aria-hidden="true" />
          Riesgo alto desde {proporcion(alto)}
        </li>
      </ul>
    </div>
  )
}

function Razones({ items }: { items: Contribucion[] }) {
  const max = Math.max(...items.map((i) => Math.abs(i.contribucion)), 1e-6)
  return (
    <ul className="space-y-3.5">
      {items.map((i) => {
        const sube = i.contribucion > 0
        return (
          <li key={i.variable}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="text-foreground">{capital(i.descripcion)}</span>
              <span className="tabular shrink-0 font-medium text-muted-foreground">{i.valor_texto ?? texto(i.valor)}</span>
            </div>
            <div className="mt-1.5 grid grid-cols-2 gap-0.5" aria-hidden="true">
              <div className="flex justify-end">
                {!sube && <div className="h-2 rounded-l-full bg-success" style={{ width: `${(100 * Math.abs(i.contribucion)) / max}%` }} />}
              </div>
              <div>{sube && <div className="h-2 rounded-r-full bg-danger" style={{ width: `${(100 * i.contribucion) / max}%` }} />}</div>
            </div>
            <p className="sr-only">{sube ? 'Aumenta el riesgo' : 'Reduce el riesgo'}</p>
          </li>
        )
      })}
    </ul>
  )
}

const RANGOS: Record<string, (actual: number) => { min: number; max: number; paso: number; formato: (v: number) => string }> = {
  promedio: () => ({ min: 0, max: 10, paso: 0.1, formato: (v) => decimal(v) }),
  asistencia_pct: () => ({ min: 0, max: 100, paso: 1, formato: (v) => porcentaje(v, false, 0) }),
  saldo_pendiente: (a) => ({ min: 0, max: Math.max(500, Math.ceil((a * 2) / 50) * 50), paso: 10, formato: (v) => moneda(v) }),
  actividad_lms: (a) => ({ min: 0, max: Math.max(300, Math.ceil(a * 3)), paso: 1, formato: (v) => entero(v) }),
  dias_sin_actividad: () => ({ min: 0, max: 90, paso: 1, formato: (v) => `${entero(v)} días` }),
  evaluaciones_entregadas: (a) => ({ min: 0, max: Math.max(12, Math.ceil(a)), paso: 1, formato: (v) => entero(v) }),
}

function Simulador({ token, simulables, actuales }: { token: string; simulables: Record<string, VariableSimulable>; actuales: Record<string, number | null> }) {
  const variables = useMemo(() => Object.keys(simulables).filter((k) => RANGOS[k] && actuales[k] != null), [simulables, actuales])
  const iniciales = useMemo(() => Object.fromEntries(variables.map((k) => [k, Number(actuales[k])])), [variables, actuales])
  const [valores, setValores] = useState<Record<string, number>>(iniciales)
  useEffect(() => setValores(iniciales), [iniciales])
  const cambios = Object.fromEntries(Object.entries(valores).filter(([k, v]) => v !== iniciales[k]))
  const m = useMutation({ mutationFn: () => enviar<ResultadoSimulacion>(`/estudiantes/${token}/simulacion`, { cambios }) })

  if (!variables.length) {
    return <p className="text-sm text-muted-foreground">El modelo de esta institución no tiene variables que se puedan simular para este estudiante.</p>
  }
  const r = m.data
  return (
    <div className="space-y-5">
      {variables.map((k) => {
        const rango = RANGOS[k](iniciales[k])
        const cambiado = valores[k] !== iniciales[k]
        return (
          <div key={k}>
            <div className="flex items-baseline justify-between gap-3">
              <label htmlFor={`sim-${k}`} className="text-sm font-medium text-foreground">
                {simulables[k].etiqueta}
              </label>
              <span className="tabular text-sm">
                {cambiado && <span className="mr-1.5 text-muted-foreground line-through">{rango.formato(iniciales[k])}</span>}
                <span className={cn('font-semibold', cambiado ? 'text-accent' : 'text-foreground')}>{rango.formato(valores[k])}</span>
              </span>
            </div>
            <input
              id={`sim-${k}`}
              type="range"
              min={rango.min}
              max={rango.max}
              step={rango.paso}
              value={valores[k]}
              onChange={(e) => {
                m.reset()
                setValores((v) => ({ ...v, [k]: Number(e.target.value) }))
              }}
              className="mt-2 w-full cursor-pointer accent-[rgb(var(--accent))]"
            />
          </div>
        )
      })}
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={() => m.mutate()} disabled={!Object.keys(cambios).length} loading={m.isPending}>
          <IconoSimular />
          Recalcular riesgo
        </Button>
        {Object.keys(cambios).length > 0 && (
          <Button variant="ghost" onClick={() => (setValores(iniciales), m.reset())}>
            Restablecer
          </Button>
        )}
      </div>
      {m.error && <Aviso tono="danger">{m.error.message}</Aviso>}
      {r && (
        <div className="entrada rounded-xl border border-border bg-surface-sunken p-4">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
            <div>
              <p className="text-xs text-muted-foreground">Ahora</p>
              <p className={cn('tabular text-xl font-semibold', COLOR_RIESGO[r.actual.categoria])}>{proporcion(r.actual.probabilidad)}</p>
            </div>
            <span className="text-muted-foreground" aria-hidden="true">
              →
            </span>
            <div>
              <p className="text-xs text-muted-foreground">Con los cambios</p>
              <p className={cn('tabular text-xl font-semibold', COLOR_RIESGO[r.simulado.categoria])}>{proporcion(r.simulado.probabilidad)}</p>
            </div>
            <div className="ml-auto text-right">
              <BadgeRiesgo riesgo={r.simulado.categoria} />
              <p className={cn('tabular mt-1 text-sm font-medium', r.diferencia_puntos <= 0 ? 'text-success' : 'text-danger')}>
                {r.diferencia_puntos > 0 ? '+' : ''}
                {decimal(r.diferencia_puntos, 1)} puntos
              </p>
            </div>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">{r.aviso}</p>
        </div>
      )}
    </div>
  )
}

function Esqueleto() {
  return (
    <div className="space-y-6" aria-busy="true">
      <Skeleton className="h-10 w-72" />
      <div className="grid gap-6 xl:grid-cols-[400px_minmax(0,1fr)]">
        <Skeleton className="h-[300px] rounded-2xl" />
        <Skeleton className="h-[300px] rounded-2xl" />
      </div>
      <Skeleton className="h-[320px] rounded-2xl" />
    </div>
  )
}

export default function Ficha() {
  const { token = '' } = useParams()
  const { puede } = useSesion()
  const { data: f, error, isLoading, refetch } = useDatos<FichaEstudiante>(`/estudiantes/${token}`)
  const [registrar, setRegistrar] = useState<{ tipo?: string } | null>(null)
  const [cerrar, setCerrar] = useState<number | null>(null)

  if (isLoading) return <Esqueleto />
  if (error || !f) return <Card><EstadoError error={error} onReintentar={() => refetch()} /></Card>

  const p = f.prediccion
  const nombre = f.nombre ?? 'Estudiante'
  const abiertas = f.seguimiento.filter((s) => s.estado === 'ABIERTA').length

  return (
    <div className="entrada">
      <EncabezadoPagina
        volver={{ href: '/estudiantes', texto: 'Estudiantes en riesgo' }}
        titulo={nombre}
        descripcion={
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>{f.carrera}</span>
            <span aria-hidden="true">·</span>
            <span>{f.sede}</span>
            <span aria-hidden="true">·</span>
            <span>{f.modalidad?.toLowerCase()}</span>
            <span aria-hidden="true">·</span>
            <span className="tabular">Cédula {f.cedula}</span>
          </span>
        }
        acciones={
          puede('registrar_seguimiento') && (
            <Button onClick={() => setRegistrar({})}>
              <IconoSeguimiento />
              Registrar intervención
            </Button>
          )
        }
      />

      {!p ? (
        <Aviso tono="info" titulo="Sin predicción vigente" className="mb-6">
          El estudiante no tiene matrícula activa en el último periodo calificado ({f.estado?.toLowerCase() ?? 'sin estado'}). Se muestra su trayectoria.
        </Aviso>
      ) : null}

      <div className="space-y-6">
        {p && (
          <div className="grid gap-6 xl:grid-cols-[400px_minmax(0,1fr)]">
            <Card>
              <CardHeader title="Riesgo de abandono" description={`Probabilidad de abandonar en el ${p.horizonte === 'PROXIMO_PERIODO' ? 'próximo periodo' : p.horizonte.toLowerCase()}.`} />
              <CardBody>
                <div className="flex items-end justify-between gap-4">
                  <p className={cn('tabular text-5xl font-semibold tracking-tight', COLOR_RIESGO[p.riesgo])}>{proporcion(p.probabilidad)}</p>
                  <BadgeRiesgo riesgo={p.riesgo} className="mb-2" />
                </div>
                <EscalaRiesgo p={p.probabilidad} medio={p.umbral_medio} alto={p.umbral_alto} />
                <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-border pt-5 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Posición en la institución</dt>
                    <dd className="mt-0.5 font-medium text-foreground">{p.percentil >= 99 ? 'En el 1 % de mayor riesgo' : `Más riesgo que el ${porcentaje(p.percentil, false, 0)}`}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Seguimiento</dt>
                    <dd className="mt-0.5 font-medium text-foreground">{abiertas ? `${abiertas} intervención abierta` : f.seguimiento.length ? 'Sin intervenciones abiertas' : 'Sin intervenciones'}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Calculado</dt>
                    <dd className="mt-0.5 font-medium text-foreground">{fechaHora(p.fecha_calculo)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Versión del modelo</dt>
                    <dd className="mt-0.5 font-medium text-foreground">{p.modelo_version}</dd>
                  </div>
                </dl>
              </CardBody>
            </Card>
            <Card>
              <CardHeader
                title="Por qué tiene este riesgo"
                description="Aporte de cada dato del estudiante a la estimación: en rojo lo que lo aumenta y en verde lo que lo reduce."
              />
              <CardBody>
                {f.explicacion.length ? <Razones items={f.explicacion} /> : <p className="text-sm text-muted-foreground">Sin detalle disponible.</p>}
              </CardBody>
            </Card>
          </div>
        )}

        {p && (
          <div className="grid gap-6 xl:grid-cols-2">
            <Card>
              <CardHeader title="Acciones sugeridas" description="Reglas de acompañamiento según las razones del riesgo. La decisión es siempre de bienestar estudiantil." />
              <CardBody>
                {f.recomendaciones.length ? (
                  <ul className="space-y-3">
                    {f.recomendaciones.map((r, i) => (
                      <li key={i} className="flex gap-3 rounded-xl border border-border p-4">
                        <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
                          <IconoCheck className="h-4 w-4" />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-foreground">{TITULO_RECOMENDACION[r.tipo] ?? r.tipo}</p>
                          <p className="mt-0.5 text-sm text-muted-foreground">{r.texto}</p>
                          {r.motivo && <p className="mt-1.5 text-xs text-subtle-foreground">Motivo: {r.motivo}</p>}
                        </div>
                        {puede('registrar_seguimiento') && TIPO_SUGERIDO[r.tipo] && (
                          <Button variant="ghost" size="sm" onClick={() => setRegistrar({ tipo: TIPO_SUGERIDO[r.tipo] })}>
                            Registrar
                          </Button>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState icon={IconoCheck} title="Sin acciones sugeridas" description="El riesgo del estudiante es bajo: basta el seguimiento regular." className="py-8" />
                )}
              </CardBody>
            </Card>
            {puede('simular') && (
              <Card>
                <CardHeader title="¿Qué pasaría si…?" description="Mueva los valores del periodo actual y recalcule el riesgo con el mismo modelo." />
                <CardBody>
                  <Simulador token={token} simulables={f.simulables} actuales={f.valores_actuales} />
                </CardBody>
              </Card>
            )}
          </div>
        )}

        <Card>
          <CardHeader title="Trayectoria académica" description="Promedio y asistencia de cada periodo cursado." />
          <CardBody className="space-y-6">
            <Suspense fallback={<Skeleton className="h-[260px]" />}>
              <GraficoTrayectoria filas={f.trayectoria} />
            </Suspense>
          </CardBody>
          <Table>
            <TableHead>
              <tr>
                <Th>Periodo</Th>
                <Th numero>Nivel</Th>
                <Th>Estado</Th>
                <Th numero>Promedio</Th>
                <Th numero>Asistencia</Th>
                <Th numero>Saldo</Th>
                <Th numero>Aula virtual</Th>
                <Th numero>Entregas</Th>
              </tr>
            </TableHead>
            <TableBody>
              {[...f.trayectoria].reverse().map((t) => (
                <TableRow key={`${t.periodo_academico}-${t.corte}`}>
                  <Td>
                    <span className="font-medium">{t.periodo_academico}</span>
                    {t.corte > 1 && <span className="text-muted-foreground"> · corte {t.corte}</span>}
                    <p className="text-xs text-muted-foreground">{fecha(t.fecha_corte)}</p>
                  </Td>
                  <Td numero>
                    {t.nivel}
                    {t.numero_matricula && t.numero_matricula > 1 ? <span className="ml-1 text-xs text-warning">({t.numero_matricula}.ª vez)</span> : null}
                  </Td>
                  <Td>
                    <Badge variant={t.estado_matricula === 'RETIRADO' ? 'danger' : t.estado_matricula === 'ACTIVO' ? 'neutral' : 'success'}>
                      {t.estado_matricula.charAt(0) + t.estado_matricula.slice(1).toLowerCase()}
                    </Badge>
                  </Td>
                  <Td numero className={cn(t.promedio != null && t.promedio < 7 && 'text-danger')}>{decimal(t.promedio)}</Td>
                  <Td numero className={cn(t.asistencia_pct != null && t.asistencia_pct < 70 && 'text-danger')}>{porcentaje(t.asistencia_pct)}</Td>
                  <Td numero>{t.saldo_pendiente ? moneda(t.saldo_pendiente) : '—'}</Td>
                  <Td numero>{t.actividad_lms != null ? `${entero(t.actividad_lms)} interacciones` : '—'}</Td>
                  <Td numero>{t.evaluaciones_entregadas != null && t.evaluaciones_vencidas ? `${entero(t.evaluaciones_entregadas)} de ${entero(t.evaluaciones_vencidas)}` : '—'}</Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>

        <Card>
          <CardHeader title="Historial de seguimiento" description="Intervenciones de bienestar estudiantil con este estudiante." />
          <CardBody>
            {f.seguimiento.length === 0 ? (
              <EmptyState
                icon={IconoAlerta}
                title="Aún no hay intervenciones"
                description={puede('registrar_seguimiento') ? 'Registre la primera acción de acompañamiento desde «Registrar intervención».' : 'Bienestar estudiantil todavía no registra acciones.'}
                className="py-8"
              />
            ) : (
              <ol className="relative space-y-5 border-l border-border pl-6">
                {f.seguimiento.map((s) => (
                  <li key={s.intervencion_id} className="relative">
                    <span
                      className={cn('absolute -left-[31px] top-1 h-3.5 w-3.5 rounded-full border-2 border-surface', s.estado === 'ABIERTA' ? 'bg-warning' : 'bg-success')}
                      aria-hidden="true"
                    />
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-foreground">{s.tipo_descripcion ?? s.tipo.replace('_', ' ').toLowerCase()}</p>
                      <Badge variant={s.estado === 'ABIERTA' ? 'warning' : 'success'}>{s.estado === 'ABIERTA' ? 'Abierta' : 'Cerrada'}</Badge>
                      {s.riesgo_al_registrar && <span className="text-xs text-muted-foreground">riesgo al registrar: {s.riesgo_al_registrar.toLowerCase()}</span>}
                    </div>
                    <p className="mt-1 text-sm text-foreground/90">{s.descripcion}</p>
                    {s.resultado && <p className="mt-1 text-sm text-success">Resultado: {s.resultado}</p>}
                    <p className="mt-1 text-xs text-muted-foreground">
                      {fechaHora(s.fecha_registro)} · {s.registrado_por}
                      {s.fecha_cierre ? ` · cerrada el ${fechaHora(s.fecha_cierre)}` : ''}
                    </p>
                    {s.estado === 'ABIERTA' && puede('registrar_seguimiento') && (
                      <Button variant="secondary" size="sm" className="mt-2" onClick={() => setCerrar(s.intervencion_id)}>
                        Cerrar con resultado
                      </Button>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </CardBody>
        </Card>
      </div>

      {registrar && (
        <DialogoRegistrar abierto onCerrar={() => setRegistrar(null)} token={token} nombre={nombre} tipoSugerido={registrar.tipo} />
      )}
      <DialogoCerrar abierto={cerrar !== null} onCerrar={() => setCerrar(null)} intervencionId={cerrar} />
    </div>
  )
}
