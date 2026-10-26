# -*- coding: utf-8 -*-
"""
Contenido del trabajo final: reúne los capítulos y numera figuras y tablas.

Los capítulos se escriben con referencias por clave ({F:clave} y {T:clave}) y
con figuras y tablas identificadas por esa misma clave; aquí se asignan los
números en el orden en que aparecen, de modo que el texto nunca cita una
figura o tabla con el número equivocado al agregar o quitar elementos.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import re

import _c1_introduccion
import _c2_analisis
import _c3_diseno
import _c3c_desarrollo
import _c4_cierre
from _c4_cierre import resumen_abstract  # noqa: F401  (lo usa construir_trabajo_final.py)

_REF = re.compile(r'\{([FT]):([a-z0-9_]+)\}')


def bloques() -> list[tuple]:
    crudos = (_c1_introduccion.bloques() + _c2_analisis.bloques() + _c3_diseno.bloques() + _c3c_desarrollo.bloques()
              + _c4_cierre.bloques())
    numeros = {'F': {}, 'T': {}}
    for b in crudos:
        if b[0] in ('fig', 'tab'):
            tipo = 'F' if b[0] == 'fig' else 'T'
            clave = b[1]
            if clave in numeros[tipo]:
                raise ValueError(f'Clave repetida: {tipo}:{clave}')
            numeros[tipo][clave] = len(numeros[tipo]) + 1

    def resolver(texto: str) -> str:
        def cambio(m):
            tipo, clave = m.group(1), m.group(2)
            if clave not in numeros[tipo]:
                raise KeyError(f'Referencia sin destino: {m.group(0)}')
            return f"{'Figura' if tipo == 'F' else 'Tabla'} {numeros[tipo][clave]}"
        return _REF.sub(cambio, texto)

    salida = []
    for b in crudos:
        if b[0] == 'p':
            salida.append(('p', resolver(b[1])))
        elif b[0] == 'ul':
            salida.append(('ul', [resolver(x) for x in b[1]]))
        elif b[0] in ('fig', 'tab'):
            salida.append((b[0],) + tuple(b[2:]))
        else:
            salida.append(b)
    citadas = {'F': set(), 'T': set()}
    for b in crudos:
        textos = [b[1]] if b[0] == 'p' else (b[1] if b[0] == 'ul' else [])
        for t in textos:
            for m in _REF.finditer(t):
                citadas[m.group(1)].add(m.group(2))
    sin_citar = [f'{t}:{k}' for t in 'FT' for k in numeros[t] if k not in citadas[t]]
    if sin_citar:
        raise ValueError(f'Figuras o tablas sin mención en el texto: {sin_citar}')
    return salida
