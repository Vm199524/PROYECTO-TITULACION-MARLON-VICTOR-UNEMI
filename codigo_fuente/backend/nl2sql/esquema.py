# -*- coding: utf-8 -*-
"""
Esquema semántico que conoce la consulta conversacional.

El modelo de lenguaje solo ve estas vistas y estas columnas, con su
significado de negocio; nunca ve las tablas físicas ni filas de datos al
escribir el SQL. El validador usa la misma lista para rechazar cualquier
objeto que no esté aquí. Si una vista cambia en la base, se cambia aquí.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

VISTAS: dict[str, dict] = {
    'VIS_ALUMNO': {
        'descripcion': 'Trayectoria de cada estudiante: UNA FILA POR ESTUDIANTE Y PERIODO (y corte). '
                       'El estado vigente de un estudiante es la fila con es_ultimo_periodo = 1. '
                       'Para contar personas use COUNT(DISTINCT cedula).',
        'columnas': {
            'cedula': 'identificador del estudiante (dato personal)', 'apellidos': 'apellidos (dato personal)',
            'nombres': 'nombres (dato personal)', 'genero': "M o F", 'ciudad_residencia': 'ciudad de residencia',
            'facultad_codigo': 'código de la facultad', 'facultad_nombre': 'nombre de la facultad',
            'carrera': 'carrera o módulo', 'sede_codigo': 'código de la sede', 'sede_nombre': 'sede o campus',
            'modalidad': "PRESENCIAL, EN LINEA o HIBRIDA", 'periodo_academico': "código del periodo, p. ej. '2024-1'",
            'inicio_periodo': 'fecha de inicio del periodo', 'fecha_corte': 'fecha del corte de seguimiento',
            'anio': 'año del corte', 'mes': 'mes del corte',
            'estado_matricula': "ACTIVO, RETIRADO, GRADUADO, EGRESADO o REPROBADO al cierre del periodo",
            'nivel': 'nivel o semestre cursado', 'corte': 'corte dentro del periodo (1 si no hay cortes)',
            'promedio': 'promedio del periodo, de 0 a 10', 'asistencia_pct': 'asistencia del periodo, de 0 a 100',
            'monto_matricula': 'valor de la matrícula (puede ser NULL)', 'beca_porcentaje': 'beca, de 0 a 100',
            'saldo_pendiente': 'saldo adeudado al cierre del periodo (mora); NULL si no se registra',
            'creditos_matriculados': 'créditos del periodo', 'numero_matricula': '1 = primera vez, 2 o más = repite',
            'dias_anticipacion_matricula': 'días de anticipación de la matrícula',
            'actividad_lms': 'interacciones en el aula virtual', 'dias_sin_actividad': 'días sin ingresar al aula virtual',
            'evaluaciones_vencidas': 'evaluaciones con plazo vencido', 'evaluaciones_entregadas': 'evaluaciones entregadas',
            'evaluaciones_tardias': 'entregas fuera de plazo', 'nota_evaluaciones': 'nota media de lo entregado (0-10)',
            'es_ultimo_periodo': '1 = periodo vigente del estudiante',
        },
    },
    'VIS_PREDICCION_ABANDONO': {
        'descripcion': 'Riesgo de abandono de cada estudiante ACTIVO para el próximo periodo (UNA FILA POR ESTUDIANTE). '
                       'riesgo_categoria es ALTO, MEDIO o BAJO; probabilidad va de 0 a 1.',
        'columnas': {
            'cedula': 'identificador (dato personal)', 'apellidos': 'apellidos (dato personal)',
            'nombres': 'nombres (dato personal)', 'genero': 'M o F', 'facultad_codigo': 'código de la facultad',
            'facultad_nombre': 'facultad', 'carrera': 'carrera o módulo', 'sede_nombre': 'sede',
            'modalidad': 'modalidad', 'periodo_academico': 'periodo vigente', 'nivel': 'nivel o semestre',
            'corte': 'corte', 'promedio_actual': 'promedio del periodo vigente',
            'asistencia_actual': 'asistencia del periodo vigente', 'saldo_actual': 'saldo pendiente vigente',
            'horizonte': "siempre 'PROXIMO_PERIODO'", 'probabilidad': 'probabilidad calibrada de abandono (0-1)',
            'riesgo_categoria': 'ALTO, MEDIO o BAJO', 'percentil_riesgo': 'posición en la institución (0-100)',
            'umbral_alto': 'umbral de la categoría ALTO', 'umbral_medio': 'umbral de la categoría MEDIO',
            'factor_1': 'razón principal del riesgo', 'factor_2': 'segunda razón', 'factor_3': 'tercera razón',
            'fecha_calculo': 'fecha de la calificación', 'modelo_version': 'versión del modelo',
        },
    },
    'VIS_SEGMENTO_CARRERA': {
        'descripcion': "Segmento de riesgo de cada carrera (UNA FILA POR CARRERA): 'Atención prioritaria', 'Estable' "
                       "o 'Bajo riesgo'; orden_segmento 1 = mayor riesgo.",
        'columnas': {
            'carrera': 'carrera', 'facultad_nombre': 'facultad', 'segmento': 'segmento de riesgo',
            'orden_segmento': '1 = mayor riesgo', 'estudiantes': 'estudiantes distintos en la historia',
            'tasa_abandono_hist': 'tasa histórica de abandono (0-1)', 'promedio_hist': 'promedio histórico',
            'asistencia_hist': 'asistencia histórica', 'riesgo_promedio': 'probabilidad media de los activos (0-1)',
            'activos_en_riesgo': 'activos en riesgo ALTO o MEDIO', 'fecha_calculo': 'fecha', 'modelo_version': 'versión',
        },
    },
    'VIS_EVALUACION_MODELO': {
        'descripcion': "Métricas de validación. componente: PREDICCION, SEGMENTACION o CONSULTA. esquema_validacion: "
                       "CV_AGRUPADA_5, TEMPORAL, PROSPECTIVA, EQUIDAD, MONITOREO o VALIDACION_INTERNA. metrica: ROC_AUC, "
                       "PR_AUC, BRIER, RECALL_MEDIO, PRECISION_MEDIO, RECALL_ALTO, PRECISION_ALTO, CAPTURA_TOP_10, "
                       "SILHOUETTE, ESTABILIDAD_ARI, KRUSKAL_WALLIS_P, EXACTITUD_EJECUCION, PSI, ...",
        'columnas': {
            'componente': 'PREDICCION, SEGMENTACION o CONSULTA', 'modelo': 'nombre del modelo',
            'esquema_validacion': 'tipo de validación', 'metrica': 'nombre de la métrica', 'valor': 'valor',
            'desviacion': 'desviación entre pliegues', 'grupo': 'subgrupo (equidad) o variable (monitoreo)',
            'es_modelo_final': '1 = modelo en uso', 'fecha_calculo': 'fecha', 'modelo_version': 'versión',
        },
    },
    'VIS_REFERENTE_EXTERNO': {
        'descripcion': 'Tasas de abandono publicadas por otras instituciones en artículos con DOI (no son datos propios).',
        'columnas': {
            'referente_codigo': 'código', 'nombre': 'institución de referencia', 'tipo': 'tipo',
            'indicador_codigo': "siempre 'TASA_ABANDONO'", 'valor': 'valor en porcentaje (0-100)', 'unidad': '%',
            'anio': 'año', 'definicion_indicador': 'qué mide exactamente', 'pais': 'país', 'modalidad': 'modalidad',
            'nivel_comparabilidad': 'ALTA, MEDIA o BAJA', 'fuente': 'cita', 'doi': 'DOI', 'url_fuente': 'enlace',
        },
    },
    'VIS_INTERVENCION': {
        'descripcion': 'Seguimiento registrado por bienestar estudiantil (UNA FILA POR INTERVENCIÓN).',
        'columnas': {
            'intervencion_id': 'número', 'cedula': 'identificador (dato personal)', 'apellidos': 'apellidos',
            'nombres': 'nombres', 'carrera': 'carrera', 'tipo': 'TUTORIA, CONSEJERIA, APOYO_ECONOMICO, CONTACTO o DERIVACION',
            'descripcion': 'descripción', 'estado': 'ABIERTA o CERRADA', 'resultado': 'resultado al cerrar',
            'riesgo_al_registrar': 'riesgo del estudiante al registrar', 'registrado_por': 'usuario',
            'fecha_registro': 'fecha de registro', 'fecha_cierre': 'fecha de cierre',
        },
    },
    'VIS_INSTITUCION': {
        'descripcion': 'Institución activa (una fila).',
        'columnas': {'institucion_codigo': 'código', 'nombre': 'nombre', 'pais': 'país',
                     'tipo_datos': 'SINTETICO o REAL_ANONIMIZADO', 'unidad_periodo': 'qué es un periodo'},
    },
}

GLOSARIO = [
    'Matrícula vigente o estudiante activo: en VIS_ALUMNO, es_ultimo_periodo = 1 AND estado_matricula = \'ACTIVO\'.',
    'Tasa de abandono de la institución: entre las trayectorias cerradas (es_ultimo_periodo = 1 y estado distinto de '
    'ACTIVO), la proporción con estado RETIRADO, en porcentaje.',
    'Estudiantes en riesgo: VIS_PREDICCION_ABANDONO con riesgo_categoria IN (\'ALTO\', \'MEDIO\').',
    'Carreras que requieren atención: VIS_SEGMENTO_CARRERA con segmento = \'Atención prioritaria\'.',
    'Confiabilidad del modelo: VIS_EVALUACION_MODELO con componente = \'PREDICCION\', esquema_validacion = \'TEMPORAL\' '
    'y es_modelo_final = 1 (ROC_AUC, RECALL_MEDIO, PRECISION_MEDIO, CAPTURA_TOP_10).',
    'Los nombres de carreras se escriben sin tildes en los datos de prueba (p. ej., \'Enfermeria\'); use LIKE con '
    'comodines cuando dude de la escritura exacta.',
]


def columnas_permitidas() -> dict[str, set[str]]:
    """Columnas autorizadas por vista, en minúsculas."""
    return {v.upper(): {c.lower() for c in spec['columnas']} for v, spec in VISTAS.items()}


def texto_esquema() -> str:
    """Esquema en texto compacto para el prompt del modelo de lenguaje."""
    partes = []
    for vista, spec in VISTAS.items():
        cols = '; '.join(f'{c} ({d})' for c, d in spec['columnas'].items())
        partes.append(f'- {vista}: {spec["descripcion"]}\n  Columnas: {cols}')
    return '\n'.join(partes)
