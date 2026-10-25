/**
 * src/paginas/Seguimiento.tsx — registro de seguimiento de bienestar estudiantil (RF-09, HU-05).
 *
 * Cierra el ciclo alerta → acción → resultado: qué se hizo con cada estudiante en
 * riesgo, qué sigue abierto y con qué resultado se cerró.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { IconoSeguimiento } from '../componentes/iconos'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { DialogoCerrar } from '../componentes/seguimiento/Dialogos'
import { Badge } from '../componentes/ui/Badge'
import { BotonEnlace, Button } from '../componentes/ui/Button'
import { Card } from '../componentes/ui/Card'
import { Actualizando, EmptyState, EstadoError } from '../componentes/ui/Estados'
import { Kpi } from '../componentes/ui/Kpi'
import { Segmentado } from '../componentes/ui/Segmentado'
import { Skeleton } from '../componentes/ui/Skeleton'
import { Table, TableBody, TableHead, TableRow, Td, Th } from '../componentes/ui/Table'
import { useDatos } from '../lib/consultas'
import { entero, fechaHora } from '../lib/formato'
import { useSesion } from '../lib/sesion'
import type { Intervencion } from '../lib/tipos'

type Filtro = 'TODAS' | 'ABIERTA' | 'CERRADA'

export default function Seguimiento() {
  const { puede } = useSesion()
  const [filtro, setFiltro] = useState<Filtro>('TODAS')
  const [cerrar, setCerrar] = useState<number | null>(null)
  const { data, error, isLoading, isFetching, refetch } = useDatos<{ tipos: Record<string, string>; intervenciones: Intervencion[] }>(
    `/seguimiento${filtro === 'TODAS' ? '' : `?estado=${filtro}`}`,
    { mantenerAnterior: true }
  )
  const todas = useDatos<{ intervenciones: Intervencion[] }>('/seguimiento')
  const lista = todas.data?.intervenciones ?? []
  const abiertas = lista.filter((i) => i.estado === 'ABIERTA').length

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Seguimiento"
        descripcion="Acciones de acompañamiento registradas por bienestar estudiantil. Para registrar una nueva, abra la ficha del estudiante."
        acciones={
          <>
            <Actualizando activo={isFetching && !isLoading} />
            <BotonEnlace to="/estudiantes?riesgo=ALTO" variant="secondary">
              Ir a estudiantes en riesgo alto
            </BotonEnlace>
          </>
        }
      />
      <section className="mb-6 grid gap-4 sm:grid-cols-3">
        <Kpi etiqueta="Intervenciones registradas" valor={entero(lista.length)} icono={IconoSeguimiento} tono="accent" cargando={todas.isLoading} />
        <Kpi etiqueta="Abiertas" valor={entero(abiertas)} tono="warning" icono={IconoSeguimiento} contexto="esperan un resultado" cargando={todas.isLoading} />
        <Kpi etiqueta="Cerradas" valor={entero(lista.length - abiertas)} tono="success" icono={IconoSeguimiento} contexto="con resultado anotado" cargando={todas.isLoading} />
      </section>
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 sm:px-6">
          <Segmentado
            etiqueta="Estado"
            valor={filtro}
            onCambio={setFiltro}
            opciones={[
              { valor: 'TODAS', texto: 'Todas' },
              { valor: 'ABIERTA', texto: 'Abiertas' },
              { valor: 'CERRADA', texto: 'Cerradas' },
            ]}
          />
          <p className="text-xs text-muted-foreground">Se muestran las 300 más recientes.</p>
        </div>
        {isLoading ? (
          <div className="space-y-3 p-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : error ? (
          <EstadoError error={error} onReintentar={() => refetch()} />
        ) : !data?.intervenciones.length ? (
          <EmptyState
            icon={IconoSeguimiento}
            title={filtro === 'TODAS' ? 'Aún no hay intervenciones registradas' : 'No hay intervenciones con este estado'}
            description="Las intervenciones se registran desde la ficha de cada estudiante, junto a sus razones de riesgo."
            action={<BotonEnlace to="/estudiantes?riesgo=ALTO">Ver estudiantes en riesgo alto</BotonEnlace>}
          />
        ) : (
          <Table>
            <TableHead>
              <tr>
                <Th>Estudiante</Th>
                <Th>Intervención</Th>
                <Th>Estado</Th>
                <Th>Registro</Th>
                <Th className="text-right">Acción</Th>
              </tr>
            </TableHead>
            <TableBody>
              {data.intervenciones.map((i) => (
                <TableRow key={i.intervencion_id}>
                  <Td>
                    <Link to={`/estudiantes/${i.token}`} className="font-medium text-foreground hover:text-accent hover:underline">
                      {i.nombre}
                    </Link>
                    <p className="max-w-[240px] truncate text-xs text-muted-foreground">{i.carrera}</p>
                  </Td>
                  <Td className="max-w-[420px]">
                    <p className="font-medium">{i.tipo_descripcion}</p>
                    <p className="line-clamp-2 text-sm text-muted-foreground">{i.descripcion}</p>
                    {i.resultado && <p className="mt-0.5 text-sm text-success">Resultado: {i.resultado}</p>}
                  </Td>
                  <Td>
                    <Badge variant={i.estado === 'ABIERTA' ? 'warning' : 'success'} dot>
                      {i.estado === 'ABIERTA' ? 'Abierta' : 'Cerrada'}
                    </Badge>
                    {i.riesgo_al_registrar && <p className="mt-1 text-xs text-muted-foreground">riesgo {i.riesgo_al_registrar.toLowerCase()} al registrar</p>}
                  </Td>
                  <Td>
                    <p className="text-sm">{fechaHora(i.fecha_registro)}</p>
                    <p className="text-xs text-muted-foreground">{i.registrado_por}</p>
                  </Td>
                  <Td className="text-right">
                    {i.estado === 'ABIERTA' && puede('registrar_seguimiento') ? (
                      <Button variant="secondary" size="sm" onClick={() => setCerrar(i.intervencion_id)}>
                        Cerrar
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">{i.fecha_cierre ? fechaHora(i.fecha_cierre) : '—'}</span>
                    )}
                  </Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
      <DialogoCerrar abierto={cerrar !== null} onCerrar={() => setCerrar(null)} intervencionId={cerrar} />
    </div>
  )
}
