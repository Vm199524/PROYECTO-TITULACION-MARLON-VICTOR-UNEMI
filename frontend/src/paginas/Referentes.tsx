/**
 * src/paginas/Referentes.tsx — tasa de abandono propia frente a referentes publicados (RF-12).
 *
 * Compara pares con pares: cada referente muestra su definición del indicador, su
 * país, modalidad y nivel de comparabilidad, con la fuente y el DOI.
 */
import { IconoEnlace, IconoReferentes } from '../componentes/iconos'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { Badge, BadgeDatos } from '../componentes/ui/Badge'
import { Card, CardBody, CardHeader } from '../componentes/ui/Card'
import { Aviso, EmptyState, EstadoError } from '../componentes/ui/Estados'
import { Skeleton } from '../componentes/ui/Skeleton'
import { cn } from '../lib/cn'
import { useDatos } from '../lib/consultas'
import { entero, porcentaje } from '../lib/formato'
import type { Referentes as TipoReferentes } from '../lib/tipos'

const COMPARABILIDAD = {
  ALTA: { variante: 'success' as const, texto: 'Comparabilidad alta', ayuda: 'Mismo país o sistema y definición equivalente.' },
  MEDIA: { variante: 'warning' as const, texto: 'Comparabilidad media', ayuda: 'Definición parecida en otro contexto.' },
  BAJA: { variante: 'neutral' as const, texto: 'Comparabilidad baja', ayuda: 'Otra modalidad o definición: solo como contexto.' },
}

export default function Referentes() {
  const { data, error, isLoading, refetch } = useDatos<TipoReferentes>('/referentes')

  if (isLoading) return <Skeleton className="h-[480px] rounded-2xl" />
  if (error || !data) return <Card><EstadoError error={error} onReintentar={() => refetch()} /></Card>

  const filas = [
    ...(data.propia.tasa != null
      ? [{ id: 'propia', nombre: data.propia.institucion?.nombre ?? 'Institución activa', valor: data.propia.tasa, propia: true, nivel: null as null | 'ALTA' | 'MEDIA' | 'BAJA' }]
      : []),
    ...data.referentes.map((r) => ({ id: r.referente_codigo, nombre: r.nombre, valor: r.valor, propia: false, nivel: r.nivel_comparabilidad })),
  ].sort((a, b) => b.valor - a.valor)
  const max = Math.max(...filas.map((f) => f.valor), 1)

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Referentes externos"
        descripcion="La tasa de abandono de la institución activa junto a las publicadas en estudios con revisión de pares. Las definiciones no siempre coinciden: lea el nivel de comparabilidad antes de sacar conclusiones."
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card>
          <CardHeader title="Tasa de abandono" description="Porcentaje de trayectorias que terminan en abandono." />
          <CardBody>
            {filas.length === 0 ? (
              <EmptyState icon={IconoReferentes} title="Sin referentes cargados" description="Ejecute el proceso de referentes externos." />
            ) : (
              <ul className="space-y-4">
                {filas.map((f) => (
                  <li key={f.id}>
                    <div className="flex items-baseline justify-between gap-3 text-sm">
                      <span className={cn('min-w-0 truncate', f.propia ? 'font-semibold text-foreground' : 'text-foreground')}>
                        {f.nombre}
                        {f.propia && <span className="ml-2 text-xs font-normal text-accent">institución activa</span>}
                      </span>
                      <span className="tabular shrink-0 font-semibold text-foreground">{porcentaje(f.valor)}</span>
                    </div>
                    <div className="mt-1.5 h-3 overflow-hidden rounded-full bg-surface-hover">
                      <div
                        className={cn('h-full rounded-full', f.propia && 'bg-accent')}
                        style={{
                          width: `${(100 * f.valor) / max}%`,
                          backgroundColor: f.propia ? undefined : f.nivel === 'ALTA' ? 'rgb(var(--chart-2))' : f.nivel === 'MEDIA' ? 'rgb(var(--subtle-foreground) / 0.75)' : 'rgb(var(--subtle-foreground) / 0.4)',
                        }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Cómo se calcula la tasa propia" />
          <CardBody className="space-y-4 pt-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <BadgeDatos tipo={data.propia.institucion?.tipo_datos} />
            </div>
            <p>{data.propia.definicion}</p>
            <p className="tabular text-foreground">
              {entero(data.propia.retirados)} retiros de {entero(data.propia.cerrados)} trayectorias cerradas.
            </p>
            {data.propia.institucion?.tipo_datos === 'SINTETICO' && (
              <Aviso tono="warning">Con datos sintéticos la comparación ilustra el funcionamiento del sistema; no describe a la UNEMI.</Aviso>
            )}
          </CardBody>
        </Card>
      </div>

      <h2 className="mb-3 mt-8 text-md font-semibold tracking-tight text-foreground">Fuentes</h2>
      <div className="grid gap-4 md:grid-cols-2">
        {data.referentes.map((r) => {
          const comp = COMPARABILIDAD[r.nivel_comparabilidad] ?? COMPARABILIDAD.BAJA
          return (
            <Card key={r.referente_codigo} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="text-md font-semibold text-foreground">{r.nombre}</p>
                <Badge variant={comp.variante} title={comp.ayuda}>
                  {comp.texto}
                </Badge>
              </div>
              <p className="tabular mt-2 text-2xl font-semibold text-foreground">{porcentaje(r.valor)}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {r.pais} · {r.modalidad.toLowerCase()}
                {r.anio ? ` · ${r.anio}` : ''}
              </p>
              <p className="mt-3 text-sm text-muted-foreground">{r.definicion_indicador}</p>
              <p className="mt-3 text-xs text-foreground/80">{r.fuente}</p>
              {(r.doi || r.url_fuente) && (
                <a
                  href={r.doi ? `https://doi.org/${r.doi.replace(/^https?:\/\/doi\.org\//, '')}` : r.url_fuente!}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
                >
                  {r.doi ? `DOI ${r.doi.replace(/^https?:\/\/doi\.org\//, '')}` : 'Ver fuente'}
                  <IconoEnlace className="h-3.5 w-3.5" />
                </a>
              )}
            </Card>
          )
        })}
      </div>
    </div>
  )
}
