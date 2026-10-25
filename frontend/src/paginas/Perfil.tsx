/** src/paginas/Perfil.tsx — datos de la cuenta y cambio de contraseña propia. */
import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { Badge } from '../componentes/ui/Badge'
import { Button } from '../componentes/ui/Button'
import { Card, CardBody, CardHeader } from '../componentes/ui/Card'
import { Aviso } from '../componentes/ui/Estados'
import { Campo, Input } from '../componentes/ui/Input'
import { useToast } from '../componentes/ui/Toast'
import { enviar } from '../lib/api'
import { fechaHora } from '../lib/formato'
import { useSesion } from '../lib/sesion'

export default function Perfil() {
  const { perfil, instituciones } = useSesion()
  const toast = useToast()
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [repetir, setRepetir] = useState('')
  const [error, setError] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: () => enviar('/auth/clave', { actual, nueva }, 'PUT'),
    onSuccess: () => {
      toast('exito', 'Contraseña actualizada.')
      setActual('')
      setNueva('')
      setRepetir('')
    },
    onError: (e) => setError(e.message),
  })

  function guardar(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (nueva.length < 8) return setError('La contraseña nueva debe tener al menos 8 caracteres.')
    if (nueva !== repetir) return setError('Las contraseñas nuevas no coinciden.')
    m.mutate()
  }

  if (!perfil) return null
  return (
    <div className="entrada">
      <EncabezadoPagina titulo="Mi cuenta" descripcion="Sus datos de acceso y las instituciones que puede consultar." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Datos de la cuenta" />
          <CardBody className="pt-4">
            <dl className="divide-y divide-border text-sm">
              {[
                ['Nombre', perfil.nombre || '—'],
                ['Usuario', perfil.usuario],
                ['Correo', perfil.correo || '—'],
                ['Rol', perfil.rol_descripcion],
                ['Último acceso', fechaHora(perfil.ultimo_acceso)],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 py-2.5">
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd className="text-right font-medium text-foreground">{v}</dd>
                </div>
              ))}
              <div className="py-2.5">
                <dt className="text-muted-foreground">Instituciones</dt>
                <dd className="mt-2 flex flex-wrap gap-2">
                  {perfil.instituciones.map((c) => (
                    <Badge key={c}>{instituciones.find((i) => i.codigo === c)?.nombre ?? c}</Badge>
                  ))}
                </dd>
              </div>
            </dl>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Cambiar contraseña" description="Mínimo 8 caracteres. Se le pedirá la contraseña actual." />
          <CardBody className="pt-4">
            <form onSubmit={guardar} className="space-y-4" noValidate>
              {error && <Aviso tono="danger">{error}</Aviso>}
              <Campo etiqueta="Contraseña actual">{(p) => <Input {...p} type="password" autoComplete="current-password" value={actual} onChange={(e) => setActual(e.target.value)} />}</Campo>
              <Campo etiqueta="Contraseña nueva">{(p) => <Input {...p} type="password" autoComplete="new-password" value={nueva} onChange={(e) => setNueva(e.target.value)} />}</Campo>
              <Campo etiqueta="Repita la contraseña nueva">{(p) => <Input {...p} type="password" autoComplete="new-password" value={repetir} onChange={(e) => setRepetir(e.target.value)} />}</Campo>
              <Button type="submit" loading={m.isPending} disabled={!actual || !nueva}>
                Guardar contraseña
              </Button>
            </form>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
