"""
core/session_state_store.py - Persistencia liviana del ESTADO de sesión
(no de los recursos vivos) para sobrevivir un reinicio del backend.

Sigue el mismo patrón híbrido que core/session_history_store.py: Redis como
vía principal, con fallback a un archivo JSON local cuando Redis no está
disponible. Así, aunque hoy el sistema corre en una sola instancia (sin
Redis obligatorio), el reinicio del proceso backend ya no obliga al usuario
a volver a seleccionar la empresa desde cero: el contexto (empresa activa,
esquema ya sincronizado) se restaura solo.

IMPORTANTE — qué NO se persiste aquí, a propósito:
    - conn_str: puede contener credenciales SQL en texto plano (PWD=...).
    - api_key: llave del proveedor de IA.
Ninguno de los dos se escribe a Redis ni a disco. Al reconectar tras un
reinicio, el conector y el cliente IA se reconstruyen desde cero (mismo
patrón que ya usa /api/bi/pulse: build_connection_string(..., windows_auth=True)
+ variable de entorno DEEPSEEK_API_KEY), nunca reutilizando un secreto guardado.
"""
from __future__ import annotations

import json
import pathlib
from typing import Optional

from config import CACHE_DIR
from cache.redis_manager import REDIS_STORE

STATE_FILE = CACHE_DIR / "session_state.json"

# Estado de sesión: se refresca en cada login/cambio de empresa, así que un
# TTL corto-a-mediano es suficiente (evita acumular sesiones de usuarios que
# ya no vuelven). 24 horas cubre sobra una jornada de trabajo con margen.
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
