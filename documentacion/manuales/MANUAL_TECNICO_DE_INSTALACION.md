# Manual técnico de instalación

**Sistema:** VicMar · alerta temprana del abandono en estudiantes universitarios con aprendizaje automático y consulta conversacional
**Versión del documento:** 3.0 · octubre de 2026 (corresponde a la versión 3 del prototipo)
**Autores:** Marlon David Pérez Almachi · Víctor Manuel Lluilema Pisco
**Institución:** Universidad Estatal de Milagro · Facultad de Ciencias e Ingenierías

**Para quién es:** el personal de TI que instala, configura y verifica el sistema en una computadora con Windows 10 u
11. No hace falta conocer el código. Los comandos se escriben en una consola (`cmd` o PowerShell) desde la carpeta
raíz del proyecto, salvo que el paso indique otra cosa.

---

## 1. Las piezas del sistema

| Pieza | Qué es | Dónde vive | Puerto |
|---|---|---|---|
| **Aplicación web** | React 18 + TypeScript + Vite; es lo que usan las personas | `codigo_fuente/frontend/` | `3000` |
| **API** | FastAPI: sesiones, panel, estudiantes, seguimiento, consulta conversacional, reportes y administración (27 servicios) | `codigo_fuente/backend/` | `8090` |
| **Procesos por lotes** | Carga de datos, ETL, entrenamiento, calificación, segmentación y reportes (`scripts/pipeline.py`) | `codigo_fuente/backend/` | |
| **Base de datos** | SQL Server 2022 en el contenedor Docker `vicmar-sqlserver` | Docker | según `DB_HOST` (por defecto `1433`) |

```
 Navegador ──▶ Aplicación web :3000 ──/api──▶ API :8090 ──chat_reader / app_seguimiento──▶ SQL Server (Docker)
                                                 └──▶ Proveedores de IA (Gemini → Groq → NVIDIA NIM → DeepSeek)
 Procesos por lotes ──cuenta de administración──▶ SQL Server
```

La API nunca usa la cuenta de administración: lee con `chat_reader` (solo vistas `VIS_*`) y registra el seguimiento
con `app_seguimiento` (solo dos procedimientos).

---

## 2. Requisitos

| # | Programa | Dónde se obtiene | Cómo comprobarlo |
|---|---|---|---|
| 1 | **Docker Desktop** | <https://www.docker.com/products/docker-desktop/> | `docker version` |
| 2 | **Python 3.14** (o 3.13), con «Add python.exe to PATH» | <https://www.python.org/downloads/> | `py -3.14 --version` |
| 3 | **Node.js 20** o superior | <https://nodejs.org/> | `node --version` |
| 4 | **ODBC Driver 18 for SQL Server** | <https://learn.microsoft.com/es-es/sql/connect/odbc/download-odbc-driver-for-sql-server> | Aparece en «Orígenes de datos ODBC» |
| 5 | **Git** (para clonar) | <https://git-scm.com/> | `git --version` |

Hardware recomendado: 8 GB de RAM (SQL Server usa unos 2 GB) y 10 GB libres en disco. El entrenamiento completo de
las dos instituciones tarda alrededor de una hora en un equipo de escritorio.

---

## 3. Obtener el proyecto

```bat
git clone https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI.git
cd PROYECTO-TITULACION-MARLON-VICTOR-UNEMI
```

Desde una copia: copie la carpeta **sin** `node_modules/`, `venv/`, `dist/` ni `datos_locales/`, que se regeneran.

**Datos reales opcionales (OULAD):** descargue el dataset de la Open University y descomprima sus CSV en
`datos\externos\oulad\` como indica [`datos/README.md`](../../datos/README.md). Sin esos archivos, el sistema funciona
solo con `UNEMI_PRUEBAS` usando la opción `--sin-oulad`.

---

## 4. Configuración (`codigo_fuente\backend\.env`)

```bat
copy codigo_fuente\backend\.env.example codigo_fuente\backend\.env
notepad codigo_fuente\backend\.env
```

El archivo nunca se sube al repositorio. Cada variable está explicada dentro de él; estas son las que importan:

| Variable | Qué poner | Obligatoria |
|---|---|---|
| `DB_HOST` | `localhost,1433`, o el puerto que use el contenedor | Sí |
| `DB_USER` / `DB_PASSWORD` | `sa` y la contraseña con la que se crea el contenedor (paso 5) | Sí |
| `CHAT_READER_PASSWORD`, `APP_SEGUIMIENTO_PASSWORD`, `JWT_SECRET_KEY` | Si quedan vacías, el pipeline las genera al azar y las escribe en el `.env` sin mostrarlas | No |
| `GEMINI_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`, `DEEPSEEK_API_KEY` | Al menos una clave para las preguntas fuera de las 40 métricas certificadas | Para la consulta generada con IA |
| `APP_ENV` | `development`; en `production` la API no arranca con la llave JWT de desarrollo | No |

> [!IMPORTANT]
> La contraseña de `sa` debe cumplir la política de SQL Server: 8 o más caracteres con mayúsculas, minúsculas,
> números y símbolos. Si no la cumple, el contenedor se detiene al arrancar.

Sin ninguna clave de IA el sistema funciona completo: paneles, fichas, seguimiento, reportes y las 40 métricas
certificadas de la consulta conversacional.

---

## 5. Crear el contenedor de SQL Server (una sola vez)

```bat
docker run -d --name vicmar-sqlserver --restart unless-stopped -p 1433:1433 ^
  -e ACCEPT_EULA=Y -e MSSQL_PID=Developer -e "MSSQL_SA_PASSWORD=<DB_PASSWORD>" ^
  mcr.microsoft.com/mssql/server:2022-latest
```

Compruebe con `docker ps` que `vicmar-sqlserver` aparece en estado `Up`. Si el puerto 1433 está ocupado, use por
ejemplo `-p 14330:1433` y `DB_HOST=localhost,14330`.

---

## 6. Reconstruir el sistema

```bat
codigo_fuente\scripts\reconstruir_sistema.bat
```

El script crea el entorno virtual de Python, instala las dependencias fijadas, inicia Docker Desktop y el contenedor si
están apagados y ejecuta el orquestador `python -m scripts.pipeline`, que registra cada paso en
`backend\datos_locales\` y se detiene en el primero que falle, indicando cómo retomarlo.

| # | Paso | Resultado |
|---|---|---|
| 1 | `entorno` | Completa en el `.env` las variables de la versión 3 que falten |
| 2 | `conexion` | Espera a que SQL Server acepte conexiones |
| 3 | `unemi` | Base operativa `UNEMI_PRUEBAS` (sintética, semilla fija) |
| 4 | `oulad` | Base operativa `OULAD_PRUEBAS` en cortes de 28 días |
| 5 | `esquema` | Almacén `ALMACEN_ACADEMICO`, vistas `VIS_*`, procedimientos y cuentas `chat_reader` y `app_seguimiento` |
| 6 | `etl` | ETL de cada institución con su perfil de mapeo, con control de calidad |
| 7 | `referentes` | Tasas de abandono publicadas, con DOI |
| 8 | `entrenar` | Cuatro algoritmos, validación cruzada agrupada, prueba temporal, calibración y umbrales |
| 9 | `calificar` | Probabilidad, nivel, razones SHAP y deriva (PSI) de cada estudiante activo |
| 10 | `segmentar` | Segmentos de carreras con K-means |
| 11 | `reportes` | Figuras de validación, exploración y evaluación prospectiva |
| 12 | `diccionario` | `documentacion/tecnica/DICCIONARIO_DE_DATOS.md` |
| 13 | `usuarios` | Cuentas de demostración, una por rol |
| 14 | `pruebas` | Pruebas automáticas del backend |
| 15 | `consulta` | (Solo con `--con-consulta`) evaluación del conjunto dorado con los proveedores de IA |

| Opción | Efecto |
|---|---|
| `--con-consulta` | Agrega el paso 15; consume cuota de los proveedores de IA |
| `--rapido` | Menos combinaciones de hiperparámetros (demostraciones) |
| `--desde PASO` | Retoma desde un paso, por ejemplo `--desde calificar` |
| `--solo PASO1,PASO2` | Ejecuta solo esos pasos |
| `--sin-oulad` | Omite la institución OULAD_UK |
| `--reentrenar INST1,INST2` | Entrena solo esas instituciones; las demás conservan su modelo |

---

## 7. Cuentas de la aplicación

El paso `usuarios` crea tres cuentas de demostración con contraseñas aleatorias que se guardan **solo** en
`codigo_fuente\backend\datos_locales\usuarios_demo.local.json`:

| Usuario | Rol | Uso |
|---|---|---|
| `autoridad.demo` | Autoridad académica | Decanato o dirección de carrera |
| `bienestar.demo` | Bienestar estudiantil | Tutoría y consejería; registra intervenciones |
| `admin.ti` | Administración de TI | Cuentas, auditoría y estado del sistema |

Para generar contraseñas nuevas: `cd codigo_fuente\backend` y `venv\Scripts\python -m scripts.crear_usuarios_demo --restablecer`.
Las cuentas reales se crean desde **Usuarios y roles** con `admin.ti`.

---

## 8. Encender y apagar el sistema

```bat
codigo_fuente\scripts\levantar_sistema.bat
```

Inicia el contenedor, abre la API en una ventana y la aplicación web en otra (instala lo que falte con `npm install`).
Abra <http://localhost:3000>. Para apagar: cierre las dos ventanas y, si quiere, `docker stop vicmar-sqlserver`.

---

## 9. Verificación de la instalación

| # | Qué comprobar | Cómo | Resultado esperado |
|---|---|---|---|
| 1 | La API está viva | <http://127.0.0.1:8090/api/salud> | `{"estado": "ok", "version": "3...", "proveedores_ia": [...]}` |
| 2 | La API está documentada | <http://127.0.0.1:8090/docs> | Swagger UI con los 27 servicios |
| 3 | Ingreso | Entrar con `autoridad.demo` | Se abre el **Panel ejecutivo** con el saludo y la fecha de calificación |
| 4 | Datos de la primera institución | Selector de institución → `UNEMI_PRUEBAS` | Indicadores con estudiantes en riesgo alto, medio y bajo |
| 5 | Segunda institución | Selector → `OULAD_UK` | El mismo panel con los datos de la Open University |
| 6 | Consulta conversacional | Preguntar «¿Cuántos estudiantes están en riesgo alto?» | Respuesta con la etiqueta **Métrica certificada** |
| 7 | Estado de los procesos | Entrar con `admin.ti` → **Estado del sistema** | Todos los pasos de la última corrida en verde |

La [Guía de pruebas de aceptación](GUIA_DE_PRUEBAS_DE_ACEPTACION.md) amplía esta verificación.

---

## 10. Pruebas automáticas

```bat
cd codigo_fuente\backend
venv\Scripts\python -m pytest -q          :: 153 pruebas; las 8 de integración se omiten sin SQL Server
cd ..\frontend
npm test                                  :: 11 pruebas de la interfaz (vitest)
npm run build                             :: verificación de tipos y compilación de producción
```

---

## 11. Respaldo y traslado de la base

```bat
docker commit vicmar-sqlserver vicmar-sqlserver-respaldo:AAAA-MM-DD
docker save -o vicmar-respaldo-AAAA-MM-DD.tar vicmar-sqlserver-respaldo:AAAA-MM-DD
```

En la computadora nueva: `docker load -i vicmar-respaldo-AAAA-MM-DD.tar` y `docker run` como en el paso 5 con la
imagen `vicmar-sqlserver-respaldo:AAAA-MM-DD`. El `.env` debe conservar las contraseñas del contenedor original.
Copie también `backend\datos_locales\` (cuentas de usuario) y `backend\ml\modelos\` (modelos entrenados).

---

## 12. Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| `pyodbc` no encuentra «ODBC Driver 18» | Falta el controlador | Instalarlo (requisito 4) y abrir una consola nueva |
| El pipeline se queda en «Esperando a que SQL Server acepte conexiones» | Contenedor apagado o `DB_HOST` con otro puerto | `docker ps`; `docker start vicmar-sqlserver`; revisar `DB_HOST` y `DB_PASSWORD` |
| El contenedor se detiene al crearlo | La contraseña de `sa` no cumple la política | Crearlo de nuevo con una contraseña más fuerte |
| Docker Desktop no arranca por un socket dañado | Apagado brusco | Cerrar Docker Desktop y **renombrar** `%LOCALAPPDATA%\Docker\run`. **Nunca** usar «Reset to factory defaults»: borra el contenedor y sus bases |
| Puerto `3000` u `8090` ocupado | Otro programa lo usa | Cambiar `port` en `vite.config.ts` o el `--port` de la API junto con `VITE_BACKEND_URL` |
| El pipeline se detiene en `oulad` | Faltan los CSV | Descargarlos (ver `datos/README.md`) o usar `--sin-oulad` |
| La consulta dice que ningún proveedor de IA está disponible | Sin claves o cuota agotada | Agregar otra clave en el `.env`; las métricas certificadas siguen respondiendo |
| El panel dice «Todavía no hay estudiantes calificados» | No se ejecutaron `entrenar` y `calificar` | `reconstruir_sistema.bat --desde entrenar` |
| `ModuleNotFoundError` | Se usó el Python del sistema | Usar `codigo_fuente\backend\venv\Scripts\python` |

---

## 13. Seguridad y privacidad (LOPDP)

- **Credenciales:** `.env` y `datos_locales\` nunca se versionan. Cambie las contraseñas de `sa` y de las cuentas de
  demostración antes de usar datos reales.
- **Mínimo privilegio:** la API lee con `chat_reader` (solo vistas) y escribe el seguimiento con `app_seguimiento`
  (solo dos procedimientos). Cada vista filtra por la institución fijada en `SESSION_CONTEXT` al abrir la conexión;
  sin institución no devuelve filas.
- **Consulta conversacional:** el SQL generado por la IA se valida sobre su árbol sintáctico (una sola sentencia
  de lectura y solo sobre vistas autorizadas) antes de ejecutarse con `chat_reader`. A los proveedores
  se envían la pregunta, el esquema de las vistas y ejemplos; filas, y solo seudonimizadas, únicamente si la persona
  pide **Interpretar con IA**.
- **Datos de prueba:** `UNEMI_PRUEBAS` es sintético (cédulas con código de provincia `00`, que el Registro Civil no
  asigna). OULAD es público y anónimo (CC BY 4.0) y no se redistribuye.
- **Sesiones y accesos:** JWT con vencimiento de 8 horas; 5 intentos fallidos bloquean 5 minutos; cada ingreso,
  ficha, consulta y exportación queda en la auditoría.

---

## 14. Referencia rápida

| Acción | Comando |
|---|---|
| Reconstruir todo | `codigo_fuente\scripts\reconstruir_sistema.bat` |
| Retomar desde un paso | `codigo_fuente\scripts\reconstruir_sistema.bat --desde calificar` |
| Evaluar la consulta con IA | `codigo_fuente\scripts\reconstruir_sistema.bat --solo consulta --con-consulta` |
| Encender | `codigo_fuente\scripts\levantar_sistema.bat` |

| Servicio | Dirección |
|---|---|
| Aplicación | <http://localhost:3000> |
| Salud de la API | <http://127.0.0.1:8090/api/salud> |
| Documentación de la API | <http://127.0.0.1:8090/docs> |
| SQL Server | según `DB_HOST` |
