# -*- coding: utf-8 -*-
"""
verificador_cifras.py — garantiza que la explicación que ve el usuario no
cite cifras que no están en el resultado.

Problema (detectado el 25/09/2026 por eval/evaluar_nl2sql.py): en el camino
de IA generativa, el modelo escribe el SQL Y la explicación en la MISMA
respuesta, ANTES de que el SQL se ejecute. No conoce el resultado, así que a
veces "completa" la explicación con un número inventado (ej. "ROC-AUC 0,87"
junto a una tabla que dice 0,9971) o deja marcadores sin rellenar
("[carrera]", "{tasa_abandono}"). La tabla es correcta; el texto, no. Para
una autoridad que debe CONFIAR en la respuesta (sección 1.2), eso es grave.

Este módulo detecta esas cifras y marcadores; routes_query.py redacta de
nuevo la explicación sobre los datos reales cuando hace falta (y, si eso
falla, usa `resumen_determinista`, que solo cita valores del resultado).
"""
from __future__ import annotations

import re
from decimal import Decimal

_NUMERO = re.compile(r'(?<![\w.])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?![\w])')
_MARCADOR = re.compile(r'\[[A-Za-z_áéíóúñ]+\]|\{[A-Za-z_áéíóúñ]+\}')


def _a_float(texto: str) -> float | None:
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
    if x == n_filas:                       # "se encontraron 18 carreras"
        return True
    if x.is_integer() and 1900 <= x <= 2100:  # años citados en la pregunta o el contexto
        return True
    for v in valores:
        for candidato in (v, v * 100, v / 100):
            if abs(candidato - x) <= max(0.051, abs(candidato) * 0.005):
                return True
    return False


def cifras_no_respaldadas(texto: str, rows: list) -> list[str]:
    """Números del texto que no aparecen en el resultado (con tolerancia de
    redondeo y escala x100) y marcadores sin rellenar."""
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
    """Resumen que SOLO cita valores del resultado (último recurso)."""
    if not rows:
        return 'La consulta no devolvió registros.'
    cols = list(columns or [])
    if len(rows) == 1:
        fila = rows[0] if not isinstance(rows[0], dict) else [rows[0].get(c) for c in cols]
        partes = [f'**{c}**: {v}' for c, v in zip(cols, fila)]
        return '📊 Resultado: ' + '; '.join(partes) + '.'
    return (f'📊 La consulta devolvió **{len(rows)} registros**; en la tabla se muestran '
            f'{"los primeros " + str(maximo) if len(rows) > maximo else "todos"} con sus valores exactos.')
