"""
Gestor de sesiones aisladas por usuario autenticado.

Mantiene en memoria el conector SQL, el cliente de IA y el contexto de cada
usuario para evitar colisiones de datos entre usuarios; lo usan main.py y
api/routes_query.py. El estado no sensible (empresa activa, esquema
sincronizado) se refleja en session_state_store.py para sobrevivir a un
reinicio; los recursos vivos (connector, client) y los secretos (conn_str,
api_key) nunca se persisten.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from core.session_state_store import get_state, save_state, clear_state

logger = logging.getLogger(__name__)


class UserSession:
    """Contexto privado de un usuario autenticado.

    Incluye el conector SQL, el cliente de IA y los metadatos de rol y módulos.
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
        # Caché por base o empresa activa para no mezclar esquemas entre dominios.
        self.schema_cache: Dict[str, dict] = {}
        # Caché del esquema completo por empresa (schema_dict, schema_text y
        # semantic_relations). Persiste entre cambios de empresa en la misma
        # sesión para evitar resincronizaciones costosas. La clave es el código
        # de empresa (p. ej., "AGRINAG"); cada empresa tiene su espacio aislado.
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
        """Actualiza los recursos de la sesión tras una conexión exitosa.

        Reinicia schema_cache con el esquema de la base de contexto. Si no se
        pasa api_key, la toma del cliente de IA cuando este la expone.
        """
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
        """Devuelve una instantánea serializable del estado no sensible de la sesión.

        Excluye a propósito connector, client, conn_str y api_key (recursos
        vivos y secretos), history_context (no se llena) y schema_cache (se
        reconstruye desde el esquema de contexto).
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
        """Aplica una instantánea guardada previamente, sin tocar connector ni client."""
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
    """Registro en memoria de las sesiones activas.

    Está diseñado para migrar con facilidad a Redis u otro almacenamiento externo.
    """

    def __init__(self):
        # El almacén vive en la memoria del proceso actual; en un despliegue
        # horizontal debe migrarse a una persistencia distribuida.
        self._sessions: Dict[str, UserSession] = {}

    def get_session(self, user_id: str) -> Optional[UserSession]:
        """Recupera la sesión activa del usuario.

        Si el proceso se reinició y no hay nada en memoria, intenta restaurar
        el último estado guardado (empresa activa y esquema sincronizado). En
        ese caso connector y client quedan en None: el flujo normal de
        conexión automática (p. ej., /api/bi/pulse o volver a elegir la
        empresa) los reconstruye, igual que en una sesión nueva sin conector.

        Returns:
            La sesión en memoria o restaurada, o None si no hay estado guardado.
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
        """Crea o reemplaza la sesión del usuario tras un inicio de sesión exitoso."""
        new_session = UserSession(user_id, role, name, allowed_modules)
        self._sessions[user_id] = new_session
        logger.info("Sesion creada para usuario: %s [%s]", user_id, role)
        return new_session

    def persist(self, user_id: str) -> None:
        """Guarda la instantánea actual de la sesión (ver UserSession.to_state_dict)."""
        session = self._sessions.get(user_id)
        if session is None:
            return
        try:
            save_state(user_id, session.to_state_dict())
        except Exception as exc:
            logger.warning("[SESSION] No se pudo guardar estado de %s: %s", user_id, exc)

    def remove_session(self, user_id: str):
        """Elimina la sesión activa, libera los recursos en memoria y borra el estado guardado."""
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info("Sesion liberada: %s", user_id)
        try:
            clear_state(user_id)
        except Exception as exc:
            logger.warning("[SESSION] No se pudo borrar estado guardado de %s: %s", user_id, exc)


SESSION_STORE = SessionManager()
