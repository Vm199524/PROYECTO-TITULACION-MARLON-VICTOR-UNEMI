# -*- coding: utf-8 -*-
"""
Autenticación, roles y capacidades.

Tres roles, pensados para quienes usan el sistema en una universidad:
  - AUTORIDAD: decanato, dirección de carrera o vicerrectorado. Consulta y
    decide; no registra seguimiento.
  - BIENESTAR: bienestar estudiantil o tutoría. Atiende las alertas, usa el
    simulador y registra el seguimiento.
  - ADMIN_TI: personal de tecnología. Administra cuentas, revisa la
    auditoría y el estado de los procesos; ve el SQL de las consultas.

El frontend oculta lo que un rol no puede usar, pero la autorización real
ocurre aquí, en cada petición (dependencia `requiere`).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import CONFIG
from core import usuarios

CAPACIDADES_POR_ROL: dict[str, set[str]] = {
    'AUTORIDAD': {
        'ver_panel', 'ver_alumnos', 'ver_ficha', 'ver_carreras', 'ver_referentes', 'ver_modelo',
        'consultar', 'exportar', 'ver_seguimiento',
    },
    'BIENESTAR': {
        'ver_panel', 'ver_alumnos', 'ver_ficha', 'simular', 'ver_carreras', 'ver_referentes',
        'consultar', 'exportar', 'ver_seguimiento', 'registrar_seguimiento',
    },
    'ADMIN_TI': {
        'ver_panel', 'ver_alumnos', 'ver_ficha', 'simular', 'ver_carreras', 'ver_referentes', 'ver_modelo',
        'consultar', 'exportar', 'ver_seguimiento', 'registrar_seguimiento',
        'administrar_usuarios', 'ver_auditoria', 'ver_estado', 'ver_sql',
    },
}

DESCRIPCION_ROL = {
    'AUTORIDAD': 'Autoridad académica',
    'BIENESTAR': 'Bienestar estudiantil',
    'ADMIN_TI': 'Administración de TI',
}


def hash_clave(clave: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return bcrypt.hashpw(clave.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_clave(clave: str, hash_guardado: str) -> bool:
    """Compara una contraseña con su hash bcrypt; nunca contra texto plano."""
    if not clave or not hash_guardado or not hash_guardado.startswith(('$2a$', '$2b$', '$2y$')):
        return False
    try:
        return bcrypt.checkpw(clave.encode('utf-8'), hash_guardado.encode('utf-8'))
    except ValueError:
        return False


def crear_token(usuario: str, rol: str) -> str:
    """Emite un JWT firmado con vencimiento."""
    vence = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=CONFIG.jwt_minutos)
    return jwt.encode({'sub': usuario, 'rol': rol, 'exp': vence}, CONFIG.jwt_clave, algorithm=CONFIG.jwt_algoritmo)


@dataclass(frozen=True)
class Sesion:
    """Usuario autenticado y la institución sobre la que trabaja en esta petición."""

    usuario: str
    nombre: str
    rol: str
    instituciones: tuple[str, ...]
    institucion: str | None

    @property
    def capacidades(self) -> set[str]:
        return CAPACIDADES_POR_ROL.get(self.rol, set())

    def puede(self, capacidad: str) -> bool:
        return capacidad in self.capacidades


_bearer = HTTPBearer(auto_error=False)


def sesion_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_institucion: str | None = Header(default=None),
) -> Sesion:
    """Valida el JWT, revalida la cuenta y resuelve la institución activa.

    La cuenta se revalida en cada petición: si se desactiva, el token deja de
    servir de inmediato. La institución pedida (cabecera X-Institucion) debe
    estar entre las asignadas al usuario.
    """
    no_autorizado = HTTPException(status.HTTP_401_UNAUTHORIZED, 'Sesión no válida o vencida.',
                                  headers={'WWW-Authenticate': 'Bearer'})
    if credenciales is None:
        raise no_autorizado
    try:
        datos = jwt.decode(credenciales.credentials, CONFIG.jwt_clave, algorithms=[CONFIG.jwt_algoritmo])
    except JWTError:
        raise no_autorizado
    cuenta = usuarios.buscar(datos.get('sub', ''))
    if not cuenta or not cuenta.get('activo', True):
        raise no_autorizado
    instituciones = tuple(cuenta.get('instituciones', []))
    institucion = None
    if x_institucion:
        pedida = x_institucion.strip().upper()
        if pedida not in instituciones:
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'No tiene acceso a esa institución.')
        institucion = pedida
    elif instituciones:
        institucion = instituciones[0]
    return Sesion(usuario=cuenta['usuario'], nombre=cuenta.get('nombre', cuenta['usuario']),
                  rol=cuenta['rol'], instituciones=instituciones, institucion=institucion)


def requiere(capacidad: str, con_institucion: bool = True):
    """Dependencia de FastAPI que exige una capacidad (y una institución activa)."""

    def _dependencia(sesion: Sesion = Depends(sesion_actual)) -> Sesion:
        if not sesion.puede(capacidad):
            raise HTTPException(status.HTTP_403_FORBIDDEN, 'Su rol no permite esta acción.')
        if con_institucion and not sesion.institucion:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Seleccione una institución.')
        return sesion

    return _dependencia
