# -*- coding: utf-8 -*-
"""
Almacén de cuentas de usuario (archivo JSON local, fuera del repositorio).

Cada cuenta guarda: usuario, nombre, correo, rol, instituciones asignadas,
hash bcrypt de la contraseña, si está activa y la fecha de su último acceso.
El archivo se escribe de forma atómica (archivo temporal + reemplazo) y con
un candado, para que dos peticiones simultáneas no lo corrompan.

Si el almacén está vacío y existen ADMIN_INICIAL_USUARIO y
ADMIN_INICIAL_CLAVE en backend/.env, se crea esa primera cuenta de
administración; nunca hay credenciales escritas en el código.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
from pathlib import Path
from typing import Any

from core.config import CONFIG

ROLES_VALIDOS = ('AUTORIDAD', 'BIENESTAR', 'ADMIN_TI')
_PATRON_USUARIO = re.compile(r'^[a-z0-9._-]{3,40}$')
_candado = threading.Lock()


def _ruta() -> Path:
    return CONFIG.ruta_usuarios


def _leer() -> dict[str, Any]:
    ruta = _ruta()
    if not ruta.exists():
        return {'usuarios': []}
    try:
        return json.loads(ruta.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {'usuarios': []}


def _escribir(datos: dict[str, Any]) -> None:
    ruta = _ruta()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix('.tmp')
    temporal.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporal, ruta)


def _sin_hash(cuenta: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in cuenta.items() if k != 'hash'}


def _arranque() -> None:
    """Crea la primera cuenta de administración desde el .env si no hay ninguna."""
    datos = _leer()
    if datos['usuarios']:
        return
    usuario = (os.getenv('ADMIN_INICIAL_USUARIO') or '').strip().lower()
    clave = os.getenv('ADMIN_INICIAL_CLAVE') or ''
    if usuario and len(clave) >= 8:
        from core.seguridad import hash_clave
        datos['usuarios'].append({
            'usuario': usuario, 'nombre': 'Administración de TI', 'correo': '', 'rol': 'ADMIN_TI',
            'instituciones': ['UNEMI_PRUEBAS', 'OULAD_UK'], 'hash': hash_clave(clave), 'activo': True,
            'creado': dt.datetime.now().isoformat(timespec='seconds'), 'ultimo_acceso': None,
        })
        _escribir(datos)


def listar() -> list[dict[str, Any]]:
    """Devuelve todas las cuentas sin el hash de la contraseña."""
    with _candado:
        _arranque()
        return [_sin_hash(c) for c in _leer()['usuarios']]


def buscar(usuario: str, con_hash: bool = False) -> dict[str, Any] | None:
    """Busca una cuenta por nombre de usuario (sin distinguir mayúsculas)."""
    usuario = (usuario or '').strip().lower()
    with _candado:
        _arranque()
        for c in _leer()['usuarios']:
            if c['usuario'] == usuario:
                return c if con_hash else _sin_hash(c)
    return None


def _validar(usuario: str, rol: str, instituciones: list[str]) -> None:
    if not _PATRON_USUARIO.match(usuario):
        raise ValueError('El usuario debe tener de 3 a 40 caracteres: letras minúsculas, números, punto o guion.')
    if rol not in ROLES_VALIDOS:
        raise ValueError(f'Rol no válido. Use uno de: {", ".join(ROLES_VALIDOS)}.')
    if not instituciones:
        raise ValueError('Asigne al menos una institución.')


def crear(usuario: str, nombre: str, correo: str, rol: str, instituciones: list[str], clave: str) -> dict:
    """Crea una cuenta nueva con la contraseña indicada (mínimo 8 caracteres)."""
    from core.seguridad import hash_clave
    usuario = usuario.strip().lower()
    instituciones = [i.strip().upper() for i in instituciones if i.strip()]
    _validar(usuario, rol, instituciones)
    if len(clave) < 8:
        raise ValueError('La contraseña debe tener al menos 8 caracteres.')
    with _candado:
        datos = _leer()
        if any(c['usuario'] == usuario for c in datos['usuarios']):
            raise ValueError('Ya existe una cuenta con ese usuario.')
        cuenta = {'usuario': usuario, 'nombre': nombre.strip() or usuario, 'correo': correo.strip(),
                  'rol': rol, 'instituciones': instituciones, 'hash': hash_clave(clave), 'activo': True,
                  'creado': dt.datetime.now().isoformat(timespec='seconds'), 'ultimo_acceso': None}
        datos['usuarios'].append(cuenta)
        _escribir(datos)
        return _sin_hash(cuenta)


def actualizar(usuario: str, **cambios: Any) -> dict:
    """Actualiza nombre, correo, rol, instituciones, estado o contraseña de una cuenta."""
    from core.seguridad import hash_clave
    usuario = usuario.strip().lower()
    with _candado:
        datos = _leer()
        cuenta = next((c for c in datos['usuarios'] if c['usuario'] == usuario), None)
        if cuenta is None:
            raise KeyError('La cuenta no existe.')
        for campo in ('nombre', 'correo'):
            if cambios.get(campo) is not None:
                cuenta[campo] = str(cambios[campo]).strip()
        if cambios.get('rol') is not None or cambios.get('instituciones') is not None:
            rol = cambios.get('rol') or cuenta['rol']
            inst = [i.strip().upper() for i in (cambios.get('instituciones') or cuenta['instituciones'])]
            _validar(usuario, rol, inst)
            cuenta['rol'], cuenta['instituciones'] = rol, inst
        if cambios.get('activo') is not None:
            cuenta['activo'] = bool(cambios['activo'])
        if cambios.get('clave'):
            if len(cambios['clave']) < 8:
                raise ValueError('La contraseña debe tener al menos 8 caracteres.')
            cuenta['hash'] = hash_clave(cambios['clave'])
        if cambios.get('ultimo_acceso'):
            cuenta['ultimo_acceso'] = cambios['ultimo_acceso']
        _escribir(datos)
        return _sin_hash(cuenta)


def eliminar(usuario: str) -> None:
    """Elimina una cuenta; nunca deja el sistema sin una cuenta ADMIN_TI activa."""
    usuario = usuario.strip().lower()
    with _candado:
        datos = _leer()
        restantes = [c for c in datos['usuarios'] if c['usuario'] != usuario]
        if len(restantes) == len(datos['usuarios']):
            raise KeyError('La cuenta no existe.')
        if not any(c['rol'] == 'ADMIN_TI' and c.get('activo', True) for c in restantes):
            raise ValueError('No se puede eliminar la última cuenta de administración activa.')
        datos['usuarios'] = restantes
        _escribir(datos)
