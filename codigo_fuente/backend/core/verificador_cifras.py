# -*- coding: utf-8 -*-
"""
Verificador de cifras de la explicación frente al resultado de la consulta.

En el camino de IA generativa el modelo escribe el SQL y la explicación en la
misma respuesta, antes de ejecutar el SQL, por lo que puede citar un número
inventado o dejar marcadores sin rellenar («[carrera]», «{tasa_abandono}»).
Este módulo detecta esas cifras y marcadores (lo mide eval/evaluar_nl2sql.py);
routes_query.py vuelve a redactar la explicación sobre los datos reales y, si
falla, usa resumen_determinista(), que solo cita valores del resultado.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import re
from decimal import Decimal

_NUMERO = re.compile(r'(?<![\w.])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?![\w])')
_MARCADOR = re.compile(r'\[[A-Za-z_áéíóúñ]+\]|\{[A-Za-z_áéíóúñ]+\}')


def _a_float(texto: str) -> float | None:
    """Convierte un número escrito en formato español o inglés a float, o None."""
    t = texto
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+(?:,\d+)?', t):   # 10.848 o 76.924,62
        t = t.replace('.', '').replace(',', '.')
    else:
        t = t.replace(',', '.')
    try:
        return float(t)
    except ValueError:
        return None


def _valores_resultado(rows: list) -> list[float]:
    """Extrae todos los valores numéricos de las filas, incluidos los escritos en texto."""
    valores = []
    for fila in rows or []:
        celdas = fila.values() if isinstance(fila, dict) else fila
        for c in celdas:
            if isinstance(c, bool):
                continue
            if isinstance(c, (int, float, Decimal)):
                valores.append(float(c))
            elif isinstance(c, str):
                valores += [v for v in (_a_float(m) for m in _NUMERO.findall(c)) if v is not None]
    return valores


def _respaldada(x: float, valores: list[float], n_filas: int) -> bool:
    """Indica si `x` coincide con un valor del resultado.

    Acepta el número de filas, años plausibles y valores con tolerancia de
    redondeo, también en escala x100 o /100 (proporción frente a porcentaje).
    """
    if x == n_filas:                      # "se encontraron 18 carreras"
        return True
    if x.is_integer() and 1900 <= x <= 2100:  # años citados en la pregunta o el contexto
        return True
    for v in valores:
        for candidato in (v, v * 100, v / 100):
            if abs(candidato - x) <= max(0.051, abs(candidato) * 0.005):
                return True
    return False


def cifras_no_respaldadas(texto: str, rows: list) -> list[str]:
    """Devuelve los números del texto que no aparecen en el resultado y los marcadores sin rellenar.

    La comparación tolera el redondeo y la escala x100. Los enteros de 0 a 10
    se ignoran porque suelen ser parte de la pregunta («top 5»).
    """
    if not texto:
        return []
    problemas = _MARCADOR.findall(texto)
    valores = _valores_resultado(rows)
    n_filas = len(rows or [])
    for m in _NUMERO.findall(texto):
        x = _a_float(m)
        if x is None or x <= 10 and x.is_integer():   # "top 5", "3 niveles": no son cifras de resultado
            continue
        if not _respaldada(x, valores, n_filas):
            problemas.append(m)
    return problemas


def resumen_determinista(columns: list, rows: list, maximo: int = 5) -> str:
    """Genera un resumen que solo cita valores del resultado; es el último recurso."""
    if not rows:
        return 'La consulta no devolvió registros.'
    cols = list(columns or [])
    if len(rows) == 1:
        fila = rows[0] if not isinstance(rows[0], dict) else [rows[0].get(c) for c in cols]
        partes = [f'**{c}**: {v}' for c, v in zip(cols, fila)]
        return '📊 Resultado: ' + '; '.join(partes) + '.'
    return (f'📊 La consulta devolvió **{len(rows)} registros**; en la tabla se muestran '
            f'{"los primeros " + str(maximo) if len(rows) > maximo else "todos"} con sus valores exactos.')
