/**
 * src/componentes/seguimiento/Dialogos.tsx — registrar y cerrar intervenciones (RF-09).
 *
 * La escritura va por la cuenta app_seguimiento, que solo puede ejecutar los dos
 * procedimientos del registro; la IA nunca escribe aquí.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { enviar } from '../../lib/api'
import { TIPOS_INTERVENCION } from '../../lib/seguimiento'
import { Button } from '../ui/Button'
import { Dialogo } from '../ui/Dialogo'
import { Aviso } from '../ui/Estados'
import { Campo, Select, Textarea } from '../ui/Input'
import { useToast } from '../ui/Toast'

export function DialogoRegistrar({
  abierto,
  onCerrar,
  token,
  nombre,
  tipoSugerido,
}: {
  abierto: boolean
  onCerrar: () => void
  token: string
  nombre: string
  tipoSugerido?: string
}) {
  const cliente = useQueryClient()
  const toast = useToast()
  const [tipo, setTipo] = useState(tipoSugerido ?? 'CONTACTO')
  const [descripcion, setDescripcion] = useState('')
  const [error, setError] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: () => enviar('/seguimiento', { token, tipo, descripcion: descripcion.trim() }),
    onSuccess: () => {
      cliente.invalidateQueries()
      toast('exito', 'Intervención registrada.')
      setDescripcion('')
      onCerrar()
    },
    onError: (e) => setError(e instanceof Error ? e.message : 'No se pudo registrar.'),
  })
  const valida = descripcion.trim().length >= 5
  return (
    <Dialogo
      abierto={abierto}
      onCerrar={onCerrar}
      titulo="Registrar intervención"
      descripcion={`Acción de acompañamiento para ${nombre}. Queda en el historial del estudiante y en la bitácora.`}
      pie={
        <>
          <Button variant="secondary" onClick={onCerrar}>
            Cancelar
          </Button>
          <Button loading={m.isPending} disabled={!valida} onClick={() => (setError(null), m.mutate())}>
            Registrar intervención
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <Aviso tono="danger">{error}</Aviso>}
        <Campo etiqueta="Tipo de intervención">
          {(p) => (
            <Select {...p} value={tipo} onChange={(e) => setTipo(e.target.value)}>
              {Object.entries(TIPOS_INTERVENCION).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          )}
        </Campo>
        <Campo etiqueta="Qué se hizo o se acordó" ayuda="Entre 5 y 400 caracteres. No escriba diagnósticos médicos ni datos sensibles.">
          {(p) => (
            <Textarea
              {...p}
              maxLength={400}
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              placeholder="Ej.: Llamada al estudiante; acordamos tutoría de Cálculo los martes."
            />
          )}
        </Campo>
      </div>
    </Dialogo>
  )
}

export function DialogoCerrar({ abierto, onCerrar, intervencionId }: { abierto: boolean; onCerrar: () => void; intervencionId: number | null }) {
  const cliente = useQueryClient()
  const toast = useToast()
  const [resultado, setResultado] = useState('')
  const [error, setError] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: () => enviar(`/seguimiento/${intervencionId}/cerrar`, { resultado: resultado.trim() }),
    onSuccess: () => {
      cliente.invalidateQueries()
      toast('exito', 'Intervención cerrada.')
      setResultado('')
      onCerrar()
    },
    onError: (e) => setError(e instanceof Error ? e.message : 'No se pudo cerrar.'),
  })
  return (
    <Dialogo
      abierto={abierto}
      onCerrar={onCerrar}
      titulo="Cerrar intervención"
      descripcion="Anote el resultado: así la institución aprende qué acciones funcionan."
      pie={
        <>
          <Button variant="secondary" onClick={onCerrar}>
            Cancelar
          </Button>
          <Button loading={m.isPending} disabled={resultado.trim().length < 3} onClick={() => (setError(null), m.mutate())}>
            Cerrar intervención
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <Aviso tono="danger">{error}</Aviso>}
        <Campo etiqueta="Resultado">
          {(p) => (
            <Textarea {...p} maxLength={200} value={resultado} onChange={(e) => setResultado(e.target.value)} placeholder="Ej.: Asiste a tutorías y aprobó el parcial." />
          )}
        </Campo>
      </div>
    </Dialogo>
  )
}
