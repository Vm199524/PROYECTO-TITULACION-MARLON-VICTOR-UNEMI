/**
 * src/paginas/admin/Auditoria.tsx — bitácora de auditoría (RNF de trazabilidad, LOPDP).
 *
 * Quién ingresó, consultó, abrió una ficha, simuló, exportó o cambió una cuenta, y
 * cuándo. Los detalles nunca guardan cédulas completas ni el SQL (solo su huella).
 */
import { useState } from 'react'
import { IconoAuditoria } from '../../componentes/iconos'
import { EncabezadoPagina } from '../../componentes/layout/EncabezadoPagina'
import { Badge } from '../../componentes/ui/Badge'
import { Card } from '../../componentes/ui/Card'
import { Actualizando, EmptyState, EstadoError } from '../../componentes/ui/Estados'
import { Input, Select } from '../../componentes/ui/Input'
import { Skeleton } from '../../componentes/ui/Skeleton'
import { Table, TableBody, TableHead, TableRow, Td, Th } from '../../componentes/ui/Table'
import { useDatos } from '../../lib/consultas'
import { entero, fechaHora } from '../../lib/formato'
import type { EventoAuditoria } from '../../lib/tipos'

const ACCIONES: Record<string, string> = {
  INGRESO: 'Ingreso',
  CONSULTA: 'Consulta conversacional',
  FICHA: 'Ficha de estudiante',
  SIMULACION: 'Simulación',
  EXPORTACION: 'Exportación',
  SEGUIMIENTO_ALTA: 'Intervención registrada',
  SEGUIMIENTO_CIERRE: 'Intervención cerrada',
  CAMBIO_CLAVE: 'Cambio de contraseña',
  CUENTA_ALTA: 'Cuenta creada',
  CUENTA_CAMBIO: 'Cuenta modificada',
  CUENTA_BAJA: 'Cuenta eliminada',
}

function detalleTexto(d: Record<string, unknown> | null | undefined): string {
  if (!d) return ''
  return Object.entries(d)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
    .join(' · ')
}

export default function Auditoria() {
  const [accion, setAccion] = useState('')
  const [usuario, setUsuario] = useState('')
  const q = new URLSearchParams({ limite: '500' })
  if (accion) q.set('accion', accion)
  if (usuario.trim()) q.set('usuario', usuario.trim())
  const { data, error, isLoading, isFetching, refetch } = useDatos<{ eventos: EventoAuditoria[] }>(`/admin/auditoria?${q}`, { mantenerAnterior: true })

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Auditoría"
        descripcion="Registro de cada acceso y acción sobre datos de estudiantes. Se muestran los 500 eventos más recientes."
        acciones={<Actualizando activo={isFetching && !isLoading} />}
        extra={
          <div className="flex flex-col gap-3 sm:flex-row">
            <Select aria-label="Acción" value={accion} onChange={(e) => setAccion(e.target.value)} className="sm:max-w-xs">
              <option value="">Todas las acciones</option>
              {Object.entries(ACCIONES).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
            <Input aria-label="Usuario" placeholder="Filtrar por usuario" value={usuario} onChange={(e) => setUsuario(e.target.value)} className="sm:max-w-xs" />
          </div>
        }
      />
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="space-y-3 p-6">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-9" />
            ))}
          </div>
        ) : error ? (
          <EstadoError error={error} onReintentar={() => refetch()} />
        ) : !data?.eventos.length ? (
          <EmptyState icon={IconoAuditoria} title="Sin eventos con estos filtros" />
        ) : (
          <>
            <Table>
              <TableHead>
                <tr>
                  <Th>Fecha</Th>
                  <Th>Usuario</Th>
                  <Th>Acción</Th>
                  <Th>Institución</Th>
                  <Th>Resultado</Th>
                  <Th>Detalle</Th>
                </tr>
              </TableHead>
              <TableBody>
                {data.eventos.map((e, i) => (
                  <TableRow key={`${e.fecha}-${i}`}>
                    <Td className="tabular whitespace-nowrap text-sm">{fechaHora(e.fecha)}</Td>
                    <Td className="text-sm">{e.usuario}</Td>
                    <Td className="whitespace-nowrap text-sm">{ACCIONES[e.accion] ?? e.accion}</Td>
                    <Td className="text-sm text-muted-foreground">{e.institucion ?? '—'}</Td>
                    <Td>
                      <Badge variant={e.resultado === 'OK' || e.resultado === 'CERTIFICADA' || e.resultado === 'GENERADA_IA' ? 'success' : e.resultado === 'RECHAZADO' || e.resultado === 'ERROR' ? 'danger' : 'neutral'}>
                        {e.resultado}
                      </Badge>
                    </Td>
                    <Td className="max-w-[420px] text-xs text-muted-foreground">
                      <p className="line-clamp-2 break-all">{detalleTexto(e.detalle)}</p>
                    </Td>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="border-t border-border px-6 py-3 text-xs text-muted-foreground">{entero(data.eventos.length)} eventos</p>
          </>
        )}
      </Card>
    </div>
  )
}
