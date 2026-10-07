/**
 * src/lib/sesion.tsx — contexto de sesión: usuario, capacidades e institución activa.
 *
 * Al cambiar de institución se vacía la caché de consultas: ninguna pantalla puede
 * mostrar por un instante cifras de la institución anterior (aislamiento por
 * institución, RNF de protección de datos).
 */
import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { enviar, obtener, sesionGuardada } from './api'
import { puede as puedeCapacidad, type Capacidad } from './permisos'
import type { Institucion, Perfil } from './tipos'

interface ValorSesion {
  perfil: Perfil | null
  cargando: boolean
  instituciones: Institucion[]
  institucion: Institucion | null
  ingresar: (usuario: string, clave: string) => Promise<void>
  salir: (motivo?: string) => void
  cambiarInstitucion: (codigo: string) => void
  puede: (capacidad: Capacidad) => boolean
  avisoSalida: string | null
}

const Contexto = createContext<ValorSesion | null>(null)

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const cliente = useQueryClient()
  const [perfil, setPerfil] = useState<Perfil | null>(null)
  const [instituciones, setInstituciones] = useState<Institucion[]>([])
  const [codigo, setCodigo] = useState<string | null>(sesionGuardada.institucion())
  const [cargando, setCargando] = useState<boolean>(!!sesionGuardada.token())
  const [avisoSalida, setAvisoSalida] = useState<string | null>(null)

  const cargarInstituciones = useCallback(async (p: Perfil) => {
    // La institución guardada solo vale si sigue asignada a este usuario.
    const guardada = sesionGuardada.institucion()
    const inicial = guardada && p.instituciones.includes(guardada) ? guardada : p.instituciones[0] ?? null
    sesionGuardada.guardarInstitucion(inicial)
    setCodigo(inicial)
    const lista = await obtener<Institucion[]>('/instituciones').catch(() => [] as Institucion[])
    setInstituciones(lista)
  }, [])

  const salir = useCallback(
    (motivo?: string) => {
      sesionGuardada.guardarToken(null)
      setPerfil(null)
      setInstituciones([])
      cliente.clear()
      setAvisoSalida(motivo ?? null)
    },
    [cliente]
  )

  // Restaura la sesión de la pestaña (si el token sigue vigente).
  useEffect(() => {
    if (!sesionGuardada.token()) return
    obtener<Perfil>('/auth/yo')
      .then(async (p) => {
        setPerfil(p)
        await cargarInstituciones(p)
      })
      .catch(() => sesionGuardada.guardarToken(null))
      .finally(() => setCargando(false))
  }, [cargarInstituciones])

  useEffect(() => {
    const vencida = () => salir('Su sesión venció. Vuelva a ingresar para continuar.')
    window.addEventListener('vicmar:sesion-vencida', vencida)
    return () => window.removeEventListener('vicmar:sesion-vencida', vencida)
  }, [salir])

  const ingresar = useCallback(
    async (usuario: string, clave: string) => {
      const r = await enviar<{ token: string; usuario: Perfil }>('/auth/ingresar', { usuario, clave })
      sesionGuardada.guardarToken(r.token)
      cliente.clear()
      setAvisoSalida(null)
      await cargarInstituciones(r.usuario)
      setPerfil(r.usuario)
    },
    [cargarInstituciones, cliente]
  )

  const cambiarInstitucion = useCallback(
    (nuevo: string) => {
      if (!perfil?.instituciones.includes(nuevo)) return
      sesionGuardada.guardarInstitucion(nuevo)
      setCodigo(nuevo)
      cliente.removeQueries()
    },
    [cliente, perfil]
  )

  const valor = useMemo<ValorSesion>(() => {
    const institucion =
      instituciones.find((i) => i.codigo === codigo) ??
      (codigo ? { codigo, nombre: codigo, pais: null, tipo_datos: null, unidad_periodo: null, disponible: false } : null)
    return {
      perfil,
      cargando,
      instituciones,
      institucion,
      ingresar,
      salir,
      cambiarInstitucion,
      puede: (c) => puedeCapacidad(perfil?.capacidades, c),
      avisoSalida,
    }
  }, [perfil, cargando, instituciones, codigo, ingresar, salir, cambiarInstitucion, avisoSalida])

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}

export function useSesion(): ValorSesion {
  const v = useContext(Contexto)
  if (!v) throw new Error('useSesion debe usarse dentro de ProveedorSesion')
  return v
}
