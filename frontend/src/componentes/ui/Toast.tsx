/**
 * src/componentes/ui/Toast.tsx — avisos breves abajo a la derecha (aria-live). Máximo 4;
 * se cierran solos (4,5 s; los errores 7 s).
 */
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { IconoAviso, IconoCerrar, IconoCheck, IconoInfo } from '../iconos'

type Tipo = 'exito' | 'error' | 'info'
interface Toast {
  id: number
  tipo: Tipo
  mensaje: string
}

const Contexto = createContext<(tipo: Tipo, mensaje: string) => void>(() => undefined)
let siguiente = 1

export function ProveedorToast({ children }: { children: ReactNode }) {
  const [lista, setLista] = useState<Toast[]>([])
  const quitar = useCallback((id: number) => setLista((l) => l.filter((t) => t.id !== id)), [])
  const mostrar = useCallback(
    (tipo: Tipo, mensaje: string) => {
      const id = siguiente++
      setLista((l) => [...l.slice(-3), { id, tipo, mensaje }])
      setTimeout(() => quitar(id), tipo === 'error' ? 7000 : 4500)
    },
    [quitar]
  )
  const valor = useMemo(() => mostrar, [mostrar])
  return (
    <Contexto.Provider value={valor}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[calc(100%-32px)] max-w-sm flex-col gap-2">
        {lista.map((t) => {
          const I = t.tipo === 'exito' ? IconoCheck : t.tipo === 'error' ? IconoAviso : IconoInfo
          return (
            <div
              key={t.id}
              role={t.tipo === 'error' ? 'alert' : 'status'}
              className="entrada pointer-events-auto flex items-start gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm shadow-flotante"
            >
              <I className={cn('mt-0.5 h-4 w-4 shrink-0', t.tipo === 'exito' ? 'text-success' : t.tipo === 'error' ? 'text-danger' : 'text-info')} />
              <p className="flex-1 text-foreground">{t.mensaje}</p>
              <button type="button" aria-label="Cerrar aviso" onClick={() => quitar(t.id)} className="text-muted-foreground hover:text-foreground">
                <IconoCerrar className="h-4 w-4" />
              </button>
            </div>
          )
        })}
      </div>
    </Contexto.Provider>
  )
}

export function useToast() {
  return useContext(Contexto)
}
