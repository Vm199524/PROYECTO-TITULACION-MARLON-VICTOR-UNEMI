"""
Historial de sesiones de chat guardado en el backend.

Expone la lectura y el reemplazo del arreglo completo de sesiones guardadas de
cada usuario (savedSessions), aislado por el JWT y respaldado por Redis con
respaldo en JSON (core/session_history_store.py). Guardarlo en el servidor evita
que el usuario pierda el historial al cambiar de equipo, limpiar el navegador o
usar modo incógnito, lo que ocurre si solo vive en el localStorage.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.session_history_store import get_sessions, save_sessions
from security import get_token_data

router = APIRouter()


class SessionsPayload(BaseModel):
    """Arreglo completo de sesiones guardadas de un usuario."""

    sessions: list = Field(default_factory=list)


def get_sessions_router() -> APIRouter:
    """Registra las rutas /sessions y devuelve el router (mismo patrón de fábrica que routes_query.py)."""

    @router.get("/sessions")
    def list_sessions(current_user: dict = Depends(get_token_data)):
        """Devuelve las sesiones guardadas del usuario autenticado."""
        user_id = current_user.get("sub")
        return {"sessions": get_sessions(user_id)}

    @router.put("/sessions")
    def replace_sessions(payload: SessionsPayload, current_user: dict = Depends(get_token_data)):
        """Reemplaza todas las sesiones guardadas del usuario autenticado.

        Returns:
            Estado y cantidad guardada; el almacén conserva como máximo 20 sesiones.
        """
        user_id = current_user.get("sub")
        save_sessions(user_id, payload.sessions)
        return {"status": "ok", "count": min(len(payload.sessions), 20)}

    return router
