# Base de datos de pruebas (Docker local)

Datos de conexión para el SQL Server 2022 que corre en Docker en esta
máquina, usado para desarrollo y pruebas de este proyecto de tesis.

## Cómo levantarlo

```bash
docker start vicmar-sqlserver
```

(Si el contenedor no existe todavía, ver la sección "Recrear el contenedor"
más abajo.)

## Datos de conexión

Desde la pantalla **Orígenes de Datos** del frontend, el selector "Nombre
del servidor" ya trae esta entrada precargada ("Docker Local — Base de
Pruebas") — selecciónala y solo falta escribir la contraseña.

| Campo | Valor |
|---|---|
| Servidor | `localhost,1433` |
| Autenticación | SQL Server Authentication |
| Usuario | `sa` |
| Contraseña | La de `codigo_fuente/backend/.env` → `DB_PASSWORD` (no se escribe aquí: los documentos se versionan en git) |
| Driver ODBC | `ODBC Driver 18 for SQL Server` |

## Bases de datos disponibles en este servidor

| Base | Contenido | Tablas/vistas |
|---|---|---|
| `ALIM` | Vacía — reservada para datos reales de una empresa | 0 |
| `UNEMI_PRUEBAS` | 14.508 alumnos y 83.678 registros alumno-semestre. **Datos sintéticos y anonimizados** (Avance 2): cédulas ficticias con código de provincia 00 (no asignable a ninguna persona) y nombres ficticios; el padrón electoral original ya no está en la base ni en el repositorio | `dbo.alumnos_prueba`, `dbo.historial_matriculas` |
| `OULAD_PRUEBAS` | Segunda institución: Open University Learning Analytics Dataset (Kuzilek et al., 2017, CC BY 4.0), transformado a bloques de 28 días por `codigo_fuente/backend/scripts/seed_oulad.py` | `dbo.historial_bloques` (189.299 filas), `dbo.verdad_futura` (desenlace real de 2014J, solo para evaluación) |
| `CHAT` | Almacén en esquema estrella, poblado por ETL desde las dos bases anteriores (perfiles `UNEMI_PRUEBAS` y `OULAD_UK`). Es lo único que consulta el motor de IA | `dim_*`, `fact_matriculas`, `fact_prediccion_abandono`, `fact_cluster_carrera`, `fact_evaluacion_modelo`, `fact_benchmark_externo` + vistas `VIS_ALUMNO`, `VIS_PREDICCION_ABANDONO`, `VIS_CLUSTER_CARRERA`, `VIS_BENCHMARK_EXTERNO`, `VIS_EVALUACION_MODELO` |

El diccionario de datos completo, generado desde el esquema real, está en
[DICCIONARIO_DE_DATOS.md](DICCIONARIO_DE_DATOS.md).

Para reconstruir todo (bases, ETL, modelos, referentes y pruebas) en un solo paso:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo_tesis.ps1
```

## "Explorar" vs. "Catálogo" en el frontend

Son dos mecanismos **distintos**, no lo mismo con otro nombre:

- **Explorar** ejecuta `SELECT name FROM sys.databases` — lista TODAS las
  bases físicas del servidor sin filtrar. Con las credenciales de arriba,
  esto **sí muestra** `ALIM`, `UNEMI_PRUEBAS` y `CHAT`.
- **Catálogo** busca una base llamada `PROYECTO` con una tabla `sys300`
  (nombres comerciales/RUC de empresas reales). Ese mecanismo es para
  cuando existe un catálogo maestro de empresas en el servidor — **este
  servidor de pruebas no tiene una base `PROYECTO`**, así que el botón
  Catálogo siempre devolverá vacío aquí. No es un error: es el
  comportamiento correcto para un servidor sin catálogo maestro.

## Login de solo lectura para el motor de IA

`chat_reader` — usado internamente por el backend para ejecutar el SQL que
genera la IA contra `CHAT` (nunca contra `ALIM`/`UNEMI_PRUEBAS`). No hace
falta usarlo manualmente; está documentado en
`codigo_fuente/backend/.env` → `CHAT_READER_USER`/`CHAT_READER_PASSWORD` y explicado en el
diseño de seguridad de la Capa 1 (ver conversación / `main.py::execute_chat_query`).

## Recrear el contenedor (si se perdió)

```bash
docker run -d --name vicmar-sqlserver \
  -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=<DB_PASSWORD de codigo_fuente/backend/.env>" \
  -p 1433:1433 --restart unless-stopped \
  mcr.microsoft.com/mssql/server:2022-latest
```

Luego ejecutar `scripts\demo_tesis.ps1`, que crea `UNEMI_PRUEBAS`, `OULAD_PRUEBAS` y `CHAT`
y recarga todos los datos. Nota: si Docker Desktop no arranca por un socket dañado en
`%LOCALAPPDATA%\Docker\run` o `%LOCALAPPDATA%\docker-secrets-engine` (error "The file cannot
be accessed by the system"), cerrar Docker Desktop y **renombrar** esas carpetas; nunca usar
"Reset to factory defaults", que borra el contenedor y sus bases.
