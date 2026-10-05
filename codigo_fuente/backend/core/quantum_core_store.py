"""
Memoria operativa y panel ejecutivo de Quantum Core.

Registra los eventos del motor de consultas (JSONL) y la retroalimentación de
los usuarios, y arma el panel: métricas de uso, señales de aprendizaje,
reflexiones sobre errores y un resumen ejecutivo con indicadores del negocio.
El resumen ejecutivo consulta la base, por lo que se difiere hasta una
actualización manual y se guarda en caché por usuario y base durante
OVERVIEW_CACHE_TTL_SECONDS para no competir con el panel principal.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Any

from config import CACHE_DIR

EVENTS_FILE = CACHE_DIR / "quantum_core_events.jsonl"
FEEDBACK_FILE = CACHE_DIR / "quantum_core_feedback.json"
OVERVIEW_CACHE_TTL_SECONDS = 180
_OVERVIEW_CACHE: dict[str, dict[str, Any]] = {}


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _read_events(limit: int | None = None) -> list[dict[str, Any]]:
    """Lee los últimos `limit` eventos del JSONL, ignorando las líneas dañadas."""
    if not EVENTS_FILE.exists():
        return []
    try:
        lines = EVENTS_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    if limit:
        lines = lines[-limit:]
    events: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _load_feedback() -> list[dict[str, Any]]:
    if not FEEDBACK_FILE.exists():
        return []
    try:
        payload = json.loads(FEEDBACK_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def _save_feedback(entries: list[dict[str, Any]]) -> None:
    FEEDBACK_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_query_event(event: dict[str, Any]) -> None:
    """Agrega un evento del motor de consultas al JSONL, con marca de tiempo UTC si no la trae."""
    payload = dict(event)
    payload.setdefault("timestamp", _utc_now())
    with EVENTS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def record_feedback(
    query_id: str,
    verdict: str,
    note: str,
    user_id: str,
    user_role: str,
) -> dict[str, Any]:
    """Guarda la valoración de un usuario sobre una consulta y devuelve la entrada creada.

    Si la consulta ya tenía una valoración, se reemplaza: solo cuenta la última.
    """
    feedback = _load_feedback()
    entry = {
        "query_id": query_id,
        "verdict": verdict,
        "note": (note or "").strip(),
        "user_id": user_id,
        "user_role": user_role,
        "timestamp": _utc_now(),
    }
    feedback = [item for item in feedback if item.get("query_id") != query_id]
    feedback.append(entry)
    _save_feedback(feedback)
    return entry


def _domain_status(session) -> list[dict[str, Any]]:
    """Indica qué dominios de negocio están listos según las tablas o vistas del esquema de la sesión."""
    if not session:
        return []

    schema_dict = getattr(session, "schema_dict", {}) or {}
    names = {str(name).strip().lower() for name in schema_dict}

    def has_any(*aliases: str) -> bool:
        alias_set = {alias.strip().lower() for alias in aliases}
        return any(name in alias_set for name in names)

    domain_checks = (
        ("RRHH", has_any("ficha_trabajador", "v_ficha_maestra"), "Ficha maestra de personal"),
        ("Nomina", has_any("rol_pago", "v_resumen_nomina"), "Roles y rubros de pago"),
        ("Ventas", has_any("cabecera_factura", "v_ventas_cabecera"), "Facturacion comercial"),
        ("Compras", has_any("cabecera_compra", "v_compras_cabecera"), "Compras y abastecimiento"),
        ("Academico", has_any("vis_alumno", "v_registro_academico"), "Registro academico"),
        ("Inventario", has_any("inventario", "productos", "v_inventario_stock"), "Inventario y stock"),
    )

    results = []
    for domain, ready, detail in domain_checks:
        results.append(
            {
                "domain": domain,
                "status": "ready" if ready else "pending",
                "detail": detail if ready else f"Falta sincronizacion semantica para {domain.lower()}",
            }
        )
    return results


def _current_context(session) -> dict[str, Any]:
    """Resume el contexto de la sesión: conexión, base activa, rol y dominios disponibles."""
    if not session:
        return {
            "connected": False,
            "database": "",
            "master_dna": False,
            "authority": "",
            "domains": [],
        }
    return {
        "connected": bool(getattr(session, "connector", None)),
        "database": getattr(session, "context_db", ""),
        "master_dna": bool(getattr(session, "master_schema_text", "")),
        "authority": getattr(session, "role", ""),
        "domains": _domain_status(session),
    }


def _session_cache_key(session) -> str:
    if not session:
        return "anonymous"
    return f"{getattr(session, 'user_id', 'anon')}::{getattr(session, 'context_db', '')}"


def _get_cached_overview(session) -> dict[str, Any] | None:
    """Devuelve el panel en caché de la sesión si no superó OVERVIEW_CACHE_TTL_SECONDS."""
    cache_key = _session_cache_key(session)
    payload = _OVERVIEW_CACHE.get(cache_key)
    if not payload:
        return None
    age_seconds = (datetime.utcnow() - payload["created_at"]).total_seconds()
    if age_seconds > OVERVIEW_CACHE_TTL_SECONDS:
        _OVERVIEW_CACHE.pop(cache_key, None)
        return None
    return payload["value"]


def _set_cached_overview(session, overview: dict[str, Any]) -> None:
    _OVERVIEW_CACHE[_session_cache_key(session)] = {
        "created_at": datetime.utcnow(),
        "value": overview,
    }


def _has_table(session, *aliases: str) -> bool:
    schema_dict = getattr(session, "schema_dict", {}) or {}
    names = {str(name).strip().lower() for name in schema_dict}
    return any(alias.strip().lower() in names for alias in aliases)


def _execute_rows(session, sql: str) -> tuple[list[str], list[list[Any]]]:
    """Ejecuta el SQL con el conector de la sesión; ante cualquier error devuelve listas vacías."""
    connector = getattr(session, "connector", None)
    if not connector:
        return [], []
    try:
        columns, rows, error = connector.execute_query(sql)
    except Exception:
        return [], []
    if error or not rows:
        return columns or [], []
    return columns or [], rows or []


def _first_row_dict(session, sql: str) -> dict[str, Any]:
    columns, rows = _execute_rows(session, sql)
    if not columns or not rows:
        return {}
    row = rows[0]
    return {
        str(columns[idx]).strip(): row[idx]
        for idx in range(min(len(columns), len(row)))
    }


def _rows_as_dicts(session, sql: str) -> list[dict[str, Any]]:
    columns, rows = _execute_rows(session, sql)
    if not columns or not rows:
        return []
    result = []
    for row in rows:
        result.append(
            {
                str(columns[idx]).strip(): row[idx]
                for idx in range(min(len(columns), len(row)))
            }
        )
    return result


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except Exception:
        return 0


def _month_name(month_number: int) -> str:
    names = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre",
    }
    return names.get(month_number, "-")


def _sales_ytd(session) -> float:
    """Devuelve el total facturado en lo que va del año, o 0.0 si no hay tabla de ventas."""
    if not _has_table(session, "cabecera_factura", "v_ventas_cabecera"):
        return 0.0
    row = _first_row_dict(
        session,
        "SELECT CAST(SUM(TRY_CAST(Total AS FLOAT)) AS DECIMAL(18,2)) AS total "
        "FROM cabecera_factura "
        "WHERE YEAR(Fecha) = YEAR(GETDATE())",
    )
    return _as_float(row.get("total"))


def _purchases_ytd(session) -> float:
    """Devuelve el total comprado en lo que va del año, o 0.0 si no hay tabla de compras."""
    if not _has_table(session, "cabecera_compra", "v_compras_cabecera"):
        return 0.0
    row = _first_row_dict(
        session,
        "SELECT CAST(SUM(TRY_CAST(Total AS FLOAT)) AS DECIMAL(18,2)) AS total "
        "FROM cabecera_compra "
        "WHERE YEAR(Fecha) = YEAR(GETDATE())",
    )
    return _as_float(row.get("total"))


def _payroll_last_period(session) -> dict[str, Any]:
    """Calcula el costo de nómina del último periodo (año y mes) con datos.

    El mes puede venir como número o como nombre (completo o abreviado), así
    que se normaliza con un CASE antes de buscar el periodo más reciente.
    Solo suma los valores positivos.
    """
    if not _has_table(session, "rol_pago", "v_resumen_nomina"):
        return {"total": 0.0, "label": "Sin periodo"}

    month_case = (
        "CASE "
        "WHEN TRY_CAST(rp.[Mes] AS INT) BETWEEN 1 AND 12 THEN TRY_CAST(rp.[Mes] AS INT) "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('ENERO','ENE') THEN 1 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('FEBRERO','FEB') THEN 2 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('MARZO','MAR') THEN 3 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('ABRIL','ABR') THEN 4 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('MAYO','MAY') THEN 5 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('JUNIO','JUN') THEN 6 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('JULIO','JUL') THEN 7 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('AGOSTO','AGO') THEN 8 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('SEPTIEMBRE','SETIEMBRE','SEP','SET') THEN 9 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('OCTUBRE','OCT') THEN 10 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('NOVIEMBRE','NOV') THEN 11 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('DICIEMBRE','DIC') THEN 12 "
        "ELSE NULL END"
    )
    row = _first_row_dict(
        session,
        "WITH Base AS ("
        "  SELECT TRY_CAST(rp.[Año] AS INT) AS anio_num, "
        f"         {month_case} AS mes_num, "
        "         TRY_CAST(rp.[Valor] AS FLOAT) AS valor_num "
        "  FROM rol_pago rp"
        "), PeriodoObjetivo AS ("
        "  SELECT TOP 1 anio_num, mes_num "
        "  FROM Base "
        "  WHERE anio_num IS NOT NULL AND mes_num IS NOT NULL "
        "  ORDER BY anio_num DESC, mes_num DESC"
        ") "
        "SELECT TOP 1 "
        "  p.anio_num AS anio, "
        "  p.mes_num AS mes, "
        "  CAST(SUM(CASE WHEN b.valor_num > 0 THEN b.valor_num ELSE 0 END) AS DECIMAL(18,2)) AS total "
        "FROM Base b "
        "JOIN PeriodoObjetivo p ON b.anio_num = p.anio_num AND b.mes_num = p.mes_num "
        "GROUP BY p.anio_num, p.mes_num",
    )
    month_num = _as_int(row.get("mes"))
    year_num = _as_int(row.get("anio"))
    return {
        "total": _as_float(row.get("total")),
        "year": year_num,
        "month": month_num,
        "label": f"{_month_name(month_num)} {year_num}".strip(),
    }


def _workforce_snapshot(session) -> dict[str, Any]:
    """Cuenta el personal activo e inactivo y las 5 áreas con más personal activo."""
    if not _has_table(session, "ficha_trabajador", "v_ficha_maestra"):
        return {"active": 0, "inactive": 0, "areas": []}

    base_where = (
        "UPPER(LTRIM(RTRIM(CAST([Estado] AS NVARCHAR(60))))) NOT LIKE '%INACTIV%' "
        "AND LTRIM(RTRIM(CAST([Estado] AS NVARCHAR(60)))) <> ''"
    )
    counts = _first_row_dict(
        session,
        "SELECT "
        f"  SUM(CASE WHEN {base_where} THEN 1 ELSE 0 END) AS activos, "
        "  SUM(CASE WHEN UPPER(LTRIM(RTRIM(CAST([Estado] AS NVARCHAR(60))))) LIKE '%INACTIV%' THEN 1 ELSE 0 END) AS inactivos "
        "FROM ficha_trabajador",
    )
    areas = _rows_as_dicts(
        session,
        "SELECT TOP 5 "
        "  COALESCE(NULLIF(LTRIM(RTRIM(CAST([Area] AS NVARCHAR(120)))), ''), 'Sin area') AS area, "
        "  COUNT(*) AS total "
        "FROM ficha_trabajador "
        f"WHERE {base_where} "
        "GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(CAST([Area] AS NVARCHAR(120)))), ''), 'Sin area') "
        "ORDER BY total DESC, area",
    )
    return {
        "active": _as_int(counts.get("activos")),
        "inactive": _as_int(counts.get("inactivos")),
        "areas": [
            {"label": item.get("area") or "Sin area", "value": _as_int(item.get("total"))}
            for item in areas
        ],
    }


def _monthly_business_overview(session) -> list[dict[str, Any]]:
    """Devuelve los últimos 6 meses con facturado, comprado, nómina y saldo neto.

    El saldo neto es facturado menos comprado menos nómina; los meses se toman
    de la unión de las tres fuentes para no perder periodos con datos parciales.
    """
    if not (
        _has_table(session, "cabecera_factura", "v_ventas_cabecera")
        or _has_table(session, "cabecera_compra", "v_compras_cabecera")
        or _has_table(session, "rol_pago", "v_resumen_nomina")
    ):
        return []

    payroll_month_case = (
        "CASE "
        "WHEN TRY_CAST(rp.[Mes] AS INT) BETWEEN 1 AND 12 THEN TRY_CAST(rp.[Mes] AS INT) "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('ENERO','ENE') THEN 1 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('FEBRERO','FEB') THEN 2 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('MARZO','MAR') THEN 3 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('ABRIL','ABR') THEN 4 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('MAYO','MAY') THEN 5 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('JUNIO','JUN') THEN 6 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('JULIO','JUL') THEN 7 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('AGOSTO','AGO') THEN 8 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('SEPTIEMBRE','SETIEMBRE','SEP','SET') THEN 9 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('OCTUBRE','OCT') THEN 10 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('NOVIEMBRE','NOV') THEN 11 "
        "WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('DICIEMBRE','DIC') THEN 12 "
        "ELSE NULL END"
    )
    rows = _rows_as_dicts(
        session,
        "WITH facturado AS ("
        "  SELECT YEAR(Fecha) AS anio, MONTH(Fecha) AS mes_num, "
        "         CAST(SUM(TRY_CAST(Total AS FLOAT)) AS DECIMAL(18,2)) AS facturado "
        "  FROM cabecera_factura "
        "  GROUP BY YEAR(Fecha), MONTH(Fecha)"
        "), comprado AS ("
        "  SELECT YEAR(Fecha) AS anio, MONTH(Fecha) AS mes_num, "
        "         CAST(SUM(TRY_CAST(Total AS FLOAT)) AS DECIMAL(18,2)) AS comprado "
        "  FROM cabecera_compra "
        "  GROUP BY YEAR(Fecha), MONTH(Fecha)"
        "), nomina AS ("
        "  SELECT TRY_CAST(rp.[Año] AS INT) AS anio, "
        f"         {payroll_month_case} AS mes_num, "
        "         CAST(SUM(CASE WHEN TRY_CAST(rp.[Valor] AS FLOAT) > 0 "
        "              THEN TRY_CAST(rp.[Valor] AS FLOAT) ELSE 0 END) AS DECIMAL(18,2)) AS nomina "
        "  FROM rol_pago rp "
        "  GROUP BY TRY_CAST(rp.[Año] AS INT), "
        f"           {payroll_month_case}"
        "), base AS ("
        "  SELECT anio, mes_num FROM facturado "
        "  UNION SELECT anio, mes_num FROM comprado "
        "  UNION SELECT anio, mes_num FROM nomina"
        ") "
        "SELECT TOP 6 "
        "  base.anio AS anio, "
        "  base.mes_num AS mes_num, "
        "  ISNULL(f.facturado, 0) AS facturado, "
        "  ISNULL(c.comprado, 0) AS comprado, "
        "  ISNULL(n.nomina, 0) AS nomina, "
        "  ISNULL(f.facturado, 0) - ISNULL(c.comprado, 0) - ISNULL(n.nomina, 0) AS saldo_neto "
        "FROM base "
        "LEFT JOIN facturado f ON base.anio = f.anio AND base.mes_num = f.mes_num "
        "LEFT JOIN comprado c ON base.anio = c.anio AND base.mes_num = c.mes_num "
        "LEFT JOIN nomina n ON base.anio = n.anio AND base.mes_num = n.mes_num "
        "WHERE base.anio IS NOT NULL AND base.mes_num IS NOT NULL "
        "ORDER BY base.anio DESC, base.mes_num DESC",
    )
    payload = []
    for item in rows:
        month_num = _as_int(item.get("mes_num"))
        year_num = _as_int(item.get("anio"))
        payload.append(
            {
                "year": year_num,
                "month_num": month_num,
                "month_label": _month_name(month_num),
                "facturado": _as_float(item.get("facturado")),
                "comprado": _as_float(item.get("comprado")),
                "nomina": _as_float(item.get("nomina")),
                "saldo_neto": _as_float(item.get("saldo_neto")),
                "period_label": f"{_month_name(month_num)} {year_num}".strip(),
            }
        )
    return payload


def _build_business_alerts(
    current_context: dict[str, Any],
    monthly_overview: list[dict[str, Any]],
    payroll_info: dict[str, Any],
    workforce: dict[str, Any],
) -> list[dict[str, str]]:
    """Genera hasta 4 alertas del negocio.

    Cubre dominios pendientes, saldo neto del último periodo, disponibilidad
    de la nómina y una base inactiva mayor al 30 % del personal activo.
    """
    alerts: list[dict[str, str]] = []
    pending_domains = [item["domain"] for item in current_context.get("domains", []) if item.get("status") != "ready"]
    if pending_domains:
        alerts.append(
            {
                "level": "warning",
                "title": "Cobertura incompleta",
                "detail": "Aun hay dominios pendientes para consultas confiables: " + ", ".join(pending_domains[:3]),
            }
        )

    latest_period = monthly_overview[0] if monthly_overview else None
    if latest_period:
        if latest_period.get("saldo_neto", 0) < 0:
            alerts.append(
                {
                    "level": "critical",
                    "title": "Resultado operativo en rojo",
                    "detail": f"El periodo {latest_period['period_label']} cerro con saldo neto negativo.",
                }
            )
        else:
            alerts.append(
                {
                    "level": "positive",
                    "title": "Resultado operativo favorable",
                    "detail": f"El periodo {latest_period['period_label']} mantiene saldo neto positivo.",
                }
            )

    if payroll_info.get("total", 0) > 0:
        alerts.append(
            {
                "level": "info",
                "title": "Nomina consolidada disponible",
                "detail": f"Ya existe lectura del costo total de nomina para {payroll_info.get('label', 'el ultimo periodo')}.",
            }
        )

    inactive = workforce.get("inactive", 0)
    active = workforce.get("active", 0)
    if inactive and active and inactive > active * 0.3:
        alerts.append(
            {
                "level": "warning",
                "title": "Plantilla con alta base inactiva",
                "detail": "Conviene revisar depuracion de historicos e inactivos en la ficha maestra.",
            }
        )

    if not alerts:
        alerts.append(
            {
                "level": "info",
                "title": "Sin alertas criticas visibles",
                "detail": "La base activa entrega suficiente señal para operar el cockpit ejecutivo.",
            }
        )
    return alerts[:4]


def _build_focus_items(
    current_context: dict[str, Any],
    metrics: dict[str, Any],
    monthly_overview: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Genera hasta 3 puntos de atención para el panel (resultado reciente, consultas sin datos, dominios pendientes)."""
    items: list[dict[str, str]] = []
    if monthly_overview:
        latest = monthly_overview[0]
        items.append(
            {
                "title": "Resultado operativo reciente",
                "detail": f"{latest['period_label']}: saldo neto de {latest['saldo_neto']:.2f}.",
            }
        )

    if metrics.get("no_data_queries", 0):
        items.append(
            {
                "title": "Preguntas sin datos",
                "detail": "El sistema detecto consultas donde aun faltan tablas maestras o vistas sincronizadas.",
            }
        )

    pending = [item["domain"] for item in current_context.get("domains", []) if item.get("status") != "ready"]
    if pending:
        items.append(
            {
                "title": "Prioridad de ampliacion",
                "detail": "Siguiente frente recomendado: " + ", ".join(pending[:2]),
            }
        )

    if not items:
        items.append(
            {
                "title": "Operacion estable",
                "detail": "No se detectan deudas evidentes en la foto actual del cockpit.",
            }
        )
    return items[:3]


def _build_executive_summary(session, current_context: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """Arma el resumen ejecutivo completo consultando la base (indicadores, meses, personal, alertas)."""
    if not session or not getattr(session, "connector", None):
        return {
            "kpis": {},
            "monthly_overview": [],
            "workforce": {"active": 0, "inactive": 0, "areas": []},
            "alerts": [],
            "focus_items": [],
            "quick_actions": [],
        }

    sales_ytd = _sales_ytd(session)
    purchases_ytd = _purchases_ytd(session)
    payroll_info = _payroll_last_period(session)
    workforce = _workforce_snapshot(session)
    monthly_overview = _monthly_business_overview(session)
    alerts = _build_business_alerts(current_context, monthly_overview, payroll_info, workforce)
    focus_items = _build_focus_items(current_context, metrics, monthly_overview)

    latest_period = monthly_overview[0] if monthly_overview else {}
    quick_actions = [
        "Cual es el volumen total de ventas facturado este ano?",
        "Resumen ejecutivo mensual de ingresos y egresos operativos",
        "Cual es el costo total de la nomina del ultimo mes con aportes?",
        "Cuantos empleados hay activos actualmente en la empresa?",
    ]

    return {
        "kpis": {
            "sales_ytd": sales_ytd,
            "purchases_ytd": purchases_ytd,
            "payroll_last_period": payroll_info.get("total", 0.0),
            "payroll_period_label": payroll_info.get("label", "Sin periodo"),
            "active_employees": workforce.get("active", 0),
            "inactive_employees": workforce.get("inactive", 0),
            "latest_net_result": latest_period.get("saldo_neto", 0.0),
            "latest_period_label": latest_period.get("period_label", "Sin periodo"),
        },
        "monthly_overview": monthly_overview,
        "workforce": workforce,
        "alerts": alerts,
        "focus_items": focus_items,
        "quick_actions": quick_actions,
    }


def _build_light_executive_summary(current_context: dict[str, Any]) -> dict[str, Any]:
    """Devuelve un resumen ejecutivo vacío, sin consultar la base, a la espera de una actualización manual."""
    return {
        "kpis": {
            "sales_ytd": 0.0,
            "purchases_ytd": 0.0,
            "payroll_last_period": 0.0,
            "payroll_period_label": "Actualizar panel",
            "active_employees": 0,
            "inactive_employees": 0,
            "latest_net_result": 0.0,
            "latest_period_label": "Actualizar panel",
        },
        "monthly_overview": [],
        "workforce": {"active": 0, "inactive": 0, "areas": []},
        "alerts": [
            {
                "level": "info",
                "title": "Panel en espera de actualización",
                "detail": "Presione 'Actualizar panel' para cargar los indicadores ejecutivos sin afectar la experiencia principal.",
            }
        ],
        "focus_items": [
            {
                "title": "Modo liviano activo",
                "detail": "El resumen ejecutivo se difiere hasta una actualización manual para no competir con el panel principal.",
            }
        ],
        "quick_actions": [
            "Resumen ejecutivo mensual de ingresos y egresos operativos",
            "Cual es el volumen total de ventas facturado este ano?",
            "Cual es el costo total de la nomina del ultimo mes con aportes?",
        ],
    }


def _build_base_overview_payload(session=None, limit: int = 20) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Arma la parte del panel que sale de los eventos y la retroalimentación, sin consultar la base.

    Usa los últimos 400 eventos para las métricas y las señales de
    aprendizaje, y hasta 8 reflexiones sobre consultas con error, sin datos,
    bloqueadas por el guardarraíl o autocorregidas.

    Returns:
        (payload, current_context, metrics, recent_events, reflections).
    """
    events = _read_events(limit=400)
    feedback = _load_feedback()

    total = len(events)
    if total:
        status_counter = Counter(event.get("status", "unknown") for event in events)
        avg_latency = round(
            sum(float(event.get("duration_ms", 0) or 0) for event in events) / total,
            1,
        )
    else:
        status_counter = Counter()
        avg_latency = 0.0

    bank_counter = Counter(
        event.get("bank_id")
        for event in events
        if event.get("bank_id")
    )
    module_counter = Counter(
        event.get("module", "GLOBAL")
        for event in events
    )

    recent_events = []
    feedback_by_query = {item.get("query_id"): item for item in feedback if item.get("query_id")}
    for event in reversed(events[-limit:]):
        event_payload = dict(event)
        if event_payload.get("query_id") in feedback_by_query:
            event_payload["feedback"] = feedback_by_query[event_payload["query_id"]]
        recent_events.append(event_payload)

    reflections = []
    for event in reversed(events):
        if event.get("status") in {"error", "no_data", "guardrail"} or event.get("auto_corrected"):
            reflections.append(
                {
                    "query_id": event.get("query_id"),
                    "timestamp": event.get("timestamp"),
                    "status": event.get("status"),
                    "prompt": event.get("prompt"),
                    "reflection": event.get("reflection")
                    or event.get("error")
                    or event.get("explanation_preview")
                    or "Sin detalle disponible.",
                }
            )
        if len(reflections) >= 8:
            break

    feedback_summary = Counter(item.get("verdict", "none") for item in feedback)
    current_context = _current_context(session)
    metrics = {
        "total_queries": total,
        "success_queries": status_counter.get("success", 0),
        "no_data_queries": status_counter.get("no_data", 0),
        "error_queries": status_counter.get("error", 0),
        "guardrail_queries": status_counter.get("guardrail", 0),
        "auto_corrected_queries": sum(1 for event in events if event.get("auto_corrected")),
        "avg_latency_ms": avg_latency,
    }
    payload = {
        "generated_at": _utc_now(),
        "current_context": current_context,
        "metrics": metrics,
        "learning_signals": {
            "top_bank_paths": [
                {"label": label, "count": count}
                for label, count in bank_counter.most_common(6)
            ],
            "module_activity": [
                {"label": label, "count": count}
                for label, count in module_counter.most_common(6)
            ],
            "feedback_summary": {
                "approved": feedback_summary.get("approved", 0),
                "rejected": feedback_summary.get("rejected", 0),
                "needs_review": feedback_summary.get("needs_review", 0),
            },
        },
        "recent_events": recent_events,
        "recent_reflections": reflections,
    }
    return payload, current_context, metrics, recent_events, reflections


def build_quantum_core_overview(session=None, limit: int = 20, force_refresh: bool = False) -> dict[str, Any]:
    """Construye el panel de Quantum Core para la sesión.

    Sin `force_refresh`, sirve la versión en caché si existe; si no, devuelve
    el panel con un resumen ejecutivo liviano (deferred=True) para no lanzar
    consultas pesadas en cada carga. Con `force_refresh`, consulta la base,
    arma el resumen ejecutivo completo y lo guarda en caché.
    """
    if not force_refresh:
        cached = _get_cached_overview(session)
        if cached:
            result = dict(cached)
            result["served_from_cache"] = True
            return result
        payload, current_context, metrics, _recent_events, _reflections = _build_base_overview_payload(session, limit=limit)
        payload["executive_summary"] = _build_light_executive_summary(current_context)
        payload["served_from_cache"] = False
        payload["deferred"] = True
        return payload

    payload, current_context, metrics, recent_events, reflections = _build_base_overview_payload(session, limit=limit)
    payload["executive_summary"] = _build_executive_summary(session, current_context, metrics)
    payload["served_from_cache"] = False
    payload["deferred"] = False
    _set_cached_overview(session, payload)
    return payload
