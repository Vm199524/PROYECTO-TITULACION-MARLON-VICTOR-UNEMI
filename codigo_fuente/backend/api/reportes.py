# -*- coding: utf-8 -*-
"""
Reportes ejecutivos descargables (Excel y PDF) de la institución activa.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from api.panel import resumen as resumen_panel
from core import auditoria, db
from core.privacidad import enmascarar_cedula
from core.reportes import excel_ejecutivo, pdf_ejecutivo
from core.seguridad import Sesion, requiere

router = APIRouter(tags=['Reportes'])


def _datos(sesion: Sesion) -> tuple[dict, list[dict], list[dict]]:
    resumen = resumen_panel(sesion)
    alertas = db.leer_dicts(
        "SELECT TOP 300 cedula, apellidos, nombres, carrera, probabilidad, riesgo_categoria, factor_1, factor_2 "
        "FROM VIS_PREDICCION_ABANDONO WHERE riesgo_categoria IN ('ALTO', 'MEDIO') ORDER BY probabilidad DESC",
        sesion.institucion)
    alertas = [{'nombre': f"{a['apellidos']} {a['nombres']}", 'cedula': enmascarar_cedula(a['cedula']),
                'carrera': a['carrera'], 'probabilidad': a['probabilidad'], 'riesgo': a['riesgo_categoria'],
                'factor_1': a['factor_1'], 'factor_2': a['factor_2']} for a in alertas]
    carreras = db.leer_dicts('SELECT carrera, facultad_nombre, segmento, estudiantes, tasa_abandono_hist, promedio_hist, '
                             'asistencia_hist, riesgo_promedio, activos_en_riesgo FROM VIS_SEGMENTO_CARRERA '
                             'ORDER BY orden_segmento, tasa_abandono_hist DESC', sesion.institucion)
    return resumen, alertas, carreras


def _nombre(sesion: Sesion, extension: str) -> str:
    return f"alerta_temprana_{sesion.institucion.lower()}_{dt.date.today().isoformat()}.{extension}"


@router.get('/reportes/ejecutivo.xlsx')
def reporte_excel(sesion: Sesion = Depends(requiere('exportar'))):
    contenido = excel_ejecutivo(*_datos(sesion), sesion)
    auditoria.registrar('EXPORTACION', sesion.usuario, sesion.institucion, detalle={'tipo': 'ejecutivo_excel'})
    return Response(contenido, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{_nombre(sesion, "xlsx")}"'})


@router.get('/reportes/ejecutivo.pdf')
def reporte_pdf(sesion: Sesion = Depends(requiere('exportar'))):
    contenido = pdf_ejecutivo(*_datos(sesion), sesion)
    auditoria.registrar('EXPORTACION', sesion.usuario, sesion.institucion, detalle={'tipo': 'ejecutivo_pdf'})
    return Response(contenido, media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{_nombre(sesion, "pdf")}"'})
