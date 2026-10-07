/*
 * Almacén académico ALMACEN_ACADEMICO (versión 3 del prototipo).
 *
 * Esquema estrella que consolida la trayectoria de los estudiantes de cada
 * institución, los resultados de los procesos por lotes (predicción,
 * segmentación, evaluación) y el registro de seguimiento de bienestar.
 *
 * Tres capas de seguridad viven aquí:
 *   1. Cada vista VIS_* filtra por SESSION_CONTEXT(N'institucion_activa'),
 *      fijado en la MISMA conexión que ejecuta el SELECT. Sin institución en
 *      la sesión, las vistas no devuelven filas (falla cerrada).
 *   2. chat_reader solo puede leer las vistas VIS_*: no ve tablas físicas ni
 *      las bases operativas, y no puede escribir nada.
 *   3. app_seguimiento solo puede ejecutar los dos procedimientos del
 *      registro de seguimiento; no lee ni modifica ninguna otra tabla.
 *
 * Es re-ejecutable: suelta y recrea los objetos. Uso, desde backend:
 *   python -m scripts.ejecutar_sql ../base_de_datos/crear_almacen_academico.sql
 * Las contraseñas de las cuentas se leen de backend/.env (CHAT_READER_PASSWORD
 * y APP_SEGUIMIENTO_PASSWORD) y se sustituyen en $(...) al ejecutar.
 *
 * Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
 * Proyecto de titulación · Universidad Estatal de Milagro · 2026
 */

IF DB_ID('ALMACEN_ACADEMICO') IS NULL
    CREATE DATABASE ALMACEN_ACADEMICO;
GO

USE ALMACEN_ACADEMICO;
GO

-- ── Limpieza en orden inverso a las llaves foráneas ──────────────────────
IF OBJECT_ID('dbo.sp_registrar_intervencion', 'P') IS NOT NULL DROP PROCEDURE dbo.sp_registrar_intervencion;
IF OBJECT_ID('dbo.sp_cerrar_intervencion', 'P') IS NOT NULL DROP PROCEDURE dbo.sp_cerrar_intervencion;
GO
IF OBJECT_ID('dbo.VIS_ALUMNO', 'V') IS NOT NULL DROP VIEW dbo.VIS_ALUMNO;
IF OBJECT_ID('dbo.VIS_PREDICCION_ABANDONO', 'V') IS NOT NULL DROP VIEW dbo.VIS_PREDICCION_ABANDONO;
IF OBJECT_ID('dbo.VIS_SEGMENTO_CARRERA', 'V') IS NOT NULL DROP VIEW dbo.VIS_SEGMENTO_CARRERA;
IF OBJECT_ID('dbo.VIS_EVALUACION_MODELO', 'V') IS NOT NULL DROP VIEW dbo.VIS_EVALUACION_MODELO;
IF OBJECT_ID('dbo.VIS_REFERENTE_EXTERNO', 'V') IS NOT NULL DROP VIEW dbo.VIS_REFERENTE_EXTERNO;
IF OBJECT_ID('dbo.VIS_INTERVENCION', 'V') IS NOT NULL DROP VIEW dbo.VIS_INTERVENCION;
IF OBJECT_ID('dbo.VIS_INSTITUCION', 'V') IS NOT NULL DROP VIEW dbo.VIS_INSTITUCION;
IF OBJECT_ID('dbo.VIS_PREDICCION_DETALLE', 'V') IS NOT NULL DROP VIEW dbo.VIS_PREDICCION_DETALLE;
GO
IF OBJECT_ID('dbo.fact_intervencion', 'U') IS NOT NULL DROP TABLE dbo.fact_intervencion;
IF OBJECT_ID('dbo.fact_prediccion_abandono', 'U') IS NOT NULL DROP TABLE dbo.fact_prediccion_abandono;
IF OBJECT_ID('dbo.fact_segmento_carrera', 'U') IS NOT NULL DROP TABLE dbo.fact_segmento_carrera;
IF OBJECT_ID('dbo.fact_evaluacion_modelo', 'U') IS NOT NULL DROP TABLE dbo.fact_evaluacion_modelo;
IF OBJECT_ID('dbo.fact_matriculas', 'U') IS NOT NULL DROP TABLE dbo.fact_matriculas;
IF OBJECT_ID('dbo.fact_referente_externo', 'U') IS NOT NULL DROP TABLE dbo.fact_referente_externo;
IF OBJECT_ID('dbo.dim_referente', 'U') IS NOT NULL DROP TABLE dbo.dim_referente;
IF OBJECT_ID('dbo.dim_alumno', 'U') IS NOT NULL DROP TABLE dbo.dim_alumno;
IF OBJECT_ID('dbo.dim_carrera', 'U') IS NOT NULL DROP TABLE dbo.dim_carrera;
IF OBJECT_ID('dbo.dim_sede', 'U') IS NOT NULL DROP TABLE dbo.dim_sede;
IF OBJECT_ID('dbo.dim_periodo_academico', 'U') IS NOT NULL DROP TABLE dbo.dim_periodo_academico;
IF OBJECT_ID('dbo.dim_modalidad', 'U') IS NOT NULL DROP TABLE dbo.dim_modalidad;
IF OBJECT_ID('dbo.dim_estado_matricula', 'U') IS NOT NULL DROP TABLE dbo.dim_estado_matricula;
IF OBJECT_ID('dbo.dim_tiempo', 'U') IS NOT NULL DROP TABLE dbo.dim_tiempo;
IF OBJECT_ID('dbo.dim_institucion', 'U') IS NOT NULL DROP TABLE dbo.dim_institucion;
GO

-- ── Dimensiones ─────────────────────────────────────────────────────────
-- Una fila por institución conectada. tipo_datos deja explícito si las
-- cifras son sintéticas (prueba de arquitectura) o reales anonimizadas, y
-- el panel lo muestra junto a cada resultado.
CREATE TABLE dbo.dim_institucion (
    institucion_codigo  VARCHAR(30)    NOT NULL PRIMARY KEY,
    nombre              NVARCHAR(200)  NOT NULL,
    pais                NVARCHAR(60)   NOT NULL,
    tipo_datos          VARCHAR(30)    NOT NULL,   -- SINTETICO / REAL_ANONIMIZADO
    unidad_periodo      NVARCHAR(60)   NOT NULL,   -- semestre, bloque de 28 días, ...
    fecha_carga         DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE dbo.dim_tiempo (
    tiempo_id  INT IDENTITY(1,1) PRIMARY KEY,
    fecha      DATE     NOT NULL UNIQUE,
    anio       SMALLINT NOT NULL,
    mes        TINYINT  NOT NULL,
    trimestre  TINYINT  NOT NULL
);

-- Estados de la matrícula al cierre de cada periodo. es_terminal marca los
-- que cierran una trayectoria (RETIRADO, GRADUADO, EGRESADO, REPROBADO).
CREATE TABLE dbo.dim_estado_matricula (
    estado_codigo  VARCHAR(20)   NOT NULL PRIMARY KEY,
    descripcion    NVARCHAR(120) NOT NULL,
    es_terminal    BIT           NOT NULL
);
INSERT INTO dbo.dim_estado_matricula (estado_codigo, descripcion, es_terminal) VALUES
    ('ACTIVO',    N'Matrícula vigente en el periodo', 0),
    ('RETIRADO',  N'Abandonó o se retiró de la carrera', 1),
    ('GRADUADO',  N'Culminó y aprobó la carrera o el módulo', 1),
    ('EGRESADO',  N'Terminó el plan de estudios sin titularse aún', 1),
    ('REPROBADO', N'Terminó el módulo sin aprobarlo', 1);

CREATE TABLE dbo.dim_modalidad (
    modalidad_codigo  VARCHAR(20)  NOT NULL PRIMARY KEY,
    descripcion       NVARCHAR(80) NOT NULL
);
INSERT INTO dbo.dim_modalidad (modalidad_codigo, descripcion) VALUES
    ('PRESENCIAL', N'Clases en el campus'),
    ('EN LINEA',   N'Clases en el aula virtual'),
    ('HIBRIDA',    N'Combinación de presencial y en línea');

-- Periodo académico de cada institución (semestre en UNEMI, presentación
-- en OULAD). Su orden permite la validación temporal por cohortes.
CREATE TABLE dbo.dim_periodo_academico (
    periodo_id          INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo  VARCHAR(30) NOT NULL REFERENCES dbo.dim_institucion(institucion_codigo),
    periodo_codigo      VARCHAR(20) NOT NULL,
    fecha_inicio        DATE        NOT NULL,
    CONSTRAINT UQ_periodo UNIQUE (institucion_codigo, periodo_codigo)
);

CREATE TABLE dbo.dim_sede (
    sede_id             INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo  VARCHAR(30)   NOT NULL REFERENCES dbo.dim_institucion(institucion_codigo),
    sede_codigo         VARCHAR(20)   NOT NULL,
    sede_nombre         NVARCHAR(100) NOT NULL,
    CONSTRAINT UQ_sede UNIQUE (institucion_codigo, sede_codigo)
);

-- La facultad se guarda dentro de la carrera (dimensión desnormalizada, al
-- estilo de Kimball): evita un copo de nieve y dos instituciones pueden usar
-- el mismo código de facultad sin chocar.
CREATE TABLE dbo.dim_carrera (
    carrera_id          INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo  VARCHAR(30)   NOT NULL REFERENCES dbo.dim_institucion(institucion_codigo),
    carrera             NVARCHAR(150) NOT NULL,
    facultad_codigo     VARCHAR(20)   NOT NULL,
    facultad_nombre     NVARCHAR(200) NOT NULL,
    CONSTRAINT UQ_carrera UNIQUE (institucion_codigo, carrera, facultad_codigo)
);

-- Identidad del estudiante = (institución, identificador). Dos instituciones
-- con el mismo identificador nunca se fusionan en una sola persona.
CREATE TABLE dbo.dim_alumno (
    alumno_id           INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo  VARCHAR(30)   NOT NULL REFERENCES dbo.dim_institucion(institucion_codigo),
    cedula              VARCHAR(15)   NOT NULL,
    apellidos           NVARCHAR(100) NOT NULL,
    nombres             NVARCHAR(100) NOT NULL,
    genero              CHAR(1)       NOT NULL,
    ciudad_residencia   NVARCHAR(50)  NOT NULL,
    CONSTRAINT UQ_alumno UNIQUE (institucion_codigo, cedula)
);
GO

-- ── Hecho central: trayectoria (grano: alumno × carrera × periodo × corte) ──
-- Las variables marcadas como OPCIONAL quedan en NULL cuando la institución
-- no las registra; el modelo usa solo las que cada institución aporta.
CREATE TABLE dbo.fact_matriculas (
    matricula_id                INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo          VARCHAR(30)   NOT NULL REFERENCES dbo.dim_institucion(institucion_codigo),
    alumno_id                   INT           NOT NULL REFERENCES dbo.dim_alumno(alumno_id),
    carrera_id                  INT           NOT NULL REFERENCES dbo.dim_carrera(carrera_id),
    sede_id                     INT           NOT NULL REFERENCES dbo.dim_sede(sede_id),
    modalidad_codigo            VARCHAR(20)   NOT NULL REFERENCES dbo.dim_modalidad(modalidad_codigo),
    periodo_id                  INT           NOT NULL REFERENCES dbo.dim_periodo_academico(periodo_id),
    tiempo_id                   INT           NOT NULL REFERENCES dbo.dim_tiempo(tiempo_id),
    estado_codigo               VARCHAR(20)   NOT NULL REFERENCES dbo.dim_estado_matricula(estado_codigo),
    nivel                       TINYINT       NOT NULL,   -- semestre o ciclo cursado
    corte                       TINYINT       NOT NULL,   -- corte de seguimiento dentro del periodo (1 si no hay)
    promedio                    DECIMAL(4,2)  NOT NULL,   -- 0 a 10
    asistencia_pct              DECIMAL(5,2)  NOT NULL,   -- 0 a 100
    monto_matricula             DECIMAL(10,2) NULL,       -- OPCIONAL
    beca_porcentaje             TINYINT       NULL,       -- OPCIONAL
    saldo_pendiente             DECIMAL(10,2) NULL,       -- OPCIONAL (mora)
    creditos_matriculados       SMALLINT      NULL,       -- OPCIONAL (carga académica)
    numero_matricula            TINYINT       NULL,       -- OPCIONAL (1 = primera vez, 2 = repite...)
    dias_anticipacion_matricula SMALLINT      NULL,       -- OPCIONAL (+ antes del inicio, - después)
    actividad_lms               INT           NULL,       -- OPCIONAL (interacciones en el aula virtual)
    dias_sin_actividad          SMALLINT      NULL,       -- OPCIONAL (al cierre del corte)
    evaluaciones_vencidas       SMALLINT      NULL,       -- OPCIONAL
    evaluaciones_entregadas     SMALLINT      NULL,       -- OPCIONAL
    evaluaciones_tardias        SMALLINT      NULL,       -- OPCIONAL
    nota_evaluaciones           DECIMAL(4,2)  NULL,       -- OPCIONAL (0 a 10, solo entregadas)
    es_ultimo_periodo           BIT           NOT NULL
);
CREATE INDEX IX_matriculas_institucion ON dbo.fact_matriculas(institucion_codigo);
CREATE INDEX IX_matriculas_trayectoria ON dbo.fact_matriculas(institucion_codigo, alumno_id, carrera_id, tiempo_id);
CREATE INDEX IX_matriculas_cohorte ON dbo.fact_matriculas(institucion_codigo, carrera_id, periodo_id, corte);
GO

-- ── Resultados de los procesos por lotes (los escribe el sistema, nunca un usuario) ──
-- Predicción: una fila por estudiante ACTIVO con su riesgo para el próximo
-- periodo. explicacion_json guarda las contribuciones SHAP más relevantes
-- (en ambos sentidos) y caracteristicas_json el vector usado, para que la
-- ficha y el simulador partan exactamente de lo que vio el modelo.
CREATE TABLE dbo.fact_prediccion_abandono (
    prediccion_id         INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo    VARCHAR(30)   NOT NULL REFERENCES dbo.dim_institucion(institucion_codigo),
    alumno_id             INT           NOT NULL REFERENCES dbo.dim_alumno(alumno_id),
    matricula_id_base     INT           NOT NULL REFERENCES dbo.fact_matriculas(matricula_id),
    horizonte             VARCHAR(30)   NOT NULL DEFAULT 'PROXIMO_PERIODO',
    probabilidad          DECIMAL(6,4)  NOT NULL,   -- calibrada (Platt)
    riesgo_categoria      VARCHAR(10)   NOT NULL,   -- ALTO / MEDIO / BAJO
    umbral_alto           DECIMAL(6,4)  NOT NULL,
    umbral_medio          DECIMAL(6,4)  NOT NULL,
    percentil_riesgo      DECIMAL(5,2)  NOT NULL,   -- posición dentro de la institución (0-100)
    factor_1              NVARCHAR(200) NULL,
    factor_2              NVARCHAR(200) NULL,
    factor_3              NVARCHAR(200) NULL,
    explicacion_json      NVARCHAR(MAX) NULL,
    caracteristicas_json  NVARCHAR(MAX) NULL,
    fecha_calculo         DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    modelo_version        VARCHAR(40)   NOT NULL
);
CREATE INDEX IX_prediccion_institucion ON dbo.fact_prediccion_abandono(institucion_codigo, probabilidad DESC);

CREATE TABLE dbo.fact_segmento_carrera (
    segmento_id         INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo  VARCHAR(30)   NOT NULL REFERENCES dbo.dim_institucion(institucion_codigo),
    carrera_id          INT           NOT NULL REFERENCES dbo.dim_carrera(carrera_id),
    segmento            NVARCHAR(60)  NOT NULL,   -- Atención prioritaria / Estable / Bajo riesgo
    orden_segmento      TINYINT       NOT NULL,   -- 1 = mayor riesgo
    estudiantes         INT           NOT NULL,
    tasa_abandono_hist  DECIMAL(6,4)  NOT NULL,
    promedio_hist       DECIMAL(4,2)  NOT NULL,
    asistencia_hist     DECIMAL(5,2)  NOT NULL,
    riesgo_promedio     DECIMAL(6,4)  NOT NULL,
    activos_en_riesgo   INT           NOT NULL,
    fecha_calculo       DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    modelo_version      VARCHAR(40)   NOT NULL
);

-- Métricas de validación consultables por el panel y por el chat.
CREATE TABLE dbo.fact_evaluacion_modelo (
    evaluacion_id       INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo  VARCHAR(30)   NOT NULL REFERENCES dbo.dim_institucion(institucion_codigo),
    componente          VARCHAR(20)   NOT NULL,   -- PREDICCION / SEGMENTACION / CONSULTA
    modelo              VARCHAR(60)   NOT NULL,
    esquema_validacion  VARCHAR(40)   NOT NULL,   -- CV_AGRUPADA_5, TEMPORAL, PROSPECTIVA, EQUIDAD, ...
    metrica             VARCHAR(60)   NOT NULL,
    valor               DECIMAL(12,4) NOT NULL,
    desviacion          DECIMAL(12,4) NULL,
    grupo               NVARCHAR(60)  NULL,       -- subgrupo (equidad) o variable (monitoreo)
    es_modelo_final     BIT           NOT NULL DEFAULT 0,
    fecha_calculo       DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    modelo_version      VARCHAR(40)   NOT NULL
);
CREATE INDEX IX_evaluacion_institucion ON dbo.fact_evaluacion_modelo(institucion_codigo, componente);

-- Referentes externos publicados en fuentes académicas con DOI (no son
-- datos de ninguna institución conectada).
CREATE TABLE dbo.dim_referente (
    referente_codigo  VARCHAR(40)   NOT NULL PRIMARY KEY,
    nombre            NVARCHAR(200) NOT NULL,
    tipo              VARCHAR(20)   NOT NULL
);
CREATE TABLE dbo.fact_referente_externo (
    referente_id          INT IDENTITY(1,1) PRIMARY KEY,
    referente_codigo      VARCHAR(40)   NOT NULL REFERENCES dbo.dim_referente(referente_codigo),
    indicador_codigo      VARCHAR(50)   NOT NULL,
    valor                 DECIMAL(10,4) NOT NULL,
    unidad                VARCHAR(20)   NOT NULL,
    anio                  SMALLINT      NULL,
    definicion_indicador  NVARCHAR(300) NOT NULL,
    pais                  NVARCHAR(60)  NOT NULL,
    modalidad             VARCHAR(20)   NOT NULL,
    nivel_comparabilidad  VARCHAR(10)   NOT NULL,
    fuente                NVARCHAR(300) NOT NULL,
    doi                   VARCHAR(100)  NULL,
    url_fuente            NVARCHAR(400) NULL,
    fecha_carga           DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);

-- Registro de seguimiento: lo que bienestar estudiantil hace con cada alerta.
-- Cierra el ciclo predicción → acción → resultado. La IA nunca escribe aquí.
CREATE TABLE dbo.fact_intervencion (
    intervencion_id     INT IDENTITY(1,1) PRIMARY KEY,
    institucion_codigo  VARCHAR(30)   NOT NULL REFERENCES dbo.dim_institucion(institucion_codigo),
    alumno_id           INT           NOT NULL REFERENCES dbo.dim_alumno(alumno_id),
    tipo                VARCHAR(30)   NOT NULL,   -- TUTORIA / CONSEJERIA / APOYO_ECONOMICO / CONTACTO / DERIVACION
    descripcion         NVARCHAR(400) NOT NULL,
    estado              VARCHAR(20)   NOT NULL DEFAULT 'ABIERTA',   -- ABIERTA / CERRADA
    resultado           NVARCHAR(200) NULL,
    riesgo_al_registrar VARCHAR(10)   NULL,
    registrado_por      NVARCHAR(60)  NOT NULL,
    fecha_registro      DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    fecha_cierre        DATETIME2     NULL
);
CREATE INDEX IX_intervencion_institucion ON dbo.fact_intervencion(institucion_codigo, alumno_id);
GO

-- ── Vistas gobernadas (capa 1): todas filtran por SESSION_CONTEXT ────────
CREATE VIEW dbo.VIS_INSTITUCION AS
SELECT institucion_codigo, nombre, pais, tipo_datos, unidad_periodo
FROM dbo.dim_institucion
WHERE institucion_codigo = CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
GO

-- Trayectoria: una fila por estudiante y periodo (y corte). El estado vigente
-- de cada estudiante es la fila con es_ultimo_periodo = 1.
CREATE VIEW dbo.VIS_ALUMNO AS
SELECT
    da.cedula, da.apellidos, da.nombres, da.genero, da.ciudad_residencia,
    dc.facultad_codigo, dc.facultad_nombre, dc.carrera,
    ds.sede_codigo, ds.sede_nombre, fm.modalidad_codigo AS modalidad,
    dp.periodo_codigo AS periodo_academico, dp.fecha_inicio AS inicio_periodo,
    dt.fecha AS fecha_corte, dt.anio, dt.mes,
    fm.estado_codigo AS estado_matricula, fm.nivel, fm.corte,
    fm.promedio, fm.asistencia_pct, fm.monto_matricula, fm.beca_porcentaje, fm.saldo_pendiente,
    fm.creditos_matriculados, fm.numero_matricula, fm.dias_anticipacion_matricula,
    fm.actividad_lms, fm.dias_sin_actividad,
    fm.evaluaciones_vencidas, fm.evaluaciones_entregadas, fm.evaluaciones_tardias, fm.nota_evaluaciones,
    fm.es_ultimo_periodo
FROM dbo.fact_matriculas fm
JOIN dbo.dim_alumno da            ON da.alumno_id = fm.alumno_id
JOIN dbo.dim_carrera dc           ON dc.carrera_id = fm.carrera_id
JOIN dbo.dim_sede ds              ON ds.sede_id = fm.sede_id
JOIN dbo.dim_periodo_academico dp ON dp.periodo_id = fm.periodo_id
JOIN dbo.dim_tiempo dt            ON dt.tiempo_id = fm.tiempo_id
WHERE fm.institucion_codigo = CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
GO

CREATE VIEW dbo.VIS_PREDICCION_ABANDONO AS
SELECT
    da.cedula, da.apellidos, da.nombres, da.genero,
    dc.facultad_codigo, dc.facultad_nombre, dc.carrera,
    ds.sede_nombre, fm.modalidad_codigo AS modalidad,
    dp.periodo_codigo AS periodo_academico, fm.nivel, fm.corte,
    fm.promedio AS promedio_actual, fm.asistencia_pct AS asistencia_actual, fm.saldo_pendiente AS saldo_actual,
    fp.horizonte, fp.probabilidad, fp.riesgo_categoria, fp.percentil_riesgo,
    fp.umbral_alto, fp.umbral_medio,
    fp.factor_1, fp.factor_2, fp.factor_3,
    fp.fecha_calculo, fp.modelo_version
FROM dbo.fact_prediccion_abandono fp
JOIN dbo.dim_alumno da            ON da.alumno_id = fp.alumno_id
JOIN dbo.fact_matriculas fm       ON fm.matricula_id = fp.matricula_id_base
JOIN dbo.dim_carrera dc           ON dc.carrera_id = fm.carrera_id
JOIN dbo.dim_sede ds              ON ds.sede_id = fm.sede_id
JOIN dbo.dim_periodo_academico dp ON dp.periodo_id = fm.periodo_id
WHERE fp.institucion_codigo = CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
GO

-- Detalle técnico de cada predicción (contribuciones SHAP y variables), para la
-- ficha y el simulador. La consulta conversacional no la conoce.
CREATE VIEW dbo.VIS_PREDICCION_DETALLE AS
SELECT da.cedula, fp.explicacion_json, fp.caracteristicas_json, fp.modelo_version
FROM dbo.fact_prediccion_abandono fp
JOIN dbo.dim_alumno da ON da.alumno_id = fp.alumno_id
WHERE fp.institucion_codigo = CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
GO

CREATE VIEW dbo.VIS_SEGMENTO_CARRERA AS
SELECT
    dc.carrera, dc.facultad_nombre,
    fs.segmento, fs.orden_segmento, fs.estudiantes, fs.tasa_abandono_hist, fs.promedio_hist,
    fs.asistencia_hist, fs.riesgo_promedio, fs.activos_en_riesgo, fs.fecha_calculo, fs.modelo_version
FROM dbo.fact_segmento_carrera fs
JOIN dbo.dim_carrera dc ON dc.carrera_id = fs.carrera_id
WHERE fs.institucion_codigo = CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
GO

CREATE VIEW dbo.VIS_EVALUACION_MODELO AS
SELECT componente, modelo, esquema_validacion, metrica, valor, desviacion, grupo,
       es_modelo_final, fecha_calculo, modelo_version
FROM dbo.fact_evaluacion_modelo
WHERE institucion_codigo = CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
GO

-- Los referentes son públicos y no pertenecen a ninguna institución
-- conectada; aun así la vista exige una sesión con institución activa, para
-- que el chat no pueda leer nada sin contexto.
CREATE VIEW dbo.VIS_REFERENTE_EXTERNO AS
SELECT
    dr.referente_codigo, dr.nombre, dr.tipo,
    fr.indicador_codigo, fr.valor, fr.unidad, fr.anio, fr.definicion_indicador,
    fr.pais, fr.modalidad, fr.nivel_comparabilidad, fr.fuente, fr.doi, fr.url_fuente
FROM dbo.fact_referente_externo fr
JOIN dbo.dim_referente dr ON dr.referente_codigo = fr.referente_codigo
WHERE SESSION_CONTEXT(N'institucion_activa') IS NOT NULL;
GO

CREATE VIEW dbo.VIS_INTERVENCION AS
SELECT
    fi.intervencion_id, da.cedula, da.apellidos, da.nombres, dc_ult.carrera,
    fi.tipo, fi.descripcion, fi.estado, fi.resultado, fi.riesgo_al_registrar,
    fi.registrado_por, fi.fecha_registro, fi.fecha_cierre
FROM dbo.fact_intervencion fi
JOIN dbo.dim_alumno da ON da.alumno_id = fi.alumno_id
OUTER APPLY (
    SELECT TOP 1 dc.carrera
    FROM dbo.fact_matriculas fm JOIN dbo.dim_carrera dc ON dc.carrera_id = fm.carrera_id
    WHERE fm.alumno_id = fi.alumno_id
    ORDER BY fm.es_ultimo_periodo DESC, fm.tiempo_id DESC
) dc_ult
WHERE fi.institucion_codigo = CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
GO

-- ── Procedimientos del registro de seguimiento (capa 3) ─────────────────
-- La aplicación los invoca con app_seguimiento, que no tiene ningún otro
-- permiso. La institución sale de SESSION_CONTEXT, no de un parámetro, para
-- que nadie registre una intervención sobre un estudiante de otra institución.
CREATE PROCEDURE dbo.sp_registrar_intervencion
    @cedula        VARCHAR(15),
    @tipo          VARCHAR(30),
    @descripcion   NVARCHAR(400),
    @registrado_por NVARCHAR(60)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @inst VARCHAR(30) = CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
    IF @inst IS NULL THROW 50001, 'No hay institución activa en la sesión.', 1;
    IF @tipo NOT IN ('TUTORIA', 'CONSEJERIA', 'APOYO_ECONOMICO', 'CONTACTO', 'DERIVACION')
        THROW 50002, 'Tipo de intervención no válido.', 1;
    DECLARE @alumno INT = (SELECT alumno_id FROM dbo.dim_alumno WHERE institucion_codigo = @inst AND cedula = @cedula);
    IF @alumno IS NULL THROW 50003, 'El estudiante no pertenece a la institución activa.', 1;
    DECLARE @riesgo VARCHAR(10) = (SELECT TOP 1 riesgo_categoria FROM dbo.fact_prediccion_abandono
                                   WHERE institucion_codigo = @inst AND alumno_id = @alumno
                                   ORDER BY fecha_calculo DESC);
    INSERT INTO dbo.fact_intervencion (institucion_codigo, alumno_id, tipo, descripcion, riesgo_al_registrar, registrado_por)
    VALUES (@inst, @alumno, @tipo, @descripcion, @riesgo, @registrado_por);
    SELECT CAST(SCOPE_IDENTITY() AS INT) AS intervencion_id;
END
GO

CREATE PROCEDURE dbo.sp_cerrar_intervencion
    @intervencion_id INT,
    @resultado       NVARCHAR(200)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @inst VARCHAR(30) = CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
    IF @inst IS NULL THROW 50001, 'No hay institución activa en la sesión.', 1;
    UPDATE dbo.fact_intervencion
       SET estado = 'CERRADA', resultado = @resultado, fecha_cierre = SYSUTCDATETIME()
     WHERE intervencion_id = @intervencion_id AND institucion_codigo = @inst AND estado = 'ABIERTA';
    IF @@ROWCOUNT = 0 THROW 50004, 'La intervención no existe, ya está cerrada o es de otra institución.', 1;
END
GO

-- ── Cuentas de mínimo privilegio ────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = 'chat_reader')
    EXEC('CREATE LOGIN chat_reader WITH PASSWORD = ''$(chat_reader_password)'', CHECK_POLICY = OFF');
ELSE
    EXEC('ALTER LOGIN chat_reader WITH PASSWORD = ''$(chat_reader_password)''');
GO
IF NOT EXISTS (SELECT 1 FROM sys.sql_logins WHERE name = 'app_seguimiento')
    EXEC('CREATE LOGIN app_seguimiento WITH PASSWORD = ''$(app_seguimiento_password)'', CHECK_POLICY = OFF');
ELSE
    EXEC('ALTER LOGIN app_seguimiento WITH PASSWORD = ''$(app_seguimiento_password)''');
GO

USE ALMACEN_ACADEMICO;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'chat_reader')
    CREATE USER chat_reader FOR LOGIN chat_reader;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'app_seguimiento')
    CREATE USER app_seguimiento FOR LOGIN app_seguimiento;
GO
-- Ninguna de las dos pertenece a db_datareader: ese rol daría lectura sobre
-- las tablas físicas, que no filtran por institución.
IF IS_ROLEMEMBER('db_datareader', 'chat_reader') = 1 ALTER ROLE db_datareader DROP MEMBER chat_reader;
IF IS_ROLEMEMBER('db_datareader', 'app_seguimiento') = 1 ALTER ROLE db_datareader DROP MEMBER app_seguimiento;
GRANT SELECT ON dbo.VIS_INSTITUCION         TO chat_reader;
GRANT SELECT ON dbo.VIS_ALUMNO              TO chat_reader;
GRANT SELECT ON dbo.VIS_PREDICCION_ABANDONO TO chat_reader;
GRANT SELECT ON dbo.VIS_SEGMENTO_CARRERA    TO chat_reader;
GRANT SELECT ON dbo.VIS_EVALUACION_MODELO   TO chat_reader;
GRANT SELECT ON dbo.VIS_REFERENTE_EXTERNO   TO chat_reader;
GRANT SELECT ON dbo.VIS_INTERVENCION        TO chat_reader;
GRANT SELECT ON dbo.VIS_PREDICCION_DETALLE  TO chat_reader;
GRANT EXECUTE ON dbo.sp_registrar_intervencion TO app_seguimiento;
GRANT EXECUTE ON dbo.sp_cerrar_intervencion    TO app_seguimiento;
GO

-- Las bases operativas no tienen usuario para estas cuentas; además se
-- revoca CONNECT a guest por si estuviera habilitado.
IF DB_ID('UNEMI_PRUEBAS') IS NOT NULL
    EXEC('USE UNEMI_PRUEBAS; IF EXISTS (SELECT 1 FROM sys.database_permissions p JOIN sys.database_principals d ON d.principal_id = p.grantee_principal_id WHERE d.name = ''guest'' AND p.permission_name = ''CONNECT'' AND p.state IN (''G'', ''W'')) REVOKE CONNECT FROM guest;');
IF DB_ID('OULAD_PRUEBAS') IS NOT NULL
    EXEC('USE OULAD_PRUEBAS; IF EXISTS (SELECT 1 FROM sys.database_permissions p JOIN sys.database_principals d ON d.principal_id = p.grantee_principal_id WHERE d.name = ''guest'' AND p.permission_name = ''CONNECT'' AND p.state IN (''G'', ''W'')) REVOKE CONNECT FROM guest;');
GO

PRINT 'ALMACEN_ACADEMICO listo: dimensiones, hechos, vistas VIS_*, procedimientos y cuentas de mínimo privilegio.';
