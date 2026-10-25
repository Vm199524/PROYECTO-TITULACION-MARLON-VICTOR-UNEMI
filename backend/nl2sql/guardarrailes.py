# -*- coding: utf-8 -*-
"""
Barreras de intención antes de generar cualquier SQL.

Clasifica la pregunta en uno de estos casos y responde sin llamar al modelo
de lenguaje cuando no hace falta:

  - ESCRITURA: pide borrar, modificar, insertar o crear datos.
  - INYECCION: intenta cambiar las instrucciones del sistema, el contexto de
    sesión o ejecutar procedimientos.
  - OTRA_INSTITUCION: pide datos de una institución distinta a la activa.
  - TABLAS_FISICAS: pide leer tablas o bases que no son las vistas autorizadas.
  - SALUDO / AYUDA: conversación o pregunta sobre lo que el sistema puede hacer.
  - FUERA_DE_ALCANCE: temas ajenos a la gestión académica.
  - CONSULTA: todo lo demás, que sigue al enrutador y al generador.

Es la primera de cuatro barreras (intención, validador del árbol SQL, vistas
filtradas y cuenta de solo lectura); ninguna depende de las otras.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from nl2sql.enrutador import normalizar

_ESCRITURA = re.compile(
    r'\b(borra|borrar|borren|elimina|eliminar|eliminen|suprime|vacia|vaciar|actualiza|actualizar|modifica|modificar|'
    r'cambia (el|la|los|las) (promedio|nota|estado|asistencia|saldo|beca)|inserta|insertar|agrega un|agregar un|crea una? '
    r'(tabla|vista|base)|drop|truncate|delete|update|insert|alter|merge|grant|revoke|create)\b')
_INYECCION = re.compile(
    r'(ignora|olvida|omite|desactiva).{0,30}(instruccion|regla|restriccion|sistema)|system prompt|prompt del sistema|'
    r'\bexec\b|\bexecute\b|xp_?cmdshell|sp_?set_?session|session_?context|contexto de sesion|modo desarrollador|'
    r'jailbreak|actua como|eres ahora')
_TABLAS = re.compile(r'(\bfact_\w+|\bdim_\w+|\bhistorial_\w+|\balumnos_prueba\b|\bsys\.\w+|information_schema|'
                     r'\bdbo\.\w+|tabla fisica|tablas fisicas|base operativa|\bunemi_pruebas\.|\boulad_pruebas\b|'
                     r'\bmaster\.)')
_SALUDO = re.compile(r'^(hola|buenas|buenos dias|buenas tardes|buenas noches|gracias|muchas gracias|ok|listo|saludos)\b')
_AYUDA = re.compile(r'(que puedes hacer|que se te puede preguntar|que preguntas|como funcionas|ayuda|que sabes hacer|'
                    r'que informacion tienes|para que sirves)')
_DOMINIO = re.compile(
    r'(alumn|estudiant|matricul|carrera|facultad|abandon|desert|retir|riesgo|promedio|nota|asistencia|beca|saldo|mora|'
    r'graduad|egresad|segment|referente|modelo|prediccion|probabilidad|semestre|periodo|sede|modalidad|tasa|'
    r'institucion|universidad|seguimiento|intervencion|tutoria|aula virtual|evaluacion|credito|cohorte|roc|auc|'
    r'recall|precision|silhouette|confiab|docente|cupo|admision|ingreso|repit|titula)')


@dataclass(frozen=True)
class Intencion:
    tipo: str
    mensaje: str = ''

    @property
    def bloqueada(self) -> bool:
        return self.tipo in ('ESCRITURA', 'INYECCION', 'OTRA_INSTITUCION', 'TABLAS_FISICAS')


def clasificar(pregunta: str, institucion_activa: str, instituciones_conocidas: list[str]) -> Intencion:
    """Clasifica la intención de la pregunta (ver docstring del módulo)."""
    t = normalizar(pregunta)
    # Para detectar nombres técnicos se conservan guiones bajos y puntos (fact_matriculas, dbo.x).
    crudo = unicodedata.normalize('NFKD', pregunta or '').encode('ascii', 'ignore').decode().lower()
    t_codigos = re.sub(r'[^a-z0-9_.\s]', ' ', crudo)
    if not t:
        return Intencion('VACIA', 'Escriba una pregunta sobre los estudiantes, el riesgo de abandono o las carreras.')
    if _INYECCION.search(t) or _INYECCION.search(t_codigos):
        return Intencion('INYECCION', 'No puedo cambiar mis reglas ni el contexto de seguridad. Solo respondo consultas '
                                      'de lectura sobre la institución activa.')
    if _ESCRITURA.search(t):
        return Intencion('ESCRITURA', 'Solo puedo consultar información; no modifico ni borro datos. Las '
                                      'intervenciones de bienestar se registran desde la ficha del estudiante.')
    otras = [i for i in instituciones_conocidas if i.upper() != institucion_activa.upper()]
    for codigo in otras:
        variantes = {codigo.lower(), codigo.lower().replace('_', ' '), codigo.split('_')[0].lower()}
        if any(re.search(rf'\b{re.escape(v)}\b', t) for v in variantes if len(v) >= 4):
            return Intencion('OTRA_INSTITUCION', 'Solo puedo consultar la institución activa. Para ver otra, cámbiela '
                                                 'en el selector de institución (si su cuenta tiene acceso).')
    if _TABLAS.search(t_codigos) or _TABLAS.search(t):
        return Intencion('TABLAS_FISICAS', 'Las consultas se responden solo con las vistas autorizadas; no puedo leer '
                                           'tablas internas ni otras bases de datos.')
    if _SALUDO.search(t) and len(t.split()) <= 4:
        return Intencion('SALUDO', '¡Hola! Puedo responder preguntas sobre la matrícula, el riesgo de abandono, las '
                                   'carreras, los referentes externos y la confiabilidad del modelo.')
    if _AYUDA.search(t):
        return Intencion('AYUDA', '')
    if not _DOMINIO.search(t):
        return Intencion('FUERA_DE_ALCANCE', 'Esa pregunta está fuera de lo que puedo consultar. Puedo ayudarle con la '
                                             'matrícula, el riesgo de abandono, las carreras, los referentes externos, '
                                             'la confiabilidad del modelo y el seguimiento de bienestar.')
    return Intencion('CONSULTA')
