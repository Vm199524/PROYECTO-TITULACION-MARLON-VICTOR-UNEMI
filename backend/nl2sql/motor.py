# -*- coding: utf-8 -*-
"""
Motor de consulta conversacional (lenguaje natural a SQL).

Flujo de una pregunta:
  1. Barrera de intención (guardarrailes.py): escritura, inyección, otra
     institución, tablas físicas, saludo, ayuda o fuera de alcance.
  2. Entidades y enrutador semántico (enrutador.py): si la pregunta coincide
     con una métrica certificada, se ejecuta su SQL fijo con parámetros
     enlazados; el modelo de lenguaje no interviene en la cifra.
  3. Si no, generación con IA (generador.py) guiada por los ejemplos
     certificados más parecidos, validación del árbol SQL (validador.py) y
     una corrección automática si la validación o la base la rechazan.
  4. Ejecución SIEMPRE con la cuenta de solo lectura y la institución fijada en
     SESSION_CONTEXT (core/db.py).
  5. Respuesta: resumen determinista, visualización sugerida, cédulas
     enmascaradas y SQL visible solo para el rol de administración de TI.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Callable

from core import db
from core.privacidad import enmascarar_para_pantalla
from nl2sql import enrutador, generador, redactor, validador
from nl2sql.guardarrailes import clasificar
from nl2sql.proveedores import SinProveedores

Lector = Callable[[str, str, tuple], tuple[list[str], list[list]]]

SUGERENCIAS = {
    'Riesgo de abandono': ['¿Cuántos estudiantes hay en cada nivel de riesgo?', 'Muéstrame los 10 estudiantes con mayor riesgo',
                           '¿Qué carreras tienen más estudiantes en riesgo?', '¿Cuáles son las razones más frecuentes del riesgo?'],
    'Matrícula y trayectoria': ['¿Cuántos estudiantes tienen matrícula vigente?', '¿Cuál es la tasa de abandono de cada carrera?',
                                '¿Cuántos estudiantes abandonaron cada año?'],
    'Carreras y referentes': ['¿Qué carreras necesitan atención prioritaria?', '¿Cómo estamos frente a otras universidades?'],
    'Confianza en el modelo': ['¿Qué tan confiable es el modelo?', '¿Qué modelos se compararon?'],
    'Seguimiento': ['¿Cuántos estudiantes en riesgo alto ya tienen seguimiento?'],
}


@dataclass
class Respuesta:
    id: str
    pregunta: str
    origen: str                      # CERTIFICADA / GENERADA_IA / BARRERA / SIN_RESPUESTA / ERROR
    intencion: str
    titulo: str = ''
    explicacion: str = ''
    columnas: list[str] = field(default_factory=list)
    filas: list[list] = field(default_factory=list)
    visualizacion: str = 'texto'
    metrica_id: str | None = None
    sql: str | None = None
    advertencias: list[str] = field(default_factory=list)
    proveedor: str | None = None
    tiempo_ms: int = 0
    sugerencias: dict | None = None

    def a_dict(self) -> dict:
        return asdict(self)


# ── Caché pequeña: entidades por institución y resultados recientes ─────
_cache_entidades: dict[str, tuple[float, list[str], list[str]]] = {}
_resultados: dict[str, tuple[float, str, str, list[str], list[list]]] = {}
_candado = threading.Lock()


def _entidades_institucion(institucion: str, lector: Lector) -> tuple[list[str], list[str]]:
    ahora = time.time()
    with _candado:
        guardado = _cache_entidades.get(institucion)
    if guardado and ahora - guardado[0] < 600:
        return guardado[1], guardado[2]
    _, filas = lector('SELECT DISTINCT carrera, facultad_nombre FROM VIS_ALUMNO', institucion, ())
    carreras = sorted({f[0] for f in filas if f[0]})
    facultades = sorted({f[1] for f in filas if f[1]})
    with _candado:
        _cache_entidades[institucion] = (ahora, carreras, facultades)
    return carreras, facultades


def _guardar_resultado(r: Respuesta, institucion: str) -> None:
    with _candado:
        ahora = time.time()
        for k in [k for k, v in _resultados.items() if ahora - v[0] > 3600]:
            _resultados.pop(k, None)
        _resultados[r.id] = (ahora, institucion, r.pregunta, r.columnas, r.filas)


def resultado_guardado(id_respuesta: str, institucion: str) -> tuple[str, list[str], list[list]] | None:
    """Resultado de una respuesta reciente de la MISMA institución (para interpretarlo o exportarlo)."""
    with _candado:
        v = _resultados.get(id_respuesta)
    if not v or v[1] != institucion:
        return None
    return v[2], v[3], v[4]


def _parametros_certificada(metrica: dict, e: enrutador.Entidades) -> tuple[str, tuple]:
    sql, valores = metrica['sql'], []
    for nombre in metrica['parametros']:
        valor = e.valor(nombre)
        if nombre == 'riesgo':
            lista = valor or ['ALTO']
            sql = sql.replace('(?*)', '(' + ', '.join('?' for _ in lista) + ')', 1)
            valores.extend(lista)
        else:
            valores.append(valor)
    return sql, tuple(valores)


def responder(pregunta: str, institucion: str, instituciones_conocidas: list[str], ver_sql: bool = False,
              historial: list[dict] | None = None, lector: Lector | None = None) -> Respuesta:
    """Responde una pregunta en lenguaje natural sobre la institución activa."""
    lector = lector or db.leer
    inicio = time.time()
    r = Respuesta(id=uuid.uuid4().hex[:12], pregunta=(pregunta or '').strip()[:500], origen='BARRERA', intencion='')

    intencion = clasificar(r.pregunta, institucion, instituciones_conocidas)
    r.intencion = intencion.tipo
    if intencion.tipo != 'CONSULTA':
        r.explicacion = intencion.mensaje or 'Estas son algunas preguntas que puede hacer:'
        if intencion.tipo in ('AYUDA', 'SALUDO', 'FUERA_DE_ALCANCE'):
            r.sugerencias = SUGERENCIAS
        r.tiempo_ms = int((time.time() - inicio) * 1000)
        return r

    try:
        carreras, facultades = _entidades_institucion(institucion, lector)
        entidades = enrutador.extraer_entidades(r.pregunta, carreras, facultades)
        elegida = enrutador.elegir(entidades)
        if elegida:
            sql, parametros = _parametros_certificada(elegida.metrica, entidades)
            columnas, filas = lector(sql, institucion, parametros)
            r.origen, r.metrica_id, r.titulo = 'CERTIFICADA', elegida.metrica['id'], elegida.metrica['titulo']
            if entidades.carrera and 'carrera' in elegida.metrica['parametros']:
                r.titulo += f' · {entidades.carrera}'
            sugerida, r.sql = elegida.metrica['visualizacion'], sql
        else:
            ejemplos = enrutador.ejemplos_guiados(entidades)
            gen = generador.generar(r.pregunta, ejemplos, historial)
            r.proveedor = f'{gen.proveedor} ({gen.modelo})'
            if not gen.sql:
                r.origen, r.explicacion = 'SIN_RESPUESTA', gen.nota or 'No encontré cómo responder esa pregunta con los datos disponibles.'
                r.sugerencias = SUGERENCIAS
                r.tiempo_ms = int((time.time() - inicio) * 1000)
                return r
            columnas, filas, sql = _ejecutar_generada(r, gen, ejemplos, institucion, lector)
            r.origen, r.titulo, sugerida = 'GENERADA_IA', gen.titulo or 'Resultado de la consulta', gen.visualizacion
            if gen.nota:
                r.advertencias.append(gen.nota)
            r.sql = sql
    except SinProveedores:
        r.origen = 'SIN_RESPUESTA'
        r.explicacion = ('Esa pregunta no está entre las métricas certificadas y los proveedores de IA no están '
                         'disponibles en este momento. Pruebe con una de las preguntas sugeridas.')
        r.sugerencias = SUGERENCIAS
        r.tiempo_ms = int((time.time() - inicio) * 1000)
        return r
    except db.ErrorBaseDatos as exc:
        r.origen, r.explicacion = 'ERROR', str(exc)
        r.tiempo_ms = int((time.time() - inicio) * 1000)
        return r

    r.columnas = columnas
    r.filas = enmascarar_para_pantalla(columnas, filas)
    r.visualizacion = redactor.elegir_visualizacion(columnas, filas, sugerida)
    r.explicacion = redactor.resumen(r.titulo, columnas, filas)
    if len(filas) >= validador.LIMITE_FILAS:
        r.advertencias.append(f'Se muestran las primeras {validador.LIMITE_FILAS} filas.')
    if not ver_sql:
        r.sql = None
    _guardar_resultado(r, institucion)
    r.tiempo_ms = int((time.time() - inicio) * 1000)
    return r


def _ejecutar_generada(r: Respuesta, gen: generador.ResultadoGeneracion, ejemplos, institucion: str,
                       lector: Lector) -> tuple[list[str], list[list], str]:
    """Valida y ejecuta el SQL generado, con una sola corrección automática si falla."""
    for intento in range(2):
        v = validador.validar(gen.sql)
        error = '; '.join(v.problemas) if not v.valido else None
        if v.valido:
            try:
                columnas, filas = lector(v.sql, institucion, ())
                if intento:
                    r.advertencias.append('La consulta se corrigió automáticamente una vez.')
                return columnas, filas, v.sql
            except db.ErrorBaseDatos as exc:
                error = str(exc)
        if intento == 0:
            gen = generador.corregir(r.pregunta, gen, error, ejemplos)
            if not gen.sql:
                break
        else:
            raise db.ErrorBaseDatos(f'No se pudo construir una consulta válida: {error}')
    raise db.ErrorBaseDatos('No se pudo construir una consulta válida para esa pregunta.')
