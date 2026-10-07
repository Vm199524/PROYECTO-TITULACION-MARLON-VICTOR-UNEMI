# -*- coding: utf-8 -*-
"""
Referentes externos de abandono con su fuente y nivel de comparabilidad.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from core import db
from core.seguridad import Sesion, requiere

router = APIRouter(tags=['Referentes'])


@router.get('/referentes')
def referentes(sesion: Sesion = Depends(requiere('ver_referentes'))) -> dict:
    """Tasa propia frente a las publicadas por otras instituciones (comparar pares con pares)."""
    externos = db.leer_dicts(
        "SELECT referente_codigo, nombre, valor, unidad, anio, definicion_indicador, pais, modalidad, "
        "nivel_comparabilidad, fuente, doi, url_fuente FROM VIS_REFERENTE_EXTERNO WHERE indicador_codigo = 'TASA_ABANDONO' "
        "ORDER BY CASE nivel_comparabilidad WHEN 'ALTA' THEN 1 WHEN 'MEDIA' THEN 2 ELSE 3 END, valor DESC",
        sesion.institucion)
    propia = db.leer_dicts(
        "SELECT SUM(CASE WHEN estado_matricula = 'RETIRADO' THEN 1 ELSE 0 END) AS retirados, COUNT(*) AS cerrados "
        "FROM VIS_ALUMNO WHERE es_ultimo_periodo = 1 AND estado_matricula <> 'ACTIVO'", sesion.institucion)[0]
    inst = db.leer_dicts('SELECT nombre, pais, tipo_datos FROM VIS_INSTITUCION', sesion.institucion)
    return {
        'propia': {'institucion': inst[0] if inst else None, 'retirados': propia['retirados'], 'cerrados': propia['cerrados'],
                   'tasa': round(100 * (propia['retirados'] or 0) / propia['cerrados'], 2) if propia['cerrados'] else None,
                   'definicion': 'Trayectorias cerradas como RETIRADO sobre el total de trayectorias cerradas '
                                 '(retiradas, graduadas, egresadas o reprobadas).'},
        'referentes': externos,
    }
