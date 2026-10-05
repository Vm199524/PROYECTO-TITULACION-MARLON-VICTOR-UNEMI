# -*- coding: utf-8 -*-
"""
Minimización de datos personales antes de enviarlos a un proveedor externo de IA.

Implementa el RNF de privacidad (LOPDP: minimización y finalidad). El SQL se
genera solo con la pregunta y el esquema; las filas salen del sistema únicamente
cuando narrativa_rapida.py pide a Gemini, Groq, NVIDIA NIM o DeepSeek redactar
la explicación. Las columnas que identifican a una persona se reemplazan por un
seudónimo estable («Alumno 1», «Alumno 2») y las cédulas en texto libre se
ocultan. Lo que ve en pantalla el usuario autorizado no pasa por aquí.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
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
    """Normaliza un nombre de columna: minúsculas, sin tildes y con guion bajo en lugar de espacios."""
    s = str(nombre or '').strip().lower()
    for a, b in (('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n'), (' ', '_')):
        s = s.replace(a, b)
    return s


def es_columna_personal(nombre: Any) -> bool:
    """Indica si el valor de la columna identifica a una persona (cédula, nombre, correo, etc.)."""
    n = _normalizar(nombre)
    return n in _COLUMNAS_EXACTAS or bool(_PATRON_COLUMNA.search(n))


def _ocultar_en_texto(valor: Any) -> Any:
    """Oculta los números con forma de cédula o RUC dentro de un texto."""
    if isinstance(valor, str):
        return _PATRON_CEDULA.sub(TEXTO_OCULTO, valor)
    return valor


def enmascarar_filas(columns: list | None, rows: list | None) -> tuple[list, list]:
    """Devuelve (columns, rows) sin datos personales y con la misma forma de entrada.

    Acepta filas como listas, tuplas o dicts. Las columnas personales se
    conservan para que el modelo sepa que existían, pero su valor pasa a ser un
    seudónimo estable por persona dentro de esta llamada; así la narración
    sigue contando bien a personas distintas sin exponer su identidad.
    """
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
    """Enmascara una cédula para mostrarla en pantalla dejando visibles los últimos 4 dígitos (******1234)."""
    s = str(cedula or '')
    return ('*' * max(len(s) - 4, 0)) + s[-4:] if len(s) > 4 else '****'
