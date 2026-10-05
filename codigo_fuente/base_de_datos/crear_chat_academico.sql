/*
 * Almacén académico CHAT: esquema estrella, vistas VIS_* y login chat_reader.
 *
 * Crea la base CHAT con tablas físicas (dim_* y fact_*) que puebla el ETL
 * (backend/scripts/etl_academico.py), no vistas que lean en vivo la base operativa.
 * Capa 1 de la seguridad del chat NL2SQL: cada vista VIS_* filtra por
 * SESSION_CONTEXT(N'empresa_activa'), fijado en la misma conexión que ejecuta el
 * SELECT; chat_reader es un login de solo lectura con SELECT únicamente sobre esas
 * vistas y sin usuario en las bases operativas, así el SQL de la IA nunca corre con
 * la cuenta sa. Es re-ejecutable (suelta y recrea los objetos). Uso, desde backend:
 *   python scripts/run_sql_file.py ../base_de_datos/crear_chat_academico.sql
 *
 * Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
 * Proyecto de titulación · Universidad Estatal de Milagro · 2026
 */

IF DB_ID('CHAT') IS NULL
    CREATE DATABASE CHAT;
GO

USE CHAT;
GO

-- Las tablas de hechos se sueltan ANTES que cualquier dimensión: tienen FK
-- hacia ellas, y si el script se re-ejecuta e intenta soltar primero una
-- dimensión, SQL Server lo rechaza con "referenced by a FOREIGN KEY
-- constraint". Este orden no debe cambiar.
IF OBJECT_ID('dbo.fact_prediccion_abandono', 'U') IS NOT NULL DROP TABLE dbo.fact_prediccion_abandono;
IF OBJECT_ID('dbo.fact_cluster_carrera', 'U') IS NOT NULL DROP TABLE dbo.fact_cluster_carrera;
IF OBJECT_ID('dbo.fact_matriculas', 'U') IS NOT NULL DROP TABLE dbo.fact_matriculas;
IF OBJECT_ID('dbo.fact_evaluacion_modelo', 'U') IS NOT NULL DROP TABLE dbo.fact_evaluacion_modelo;
IF OBJECT_ID('dbo.dim_carrera', 'U') IS NOT NULL DROP TABLE dbo.dim_carrera;
-- dim_alumno referencia a dim_empresa: se suelta antes que ella.
IF OBJECT_ID('dbo.dim_alumno', 'U') IS NOT NULL DROP TABLE dbo.dim_alumno;
GO

-- ── Dimensiones ─────────────────────────────────────────────────────────
IF OBJECT_ID('dbo.dim_tiempo', 'U') IS NOT NULL DROP TABLE dbo.dim_tiempo;
CREATE TABLE dbo.dim_tiempo (
    tiempo_id  INT IDENTITY(1,1) PRIMARY KEY,
    fecha      DATE NOT NULL UNIQUE,
    anio       SMALLINT NOT NULL,
    mes        TINYINT NOT NULL,
    trimestre  TINYINT NOT NULL
);

IF OBJECT_ID('dbo.dim_empresa', 'U') IS NOT NULL DROP TABLE dbo.dim_empresa;
CREATE TABLE dbo.dim_empresa (
    empresa_codigo  VARCHAR(30) PRIMARY KEY,
    business_name   NVARCHAR(200) NOT NULL
);

IF OBJECT_ID('dbo.dim_facultad', 'U') IS NOT NULL DROP TABLE dbo.dim_facultad;
CREATE TABLE dbo.dim_facultad (
    facultad_codigo  VARCHAR(20) PRIMARY KEY,
    facultad_nombre  NVARCHAR(200) NOT NULL
);

IF OBJECT_ID('dbo.dim_carrera', 'U') IS NOT NULL DROP TABLE dbo.dim_carrera;
CREATE TABLE dbo.dim_carrera (
    carrera_id       INT IDENTITY(1,1) PRIMARY KEY,
    carrera          NVARCHAR(150) NOT NULL,
    facultad_codigo  VARCHAR(20) NOT NULL REFERENCES dbo.dim_facultad(facultad_codigo),
    CONSTRAINT UQ_dim_carrera UNIQUE (carrera, facultad_codigo)
);

IF OBJECT_ID('dbo.dim_estado_matricula', 'U') IS NOT NULL DROP TABLE dbo.dim_estado_matricula;
CREATE TABLE dbo.dim_estado_matricula (
    estado_codigo  VARCHAR(20) PRIMARY KEY
);

-- Requerimiento "variables relevantes: carrera, sede, ciclo, rendimiento,
-- canal" (ver documentacion/tecnica/PREDICCION_ABANDONO.md, sección 3):
-- sede = campus o extensión física (p. ej., Cuenca/Quito/Guayaquil en una IES
-- multisede), canal = vía de ingreso o modalidad (PRESENCIAL/DISTANCIA/EN
-- LINEA). Una institución de un solo campus o modalidad carga un literal fijo
-- en el SELECT de su perfil (backend/etl/perfiles.py): el modelo funciona con
-- una sola sede, y la columna existe para no requerir otra migración de
-- esquema cuando se conecte una IES multisede real.
IF OBJECT_ID('dbo.dim_sede', 'U') IS NOT NULL DROP TABLE dbo.dim_sede;
CREATE TABLE dbo.dim_sede (
    sede_codigo  VARCHAR(20) PRIMARY KEY,
    sede_nombre  NVARCHAR(100) NOT NULL
);

IF OBJECT_ID('dbo.dim_canal', 'U') IS NOT NULL DROP TABLE dbo.dim_canal;
CREATE TABLE dbo.dim_canal (
    canal_codigo  VARCHAR(20) PRIMARY KEY
);

-- Multiinstitución: la identidad de un alumno es (institución,
-- identificador). Un UNIQUE global sobre `cedula` fusionaría en una sola
-- persona a dos alumnos de instituciones distintas con el mismo
-- identificador. dim_alumno se referencia desde fact_matriculas y
-- fact_prediccion_abandono, que se sueltan al inicio (junto con dim_alumno).
CREATE TABLE dbo.dim_alumno (
    alumno_id          INT IDENTITY(1,1) PRIMARY KEY,
    empresa_codigo     VARCHAR(30) NOT NULL REFERENCES dbo.dim_empresa(empresa_codigo),
    cedula             VARCHAR(15) NOT NULL,
    apellidos          NVARCHAR(100) NOT NULL,
    nombres            NVARCHAR(100) NOT NULL,
    genero             CHAR(1) NOT NULL,
    ciudad_residencia  NVARCHAR(50) NOT NULL,
    CONSTRAINT UQ_dim_alumno_empresa_cedula UNIQUE (empresa_codigo, cedula)
);

-- ── Hechos (grano: una fila por registro de matrícula) ─────────────────
IF OBJECT_ID('dbo.fact_matriculas', 'U') IS NOT NULL DROP TABLE dbo.fact_matriculas;
CREATE TABLE dbo.fact_matriculas (
    fact_id           INT IDENTITY(1,1) PRIMARY KEY,
    empresa_codigo    VARCHAR(30) NOT NULL REFERENCES dbo.dim_empresa(empresa_codigo),
    alumno_id         INT NOT NULL REFERENCES dbo.dim_alumno(alumno_id),
    carrera_id        INT NOT NULL REFERENCES dbo.dim_carrera(carrera_id),
    facultad_codigo   VARCHAR(20) NOT NULL REFERENCES dbo.dim_facultad(facultad_codigo),
    estado_codigo     VARCHAR(20) NOT NULL REFERENCES dbo.dim_estado_matricula(estado_codigo),
    tiempo_id         INT NOT NULL REFERENCES dbo.dim_tiempo(tiempo_id),
    sede_codigo       VARCHAR(20) NOT NULL REFERENCES dbo.dim_sede(sede_codigo),
    canal_codigo      VARCHAR(20) NOT NULL REFERENCES dbo.dim_canal(canal_codigo),
    semestre          TINYINT NOT NULL,
    promedio          DECIMAL(4,2) NOT NULL,
    asistencia_pct    DECIMAL(5,2) NOT NULL,
    monto_matricula   DECIMAL(10,2) NOT NULL,
    beca_porcentaje   TINYINT NOT NULL,
    saldo_pendiente   DECIMAL(10,2) NOT NULL,
    monto_neto        DECIMAL(10,2) NOT NULL,
    es_ultimo_periodo BIT NOT NULL DEFAULT 1
);
CREATE INDEX IX_fact_matriculas_empresa ON dbo.fact_matriculas(empresa_codigo);
CREATE INDEX IX_fact_matriculas_alumno ON dbo.fact_matriculas(alumno_id);
-- Panel alumno-periodo (ml/features_abandono.py::construir_panel) recorre
-- la trayectoria de cada alumno por institución en orden temporal.
CREATE INDEX IX_fact_matriculas_panel ON dbo.fact_matriculas(empresa_codigo, alumno_id, carrera_id, tiempo_id);
GO

-- ── VIS_ALUMNO: vista ESTÁTICA, aislada por SESSION_CONTEXT ─────────────
-- La vista es fija: no se recrea con ALTER VIEW al activar cada empresa,
-- porque eso la convertiría en un objeto global COMPARTIDO y mutable, el
-- patrón que permite que un usuario lea los datos de otra empresa cuando
-- dos consultas corren a la vez. Con SESSION_CONTEXT() el filtro de empresa
-- vive aislado POR CONEXIÓN física: dos usuarios en empresas distintas no
-- pueden pisarse aunque consulten al mismo tiempo. El backend fija ese
-- contexto y ejecuta el SELECT en la MISMA conexión (ver
-- db_connector.py::execute_query_with_context), nunca en pasos separados.
IF OBJECT_ID('dbo.VIS_ALUMNO', 'V') IS NOT NULL DROP VIEW dbo.VIS_ALUMNO;
GO
CREATE VIEW dbo.VIS_ALUMNO AS
SELECT
    da.cedula, da.apellidos, da.nombres, da.genero, da.ciudad_residencia,
    df.facultad_codigo, df.facultad_nombre,
    dc.carrera,
    ds.sede_codigo, ds.sede_nombre, dcanal.canal_codigo,
    dt.fecha AS fecha_matricula, dt.anio, dt.mes, dt.trimestre,
    de.estado_codigo AS estado_matricula,
    fm.semestre, fm.promedio, fm.asistencia_pct, fm.monto_matricula, fm.beca_porcentaje,
    fm.saldo_pendiente, fm.monto_neto, fm.es_ultimo_periodo
FROM dbo.fact_matriculas fm
JOIN dbo.dim_alumno da ON da.alumno_id = fm.alumno_id
JOIN dbo.dim_facultad df ON df.facultad_codigo = fm.facultad_codigo
JOIN dbo.dim_carrera dc ON dc.carrera_id = fm.carrera_id
JOIN dbo.dim_tiempo dt ON dt.tiempo_id = fm.tiempo_id
JOIN dbo.dim_estado_matricula de ON de.estado_codigo = fm.estado_codigo
JOIN dbo.dim_sede ds ON ds.sede_codigo = fm.sede_codigo
JOIN dbo.dim_canal dcanal ON dcanal.canal_codigo = fm.canal_codigo
WHERE fm.empresa_codigo = CAST(SESSION_CONTEXT(N'empresa_activa') AS VARCHAR(30));
GO

-- ── SP_MODIFICA_VISTA_IA: se conserva SOLO por compatibilidad ──────────
-- backend/main.py::_activate_chat_views invoca este SP con la firma
-- exec CHAT.dbo.SP_MODIFICA_VISTA_IA '<empresa>'. No hace ningún ALTER VIEW
-- ni cambia estado global: el aislamiento lo pone SESSION_CONTEXT en la
-- conexión que ejecuta el SELECT (ver VIS_ALUMNO). Solo valida que la
-- empresa exista; RAISERROR con severidad 10 es informativo y no corta el
-- lote.
IF OBJECT_ID('dbo.SP_MODIFICA_VISTA_IA', 'P') IS NOT NULL DROP PROCEDURE dbo.SP_MODIFICA_VISTA_IA;
GO
CREATE PROCEDURE dbo.SP_MODIFICA_VISTA_IA
    @empresa VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT EXISTS (SELECT 1 FROM dbo.dim_empresa WHERE empresa_codigo = @empresa)
        RAISERROR('Empresa no reconocida en el warehouse CHAT: %s', 10, 1, @empresa);
END
GO

-- ── fact_prediccion_abandono: salida del modelo ML (ver backend/ml/) ────
-- Grano: 1 fila por alumno ACTIVO con su probabilidad de abandono más
-- reciente. La puebla backend/ml/predecir_abandono.py con recarga completa
-- por empresa (DELETE filtrado por empresa_codigo + INSERT, el mismo patrón
-- del ETL de fact_matriculas). Vive en CHAT (no en UNEMI_PRUEBAS) porque es
-- un resultado derivado, no un dato operativo.
IF OBJECT_ID('dbo.fact_prediccion_abandono', 'U') IS NOT NULL DROP TABLE dbo.fact_prediccion_abandono;
GO
-- Panel alumno-periodo: la predicción es "probabilidad de que
-- el alumno abandone en el PRÓXIMO periodo", calculada con los datos hasta
-- su periodo más reciente (fact_id_base = esa fila de fact_matriculas, que
-- da carrera, sede, canal y semestre sin ambigüedad aunque un alumno tenga
-- varias matrículas). factor_1..3: las tres variables que más empujaron la
-- probabilidad de ESE alumno hacia el riesgo (SHAP), en lenguaje natural,
-- para que una autoridad no técnica sepa por qué está en la lista.
CREATE TABLE dbo.fact_prediccion_abandono (
    prediccion_id    INT IDENTITY(1,1) PRIMARY KEY,
    empresa_codigo   VARCHAR(30) NOT NULL REFERENCES dbo.dim_empresa(empresa_codigo),
    alumno_id        INT NOT NULL REFERENCES dbo.dim_alumno(alumno_id),
    fact_id_base     INT NOT NULL REFERENCES dbo.fact_matriculas(fact_id),
    horizonte        VARCHAR(30) NOT NULL DEFAULT 'PROXIMO_PERIODO',
    probabilidad     DECIMAL(5,4) NOT NULL,
    umbral_operativo DECIMAL(5,4) NOT NULL,
    riesgo_categoria VARCHAR(10) NOT NULL,
    factor_1         NVARCHAR(200) NULL,
    factor_2         NVARCHAR(200) NULL,
    factor_3         NVARCHAR(200) NULL,
    fecha_calculo    DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    modelo_version   VARCHAR(40) NOT NULL
);
CREATE INDEX IX_prediccion_abandono_empresa ON dbo.fact_prediccion_abandono(empresa_codigo);
GO

-- ── fact_evaluacion_modelo: métricas de validación, consultables ────────
-- La sección 1.2 promete que una autoridad pueda "consultar y confiar" en
-- el modelo: las métricas reales (por esquema de validación) viven en el
-- warehouse, no solo en un JSON del servidor, y se leen por
-- VIS_EVALUACION_MODELO desde el panel y desde el chat.
CREATE TABLE dbo.fact_evaluacion_modelo (
    evaluacion_id       INT IDENTITY(1,1) PRIMARY KEY,
    empresa_codigo      VARCHAR(30) NOT NULL REFERENCES dbo.dim_empresa(empresa_codigo),
    componente          VARCHAR(20) NOT NULL,        -- PREDICCION / CLUSTERING / NL2SQL
    modelo              VARCHAR(60) NOT NULL,        -- ej. RF_CLASS_WEIGHT, KMEANS_K3
    esquema_validacion  VARCHAR(40) NOT NULL,        -- CV_GRUPOS_5, TEMPORAL, PROSPECTIVA, ...
    metrica             VARCHAR(40) NOT NULL,        -- ROC_AUC, PR_AUC, RECALL, SILHOUETTE, ...
    valor               DECIMAL(10,4) NOT NULL,
    desviacion          DECIMAL(10,4) NULL,
    es_modelo_final     BIT NOT NULL DEFAULT 0,
    fecha_calculo       DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    modelo_version      VARCHAR(40) NOT NULL
);
CREATE INDEX IX_evaluacion_modelo_empresa ON dbo.fact_evaluacion_modelo(empresa_codigo);
GO

-- Misma estrategia de aislamiento que VIS_ALUMNO: filtro por SESSION_CONTEXT
-- fijado en la MISMA conexión que ejecuta el SELECT, nunca por un objeto
-- global mutable (ver el comentario de VIS_ALUMNO).
IF OBJECT_ID('dbo.VIS_PREDICCION_ABANDONO', 'V') IS NOT NULL DROP VIEW dbo.VIS_PREDICCION_ABANDONO;
GO
CREATE VIEW dbo.VIS_PREDICCION_ABANDONO AS
SELECT
    da.cedula, da.apellidos, da.nombres,
    df.facultad_codigo, df.facultad_nombre, dc.carrera,
    fm.sede_codigo, fm.canal_codigo, fm.semestre AS periodo_actual,
    fp.horizonte, fp.probabilidad, fp.umbral_operativo, fp.riesgo_categoria,
    fp.factor_1, fp.factor_2, fp.factor_3,
    fp.fecha_calculo, fp.modelo_version
FROM dbo.fact_prediccion_abandono fp
JOIN dbo.dim_alumno da ON da.alumno_id = fp.alumno_id
JOIN dbo.fact_matriculas fm ON fm.fact_id = fp.fact_id_base
JOIN dbo.dim_facultad df ON df.facultad_codigo = fm.facultad_codigo
JOIN dbo.dim_carrera dc ON dc.carrera_id = fm.carrera_id
WHERE fp.empresa_codigo = CAST(SESSION_CONTEXT(N'empresa_activa') AS VARCHAR(30));
GO

IF OBJECT_ID('dbo.VIS_EVALUACION_MODELO', 'V') IS NOT NULL DROP VIEW dbo.VIS_EVALUACION_MODELO;
GO
CREATE VIEW dbo.VIS_EVALUACION_MODELO AS
SELECT componente, modelo, esquema_validacion, metrica, valor, desviacion,
       es_modelo_final, fecha_calculo, modelo_version
FROM dbo.fact_evaluacion_modelo
WHERE empresa_codigo = CAST(SESSION_CONTEXT(N'empresa_activa') AS VARCHAR(30));
GO

-- ── Módulo 2: Benchmarking institucional (ver documentacion/tecnica/BENCHMARKING_INSTITUCIONAL.md) ──
-- Indicadores comparativos de fuentes EXTERNAS (artículos académicos con
-- DOI; el documento enlazado lista cada fuente). Patrón "indicator fact"
-- (EAV acotado): los indicadores externos son heterogéneos, pocos y de
-- fuentes y años distintos, así que no encajan en el modelo dimensional de
-- matrículas, que es para datos operativos propios de una sola institución.
IF OBJECT_ID('dbo.fact_benchmark_externo', 'U') IS NOT NULL DROP TABLE dbo.fact_benchmark_externo;
IF OBJECT_ID('dbo.dim_institucion_externa', 'U') IS NOT NULL DROP TABLE dbo.dim_institucion_externa;
GO
CREATE TABLE dbo.dim_institucion_externa (
    institucion_codigo  VARCHAR(30) PRIMARY KEY,
    nombre               NVARCHAR(200) NOT NULL,
    tipo                 VARCHAR(20) NOT NULL,       -- PUBLICA / PARTICULAR / REFERENCIA
    categoria_caces      VARCHAR(30) NULL,           -- ACREDITADA / NO ACREDITADA / EN PROCESO / NULL (no aplica, ej. UNESCO)
    fecha_evaluacion_caces DATE NULL
);
-- Comparar pares con pares (Lepori y Bornmann, 2026): cada cifra
-- declara QUÉ mide exactamente (definicion_indicador), el contexto que la
-- hace comparable o no (pais, modalidad) y un nivel de comparabilidad
-- explícito frente a la institución propia. Solo se cargan cifras
-- publicadas en fuentes académicas con DOI, verificadas en el texto.
CREATE TABLE dbo.fact_benchmark_externo (
    fact_id               INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo    VARCHAR(30) NOT NULL REFERENCES dbo.dim_institucion_externa(institucion_codigo),
    indicador_codigo      VARCHAR(50) NOT NULL,        -- ej. TASA_ABANDONO
    valor                 DECIMAL(10,4) NOT NULL,
    unidad                VARCHAR(20) NOT NULL,        -- % , PUNTOS, etc.
    anio                  SMALLINT NULL,
    definicion_indicador  NVARCHAR(300) NOT NULL,      -- ej. "retiros / matrículas módulo-presentación"
    pais                  NVARCHAR(60) NOT NULL,
    modalidad             VARCHAR(20) NOT NULL,        -- PRESENCIAL / DISTANCIA / MIXTA / NO_REPORTADA
    nivel_comparabilidad  VARCHAR(10) NOT NULL,        -- ALTA / MEDIA / BAJA
    fuente                NVARCHAR(300) NOT NULL,      -- cita APA corta: "Núñez-Naranjo (2024)"
    doi                   VARCHAR(100) NULL,
    url_fuente            NVARCHAR(400) NULL,
    fecha_carga           DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('dbo.VIS_BENCHMARK_EXTERNO', 'V') IS NOT NULL DROP VIEW dbo.VIS_BENCHMARK_EXTERNO;
GO
-- Sin SESSION_CONTEXT: son datos públicos externos, no propios de ninguna
-- empresa/institución conectada — visibles para cualquier empresa activa.
CREATE VIEW dbo.VIS_BENCHMARK_EXTERNO AS
SELECT
    di.institucion_codigo, di.nombre, di.tipo, di.categoria_caces, di.fecha_evaluacion_caces,
    fb.indicador_codigo, fb.valor, fb.unidad, fb.anio, fb.definicion_indicador,
    fb.pais, fb.modalidad, fb.nivel_comparabilidad, fb.fuente, fb.doi, fb.url_fuente
FROM dbo.fact_benchmark_externo fb
JOIN dbo.dim_institucion_externa di ON di.institucion_codigo = fb.institucion_codigo;
GO

-- ── Clustering institucional (por carrera) — ver backend/ml/clustering_institucional.py ──
-- Segmenta las carreras de la empresa activa por perfil de riesgo (tasa de
-- abandono histórica, rendimiento, riesgo actual del modelo predictivo) vía
-- K-Means. Grano: 1 fila por carrera por empresa.
IF OBJECT_ID('dbo.fact_cluster_carrera', 'U') IS NOT NULL DROP TABLE dbo.fact_cluster_carrera;
GO
CREATE TABLE dbo.fact_cluster_carrera (
    fact_id            INT IDENTITY(1,1) PRIMARY KEY,
    empresa_codigo     VARCHAR(30) NOT NULL REFERENCES dbo.dim_empresa(empresa_codigo),
    carrera_id         INT NOT NULL REFERENCES dbo.dim_carrera(carrera_id),
    cluster_id         TINYINT NOT NULL,
    cluster_label      NVARCHAR(60) NOT NULL,
    matricula_total     INT NOT NULL,
    tasa_abandono_hist DECIMAL(5,4) NOT NULL,
    promedio_hist      DECIMAL(4,2) NOT NULL,
    riesgo_promedio    DECIMAL(5,4) NOT NULL,
    fecha_calculo      DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    modelo_version     VARCHAR(30) NOT NULL
);
CREATE INDEX IX_cluster_carrera_empresa ON dbo.fact_cluster_carrera(empresa_codigo);
GO

IF OBJECT_ID('dbo.VIS_CLUSTER_CARRERA', 'V') IS NOT NULL DROP VIEW dbo.VIS_CLUSTER_CARRERA;
GO
CREATE VIEW dbo.VIS_CLUSTER_CARRERA AS
SELECT
    dc.carrera, df.facultad_nombre,
    fc.cluster_label, fc.matricula_total, fc.tasa_abandono_hist,
    fc.promedio_hist, fc.riesgo_promedio, fc.fecha_calculo
FROM dbo.fact_cluster_carrera fc
JOIN dbo.dim_carrera dc ON dc.carrera_id = fc.carrera_id
JOIN dbo.dim_facultad df ON df.facultad_codigo = dc.facultad_codigo
WHERE fc.empresa_codigo = CAST(SESSION_CONTEXT(N'empresa_activa') AS VARCHAR(30));
GO

-- ── Login de solo lectura, exclusivo de CHAT ────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = 'chat_reader')
BEGIN
    EXEC('CREATE LOGIN chat_reader WITH PASSWORD = ''' + '$(chat_reader_password)' + ''', CHECK_POLICY = OFF');
END
GO

USE CHAT;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'chat_reader')
    CREATE USER chat_reader FOR LOGIN chat_reader;
GO
-- chat_reader NO pertenece a db_datareader: ese rol da SELECT sobre TODO el
-- esquema de CHAT, incluidas las tablas físicas (fact_matriculas, dim_*), y
-- la IA a veces genera SQL contra esas tablas en vez de las vistas, sin el
-- filtro de empresa que solo tienen las vistas. Con una sola empresa
-- cargada no se nota, pero desde la segunda esa ruta se salta por completo
-- el aislamiento de SESSION_CONTEXT. Por eso chat_reader solo puede leer
-- las vistas VIS_*: si la IA consulta una tabla física, la consulta falla
-- con "permission denied" y el pipeline de autocorrección la reintenta, en
-- vez de devolver datos sin filtrar.
IF IS_ROLEMEMBER('db_datareader', 'chat_reader') = 1
    ALTER ROLE db_datareader DROP MEMBER chat_reader;
GRANT SELECT ON dbo.VIS_ALUMNO TO chat_reader;
GRANT SELECT ON dbo.VIS_PREDICCION_ABANDONO TO chat_reader;
GRANT SELECT ON dbo.VIS_BENCHMARK_EXTERNO TO chat_reader;
GRANT SELECT ON dbo.VIS_CLUSTER_CARRERA TO chat_reader;
GRANT SELECT ON dbo.VIS_EVALUACION_MODELO TO chat_reader;
GO

-- No se crea usuario para chat_reader en ALIM ni UNEMI_PRUEBAS: sin un
-- usuario mapeado (y con el usuario 'guest' deshabilitado, valor por defecto
-- de SQL Server), ese login no puede conectarse a esas bases. Se refuerza
-- explícitamente revocando CONNECT a 'guest' por si estuviera habilitado.
-- ALIM es una base operativa opcional: si no existe, el bloque se omite.
IF DB_ID('ALIM') IS NOT NULL
    EXEC('USE ALIM; IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = ''guest'' AND authentication_type_desc <> ''NONE'') REVOKE CONNECT FROM guest;');
GO

USE UNEMI_PRUEBAS;
GO
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'guest' AND authentication_type_desc <> 'NONE')
    REVOKE CONNECT FROM guest;
GO

-- Segunda institución (OULAD_PRUEBAS): misma regla para su base operativa;
-- si la base no existe, el bloque se omite.
IF DB_ID('OULAD_PRUEBAS') IS NOT NULL
    EXEC('USE OULAD_PRUEBAS; IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = ''guest'' AND authentication_type_desc <> ''NONE'') REVOKE CONNECT FROM guest;');
GO

PRINT 'CHAT creada: dimensiones, fact_matriculas, SP_MODIFICA_VISTA_IA y login chat_reader listos.';
