/**
 * src/lib/consultas.ts — lectura de datos con caché por institución. La clave de cada
 * consulta incluye la institución activa: los datos de una nunca se muestran en otra.
 */
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { obtener } from './api'
import { useSesion } from './sesion'

export function useDatos<T>(ruta: string | null, opciones: { mantenerAnterior?: boolean; refrescoMs?: number } = {}) {
  const { institucion } = useSesion()
  return useQuery<T>({
    queryKey: [institucion?.codigo ?? '-', ruta],
    queryFn: () => obtener<T>(ruta as string),
    enabled: !!ruta && !!institucion,
    placeholderData: opciones.mantenerAnterior ? keepPreviousData : undefined,
    refetchInterval: opciones.refrescoMs,
  })
}
