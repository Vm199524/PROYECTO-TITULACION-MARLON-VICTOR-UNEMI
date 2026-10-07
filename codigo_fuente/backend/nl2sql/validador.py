# -*- coding: utf-8 -*-
"""
Validador estructural del SQL generado (capa 3 de seguridad, en la aplicación).

En lugar de buscar palabras prohibidas con expresiones regulares, que se
burlan con comentarios o mayúsculas, el SQL se analiza con sqlglot y se
valida su ÁRBOL SINTÁCTICO:

  1. Una sola sentencia, y debe ser una lectura (SELECT, con CTE o UNION).
  2. Ningún nodo de escritura o definición en todo el árbol (INSERT, UPDATE,
     DELETE, MERGE, DROP, CREATE, ALTER, SELECT INTO, EXEC, USE...).
  3. Solo se leen las vistas gobernadas VIS_* (o CTE definidas en la misma
     consulta); nada de tablas físicas, catálogos del sistema ni otras bases.
  4. Funciones peligrosas prohibidas (OPENROWSET, OPENQUERY, xp_, sp_...).
  5. Las columnas deben existir en las vistas que se leen (o ser alias).
  6. Si la consulta no limita filas, se le agrega TOP 500.

Aunque este filtro fallara, la cuenta chat_reader no tiene permiso para
escribir ni para leer otra cosa que las vistas: la garantía real está en el
motor de base de datos.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from nl2sql.esquema import columnas_permitidas

LIMITE_FILAS = 500
_FUNCIONES_PROHIBIDAS = re.compile(r'^(openrowset|openquery|opendatasource|openxml|xp_|sp_|fn_|bulk)', re.I)
_NODOS_PROHIBIDOS = tuple(t for t in (
    getattr(exp, n, None) for n in ('Insert', 'Update', 'Delete', 'Merge', 'Drop', 'Create', 'Alter', 'Into',
                                    'Command', 'Transaction', 'Commit', 'Rollback', 'Use', 'Grant', 'Set',
                                    'TruncateTable', 'Copy', 'LoadData')) if t is not None)


@dataclass
class ResultadoValidacion:
    sql: str = ''
    problemas: list[str] = field(default_factory=list)
    vistas: list[str] = field(default_factory=list)

    @property
    def valido(self) -> bool:
        return not self.problemas


def limpiar(sql: str) -> str:
    """Quita cercas de Markdown, espacios y el punto y coma final."""
    sql = re.sub(r'```(?:sql)?', '', sql or '', flags=re.I).strip()
    return sql.rstrip(';').strip()


def validar(sql: str, limite: int = LIMITE_FILAS) -> ResultadoValidacion:
    """Valida el SQL y devuelve la versión segura (con límite de filas) o los problemas."""
    r = ResultadoValidacion()
    sql = limpiar(sql)
    if not sql:
        r.problemas.append('La consulta está vacía.')
        return r
    try:
        sentencias = [s for s in sqlglot.parse(sql, read='tsql') if s is not None]
    except sqlglot.errors.ParseError as exc:
        r.problemas.append(f'SQL no válido para SQL Server: {str(exc).splitlines()[0][:200]}')
        return r
    if len(sentencias) != 1:
        r.problemas.append('Solo se permite una sentencia por consulta.')
        return r
    arbol = sentencias[0]
    if not isinstance(arbol, (exp.Select, exp.Union, exp.Intersect, exp.Except, exp.Subquery)):
        r.problemas.append('Solo se permiten consultas de lectura (SELECT).')
        return r
    for nodo in arbol.walk():
        nodo = nodo[0] if isinstance(nodo, tuple) else nodo
        if isinstance(nodo, _NODOS_PROHIBIDOS):
            r.problemas.append(f'Operación no permitida: {type(nodo).__name__.upper()}.')
            return r

    ctes = {c.alias_or_name.upper() for c in arbol.find_all(exp.CTE)}
    permitidas = columnas_permitidas()
    vistas: set[str] = set()
    for tabla in arbol.find_all(exp.Table):
        nombre = (tabla.name or '').upper()
        if nombre in ctes:
            continue
        esquema, catalogo = (tabla.db or '').lower(), (tabla.catalog or '')
        if catalogo or esquema not in ('', 'dbo'):
            r.problemas.append(f'No se permite leer objetos de otra base o esquema ({tabla.sql(dialect="tsql")}).')
        elif nombre not in permitidas:
            r.problemas.append(f'Objeto no autorizado: {tabla.name}. Solo se pueden leer las vistas VIS_*.')
        else:
            vistas.add(nombre)
    for funcion in arbol.find_all(exp.Anonymous, exp.Func):
        nombre = (getattr(funcion, 'name', '') or funcion.sql_name() or '').lower()
        if _FUNCIONES_PROHIBIDAS.match(nombre):
            r.problemas.append(f'Función no permitida: {nombre}.')
    if r.problemas:
        return r

    alias = {a.alias.lower() for a in arbol.find_all(exp.Alias) if a.alias}
    alias |= {c.alias_or_name.lower() for c in arbol.find_all(exp.CTE)}
    for cte in arbol.find_all(exp.CTE):
        alias |= {s.alias_or_name.lower() for s in cte.this.selects if hasattr(cte.this, 'selects')}
    conocidas = set().union(*(permitidas[v] for v in vistas)) if vistas else set()
    for columna in arbol.find_all(exp.Column):
        nombre = (columna.name or '').lower()
        if nombre and nombre != '*' and nombre not in conocidas and nombre not in alias:
            r.problemas.append(f"La columna '{columna.name}' no existe en {', '.join(sorted(vistas)) or 'las vistas'}.")
    if r.problemas:
        return r

    if isinstance(arbol, exp.Select) and not arbol.args.get('limit') and not arbol.args.get('fetch'):
        arbol = arbol.limit(limite)
    r.sql = arbol.sql(dialect='tsql')
    r.vistas = sorted(vistas)
    return r
