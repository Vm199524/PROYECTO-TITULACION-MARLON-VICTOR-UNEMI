/**
 * src/paginas/admin/Usuarios.tsx — cuentas, roles e instituciones asignadas (RF-15).
 *
 * Solo para Administración de TI. El backend impide quitarse el propio rol, desactivarse
 * a sí mismo o eliminar la última cuenta de administración.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { IconoEditar, IconoMas, IconoPapelera, IconoUsuarios } from '../../componentes/iconos'
import { EncabezadoPagina } from '../../componentes/layout/EncabezadoPagina'
import { Badge } from '../../componentes/ui/Badge'
import { Button } from '../../componentes/ui/Button'
import { Card } from '../../componentes/ui/Card'
import { Dialogo } from '../../componentes/ui/Dialogo'
import { Aviso, EmptyState, EstadoError } from '../../componentes/ui/Estados'
import { Campo, Input, Select } from '../../componentes/ui/Input'
import { Skeleton } from '../../componentes/ui/Skeleton'
import { Table, TableBody, TableHead, TableRow, Td, Th } from '../../componentes/ui/Table'
import { useToast } from '../../componentes/ui/Toast'
import { enviar } from '../../lib/api'
import { useDatos } from '../../lib/consultas'
import { fechaHora } from '../../lib/formato'
import { useSesion } from '../../lib/sesion'
import type { Cuenta, Rol } from '../../lib/tipos'

interface Datos {
  usuarios: Cuenta[]
  roles: Record<Rol, string>
  instituciones: string[]
}

const VARIANTE_ROL: Record<Rol, 'accent' | 'info' | 'neutral'> = { ADMIN_TI: 'accent', BIENESTAR: 'info', AUTORIDAD: 'neutral' }

function Formulario({ datos, cuenta, onCerrar }: { datos: Datos; cuenta: Cuenta | null; onCerrar: () => void }) {
  const cliente = useQueryClient()
  const toast = useToast()
  const { instituciones: info } = useSesion()
  const nueva = !cuenta
  const [f, setF] = useState({
    usuario: cuenta?.usuario ?? '',
    nombre: cuenta?.nombre ?? '',
    correo: cuenta?.correo ?? '',
    rol: (cuenta?.rol ?? 'AUTORIDAD') as Rol,
    instituciones: cuenta?.instituciones ?? [datos.instituciones[0]],
    activo: cuenta?.activo ?? true,
    clave: '',
  })
  const [error, setError] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: () =>
      nueva
        ? enviar('/admin/usuarios', { ...f, activo: undefined })
        : enviar(`/admin/usuarios/${cuenta!.usuario}`, { nombre: f.nombre, correo: f.correo, rol: f.rol, instituciones: f.instituciones, activo: f.activo, clave: f.clave || undefined }, 'PUT'),
    onSuccess: () => {
      cliente.invalidateQueries()
      toast('exito', nueva ? 'Cuenta creada.' : 'Cuenta actualizada.')
      onCerrar()
    },
    onError: (e) => setError(e.message),
  })
  const nombreInst = (c: string) => info.find((i) => i.codigo === c)?.nombre ?? c
  const valido = f.usuario.trim().length >= 3 && f.nombre.trim().length >= 2 && f.instituciones.length > 0 && (!nueva || f.clave.length >= 8)
  return (
    <Dialogo
      abierto
      onCerrar={onCerrar}
      titulo={nueva ? 'Nueva cuenta' : `Editar ${cuenta!.usuario}`}
      descripcion="El rol define qué pantallas y acciones tiene la persona; las instituciones, qué datos puede ver."
      pie={
        <>
          <Button variant="secondary" onClick={onCerrar}>
            Cancelar
          </Button>
          <Button loading={m.isPending} disabled={!valido} onClick={() => (setError(null), m.mutate())}>
            {nueva ? 'Crear cuenta' : 'Guardar cambios'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <Aviso tono="danger">{error}</Aviso>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo etiqueta="Usuario">{(p) => <Input {...p} disabled={!nueva} value={f.usuario} onChange={(e) => setF({ ...f, usuario: e.target.value })} placeholder="nombre.apellido" />}</Campo>
          <Campo etiqueta="Nombre completo">{(p) => <Input {...p} value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} />}</Campo>
        </div>
        <Campo etiqueta="Correo institucional">{(p) => <Input {...p} type="email" value={f.correo} onChange={(e) => setF({ ...f, correo: e.target.value })} />}</Campo>
        <Campo etiqueta="Rol">
          {(p) => (
            <Select {...p} value={f.rol} onChange={(e) => setF({ ...f, rol: e.target.value as Rol })}>
              {Object.entries(datos.roles).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          )}
        </Campo>
        <fieldset>
          <legend className="text-sm font-medium text-foreground">Instituciones</legend>
          <div className="mt-2 space-y-2">
            {datos.instituciones.map((c) => (
              <label key={c} className="flex cursor-pointer items-center gap-2.5 text-sm text-foreground">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded accent-[rgb(var(--accent))]"
                  checked={f.instituciones.includes(c)}
                  onChange={(e) => setF({ ...f, instituciones: e.target.checked ? [...f.instituciones, c] : f.instituciones.filter((x) => x !== c) })}
                />
                {nombreInst(c)}
              </label>
            ))}
          </div>
        </fieldset>
        <Campo etiqueta={nueva ? 'Contraseña inicial' : 'Nueva contraseña (opcional)'} ayuda="Mínimo 8 caracteres. Entréguela por un canal seguro.">
          {(p) => <Input {...p} type="password" autoComplete="new-password" value={f.clave} onChange={(e) => setF({ ...f, clave: e.target.value })} />}
        </Campo>
        {!nueva && (
          <label className="flex cursor-pointer items-center gap-2.5 text-sm text-foreground">
            <input type="checkbox" className="h-4 w-4 accent-[rgb(var(--accent))]" checked={f.activo} onChange={(e) => setF({ ...f, activo: e.target.checked })} />
            Cuenta activa
          </label>
        )}
      </div>
    </Dialogo>
  )
}

export default function Usuarios() {
  const { perfil } = useSesion()
  const cliente = useQueryClient()
  const toast = useToast()
  const { data, error, isLoading, refetch } = useDatos<Datos>('/admin/usuarios')
  const [editar, setEditar] = useState<Cuenta | null | 'nueva'>(null)
  const [eliminar, setEliminar] = useState<Cuenta | null>(null)
  const baja = useMutation({
    mutationFn: (u: string) => enviar(`/admin/usuarios/${u}`, undefined, 'DELETE'),
    onSuccess: () => {
      cliente.invalidateQueries()
      toast('exito', 'Cuenta eliminada.')
      setEliminar(null)
    },
    onError: (e) => toast('error', e.message),
  })

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Usuarios y roles"
        descripcion="Autoridad académica: consulta y reportes. Bienestar estudiantil: además simula y registra seguimiento. Administración de TI: todo, más cuentas, auditoría y estado."
        acciones={
          <Button onClick={() => setEditar('nueva')}>
            <IconoMas />
            Nueva cuenta
          </Button>
        }
      />
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="space-y-3 p-6">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : error ? (
          <EstadoError error={error} onReintentar={() => refetch()} />
        ) : !data?.usuarios.length ? (
          <EmptyState icon={IconoUsuarios} title="No hay cuentas" />
        ) : (
          <Table>
            <TableHead>
              <tr>
                <Th>Cuenta</Th>
                <Th>Rol</Th>
                <Th>Instituciones</Th>
                <Th>Estado</Th>
                <Th>Último acceso</Th>
                <Th className="text-right">Acciones</Th>
              </tr>
            </TableHead>
            <TableBody>
              {data.usuarios.map((u) => (
                <TableRow key={u.usuario}>
                  <Td>
                    <p className="font-medium">{u.nombre}</p>
                    <p className="text-xs text-muted-foreground">
                      {u.usuario}
                      {u.correo ? ` · ${u.correo}` : ''}
                    </p>
                  </Td>
                  <Td>
                    <Badge variant={VARIANTE_ROL[u.rol]}>{data.roles[u.rol] ?? u.rol}</Badge>
                  </Td>
                  <Td className="text-sm text-muted-foreground">{u.instituciones.join(', ')}</Td>
                  <Td>{u.activo ? <Badge variant="success" dot>Activa</Badge> : <Badge dot>Inactiva</Badge>}</Td>
                  <Td className="text-sm text-muted-foreground">{fechaHora(u.ultimo_acceso)}</Td>
                  <Td className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" aria-label={`Editar ${u.usuario}`} onClick={() => setEditar(u)}>
                        <IconoEditar />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Eliminar ${u.usuario}`}
                        disabled={u.usuario === perfil?.usuario}
                        onClick={() => setEliminar(u)}
                        className="hover:text-danger"
                      >
                        <IconoPapelera />
                      </Button>
                    </div>
                  </Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
      {editar && data && <Formulario datos={data} cuenta={editar === 'nueva' ? null : editar} onCerrar={() => setEditar(null)} />}
      <Dialogo
        abierto={!!eliminar}
        onCerrar={() => setEliminar(null)}
        titulo="Eliminar cuenta"
        descripcion={`La cuenta ${eliminar?.usuario ?? ''} dejará de poder ingresar. Su historial en la bitácora se conserva.`}
        pie={
          <>
            <Button variant="secondary" onClick={() => setEliminar(null)}>
              Cancelar
            </Button>
            <Button variant="destructive" loading={baja.isPending} onClick={() => eliminar && baja.mutate(eliminar.usuario)}>
              Eliminar cuenta
            </Button>
          </>
        }
      />
    </div>
  )
}
