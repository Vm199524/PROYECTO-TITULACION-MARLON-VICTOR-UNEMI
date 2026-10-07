# -*- coding: utf-8 -*-
"""
Panel ejecutivo: indicadores de la institución activa en una sola llamada.

Todas las cifras salen de las vistas gobernadas con la cuenta de solo
lectura, las mismas que usa la consulta conversacional: el panel y el chat
nunca muestran números distintos.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends

from core import db
from core.privacidad import token_estudiante
from core.reportes import lectura
from core.seguridad import Sesion, requiere

router = APIRouter(tags=['Panel'])

CONSULTAS = {
    'institucion': 'SELECT nombre, pais, tipo_datos, unidad_periodo FROM VIS_INSTITUCION',
    'riesgo': "SELECT riesgo_categoria, COUNT(*) AS n, MAX(fecha_calculo) AS fecha, MAX(modelo_version) AS version "
              "FROM VIS_PREDICCION_ABANDONO GROUP BY riesgo_categoria",
    'abandono': "SELECT SUM(CASE WHEN estado_matricula = 'RETIRADO' THEN 1 ELSE 0 END) AS retirados, COUNT(*) AS cerrados "
                "FROM VIS_ALUMNO WHERE es_ultimo_periodo = 1 AND estado_matricula <> 'ACTIVO'",
    'confiabilidad': "SELECT metrica, valor FROM VIS_EVALUACION_MODELO WHERE componente = 'PREDICCION' "
                     "AND esquema_validacion = 'TEMPORAL' AND es_modelo_final = 1",
    'modelo': "SELECT TOP 1 modelo FROM VIS_EVALUACION_MODELO WHERE componente = 'PREDICCION' AND es_modelo_final = 1 "
              "AND esquema_validacion = 'TEMPORAL'",
    'segmentos': 'SELECT segmento, orden_segmento, COUNT(*) AS carreras FROM VIS_SEGMENTO_CARRERA '
                 'GROUP BY segmento, orden_segmento ORDER BY orden_segmento',
    'por_carrera': "SELECT TOP 12 carrera, SUM(CASE WHEN riesgo_categoria = 'ALTO' THEN 1 ELSE 0 END) AS alto, "
                   "SUM(CASE WHEN riesgo_categoria = 'MEDIO' THEN 1 ELSE 0 END) AS medio, COUNT(*) AS activos "
                   "FROM VIS_PREDICCION_ABANDONO GROUP BY carrera "
                   "ORDER BY SUM(CASE WHEN riesgo_categoria IN ('ALTO', 'MEDIO') THEN 1 ELSE 0 END) DESC",
    'tendencia': "SELECT periodo_academico, MIN(inicio_periodo) AS inicio, COUNT(DISTINCT cedula) AS estudiantes, "
                 "COUNT(DISTINCT CASE WHEN es_ultimo_periodo = 1 AND estado_matricula = 'RETIRADO' THEN cedula END) "
                 "AS retirados FROM VIS_ALUMNO GROUP BY periodo_academico ORDER BY MIN(inicio_periodo)",
    'alertas': "SELECT TOP 6 cedula, apellidos, nombres, carrera, probabilidad, percentil_riesgo, factor_1 "
               "FROM VIS_PREDICCION_ABANDONO WHERE riesgo_categoria = 'ALTO' ORDER BY probabilidad DESC, percentil_riesgo DESC",
    # Sin EXISTS dentro de SUM: SQL Server no admite subconsultas en un agregado (error 130).
    'seguimiento': "SELECT COUNT(*) AS en_alto, SUM(CASE WHEN i.cedula IS NOT NULL THEN 1 ELSE 0 END) AS atendidos "
                   "FROM VIS_PREDICCION_ABANDONO p LEFT JOIN (SELECT DISTINCT cedula FROM VIS_INTERVENCION) i "
                   "ON i.cedula = p.cedula WHERE p.riesgo_categoria = 'ALTO'",
    'abiertas': "SELECT COUNT(*) AS abiertas FROM VIS_INTERVENCION WHERE estado = 'ABIERTA'",
}


@router.get('/panel/resumen')
def resumen(sesion: Sesion = Depends(requiere('ver_panel'))) -> dict:
    """Indicadores, distribución del riesgo, carreras, tendencia, alertas y seguimiento."""
    inst = sesion.institucion
    with ThreadPoolExecutor(max_workers=6) as pool:
        futuros = {k: pool.submit(db.leer_dicts, sql, inst) for k, sql in CONSULTAS.items()}
        datos = {k: f.result() for k, f in futuros.items()}

    riesgo = {f['riesgo_categoria']: f['n'] for f in datos['riesgo']}
    evaluados = sum(riesgo.values())
    abandono = datos['abandono'][0] if datos['abandono'] else {'retirados': 0, 'cerrados': 0}
    conf = {f['metrica']: f['valor'] for f in datos['confiabilidad']}
    seg = datos['seguimiento'][0] if datos['seguimiento'] else {'en_alto': 0, 'atendidos': 0}
    tendencia = [{'periodo': t['periodo_academico'], 'estudiantes': t['estudiantes'], 'retirados': t['retirados'],
                  'tasa': round(100 * t['retirados'] / t['estudiantes'], 2) if t['estudiantes'] else 0.0}
                 for t in datos['tendencia']]
    salida = {
        'institucion': datos['institucion'][0] if datos['institucion'] else None,
        'calificacion': {'fecha': max((f['fecha'] for f in datos['riesgo'] if f.get('fecha')), default=None),
                         'version': next((f['version'] for f in datos['riesgo']), None),
                         'modelo': datos['modelo'][0]['modelo'] if datos['modelo'] else None},
        'indicadores': {
            'evaluados': evaluados, 'alto': riesgo.get('ALTO', 0), 'medio': riesgo.get('MEDIO', 0), 'bajo': riesgo.get('BAJO', 0),
            'tasa_abandono_hist': round(100 * (abandono['retirados'] or 0) / abandono['cerrados'], 2) if abandono['cerrados'] else None,
            'carreras_prioritarias': next((s['carreras'] for s in datos['segmentos'] if s['orden_segmento'] == 1), 0),
            'intervenciones_abiertas': datos['abiertas'][0]['abiertas'] if datos['abiertas'] else 0,
            'cobertura_alto': round(100 * (seg['atendidos'] or 0) / seg['en_alto'], 1) if seg['en_alto'] else None,
        },
        'confiabilidad': {k: conf.get(k) for k in ('ROC_AUC', 'PR_AUC', 'RECALL_MEDIO', 'PRECISION_MEDIO',
                                                    'RECALL_ALTO', 'PRECISION_ALTO', 'CAPTURA_TOP_10', 'BRIER', 'PREVALENCIA')},
        'segmentos': datos['segmentos'],
        'riesgo_por_carrera': datos['por_carrera'],
        'tendencia': tendencia,
        'alertas': [{'token': token_estudiante(a['cedula']), 'nombre': f"{a['apellidos']} {a['nombres']}",
                     'carrera': a['carrera'], 'probabilidad': a['probabilidad'], 'percentil': a['percentil_riesgo'],
                     'factor': a['factor_1']} for a in datos['alertas']],
    }
    # Lectura del periodo: las mismas frases por reglas del reporte ejecutivo (sin texto libre de IA).
    salida['lectura'] = lectura(salida)
    return salida
