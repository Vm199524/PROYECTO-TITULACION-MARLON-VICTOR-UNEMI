/* ============================================================================
   Capa de consulta alternativa para Metabase (inteligencia de negocios clásica)
   ----------------------------------------------------------------------------
   Metabase no fija SESSION_CONTEXT, así que no puede usar las vistas VIS_* de la
   consulta conversacional (devolverían cero filas). Esta capa expone SOLO datos
   agregados, sin cédula, nombres ni ningún identificador personal, en el esquema
   «bi», y una cuenta propia de solo lectura sobre ese esquema:

     bi.VIS_BI_ABANDONO_PERIODO   matriculados y retirados por institución, carrera y periodo
     bi.VIS_BI_RIESGO_CARRERA     estudiantes activos por nivel de riesgo y carrera
     bi.VIS_BI_EVALUACION_MODELO  métricas publicadas del modelo (validación y monitoreo)

   Control de reidentificación: los grupos con menos de 5 estudiantes no se
   publican (supresión de celdas pequeñas, k = 5).

   Ejecución (después de crear_almacen_academico.sql), con METABASE_DB_PASSWORD
   definida en backend/.env:
       cd backend
       python -m scripts.ejecutar_sql ../base_de_datos/crear_vistas_metabase.sql

   Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
   Proyecto de titulación · Universidad Estatal de Milagro · 2026
   ========================================================================== */
USE ALMACEN_ACADEMICO;
GO
IF SCHEMA_ID('bi') IS NULL EXEC('CREATE SCHEMA bi');
GO

CREATE OR ALTER VIEW bi.VIS_BI_ABANDONO_PERIODO AS
SELECT fm.institucion_codigo, di.nombre AS institucion, dc.facultad_nombre, dc.carrera,
       dp.periodo_codigo AS periodo_academico, dp.fecha_inicio AS inicio_periodo,
       COUNT(DISTINCT fm.alumno_id) AS matriculados,
       COUNT(DISTINCT CASE WHEN fm.estado_codigo = 'RETIRADO' THEN fm.alumno_id END) AS retirados,
       CAST(COUNT(DISTINCT CASE WHEN fm.estado_codigo = 'RETIRADO' THEN fm.alumno_id END) AS DECIMAL(12,4))
           / NULLIF(COUNT(DISTINCT fm.alumno_id), 0) AS tasa_retiro,
       AVG(CAST(fm.promedio AS DECIMAL(9,4))) AS promedio_medio,
       AVG(CAST(fm.asistencia_pct AS DECIMAL(9,4))) AS asistencia_media
FROM dbo.fact_matriculas fm
JOIN dbo.dim_institucion di       ON di.institucion_codigo = fm.institucion_codigo
JOIN dbo.dim_carrera dc           ON dc.carrera_id = fm.carrera_id
JOIN dbo.dim_periodo_academico dp ON dp.periodo_id = fm.periodo_id
GROUP BY fm.institucion_codigo, di.nombre, dc.facultad_nombre, dc.carrera, dp.periodo_codigo, dp.fecha_inicio
HAVING COUNT(DISTINCT fm.alumno_id) >= 5;
GO

CREATE OR ALTER VIEW bi.VIS_BI_RIESGO_CARRERA AS
SELECT fp.institucion_codigo, dc.facultad_nombre, dc.carrera, fp.riesgo_categoria,
       COUNT(*) AS estudiantes, AVG(CAST(fp.probabilidad AS DECIMAL(9,4))) AS probabilidad_media,
       MAX(fp.fecha_calculo) AS fecha_calculo, MAX(fp.modelo_version) AS modelo_version
FROM dbo.fact_prediccion_abandono fp
JOIN dbo.fact_matriculas fm ON fm.matricula_id = fp.matricula_id_base
JOIN dbo.dim_carrera dc     ON dc.carrera_id = fm.carrera_id
GROUP BY fp.institucion_codigo, dc.facultad_nombre, dc.carrera, fp.riesgo_categoria
HAVING COUNT(*) >= 5;
GO

CREATE OR ALTER VIEW bi.VIS_BI_EVALUACION_MODELO AS
SELECT institucion_codigo, componente, modelo, esquema_validacion, metrica, valor, desviacion, grupo,
       es_modelo_final, fecha_calculo, modelo_version
FROM dbo.fact_evaluacion_modelo;
GO

-- ── Cuenta de solo lectura para Metabase ─────────────────────────────────
USE master;
GO
IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = 'metabase_lector')
    EXEC('CREATE LOGIN metabase_lector WITH PASSWORD = ''$(metabase_password)'', CHECK_POLICY = ON, DEFAULT_DATABASE = ALMACEN_ACADEMICO');
ELSE
    EXEC('ALTER LOGIN metabase_lector WITH PASSWORD = ''$(metabase_password)'', CHECK_POLICY = ON');
GO
USE ALMACEN_ACADEMICO;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'metabase_lector')
    CREATE USER metabase_lector FOR LOGIN metabase_lector;
GO
-- Solo el esquema bi: ni las tablas físicas (dbo) ni las vistas con datos personales.
GRANT SELECT ON SCHEMA::bi TO metabase_lector;
DENY SELECT ON SCHEMA::dbo TO metabase_lector;
GO
