/*
 * crear_chat_academico.sql — Capa 1 de la arquitectura de seguridad BI.
 *
 * Reconstruye lo que la practica preprofesional dejo solo en su propio
 * servidor (base CHAT + SP_MODIFICA_VISTA_IA), esta vez como codigo
 * versionado, con dos cambios de fondo:
 *
 *   1. ETL FISICO: fact_matriculas/dim_* son tablas reales, pobladas por
 *      scripts/etl_academico.py — no vistas que leen en vivo de la base
 *      operativa.
 *   2. Login de solo lectura (chat_reader) exclusivo de CHAT: el motor de
 *      IA nunca ejecuta su SELECT final con la cuenta admin (sa) que uso el
 *      usuario para conectarse. Sin usuario mapeado en ALIM/UNEMI_PRUEBAS,
 *      chat_reader no puede ver la base operativa aunque quisiera.
 *
 * SP_MODIFICA_VISTA_IA se mantiene con la MISMA firma que ya espera
 * backend/main.py (`_activate_chat_views`): exec CHAT.dbo.SP_MODIFICA_VISTA_IA
 * '<empresa>'. Antes reapuntaba vistas a tablas de OTRA base; ahora filtra
 * las tablas fisicas de CHAT por empresa_codigo — mismo contrato, origen de
 * datos distinto.
 *
 * Uso: sqlcmd -S <host> -U sa -P <password> -C -i crear_chat_academico.sql
 */

IF DB_ID('CHAT') IS NULL
    CREATE DATABASE CHAT;
GO

USE CHAT;
GO

-- El hecho se borra ANTES que cualquier dimension: tiene FK a las 6, asi
-- que si este script se re-ejecuta (idempotente, ver encabezado) y se
-- intenta soltar una dimension primero, SQL Server lo rechaza con
-- "referenced by a FOREIGN KEY constraint". Nunca cambiar este orden.
IF OBJECT_ID('dbo.fact_prediccion_abandono', 'U') IS NOT NULL DROP TABLE dbo.fact_prediccion_abandono;
IF OBJECT_ID('dbo.fact_cluster_carrera', 'U') IS NOT NULL DROP TABLE dbo.fact_cluster_carrera;
IF OBJECT_ID('dbo.fact_matriculas', 'U') IS NOT NULL DROP TABLE dbo.fact_matriculas;
IF OBJECT_ID('dbo.fact_evaluacion_modelo', 'U') IS NOT NULL DROP TABLE dbo.fact_evaluacion_modelo;
IF OBJECT_ID('dbo.dim_carrera', 'U') IS NOT NULL DROP TABLE dbo.dim_carrera;
-- dim_alumno referencia a dim_empresa desde el Avance 2: se suelta antes.
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
-- canal" (ver documentacion/tecnica/PREDICCION_ABANDONO.md #8): sede = campus/extensión
-- física (ej. Cuenca/Quito/Guayaquil en una IES multi-sede), canal = vía de
-- ingreso/modalidad (PRESENCIAL/DISTANCIA/EN LINEA). Instituciones de un
-- solo campus/modalidad simplemente cargan un único valor fijo aquí (ver
-- backend/etl/perfiles.py, valores_fijos) — el modelo no se rompe por tener
-- una sola sede, pero la columna existe desde ya para no requerir otra
-- migración de esquema cuando se conecte una IES multi-sede real.
IF OBJECT_ID('dbo.dim_sede', 'U') IS NOT NULL DROP TABLE dbo.dim_sede;
CREATE TABLE dbo.dim_sede (
    sede_codigo  VARCHAR(20) PRIMARY KEY,
    sede_nombre  NVARCHAR(100) NOT NULL
);

IF OBJECT_ID('dbo.dim_canal', 'U') IS NOT NULL DROP TABLE dbo.dim_canal;
CREATE TABLE dbo.dim_canal (
    canal_codigo  VARCHAR(20) PRIMARY KEY
);

-- Avance 2 (multi-institución real): la identidad de un alumno es
-- (institución, identificador). Antes `cedula` era UNIQUE global: dos
-- instituciones con un identificador coincidente se habrían fusionado en
-- una sola persona. dim_alumno se referencia desde fact_matriculas y
-- fact_prediccion_abandono, que ya se soltaron arriba (junto con dim_alumno).
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

-- ── Hechos (grano: una fila por registro de matricula) ─────────────────
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
-- Auditoría 09/09/2026 (auditoría interna del 09/09/2026, hallazgo #2): la
-- version anterior de esta vista se recreaba con ALTER VIEW cada vez que
-- una empresa se activaba — un namespace COMPARTIDO y mutable, exactamente
-- el patron que ya causo una fuga de datos real documentada en
-- incidente de fuga de datos entre empresas del 27/07/2026 (27/07/2026). Con SESSION_CONTEXT() el
-- filtro de empresa vive aislado POR CONEXION fisica, no en un objeto
-- global: dos usuarios en empresas distintas ya no pueden pisarse, sin
-- importar que corran al mismo tiempo. El backend fija ese contexto y
-- ejecuta el SELECT en la MISMA conexion (ver
-- db_connector.py::execute_query_with_context) — nunca en pasos separados.
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
-- backend/main.py::_activate_chat_views sigue invocando este SP con la
-- misma firma de siempre (exec CHAT.dbo.SP_MODIFICA_VISTA_IA '<empresa>').
-- Ya NO hace ningun ALTER VIEW ni cambia estado global: el aislamiento real
-- ahora lo pone SESSION_CONTEXT en la conexion que ejecuta el SELECT (ver
-- arriba). Aqui solo queda para no tener que tocar esa parte de main.py, y
-- de paso valida que la empresa exista.
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
-- Grano: 1 fila por alumno ACTIVO con su probabilidad de abandono mas
-- reciente. La puebla backend/ml/predecir_abandono.py (recarga completa por
-- empresa, mismo patron TRUNCATE+INSERT que fact_matriculas). Vive en CHAT
-- (no en UNEMI_PRUEBAS) porque es un resultado derivado, no dato operativo.
IF OBJECT_ID('dbo.fact_prediccion_abandono', 'U') IS NOT NULL DROP TABLE dbo.fact_prediccion_abandono;
GO
-- Avance 2 (panel alumno-periodo): la predicción es "probabilidad de que
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
-- fijado en la MISMA conexion que ejecuta el SELECT, nunca por un objeto
-- global mutable (ver comentario extenso arriba, hallazgo #2 de la auditoria).
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
-- Indicadores comparativos de fuentes EXTERNAS reales (CACES, SENESCYT,
-- prensa especializada citando SENESCYT/UNESCO/Banco Mundial — ver el doc
-- para las URLs exactas). Patrón "indicator fact" (EAV acotado): los
-- indicadores externos son heterogéneos, pocos, y de fuentes/años distintos
-- — no encajan en el modelo dimensional de matrículas de arriba, que es
-- para datos operativos propios de una sola institución.
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
-- Avance 2 (Lepori & Bornmann, 2026: comparar pares con pares): cada cifra
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
    modalidad             VARCHAR(20) NOT NULL,        -- PRESENCIAL / DISTANCIA / MIXTA
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
-- OJO (auditoría 09/09/2026, hallazgo detectado en pruebas): db_datareader
-- le daba a chat_reader SELECT sobre TODO el esquema de CHAT, incluidas las
-- tablas físicas (fact_matriculas, dim_*) — y la IA a veces genera SQL
-- contra esas tablas en vez de VIS_ALUMNO, sin el filtro de empresa que
-- solo tiene la vista. Con una sola empresa cargada no se nota, pero en
-- cuanto exista una segunda, esa ruta se salta por completo el aislamiento
-- de SESSION_CONTEXT. chat_reader ahora solo puede leer VIS_ALUMNO — si la
-- IA insiste en consultar las tablas físicas, la consulta falla con
-- "permission denied" y el pipeline de autocorrección ya existente la
-- reintenta, en vez de dejarla pasar sin filtrar.
IF IS_ROLEMEMBER('db_datareader', 'chat_reader') = 1
    ALTER ROLE db_datareader DROP MEMBER chat_reader;
GRANT SELECT ON dbo.VIS_ALUMNO TO chat_reader;
GRANT SELECT ON dbo.VIS_PREDICCION_ABANDONO TO chat_reader;
GRANT SELECT ON dbo.VIS_BENCHMARK_EXTERNO TO chat_reader;
GRANT SELECT ON dbo.VIS_CLUSTER_CARRERA TO chat_reader;
GRANT SELECT ON dbo.VIS_EVALUACION_MODELO TO chat_reader;
GO

-- No se crea usuario para chat_reader en ALIM ni UNEMI_PRUEBAS: sin un
-- usuario mapeado (y con el usuario 'guest' deshabilitado, el default de
-- SQL Server), ese login sencillamente no puede conectarse a esas bases.
-- Se refuerza explicitamente por si 'guest' estuviera habilitado.
USE ALIM;
GO
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'guest' AND authentication_type_desc <> 'NONE')
    REVOKE CONNECT FROM guest;
GO

USE UNEMI_PRUEBAS;
GO
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'guest' AND authentication_type_desc <> 'NONE')
    REVOKE CONNECT FROM guest;
GO

-- Segunda institución (Avance 2): misma regla para su base operativa.
IF DB_ID('OULAD_PRUEBAS') IS NOT NULL
    EXEC('USE OULAD_PRUEBAS; IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = ''guest'' AND authentication_type_desc <> ''NONE'') REVOKE CONNECT FROM guest;');
GO

PRINT 'CHAT creada: dimensiones, fact_matriculas, SP_MODIFICA_VISTA_IA y login chat_reader listos.';
