/**
 * src/paginas/Carreras.tsx — segmentación de carreras por perfil de riesgo (RF-11, HU-07).
 *
 * Agrupa las carreras con K-means según su abandono histórico, rendimiento, asistencia
 * y riesgo actual, para priorizar recursos por carrera. La validación (silhouette,
 * estabilidad, Kruskal-Wallis y comparación con otros algoritmos) se muestra con una
 * lectura en lenguaje llano.
 */
import { lazy, Suspense } from 'react'
import { IconoCarreras } from '../componentes/iconos'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { Badge, type VarianteBadge } from '../componentes/ui/Badge'
import { BotonEnlace } from '../componentes/ui/Button'
import { Card, CardBody, CardHeader } from '../componentes/ui/Card'
import { EmptyState, EstadoError } from '../componentes/ui/Estados'
import { Skeleton } from '../componentes/ui/Skeleton'
import { Table, TableBody, TableHead, TableRow, Td, Th } from '../componentes/ui/Table'
import { useDatos } from '../lib/consultas'
import { decimal, entero, porcentaje, proporcion } from '../lib/formato'
import type { Segmentacion } from '../lib/tipos'

const MapaCarreras = lazy(() => import('./carreras/MapaCarreras'))

export const VARIANTE_SEGMENTO: Record<string, VarianteBadge> = {
  'Atención prioritaria': 'danger',
  Estable: 'warning',
  'Bajo riesgo': 'success',
}
const DESCRIPCION_SEGMENTO: Record<string, string> = {
  'Atención prioritaria': 'Mayor abandono histórico o más estudiantes en riesgo hoy: conviene reforzar tutorías y apoyo.',
  Estable: 'Indicadores intermedios: mantener el seguimiento y vigilar su evolución.',
  'Bajo riesgo': 'Menor abandono y mejor rendimiento: sus prácticas pueden servir de referencia.',
}

function Validacion({ v }: { v: Segmentacion['validacion'] }) {
  const sil = v.silhouette
  const ari = v.estabilidad?.ari_medio
  const kw = v.kruskal_wallis
  const filas = [
    {
      nombre: 'Separación de los grupos (silhouette)',
      valor: decimal(sil, 3),
      lectura:
        sil == null ? '—' : sil >= 0.5 ? 'Grupos bien separados.' : sil >= 0.25 ? 'Separación razonable: los grupos se distinguen, con carreras en la frontera.' : 'Separación débil: tómese como orientación.',
    },
    {
      nombre: 'Estabilidad al remuestrear (ARI)',
      valor: decimal(ari, 3),
      lectura: ari == null ? '—' : ari >= 0.6 ? 'Los grupos se repiten casi siempre.' : 'Algunas carreras cambian de grupo según la muestra: revisar las de frontera.',
    },
    {
      nombre: 'Diferencia real de abandono entre grupos (Kruskal-Wallis)',
      valor: kw ? `p = ${decimal(kw.p, 4)}` : '—',
      lectura: kw ? (kw.p < 0.05 ? 'La tasa de abandono difiere entre segmentos (no es azar).' : 'Las tasas no difieren de forma significativa.') : '—',
    },
  ]
  return (
    <Card>
      <CardHeader title="¿Qué tan sólida es la agrupación?" description={`${entero(v.unidades)} carreras en ${entero(v.k)} segmentos con K-means.`} />
      <CardBody className="space-y-4 pt-4">
        {filas.map((f) => (
          <div key={f.nombre} className="border-b border-border pb-4 last:border-0 last:pb-0">
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-[13px] font-medium text-foreground">{f.nombre}</p>
              <p className="tabular text-[13px] font-semibold text-foreground">{f.valor}</p>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{f.lectura}</p>
          </div>
        ))}
        {v.comparacion_algoritmos && (
          <div>
            <p className="mb-2 text-[13px] font-medium text-foreground">Comparación con otros algoritmos</p>
            <ul className="space-y-1 text-xs text-muted-foreground">
              {Object.entries(v.comparacion_algoritmos).map(([k, a]) => (
                <li key={k} className="flex justify-between gap-3">
                  <span>{k === 'KMEANS' ? 'K-means (elegido)' : k === 'JERARQUICO_WARD' ? 'Jerárquico de Ward' : 'HDBSCAN'}</span>
                  <span className="tabular">
                    {a.clusteres} grupos{a.ruido ? ` · ${a.ruido} sin grupo` : ''} · silhouette {decimal(a.silhouette, 3)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardBody>
    </Card>
  )
}

export default function Carreras() {
  const { data, error, isLoading, refetch } = useDatos<Segmentacion>('/carreras/segmentos')

  if (isLoading)
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-32 rounded-2xl" />
          ))}
        </div>
        <Skeleton className="h-[420px] rounded-2xl" />
      </div>
    )

  const carreras = data?.carreras ?? []
  const segmentos = ['Atención prioritaria', 'Estable', 'Bajo riesgo'].map((s) => {
    const del = carreras.filter((c) => c.segmento === s)
    const estudiantes = del.reduce((a, c) => a + c.estudiantes, 0)
    return {
      nombre: s,
      carreras: del.length,
      enRiesgo: del.reduce((a, c) => a + c.activos_en_riesgo, 0),
      tasa: estudiantes ? del.reduce((a, c) => a + c.tasa_abandono_hist * c.estudiantes, 0) / estudiantes : null,
    }
  })

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Carreras"
        descripcion="Las carreras se agrupan por su perfil de abandono, rendimiento, asistencia y riesgo actual para decidir dónde reforzar el acompañamiento."
      />
      {error ? (
        <Card>
          <EstadoError error={error} onReintentar={() => refetch()} />
        </Card>
      ) : !carreras.length ? (
        <Card>
          <EmptyState icon={IconoCarreras} title="La segmentación aún no se ha calculado" description="Ejecute el proceso de segmentación para esta institución." />
        </Card>
      ) : (
        <div className="space-y-6">
          <section className="grid gap-4 md:grid-cols-3" aria-label="Segmentos">
            {segmentos.map((s) => (
              <Card key={s.nombre} className="p-5">
                <div className="flex items-center justify-between gap-3">
                  <Badge variant={VARIANTE_SEGMENTO[s.nombre]} dot>
                    {s.nombre}
                  </Badge>
                  <span className="tabular text-[13px] text-muted-foreground">{entero(s.carreras)} carreras</span>
                </div>
                <p className="tabular mt-3 text-[26px] font-semibold tracking-tight text-foreground">{proporcion(s.tasa)}</p>
                <p className="text-xs text-muted-foreground">abandono histórico ponderado · {entero(s.enRiesgo)} activos en riesgo</p>
                <p className="mt-3 text-[13px] text-muted-foreground">{DESCRIPCION_SEGMENTO[s.nombre]}</p>
              </Card>
            ))}
          </section>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
            <Card>
              <CardHeader title="Mapa de carreras" description="Cada punto es una carrera: abandono histórico frente al riesgo promedio de sus estudiantes activos. El tamaño indica el número de estudiantes." />
              <CardBody>
                <Suspense fallback={<Skeleton className="h-[360px]" />}>
                  <MapaCarreras carreras={carreras} />
                </Suspense>
              </CardBody>
            </Card>
            <Validacion v={data!.validacion} />
          </div>

          <Card className="overflow-hidden">
            <CardHeader title="Detalle por carrera" description="Ordenado por segmento y abandono histórico." className="pb-4" />
            <Table>
              <TableHead>
                <tr>
                  <Th>Carrera</Th>
                  <Th>Segmento</Th>
                  <Th numero>Estudiantes</Th>
                  <Th numero>Abandono histórico</Th>
                  <Th numero>Promedio</Th>
                  <Th numero>Asistencia</Th>
                  <Th numero>Riesgo promedio</Th>
                  <Th numero>Activos en riesgo</Th>
                  <Th />
                </tr>
              </TableHead>
              <TableBody>
                {carreras.map((c) => (
                  <TableRow key={c.carrera}>
                    <Td>
                      <p className="font-medium">{c.carrera}</p>
                      <p className="max-w-[300px] truncate text-xs text-muted-foreground">{c.facultad_nombre}</p>
                    </Td>
                    <Td>
                      <Badge variant={VARIANTE_SEGMENTO[c.segmento] ?? 'neutral'}>{c.segmento}</Badge>
                    </Td>
                    <Td numero>{entero(c.estudiantes)}</Td>
                    <Td numero>{proporcion(c.tasa_abandono_hist)}</Td>
                    <Td numero>{decimal(c.promedio_hist)}</Td>
                    <Td numero>{porcentaje(c.asistencia_hist)}</Td>
                    <Td numero>{proporcion(c.riesgo_promedio)}</Td>
                    <Td numero>{entero(c.activos_en_riesgo)}</Td>
                    <Td className="text-right">
                      <BotonEnlace to={`/estudiantes?carrera=${encodeURIComponent(c.carrera)}`} variant="ghost" size="sm">
                        Ver estudiantes
                      </BotonEnlace>
                    </Td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </div>
      )}
    </div>
  )
}
