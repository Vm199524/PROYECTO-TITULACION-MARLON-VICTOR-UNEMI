"""
api/routes_sessions.py - Historial de sesiones de chat persistido en backend.
Antes el historial (savedSessions) solo vivia en localStorage del navegador:
el usuario lo perdia al cambiar de equipo, limpiar el navegador o usar modo
incognito. Este router expone lectura/escritura simple (todo el arreglo a la
vez, igual que ya hace el frontend con localStorage) respaldada por Redis con
fallback a JSON, aislada por usuario via el JWT.
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
    """Factory del router, para mantener el mismo patron que routes_query.py."""

    @router.get("/sessions")
    def list_sessions(current_user: dict = Depends(get_token_data)):
        user_id = current_user.get("sub")
        return {"sessions": get_sessions(user_id)}

    @router.put("/sessions")
    def replace_sessions(payload: SessionsPayload, current_user: dict = Depends(get_token_data)):
        user_id = current_user.get("sub")
        save_sessions(user_id, payload.sessions)
        return {"status": "ok", "count": min(len(payload.sessions), 20)}

    return router
