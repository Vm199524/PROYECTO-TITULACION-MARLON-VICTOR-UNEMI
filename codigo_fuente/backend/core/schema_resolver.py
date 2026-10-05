"""
Resolución segura del esquema de la base activa.

Evita mezclar el esquema de la base de conexión con el de la empresa
seleccionada. Busca en tres niveles (caché de sesión, db_insights.json y
escaneo real) y filtra las tablas crudas para que el modelo de IA reciba solo
vistas VIS_ y tablas maestras relevantes.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
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
    """Devuelve el esquema real de la base solicitada usando la caché de la sesión.

    Prioriza las vistas VIS_ y descarta el ruido de las tablas crudas (tb_).

    Args:
        session: sesión activa con connector, context_db y schema_cache.
        target_db: base solicitada; si falta, se usa session.context_db.
        refresh: si es True, ignora las cachés y escanea la base.
        logger: logger opcional para registrar de dónde salió el esquema.

    Returns:
        Diccionario {tabla: columnas}; vacío si no hay sesión, si la base es
        de sistema o si no se pudo resolver.
    """
    if not session:
        return {}

    target_key = _norm_db_name(target_db) or _norm_db_name(getattr(session, "context_db", ""))
    
    # Protección: no se procesan esquemas de bases de sistema.
    if target_key in ('MASTER', 'TEMPDB', 'MODEL', 'MSDB', ''):
        return {}
    base_key = _norm_db_name(getattr(session, "context_db", ""))

    if not hasattr(session, "schema_cache") or not isinstance(session.schema_cache, dict):
        session.schema_cache = {}

    # 1. Caché de la sesión (memoria rápida).
    if target_key and not refresh:
        cached = session.schema_cache.get(target_key)
        if isinstance(cached, dict) and cached:
            return cached

    # 2. Caché global (db_insights.json).
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
                    # Se aplica el mismo filtro de ruido a los insights.
                    curated_tables = []
                    for t in db_data["ready_tables"]:
                        t_name = t.split(".")[-1]
                        # Prioridad 1: vistas VIS_.
                        if t_name.startswith("VIS_"):
                            curated_tables.append(t_name)
                        # Prioridad 2: tablas maestras críticas.
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

    # 3. Escaneo real de la base de datos.
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

    # 4. Filtrado dinámico de ruido: si hay más de 50 tablas, solo se conservan
    # las vistas y las tablas de la lista blanca para no confundir al modelo de IA.
    if isinstance(resolved, dict) and len(resolved) > 50:
        filtered = {}
        # Tablas de catálogo y soporte.
        whitelist_catalog = {
            "tb_empresa", "tb_empres", "tb_rubros", "tb_cargo", "tb_departamento",
            "tb_area", "tb_tipemp", "tb_estemp",
        }
        # Tablas transaccionales críticas para el motor BI (get_bi_pulse): sin
        # ellas el tablero no genera ninguna tarjeta y provoca reintentos en cadena.
        whitelist_bi = {
            # Ventas y compras (Balance Comercial)
            "tb_cabmov", "tb_detmov",
            "tb_cabmov1", "tb_detmov1",
            # RRHH
            "tb_trabaj",
            # Nómina
            "tb_cabrol", "tb_detrol", "tb_acutra",
            # Académico
            "edu_alumno", "edu_cursos",
            # Relaciones frecuentes en los JOIN de las vistas maestras
            "tb_client", "tb_provee", "tb_item",
            "tb_cencos", "tb_seccion",
        }
        whitelist = whitelist_catalog | whitelist_bi
        for t_name, t_data in resolved.items():
            # Regla A: las vistas de reporte (VIS_) se incluyen.
            if t_name.startswith("VIS_"):
                filtered[t_name] = t_data
            # Regla B: las tablas maestras críticas o de BI se incluyen.
            elif t_name.lower() in whitelist:
                filtered[t_name] = t_data
            # Regla C: el resto de tablas crudas se omite para reducir ruido en la IA.

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
