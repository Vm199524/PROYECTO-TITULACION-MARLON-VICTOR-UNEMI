# Bases de datos de prueba (SQL Server en Docker)

El prototipo usa un SQL Server 2022 local en el contenedor `vicmar-sqlserver`. Las credenciales
nunca se escriben en los documentos: se leen de `codigo_fuente/backend/.env` (`DB_HOST`,
`DB_USER`, `DB_PASSWORD`, `CHAT_READER_*`, `APP_SEGUIMIENTO_*`).

## Bases del servidor

| Base | Contenido | Objetos |
|---|---|---|
| `UNEMI_PRUEBAS` | Base operativa de prueba con la estructura de la UNEMI: 14.508 estudiantes y 79.268 registros estudiante-semestre (2019-1 a 2026-1). **Datos sintéticos**: cédulas ficticias con código de provincia 00 y nombres ficticios | `dbo.alumnos_prueba`, `dbo.historial_matriculas` |
| `OULAD_PRUEBAS` | Base operativa de la Open University (Kuzilek et al., 2017, CC BY 4.0) transformada a cortes de 28 días por `scripts/cargar_oulad.py` | `dbo.historial_bloques` (189.299 filas), `dbo.verdad_futura` (desenlace real de 2014J, solo para la evaluación prospectiva; no pasa al almacén) |
| `ALMACEN_ACADEMICO` | Almacén en esquema estrella poblado por el ETL de ambas bases (perfiles `UNEMI_PRUEBAS` y `OULAD_UK`). Es lo único que leen la API y la consulta conversacional | `dim_*`, `fact_matriculas`, `fact_prediccion_abandono`, `fact_segmento_carrera`, `fact_evaluacion_modelo`, `fact_intervencion`, `fact_referente_externo` y vistas `VIS_*` |

El diccionario completo está en [DICCIONARIO_DE_DATOS.md](DICCIONARIO_DE_DATOS.md).

## Cómo se generan los datos de prueba

`codigo_fuente/base_de_datos/datos_de_prueba/generate_historial.py` simula la trayectoria de cada
estudiante con factores latentes (capacidad, compromiso, vulnerabilidad económica) y un componente
que el sistema no observa; el riesgo de retiro sigue una función logística no lineal y aplica la
regla de la tercera matrícula. La semilla fija (20260909) hace el conjunto reproducible. Los
coeficientes se documentan en el Avance 2 (sección 3.1.3).

## Cuentas de la base

| Cuenta | Permisos | Uso |
|---|---|---|
| Administración (`DB_USER`) | Crea las bases y ejecuta los procesos por lotes | Pipeline |
| `chat_reader` | `SELECT` solo sobre las vistas `VIS_*` | API y consulta conversacional |
| `app_seguimiento` | `EXECUTE` solo sobre `sp_registrar_intervencion` y `sp_cerrar_intervencion` | Registro del seguimiento |

Ambas cuentas de la aplicación leen la institución activa de `SESSION_CONTEXT`, que la API fija
en cada conexión y que no se puede cambiar dentro de la sesión.

## Reconstruir todo

```bat
codigo_fuente\scripts\reconstruir_sistema.bat
```

Si el contenedor no existe todavía, créelo una sola vez (el puerto debe coincidir con `DB_HOST`):

```bash
docker run -d --name vicmar-sqlserver -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=<DB_PASSWORD>" ^
  -p 1433:1433 --restart unless-stopped mcr.microsoft.com/mssql/server:2022-latest
```

Si Docker Desktop no arranca por un socket dañado en `%LOCALAPPDATA%\Docker\run`, cierre Docker
Desktop y renombre esa carpeta; no use «Reset to factory defaults», que borra el contenedor y sus
bases.
