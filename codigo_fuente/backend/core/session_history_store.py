"""
Persistencia del historial de sesiones de chat.

Guarda por usuario la lista de conversaciones para que no se pierda al cambiar
de equipo o limpiar el navegador. Sigue el patrón híbrido de
cache/query_cache.py: Redis como vía principal (compartida entre instancias) y
un archivo JSON local como respaldo. El frontend mantiene localStorage como
caché sin conexión; este módulo es la fuente de verdad cuando hay conexión.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
import pathlib
from typing import Optional

from config import CACHE_DIR
from cache.redis_manager import REDIS_STORE

SESSIONS_FILE = CACHE_DIR / "session_history.json"

# Historial de chat: retención larga (90 días), no un caché de corta duración.
# Distinto del CACHE_TTL genérico (pensado para respuestas de consulta), por
# eso se pasa explícito en cada escritura a Redis.
SESSION_HISTORY_TTL = 60 * 60 * 24 * 90

MAX_SESSIONS_PER_USER = 20


def _key(user_id: str) -> str:
    return f"session_history::{user_id}"


def _load_json_store() -> dict:
    try:
        if SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_json_store(data: dict) -> None:
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_sessions(user_id: str) -> list:
    """Recupera la lista de sesiones guardadas de un usuario (vía Redis o JSON)."""
    if not user_id:
        return []

    if REDIS_STORE.ensure_connected():
        entry = REDIS_STORE.get(_key(user_id))
        if entry is not None:
            return entry if isinstance(entry, list) else []

    store = _load_json_store()
    entry = store.get(user_id)
    return entry if isinstance(entry, list) else []


def save_sessions(user_id: str, sessions: list) -> None:
    """Reemplaza la lista completa de sesiones de un usuario.

    Sigue el patrón del frontend, que reescribe el arreglo entero en cada
    cambio, y lo trunca a MAX_SESSIONS_PER_USER.
    """
    if not user_id:
        return

    clean_sessions = list(sessions or [])[:MAX_SESSIONS_PER_USER]

    if REDIS_STORE.ensure_connected():
        REDIS_STORE.set(_key(user_id), clean_sessions, ttl=SESSION_HISTORY_TTL)
    else:
        store = _load_json_store()
        store[user_id] = clean_sessions
        _save_json_store(store)
