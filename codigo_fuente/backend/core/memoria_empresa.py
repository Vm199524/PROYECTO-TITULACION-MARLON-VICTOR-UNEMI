"""
Memoria de largo plazo por empresa.

Guarda reglas de negocio cortas en lenguaje natural (p. ej., «advertir que 5
alumnos no se cuentan por no tener curso asignado») y las inyecta en el prompt
de todas las consultas posteriores de esa empresa, en cualquier chat y tras
reiniciar el backend. Cada regla vive bajo el código de su empresa y nunca se
sirve a otra: una memoria mal aislada sería una fuga de datos entre empresas.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
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
# cada prompt (más reglas son más tokens por consulta) y una memoria sin
# límite termina mezclando lo útil con lo anecdótico.
MAX_REGLAS_POR_EMPRESA = 40

# Tope de caracteres de una regla: lo que se inyecta al prompt debe ser una
# instrucción, no un ensayo.
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
        # responde con el prompt base.
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


# ─── Normalización y deduplicación ──────────────────────────────────────────


def _normalizar(texto: str) -> str:
    """Pasa el texto a minúsculas sin tildes ni puntuación; solo se usa para comparar reglas."""
    txt = str(texto or "").lower()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    txt = re.sub(r"[^a-z0-9ñ\s]", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _es_duplicada(texto_nuevo: str, reglas: list[dict]) -> dict | None:
    """Devuelve la regla existente equivalente, si la hay.

    La comparación es por solapamiento de palabras (70 % o más) y no por
    igualdad exacta: el extractor es un modelo de lenguaje y redacta la misma
    regla de forma distinta cada vez («faltan 5 alumnos sin curso» frente a
    «5 alumnos no se cuentan por no tener curso asignado»). Sin esto, repetir
    una corrección tres veces metería tres reglas casi idénticas en el prompt.
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


# ─── API pública ────────────────────────────────────────────────────────────


def reglas_de(empresa: str | None, solo_activas: bool = True) -> list[dict]:
    """Devuelve las reglas aprendidas de una sola empresa; nunca mezcla empresas."""
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
    """Guarda una regla para la empresa y la devuelve; None si no se guardó.

    Si ya existe una regla equivalente no se duplica: se refresca su marca de
    tiempo y se suma un refuerzo, lo que indica que esa corrección se repitió
    y por tanto importa.

    Cada regla guarda su origen, la pregunta que la motivó (`evidencia`) y su
    fecha. Como el aprendizaje es automático, eso permite auditar lo aprendido
    y borrar lo incorrecto antes de que contamine las respuestas futuras.
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

        # Si se pasa del tope, se descarta lo más antiguo con menos refuerzos:
        # una regla reforzada varias veces vale más que una que se aprendió
        # una vez y no volvió a aparecer.
        if len(reglas) > MAX_REGLAS_POR_EMPRESA:
            reglas.sort(key=lambda r: (int(r.get("refuerzos", 1)), r.get("actualizada", "")))
            del reglas[: len(reglas) - MAX_REGLAS_POR_EMPRESA]

        _escribir(datos)
        return regla


def olvidar(empresa: str | None, regla_id: str) -> bool:
    """Elimina una regla concreta; devuelve True si existía."""
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
    """Borra la memoria completa de una empresa y devuelve cuántas reglas se eliminaron."""
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
    """Arma el fragmento de memoria que se inyecta en el SYSTEM_PROMPT del motor.

    Devuelve una cadena vacía cuando no hay nada aprendido, para que el prompt
    quede igual al prompt base.

    Las reglas más reforzadas van primero: si hay que recortar por `limite`,
    se conserva lo que el usuario ha tenido que corregir más veces.
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
