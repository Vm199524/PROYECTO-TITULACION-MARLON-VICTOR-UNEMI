// ==========================================================================
//  Arranque único del sistema desde la raíz del repositorio:
//    npm start            (o doble clic en iniciar.bat)
//  1. Crea el entorno virtual de Python si no existe (backend/venv).
//  2. Instala las dependencias del backend y de la web solo si cambiaron.
//  3. Inicia el contenedor de SQL Server si Docker está disponible.
//  4. Levanta la API (FastAPI, puerto 8090) y la web (Vite, puerto 3000)
//     en la misma consola. Ctrl+C detiene ambas.
//  Sin dependencias externas: solo Node.js y Python.
//  Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco (UNEMI, 2026)
// ==========================================================================
import { spawn, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { copyFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..')
const BACKEND = join(RAIZ, 'backend')
const FRONTEND = join(RAIZ, 'frontend')
const WINDOWS = process.platform === 'win32'
const PYTHON = join(BACKEND, 'venv', WINDOWS ? 'Scripts/python.exe' : 'bin/python')
const NPM = 'npm'
const PUERTO_API = process.env.PUERTO_API ?? '8090'
const ENTORNO = { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' }

const paso = (texto) => console.log(`\n\x1b[36m▸ ${texto}\x1b[0m`)
const fallar = (texto) => {
  console.error(`\n\x1b[31m✖ ${texto}\x1b[0m`)
  process.exit(1)
}

// En Windows npm es un .cmd: se invoca a través de cmd.exe, sin la opción shell de Node.
const orden = (comando, args) => (WINDOWS && comando === NPM ? ['cmd.exe', ['/d', '/c', 'npm', ...args]] : [comando, args])

function ejecutar(comando, args, cwd) {
  const r = spawnSync(...orden(comando, args), { cwd, stdio: 'inherit', env: ENTORNO })
  return r.status === 0
}

// Huella del archivo de dependencias: se reinstala solo si cambió.
function huella(archivo) {
  return createHash('sha256').update(readFileSync(archivo)).digest('hex')
}
function necesitaInstalar(archivo, marca) {
  return !existsSync(marca) || readFileSync(marca, 'utf8') !== huella(archivo)
}

// ── 1. Backend: entorno virtual y dependencias ────────────────────────────
if (!existsSync(PYTHON)) {
  paso('Creando el entorno virtual de Python (backend/venv) ...')
  const creado = WINDOWS
    ? ejecutar('py', ['-3', '-m', 'venv', 'venv'], BACKEND) || ejecutar('python', ['-m', 'venv', 'venv'], BACKEND)
    : ejecutar('python3', ['-m', 'venv', 'venv'], BACKEND)
  if (!creado) fallar('No se pudo crear el entorno virtual. Instale Python 3.13 o 3.14.')
}
const requisitos = join(BACKEND, 'requirements.txt')
const marcaPip = join(BACKEND, 'venv', '.requisitos_instalados')
if (necesitaInstalar(requisitos, marcaPip)) {
  paso('Instalando las dependencias del backend ...')
  if (!ejecutar(PYTHON, ['-m', 'pip', 'install', '--disable-pip-version-check', '-r', 'requirements.txt'], BACKEND))
    fallar('Falló la instalación de las dependencias del backend.')
  writeFileSync(marcaPip, huella(requisitos))
}
if (!existsSync(join(BACKEND, '.env'))) {
  copyFileSync(join(BACKEND, '.env.example'), join(BACKEND, '.env'))
  console.log('\x1b[33m! Se creó backend/.env desde .env.example: complete las credenciales de SQL Server.\x1b[0m')
}

// ── 2. Frontend: dependencias ─────────────────────────────────────────────
const bloqueo = join(FRONTEND, 'package-lock.json')
const marcaNpm = join(FRONTEND, 'node_modules', '.requisitos_instalados')
if (!existsSync(join(FRONTEND, 'node_modules')) || necesitaInstalar(bloqueo, marcaNpm)) {
  paso('Instalando las dependencias de la aplicación web ...')
  if (!ejecutar(NPM, ['install', '--no-fund', '--no-audit'], FRONTEND))
    fallar('Falló la instalación de las dependencias de la web.')
  writeFileSync(marcaNpm, huella(bloqueo))
}

// ── 3. SQL Server (opcional, si hay Docker) ───────────────────────────────
spawnSync('docker', ['start', 'vicmar-sqlserver'], { stdio: 'ignore' })

// ── 4. API y web en paralelo ──────────────────────────────────────────────
paso(`Levantando la API (http://localhost:${PUERTO_API}/docs) y la web (http://localhost:3000) ...`)
const procesos = []
function lanzar(nombre, color, comando, args, cwd) {
  const p = spawn(...orden(comando, args), { cwd, env: ENTORNO })
  const prefijo = `\x1b[${color}m[${nombre}]\x1b[0m `
  const imprimir = (flujo) => (datos) =>
    datos.toString().split(/\r?\n/).filter(Boolean).forEach((l) => flujo.write(prefijo + l + '\n'))
  p.stdout.on('data', imprimir(process.stdout))
  p.stderr.on('data', imprimir(process.stderr))
  p.on('exit', (codigo) => {
    console.log(`${prefijo}terminó (código ${codigo}).`)
    detener()
  })
  procesos.push(p)
}

let deteniendo = false
function detener() {
  if (deteniendo) return
  deteniendo = true
  for (const p of procesos) {
    if (p.exitCode !== null) continue
    if (WINDOWS) spawnSync('taskkill', ['/pid', String(p.pid), '/T', '/F'], { stdio: 'ignore' })
    else p.kill('SIGTERM')
  }
  process.exit(0)
}
process.on('SIGINT', detener)
process.on('SIGTERM', detener)

lanzar('api', '35', PYTHON, ['-m', 'uvicorn', 'main:app', '--reload', '--port', PUERTO_API], BACKEND)
lanzar('web', '32', NPM, ['run', 'dev'], FRONTEND)
