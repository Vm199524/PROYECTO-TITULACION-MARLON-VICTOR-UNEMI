# -*- coding: utf-8 -*-
"""
Inicio de sesión, perfil e instituciones del usuario.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import datetime as dt
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core import auditoria, db, usuarios
from core.seguridad import CAPACIDADES_POR_ROL, DESCRIPCION_ROL, Sesion, crear_token, sesion_actual, verificar_clave

router = APIRouter(tags=['Sesión'])

# Freno contra adivinar contraseñas: 5 intentos fallidos por usuario e IP bloquean 5 minutos.
_fallidos: dict[str, list[float]] = {}
_candado = threading.Lock()


class Credenciales(BaseModel):
    usuario: str = Field(min_length=3, max_length=40)
    clave: str = Field(min_length=1, max_length=128)


class CambioClave(BaseModel):
    actual: str
    nueva: str = Field(min_length=8, max_length=128)


def _perfil(cuenta: dict) -> dict:
    return {
        'usuario': cuenta['usuario'], 'nombre': cuenta.get('nombre'), 'correo': cuenta.get('correo'),
        'rol': cuenta['rol'], 'rol_descripcion': DESCRIPCION_ROL.get(cuenta['rol'], cuenta['rol']),
        'capacidades': sorted(CAPACIDADES_POR_ROL.get(cuenta['rol'], set())),
        'instituciones': cuenta.get('instituciones', []), 'ultimo_acceso': cuenta.get('ultimo_acceso'),
    }


@router.post('/auth/ingresar')
def ingresar(datos: Credenciales, request: Request) -> dict:
    """Valida usuario y contraseña y entrega un token de sesión."""
    ip = request.client.host if request.client else '?'
    clave_freno = f'{datos.usuario.lower()}|{ip}'
    ahora = time.time()
    with _candado:
        recientes = [t for t in _fallidos.get(clave_freno, []) if ahora - t < 300]
        _fallidos[clave_freno] = recientes
    if len(recientes) >= 5:
        raise HTTPException(429, 'Demasiados intentos fallidos. Espere cinco minutos e inténtelo otra vez.')
    cuenta = usuarios.buscar(datos.usuario, con_hash=True)
    if not cuenta or not cuenta.get('activo', True) or not verificar_clave(datos.clave, cuenta.get('hash', '')):
        with _candado:
            _fallidos.setdefault(clave_freno, []).append(ahora)
        auditoria.registrar('INGRESO', datos.usuario.lower(), resultado='RECHAZADO', ip=ip)
        raise HTTPException(401, 'Usuario o contraseña incorrectos.')
    with _candado:
        _fallidos.pop(clave_freno, None)
    usuarios.actualizar(cuenta['usuario'], ultimo_acceso=dt.datetime.now().isoformat(timespec='seconds'))
    auditoria.registrar('INGRESO', cuenta['usuario'], ip=ip)
    return {'token': crear_token(cuenta['usuario'], cuenta['rol']), 'usuario': _perfil(cuenta)}


@router.get('/auth/yo')
def yo(sesion: Sesion = Depends(sesion_actual)) -> dict:
    """Perfil del usuario autenticado."""
    return _perfil(usuarios.buscar(sesion.usuario))


@router.put('/auth/clave')
def cambiar_clave(datos: CambioClave, sesion: Sesion = Depends(sesion_actual)) -> dict:
    """Cambia la contraseña propia (exige la actual)."""
    cuenta = usuarios.buscar(sesion.usuario, con_hash=True)
    if not verificar_clave(datos.actual, cuenta.get('hash', '')):
        raise HTTPException(400, 'La contraseña actual no es correcta.')
    usuarios.actualizar(sesion.usuario, clave=datos.nueva)
    auditoria.registrar('CAMBIO_CLAVE', sesion.usuario)
    return {'ok': True}


@router.get('/instituciones')
def instituciones(sesion: Sesion = Depends(sesion_actual)) -> list[dict]:
    """Instituciones asignadas al usuario, con su descripción (si ya están cargadas)."""
    salida = []
    for codigo in sesion.instituciones:
        info = {'codigo': codigo, 'nombre': codigo, 'tipo_datos': None, 'pais': None, 'unidad_periodo': None,
                'disponible': False}
        try:
            filas = db.leer_dicts('SELECT nombre, pais, tipo_datos, unidad_periodo FROM VIS_INSTITUCION', codigo)
            if filas:
                info.update(filas[0], disponible=True)
        except db.ErrorBaseDatos:
            pass
        salida.append(info)
    return salida
