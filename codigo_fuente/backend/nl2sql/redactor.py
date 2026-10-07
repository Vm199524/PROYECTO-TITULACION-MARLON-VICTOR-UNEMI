# -*- coding: utf-8 -*-
"""
Redacción de la respuesta y elección de la visualización.

  - Resumen determinista: toda respuesta trae una frase construida SOLO con
    los valores del resultado (nunca con cifras que el modelo imagine).
  - Interpretación con IA (opcional, a pedido del usuario): el proveedor
    recibe las filas seudonimizadas y redacta una lectura breve. Antes de
    mostrarla, el verificador de cifras comprueba que cada número citado
    exista en el resultado; si encuentra uno que no, se descarta la
    interpretación y queda el resumen determinista.
  - Visualización: valor, tabla, barras o líneas según la forma del
    resultado (una cifra, categorías, serie temporal).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import re
from decimal import Decimal

from core.privacidad import seudonimizar

_NUMERO = re.compile(r'(?<![\w.])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?![\w])')
_MARCADOR = re.compile(r'\[[A-Za-z_áéíóúñ]+\]|\{[A-Za-z_áéíóúñ]+\}')
_TEMPORAL = re.compile(r'(año|anio|mes|periodo|fecha|corte|semestre)', re.I)


def formato_numero(v) -> str:
    """Número con formato del Ecuador: 1.234,5."""
    if isinstance(v, bool) or v is None:
        return '—' if v is None else str(v)
    if isinstance(v, (int,)) or (isinstance(v, float) and v.is_integer() and abs(v) >= 1):
        return f'{int(v):,}'.replace(',', '.')
    if isinstance(v, (float, Decimal)):
        return f'{float(v):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return str(v)


def _es_numero(v) -> bool:
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)


def elegir_visualizacion(columnas: list[str], filas: list[list], sugerida: str | None = None) -> str:
    """valor | tabla | barras | lineas, según la forma del resultado."""
    if not filas:
        return 'tabla'
    if len(filas) == 1 and len(columnas) == 1:
        return 'valor'
    numericas = [i for i in range(len(columnas)) if all(_es_numero(f[i]) or f[i] is None for f in filas)]
    if len(columnas) >= 2 and numericas and 2 <= len(filas) <= 30 and 0 not in numericas:
        if _TEMPORAL.search(columnas[0]):
            return 'lineas'
        return sugerida if sugerida in ('barras', 'lineas') else 'barras'
    if len(columnas) >= 2 and _TEMPORAL.search(columnas[0]) and 1 in numericas and len(filas) >= 2:
        return 'lineas'
    return 'tabla'


def resumen(titulo: str, columnas: list[str], filas: list[list]) -> str:
    """Frase que solo cita valores del resultado."""
    if not filas:
        return f'No se encontraron registros para «{titulo or "la consulta"}».'
    if len(filas) == 1:
        partes = [f'{c}: **{formato_numero(v)}**' for c, v in zip(columnas, filas[0])]
        return (f'{titulo}: ' if titulo else '') + '; '.join(partes) + '.'
    numericas = [i for i in range(1, len(columnas)) if all(_es_numero(f[i]) for f in filas)]
    texto = f'{titulo}: {formato_numero(len(filas))} registros.' if titulo else f'{len(filas)} registros.'
    if numericas and len(columnas) >= 2:
        i = numericas[0]
        mayor = max(filas, key=lambda f: f[i])
        menor = min(filas, key=lambda f: f[i])
        texto += (f' El valor más alto de {columnas[i].lower()} corresponde a **{mayor[0]}** ({formato_numero(mayor[i])})'
                  f' y el más bajo a {menor[0]} ({formato_numero(menor[i])}).')
    return texto


# ── Verificación de cifras de un texto generado ─────────────────────────
def _a_float(t: str) -> float | None:
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+(?:,\d+)?', t):
        t = t.replace('.', '').replace(',', '.')
    else:
        t = t.replace(',', '.')
    try:
        return float(t)
    except ValueError:
        return None


def cifras_no_respaldadas(texto: str, filas: list[list]) -> list[str]:
    """Números del texto que no aparecen en el resultado (tolera redondeo y escala x100) y marcadores sin llenar."""
    if not texto:
        return []
    problemas = _MARCADOR.findall(texto)
    valores = []
    for f in filas or []:
        for c in f:
            if _es_numero(c):
                valores.append(float(c))
            elif isinstance(c, str):
                valores += [v for v in (_a_float(m) for m in _NUMERO.findall(c)) if v is not None]
    for m in _NUMERO.findall(texto):
        x = _a_float(m)
        if x is None or (x <= 10 and x.is_integer()) or x == len(filas or []) or (x.is_integer() and 1900 <= x <= 2100):
            continue
        if not any(abs(c - x) <= max(0.051, abs(c) * 0.005) for v in valores for c in (v, v * 100, v / 100)):
            problemas.append(m)
    return problemas


INTERPRETAR_SISTEMA = """Eres un analista institucional que explica resultados a una autoridad universitaria sin perfil
técnico. Escribe en español del Ecuador, en 2 o 3 frases, qué muestra el resultado y qué conviene mirar después.
Reglas: cita solo cifras que estén en el resultado; no inventes causas; no nombres vistas, tablas ni columnas
técnicas; no uses emojis ni muletillas. Si el resultado está vacío, dilo con claridad."""


def interpretar(pregunta: str, columnas: list[str], filas: list[list]) -> dict:
    """Interpretación con IA de un resultado, verificada contra sus cifras."""
    from nl2sql.proveedores import SinProveedores, completar
    cols, seudo = seudonimizar(list(columnas), [list(f) for f in filas[:25]])
    tabla = '\n'.join([' | '.join(cols)] + [' | '.join(formato_numero(v) for v in f) for f in seudo])
    try:
        r = completar(INTERPRETAR_SISTEMA, f'Pregunta: {pregunta}\nResultado ({len(filas)} filas):\n{tabla}', max_tokens=500)
    except SinProveedores as exc:
        return {'texto': '', 'verificada': False, 'motivo': str(exc)}
    texto = r.texto.strip()
    problemas = cifras_no_respaldadas(texto, filas)
    if problemas:
        return {'texto': '', 'verificada': False, 'proveedor': r.proveedor,
                'motivo': f'La interpretación citaba cifras que no están en el resultado ({", ".join(problemas[:3])}) y se descartó.'}
    return {'texto': texto, 'verificada': True, 'proveedor': r.proveedor, 'modelo': r.modelo}
