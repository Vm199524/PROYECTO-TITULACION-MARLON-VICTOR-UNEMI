# -*- coding: utf-8 -*-
"""
Enrutador semántico hacia las métricas certificadas.

Antes de recurrir al modelo de lenguaje, la pregunta se compara con las
preguntas de ejemplo de cada métrica certificada:

  1. Se reconocen las entidades de la pregunta (carrera, facultad, nivel de
     riesgo, año, cantidad) contra los valores reales de la institución, sin
     importar tildes ni mayúsculas, y se reemplazan por marcadores
     (<carrera>, <riesgo>, ...). Así «¿cuántos activos hay en Medicina?» y
     «¿cuántos activos hay en Derecho?» tienen la misma forma.
  2. Se mide la similitud entre esa forma y las preguntas de ejemplo con
     TF-IDF de n-gramas de caracteres (robusto a errores de tipeo y a
     variantes morfológicas del español).
  3. Si la mejor métrica supera el umbral y la pregunta trae todas las
     entidades que la métrica necesita, se responde con su SQL fijo y
     verificado; si no, la pregunta pasa al modelo de lenguaje.

Las mismas preguntas de ejemplo sirven de ejemplos guiados (few-shot) para el
modelo de lenguaje cuando la pregunta no es certificada.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

RUTA_CATALOGO = Path(__file__).resolve().parent / 'catalogo_metricas.json'
UMBRAL_CERTIFICADA = 0.56
N_POR_DEFECTO = 10

_PALABRAS_VACIAS = {'el', 'la', 'los', 'las', 'de', 'del', 'en', 'y', 'a', 'que', 'qué', 'por', 'para', 'un', 'una',
                    'me', 'mi', 'nos', 'se', 'al', 'lo', 'es', 'son', 'hay', 'con', 'su', 'sus', 'o'}


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos de puntuación."""
    t = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode().lower()
    t = re.sub(r'[^a-z0-9<>\s-]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


# Expresiones coloquiales con que una autoridad nombra el abandono; se llevan a
# una sola forma antes de comparar, tanto en la pregunta como en los ejemplos.
_SINONIMOS = (
    (r'\b(dejar|dejen|deje|dejan) (la carrera|los estudios|de estudiar|la universidad)\b', 'abandonar'),
    (r'\b(desertar|desercion|desertores|retirarse|se retiren|retiro estudiantil)\b', 'abandono'),
    (r'\bestudiantes?\b', 'alumnos'),
)


def canonizar(texto_norm: str) -> str:
    for patron, reemplazo in _SINONIMOS:
        texto_norm = re.sub(patron, reemplazo, texto_norm)
    return texto_norm


@dataclass
class Entidades:
    carrera: str | None = None
    facultad: str | None = None
    riesgo: list[str] = field(default_factory=list)
    segmento: str | None = None
    anio: int | None = None
    n: int | None = None
    forma: str = ''

    def valor(self, nombre: str):
        if nombre == 'n':
            return self.n or N_POR_DEFECTO
        return getattr(self, nombre)


def _buscar_nombre(texto_norm: str, candidatos: list[str]) -> tuple[str | None, str | None]:
    """Busca el nombre de carrera o facultad mencionado (exacto o aproximado). Devuelve (nombre, fragmento)."""
    mejor, fragmento, puntaje = None, None, 0.0
    for nombre in candidatos:
        n = normalizar(nombre)
        n_corto = re.sub(r'^(facultad de |modulo |ingenieria en |licenciatura en )', '', n)
        for variante in {n, n_corto}:
            if len(variante) >= 4 and re.search(rf'\b{re.escape(variante)}\b', texto_norm):
                if len(variante) > puntaje:
                    mejor, fragmento, puntaje = nombre, variante, len(variante)
    if mejor:
        return mejor, fragmento
    # Aproximado: ventanas de 1 a 4 palabras contra cada nombre (errores de tipeo).
    palabras = texto_norm.split()
    for nombre in candidatos:
        n = normalizar(nombre)
        largo = len(n.split())
        for i in range(len(palabras)):
            ventana = ' '.join(palabras[i:i + largo])
            r = difflib.SequenceMatcher(None, ventana, n).ratio()
            if r > 0.86 and r > puntaje:
                mejor, fragmento, puntaje = nombre, ventana, r
    return mejor, fragmento


def extraer_entidades(pregunta: str, carreras: list[str], facultades: list[str]) -> Entidades:
    """Reconoce las entidades de la pregunta y devuelve también su forma con marcadores."""
    e = Entidades()
    forma = normalizar(pregunta)
    carrera, frag = _buscar_nombre(forma, carreras)
    if carrera:
        e.carrera = carrera
        forma = forma.replace(frag, ' <carrera> ')
    else:
        facultad, frag = _buscar_nombre(forma, facultades)
        if facultad:
            e.facultad = facultad
            forma = forma.replace(frag, ' <facultad> ')
    if re.search(r'medio o alto|alto o medio|alto y medio|medio y alto|\ben riesgo\b(?! (alto|medio|bajo))', forma):
        e.riesgo = ['ALTO', 'MEDIO']
    for nivel in ('alto', 'medio', 'bajo'):
        if re.search(rf'riesgo (de abandono )?(muy )?{nivel}\b|\b{nivel} riesgo', forma) and nivel.upper() not in e.riesgo:
            e.riesgo.append(nivel.upper())
    if e.riesgo:
        forma = re.sub(r'riesgo (de abandono )?(muy )?(alto|medio|bajo)( o (alto|medio|bajo))?', 'riesgo <riesgo>', forma)
    if 'atencion prioritaria' in forma:
        e.segmento = 'Atención prioritaria'
    m = re.search(r'\b(19|20)\d{2}\b', forma)
    if m:
        e.anio = int(m.group(0))
        forma = forma.replace(m.group(0), '<anio>')
    m = re.search(r'\b(?:los|las|top|primeros|primeras)\s+(\d{1,3})\b', forma) or re.search(r'\b(\d{1,3})\s+(?:estudiantes|alumnos)', forma)
    if m:
        e.n = max(1, min(int(m.group(1)), 200))
        forma = forma.replace(m.group(1), '<n>', 1)
    e.forma = re.sub(r'\s+', ' ', canonizar(forma)).strip()
    return e


@lru_cache(maxsize=1)
def catalogo() -> list[dict]:
    return json.loads(RUTA_CATALOGO.read_text(encoding='utf-8'))['metricas']


@lru_cache(maxsize=1)
def _indice():
    metricas = catalogo()
    textos, duenos = [], []
    for i, m in enumerate(metricas):
        for p in m['preguntas']:
            textos.append(canonizar(normalizar(p)))
            duenos.append(i)
    vectorizador = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)
    matriz = vectorizador.fit_transform(textos)
    return vectorizador, matriz, np.asarray(duenos), textos


@dataclass
class Coincidencia:
    metrica: dict
    similitud: float
    faltantes: list[str]
    no_cubiertos: list[str] = field(default_factory=list)


# Palabras que no distinguen una métrica de otra: aparecen en casi cualquier pregunta.
_GENERICAS = {
    'cuantos', 'cuantas', 'cuanto', 'cual', 'cuales', 'como', 'donde', 'alumnos', 'alumno', 'estudiantes',
    'estudiante', 'muestrame', 'mostrar', 'muestra', 'dame', 'dime', 'quiero', 'saber', 'favor', 'lista', 'total',
    'numero', 'cantidad', 'tiene', 'tienen', 'tenemos', 'institucion', 'universidad', 'actualmente', 'ahora',
    'actual', 'esta', 'estan', 'esto', 'este', 'ese', 'sobre', 'segun', 'datos', 'hoy', 'vigente', 'vigentes',
    'matricula', 'activos', 'activo', 'han', 'ser', 'sido', 'puedes', 'podrias', 'nuestra', 'nuestro', 'nuestros',
    'nuestras', 'mas', 'menos', 'todos', 'todas', 'por', 'que', 'una', 'uno', 'las', 'los', 'del', 'periodo',
    'presente', 'actualidad', 'sus', 'hay', 'ver', 'consulta', 'informacion', 'quisiera', 'necesito',
}


_DEL_MODELO = re.compile(r'riesgo|probab|abandon|alerta|prediccion|modelo|desert|segment')


def _raiz(palabra: str) -> str:
    """Reducción mínima de plurales para comparar vocabulario («carreras» → «carrera»)."""
    for sufijo in ('es', 's'):
        if len(palabra) > 5 and palabra.endswith(sufijo):
            return palabra[: -len(sufijo)]
    return palabra


def _terminos(texto: str) -> set[str]:
    return {_raiz(p) for p in re.findall(r'[a-z0-9]{3,}', texto) if p not in _GENERICAS and p not in _PALABRAS_VACIAS}


@lru_cache(maxsize=1)
def _vocabularios() -> list[set[str]]:
    return [set().union(*(_terminos(canonizar(normalizar(p))) for p in m['preguntas'])) | _terminos(canonizar(normalizar(m['titulo'])))
            for m in catalogo()]


def buscar(entidades: Entidades, cuantas: int = 5) -> list[Coincidencia]:
    """Métricas más parecidas a la forma de la pregunta, ajustadas por cobertura de términos.

    La similitud de caracteres sola confunde preguntas que comparten frases
    largas («alumnos con matrícula vigente en cada sede» frente a «... en cada
    carrera»). Por eso cada término informativo de la pregunta que la métrica
    no cubre en su vocabulario resta 0,12 al ordenar, y elegir() exige que no
    quede ninguno: una métrica certificada solo responde si entiende TODA la
    pregunta.
    """
    vectorizador, matriz, duenos, _ = _indice()
    sims = (matriz @ vectorizador.transform([entidades.forma]).T).toarray().ravel()
    por_metrica: dict[int, float] = {}
    for fila, s in enumerate(sims):
        m = int(duenos[fila])
        por_metrica[m] = max(por_metrica.get(m, 0.0), float(s))
    terminos = _terminos(re.sub(r'<[a-z]+>', ' ', entidades.forma))
    salida = []
    for i, sim in por_metrica.items():
        m = catalogo()[i]
        faltantes = [p for p in m['parametros'] if p != 'n' and not entidades.valor(p)]
        no_cubiertos = terminos - _vocabularios()[i]
        sim -= 0.12 * len(no_cubiertos)
        # Una pregunta que nombra una carrera o facultad nunca se responde con una métrica que no
        # filtra por ella (la cifra sería la de toda la institución).
        for entidad in ('carrera', 'facultad'):
            if entidades.valor(entidad) and entidad not in m['parametros']:
                sim -= 1.0
        # Las métricas del modelo (probabilidad, nivel de riesgo) exigen que la pregunta hable de
        # riesgo o abandono: «el promedio de los activos» se refiere a calificaciones.
        sql_m = m['sql'].lower()
        if ('probabilidad' in sql_m or 'riesgo_categoria' in sql_m) and not _DEL_MODELO.search(entidades.forma):
            sim -= 1.0
        # Un nivel de riesgo concreto («riesgo medio») solo lo responde una métrica que filtre por nivel.
        if len(entidades.riesgo) == 1 and 'riesgo' not in m['parametros']:
            sim -= 1.0
        # «¿Cuántos...?» pide una cifra: se prefieren las métricas que cuentan o suman sobre las que listan.
        if entidades.forma.startswith('cuant') and 'count(' not in sql_m and 'sum(' not in sql_m:
            sim -= 0.3
        salida.append(Coincidencia(m, round(sim, 4), faltantes, sorted(no_cubiertos)))
    salida.sort(key=lambda c: -c.similitud)
    return salida[:cuantas]


def elegir(entidades: Entidades) -> Coincidencia | None:
    """La métrica certificada que responde la pregunta, o None si debe ir al modelo de lenguaje."""
    for c in buscar(entidades, 3):
        if c.similitud < UMBRAL_CERTIFICADA:
            break
        if not c.faltantes and not c.no_cubiertos:
            return c
    return None


def ejemplos_guiados(entidades: Entidades, cuantos: int = 4) -> list[tuple[str, str]]:
    """Pares (pregunta, SQL) de las métricas más parecidas, para guiar al modelo de lenguaje."""
    pares = []
    for c in buscar(entidades, cuantos):
        m = c.metrica
        pregunta = m['preguntas'][0].replace('<carrera>', 'Medicina').replace('<riesgo>', 'alto') \
            .replace('<anio>', '2024').replace('<n>', '5').replace('<facultad>', 'Ciencias de la Salud')
        sql = m['sql']
        for p in m['parametros']:
            ejemplo = {'carrera': "'Medicina'", 'n': '5', 'anio': '2024', 'riesgo': "'ALTO'",
                       'facultad': "'Facultad de Ciencias de la Salud'"}[p]
            sql = sql.replace('(?*)', f'({ejemplo})', 1) if p == 'riesgo' else sql.replace('?', ejemplo, 1)
        pares.append((pregunta, sql))
    return pares
