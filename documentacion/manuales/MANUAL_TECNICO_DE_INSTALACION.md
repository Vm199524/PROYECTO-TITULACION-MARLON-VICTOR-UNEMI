# Manual técnico de instalación

**Sistema:** VicMar Data AI — predicción del abandono estudiantil con inteligencia de negocios y consultas en lenguaje natural
**Versión del documento:** 1.0 · octubre de 2026
**Autores:** Marlon David Pérez Almachi · Víctor Manuel Lluilema Pisco
**Institución:** Universidad Estatal de Milagro · Facultad de Ciencias e Ingenierías

**Para quién es:** el personal de TI que recibe el sistema y debe instalarlo, configurarlo y verificarlo en una computadora con Windows 10 u 11. No hace falta conocer el código. Siga los pasos en orden; los comandos se escriben en **PowerShell**, uno a la vez, desde la carpeta raíz del proyecto, salvo que el paso indique otra cosa.

---

## 1. Las tres piezas del sistema

| Pieza | Qué es | Dónde vive | Puerto |
|---|---|---|---|
| **Frontend** | La aplicación web (React + Vite) que usan las personas | `codigo_fuente/frontend/` | `3000` |
| **Backend** | API FastAPI: modelo predictivo, consultas en lenguaje natural, seguridad | `codigo_fuente/backend/` | `8090` |
| **Base de datos** | SQL Server 2022 dentro de un contenedor Docker | contenedor `vicmar-sqlserver` | `1433` |

Las tres deben estar encendidas al mismo tiempo: la aplicación web habla con el backend y el backend con la base de datos.

```
 Navegador ──▶ Frontend :3000 ──/api──▶ Backend :8090 ──▶ SQL Server :1433 (Docker)
                                            └──▶ Proveedores de IA (Gemini → Groq → NVIDIA NIM)
```

---

## 2. Requisitos

| # | Programa | Dónde se obtiene | Cómo comprobarlo |
|---|---|---|---|
| 1 | **Docker Desktop** | <https://www.docker.com/products/docker-desktop/> | Abrirlo y esperar a que el ícono de la ballena quede quieto; `docker version` |
| 2 | **Node.js 22 LTS** o superior | <https://nodejs.org/> | `node --version` |
| 3 | **Python 3.14** (marcar «Add python.exe to PATH») | <https://www.python.org/downloads/> | `py -3.14 --version` |
| 4 | **ODBC Driver 18 for SQL Server** | <https://learn.microsoft.com/es-es/sql/connect/odbc/download-odbc-driver-for-sql-server> | Aparece en «Orígenes de datos ODBC» de Windows |
| 5 | **Git** (solo si se clona desde GitHub) | <https://git-scm.com/> | `git --version` |

Hardware recomendado: 8 GB de RAM (SQL Server usa unos 2 GB) y 10 GB libres en disco.

---

## 3. Obtener el proyecto

- **Desde GitHub** (repositorio privado; requiere permiso de acceso):
  ```powershell
  git clone https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI.git
  cd PROYECTO-TITULACION-MARLON-VICTOR-UNEMI
  ```
- **Desde una copia** (carpeta comprimida o memoria USB): copiar la carpeta del proyecto **sin** `node_modules/`, `venv/` ni `dist/`, que se regeneran en la computadora nueva.

---

## 4. Configuración local

Estos archivos guardan contraseñas y claves, por eso **nunca se suben al repositorio**. Se crean a partir de sus plantillas:

```powershell
copy codigo_fuente\backend\.env.example codigo_fuente\backend\.env
copy codigo_fuente\backend\usuarios_prueba.example.json codigo_fuente\backend\usuarios_prueba.local.json
```

### 4.1 `codigo_fuente\backend\.env`

Ábralo con el Bloc de notas. Cada variable está explicada dentro del archivo; estas son las imprescindibles:

| Variable | Qué poner | Obligatoria |
|---|---|---|
| `DB_HOST` | `localhost,1433` (el contenedor de este manual) | Sí |
| `DB_USER` / `DB_PASSWORD` | `sa` y la contraseña que se usará al crear el contenedor (paso 5) | Sí |
| `CHAT_READER_PASSWORD` | Contraseña de la cuenta de **solo lectura** que ejecuta el SQL de la IA (la crea el pipeline) | Sí |
| `GEMINI_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY` | Al menos una clave gratuita de proveedor de IA | Para el chat |
| `JWT_SECRET_KEY` | Una cadena larga y aleatoria: `python -c "import secrets; print(secrets.token_urlsafe(64))"` | En producción |
| `FAL_KEY`, `SMTP_*`, `REDIS_*`, `SENTRY_DSN` | Lectura en voz alta, correo de recuperación, caché y monitoreo | No |

> [!IMPORTANT]
> La contraseña de `sa` debe cumplir la política de SQL Server: al menos 8 caracteres con mayúsculas, minúsculas, números y símbolos. Si no la cumple, el contenedor se detiene al arrancar.

Sin ninguna clave de IA el sistema funciona (paneles, métricas certificadas, administración); solo el chat responde con un aviso.

### 4.2 `codigo_fuente\backend\usuarios_prueba.local.json`

Contiene la contraseña de cada usuario de prueba, uno por rol. Reemplace cada `CAMBIAR_POR_UNA_CONTRASEÑA` por una contraseña de 8 o más caracteres. Las contraseñas de la demostración se entregan aparte, nunca por el repositorio.

---

## 5. Base de datos

### Opción A — Reconstruir todo con el pipeline (recomendada)

1. **Crear el contenedor** de SQL Server con la misma contraseña de `DB_PASSWORD`:
   ```powershell
   docker run -d --name vicmar-sqlserver --restart unless-stopped -p 1433:1433 -e ACCEPT_EULA=Y -e MSSQL_PID=developer -e MSSQL_SA_PASSWORD="SU_CONTRASEÑA" mcr.microsoft.com/mssql/server:2022-latest
   ```
   Compruebe con `docker ps` que `vicmar-sqlserver` aparece con estado `Up`.
2. **Descargar el dataset público OULAD** en `datos\externos\oulad\` siguiendo [`datos/README.md`](../../datos/README.md).
3. **Crear el entorno de Python** del backend:
   ```powershell
   py -3.14 -m venv codigo_fuente\backend\venv
   codigo_fuente\backend\venv\Scripts\pip install -r codigo_fuente\backend\requirements.txt
   ```
4. **Ejecutar el pipeline completo:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File codigo_fuente\scripts\demo_tesis.ps1
   ```

El pipeline hace estos pasos en orden y se detiene si alguno falla:

| # | Paso | Resultado |
|---|---|---|
| 1 | Arranca el contenedor y espera a que SQL Server acepte conexiones | Base de datos lista |
| 2 | Anonimiza los datos de prueba | Datos sin información personal real |
| 3 | Carga `UNEMI_PRUEBAS` (alumnos e historial) | Primera institución |
| 4 | Carga `OULAD_PRUEBAS` | Segunda institución, con datos reales anónimos |
| 5 | Ejecuta `crear_chat_academico.sql` | Almacén `CHAT`, vistas `VIS_*` y usuario `chat_reader` |
| 6 | ETL con los perfiles `UNEMI_PRUEBAS` y `OULAD_UK` | Hechos y dimensiones cargados |
| 7 | Entrena, califica, segmenta y genera las figuras de cada institución | Predicciones y segmentos |
| 8 | Carga los referentes externos | Benchmarking con DOI |
| 9 | Genera el diccionario de datos | `documentacion/tecnica/DICCIONARIO_DE_DATOS.md` |
| 10 | Ejecuta las pruebas principales | Verificación automática |

Opciones del script:

| Opción | Efecto |
|---|---|
| `-Levantar` | Al terminar, abre el backend y el frontend |
| `-ConEvaluacionNL2SQL` | Agrega la evaluación de las 40 preguntas de referencia; consume cuota de los proveedores de IA |

### Opción B — Trasladar el contenedor ya cargado

En la computadora original:
```powershell
docker commit vicmar-sqlserver vicmar-sqlserver-portable:ultima
docker save -o vicmar-sqlserver-respaldo.tar vicmar-sqlserver-portable:ultima
```
En la computadora nueva:
```powershell
docker load -i vicmar-sqlserver-respaldo.tar
docker run -d --name vicmar-sqlserver --restart unless-stopped -p 1433:1433 vicmar-sqlserver-portable:ultima
```
Las contraseñas de `sa` y `chat_reader` son las del contenedor original; `.env` debe usar las mismas.

---

## 6. Usuarios de la aplicación

Los usuarios viven en `codigo_fuente\backend\security_config.json`, que no se versiona. En una instalación nueva el script lo crea con los roles por defecto:

```powershell
cd codigo_fuente\backend
venv\Scripts\python.exe scripts\fijar_passwords_prueba.py
cd ..\..
```

| Usuario | Rol | Qué puede hacer |
|---|---|---|
| `acad` | ACADÉMICO | Panel de riesgo, inteligencia institucional y chat académico |
| `clec` | ADMINISTRADOR | Todo, más la gestión de usuarios y la auditoría |
| `cont` | CONTABILIDAD | Módulos de finanzas y ventas (no ve datos académicos) |
| `rrhh` | RRHH | Módulo de talento humano |
| `logi` | LOGÍSTICA | Módulo de operaciones |
| `demo` | INVITADO | Demostración con datos ficticios, sin conectarse a ninguna base |

Para la cuenta protegida del desarrollador (opcional), la contraseña se pasa explícitamente:
```powershell
cd codigo_fuente\backend
venv\Scripts\python.exe scripts\crear_usuario_desarrollador.py --password "<clave de 8 o más caracteres>"
```

---

## 7. Encender el sistema

Instale las dependencias del frontend la primera vez:
```powershell
cd codigo_fuente\frontend
npm install
```

Luego, cada vez que quiera usar el sistema:

```powershell
docker start vicmar-sqlserver                     # 1. base de datos
cd codigo_fuente\frontend; npm run dev:backend    # 2. backend (terminal 1, déjela abierta)
cd codigo_fuente\frontend; npm run dev            # 3. frontend (terminal 2, déjela abierta)
```

Abra <http://localhost:3000> en el navegador. Para apagar: cierre las dos terminales y ejecute `docker stop vicmar-sqlserver`.

---

## 8. Verificación de la instalación

| # | Qué comprobar | Cómo | Resultado esperado |
|---|---|---|---|
| 1 | El backend está vivo | Abrir <http://127.0.0.1:8090/api/health> | `{"status":"online", ...}` |
| 2 | La API está documentada | Abrir <http://127.0.0.1:8090/docs> | Página «Swagger UI» con las rutas de la API |
| 3 | Inicio de sesión | Entrar con `acad` | Aparece el área de consulta con «Academia · ACADÉMICO» arriba a la derecha |
| 4 | Conexión a la base | Seguir el [Manual de usuario, sección 3](MANUAL_DE_USUARIO.md#3-conectarse-a-la-base-de-datos) | «Conexión establecida con localhost,1433» y 4 bases detectadas |
| 5 | Panel de riesgo | Elegir `UNEMI_PRUEBAS` → **Indicadores** | Tarjeta «Riesgo de abandono estudiantil» con alumnos ALTO, MEDIO y BAJO |
| 6 | Segunda institución | Elegir `OULAD_PRUEBAS` → **Indicadores** | El mismo panel con estudiantes «Estudiante OU …» |
| 7 | Chat | Preguntar «¿Cuántos alumnos hay en cada nivel de riesgo de abandono?» | Tabla con ALTO, MEDIO, BAJO y el total |

La [Guía de pruebas de aceptación](GUIA_DE_PRUEBAS_DE_ACEPTACION.md) amplía esta verificación con todos los casos de prueba.

---

## 9. Pruebas automáticas

```powershell
cd codigo_fuente\backend
venv\Scripts\python.exe -m pytest                       # backend: unitarias e integración
venv\Scripts\python.exe -m eval.evaluar_nl2sql          # 40 preguntas de referencia (usa cuota de IA)

cd ..\frontend
npm test                                                # frontend (vitest)
npm run build                                           # compilación de producción
```

Resultado esperado del backend: todas las pruebas en verde; las de integración se omiten si SQL Server no está disponible. En GitHub las mismas pruebas corren solas con cada cambio (insignia **CI** del README).

---

## 10. Respaldo y restauración de la base

Respaldo del contenedor completo (bases, usuarios y modelos cargados):
```powershell
docker commit vicmar-sqlserver vicmar-sqlserver-respaldo:AAAA-MM-DD
docker save -o vicmar-respaldo-AAAA-MM-DD.tar vicmar-sqlserver-respaldo:AAAA-MM-DD
```
Restauración: igual que la [opción B del paso 5](#opción-b--trasladar-el-contenedor-ya-cargado), con el archivo `.tar` del respaldo.

---

## 11. Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| Error de `pyodbc` u «ODBC Driver» al iniciar el backend | Falta el ODBC Driver 18 | Instalarlo (requisito 4) y abrir una terminal nueva |
| «Conexión rechazada» o «Tiempo de espera agotado» al conectar | El contenedor está apagado o la contraseña no coincide | `docker ps`; `docker start vicmar-sqlserver`; revisar `DB_PASSWORD` en `.env` |
| El contenedor se detiene al crearlo | La contraseña de `sa` no cumple la política | Volver a crearlo con una contraseña más fuerte |
| Docker Desktop no arranca y habla de `dockerInference` o `engine.sock` | Archivos de comunicación dañados tras un apagado brusco | Cerrar Docker Desktop y **renombrar** (no borrar) las carpetas `%LOCALAPPDATA%\Docker\run` y `%LOCALAPPDATA%\docker-secrets-engine`; volver a abrirlo. **Nunca** usar «Reset to factory defaults»: borra el contenedor con todas las bases |
| Puerto `8080` ocupado | Otro programa lo usa | Este sistema usa el `8090` para el backend; no cambie ese valor salvo que también esté ocupado |
| Puerto `1433`, `3000` u `8090` ocupado | Otro programa usa el puerto | Cambiar el mapeo de Docker (`-p 14330:1433` y `DB_HOST=localhost,14330`), el puerto de `vite.config.ts` o el `--port` de `dev:backend` junto con `VITE_BACKEND_URL` |
| El chat responde con un aviso de que ningún proveedor de IA está disponible | Sin claves o cuota agotada | Agregar otra clave gratuita en `.env` o esperar a que se renueve la cuota del día |
| El panel de riesgo no aparece | El usuario no tiene el rol ACADÉMICO o ADMINISTRADOR | Entrar con `acad` o con un administrador |
| `ModuleNotFoundError` al ejecutar un script | Se usó el Python del sistema | Usar `codigo_fuente\backend\venv\Scripts\python.exe` |
| El pipeline se detiene en OULAD | Faltan los CSV en `datos\externos\oulad\` | Descargarlos (ver `datos/README.md`) |

---

## 12. Seguridad y privacidad

- **Credenciales:** `.env`, `security_config.json` y `usuarios_prueba.local.json` nunca se suben al repositorio. Cambie las contraseñas de `sa`, `chat_reader` y de los usuarios antes de usar el sistema con datos reales.
- **Solo lectura para la IA:** el SQL que genera la IA se ejecuta con `chat_reader`, que solo puede leer las vistas `VIS_*`. Cada vista se filtra por la institución de la sesión; sin institución no devuelve nada.
- **Datos de prueba:** `UNEMI_PRUEBAS` es sintético y anonimizado (nombres ficticios; cédulas con el código de provincia «00», que el Registro Civil no asigna). OULAD es público y anónimo (CC BY 4.0).
- **Datos personales:** antes de enviar resultados a un proveedor externo de IA, el sistema reemplaza cédulas y nombres por seudónimos; en pantalla la cédula siempre aparece enmascarada.
- **Sesiones:** se cierran solas tras 30 minutos sin actividad.

---

## 13. Referencia rápida

```powershell
docker start vicmar-sqlserver                      # encender la base de datos
cd codigo_fuente\frontend; npm run dev:backend     # backend (terminal 1)
cd codigo_fuente\frontend; npm run dev             # frontend (terminal 2)
docker stop vicmar-sqlserver                       # apagar la base de datos
```

| Servicio | Dirección |
|---|---|
| Aplicación | <http://localhost:3000> |
| Salud del backend | <http://127.0.0.1:8090/api/health> |
| Documentación de la API | <http://127.0.0.1:8090/docs> |
| SQL Server | `localhost,1433` |
