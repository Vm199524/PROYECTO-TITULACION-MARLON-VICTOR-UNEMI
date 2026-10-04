"""
api/routes_quantum_core.py - Endpoints de observabilidad y feedback de Quantum Core.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.mirror_manager import MirrorManager
from core.quantum_core_store import build_quantum_core_overview, record_feedback
from core.schema_resolver import resolve_schema_for_db
from core.session_manager import SESSION_STORE
from security import get_token_data

router = APIRouter()


class FeedbackRequest(BaseModel):
    query_id: str
    verdict: str
    note: str = ""


def _build_context_overview(session, target_db: str, allowed_modules: list = None) -> dict:
    mirror = MirrorManager(session.connector)
    schema = resolve_schema_for_db(session, target_db)
    snapshot = mirror.get_capability_snapshot(target_db, schema)
    metrics = snapshot.get("metrics", {})
    modules = snapshot.get("modules", ["GENERAL"])
    areas = snapshot.get("areas", [])

    # Filtro por módulos permitidos (rol del usuario): un CONTABILIDAD no debe
    # ver áreas/KPIs de un módulo que no tiene habilitado (ej. ACADEMICO en
    # una empresa con esquema académico como MONT). Con allowed_modules vacío
    # (ADMIN/GUEST sin restricción) no se filtra nada. El id de cada área es
    # la clave del módulo en minúsculas (academico → ACADEMICO).
    allowed = {str(m).strip().upper() for m in (allowed_modules or []) if m}
    if allowed:
        modules = [m for m in modules if str(m).strip().upper() in allowed]
        areas = [a for a in areas if str((a or {}).get("id") or "").strip().upper() in allowed]

    ready_areas = [area for area in areas if area.get("status") == "ready"]
    company_label = str(target_db or session.context_db or "ACTIVA").strip().upper()

    kpis = [
        {
            "id": "ready-domains",
            "label": "Dominios listos",
            "display_value": str(metrics.get("ready_domains", 0)),
            "icon": "trending-up",
            "hint": "Areas reales detectadas a partir del esquema activo y las vistas espejo.",
        },
        {
            "id": "virtual-views",
            "label": "Vistas virtuales",
            "display_value": str(metrics.get("virtual_view_count", 0)),
            "icon": "database",
            "hint": "Capas de negocio listas para consulta sobre la empresa/base activa.",
        },
        {
            "id": "entities",
            "label": "Entidades",
            "display_value": str(metrics.get("entities_count", 0)),
            "icon": "users",
            "hint": "Tablas o vistas fisicas detectadas en el origen conectado.",
        },
        {
            "id": "modules",
            "label": "Modulos",
            "display_value": str(len(modules)),
            "icon": "graduation-cap",
            "hint": "Bloques funcionales que VicMar Data AI puede recomendar con evidencia del esquema.",
        },
    ]

    return {
        "database": company_label,
        "profile": {
            "business_name": company_label,
            "modules": modules,
        },
        "summary": snapshot.get("summary", ""),
        "kpis": kpis,
        "areas": areas,
        "quick_questions": snapshot.get("quick_questions", []),
        "details": snapshot.get("details", []),
        "ready_area_count": len(ready_areas),
    }


@router.get("/quantum-core/overview")
async def quantum_core_overview(
    force_refresh: bool = Query(False),
    current_user: dict = Depends(get_token_data),
):
    user_id = current_user.get("sub")
    session = SESSION_STORE.get_session(user_id)
    return build_quantum_core_overview(session=session, force_refresh=force_refresh)


@router.get("/context-overview")
async def context_overview(
    target_db: str = Query(""),
    force_refresh: bool = Query(False),
    current_user: dict = Depends(get_token_data),
):
    _ = force_refresh
    user_id = current_user.get("sub")
    session = SESSION_STORE.get_session(user_id)
    if not session or not session.connector:
        raise HTTPException(status_code=400, detail="No hay una conexion activa para construir el contexto.")

    effective_db = (target_db or session.context_db or "").strip().upper()
    if not effective_db:
        raise HTTPException(status_code=400, detail="No hay base activa para construir el contexto.")

    # El JWT guarda los módulos del rol en "modules" (ver login). Se leen ambas
    # claves por compatibilidad con tokens viejos.
    allowed_modules = current_user.get("modules", current_user.get("allowed_modules", [])) or []
    return _build_context_overview(session, effective_db, allowed_modules=allowed_modules)


@router.post("/quantum-core/feedback")
async def quantum_core_feedback(
    req: FeedbackRequest,
    current_user: dict = Depends(get_token_data),
):
    verdict = (req.verdict or "").strip().lower()
    if verdict not in {"approved", "rejected", "needs_review"}:
        raise HTTPException(status_code=400, detail="Veredicto invalido.")

    payload = record_feedback(
        query_id=(req.query_id or "").strip(),
        verdict=verdict,
        note=req.note,
        user_id=current_user.get("sub", "unknown"),
        user_role=current_user.get("role", "GUEST"),
    )
    return {"status": "saved", "feedback": payload}
