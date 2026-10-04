"""
aprendizaje.py — Extraccion automatica de reglas de negocio desde el chat.

QUE HACE
--------
Despues de responder, mira la conversacion y decide por su cuenta si en ella
quedo una regla que merezca recordarse para futuras consultas de esa empresa.
Si la hay, la escribe en `core/memoria_empresa.py`. El usuario no tiene que
pedir nada: no existe un comando "graba en memoria".

POR QUE NO SE ANALIZA CADA CONSULTA
-----------------------------------
La extraccion cuesta una llamada al modelo. Hacerla en las miles de consultas
rutinarias ("total de ventas por meses") seria pagar por nada: de una consulta
respondida y aceptada no sale ninguna regla. Lo que si produce reglas es el
momento en que el usuario CORRIGE, ACLARA o pide mas precision — ahi es donde
esta el conocimiento que el sistema no tenia.

`hay_senal_de_aprendizaje()` reconoce ese momento por como escribe el usuario.
Sigue siendo automatico: la senal es la forma del mensaje, no una orden.

POR QUE CORRE EN SEGUNDO PLANO
------------------------------
El usuario ya tiene su respuesta en pantalla. Hacerle esperar una llamada
extra al modelo para guardar una nota seria cambiar latencia visible por
trabajo invisible. Si la extraccion falla, la consulta ya fue respondida y no
se entera nadie: la memoria es una mejora, nunca un punto de fallo.

RIESGO CONOCIDO
---------------
Al aprender solo, el sistema puede grabar como verdad una deduccion
equivocada de la IA y aplicarla despues a todas las consultas de esa empresa.
Por eso:
  · Solo se aprende de lo que dijo el USUARIO, nunca de una conclusion que la
    IA saco por si misma. Una IA que aprende de sus propias afirmaciones
    termina reforzando sus errores.
  · Cada regla queda con `origen` y `evidencia` para poder auditarla, y se
    puede borrar desde /api/memoria.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import unicodedata

from core.memoria_empresa import recordar

logger = logging.getLogger(__name__)


# ─── 1. Deteccion del momento en que hay algo que aprender ──────────────────

# Formas en que una persona corrige, precisa o instruye a la herramienta.
# Reconocerlas NO es "esperar una orden": es identificar donde aparece
# conocimiento nuevo. Una consulta normal no lleva ninguna de estas marcas.
_SENALES = (
    # Correccion directa
    r"\bno es (?:correcto|asi|exacto)\b", r"\bestas? mal\b", r"\bte equivocas\b",
    r"\ben realidad\b", r"\bincorrecto\b", r"\berror\b",
    # Falta de precision en la respuesta
    r"\bfaltan?\b", r"\bfalto\b", r"\bno me diste\b", r"\bno diste\b",
    r"\bmas detall", r"\bmas precis", r"\bbien detallad", r"\bnuevamente\b",
    r"\bno cuadra\b", r"\bno coincide\b", r"\bpor que (?:da|sale|aparece)\b",
    # Instruccion sobre como responder en adelante
    r"\bdeber[ií]as?\b", r"\bdebes\b", r"\btienes que\b", r"\ba la proxima\b",
    r"\bde ahora en adelante\b", r"\bsiempre que\b", r"\bcada vez que\b",
    r"\bgraba\b", r"\bguarda\b", r"\brecuerda\b", r"\bmemoriza\b", r"\banota\b",
    r"\bten en cuenta\b", r"\bconsidera\b",
    # Explicacion que aporta el usuario sobre sus propios datos
    r"\bporque (?:tienen|estan|se encuentran|son|no)\b",
    r"\bse debe a\b", r"\bla razon es\b",
)

_RE_SENALES = re.compile("|".join(_SENALES))


def _normalizar(texto: str) -> str:
    txt = str(texto or "").lower()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    txt = re.sub(r"[^a-z0-9ñ\s]", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def hay_senal_de_aprendizaje(mensaje_usuario: str) -> bool:
    """True cuando el mensaje corrige, precisa o instruye — no una consulta normal."""
    texto = _normalizar(mensaje_usuario)
    if len(texto) < 12:
        return False
    return bool(_RE_SENALES.search(texto))


# ─── 2. Extraccion de la regla ──────────────────────────────────────────────

_PROMPT_EXTRACCION = """Eres el modulo de memoria de VicMar Data AI, una herramienta de Inteligencia de Negocios.

Analiza este fragmento de conversacion entre un usuario y el asistente, sobre la empresa {empresa}.

CONVERSACION RECIENTE:
{conversacion}

ULTIMO MENSAJE DEL USUARIO:
{mensaje}

Tu tarea: decidir si el USUARIO aporto un conocimiento de negocio DURADERO que el
asistente deba recordar para responder mejor en futuras consultas de {empresa}.

Aprende SOLO si se cumple todo esto:
- Lo aporta el usuario, no es una deduccion del asistente.
- Sigue siendo cierto la proxima semana (una regla, no el resultado de hoy).
- Es especifico y accionable al presentar una metrica o interpretar los datos.

NO aprendas:
- Consultas normales, saludos o preguntas sin correccion.
- Cifras puntuales que cambian con el tiempo ("este mes vendimos 40.000").
- Opiniones, quejas o frustracion sin contenido de negocio.
- Nada que el asistente haya concluido por si mismo.

Responde SOLO JSON valido:
{{
  "aprender": true|false,
  "regla": "Instruccion en una o dos frases, en imperativo, lista para que el asistente la siga. Vacio si aprender es false.",
  "tema": "palabra clave del area (alumnos, ventas, compras, nomina, inventario, contabilidad, general)"
}}"""


def _extraer_json(texto: str) -> dict | None:
    if not texto:
        return None
    limpio = str(texto).strip()
    limpio = re.sub(r"^```(?:json)?|```$", "", limpio, flags=re.MULTILINE).strip()
    inicio, fin = limpio.find("{"), limpio.rfind("}")
    if inicio == -1 or fin == -1 or fin <= inicio:
        return None
    try:
        parsed = json.loads(limpio[inicio : fin + 1])
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _formatear_conversacion(historial: list, limite: int = 6) -> str:
    """Convierte el historial que envia el frontend en texto plano."""
    lineas = []
    for item in list(historial or [])[-limite:]:
        if isinstance(item, dict):
            tipo, contenido = item.get("type", ""), item.get("content", "")
        else:
            tipo, contenido = getattr(item, "type", ""), getattr(item, "content", "")
        contenido = " ".join(str(contenido or "").split())[:600]
        if not contenido:
            continue
        quien = "USUARIO" if str(tipo).lower() in ("user", "usuario", "human") else "ASISTENTE"
        lineas.append(f"{quien}: {contenido}")
    return "\n".join(lineas) if lineas else "(sin historial previo)"


def _construir_llm():
    """
    Modelo para la extraccion: el barato (flash), no el experto.

    Se construye aqui en lugar de reutilizar el del motor porque
    `finalize_response` es el embudo de TODAS las respuestas, incluidas las que
    salen por caminos donde el cliente de IA todavia no existe (metrica
    certificada, cache). Depender de el habria dejado sin aprendizaje justo las
    correcciones que llegan despues de una metrica certificada. Instanciar
    ChatOpenAI no abre conexion, y esto corre dentro del hilo de aprendizaje,
    fuera del camino de la respuesta.
    """
    try:
        from langchain_openai import ChatOpenAI

        from config import DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            return None
        return ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0,
            max_retries=1,
            timeout=30,
        )
    except Exception as exc:
        logger.warning("[MEMORIA] No se pudo construir el modelo extractor: %s", exc)
        return None


def extraer_y_recordar(
    empresa: str,
    mensaje_usuario: str,
    historial: list,
    llm=None,
) -> dict | None:
    """
    Analiza la conversacion y guarda la regla si la hay. Devuelve la regla o None.

    `llm` se puede inyectar (los tests lo hacen con un doble); si no se pasa,
    se construye el modelo barato.
    """
    if not empresa:
        return None
    if llm is None:
        llm = _construir_llm()
    if llm is None:
        return None

    try:
        prompt = _PROMPT_EXTRACCION.format(
            empresa=empresa,
            conversacion=_formatear_conversacion(historial),
            mensaje=" ".join(str(mensaje_usuario or "").split())[:800],
        )
        respuesta = llm.invoke(prompt)
        crudo = getattr(respuesta, "content", respuesta)
        parsed = _extraer_json(str(crudo))
        if not parsed or not parsed.get("aprender"):
            return None

        regla_texto = str(parsed.get("regla") or "").strip()
        if len(regla_texto) < 10:
            return None

        guardada = recordar(
            empresa,
            regla_texto,
            origen="automatico",
            evidencia=mensaje_usuario,
            tema=str(parsed.get("tema") or ""),
        )
        if guardada:
            logger.info("[MEMORIA] %s aprendio: %s", empresa, regla_texto[:120])
        return guardada
    except Exception as exc:
        # La consulta del usuario ya fue respondida: que falle el aprendizaje
        # no puede afectarla de ninguna manera.
        logger.warning("[MEMORIA] No se pudo extraer regla para %s: %s", empresa, exc)
        return None


def aprender_en_segundo_plano(
    empresa: str, mensaje_usuario: str, historial: list, llm=None
) -> None:
    """
    Lanza la extraccion en un hilo aparte y vuelve de inmediato.

    El hilo es daemon: si el backend se apaga, no queda nada colgando
    impidiendo el cierre.
    """
    if not hay_senal_de_aprendizaje(mensaje_usuario):
        return
    try:
        hilo = threading.Thread(
            target=extraer_y_recordar,
            args=(empresa, mensaje_usuario, historial, llm),
            daemon=True,
            name=f"memoria-{empresa}",
        )
        hilo.start()
    except Exception as exc:
        logger.warning("[MEMORIA] No se pudo lanzar el aprendizaje: %s", exc)
