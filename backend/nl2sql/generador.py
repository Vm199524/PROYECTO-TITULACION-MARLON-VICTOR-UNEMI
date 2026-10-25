# -*- coding: utf-8 -*-
"""
Generación de SQL con un modelo de lenguaje para preguntas no certificadas.

Estrategia de contexto (Ascoli y Choi, 2025): el modelo recibe el esquema
semántico de las vistas gobernadas, un glosario de definiciones del dominio
académico, las reglas del dialecto T-SQL, los ejemplos certificados más
parecidos a la pregunta (aprendizaje con pocos ejemplos recuperados por
similitud) y las dos últimas preguntas de la conversación. NUNCA recibe filas
de datos para escribir el SQL.

La salida se valida con el árbol sintáctico (validador.py) y, si la base la
rechaza, se intenta UNA corrección con el mensaje de error.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from nl2sql.esquema import GLOSARIO, texto_esquema
from nl2sql.proveedores import RespuestaIA, completar

SISTEMA = """Eres el traductor de preguntas a SQL del sistema académico VicMar, que predice el abandono
estudiantil en una universidad. Tu única tarea es escribir UNA consulta SELECT en T-SQL (SQL Server 2022) que
responda la pregunta de una autoridad académica, usando EXCLUSIVAMENTE estas vistas:

{esquema}

Definiciones del dominio:
{glosario}

Reglas obligatorias:
1. Solo SELECT de lectura sobre las vistas anteriores, sin prefijos de base de datos. Nada de INSERT, UPDATE,
   DELETE, EXEC, tablas físicas ni otras bases.
2. Las vistas ya filtran la institución activa: no agregues filtros de institución.
3. Para contar estudiantes usa COUNT(DISTINCT cedula) en VIS_ALUMNO (tiene una fila por periodo). En
   VIS_PREDICCION_ABANDONO cada fila es un estudiante.
4. Usa TOP N para rankings; CAST(... AS DECIMAL(10,2)) para promedios y porcentajes; alias de columna en
   español entre corchetes, legibles para una persona sin perfil técnico.
5. No inventes columnas. Si la pregunta no se puede responder con estas vistas, devuelve "sql": "" y explica
   por qué en "nota".
6. No incluyas cédulas salvo que se pidan explícitamente; para identificar estudiantes usa apellidos y nombres.

Responde SOLO un objeto JSON, sin texto adicional:
{{"sql": "SELECT ...", "visualizacion": "valor|tabla|barras|lineas", "titulo": "título breve en español", "nota": "supuesto o aclaración breve, o vacío"}}"""

USUARIO = """Ejemplos verificados de preguntas parecidas y su SQL:
{ejemplos}
{historial}
Pregunta: {pregunta}"""

CORRECCION = """La consulta anterior falló.
SQL: {sql}
Error: {error}
Corrígela respetando las mismas reglas y responde solo el JSON."""


@dataclass
class ResultadoGeneracion:
    sql: str = ''
    visualizacion: str = 'tabla'
    titulo: str = ''
    nota: str = ''
    proveedor: str = ''
    modelo: str = ''
    intentos: list[dict] = field(default_factory=list)
    texto_crudo: str = ''


def extraer_json(texto: str) -> dict | None:
    """Extrae el primer objeto JSON de la respuesta del modelo (tolera cercas de código y texto alrededor)."""
    texto = re.sub(r'```(?:json)?', '', texto or '')
    inicio = texto.find('{')
    while inicio != -1:
        profundidad, en_cadena, escape = 0, False, False
        for i in range(inicio, len(texto)):
            c = texto[i]
            if en_cadena:
                escape = (c == '\\' and not escape)
                if c == '"' and not escape:
                    en_cadena = False
                continue
            if c == '"':
                en_cadena = True
            elif c == '{':
                profundidad += 1
            elif c == '}':
                profundidad -= 1
                if profundidad == 0:
                    try:
                        return json.loads(texto[inicio:i + 1])
                    except json.JSONDecodeError:
                        break
        inicio = texto.find('{', inicio + 1)
    m = re.search(r'(SELECT|WITH)\b[\s\S]+', texto, re.I)
    return {'sql': m.group(0).strip()} if m else None


def _a_resultado(r: RespuestaIA, datos: dict | None) -> ResultadoGeneracion:
    datos = datos or {}
    viz = str(datos.get('visualizacion') or 'tabla').lower()
    return ResultadoGeneracion(sql=str(datos.get('sql') or '').strip(),
                               visualizacion=viz if viz in ('valor', 'tabla', 'barras', 'lineas') else 'tabla',
                               titulo=str(datos.get('titulo') or '').strip()[:120], nota=str(datos.get('nota') or '')[:300],
                               proveedor=r.proveedor, modelo=r.modelo, intentos=r.intentos, texto_crudo=r.texto[:2000])


def generar(pregunta: str, ejemplos: list[tuple[str, str]], historial: list[dict] | None = None) -> ResultadoGeneracion:
    """Pide el SQL a la cascada de proveedores."""
    sistema = SISTEMA.format(esquema=texto_esquema(), glosario='\n'.join(f'- {g}' for g in GLOSARIO))
    texto_ej = '\n'.join(f'P: {p}\nSQL: {s}' for p, s in ejemplos) or '(sin ejemplos)'
    texto_hist = ''
    if historial:
        ultimas = [h for h in historial if h.get('pregunta')][-2:]
        if ultimas:
            texto_hist = '\nPreguntas anteriores de la conversación (por si la actual hace referencia a ellas):\n' + \
                         '\n'.join(f"- {h['pregunta']}" for h in ultimas) + '\n'
    r = completar(sistema, USUARIO.format(ejemplos=texto_ej, historial=texto_hist, pregunta=pregunta.strip()))
    return _a_resultado(r, extraer_json(r.texto))


def corregir(pregunta: str, anterior: ResultadoGeneracion, error: str, ejemplos: list[tuple[str, str]]) -> ResultadoGeneracion:
    """Un intento de corrección con el mensaje de error de la validación o de la base."""
    sistema = SISTEMA.format(esquema=texto_esquema(), glosario='\n'.join(f'- {g}' for g in GLOSARIO))
    texto_ej = '\n'.join(f'P: {p}\nSQL: {s}' for p, s in ejemplos)
    usuario = USUARIO.format(ejemplos=texto_ej, historial='', pregunta=pregunta) + '\n\n' + \
        CORRECCION.format(sql=anterior.sql, error=error)
    r = completar(sistema, usuario)
    return _a_resultado(r, extraer_json(r.texto))
