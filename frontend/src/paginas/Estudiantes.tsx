/**
 * src/paginas/Estudiantes.tsx — lista priorizada de estudiantes activos (RF-06, HU-02).
 *
 * Ordenada por probabilidad de abandono, con filtros por nivel de riesgo, carrera y
 * nombre. Cada estudiante se abre por un enlace cifrado (nunca por su cédula) y la
 * cédula se muestra enmascarada. En pantallas angostas la tabla pasa a tarjetas.
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { IconoBuscar, IconoDerecha, IconoEstudiantes } from '../componentes/iconos'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { BadgeRiesgo } from '../componentes/ui/Badge'
import { Card } from '../componentes/ui/Card'
import { Actualizando, EmptyState, EstadoError } from '../componentes/ui/Estados'
import { Input, Select } from '../componentes/ui/Input'
import { Paginacion } from '../componentes/ui/Paginacion'
import { Segmentado } from '../componentes/ui/Segmentado'
import { Skeleton } from '../componentes/ui/Skeleton'
import { Table, TableBody, TableHead, TableRow, Td, Th } from '../componentes/ui/Table'
import { cn } from '../lib/cn'
import { useDatos } from '../lib/consultas'
import { capital, decimal, entero, porcentaje, proporcion } from '../lib/formato'
import type { ListaEstudiantes, Riesgo } from '../lib/tipos'

type FiltroRiesgo = 'ALTO,MEDIO' | 'ALTO' | 'MEDIO' | 'BAJO' | 'TODOS'
const OPCIONES: { valor: FiltroRiesgo; texto: string }[] = [
  { valor: 'ALTO,MEDIO', texto: 'En riesgo' },
  { valor: 'ALTO', texto: 'Alto' },
  { valor: 'MEDIO', texto: 'Medio' },
  { valor: 'BAJO', texto: 'Bajo' },
  { valor: 'TODOS', texto: 'Todos' },
]
const COLOR_RIESGO: Record<Riesgo, string> = { ALTO: 'bg-danger', MEDIO: 'bg-warning', BAJO: 'bg-success' }

export function Probabilidad({ valor, riesgo, className }: { valor: number; riesgo: Riesgo; className?: string }) {
  return (
    <div className={cn('flex items-center justify-end gap-2.5', className)}>
      <div className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-surface-hover md:block" aria-hidden="true">
        <div className={cn('h-full rounded-full', COLOR_RIESGO[riesgo])} style={{ width: `${Math.max(3, valor * 100)}%` }} />
      </div>
      <span className="tabular w-12 text-right font-semibold">{proporcion(valor, 1)}</span>
    </div>
  )
}

function useDemorado(valor: string, ms = 350) {
  const [v, setV] = useState(valor)
  useEffect(() => {
    const t = setTimeout(() => setV(valor), ms)
    return () => clearTimeout(t)
  }, [valor, ms])
  return v
}

export default function Estudiantes() {
  const [params, setParams] = useSearchParams()
  const navegar = useNavigate()
  const riesgo = (params.get('riesgo') as FiltroRiesgo) || 'ALTO,MEDIO'
  const carrera = params.get('carrera') ?? ''
  const pagina = Number(params.get('pagina') ?? '1') || 1
  const [buscar, setBuscar] = useState(params.get('buscar') ?? '')
  const buscarDemorado = useDemorado(buscar)

  function cambiar(cambios: Record<string, string | null>) {
    const p = new URLSearchParams(params)
    for (const [k, v] of Object.entries(cambios)) {
      if (v) p.set(k, v)
      else p.delete(k)
    }
    if (!('pagina' in cambios)) p.delete('pagina')
    setParams(p, { replace: true })
  }

  useEffect(() => {
    if ((params.get('buscar') ?? '') !== buscarDemorado) cambiar({ buscar: buscarDemorado || null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buscarDemorado])

  const consulta = new URLSearchParams({ orden: 'probabilidad', pagina: String(pagina), tamano: '25' })
  if (riesgo !== 'TODOS') consulta.set('riesgo', riesgo)
  if (carrera) consulta.set('carrera', carrera)
  if (buscarDemorado) consulta.set('buscar', buscarDemorado)
  const { data, error, isLoading, isFetching, refetch } = useDatos<ListaEstudiantes>(`/estudiantes?${consulta}`, { mantenerAnterior: true })

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Estudiantes en riesgo"
        descripcion="Estudiantes con matrícula vigente ordenados por la probabilidad de abandonar en el próximo periodo. Abra un estudiante para ver por qué tiene ese riesgo y qué acciones se sugieren."
        acciones={<Actualizando activo={isFetching && !isLoading} />}
        extra={
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <Segmentado etiqueta="Nivel de riesgo" opciones={OPCIONES} valor={riesgo} onCambio={(v) => cambiar({ riesgo: v })} />
            <div className="flex flex-1 flex-col gap-3 sm:flex-row">
              <Select aria-label="Carrera" value={carrera} onChange={(e) => cambiar({ carrera: e.target.value || null })} className="sm:max-w-xs">
                <option value="">Todas las carreras</option>
                {data?.carreras.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
              <div className="relative sm:max-w-xs sm:flex-1">
                <IconoBuscar className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle-foreground" />
                <Input aria-label="Buscar por apellidos o nombres" placeholder="Buscar por apellidos o nombres" value={buscar} onChange={(e) => setBuscar(e.target.value)} className="pl-9" />
              </div>
            </div>
          </div>
        }
      />

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="space-y-3 p-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : error ? (
          <EstadoError error={error} onReintentar={() => refetch()} />
        ) : !data || data.estudiantes.length === 0 ? (
          <EmptyState
            icon={IconoEstudiantes}
            title="No hay estudiantes con estos filtros"
            description="Pruebe con otro nivel de riesgo, otra carrera o borre la búsqueda."
          />
        ) : (
          <>
            {/* Tabla desde 768 px */}
            <div className="hidden md:block">
              <Table>
                <TableHead>
                  <tr>
                    <Th>Estudiante</Th>
                    <Th>Carrera</Th>
                    <Th numero>Promedio</Th>
                    <Th numero>Asistencia</Th>
                    <Th numero>Probabilidad</Th>
                    <Th>Nivel</Th>
                    <Th>Principales razones</Th>
                  </tr>
                </TableHead>
                <TableBody>
                  {data.estudiantes.map((e) => (
                    <TableRow key={e.token} className="cursor-pointer" onClick={() => navegar(`/estudiantes/${e.token}`)}>
                      <Td>
                        <Link to={`/estudiantes/${e.token}`} onClick={(ev) => ev.stopPropagation()} className="font-medium text-foreground hover:text-accent hover:underline">
                          {e.nombre}
                        </Link>
                        <p className="tabular text-xs text-muted-foreground">{e.cedula}</p>
                      </Td>
                      <Td>
                        <p className="max-w-[220px] truncate">{e.carrera}</p>
                        <p className="text-xs text-muted-foreground">
                          Nivel {e.nivel} · {e.periodo}
                        </p>
                      </Td>
                      <Td numero>{decimal(e.promedio)}</Td>
                      <Td numero>{porcentaje(e.asistencia)}</Td>
                      <Td numero>
                        <Probabilidad valor={e.probabilidad} riesgo={e.riesgo} />
                      </Td>
                      <Td>
                        <BadgeRiesgo riesgo={e.riesgo} corto />
                      </Td>
                      <Td className="max-w-[320px]">
                        <p className="line-clamp-2 text-sm text-muted-foreground">{capital(e.factores.slice(0, 2).join(' · ')) || '—'}</p>
                      </Td>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {/* Tarjetas en pantallas angostas */}
            <ul className="divide-y divide-border md:hidden">
              {data.estudiantes.map((e) => (
                <li key={e.token}>
                  <Link to={`/estudiantes/${e.token}`} className="flex items-start gap-3 px-4 py-4 hover:bg-surface-hover">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">{e.nombre}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {e.carrera} · Nivel {e.nivel}
                      </p>
                      <div className="mt-2 flex items-center gap-2">
                        <BadgeRiesgo riesgo={e.riesgo} corto />
                        <span className="truncate text-xs text-muted-foreground">{capital(e.factores[0])}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="tabular text-base font-semibold text-foreground">{proporcion(e.probabilidad, 0)}</p>
                      <IconoDerecha className="ml-auto mt-1 h-4 w-4 text-subtle-foreground" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
            <Paginacion pagina={data.pagina} tamano={data.tamano} total={data.total} onCambio={(p) => cambiar({ pagina: String(p) })} />
          </>
        )}
      </Card>
      {data && (
        <p className="mt-3 text-xs text-muted-foreground">
          {entero(data.total)} estudiantes con este filtro. La probabilidad está calibrada: 30 % significa que, de cada 10 estudiantes con ese valor, unos 3 abandonan.
        </p>
      )}
    </div>
  )
}
