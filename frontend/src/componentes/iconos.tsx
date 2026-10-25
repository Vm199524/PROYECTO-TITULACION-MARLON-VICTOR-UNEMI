/**
 * src/componentes/iconos.tsx — iconos propios de trazo 1,75 px en cuadrícula de 24 px.
 * Usan `currentColor`, así heredan el color del texto y respetan el tema. Sin librería
 * externa: solo los iconos que la aplicación usa.
 */
import type { SVGProps } from 'react'

export type Icono = ((props: SVGProps<SVGSVGElement>) => JSX.Element) & { displayName?: string }

function crear(nombre: string, trazos: JSX.Element): Icono {
  const I: Icono = (props) => (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {trazos}
    </svg>
  )
  I.displayName = nombre
  return I
}

export const IconoPanel = crear('IconoPanel', <><rect x="3" y="3" width="7.5" height="9" rx="1.5" /><rect x="13.5" y="3" width="7.5" height="5" rx="1.5" /><rect x="13.5" y="11" width="7.5" height="10" rx="1.5" /><rect x="3" y="15" width="7.5" height="6" rx="1.5" /></>)
export const IconoEstudiantes = crear('IconoEstudiantes', <><circle cx="9" cy="8" r="3.25" /><path d="M3 19.5c.6-3.2 3-5 6-5s5.4 1.8 6 5" /><path d="M15.5 4.9a3.2 3.2 0 0 1 0 6.2" /><path d="M17.5 14.7c1.9.6 3.1 2.3 3.5 4.8" /></>)
export const IconoAlerta = crear('IconoAlerta', <><path d="M6 16.5V11a6 6 0 1 1 12 0v5.5l1.5 2H4.5Z" /><path d="M10 20.5a2 2 0 0 0 4 0" /></>)
export const IconoSeguimiento = crear('IconoSeguimiento', <><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4V3h6v1" /><path d="m9 12.5 2 2 4-4.5" /><path d="M9 17.5h6" /></>)
export const IconoCarreras = crear('IconoCarreras', <><path d="M12 4 2.5 8.5 12 13l9.5-4.5Z" /><path d="M6.5 10.5V15c0 1.7 2.5 3 5.5 3s5.5-1.3 5.5-3v-4.5" /><path d="M21.5 8.5V14" /></>)
export const IconoReferentes = crear('IconoReferentes', <><path d="M12 3.5v17" /><path d="M5 20.5h14" /><path d="M5 7h14" /><path d="m5 7-3 6.5a3 3 0 0 0 6 0Z" /><path d="m19 7-3 6.5a3 3 0 0 0 6 0Z" /></>)
export const IconoConsulta = crear('IconoConsulta', <><path d="M20 12.5a7.5 7.5 0 0 1-11 6.6L4 20.5l1.4-4.6A7.5 7.5 0 1 1 20 12.5Z" /><path d="M9 11h6" /><path d="M9 14.5h3.5" /></>)
export const IconoModelo = crear('IconoModelo', <><path d="M12 3 4.5 6v5.5c0 4.5 3.1 8.2 7.5 9.5 4.4-1.3 7.5-5 7.5-9.5V6Z" /><path d="m9 12 2.2 2.2L15.5 10" /></>)
export const IconoReportes = crear('IconoReportes', <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" /><path d="M14 3v5h5" /><path d="M9 17v-3" /><path d="M12 17v-5" /><path d="M15 17v-2" /></>)
export const IconoUsuarios = crear('IconoUsuarios', <><circle cx="10" cy="8" r="3.5" /><path d="M3.5 20c.7-3.5 3.3-5.5 6.5-5.5 1.3 0 2.5.3 3.5.9" /><path d="M18 15v6" /><path d="M15 18h6" /></>)
export const IconoAuditoria = crear('IconoAuditoria', <><path d="M8 6h12" /><path d="M8 12h6" /><path d="M8 18h4" /><path d="M4 6h.01" /><path d="M4 12h.01" /><path d="M4 18h.01" /><circle cx="17.5" cy="16" r="3" /><path d="m19.7 18.2 1.8 1.8" /></>)
export const IconoEstado = crear('IconoEstado', <><rect x="3" y="4" width="18" height="6.5" rx="1.5" /><rect x="3" y="13.5" width="18" height="6.5" rx="1.5" /><path d="M7 7.25h.01" /><path d="M7 16.75h.01" /><path d="M11 7.25h6" /><path d="M11 16.75h6" /></>)
export const IconoSol = crear('IconoSol', <><circle cx="12" cy="12" r="4" /><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4" /></>)
export const IconoLuna = crear('IconoLuna', <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z" />)
export const IconoMenu = crear('IconoMenu', <><path d="M4 6.5h16" /><path d="M4 12h16" /><path d="M4 17.5h16" /></>)
export const IconoLateral = crear('IconoLateral', <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /><path d="m15.5 10-2 2 2 2" /></>)
export const IconoCerrar =crear('IconoCerrar', <><path d="m6 6 12 12" /><path d="M18 6 6 18" /></>)
export const IconoSalir = crear('IconoSalir', <><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" /><path d="m10 16-4-4 4-4" /><path d="M6 12h10" /></>)
export const IconoVolver = crear('IconoVolver', <><path d="m11 18-6-6 6-6" /><path d="M5 12h14" /></>)
export const IconoDerecha = crear('IconoDerecha', <path d="m9 6 6 6-6 6" />)
export const IconoAbajo = crear('IconoAbajo', <path d="m6 9 6 6 6-6" />)
export const IconoBuscar = crear('IconoBuscar', <><circle cx="11" cy="11" r="6.5" /><path d="m20 20-4.4-4.4" /></>)
export const IconoDescargar = crear('IconoDescargar', <><path d="M12 4v11" /><path d="m7.5 11 4.5 4.5 4.5-4.5" /><path d="M5 20h14" /></>)
export const IconoSubida = crear('IconoSubida', <><path d="M12 19V5" /><path d="m6 11 6-6 6 6" /></>)
export const IconoBajada = crear('IconoBajada', <><path d="M12 5v14" /><path d="m6 13 6 6 6-6" /></>)
export const IconoInfo = crear('IconoInfo', <><circle cx="12" cy="12" r="9" /><path d="M12 11v5.5" /><path d="M12 7.5h.01" /></>)
export const IconoAviso = crear('IconoAviso', <><path d="M10.3 4.2 2.8 17.5A2 2 0 0 0 4.5 20.5h15a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z" /><path d="M12 9.5v4" /><path d="M12 17h.01" /></>)
export const IconoCheck = crear('IconoCheck', <path d="m5 12.5 4.5 4.5L19 7.5" />)
export const IconoEnviar = crear('IconoEnviar', <><path d="M21 3 10 14" /><path d="m21 3-6.5 18-4.5-7-7-4.5Z" /></>)
export const IconoChispa = crear('IconoChispa', <><path d="M12 3.5 13.8 9 19.5 10.5 13.8 12 12 17.5 10.2 12 4.5 10.5 10.2 9Z" /><path d="M19 16v4" /><path d="M17 18h4" /></>)
export const IconoBaseDatos = crear('IconoBaseDatos', <><ellipse cx="12" cy="5.5" rx="7.5" ry="2.75" /><path d="M4.5 5.5v13c0 1.5 3.4 2.75 7.5 2.75s7.5-1.25 7.5-2.75v-13" /><path d="M4.5 12c0 1.5 3.4 2.75 7.5 2.75s7.5-1.25 7.5-2.75" /></>)
export const IconoCodigo = crear('IconoCodigo', <><path d="m8 7-5 5 5 5" /><path d="m16 7 5 5-5 5" /></>)
export const IconoMas = crear('IconoMas', <><path d="M12 5v14" /><path d="M5 12h14" /></>)
export const IconoReloj = crear('IconoReloj', <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>)
export const IconoInstitucion = crear('IconoInstitucion', <><path d="M3 20.5h18" /><path d="M4.5 9.5 12 4l7.5 5.5" /><path d="M6.5 10v8" /><path d="M10 10v8" /><path d="M14 10v8" /><path d="M17.5 10v8" /></>)
export const IconoLlave = crear('IconoLlave', <><circle cx="8" cy="15" r="4" /><path d="m11 12 9-9" /><path d="m17 6 2.5 2.5" /><path d="m15 8 2 2" /></>)
export const IconoTendencia = crear('IconoTendencia', <><path d="m3 17 6-6 4 4 8-8" /><path d="M15 7h6v6" /></>)
export const IconoSimular = crear('IconoSimular', <><path d="M4 6h10" /><path d="M18 6h2" /><circle cx="16" cy="6" r="2" /><path d="M4 12h3" /><path d="M11 12h9" /><circle cx="9" cy="12" r="2" /><path d="M4 18h12" /><circle cx="18" cy="18" r="2" /></>)
export const IconoLibro = crear('IconoLibro', <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5Z" /><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5" /></>)
export const IconoEnlace = crear('IconoEnlace', <><path d="M14 4h6v6" /><path d="M20 4 11 13" /><path d="M18 14v5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 19V7.5A1.5 1.5 0 0 1 5.5 6H10" /></>)
export const IconoEditar = crear('IconoEditar', <><path d="M4 20h4L19 9l-4-4L4 16Z" /><path d="m13.5 6.5 4 4" /></>)
export const IconoPapelera = crear('IconoPapelera', <><path d="M4 7h16" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M6 7l1 13h10l1-13" /><path d="M9 7V4h6v3" /></>)
export const IconoActualizar = crear('IconoActualizar', <><path d="M20 11a8 8 0 0 0-14.6-4.5L4 8" /><path d="M4 4v4h4" /><path d="M4 13a8 8 0 0 0 14.6 4.5L20 16" /><path d="M20 20v-4h-4" /></>)
