/**
 * src/paginas/Panel.tsx — panel ejecutivo de la autoridad académica (RF-05, HU-01).
 *
 * Responde, en una sola pantalla y sin vocabulario técnico: cuántos estudiantes están
 * en riesgo, en qué carreras, a quién atender primero, cómo evoluciona el abandono y
 * cuánto confiar en las alertas. Todas las cifras llegan agregadas del backend.
 */
import { lazy, Suspense } from 'react'
import { Link } from 'react-router-dom'
import { IconoAlerta, IconoDerecha, IconoDescargar, IconoEstudiantes, IconoSeguimiento, IconoTendencia } from '../componentes/iconos'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { Badge } from '../componentes/ui/Badge'
import { Barra } from '../componentes/ui/Barra'
import { BotonEnlace, Button } from '../componentes/ui/Button'
import { Card, CardBody, CardHeader } from '../componentes/ui/Card'
import { EmptyState, EstadoError } from '../componentes/ui/Estados'
import { Kpi } from '../componentes/ui/Kpi'
import { Skeleton } from '../componentes/ui/Skeleton'
import { useToast } from '../componentes/ui/Toast'
import { descargar } from '../lib/api'
import { useDatos } from '../lib/consultas'
import { entero, fechaHora, porcentaje, primerNombre, proporcion, saludo } from '../lib/formato'
import { useSesion } from '../lib/sesion'
import { NOMBRE_MODELO } from '../lib/modelos'
import type { ResumenPanel } from '../lib/tipos'

const GraficoCarreras = lazy(() => import('./panel/GraficoCarreras'))
const GraficoTendencia = lazy(() => import('./panel/GraficoTendencia'))

function Confiabilidad({ c }: { c: ResumenPanel['confiabilidad'] }) {
  const recall = c.RECALL_MEDIO
  const precision = c.PRECISION_MEDIO
  const filas = [
    {
      titulo: 'Abandonos que el sistema anticipa',
      valor: proporcion(recall, 0),
      barra: (recall ?? 0) * 100,
      lectura: recall != null ? `De cada 10 estudiantes que abandonaron, ${Math.round(recall * 10)} tenían alerta (media o alta).` : null,
    },
    {
      titulo: 'Alertas que resultaron en abandono',
      valor: proporcion(precision, 0),
      barra: (precision ?? 0) * 100,
      lectura: precision != null ? 'El resto son estudiantes con señales de riesgo que no llegaron a irse: igual merecen un contacto.' : null,
    },
    {
      titulo: 'Abandonos concentrados en el 10 % de mayor riesgo',
      valor: proporcion(c.CAPTURA_TOP_10, 0),
      barra: (c.CAPTURA_TOP_10 ?? 0) * 100,
      lectura: 'Atender primero a ese 10 % alcanza a esta proporción de quienes se irían.',
    },
  ]
  return (
    <Card>
      <CardHeader
        title="¿Cuánto confiar en las alertas?"
        description="Medido con periodos que el modelo no vio al entrenar (validación temporal)."
        actions={
          <Link to="/modelo" className="text-[13px] font-medium text-accent hover:underline">
            Detalle
          </Link>
        }
      />
      <CardBody className="space-y-5">
        {filas.map((f) => (
          <div key={f.titulo}>
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-[13px] font-medium text-foreground">{f.titulo}</p>
              <p className="tabular text-[15px] font-semibold text-foreground">{f.valor}</p>
            </div>
            <Barra valor={f.barra} etiqueta={f.titulo} className="mt-2" />
            {f.lectura && <p className="mt-1.5 text-xs text-muted-foreground">{f.lectura}</p>}
          </div>
        ))}
        <p className="border-t border-border pt-4 text-xs text-muted-foreground">
          Capacidad de distinguir quién abandona (ROC-AUC): <span className="tabular font-semibold text-foreground">{c.ROC_AUC != null ? c.ROC_AUC.toFixed(3).replace('.', ',') : '—'}</span>{' '}
          · 0,5 sería azar y 1 sería perfecto.
        </p>
      </CardBody>
    </Card>
  )
}

function Alertas({ datos }: { datos: ResumenPanel }) {
  return (
    <Card className="flex flex-col">
      <CardHeader
        title="Atender primero"
        description="Estudiantes con la probabilidad de abandono más alta."
        actions={
          <Link to="/estudiantes?riesgo=ALTO" className="text-[13px] font-medium text-accent hover:underline">
            Ver todos
          </Link>
        }
      />
      <CardBody className="flex-1 pt-3">
        {datos.alertas.length === 0 ? (
          <EmptyState icon={IconoAlerta} title="Sin estudiantes en riesgo alto" description="La última calificación no marcó a nadie por encima del umbral alto." className="py-8" />
        ) : (
          <ul className="-mx-2 divide-y divide-border">
            {datos.alertas.map((a) => (
              <li key={a.token}>
                <Link to={`/estudiantes/${a.token}`} className="group flex items-center gap-3 rounded-lg px-2 py-3 hover:bg-surface-hover">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13.5px] font-medium text-foreground">{a.nombre}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {a.carrera}
                      {a.factor ? ` · ${a.factor}` : ''}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="tabular text-[15px] font-semibold text-danger">{proporcion(a.probabilidad, 0)}</p>
                    <p className="text-2xs text-muted-foreground">probabilidad</p>
                  </div>
                  <IconoDerecha className="h-4 w-4 text-subtle-foreground group-hover:text-foreground" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  )
}

function Esqueleto() {
  return (
    <div className="space-y-6" aria-busy="true">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i} className="p-5">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="mt-4 h-8 w-2/3" />
            <Skeleton className="mt-3 h-3 w-3/4" />
          </Card>
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <Skeleton className="h-[380px] rounded-2xl" />
        <Skeleton className="h-[380px] rounded-2xl" />
      </div>
    </div>
  )
}

export default function Panel() {
  const { perfil, puede } = useSesion()
  const toast = useToast()
  const { data, error, isLoading, refetch } = useDatos<ResumenPanel>('/panel/resumen')

  const ind = data?.indicadores
  const pct = (n: number) => (ind?.evaluados ? (100 * n) / ind.evaluados : null)
  const tendencia = data?.tendencia ?? []
  const ultimo = tendencia.length > 1 ? tendencia[tendencia.length - 1] : null
  const previo = tendencia.length > 1 ? tendencia[tendencia.length - 2] : null

  async function reporte() {
    try {
      await descargar('/reportes/ejecutivo.pdf', 'alerta_temprana.pdf')
      toast('exito', 'Reporte ejecutivo descargado.')
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'No se pudo generar el reporte.')
    }
  }

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo={`${saludo()}, ${primerNombre(perfil?.nombre || perfil?.usuario)}`}
        descripcion={
          data?.calificacion.fecha ? (
            <>
              Riesgo de abandono para el próximo periodo, calculado el {fechaHora(data.calificacion.fecha)} con{' '}
              {NOMBRE_MODELO[data.calificacion.modelo ?? ''] ?? data.calificacion.modelo ?? 'el modelo vigente'}.
            </>
          ) : (
            'Resumen del riesgo de abandono de la institución activa.'
          )
        }
        acciones={
          <>
            {puede('exportar') && (
              <Button variant="secondary" onClick={reporte}>
                <IconoDescargar />
                Reporte PDF
              </Button>
            )}
            <BotonEnlace to="/estudiantes?riesgo=ALTO,MEDIO">
              <IconoEstudiantes />
              Ver estudiantes en riesgo
            </BotonEnlace>
          </>
        }
      />

      {isLoading ? (
        <Esqueleto />
      ) : error ? (
        <Card>
          <EstadoError error={error} onReintentar={() => refetch()} />
        </Card>
      ) : !data || !ind || ind.evaluados === 0 ? (
        <Card>
          <EmptyState
            title="Todavía no hay estudiantes calificados"
            description="Ejecute los procesos por lotes (ETL, entrenamiento y calificación) para esta institución. El área de TI puede verlos en Estado del sistema."
          />
        </Card>
      ) : (
        <div className="space-y-6">
          <section aria-label="Indicadores clave" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <Kpi etiqueta="Estudiantes evaluados" valor={entero(ind.evaluados)} icono={IconoEstudiantes} tono="accent" contexto="activos con predicción vigente" />
            <Kpi
              etiqueta="Riesgo alto"
              valor={entero(ind.alto)}
              icono={IconoAlerta}
              tono="danger"
              contexto={`${porcentaje(pct(ind.alto))} de los evaluados`}
            />
            <Kpi
              etiqueta="Riesgo medio"
              valor={entero(ind.medio)}
              icono={IconoAlerta}
              tono="warning"
              contexto={`${porcentaje(pct(ind.medio))} de los evaluados`}
            />
            <Kpi
              etiqueta="Abandono histórico"
              valor={porcentaje(ind.tasa_abandono_hist)}
              icono={IconoTendencia}
              variacion={ultimo && previo ? ultimo.tasa - previo.tasa : null}
              invertir
              contexto={ultimo ? `último periodo: ${porcentaje(ultimo.tasa)}` : 'de las trayectorias cerradas'}
            />
            <Kpi
              etiqueta="Riesgo alto con seguimiento"
              valor={porcentaje(ind.cobertura_alto)}
              icono={IconoSeguimiento}
              tono={ind.cobertura_alto != null && ind.cobertura_alto >= 50 ? 'success' : 'warning'}
              contexto={`${entero(ind.intervenciones_abiertas)} intervenciones abiertas`}
            />
          </section>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
            <Card>
              <CardHeader
                title="Estudiantes en riesgo por carrera"
                description="Carreras con más estudiantes en riesgo alto y medio."
                actions={
                  data.indicadores.carreras_prioritarias > 0 ? (
                    <Link to="/carreras">
                      <Badge variant="danger">{entero(data.indicadores.carreras_prioritarias)} carreras en atención prioritaria</Badge>
                    </Link>
                  ) : null
                }
              />
              <CardBody>
                <Suspense fallback={<Skeleton className="h-[340px]" />}>
                  <GraficoCarreras datos={data.riesgo_por_carrera} />
                </Suspense>
              </CardBody>
            </Card>
            <Alertas datos={data} />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
            <Card>
              <CardHeader title="Abandono por periodo académico" description="Estudiantes matriculados y retiros registrados en cada periodo." />
              <CardBody>
                <Suspense fallback={<Skeleton className="h-[300px]" />}>
                  <GraficoTendencia datos={tendencia} />
                </Suspense>
              </CardBody>
            </Card>
            <Confiabilidad c={data.confiabilidad} />
          </div>
        </div>
      )}
    </div>
  )
}
