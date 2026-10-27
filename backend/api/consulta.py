# -*- coding: utf-8 -*-
"""
Consulta conversacional: preguntas en español respondidas con datos.

Requerimientos que implementa: RF-10 (consulta en español), RF-14 (exportación
    e informe ejecutivo), RF-18 (aislamiento por institución), RNF-03
    (trazabilidad).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core import auditoria
from core.auditoria import huella
from core.reportes import excel_tabla
from core.seguridad import Sesion, requiere
from nl2sql import motor, redactor

router = APIRouter(tags=['Consulta conversacional'])


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=1, max_length=500)
    historial: list[dict] = Field(default_factory=list, max_length=10)


@router.get('/consulta/sugerencias')
def sugerencias(_: Sesion = Depends(requiere('consultar'))) -> dict:
    """Preguntas de ejemplo agrupadas por tema."""
    return motor.SUGERENCIAS


@router.post('/consulta')
def consultar(datos: Pregunta, sesion: Sesion = Depends(requiere('consultar'))) -> dict:
    """Responde una pregunta sobre la institución activa."""
    r = motor.responder(datos.pregunta, sesion.institucion, list(sesion.instituciones),
                        ver_sql=sesion.puede('ver_sql'), historial=datos.historial)
    auditoria.registrar('CONSULTA', sesion.usuario, sesion.institucion,
                        resultado=r.origen if r.origen not in ('ERROR',) else 'ERROR',
                        detalle={'intencion': r.intencion, 'metrica': r.metrica_id, 'filas': len(r.filas),
                                 'sql_huella': huella(r.sql or ''), 'proveedor': r.proveedor, 'ms': r.tiempo_ms})
    return r.a_dict()


@router.post('/consulta/{id_respuesta}/interpretar')
def interpretar(id_respuesta: str, sesion: Sesion = Depends(requiere('consultar'))) -> dict:
    """Lectura con IA de un resultado reciente, verificada contra sus cifras.

    Cada llamada queda en la bitácora (tipo INTERPRETACION) con el proveedor,
    el número de filas enviadas y la huella del mensaje; nunca los datos.
    """
    from core.config import CONFIG
    if not CONFIG.interpretar_con_ia:
        raise HTTPException(403, 'La interpretación con IA está deshabilitada por la política de datos de la '
                                 'institución (CONSULTA_INTERPRETAR=0).')
    guardado = motor.resultado_guardado(id_respuesta, sesion.institucion)
    if not guardado:
        raise HTTPException(404, 'La respuesta ya no está disponible; vuelva a hacer la pregunta.')
    pregunta, columnas, filas = guardado
    r = redactor.interpretar(pregunta, columnas, filas, nombres=motor.nombres_institucion(sesion.institucion))
    filas_enviadas, huella_mensaje = r.pop('filas_enviadas', 0), r.pop('huella', '')
    if r.get('verificada'):
        resultado = 'OK'
    else:
        resultado = 'DESCARTADA' if r.get('proveedor') else 'SIN_PROVEEDOR'
    auditoria.registrar('INTERPRETACION', sesion.usuario, sesion.institucion, resultado=resultado,
                        detalle={'id_respuesta': id_respuesta, 'proveedor': r.get('proveedor'), 'modelo': r.get('modelo'),
                                 'filas_enviadas': filas_enviadas, 'filas_resultado': len(filas),
                                 'huella': huella_mensaje})
    return r


@router.get('/consulta/{id_respuesta}/excel')
def exportar(id_respuesta: str, sesion: Sesion = Depends(requiere('exportar'))):
    """Descarga el resultado de una respuesta en Excel."""
    guardado = motor.resultado_guardado(id_respuesta, sesion.institucion)
    if not guardado:
        raise HTTPException(404, 'La respuesta ya no está disponible; vuelva a hacer la pregunta.')
    pregunta, columnas, filas = guardado
    contenido = excel_tabla(pregunta, columnas, filas, sesion)
    auditoria.registrar('EXPORTACION', sesion.usuario, sesion.institucion, detalle={'tipo': 'consulta', 'filas': len(filas)})
    return StreamingResponse(iter([contenido]), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                             headers={'Content-Disposition': 'attachment; filename="consulta_vicmar.xlsx"'})
