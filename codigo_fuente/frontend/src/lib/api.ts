/**
 * src/lib/api.ts — cliente de la API (RF de seguridad: token JWT + institución activa).
 *
 * Cada petición lleva el token de sesión y la cabecera X-Institucion; el backend
 * valida ambos y fija la institución en SESSION_CONTEXT antes de leer. El token se
 * guarda en sessionStorage (se borra al cerrar la pestaña). Un 401 cierra la sesión
 * en todas las pantallas a la vez.
 */
const CLAVE_TOKEN = 'vicmar.token'
const CLAVE_INSTITUCION = 'vicmar.institucion'

export class ErrorApi extends Error {
  constructor(public estado: number, mensaje: string) {
    super(mensaje)
  }
}

function leer(almacen: Storage, clave: string): string | null {
  try {
    return almacen.getItem(clave)
  } catch {
    return null
  }
}

function escribir(almacen: Storage, clave: string, valor: string | null) {
  try {
    if (valor === null) almacen.removeItem(clave)
    else almacen.setItem(clave, valor)
  } catch {
    /* almacenamiento bloqueado: la sesión vive solo en memoria */
  }
}

let tokenEnMemoria: string | null = leer(sessionStorage, CLAVE_TOKEN)
let institucionEnMemoria: string | null = leer(localStorage, CLAVE_INSTITUCION)

export const sesionGuardada = {
  token: () => tokenEnMemoria,
  institucion: () => institucionEnMemoria,
  guardarToken(token: string | null) {
    tokenEnMemoria = token
    escribir(sessionStorage, CLAVE_TOKEN, token)
  },
  guardarInstitucion(codigo: string | null) {
    institucionEnMemoria = codigo
    escribir(localStorage, CLAVE_INSTITUCION, codigo)
  },
}

/** Mensaje legible a partir del `detail` de FastAPI (texto o lista de validación). */
function mensajeDe(cuerpo: unknown, estado: number): string {
  const detalle = (cuerpo as { detail?: unknown })?.detail
  if (typeof detalle === 'string') return detalle
  if (Array.isArray(detalle) && detalle.length) {
    const d = detalle[0] as { loc?: string[]; msg?: string }
    return `Revise el campo «${d.loc?.slice(-1)[0] ?? 'dato'}»: ${d.msg ?? 'valor no válido'}.`
  }
  if (estado === 0) return 'No hay conexión con el servidor. Verifique que el backend esté en ejecución.'
  if (estado >= 500) return 'El servidor no pudo completar la operación. Inténtelo de nuevo en unos segundos.'
  return 'No se pudo completar la operación.'
}

function cabeceras(extra?: HeadersInit): Headers {
  const h = new Headers(extra)
  const token = tokenEnMemoria
  if (token) h.set('Authorization', `Bearer ${token}`)
  if (institucionEnMemoria) h.set('X-Institucion', institucionEnMemoria)
  return h
}

async function pedir(ruta: string, opciones: RequestInit = {}): Promise<Response> {
  let respuesta: Response
  try {
    respuesta = await fetch(`/api${ruta}`, { ...opciones, headers: cabeceras(opciones.headers) })
  } catch {
    throw new ErrorApi(0, mensajeDe(null, 0))
  }
  if (respuesta.status === 401 && tokenEnMemoria) {
    sesionGuardada.guardarToken(null)
    window.dispatchEvent(new CustomEvent('vicmar:sesion-vencida'))
  }
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null)
    throw new ErrorApi(respuesta.status, mensajeDe(cuerpo, respuesta.status))
  }
  return respuesta
}

export async function obtener<T>(ruta: string): Promise<T> {
  return (await pedir(ruta)).json() as Promise<T>
}

export async function enviar<T>(ruta: string, cuerpo?: unknown, metodo: 'POST' | 'PUT' | 'DELETE' = 'POST'): Promise<T> {
  const r = await pedir(ruta, {
    method: metodo,
    headers: { 'Content-Type': 'application/json' },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  })
  return r.json() as Promise<T>
}

/** Descarga un archivo (Excel o PDF) respetando el nombre que propone el servidor. */
export async function descargar(ruta: string, nombrePorDefecto: string): Promise<void> {
  const r = await pedir(ruta)
  const disposicion = r.headers.get('Content-Disposition') ?? ''
  const nombre = /filename="?([^";]+)"?/.exec(disposicion)?.[1] ?? nombrePorDefecto
  const url = URL.createObjectURL(await r.blob())
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
