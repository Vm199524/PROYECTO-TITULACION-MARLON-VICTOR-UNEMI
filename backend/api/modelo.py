# -*- coding: utf-8 -*-
"""
Calidad y transparencia del modelo: lo que una autoridad necesita para decidir
cuánto confiar en las alertas (validación cruzada, prueba temporal, prueba
prospectiva, calibración, equidad, importancia de variables, deriva y
exactitud de la consulta conversacional).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends

from core.seguridad import Sesion, requiere
from ml import servicio
from ml.caracteristicas import describir

router = APIRouter(tags=['Modelo'])
RAIZ_EVAL = Path(__file__).resolve().parent.parent / 'eval' / 'resultados'


def _evaluacion_consulta(institucion: str) -> dict | None:
    """Última evaluación del motor conversacional de la institución (si existe)."""
    if not RAIZ_EVAL.exists():
        return None
    archivos = sorted(RAIZ_EVAL.glob(f'consulta_{institucion}_*.json'))
    if not archivos:
        return None
    datos = json.loads(archivos[-1].read_text(encoding='utf-8'))
    return {k: datos.get(k) for k in ('fecha', 'resumen', 'por_categoria', 'por_origen', 'adversariales')}


@router.get('/modelo/calidad')
def calidad(sesion: Sesion = Depends(requiere('ver_modelo'))) -> dict:
    """Métricas y gráficos de validación del modelo de la institución activa."""
    inst = sesion.institucion
    m = servicio.reporte(inst, 'metricas')
    if not m:
        return {'disponible': False}
    importancia = [{**i, 'descripcion': describir(i['variable'])} for i in m.get('importancia_permutacion', [])[:15]]
    return {
        'disponible': True, 'version': m.get('version'), 'fecha': m.get('fecha'), 'horizonte': m.get('horizonte'),
        'modelo_final': m.get('modelo_final'), 'panel': m.get('panel'), 'grupos_de_variables': m.get('grupos_de_variables'),
        'comparacion_cv': m.get('comparacion_cv'), 'umbrales': m.get('umbrales'), 'calibracion': m.get('calibracion'),
        'temporal': m.get('validacion_temporal'), 'equidad': m.get('equidad'), 'importancia': importancia,
        'prospectiva': servicio.reporte(inst, 'prospectiva'), 'monitoreo': servicio.reporte(inst, 'monitoreo'),
        'consulta': _evaluacion_consulta(inst),
        'ficha': {
            'proposito': 'Priorizar el acompañamiento de bienestar estudiantil: estima la probabilidad de que un '
                         'estudiante activo abandone en el próximo periodo.',
            'usos_no_previstos': 'No debe usarse para sancionar, negar matrícula, becas ni ningún beneficio, ni como '
                                 'única base de una decisión sobre un estudiante.',
            'datos': 'Trayectoria académica de la institución activa (rendimiento, asistencia y, si existen, '
                     'variables financieras, de aula virtual, de evaluaciones y de matrícula).',
            'limitaciones': 'Predice, no explica causas. Quien abandona en su primer periodo no tiene historia que '
                            'analizar. Con datos sintéticos el desempeño es mayor que el esperable con datos reales.',
            'supervision': 'Cada alerta la revisa una persona de bienestar estudiantil antes de cualquier contacto.',
        },
    }
