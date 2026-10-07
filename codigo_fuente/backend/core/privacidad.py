# -*- coding: utf-8 -*-
"""
Protección de datos personales de los estudiantes (LOPDP del Ecuador).

Aplica tres principios de la Ley Orgánica de Protección de Datos Personales
(2021):
  - Minimización: antes de que unas filas salgan hacia un proveedor externo
    de IA para redactar una respuesta, las columnas que identifican a una
    persona se reemplazan por un seudónimo («Estudiante 1») y cualquier
    número con forma de cédula se oculta.
  - Finalidad y acceso: en pantalla la cédula siempre aparece enmascarada
    (******1234) y la ficha de un estudiante se identifica con un token
    cifrado, no con su cédula, para que no viaje en direcciones ni registros.
  - Seguridad: el token se cifra con una llave derivada del secreto del
    servidor (Fernet: AES-128 en modo CBC con HMAC-SHA256).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import base64
import hashlib
import re
import unicodedata
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from core.config import CONFIG

_COLUMNAS_PERSONALES = {
    'cedula', 'identificacion', 'dni', 'pasaporte', 'apellidos', 'apellido', 'nombres',
    'nombre_completo', 'alumno', 'estudiante', 'correo', 'email', 'telefono', 'celular', 'direccion',
}
_PATRON_COLUMNA = re.compile(r'(^|_)(cedula|identificacion|correo|email|telefono|celular|direccion|apellido)')
_PATRON_CEDULA = re.compile(r'(?<!\d)(\d{10}|\d{13})(?!\d)')
OCULTO = '[dato personal oculto]'


def _normalizar(nombre: Any) -> str:
    s = unicodedata.normalize('NFKD', str(nombre or '')).encode('ascii', 'ignore').decode()
    return s.strip().lower().replace(' ', '_')


def es_columna_personal(nombre: Any) -> bool:
    """Indica si una columna identifica a una persona."""
    n = _normalizar(nombre)
    return n in _COLUMNAS_PERSONALES or bool(_PATRON_COLUMNA.search(n))


def enmascarar_cedula(cedula: Any) -> str:
    """Deja visibles solo los últimos 4 caracteres: ******1234."""
    s = str(cedula or '')
    return ('*' * (len(s) - 4)) + s[-4:] if len(s) > 4 else '****'


def seudonimizar(columnas: list[str], filas: list[list[Any]]) -> tuple[list[str], list[list[Any]]]:
    """Reemplaza las columnas personales por un seudónimo estable dentro de la llamada.

    Se usa antes de enviar filas a un proveedor externo de IA: el modelo puede
    redactar «dos estudiantes en riesgo alto» sin conocer quiénes son.
    """
    personales = [i for i, c in enumerate(columnas) if es_columna_personal(c)]
    seudonimos: dict[tuple, str] = {}
    salida = []
    for fila in filas:
        clave = tuple(str(fila[i]) for i in personales)
        if personales and clave not in seudonimos:
            seudonimos[clave] = f'Estudiante {len(seudonimos) + 1}'
        nueva = []
        for i, v in enumerate(fila):
            if i in personales:
                nueva.append(seudonimos[clave])
            elif isinstance(v, str):
                nueva.append(_PATRON_CEDULA.sub(OCULTO, v))
            else:
                nueva.append(v)
        salida.append(nueva)
    return columnas, salida


def enmascarar_para_pantalla(columnas: list[str], filas: list[list[Any]]) -> list[list[Any]]:
    """Enmascara las columnas de identificación (cédula) que se muestran en pantalla."""
    idx = [i for i, c in enumerate(columnas) if _normalizar(c) in ('cedula', 'identificacion', 'dni', 'pasaporte')]
    if not idx:
        return filas
    return [[enmascarar_cedula(v) if i in idx else v for i, v in enumerate(f)] for f in filas]


def _fernet() -> Fernet:
    llave = hashlib.sha256(('vicmar-token-estudiante|' + CONFIG.jwt_clave).encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(llave))


def token_estudiante(cedula: str) -> str:
    """Token opaco que identifica a un estudiante en la API sin exponer su cédula."""
    return _fernet().encrypt(str(cedula).encode('utf-8')).decode('ascii')


def cedula_desde_token(token: str) -> str | None:
    """Recupera la cédula de un token emitido por este servidor (o None si no es válido)."""
    try:
        return _fernet().decrypt(token.encode('ascii'), ttl=60 * 60 * 24).decode('utf-8')
    except (InvalidToken, ValueError):
        return None
