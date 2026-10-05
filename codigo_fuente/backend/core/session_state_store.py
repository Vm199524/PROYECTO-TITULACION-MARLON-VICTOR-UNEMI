"""
Persistencia liviana del estado de sesión para sobrevivir a un reinicio del backend.

Guarda el contexto (empresa activa, esquema sincronizado), no los recursos
vivos, para que el usuario no tenga que volver a elegir la empresa. Sigue el
patrón híbrido de session_history_store.py: Redis como vía principal y un JSON
local como respaldo. Por diseño no persiste conn_str (puede llevar PWD=...) ni
api_key: al reconectar, el conector y el cliente de IA se reconstruyen con
build_connection_string(..., windows_auth=True) y DEEPSEEK_API_KEY del entorno.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
import pathlib
from typing import Optional

from config import CACHE_DIR
from cache.redis_manager import REDIS_STORE

STATE_FILE = CACHE_DIR / "session_state.json"

# El estado se refresca en cada inicio de sesión o cambio de empresa, así que
# basta un TTL corto o mediano que evite acumular sesiones de usuarios que no
# vuelven. 24 horas cubren una jornada de trabajo con margen.
SESSION_STATE_TTL = 60 * 60 * 24


def _key(user_id: str) -> str:
    return f"session_state::{user_id}"


def _load_json_store() -> dict:
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_json_store(data: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_state(user_id: str) -> Optional[dict]:
    """Recupera el último estado guardado de un usuario (vía Redis o JSON)."""
    if not user_id:
        return None

    if REDIS_STORE.ensure_connected():
        entry = REDIS_STORE.get(_key(user_id))
        if entry is not None:
            return entry if isinstance(entry, dict) else None

    store = _load_json_store()
    entry = store.get(user_id)
    return entry if isinstance(entry, dict) else None


def save_state(user_id: str, state: dict) -> None:
    """Reemplaza el estado guardado de un usuario."""
    if not user_id or not isinstance(state, dict):
        return

    if REDIS_STORE.ensure_connected():
        REDIS_STORE.set(_key(user_id), state, ttl=SESSION_STATE_TTL)
    else:
        store = _load_json_store()
        store[user_id] = state
        _save_json_store(store)


def clear_state(user_id: str) -> None:
    """Borra el estado guardado de un usuario (logout explícito)."""
    if not user_id:
        return

    if REDIS_STORE.ensure_connected():
        try:
            REDIS_STORE.delete(_key(user_id))
        except Exception:
            pass

    store = _load_json_store()
    if user_id in store:
        del store[user_id]
        _save_json_store(store)
