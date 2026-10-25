# -*- coding: utf-8 -*-
"""
Segmentación de carreras por perfil de riesgo y su validación.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from core import db
from core.seguridad import Sesion, requiere
from ml import servicio

router = APIRouter(tags=['Carreras'])


@router.get('/carreras/segmentos')
def segmentos(sesion: Sesion = Depends(requiere('ver_carreras'))) -> dict:
    """Carreras con su segmento, indicadores y la validación de la segmentación."""
    carreras = db.leer_dicts(
        'SELECT carrera, facultad_nombre, segmento, orden_segmento, estudiantes, tasa_abandono_hist, promedio_hist, '
        'asistencia_hist, riesgo_promedio, activos_en_riesgo, fecha_calculo FROM VIS_SEGMENTO_CARRERA '
        'ORDER BY orden_segmento, tasa_abandono_hist DESC', sesion.institucion)
    validacion = servicio.reporte(sesion.institucion, 'segmentacion') or {}
    return {'carreras': carreras,
            'validacion': {k: validacion.get(k) for k in ('unidades', 'k', 'silhouette', 'estabilidad', 'kruskal_wallis',
                                                           'barrido_k', 'comparacion_algoritmos', 'ari_sin_riesgo_del_modelo')}}
