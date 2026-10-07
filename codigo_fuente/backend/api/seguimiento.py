# -*- coding: utf-8 -*-
"""
Registro de seguimiento de bienestar estudiantil (cierra el ciclo alerta → acción).

Las escrituras van por la cuenta app_seguimiento, que solo puede ejecutar los
dos procedimientos del registro; la institución sale de SESSION_CONTEXT.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import auditoria, db
from core.privacidad import cedula_desde_token, enmascarar_cedula, token_estudiante
from core.seguridad import Sesion, requiere

router = APIRouter(tags=['Seguimiento'])
TIPOS = {'TUTORIA': 'Tutoría académica', 'CONSEJERIA': 'Consejería', 'APOYO_ECONOMICO': 'Apoyo económico',
         'CONTACTO': 'Contacto con el estudiante', 'DERIVACION': 'Derivación a otra instancia'}


class NuevaIntervencion(BaseModel):
    token: str
    tipo: str
    descripcion: str = Field(min_length=5, max_length=400)


class Cierre(BaseModel):
    resultado: str = Field(min_length=3, max_length=200)


@router.get('/seguimiento')
def listar(sesion: Sesion = Depends(requiere('ver_seguimiento')), estado: str | None = None) -> dict:
    """Intervenciones registradas en la institución activa."""
    filtro, parametros = '', ()
    if estado in ('ABIERTA', 'CERRADA'):
        filtro, parametros = 'WHERE estado = ?', (estado,)
    filas = db.leer_dicts(
        f'SELECT TOP 300 intervencion_id, cedula, apellidos, nombres, carrera, tipo, descripcion, estado, resultado, '
        f'riesgo_al_registrar, registrado_por, fecha_registro, fecha_cierre FROM VIS_INTERVENCION {filtro} '
        f'ORDER BY fecha_registro DESC', sesion.institucion, parametros)
    for f in filas:
        f['token'] = token_estudiante(f.pop('cedula'))
        f['nombre'] = f"{f.pop('apellidos')} {f.pop('nombres')}"
        f['tipo_descripcion'] = TIPOS.get(f['tipo'], f['tipo'])
    return {'tipos': TIPOS, 'intervenciones': filas}


@router.post('/seguimiento')
def registrar(datos: NuevaIntervencion, sesion: Sesion = Depends(requiere('registrar_seguimiento'))) -> dict:
    """Registra una intervención para un estudiante de la institución activa."""
    cedula = cedula_desde_token(datos.token)
    if not cedula or datos.tipo not in TIPOS:
        raise HTTPException(400, 'Estudiante o tipo de intervención no válidos.')
    filas = db.ejecutar_seguimiento('dbo.sp_registrar_intervencion', sesion.institucion,
                                    (cedula, datos.tipo, datos.descripcion.strip(), sesion.usuario))
    auditoria.registrar('SEGUIMIENTO_ALTA', sesion.usuario, sesion.institucion,
                        detalle={'estudiante': enmascarar_cedula(cedula), 'tipo': datos.tipo})
    return {'ok': True, 'intervencion_id': filas[0]['intervencion_id'] if filas else None}


@router.post('/seguimiento/{intervencion_id}/cerrar')
def cerrar(intervencion_id: int, datos: Cierre, sesion: Sesion = Depends(requiere('registrar_seguimiento'))) -> dict:
    """Cierra una intervención abierta con su resultado."""
    db.ejecutar_seguimiento('dbo.sp_cerrar_intervencion', sesion.institucion, (intervencion_id, datos.resultado.strip()))
    auditoria.registrar('SEGUIMIENTO_CIERRE', sesion.usuario, sesion.institucion, detalle={'id': intervencion_id})
    return {'ok': True}
