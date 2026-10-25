/**
 * src/App.tsx — rutas de la aplicación. Cada ruta protegida declara la capacidad que
 * exige (la misma que valida el backend); las pantallas se cargan bajo demanda.
 */
import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AppShell } from './componentes/layout/AppShell'
import { inicioPara } from './componentes/layout/navegacion'
import { Logo } from './componentes/marca/Logo'
import { EmptyState } from './componentes/ui/Estados'
import { IconoLlave } from './componentes/iconos'
import type { Capacidad } from './lib/permisos'
import { useSesion } from './lib/sesion'
import Ingresar from './paginas/Ingresar'

const Panel = lazy(() => import('./paginas/Panel'))
const Estudiantes = lazy(() => import('./paginas/Estudiantes'))
const Ficha = lazy(() => import('./paginas/Ficha'))
const Seguimiento = lazy(() => import('./paginas/Seguimiento'))
const Consulta = lazy(() => import('./paginas/Consulta'))
const Carreras = lazy(() => import('./paginas/Carreras'))
const Referentes = lazy(() => import('./paginas/Referentes'))
const CalidadModelo = lazy(() => import('./paginas/CalidadModelo'))
const Reportes = lazy(() => import('./paginas/Reportes'))
const Usuarios = lazy(() => import('./paginas/admin/Usuarios'))
const Auditoria = lazy(() => import('./paginas/admin/Auditoria'))
const Estado = lazy(() => import('./paginas/admin/Estado'))
const Perfil = lazy(() => import('./paginas/Perfil'))

function Cargando() {
  return (
    <div className="flex h-[60vh] items-center justify-center" role="status" aria-label="Cargando">
      <Logo className="h-12 w-12" />
    </div>
  )
}

function Protegida({ requiere, children }: { requiere?: Capacidad; children: ReactNode }) {
  const { puede } = useSesion()
  if (requiere && !puede(requiere)) {
    return (
      <EmptyState
        icon={IconoLlave}
        title="Esta sección no está disponible para su rol"
        description="Si necesita acceder, solicite el permiso al área de Administración de TI."
      />
    )
  }
  return <Suspense fallback={<Cargando />}>{children}</Suspense>
}

export function App() {
  const { perfil, cargando, puede } = useSesion()
  const { pathname } = useLocation()

  if (cargando) {
    return (
      <div className="fondo-corporativo flex h-[100dvh] items-center justify-center">
        <Logo className="h-14 w-14" />
      </div>
    )
  }
  if (!perfil) {
    return pathname === '/ingresar' ? <Ingresar /> : <Navigate to="/ingresar" replace state={{ desde: pathname }} />
  }

  const inicio = inicioPara(puede)
  return (
    <Routes>
      <Route path="/ingresar" element={<Navigate to={inicio} replace />} />
      <Route element={<AppShell />}>
        <Route index element={<Navigate to={inicio} replace />} />
        <Route path="panel" element={<Protegida requiere="ver_panel"><Panel /></Protegida>} />
        <Route path="estudiantes" element={<Protegida requiere="ver_alumnos"><Estudiantes /></Protegida>} />
        <Route path="estudiantes/:token" element={<Protegida requiere="ver_ficha"><Ficha /></Protegida>} />
        <Route path="seguimiento" element={<Protegida requiere="ver_seguimiento"><Seguimiento /></Protegida>} />
        <Route path="consulta" element={<Protegida requiere="consultar"><Consulta /></Protegida>} />
        <Route path="carreras" element={<Protegida requiere="ver_carreras"><Carreras /></Protegida>} />
        <Route path="referentes" element={<Protegida requiere="ver_referentes"><Referentes /></Protegida>} />
        <Route path="modelo" element={<Protegida requiere="ver_modelo"><CalidadModelo /></Protegida>} />
        <Route path="reportes" element={<Protegida requiere="exportar"><Reportes /></Protegida>} />
        <Route path="admin/usuarios" element={<Protegida requiere="administrar_usuarios"><Usuarios /></Protegida>} />
        <Route path="admin/auditoria" element={<Protegida requiere="ver_auditoria"><Auditoria /></Protegida>} />
        <Route path="admin/estado" element={<Protegida requiere="ver_estado"><Estado /></Protegida>} />
        <Route path="perfil" element={<Protegida><Perfil /></Protegida>} />
        <Route
          path="*"
          element={<EmptyState title="Página no encontrada" description="La dirección no corresponde a ninguna sección del sistema." />}
        />
      </Route>
    </Routes>
  )
}
