"""
core/session_manager.py - Gestor de sesiones aisladas por usuario.
Mantiene estado de conexion y contexto IA por identidad autenticada.
Evita colisiones de datos entre usuarios durante una misma ejecucion.

FASE 3 — C3: además del store en memoria, el estado NO sensible de cada
sesión (empresa activa, esquema ya sincronizado) se refleja en
core/session_state_store.py para sobrevivir un reinicio del proceso backend.
connector/client (recursos vivos) y conn_str/api_key (secretos) nunca se
persisten — ver el docstring de session_state_store.py para el porqué.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from core.session_state_store import get_state, save_state, clear_state

logger = logging.getLogger(__name__)

# Archivo: session_manager.py
# Rol: store en memoria de sesiones activas por usuario autenticado.
# Recibe desde: backend/main.py y backend/api/routes_query.py.
# Se conecta con: el conector SQL y el cliente IA asignados al login actual.
# Responsabilidades: crear sesion, guardar contexto y aislar usuarios.


class UserSession:
    """
    Representa el contexto privado de un usuario autenticado.
    Incluye conector SQL, cliente IA y metadatos de modulo/rol.
    """

    def __init__(self, user_id: str, role: str, name: str, allowed_modules: list):
        self.user_id = user_id
        self.role = role
        self.name = name
        self.allowed_modules = allowed_modules

        self.connector = None
        self.client = None
        self.schema_dict = {}
        self.schema_text = ""
        self.master_schema_text = ""
        self.semantic_relations = ""
        # Cache por base/empresa activa para evitar mezclar esquemas entre dominios.
        self.schema_cache: Dict[str, dict] = {}
        # Cache de esquema COMPLETO por empresa (schema_dict + schema_text + semantic_relations).
        # Persiste entre cambios de empresa en la misma sesión para evitar re-sync costosos.
        # Clave = código de empresa (ej: "AGRINAG"). Cada empresa tiene su propio espacio aislado.
        self.full_schema_cache: Dict[str, dict] = {}
        self.context_db = ""
        self.conn_str = ""
        self.api_key = ""
        self.history_context = []

    def update_connection(
        self,
        connector,
        client,
        schema_dict = None,
        schema_text = "",
        context_db = "",
        conn_str = "",
        semantic_relations: str = "",
        api_key: str = "",
    ):
        """Actualiza recursos de la sesion tras un connect exitoso."""
        self.connector = connector
        self.client = client
        self.schema_dict = schema_dict
        self.schema_text = schema_text
        self.semantic_relations = semantic_relations or ""
        self.context_db = context_db
        self.conn_str = conn_str
        if api_key:
            self.api_key = api_key
        elif client and getattr(client, "_api_key", None):
            self.api_key = client._api_key
        self.schema_cache = {}
        context_key = str(context_db or "").strip().upper()
        if context_key and isinstance(schema_dict, dict) and schema_dict:
            self.schema_cache[context_key] = schema_dict

    def to_state_dict(self) -> dict:
        """
        Snapshot serializable del estado NO sensible de la sesión.
        Deliberadamente excluye: connector, client, conn_str, api_key,
        history_context (nunca se llenó, no vale la pena persistir), y
        schema_cache (derivable de nuevo desde full_schema_cache).
        """
        return {
            "role": self.role,
            "name": self.name,
            "allowed_modules": self.allowed_modules,
            "context_db": self.context_db,
            "schema_dict": self.schema_dict if isinstance(self.schema_dict, dict) else {},
            "schema_text": self.schema_text,
            "master_schema_text": self.master_schema_text,
            "semantic_relations": self.semantic_relations,
            "full_schema_cache": self.full_schema_cache if isinstance(self.full_schema_cache, dict) else {},
        }

    def restore_state_dict(self, state: dict) -> None:
        """Aplica un snapshot previamente guardado (no toca connector/client)."""
        if not isinstance(state, dict):
            return
        self.context_db = state.get("context_db", "") or ""
        schema_dict = state.get("schema_dict")
        self.schema_dict = schema_dict if isinstance(schema_dict, dict) else {}
        self.schema_text = state.get("schema_text", "") or ""
        self.master_schema_text = state.get("master_schema_text", "") or ""
        self.semantic_relations = state.get("semantic_relations", "") or ""
        full_cache = state.get("full_schema_cache")
        self.full_schema_cache = full_cache if isinstance(full_cache, dict) else {}
        context_key = str(self.context_db or "").strip().upper()
        if context_key and self.schema_dict:
            self.schema_cache[context_key] = self.schema_dict


class SessionManager:
    """
    Registro en memoria de sesiones activas.
    Diseñado para migrar facilmente a Redis o almacenamiento externo.
    """

    def __init__(self):
        # Este store vive en memoria del proceso actual.
        # En despliegue horizontal debe migrarse a persistencia distribuida.
        self._sessions: Dict[str, UserSession] = {}

    def get_session(self, user_id: str) -> Optional[UserSession]:
        """
        Recupera sesion activa por usuario. Si el proceso se reinició y no
        hay nada en memoria, intenta restaurar el último estado guardado
        (empresa activa + esquema ya sincronizado). connector/client quedan
        en None tras esta restauración — el flujo normal de auto-conexión
        (ej. /api/bi/pulse, o que el usuario reseleccione la empresa) se
        encarga de reconstruirlos, igual que ya hace hoy para una sesión
        nueva sin conector.
        """
        session = self._sessions.get(user_id)
        if session is not None:
            return session

        try:
            saved_state = get_state(user_id)
        except Exception as exc:
            logger.warning("[SESSION] No se pudo leer estado guardado de %s: %s", user_id, exc)
            saved_state = None

        if not saved_state:
            return None

        restored = UserSession(
            user_id,
            saved_state.get("role", "ADMINISTRADOR"),
            saved_state.get("name", user_id),
            saved_state.get("allowed_modules", []),
        )
        restored.restore_state_dict(saved_state)
        self._sessions[user_id] = restored
        logger.info(
            "[SESSION] Sesion restaurada desde estado guardado para %s (empresa=%s, tras reinicio del backend)",
            user_id, restored.context_db,
        )
        return restored

    def create_session(self, user_id: str, role: str, name: str, allowed_modules: list) -> UserSession:
        """Crea o refresca sesion del usuario luego de login exitoso."""
        new_session = UserSession(user_id, role, name, allowed_modules)
        self._sessions[user_id] = new_session
        logger.info("Sesion creada para usuario: %s [%s]", user_id, role)
        return new_session

    def persist(self, user_id: str) -> None:
        """Guarda el snapshot actual de la sesión (ver UserSession.to_state_dict)."""
        session = self._sessions.get(user_id)
        if session is None:
            return
        try:
            save_state(user_id, session.to_state_dict())
        except Exception as exc:
            logger.warning("[SESSION] No se pudo guardar estado de %s: %s", user_id, exc)

    def remove_session(self, user_id: str):
        """Elimina sesion activa, libera recursos en memoria y borra el estado guardado."""
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info("Sesion liberada: %s", user_id)
        try:
            clear_state(user_id)
        except Exception as exc:
            logger.warning("[SESSION] No se pudo borrar estado guardado de %s: %s", user_id, exc)


SESSION_STORE = SessionManager()
