"""
core/schema_resolver.py - Resolucion segura de esquema por base activa.
Evita mezclar el schema de la base de conexion con la empresa seleccionada.
"""
from __future__ import annotations

import logging
from typing import Optional


def _norm_db_name(value: str | None) -> str:
    return str(value or "").strip().upper()


def resolve_schema_for_db(
    session,
    target_db: str | None,
    *,
    refresh: bool = False,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """
    Retorna el schema real para la base solicitada usando cache por sesion.
    Incluye un filtro para priorizar vistas (VIS_) y eliminar ruido de tablas crudas (tb_).
    """
    if not session:
        return {}

    target_key = _norm_db_name(target_db) or _norm_db_name(getattr(session, "context_db", ""))
    
    # PROTECCION: No procesar esquemas de bases de sistema
    if target_key in ('MASTER', 'TEMPDB', 'MODEL', 'MSDB', ''):
        return {}
    base_key = _norm_db_name(getattr(session, "context_db", ""))

    if not hasattr(session, "schema_cache") or not isinstance(session.schema_cache, dict):
        session.schema_cache = {}

    # 1. Cache de Sesion (Memoria Rapida)
    if target_key and not refresh:
        cached = session.schema_cache.get(target_key)
        if isinstance(cached, dict) and cached:
            return cached

    # 2. Cache Global (db_insights.json)
    if target_key and not refresh:
        try:
            from pathlib import Path
            import json
            insight_path = Path("data/db_insights.json")
            if not insight_path.exists():
                insight_path = Path("backend/data/db_insights.json")
            
            if insight_path.exists():
                with open(insight_path, "r", encoding="utf-8") as f:
                    insights = json.load(f)
                
                db_data = insights.get(target_key)
                if db_data and "ready_tables" in db_data:
                    # Aplicar filtro a insights
                    curated_tables = []
                    for t in db_data["ready_tables"]:
                        t_name = t.split(".")[-1]
                        # Prioridad 1: Vistas VIS_
                        if t_name.startswith("VIS_"):
                            curated_tables.append(t_name)
                        # Prioridad 2: Tablas maestras criticas
                        elif t_name in ("tb_trabaj", "tb_cabrol", "tb_detrol", "tb_cabmov", "tb_detmov", "tb_acutra", "tb_empresa"):
                            curated_tables.append(t_name)
                    
                    resolved = {t: {} for t in curated_tables}
                    if resolved:
                        if logger:
                            logger.info("[SPEED] Usando insights filtrados para %s", target_key)
                        session.schema_cache[target_key] = resolved
                        return resolved
        except Exception as e:
            if logger:
                logger.warning("Error cargando insights para %s: %s", target_key, e)

    # 3. Escaneo Real (Base de Datos)
    resolved = {}
    connector = getattr(session, "connector", None)
    if connector and hasattr(connector, "get_schema") and target_key:
        try:
            if target_key == base_key:
                resolved = connector.get_schema() or {}
            else:
                resolved = connector.get_schema(database_override=target_key) or {}
        except Exception as exc:
            if logger:
                logger.warning("No se pudo resolver schema para %s en DB: %s", target_key, exc)

    # 4. FILTRADO DINAMICO DE RUIDO (CRITICO PARA EVITAR CONFUSION DE IA)
    if isinstance(resolved, dict) and len(resolved) > 50:
        filtered = {}
        # Tablas de catalogo/soporte base
        whitelist_catalog = {
            "tb_empresa", "tb_empres", "tb_rubros", "tb_cargo", "tb_departamento",
            "tb_area", "tb_tipemp", "tb_estemp",
        }
        # Tablas transaccionales criticas para el motor BI (get_bi_pulse)
        # SIN estas tablas el dashboard no puede generar ninguna tarjeta y provoca retries en cadena
        whitelist_bi = {
            # Ventas y Compras (Balance Comercial)
            "tb_cabmov", "tb_detmov",
            "tb_cabmov1", "tb_detmov1",
            # RRHH
            "tb_trabaj",
            # Nomina
            "tb_cabrol", "tb_detrol", "tb_acutra",
            # Academico
            "edu_alumno", "edu_cursos",
            # Relaciones frecuentes en JOINs de las vistas maestras
            "tb_client", "tb_provee", "tb_item",
            "tb_cencos", "tb_seccion",
        }
        whitelist = whitelist_catalog | whitelist_bi
        for t_name, t_data in resolved.items():
            # Regla A: Si es una vista de reporte (VIS_), la incluimos
            if t_name.startswith("VIS_"):
                filtered[t_name] = t_data
            # Regla B: Si es una tabla maestra critica o BI, la incluimos
            elif t_name.lower() in whitelist:
                filtered[t_name] = t_data
            # Regla C: Resto de tablas crudas se omiten para reducir ruido en la IA

        if len(filtered) > 0:
            if logger:
                logger.info(
                    "[CLEANUP] Filtradas %d tablas crudas de %d totales "
                    "(conservadas: %d incluye BI criticas)",
                    len(resolved) - len(filtered), len(resolved), len(filtered)
                )
            resolved = filtered

    if isinstance(resolved, dict) and resolved:
        session.schema_cache[target_key] = resolved
        return resolved

    return {}
