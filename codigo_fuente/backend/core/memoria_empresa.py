"""
memoria_empresa.py — Memoria de largo plazo de VicMar Data AI, por empresa.

PROBLEMA QUE RESUELVE
---------------------
Hasta ahora el sistema no recordaba NADA entre conversaciones. Al usuario le
decia "Entendido, he registrado en la memoria..." y no se escribia una sola
linea en ningun lado: era texto generado por el modelo, no una accion. Al
abrir un chat nuevo el contexto era cero, porque el frontend solo envia los
ultimos 4 mensajes de la conversacion ABIERTA (`chatHistory.slice(-4)` en
App.jsx). Resultado: la misma correccion habia que repetirla cada vez.

Lo unico persistente que existia era:
  · `cache/semantic_query_cache.json` — pregunta exacta -> SQL. Repeticion
    literal, no aprendizaje: cambia una palabra y ya no aplica.
  · `knowledge/consolidated_patterns.json` — nombres de tablas frecuentes.
  · `cache/session_history.json` — archivo de conversaciones para el panel
    lateral; el motor nunca lo lee.

QUE GUARDA ESTE MODULO
----------------------
Reglas de negocio en lenguaje natural, cortas, que la IA debe tener presentes
al responder sobre UNA empresa concreta. Por ejemplo, para MONT:

    "Al presentar alumnos por curso, advertir que 5 alumnos no se contabilizan
     porque estan en estado 'sin curso asignado' (1.033 con curso + 5 = 1.038)."

Esas reglas se inyectan en el prompt de TODAS las consultas posteriores de esa
empresa, en cualquier chat, tambien despues de reiniciar el backend.

AISLAMIENTO POR EMPRESA (NO NEGOCIABLE)
---------------------------------------
Cada regla vive bajo el codigo de empresa y jamas se sirve a otra. Este
producto ya sufrio una fuga de datos entre empresas por compartir un cache
con clave global (incidente de fuga de datos entre empresas del 27/07/2026); una memoria mal aislada
seria la misma falla con otro nombre. `bloque_para_prompt("AGGO")` no puede
devolver una sola palabra aprendida en MONT.

TRAZABILIDAD
------------
Cada regla guarda de donde salio (`origen`), la pregunta que la motivo
(`evidencia`) y cuando se creo. Como el aprendizaje es automatico, esto es lo
que permite auditar despues que aprendio el sistema y borrar lo que este mal:
una regla incorrecta que nadie puede ver ni quitar contamina en silencio todas
las respuestas futuras de esa empresa.
"""

from __future__ import annotations

import json
import re
import threading
import unicodedata
import uuid
from datetime import datetime, timezone

from config import CACHE_DIR

MEMORIA_FILE = CACHE_DIR / "memoria_empresa.json"

# Tope de reglas por empresa. Existe por dos razones: el bloque se inyecta en
# CADA prompt (mas reglas = mas tokens en cada consulta) y una memoria sin
# limite acaba siendo un vertedero donde lo util se pierde entre lo anecdotico.
MAX_REGLAS_POR_EMPRESA = 40

# Tope de caracteres de una regla. Lo que se inyecta al prompt tiene que ser
# una instruccion, no un ensayo.
MAX_LARGO_REGLA = 400

_LOCK = threading.Lock()


# ─── Persistencia ───────────────────────────────────────────────────────────


def _leer() -> dict:
    if not MEMORIA_FILE.exists():
        return {}
    try:
        with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except Exception:
        # Un JSON corrupto no puede tumbar una consulta: sin memoria se
        # responde igual que antes de que este modulo existiera.
        return {}


def _escribir(datos: dict) -> None:
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _clave_empresa(empresa: str | None) -> str:
    return str(empresa or "").strip().upper()


def _ahora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ─── Normalizacion y deduplicacion ──────────────────────────────────────────


def _normalizar(texto: str) -> str:
    """Minusculas, sin tildes ni puntuacion. Solo para comparar reglas."""
    txt = str(texto or "").lower()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    txt = re.sub(r"[^a-z0-9ñ\s]", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _es_duplicada(texto_nuevo: str, reglas: list[dict]) -> dict | None:
    """
    Devuelve la regla existente equivalente, si la hay.

    La comparacion es por solapamiento de palabras y no por igualdad exacta:
    el extractor es un modelo de lenguaje y redacta la misma regla distinto
    cada vez ("faltan 5 alumnos sin curso" / "5 alumnos no se cuentan por no
    tener curso asignado"). Sin esto, repetir la correccion tres veces mete
    tres reglas casi identicas en el prompt.
    """
    nuevas = set(_normalizar(texto_nuevo).split())
    if not nuevas:
        return None
    for regla in reglas:
        viejas = set(_normalizar(regla.get("texto", "")).split())
        if not viejas:
            continue
        comunes = nuevas & viejas
        solapamiento = len(comunes) / max(len(nuevas), len(viejas))
        if solapamiento >= 0.7:
            return regla
    return None


# ─── API publica ────────────────────────────────────────────────────────────


def reglas_de(empresa: str | None, solo_activas: bool = True) -> list[dict]:
    """Reglas aprendidas de UNA empresa. Nunca mezcla empresas."""
    clave = _clave_empresa(empresa)
    if not clave:
        return []
    reglas = _leer().get(clave, {}).get("reglas", [])
    if not isinstance(reglas, list):
        return []
    if solo_activas:
        return [r for r in reglas if r.get("activa", True)]
    return list(reglas)


def recordar(
    empresa: str | None,
    texto: str,
    *,
    origen: str = "automatico",
    evidencia: str = "",
    tema: str = "",
) -> dict | None:
    """
    Guarda una regla para esa empresa y la devuelve. None si no se guardo.

    Si ya existe una regla equivalente no se duplica: se refresca su marca de
    tiempo y se suma un refuerzo, lo que sirve para saber que esa correccion
    se repitio y por tanto importa.
    """
    clave = _clave_empresa(empresa)
    texto_limpio = " ".join(str(texto or "").split())[:MAX_LARGO_REGLA]
    if not clave or len(texto_limpio) < 10:
        return None

    with _LOCK:
        datos = _leer()
        bloque = datos.setdefault(clave, {"empresa": clave, "reglas": []})
        reglas = bloque.setdefault("reglas", [])

        existente = _es_duplicada(texto_limpio, reglas)
        if existente:
            existente["refuerzos"] = int(existente.get("refuerzos", 1)) + 1
            existente["actualizada"] = _ahora()
            existente["activa"] = True
            _escribir(datos)
            return existente

        regla = {
            "id": uuid.uuid4().hex[:12],
            "texto": texto_limpio,
            "tema": str(tema or "").strip().lower(),
            "origen": str(origen or "automatico"),
            "evidencia": " ".join(str(evidencia or "").split())[:300],
            "creada": _ahora(),
            "actualizada": _ahora(),
            "refuerzos": 1,
            "activa": True,
        }
        reglas.append(regla)

        # Si se pasa del tope, se descarta lo mas antiguo con menos refuerzos:
        # una regla que el usuario ha reforzado varias veces vale mas que una
        # que se aprendio una vez y nunca volvio a aparecer.
        if len(reglas) > MAX_REGLAS_POR_EMPRESA:
            reglas.sort(key=lambda r: (int(r.get("refuerzos", 1)), r.get("actualizada", "")))
            del reglas[: len(reglas) - MAX_REGLAS_POR_EMPRESA]

        _escribir(datos)
        return regla


def olvidar(empresa: str | None, regla_id: str) -> bool:
    """Elimina una regla concreta. True si existia."""
    clave = _clave_empresa(empresa)
    if not clave or not regla_id:
        return False
    with _LOCK:
        datos = _leer()
        reglas = datos.get(clave, {}).get("reglas", [])
        restantes = [r for r in reglas if r.get("id") != regla_id]
        if len(restantes) == len(reglas):
            return False
        datos[clave]["reglas"] = restantes
        _escribir(datos)
        return True


def olvidar_todo(empresa: str | None) -> int:
    """Borra la memoria completa de una empresa. Devuelve cuantas reglas cayeron."""
    clave = _clave_empresa(empresa)
    if not clave:
        return 0
    with _LOCK:
        datos = _leer()
        cuantas = len(datos.get(clave, {}).get("reglas", []))
        if clave in datos:
            del datos[clave]
            _escribir(datos)
        return cuantas


def bloque_para_prompt(empresa: str | None, limite: int = 15) -> str:
    """
    Fragmento que se inyecta en el SYSTEM_PROMPT del motor.

    Devuelve cadena vacia cuando no hay nada aprendido, para que el prompt
    quede exactamente igual que antes de que existiera la memoria.

    Las reglas mas reforzadas van primero: si hay que recortar por el limite,
    se conserva lo que el usuario ha tenido que corregir mas veces.
    """
    reglas = reglas_de(empresa)
    if not reglas:
        return ""

    reglas.sort(
        key=lambda r: (int(r.get("refuerzos", 1)), r.get("actualizada", "")),
        reverse=True,
    )
    lineas = [f"- {r.get('texto', '').strip()}" for r in reglas[:limite] if r.get("texto")]
    if not lineas:
        return ""

    nombre = _clave_empresa(empresa)
    return (
        f"🧠 MEMORIA APRENDIDA DE {nombre} (correcciones y precisiones de conversaciones anteriores).\n"
        "Aplicalas cuando la consulta actual las toque; si ninguna aplica, ignoralas en silencio.\n"
        "Nunca las menciones como 'memoria' ni expliques que las estas usando: incorpora el dato\n"
        "en la respuesta con naturalidad.\n"
        + "\n".join(lineas)
    )
