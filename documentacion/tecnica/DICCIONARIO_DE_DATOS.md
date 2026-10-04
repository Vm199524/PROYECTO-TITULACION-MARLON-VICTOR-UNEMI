# Diccionario de datos del almacén CHAT

Generado desde el esquema real por `codigo_fuente/backend/scripts/generar_diccionario_datos.py`. No editar a mano.

## fact_matriculas

Hecho central. Grano: una fila por alumno y periodo académico (semestre en UNEMI, bloque de 28 días en OULAD).

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| fact_id | INT | PK | Identificador sustituto de la fila |
| empresa_codigo | VARCHAR(30) | FK → dim_empresa | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| alumno_id | INT | FK → dim_alumno | Alumno (clave sustituta) |
| carrera_id | INT | FK → dim_carrera | Carrera o módulo |
| facultad_codigo | VARCHAR(20) | FK → dim_facultad | Código de la facultad o dominio |
| estado_codigo | VARCHAR(20) | FK → dim_estado_matricula | Estado al cierre del periodo (ACTIVO, RETIRADO, GRADUADO, EGRESADO, REPROBADO) |
| tiempo_id | INT | FK → dim_tiempo | Fecha de matrícula del periodo |
| sede_codigo | VARCHAR(20) | FK → dim_sede | Sede o campus |
| canal_codigo | VARCHAR(20) | FK → dim_canal | Modalidad (PRESENCIAL, EN LINEA) |
| semestre | TINYINT |  | Número de periodo dentro de la trayectoria |
| promedio | DECIMAL(4,2) |  | Promedio de calificaciones del periodo (0-10) |
| asistencia_pct | DECIMAL(5,2) |  | Asistencia del periodo (%); en OULAD, días con actividad en el aula virtual |
| monto_matricula | DECIMAL(10,2) |  | Valor de la matrícula |
| beca_porcentaje | TINYINT |  | Porcentaje de beca (0-100) |
| saldo_pendiente | DECIMAL(10,2) |  | Saldo adeudado al cierre del periodo (mora) |
| monto_neto | DECIMAL(10,2) |  | Matrícula menos beca (calculado en el ETL) |
| es_ultimo_periodo | BIT |  | 1 = periodo más reciente de la trayectoria (estado vigente del alumno) |

## dim_alumno

Alumno, identificado por (institución, cédula).

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| alumno_id | INT | PK | Alumno (clave sustituta) |
| empresa_codigo | VARCHAR(30) | FK → dim_empresa | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| cedula | VARCHAR(15) |  | Identificador del alumno (ficticio en los datos de prueba) |
| apellidos | NVARCHAR(100) |  | Apellidos (ficticios en los datos de prueba) |
| nombres | NVARCHAR(100) |  | Nombres (ficticios en los datos de prueba) |
| genero | CHAR(1) |  | Género (M/F) |
| ciudad_residencia | NVARCHAR(50) |  | Ciudad o región de residencia |

## dim_tiempo

Calendario de las fechas de matrícula.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| tiempo_id | INT | PK | Fecha de matrícula del periodo |
| fecha | DATE |  | Fecha calendario |
| anio | SMALLINT |  | Año |
| mes | TINYINT |  | Mes |
| trimestre | TINYINT |  | Trimestre |

## dim_empresa

Institución (tenant) dueña de los datos.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| empresa_codigo | VARCHAR(30) | PK | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| business_name | NVARCHAR(200) |  | Nombre comercial de la institución |

## dim_facultad

Facultad o dominio académico.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| facultad_codigo | VARCHAR(20) | PK | Código de la facultad o dominio |
| facultad_nombre | NVARCHAR(200) |  | Nombre de la facultad |

## dim_carrera

Carrera o módulo, dentro de una facultad.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| carrera_id | INT | PK | Carrera o módulo |
| carrera | NVARCHAR(150) |  | Nombre de la carrera o módulo |
| facultad_codigo | VARCHAR(20) | FK → dim_facultad | Código de la facultad o dominio |

## dim_estado_matricula

Estado del alumno al cierre del periodo.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| estado_codigo | VARCHAR(20) | PK | Estado al cierre del periodo (ACTIVO, RETIRADO, GRADUADO, EGRESADO, REPROBADO) |

## dim_sede

Sede o campus.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| sede_codigo | VARCHAR(20) | PK | Sede o campus |
| sede_nombre | NVARCHAR(100) |  | Nombre de la sede |

## dim_canal

Modalidad de estudio.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| canal_codigo | VARCHAR(20) | PK | Modalidad (PRESENCIAL, EN LINEA) |

## fact_prediccion_abandono

Resultado del modelo: una fila por alumno activo con su riesgo para el próximo periodo.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| prediccion_id | INT | PK | Identificador de la predicción |
| empresa_codigo | VARCHAR(30) | FK → dim_empresa | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| alumno_id | INT | FK → dim_alumno | Alumno (clave sustituta) |
| fact_id_base | INT | FK → fact_matriculas | Periodo (fila de fact_matriculas) con cuyos datos se calculó la predicción |
| horizonte | VARCHAR(30) |  | Qué se predice: abandono en el PRÓXIMO periodo |
| probabilidad | DECIMAL(5,4) |  | Probabilidad estimada de abandono (0-1) |
| umbral_operativo | DECIMAL(5,4) |  | Umbral elegido para recall ≥ 0,80 en validación |
| riesgo_categoria | VARCHAR(10) |  | ALTO (≥ umbral), MEDIO (≥ umbral/2), BAJO |
| factor_1 | NVARCHAR(200) |  | Variable que más eleva el riesgo de ese alumno (SHAP) |
| factor_2 | NVARCHAR(200) |  | Segunda variable que más eleva el riesgo (SHAP) |
| factor_3 | NVARCHAR(200) |  | Tercera variable que más eleva el riesgo (SHAP) |
| fecha_calculo | DATETIME2 |  | Momento del cálculo (UTC) |
| modelo_version | VARCHAR(40) |  | Versión del modelo que produjo la fila |

## fact_cluster_carrera

Resultado de K-Means: una fila por carrera con su segmento de riesgo.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| fact_id | INT | PK | Identificador sustituto de la fila |
| empresa_codigo | VARCHAR(30) | FK → dim_empresa | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| carrera_id | INT | FK → dim_carrera | Carrera o módulo |
| cluster_id | TINYINT |  | Número de clúster devuelto por K-Means |
| cluster_label | NVARCHAR(60) |  | Segmento: Atención prioritaria / Estable / Bajo riesgo |
| matricula_total | INT |  | Alumnos distintos de la carrera |
| tasa_abandono_hist | DECIMAL(5,4) |  | Proporción histórica de trayectorias cerradas como RETIRADO |
| promedio_hist | DECIMAL(4,2) |  | Promedio histórico de la carrera |
| riesgo_promedio | DECIMAL(5,4) |  | Probabilidad media de abandono de los activos de la carrera |
| fecha_calculo | DATETIME2 |  | Momento del cálculo (UTC) |
| modelo_version | VARCHAR(30) |  | Versión del modelo que produjo la fila |

## fact_evaluacion_modelo

Métricas de validación de los modelos (predicción, clustering, NL2SQL).

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| evaluacion_id | INT | PK | Identificador de la métrica |
| empresa_codigo | VARCHAR(30) | FK → dim_empresa | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| componente | VARCHAR(20) |  | PREDICCION, CLUSTERING o NL2SQL |
| modelo | VARCHAR(60) |  | Modelo evaluado (ej. RF_SMOTE, KMEANS_K3) |
| esquema_validacion | VARCHAR(40) |  | CV_GRUPOS_5, TEMPORAL, PROSPECTIVA, VALIDACION_INTERNA, CONJUNTO_DORADO |
| metrica | VARCHAR(40) |  | Nombre de la métrica (ROC_AUC, RECALL, SILHOUETTE, ...) |
| valor | DECIMAL(10,4) |  | Valor de la métrica o del indicador |
| desviacion | DECIMAL(10,4) |  | Desviación estándar entre pliegues, si aplica |
| es_modelo_final | BIT |  | 1 = métrica del modelo elegido |
| fecha_calculo | DATETIME2 |  | Momento del cálculo (UTC) |
| modelo_version | VARCHAR(40) |  | Versión del modelo que produjo la fila |

## dim_institucion_externa

Referente externo de benchmarking.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| institucion_codigo | VARCHAR(30) | PK | Código del referente externo |
| nombre | NVARCHAR(200) |  | Nombre del referente |
| tipo | VARCHAR(20) |  | PUBLICA, PARTICULAR o REFERENCIA |
| categoria_caces | VARCHAR(30) |  | Categoría de acreditación (si aplica) |
| fecha_evaluacion_caces | DATE |  | Fecha de evaluación CACES (si aplica) |

## fact_benchmark_externo

Indicador publicado de un referente externo, con su fuente.

| Columna | Tipo | Clave | Descripción |
|---|---|---|---|
| fact_id | INT | PK | Identificador sustituto de la fila |
| institucion_codigo | VARCHAR(30) | FK → dim_institucion_externa | Código del referente externo |
| indicador_codigo | VARCHAR(50) |  | Indicador (TASA_ABANDONO) |
| valor | DECIMAL(10,4) |  | Valor de la métrica o del indicador |
| unidad | VARCHAR(20) |  | Unidad del valor |
| anio | SMALLINT |  | Año |
| definicion_indicador | NVARCHAR(300) |  | Qué mide exactamente la cifra y dónde aparece en la fuente |
| pais | NVARCHAR(60) |  | País del referente |
| modalidad | VARCHAR(20) |  | PRESENCIAL, DISTANCIA, MIXTA o NO_REPORTADA |
| nivel_comparabilidad | VARCHAR(10) |  | ALTA, MEDIA o BAJA frente a la institución propia |
| fuente | NVARCHAR(300) |  | Cita APA corta |
| doi | VARCHAR(100) |  | DOI de la fuente |
| url_fuente | NVARCHAR(400) |  | Enlace a la fuente |
| fecha_carga | DATETIME2 |  | Momento de la carga (UTC) |

## Vistas de presentación (lo único que ve chat_reader)

- `VIS_ALUMNO`
- `VIS_BENCHMARK_EXTERNO`
- `VIS_CLUSTER_CARRERA`
- `VIS_EVALUACION_MODELO`
- `VIS_PREDICCION_ABANDONO`
