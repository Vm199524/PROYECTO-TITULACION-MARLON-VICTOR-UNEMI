# -*- coding: utf-8 -*-
"""
privacidad.py — minimización de datos personales antes de enviarlos a un
proveedor EXTERNO de IA (Avance 2, RNF de privacidad; LOPDP, principios de
minimización y finalidad).

Dónde aplica: el SQL lo genera la IA a partir de la pregunta y del esquema
de las vistas VIS_* (sin filas). Las filas de resultado solo salen del
sistema cuando se le pide a un modelo externo que REDACTE la explicación de
un resultado ya calculado:
  - core/narrativa_rapida.py::_intentar_proveedor   (Gemini/Groq/NVIDIA/DeepSeek)
Para redactar "hay 3 alumnos en riesgo alto en Enfermería" el modelo no
necesita saber QUIÉNES son: las columnas que identifican a una persona se
reemplazan por un seudónimo estable dentro de la misma llamada ("Alumno 1",
"Alumno 2", ...) — así la narración sigue siendo correcta (cuenta personas
distintas) sin exponer su identidad. Además, cualquier número con forma de
cédula que aparezca en otra columna se oculta.

La pantalla del usuario autorizado NO pasa por aquí: esto protege lo que
sale hacia terceros, no lo que ve quien tiene permiso de verlo.
"""
from __future__ import annotations

import re
from typing import Any

# Columnas cuyo VALOR identifica a una persona. Se compara el nombre de la
# columna normalizado (minúsculas, sin tildes ni espacios).
_COLUMNAS_EXACTAS = {
    'cedula', 'identificacion', 'dni', 'pasaporte', 'ruc',
    'apellidos', 'apellido', 'nombres', 'nombre_completo', 'nombres_completos',
    'alumno', 'estudiante', 'nombre_alumno', 'nombre_estudiante',
    'correo', 'email', 'correo_electronico', 'telefono', 'celular', 'direccion',
}
_PATRON_COLUMNA = re.compile(
    r'(^|_)(cedula|identificacion|dni|pasaporte|correo|email|telefono|celular|direccion)(_|$)'
)
# Cédula ecuatoriana (10 dígitos) o RUC (13 dígitos) dentro de un texto libre.
_PATRON_CEDULA = re.compile(r'(?<!\d)(\d{10}|\d{13})(?!\d)')

TEXTO_OCULTO = '[dato personal oculto]'


def _normalizar(nombre: Any) -> str:
    s = str(nombre or '').strip().lower()
    for a, b in (('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n'), (' ', '_')):
        s = s.replace(a, b)
    return s


def es_columna_personal(nombre: Any) -> bool:
    n = _normalizar(nombre)
    return n in _COLUMNAS_EXACTAS or bool(_PATRON_COLUMNA.search(n))


def _ocultar_en_texto(valor: Any) -> Any:
    if isinstance(valor, str):
        return _PATRON_CEDULA.sub(TEXTO_OCULTO, valor)
    return valor


def enmascarar_filas(columns: list | None, rows: list | None) -> tuple[list, list]:
    """Devuelve (columns, rows) sin datos personales, con la misma forma de
    entrada (filas como listas/tuplas o como dicts). Las columnas personales
    se conservan (el modelo sabe que existían) pero su valor pasa a ser un
    seudónimo estable por persona dentro de esta llamada."""
    columns = list(columns or [])
    rows = list(rows or [])
    if not rows:
        return columns, rows

    personales = {c for c in columns if es_columna_personal(c)}
    if rows and isinstance(rows[0], dict):
        personales |= {k for k in rows[0] if es_columna_personal(k)}

    seudonimos: dict[tuple, str] = {}

    def _seudonimo(clave: tuple) -> str:
        if clave not in seudonimos:
            seudonimos[clave] = f'Alumno {len(seudonimos) + 1}'
        return seudonimos[clave]

    salida = []
    for fila in rows:
        if isinstance(fila, dict):
            clave = tuple(str(fila.get(c)) for c in sorted(personales))
            nueva = {
                k: (_seudonimo(clave) if k in personales else _ocultar_en_texto(v))
                for k, v in fila.items()
            }
        else:
            valores = list(fila)
            clave = tuple(str(v) for c, v in zip(columns, valores) if c in personales)
            nueva = [
                (_seudonimo(clave) if c in personales else _ocultar_en_texto(v))
                for c, v in zip(columns, valores)
            ]
            nueva += [_ocultar_en_texto(v) for v in valores[len(columns):]]
            nueva = type(fila)(nueva) if isinstance(fila, tuple) else nueva
        salida.append(nueva)
    return columns, salida


def enmascarar_cedula(cedula: Any) -> str:
    """Para mostrar en pantalla: ******1234."""
    s = str(cedula or '')
    return ('*' * max(len(s) - 4, 0)) + s[-4:] if len(s) > 4 else '****'
