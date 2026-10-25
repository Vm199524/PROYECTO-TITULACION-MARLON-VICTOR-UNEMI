/**
 * src/paginas/admin/Estado.tsx — estado del sistema para Administración de TI.
 *
 * Por institución: datos cargados, estudiantes calificados, modelo vigente y deriva.
 * Además, el resultado de la última corrida de los procesos por lotes, las cuentas de
 * base de datos de mínimo privilegio y los proveedores de IA configurados.
 */
import { IconoActualizar, IconoBaseDatos, IconoChispa, IconoEstado } from '../../componentes/iconos'
import { EncabezadoPagina } from '../../componentes/layout/EncabezadoPagina'
import { Badge, BadgeDatos } from '../../componentes/ui/Badge'
import { Button } from '../../componentes/ui/Button'
import { Card, CardBody, CardHeader } from '../../componentes/ui/Card'
import { Aviso, EmptyState, EstadoError } from '../../componentes/ui/Estados'
import { Skeleton } from '../../componentes/ui/Skeleton'
import { Table, TableBody, TableHead, TableRow, Td, Th } from '../../componentes/ui/Table'
import { cn } from '../../lib/cn'
import { useDatos } from '../../lib/consultas'
import { decimal, entero, fecha, fechaHora } from '../../lib/formato'
import { NOMBRE_MODELO } from '../../lib/modelos'
import type { EstadoSistema } from '../../lib/tipos'

const ESTADO_PASO: Record<string, { variante: 'success' | 'danger' | 'warning' | 'neutral' | 'info'; texto: string }> = {
  OK: { variante: 'success', texto: 'Correcto' },
  ERROR: { variante: 'danger', texto: 'Error' },
  EN_CURSO: { variante: 'info', texto: 'En curso' },
  PENDIENTE: { variante: 'warning', texto: 'Pendiente' },
  OMITIDO: { variante: 'neutral', texto: 'Omitido' },
}

export default function Estado() {
  const { data, error, isLoading, isFetching, refetch } = useDatos<EstadoSistema>('/admin/estado')

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Estado del sistema"
        descripcion="Carga de datos, modelo y calificación de cada institución, y la última corrida de los procesos por lotes."
        acciones={
          <Button variant="secondary" onClick={() => refetch()} loading={isFetching}>
            {!isFetching && <IconoActualizar />}
            Actualizar
          </Button>
        }
      />
      {isLoading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-60 rounded-2xl" />
          <Skeleton className="h-60 rounded-2xl" />
        </div>
      ) : error || !data ? (
        <Card>
          <EstadoError error={error} onReintentar={() => refetch()} />
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {data.instituciones.map((i) => (
              <Card key={i.codigo}>
                <CardHeader
                  title={i.nombre}
                  description={i.codigo}
                  actions={
                    <div className="flex items-center gap-2">
                      <BadgeDatos tipo={i.tipo_datos} />
                      {i.cargada ? <Badge variant="success" dot>Cargada</Badge> : <Badge variant="warning" dot>Sin datos</Badge>}
                    </div>
                  }
                />
                <CardBody className="pt-4">
                  {i.error && <Aviso tono="danger" className="mb-4">{i.error}</Aviso>}
                  <dl className="grid grid-cols-2 gap-4 text-sm">
                    {[
                      ['Estudiantes', entero(i.estudiantes)],
                      ['Filas de trayectoria', entero(i.filas)],
                      ['Último corte', fecha(i.ultimo_corte)],
                      ['Calificados', entero(i.calificados)],
                      ['Calificación', fechaHora(i.fecha_calificacion)],
                      ['Modelo', i.modelo ? `${NOMBRE_MODELO[i.modelo.nombre] ?? i.modelo.nombre} v${i.modelo.version}` : '—'],
                      ['ROC-AUC temporal', decimal(i.modelo?.roc_auc_temporal, 3)],
                      ['Entrenado', fechaHora(i.modelo?.fecha)],
                    ].map(([k, v]) => (
                      <div key={k}>
                        <dt className="text-muted-foreground">{k}</dt>
                        <dd className="tabular mt-0.5 font-medium text-foreground">{v}</dd>
                      </div>
                    ))}
                  </dl>
                  {i.deriva && i.deriva.length > 0 && (
                    <Aviso tono="warning" className="mt-4" titulo="Deriva detectada">
                      {i.deriva.map((d) => `${d.variable} (PSI ${decimal(d.psi, 3)})`).join(', ')}. Considere reentrenar el modelo.
                    </Aviso>
                  )}
                </CardBody>
              </Card>
            ))}
          </div>

          <Card className="overflow-hidden">
            <CardHeader
              title="Procesos por lotes"
              description={
                data.procesos
                  ? `Última corrida: ${fechaHora(data.procesos.inicio)}${data.procesos.fin ? ` → ${fechaHora(data.procesos.fin)}` : ''} · ${data.procesos.resultado.toLowerCase().replace('_', ' ')}`
                  : 'Aún no se ha ejecutado scripts/pipeline.py en este equipo.'
              }
              className="pb-4"
            />
            {data.procesos?.pasos?.length ? (
              <Table>
                <TableHead>
                  <tr>
                    <Th>Paso</Th>
                    <Th>Estado</Th>
                    <Th numero>Duración</Th>
                    <Th>Detalle</Th>
                  </tr>
                </TableHead>
                <TableBody>
                  {data.procesos.pasos.map((p, n) => {
                    const e = ESTADO_PASO[p.estado] ?? ESTADO_PASO.OMITIDO
                    return (
                      <TableRow key={p.paso}>
                        <Td>
                          <span className="tabular mr-2 text-xs text-subtle-foreground">{String(n + 1).padStart(2, '0')}</span>
                          {p.descripcion}
                        </Td>
                        <Td>
                          <Badge variant={e.variante} dot>
                            {e.texto}
                          </Badge>
                        </Td>
                        <Td numero>{p.segundos != null ? `${decimal(p.segundos, 1)} s` : '—'}</Td>
                        <Td className="max-w-[420px] text-xs text-muted-foreground">
                          <p className="line-clamp-2">{p.detalle || '—'}</p>
                        </Td>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            ) : (
              <EmptyState icon={IconoEstado} title="Sin registro de procesos" description="Ejecute: cd backend && python -m scripts.pipeline" className="py-10" />
            )}
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader title="Cuentas de base de datos" description="Mínimo privilegio: la aplicación nunca usa la cuenta de administración." />
              <CardBody className="space-y-3 pt-4">
                {[
                  ['chat_reader', 'Solo lectura de las vistas VIS_*', data.cuentas_bd.lectura_configurada],
                  ['app_seguimiento', 'Solo ejecuta los dos procedimientos de seguimiento', data.cuentas_bd.seguimiento_configurado],
                ].map(([n, d, ok]) => (
                  <div key={String(n)} className="flex items-center gap-3 rounded-xl border border-border p-3">
                    <IconoBaseDatos className={cn('h-5 w-5', ok ? 'text-success' : 'text-danger')} />
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-sm text-foreground">{String(n)}</p>
                      <p className="text-xs text-muted-foreground">{String(d)}</p>
                    </div>
                    {ok ? <Badge variant="success">Configurada</Badge> : <Badge variant="danger">Falta en .env</Badge>}
                  </div>
                ))}
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Proveedores de IA" description="Cascada para preguntas fuera de las métricas certificadas; se usa el primero disponible." />
              <CardBody className="space-y-3 pt-4">
                {data.proveedores_ia.map((p, n) => (
                  <div key={p.nombre} className="flex items-center gap-3 rounded-xl border border-border p-3">
                    <IconoChispa className={cn('h-5 w-5', p.configurado ? 'text-accent' : 'text-subtle-foreground')} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground">
                        {n + 1}. {p.nombre}
                      </p>
                      <p className="truncate font-mono text-xs text-muted-foreground">{p.modelo}</p>
                    </div>
                    {p.configurado ? <Badge variant="success">Con llave</Badge> : <Badge>Sin llave</Badge>}
                  </div>
                ))}
              </CardBody>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
