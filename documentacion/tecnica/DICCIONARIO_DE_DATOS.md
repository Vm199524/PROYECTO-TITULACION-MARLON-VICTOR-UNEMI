# Diccionario de datos del almacén ALMACEN_ACADEMICO

Generado desde el esquema real con `python -m scripts.generar_diccionario` (servidor) o con la opción `--script` (desde `base_de_datos/crear_almacen_academico.sql`). No se edita a mano.

## fact_matriculas

Hecho central. Grano: un estudiante en una carrera, periodo académico y corte.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| matricula_id | INT | no | PK | Identificador sustituto de la fila |
| institucion_codigo | VARCHAR(30) | no | FK → dim_institucion | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| alumno_id | INT | no | FK → dim_alumno | Estudiante (clave sustituta) |
| carrera_id | INT | no | FK → dim_carrera | Carrera o módulo |
| sede_id | INT | no | FK → dim_sede | Sede o campus |
| modalidad_codigo | VARCHAR(20) | no | FK → dim_modalidad | Modalidad (PRESENCIAL, EN LINEA, HIBRIDA) |
| periodo_id | INT | no | FK → dim_periodo_academico | Periodo académico |
| tiempo_id | INT | no | FK → dim_tiempo | Fecha del corte |
| estado_codigo | VARCHAR(20) | no | FK → dim_estado_matricula | Estado al cierre del periodo |
| nivel | TINYINT | no |  | Nivel o semestre cursado |
| corte | TINYINT | no |  | Corte de seguimiento dentro del periodo (1 si no hay cortes) |
| promedio | DECIMAL(4,2) | no |  | Promedio del periodo (0 a 10) |
| asistencia_pct | DECIMAL(5,2) | no |  | Asistencia del periodo (%); en OULAD, días con actividad en el aula virtual |
| monto_matricula | DECIMAL(10,2) | sí |  | Valor de la matrícula (opcional) |
| beca_porcentaje | TINYINT | sí |  | Porcentaje de beca, 0 a 100 (opcional) |
| saldo_pendiente | DECIMAL(10,2) | sí |  | Saldo adeudado al cierre del periodo (opcional) |
| creditos_matriculados | SMALLINT | sí |  | Créditos del periodo (opcional) |
| numero_matricula | TINYINT | sí |  | 1 = primera vez; 2 o más = repetición (opcional) |
| dias_anticipacion_matricula | SMALLINT | sí |  | Días de anticipación de la matrícula respecto al inicio (opcional) |
| actividad_lms | INT | sí |  | Interacciones en el aula virtual durante el corte (opcional) |
| dias_sin_actividad | SMALLINT | sí |  | Días sin actividad en el aula virtual al cierre del corte (opcional) |
| evaluaciones_vencidas | SMALLINT | sí |  | Evaluaciones con plazo vencido al cierre del corte (opcional) |
| evaluaciones_entregadas | SMALLINT | sí |  | Evaluaciones entregadas hasta el cierre del corte (opcional) |
| evaluaciones_tardias | SMALLINT | sí |  | Entregas fuera de plazo (opcional) |
| nota_evaluaciones | DECIMAL(4,2) | sí |  | Nota media de lo entregado, 0 a 10 (opcional) |
| es_ultimo_periodo | BIT | no |  | 1 = periodo vigente o de cierre de la trayectoria |

## dim_alumno

Estudiante, identificado por (institución, cédula).

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| alumno_id | INT | no | PK | Estudiante (clave sustituta) |
| institucion_codigo | VARCHAR(30) | no | FK → dim_institucion | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| cedula | VARCHAR(15) | no |  | Identificador del estudiante (ficticio en los datos de prueba) |
| apellidos | NVARCHAR(100) | no |  | Apellidos (ficticios en los datos de prueba) |
| nombres | NVARCHAR(100) | no |  | Nombres (ficticios en los datos de prueba) |
| genero | CHAR(1) | no |  | Género (M/F) |
| ciudad_residencia | NVARCHAR(50) | no |  | Ciudad o región de residencia |

## dim_institucion

Institución conectada y tipo de sus datos.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| institucion_codigo | VARCHAR(30) | no | PK | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| nombre | NVARCHAR(200) | no |  | Nombre |
| pais | NVARCHAR(60) | no |  | País |
| tipo_datos | VARCHAR(30) | no |  | SINTETICO o REAL_ANONIMIZADO |
| unidad_periodo | NVARCHAR(60) | no |  | Qué es un periodo en la institución |
| fecha_carga | DATETIME2 | no |  | Momento de la carga (UTC) |

## dim_periodo_academico

Periodo académico de cada institución (semestre, presentación del módulo).

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| periodo_id | INT | no | PK | Periodo académico |
| institucion_codigo | VARCHAR(30) | no | FK → dim_institucion | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| periodo_codigo | VARCHAR(20) | no |  | Código del periodo (p. ej., 2024-1 o 2014B) |
| fecha_inicio | DATE | no |  | Fecha de inicio del periodo |

## dim_carrera

Carrera o módulo con su facultad (dimensión desnormalizada).

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| carrera_id | INT | no | PK | Carrera o módulo |
| institucion_codigo | VARCHAR(30) | no | FK → dim_institucion | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| carrera | NVARCHAR(150) | no |  | Carrera o módulo |
| facultad_codigo | VARCHAR(20) | no |  | Código de la facultad |
| facultad_nombre | NVARCHAR(200) | no |  | Nombre de la facultad |

## dim_sede

Sede o campus de cada institución.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| sede_id | INT | no | PK | Sede o campus |
| institucion_codigo | VARCHAR(30) | no | FK → dim_institucion | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| sede_codigo | VARCHAR(20) | no |  | Código de la sede |
| sede_nombre | NVARCHAR(100) | no |  | Nombre de la sede |

## dim_modalidad

Modalidad de estudio.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| modalidad_codigo | VARCHAR(20) | no | PK | Modalidad (PRESENCIAL, EN LINEA, HIBRIDA) |
| descripcion | NVARCHAR(80) | no |  | Descripción |

## dim_estado_matricula

Estado de la matrícula al cierre del periodo.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| estado_codigo | VARCHAR(20) | no | PK | Estado al cierre del periodo |
| descripcion | NVARCHAR(120) | no |  | Descripción |
| es_terminal | BIT | no |  | 1 = el estado cierra la trayectoria |

## dim_tiempo

Calendario de las fechas de corte.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| tiempo_id | INT | no | PK | Fecha del corte |
| fecha | DATE | no |  | Fecha calendario |
| anio | SMALLINT | no |  | Año |
| mes | TINYINT | no |  | Mes |
| trimestre | TINYINT | no |  | Trimestre |

## fact_prediccion_abandono

Resultado del modelo: un estudiante activo con su riesgo para el próximo periodo.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| prediccion_id | INT | no | PK | Identificador de la predicción |
| institucion_codigo | VARCHAR(30) | no | FK → dim_institucion | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| alumno_id | INT | no | FK → dim_alumno | Estudiante (clave sustituta) |
| matricula_id_base | INT | no | FK → fact_matriculas | Fila de la trayectoria con cuyos datos se predijo |
| horizonte | VARCHAR(30) | no |  | Qué se predice: abandono en el PRÓXIMO periodo |
| probabilidad | DECIMAL(6,4) | no |  | Probabilidad calibrada de abandono (0 a 1) |
| riesgo_categoria | VARCHAR(10) | no |  | ALTO, MEDIO o BAJO según los umbrales del entrenamiento |
| umbral_alto | DECIMAL(6,4) | no |  | Umbral de la categoría ALTO (recall objetivo 0,50) |
| umbral_medio | DECIMAL(6,4) | no |  | Umbral de la categoría MEDIO (recall objetivo 0,80) |
| percentil_riesgo | DECIMAL(5,2) | no |  | Posición del estudiante en la institución (0 a 100) |
| factor_1 | NVARCHAR(200) | sí |  | Razón que más eleva el riesgo (SHAP), en lenguaje natural |
| factor_2 | NVARCHAR(200) | sí |  | Segunda razón |
| factor_3 | NVARCHAR(200) | sí |  | Tercera razón |
| explicacion_json | NVARCHAR(MAX) | sí |  | Contribuciones SHAP más relevantes (JSON) |
| caracteristicas_json | NVARCHAR(MAX) | sí |  | Variables usadas y estado para el simulador (JSON) |
| fecha_calculo | DATETIME2 | no |  | Momento del cálculo (UTC) |
| modelo_version | VARCHAR(40) | no |  | Versión del modelo que produjo la fila |

## fact_segmento_carrera

Resultado de la segmentación: una carrera con su segmento de riesgo.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| segmento_id | INT | no | PK | Identificador de la fila |
| institucion_codigo | VARCHAR(30) | no | FK → dim_institucion | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| carrera_id | INT | no | FK → dim_carrera | Carrera o módulo |
| segmento | NVARCHAR(60) | no |  | Atención prioritaria, Estable o Bajo riesgo |
| orden_segmento | TINYINT | no |  | 1 = mayor riesgo |
| estudiantes | INT | no |  | Estudiantes distintos de la carrera |
| tasa_abandono_hist | DECIMAL(6,4) | no |  | Proporción de trayectorias cerradas como RETIRADO |
| promedio_hist | DECIMAL(4,2) | no |  | Promedio histórico |
| asistencia_hist | DECIMAL(5,2) | no |  | Asistencia histórica (%) |
| riesgo_promedio | DECIMAL(6,4) | no |  | Probabilidad media de los activos |
| activos_en_riesgo | INT | no |  | Activos en riesgo ALTO o MEDIO |
| fecha_calculo | DATETIME2 | no |  | Momento del cálculo (UTC) |
| modelo_version | VARCHAR(40) | no |  | Versión del modelo que produjo la fila |

## fact_evaluacion_modelo

Métricas de validación de la predicción, la segmentación y la consulta conversacional.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| evaluacion_id | INT | no | PK | Identificador de la métrica |
| institucion_codigo | VARCHAR(30) | no | FK → dim_institucion | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| componente | VARCHAR(20) | no |  | PREDICCION, SEGMENTACION o CONSULTA |
| modelo | VARCHAR(60) | no |  | Modelo evaluado |
| esquema_validacion | VARCHAR(40) | no |  | Tipo de validación |
| metrica | VARCHAR(60) | no |  | Nombre de la métrica |
| valor | DECIMAL(12,4) | no |  | Valor |
| desviacion | DECIMAL(12,4) | sí |  | Desviación entre pliegues |
| grupo | NVARCHAR(60) | sí |  | Subgrupo o variable |
| es_modelo_final | BIT | no |  | 1 = métrica del modelo en uso |
| fecha_calculo | DATETIME2 | no |  | Momento del cálculo (UTC) |
| modelo_version | VARCHAR(40) | no |  | Versión del modelo que produjo la fila |

## fact_intervencion

Registro de seguimiento de bienestar estudiantil.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| intervencion_id | INT | no | PK | Identificador de la intervención |
| institucion_codigo | VARCHAR(30) | no | FK → dim_institucion | Institución dueña del dato (aislamiento por SESSION_CONTEXT) |
| alumno_id | INT | no | FK → dim_alumno | Estudiante (clave sustituta) |
| tipo | VARCHAR(30) | no |  | Tipo |
| descripcion | NVARCHAR(400) | no |  | Descripción |
| estado | VARCHAR(20) | no |  | ABIERTA o CERRADA |
| resultado | NVARCHAR(200) | sí |  | Resultado al cerrar |
| riesgo_al_registrar | VARCHAR(10) | sí |  | Riesgo del estudiante al registrar |
| registrado_por | NVARCHAR(60) | no |  | Usuario que registró |
| fecha_registro | DATETIME2 | no |  | Fecha de registro (UTC) |
| fecha_cierre | DATETIME2 | sí |  | Fecha de cierre (UTC) |

## dim_referente

Institución de referencia externa.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| referente_codigo | VARCHAR(40) | no | PK | Código del referente |
| nombre | NVARCHAR(200) | no |  | Nombre |
| tipo | VARCHAR(20) | no |  | Tipo |

## fact_referente_externo

Indicador publicado por un referente externo, con su fuente y DOI.

| Columna | Tipo | Nulo | Clave | Descripción |
|---|---|---|---|---|
| referente_id | INT | no | PK | Identificador de la fila |
| referente_codigo | VARCHAR(40) | no | FK → dim_referente | Código del referente |
| indicador_codigo | VARCHAR(50) | no |  | Indicador (TASA_ABANDONO) |
| valor | DECIMAL(10,4) | no |  | Valor |
| unidad | VARCHAR(20) | no |  | Unidad del valor |
| anio | SMALLINT | sí |  | Año |
| definicion_indicador | NVARCHAR(300) | no |  | Qué mide exactamente la cifra y dónde aparece en la fuente |
| pais | NVARCHAR(60) | no |  | País |
| modalidad | VARCHAR(20) | no |  | Modalidad |
| nivel_comparabilidad | VARCHAR(10) | no |  | ALTA, MEDIA o BAJA |
| fuente | NVARCHAR(300) | no |  | Cita APA corta |
| doi | VARCHAR(100) | sí |  | DOI |
| url_fuente | NVARCHAR(400) | sí |  | Enlace |
| fecha_carga | DATETIME2 | no |  | Momento de la carga (UTC) |
