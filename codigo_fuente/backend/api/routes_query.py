"""
api/routes_query.py - Orquestador NL2SQL con aislamiento por sesion.
Aplica seguridad server-side, cache y autocuracion en un flujo unico.
Protege el acceso por token y modulo antes de ejecutar cualquier SQL.
"""
from __future__ import annotations

import re
import time
import unicodedata
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _log_query_error(origen: str, prompt: str = "", empresa: str = "", detalle: str = "", traza: str = "") -> None:
    """Traza persistente de errores de consulta a debug/query_error.log.

    El log de uvicorn va a la consola del lanzador (oculta), por lo que un
    fallo en /query/stream quedaba sin rastro para diagnosticar. Aquí se
    anexa una línea JSON por error con la pregunta, la empresa y el traceback
    completo, de modo que el siguiente fallo sea reproducible sin pantalla.
    """
    try:
        ruta = DEBUG_DIR / "query_error.log"
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(_json.dumps({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "origen": origen,
                "empresa": empresa,
                "prompt": prompt,
                "detalle": detalle[:2000],
                "traza": traza[-4000:],
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncio
import json as _json

from cache.query_cache import get_cached, set_cached
from config import DEBUG_DIR
from core.quantum_core_store import record_query_event
from core.question_bank import buscar_en_banco
from core.metric_catalog import resolver_metrica, hints_para_prompt
from core.vista_resolver import CANDIDATOS_VENTAS, CANDIDATOS_COMPRAS, detectar_vista_connector
from core.integridad_vistas import (
    vistas_no_aisladas_en_sql,
    vista_aislada_para_empresa,
    pregunta_es_de_nomina,
    resolver_aviso_integridad,
)
from core.schema_resolver import resolve_schema_for_db
from core.session_manager import SESSION_STORE
from core.sql_sanitizer import sanitize_pipeline
from knowledge.chat_mapping import get_relevant_schema
from security import get_token_data
from core.mirror_manager import MirrorManager
from core.semantic_processor import SemanticProcessor

# Inicializar Procesador Semantico Global
SEMANTIC_PROC = SemanticProcessor()

# TTL del caché de RESPUESTA COMPLETA (Redis). Deliberadamente corto: a
# diferencia de SEMANTIC_PROC (que solo memoriza el SQL y siempre vuelve a
# golpear la base de datos), esta capa devuelve filas ya resueltas sin tocar
# la BD ni el LLM. Un TTL de 5 minutos cubre el caso real (el usuario o su
# equipo repite la misma pregunta exacta en la misma sesión de trabajo) sin
# arriesgar mostrar cifras de negocio "congeladas" como si fueran en vivo.
FULL_RESPONSE_CACHE_TTL = 300

# Archivo: routes_query.py
# Rol: pipeline principal de /api/query.
# Recibe desde: App.jsx cuando el usuario envia una pregunta desde ChatInput.jsx.
# Coordina con: session_manager, question_bank, sql_sanitizer, query_cache,
# chat_mapping y el cliente IA guardado en la sesion.
# Entrega: SQL, filas, narrativa, visualizacion y trazas operativas.

router = APIRouter()


def _vista_confiable_o_none(
    candidatos: tuple[str, ...], nombre_generico: str, connector, active_company_code: str
) -> str | None:
    """
    Nombre de vista a usar para `nombre_generico` (ej. "cabecera_factura"),
    solo si además se confirma en vivo que pertenece a la empresa activa.

    Dos verificaciones, ambas necesarias (regla fija: Reportes BI/chat solo
    muestran datos de la empresa activa):
      1. ¿Cuál de `candidatos` existe HOY en CHAT? (detectar_vista_connector) —
         cierra el bug del 28/08/2026 donde "cabecera_factura" ya no existe en
         el servidor y solo existe "Ventas"/"Compras".
      2. ¿Esa vista apunta HOY a la base física de `active_company_code`?
         (vista_aislada_para_empresa) — cierra el otro bug del mismo día: CHAT
         es un namespace compartido, y aunque el nombre exista, puede estar
         apuntando a OTRA empresa por una activación concurrente.

    Devuelve None si cualquiera de las dos falla — el llamador debe tratarlo
    como si la métrica hubiese fallado (nunca ejecutar "a ciegas").
    """
    vista_real = detectar_vista_connector(connector, candidatos, target_db="CHAT")
    if not vista_real:
        return None
    if not vista_aislada_para_empresa(connector, vista_real, active_company_code, target_db="CHAT"):
        return None
    return vista_real


class HistoryItem(BaseModel):
    """Fragmento de historial enviado por frontend para contexto de IA."""

    type: str = ""
    content: str = ""


class QueryRequest(BaseModel):
    """Contrato estricto para consultas NL2SQL."""

    prompt: str
    module: str | None = None
    history: list[HistoryItem] = Field(default_factory=list)
    selected_company_code: str = ""
    selected_company_name: str = ""
    selected_company_short_name: str = ""
    bi_context: dict | None = None
    # Selector manual de motor (30/08/2026): "", "flash", "pro" o un
    # proveedor puntual. Vacío = comportamiento por defecto
    # (Flash siempre). Se revalida en el servidor contra
    # `current_user["modelos_permitidos"]` — el valor que mande el cliente
    # nunca se usa a ciegas (mismo principio que ya aplicó el blindaje de
    # SQL/trazabilidad: la única fuente de verdad de permisos es el backend).
    motor_ia: str = ""


class VisionQueryRequest(BaseModel):
    """FASE 4 — punto 6: contrato para preguntas con imágenes adjuntas.

    `images` son data URLs completas (data:image/<tipo>;base64,....), tal
    como las produce FileReader.readAsDataURL() en el navegador.
    """

    prompt: str = ""
    images: list[str] = Field(default_factory=list)
    selected_company_code: str = ""
    selected_company_name: str = ""


class SpeakRequest(BaseModel):
    """Contrato de /query/speak — lectura en voz alta con FAL AI."""

    text: str
    voice: str = "Rachel"


def _normalize_module(module: str | None) -> str:
    return (module or "").strip().upper()


def _normalize_text(text: str) -> str:
    raw = (text or "").strip().lower()
    raw = unicodedata.normalize("NFD", raw)
    raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    raw = re.sub(r"[^a-z0-9\s]", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def _normalize_col_name(name: str) -> str:
    return _normalize_text(name or "").replace(" ", "")


def _is_missing_meta_value(value) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text in {"", "-", "0", "0.0", "0,0", "null", "none", "n/a", "na"}


def _find_col_index(columns: list[str], aliases: tuple[str, ...]) -> int:
    if not columns:
        return -1
    normalized = [_normalize_col_name(c) for c in columns]
    alias_norm = [_normalize_col_name(a) for a in aliases]
    for i in range(len(normalized) - 1, -1, -1):
        if normalized[i] in alias_norm:
            return i
    for i in range(len(normalized) - 1, -1, -1):
        if any(a in normalized[i] for a in alias_norm):
            return i
    return -1


def _extract_first_cedula(columns: list[str], rows: list) -> str | None:
    idx = _find_col_index(columns, ("cedula", "identificacion", "cedulaid", "id"))
    if idx < 0 or not rows:
        return None
    for row in rows:
        if idx < len(row):
            value = str(row[idx]).strip()
            if value:
                return value
    return None


def _enrich_payslip_metadata(connector, columns: list[str], rows: list) -> tuple[list[str], list] | None:
    if not rows:
        return None

    cedula = _extract_first_cedula(columns, rows)
    if not cedula:
        return None

    safe_cedula = cedula.replace("'", "''")
    meta_sql = (
        "SELECT TOP 1 * "
        "FROM ficha_trabajador "
        "WHERE LTRIM(RTRIM(CAST([Cedula] AS NVARCHAR(80)))) = "
        f"LTRIM(RTRIM(N'{safe_cedula}'))"
    )
    meta_cols, meta_rows, meta_err = connector.execute_query(meta_sql)
    if meta_err or not meta_rows:
        return None

    meta_row = meta_rows[0]
    field_map = (
        ("Nombres", ("nombres", "apellidosynombres", "nombresapellidos", "nombre")),
        ("Cargo", ("cargo", "descripcioncargo", "puesto", "ocupacion")),
        ("Area", ("area", "departamento", "departamentoarea", "unidad")),
        ("Tipo Contrato", ("tipocontrato", "contrato", "modalidad", "regimen", "estado")),
        ("Fecha Ingreso", ("fechaingreso", "ingreso", "fechacontrato")),
    )

    target_columns = list(columns)
    target_rows = [list(r) for r in rows]
    if not target_rows:
        return None

    for target_label, source_aliases in field_map:
        source_idx = _find_col_index(meta_cols, source_aliases)
        if source_idx < 0:
            continue
        source_val = meta_row[source_idx]
        if _is_missing_meta_value(source_val):
            continue

        target_idx = _find_col_index(target_columns, (target_label,))
        if target_idx >= 0:
            for row in target_rows:
                if target_idx < len(row) and _is_missing_meta_value(row[target_idx]):
                    row[target_idx] = source_val
        else:
            target_columns.append(target_label)
            for row in target_rows:
                row.append(source_val)

    return target_columns, target_rows


def _is_dynamic_payroll_query(prompt: str) -> bool:
    norm = _normalize_text(prompt)
    payroll_scope = any(token in norm for token in ("rol", "nomina", "pago", "payslip", "ficha"))
    salary_scope = any(token in norm for token in ("sueldo", "salario", "remuneracion"))
    extreme_scope = any(token in norm for token in ("mayor", "menor", "mas alto", "mas bajo", "maximo", "minimo"))
    return payroll_scope and salary_scope and extreme_scope


def _should_force_payslip(prompt: str) -> bool:
    norm = _normalize_text(prompt)
    payroll_scope = any(token in norm for token in ("rol", "pago", "payslip", "ficha"))
    person_scope = any(token in norm for token in ("trabajador", "empleado", "colaborador", "persona"))
    aggregate_scope = any(
        phrase in norm
        for phrase in (
            "costo total",
            "total de la nomina",
            "total nomina",
            "nomina del ultimo mes con aportes",
            "con aportes",
            "aporte patronal",
            "iess",
            "promedio",
            "comparativo",
            "resumen",
            "headcount",
        )
    )
    return payroll_scope and person_scope and not aggregate_scope


def _is_stock_query(prompt: str) -> bool:
    norm = _normalize_text(prompt)
    return any(token in norm for token in ("stock", "inventario", "reorden", "punto de reorden"))


def _schema_has_inventory_support(schema_dict: dict) -> bool:
    inventory_tokens = ("inventario", "producto", "productos", "item", "items", "bodega", "stock")
    for table_name in schema_dict:
        norm_table = _normalize_text(table_name)
        if any(token in norm_table for token in inventory_tokens):
            return True
    return False


def _find_schema_table(schema_dict: dict, aliases: tuple[str, ...]) -> str | None:
    alias_norm = {_normalize_text(alias).replace(" ", "") for alias in aliases}
    for table_name in schema_dict:
        candidate = _normalize_text(table_name).replace(" ", "")
        if candidate in alias_norm:
            return table_name
    return None


def _find_schema_column(schema_dict: dict, table_name: str | None, aliases: tuple[str, ...]) -> str | None:
    if not table_name:
        return None
    alias_norm = {_normalize_col_name(alias) for alias in aliases}
    for col in schema_dict.get(table_name, {}).get("columns", []):
        col_name = str(col.get("name", "")).strip()
        if _normalize_col_name(col_name) in alias_norm:
            return col_name
    return None


def _quote_identifier(name: str) -> str:
    return f"[{str(name or '').replace(']', ']]')}]"


_DB_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _safe_db_identifier(name: str | None) -> str:
    candidate = str(name or "").strip()
    if not candidate or not _DB_IDENTIFIER_RE.fullmatch(candidate):
        return ""
    return candidate


def _probe_db_metadata_access(connector, target_db: str | None) -> tuple[str, str]:
    """Valida acceso minimo de lectura a la BD objetivo para explicar fallos de metadata."""
    safe_db = _safe_db_identifier(target_db)
    if not safe_db:
        return "invalid_db", "El identificador de la base activa no es valido."
    if not connector:
        return "no_connector", "No existe un conector SQL activo en la sesion."

    probe_sql = f"SELECT TOP 1 name FROM [{safe_db}].sys.tables ORDER BY name"
    _, rows, err = connector.execute_query(probe_sql)
    if not err:
        return "ok", f"Lectura de catalogo confirmada en {safe_db} (sys.tables accesible)."

    lower = str(err).lower()
    if "permission" in lower or "denied" in lower or "permiso" in lower:
        return "permission_denied", f"Sin permisos de lectura sobre {safe_db}."
    if "cannot open database" in lower or "no se puede abrir la base de datos" in lower:
        return "db_unavailable", f"La base {safe_db} no esta accesible para este usuario SQL."
    if "login failed" in lower:
        return "auth_failed", "El login SQL no tiene autorizacion para la base activa."
    return "probe_error", f"Probe de metadata fallo: {err}"


def _extract_person_tokens(prompt: str) -> list[str]:
    stopwords = {
        "muestrame", "muestrame", "muestrame", "muestrame", "muestrame", "muestrame",
        "muestrame", "muestrame", "muestreme", "muestrame", "mostrar", "quiero", "ver",
        "rol", "pago", "nomina", "del", "de", "la", "el", "trabajador", "empleado",
        "colaborador", "persona", "detalle", "detallado", "ficha", "con", "para", "al",
        "por", "que", "cual", "cuanto", "su", "sus", "actual", "ultimo", "ultimos",
    }
    tokens: list[str] = []
    for token in _normalize_text(prompt).split():
        if len(token) < 3 or token in stopwords or token.isdigit():
            continue
        tokens.append(token.upper())
    return tokens[:5]


def _is_inactive_status(value: str | None) -> bool:
    if not value:
        return False
    norm = _normalize_text(value)
    active_markers = {"activo", "activa", "vigente", "habilitado", "habilitada"}
    inactive_markers = {
        "inactivo", "inactiva", "retirado", "retirada", "desvinculado", "desvinculada",
        "baja", "salio", "salida", "finiquitado", "finiquitada", "liquidado", "liquidada",
        "cesado", "cesada", "no vigente",
    }
    if norm in active_markers:
        return False
    return norm in inactive_markers or ("activo" not in norm and "vigente" not in norm)


def _lookup_employee_status(connector, schema_dict: dict, prompt: str) -> dict | None:
    ficha_table = _find_schema_table(schema_dict, ("ficha_trabajador", "V_Ficha_Maestra"))
    if not ficha_table:
        return None

    name_col = _find_schema_column(
        schema_dict,
        ficha_table,
        ("Nombres", "Apellidos y Nombres", "Nombre", "Nombres Completos"),
    )
    status_col = _find_schema_column(
        schema_dict,
        ficha_table,
        ("Estado", "Estado Laboral", "Estatus", "Status"),
    )
    if not name_col:
        return None

    tokens = _extract_person_tokens(prompt)
    if len(tokens) < 2:
        return None

    where_parts = []
    for token in tokens:
        safe_token = token.replace("'", "''")
        where_parts.append(
            f"UPPER(CAST({_quote_identifier(name_col)} AS NVARCHAR(300))) LIKE N'%{safe_token}%'"
        )
    status_select = f", {_quote_identifier(status_col)} AS EstadoLaboral" if status_col else ""
    status_order = (
        "CASE WHEN UPPER(CAST("
        f"{_quote_identifier(status_col)} AS NVARCHAR(100))) IN ('ACTIVO','ACTIVA','VIGENTE') "
        "THEN 1 ELSE 0 END,"
        if status_col
        else ""
    )
    sql = (
        "SELECT TOP 1 "
        f"{_quote_identifier(name_col)} AS NombreDetectado"
        f"{status_select} "
        f"FROM {_quote_identifier(ficha_table)} "
        f"WHERE {' AND '.join(where_parts)} "
        f"ORDER BY {status_order} {_quote_identifier(name_col)}"
    )
    cols, rows, err = connector.execute_query(sql)
    if err or not rows:
        return None

    row = rows[0]
    name_idx = _find_col_index(cols, ("NombreDetectado",))
    status_idx = _find_col_index(cols, ("EstadoLaboral",))
    return {
        "name": row[name_idx] if name_idx >= 0 and name_idx < len(row) else None,
        "status": row[status_idx] if status_idx >= 0 and status_idx < len(row) else None,
    }


def _build_no_rows_narrative(prompt: str, connector, schema_dict: dict) -> tuple[str, str]:
    norm = _normalize_text(prompt)
    payroll_scope = any(token in norm for token in ("rol", "nomina", "pago", "payslip", "ficha"))
    if payroll_scope:
        worker = _lookup_employee_status(connector, schema_dict, prompt)
        if worker:
            worker_name = str(worker.get("name") or "ese colaborador").strip()
            status = str(worker.get("status") or "").strip()
            if _is_inactive_status(status):
                explanation = (
                    f"No encontré roles de pago vigentes para {worker_name}. "
                    f"En la ficha de personal figura con estado {status or 'inactivo'}."
                )
                business = (
                    "### Lectura de negocio\n"
                    f"El colaborador {worker_name} ya no figura como personal activo, "
                    "por eso no aparecen roles vigentes en la consulta actual. "
                    "Si necesitas su historial, consulta un mes o anio especifico."
                )
                return explanation, business

            explanation = (
                f"No encontré registros de rol de pago para {worker_name} con el criterio consultado."
            )
            business = (
                "### Lectura de negocio\n"
                f"El colaborador {worker_name} existe en la base maestra, pero no tiene registros "
                "de rol que cumplan ese filtro. Prueba indicando el periodo exacto si buscas un rol historico."
            )
            return explanation, business

        explanation = (
            "No encontré registros de rol de pago que coincidan con el colaborador o periodo consultado."
        )
        business = (
            "### Lectura de negocio\n"
            "La base no devolvió coincidencias para ese colaborador en nómina. "
            "Puede tratarse de un trabajador inactivo, un nombre incompleto o un periodo sin roles cargados."
        )
        return explanation, business

    # Contextualizar la respuesta según el tema y el año detectado en la pregunta
    anio_match = re.search(r"\b(20\d{2})\b", prompt)
    anio_str = f" para el año {anio_match.group(1)}" if anio_match else ""

    norm = _normalize_text(prompt)
    tema = "datos"
    sugerencia = "Prueba ajustando el período de consulta o verificando los filtros aplicados."

    if "compra" in norm:
        tema = "compras"
        sugerencia = "Verifica que se hayan registrado movimientos de compra en el período indicado o prueba con otro rango de fechas."
    elif "venta" in norm or "factur" in norm:
        tema = "ventas / facturación"
        sugerencia = "Verifica que existan facturas emitidas en el período solicitado. Puedes intentar con el año más reciente."
    elif "inventario" in norm or "stock" in norm:
        tema = "inventario / stock"
        sugerencia = "Comprueba que los movimientos de inventario estén registrados en el sistema o consulta un período diferente."
    elif "cliente" in norm:
        tema = "clientes"
        sugerencia = "Asegúrate de que existan clientes registrados con los criterios indicados."
    elif "proveedor" in norm:
        tema = "proveedores"
        sugerencia = "Verifica que los proveedores estén ingresados en el sistema ERP activo."
    elif "empleado" in norm or "trabaj" in norm or "personal" in norm:
        tema = "personal / empleados"
        sugerencia = "Comprueba que los empleados estén activos o prueba sin filtro de estado."
    elif "alumno" in norm or "estudiante" in norm or "matric" in norm:
        tema = "alumnos / matrículas"
        sugerencia = "Verifica que la base tenga módulo académico activo y que el período lectivo esté configurado."
    elif "producto" in norm or "item" in norm or "articulo" in norm:
        tema = "productos / artículos"
        sugerencia = "Comprueba que los ítems estén activos en el catálogo del sistema."

    explanation = (
        f"🔍 No se encontraron registros de **{tema}**{anio_str} en la base activa.\n\n"
        f"{sugerencia}"
    )
    business = (
        "### Lectura de negocio\n"
        f"La consulta sobre **{tema}**{anio_str} devolvió 0 registros. "
        f"{sugerencia} "
        "Si el problema persiste, contacta al administrador para verificar el estado de los datos en el ERP."
    )
    return explanation, business



# Tope de palabras para que un mensaje pueda considerarse "probe de
# capacidades". Defecto detectado en pruebas (30/08/2026): "en una
# interacción le envié un mensaje largo y me respondió por defecto".
#
# La causa era este detector. Sus marcadores se buscan como SUBCADENA, y varios
# son fragmentos sueltos ("detecta", "alcance", "que base", "puedes ver",
# "conectado a", "puedo consultar"). En un mensaje de tres párrafos es casi
# seguro que aparezca alguno, así que el pipeline cortaba de inmediato y
# devolvía el catálogo de áreas de negocio — la "respuesta por defecto" — sin
# haber leído nada de lo que el usuario realmente pidió. La heurística final
# (que/cual + informacion/datos + tiene/hay) lo empeoraba: en un texto largo
# esas tres palabras coinciden por pura estadística.
#
# Un mensaje largo NUNCA es un probe: quien quiere saber qué puede consultar lo
# pregunta en una línea. Si es largo, es una instrucción concreta y tiene que
# llegar a la IA completa.
_MAX_PALABRAS_PROBE = 25

# Marcadores ambiguos: valen solo en mensajes cortos, porque son fragmentos que
# aparecen de paso en cualquier texto extenso.
_MARCADORES_PROBE_DEBILES = (
    "puedo consultar",
    "puedo preguntar",
    "que mas hay",
    "que otras cosas",
    "detecta",
    "puedes ver",
    "alcance",
    "capacidades",
    "que base",
    "conectado a",
    "conexion actual",
    "como esta organizada",
)
_MAX_PALABRAS_PROBE_DEBIL = 12


def _is_capability_probe(prompt: str) -> bool:
    """Detecta si el usuario pregunta sobre las capacidades del sistema."""
    norm = _normalize_text(prompt)
    palabras = norm.split()
    if len(palabras) > _MAX_PALABRAS_PROBE:
        return False
    markers = (
        "que puedo consultar",
        "que informacion puedo consultar",
        "que informacion tiene",
        "que tipo de informacion tiene",
        "que datos tiene",
        "que tipo de datos tiene",
        "que informacion contiene",
        "que datos contiene",
        "sobre que me puedes ayudar",
        "sobre que puedo preguntar",
        "que areas tiene",
        "que modulo tiene",
        "que puedes analizar",
        "que se puede consultar",
        "que puedo preguntar",
        "puedo consultar",
        "puedo preguntar",
        "que mas hay",
        "que otras cosas",
        "que dominios",
        "dominios espejo",
        "dominios clasicos",
        "detecta",
        "puedes ver",
        "alcance",
        "capacidades",
        "modulos disponibles",
        "tablas disponibles",
        "informacion disponible",
        "datos disponibles",
        "areas disponibles",
        "vistas espejo",
        "vistas virtuales",
        "adn virtual",
        "esquema actual",
        "estructura de la base",
        "como esta organizada",
        "que tablas puedes usar",
        "a que tienes acceso",
        "que campos tiene",
        "columnas disponibles",
        "que base",
        "base activa",
        "empresa activa",
        "conectado a",
        "conexion actual",
    )
    for marker in markers:
        if marker not in norm:
            continue
        # Los marcadores ambiguos solo cuentan en mensajes cortos (ver el
        # comentario de _MAX_PALABRAS_PROBE): en un texto medianamente largo
        # aparecen de paso y secuestran la respuesta.
        if marker in _MARCADORES_PROBE_DEBILES and len(palabras) > _MAX_PALABRAS_PROBE_DEBIL:
            continue
        return True

    # La heurística por conjuntos de palabras es la más propensa a falsos
    # positivos de todas, así que se limita al mismo rango corto.
    if len(palabras) > _MAX_PALABRAS_PROBE_DEBIL:
        return False

    words = set(palabras)
    asks_for_overview = bool({"que", "cual", "cuales"} & words)
    asks_capabilities = bool(
        {
            "informacion",
            "datos",
            "tablas",
            "campos",
            "columnas",
            "modulos",
            "areas",
            "dominios",
            "esquema",
            "estructura",
            "acceso",
            "consultar",
            "preguntar",
            "analizar",
        }
        & words
    )
    asks_availability = bool({"tiene", "tengo", "hay", "puedo", "puedes", "disponibles"} & words)
    return asks_for_overview and asks_capabilities and asks_availability





def _is_business_role_probe(prompt: str) -> bool:
    norm = _normalize_text(prompt)
    markers = (
        "rol de negocio",
        "giro de negocio",
        "sector de negocio",
        "a que se dedica",
        "actividad principal",
        "linea de negocio",
        "tipo de empresa",
        "cual es el rol de negocio",
        "cual es el giro",
        "que rol cumple",
    )
    return any(marker in norm for marker in markers)


def _build_business_role_response(snapshot: dict, company_label: str) -> dict:
    ready_areas = [area for area in snapshot.get("areas", []) if area.get("status") == "ready"]
    ready_names = [str(area.get("name") or "").strip() for area in ready_areas if area.get("name")]
    entities_count = int(snapshot.get("metrics", {}).get("entities_count", 0) or 0)

    if ready_names:
        domain_text = ", ".join(ready_names[:4])
        explanation = (
            f"Con base en el esquema activo de {company_label}, detecto foco de negocio en: {domain_text}. "
            "Esta lectura sale de tablas reales disponibles en este momento."
        )
        if len(ready_names) > 4:
            explanation += f" Tambien hay {len(ready_names) - 4} dominios adicionales detectados."
    else:
        explanation = (
            f"No puedo afirmar un giro unico para {company_label} con certeza, "
            "porque el esquema activo no expone dominios espejo suficientes para clasificarlo."
        )

    business = (
        "### Lectura de negocio\n"
        f"Empresa activa: {company_label}\n"
        f"Entidades analizadas: {entities_count}\n"
        + ("Dominios detectados: " + ", ".join(ready_names) if ready_names else "Dominios detectados: sin evidencia concluyente")
    )

    return {
        "sql": "",
        "visualization_type": "text",
        "is_greeting": True,
        "explanation": explanation,
        "business_analysis": business,
        "quick_questions": snapshot.get("quick_questions", []),
        "areas": snapshot.get("areas", []),
        "modules": snapshot.get("modules", []),
        "agent_log": ["Business role probe - schema grounded"],
    }


def _filter_questions_by_module(all_questions: list, prompt: str, modules: list) -> list:
    """
    Filtra las quick questions para mostrar solo las del módulo relevante a la consulta.
    Si no se puede determinar el módulo, devuelve las primeras 4 preguntas generales.
    """
    if not all_questions:
        return []
    
    norm_prompt = _normalize_text(prompt)
    
    # Diccionario de palabras clave por módulo con prioridades
    module_keywords = {
        "VENTAS": {"priority": 10, "keywords": ["venta", "factura", "cliente", "vendedor", "facturacion", "vendido", "vendidos", "vender", "ingreso"]},
        "RRHH": {"priority": 10, "keywords": ["trabajador", "empleado", "nomina", "sueldo", "salario", "cargo", "area", "personal"]},
    }
    
    # Detectar módulos relevantes con scoring
    detected_modules = {}
    for module, config in module_keywords.items():
        matches = [kw for kw in config["keywords"] if kw in norm_prompt]
        if matches:
            detected_modules[module] = {"priority": config["priority"], "matches": len(matches)}
    
    if detected_modules:
        sorted_modules = sorted(detected_modules.items(), key=lambda x: (x[1]["priority"], x[1]["matches"]), reverse=True)
        primary_module = sorted_modules[0][0]
        
        from core.mirror_manager import _CAPABILITY_DOMAINS
        relevant_questions = []
        for domain in _CAPABILITY_DOMAINS:
            if domain["module"] == primary_module:
                relevant_questions.extend(domain.get("quick_questions", []))
        
        if relevant_questions:
            return list(dict.fromkeys(relevant_questions))[:4]
    
    return all_questions[:4]


def _build_capability_response(snapshot: dict, company_label: str) -> dict:
    """Genera respuesta detallada sobre capacidades detectadas en la BD."""
    ready_areas = [area for area in snapshot.get("areas", []) if area.get("status") == "ready"]
    ready_names = [area.get("name", "") for area in ready_areas if area.get("name")]
    
    metrics = snapshot.get("metrics", {})
    entities_count = int(metrics.get("entities_count", 0) or 0)
    
    from core.business_logic import get_business_logic
    business_logic_text = get_business_logic(company_label)

    if ready_names:
        explanation = (
            f"✅ En **{company_label}** el sistema detecta que el **Giro de Negocio** es: **{business_logic_text}**.\n"
            f"Tengo listos estos dominios optimizados: "
            + ", ".join(ready_names)
            + f". Además, puedo acceder a las **{entities_count} entidades** completas de la base para cualquier consulta personalizada. "
        )
    else:
        explanation = (
            f"🔍 La base **{company_label}** está conectada ({entities_count} entidades detectadas). "
            f"¿Qué área te interesa analizar?"
        )

    return {
        "sql": "",
        "visualization_type": "text",
        "explanation": explanation,
        "business_analysis": snapshot.get("summary", ""),
        "quick_questions": snapshot.get("quick_questions", []),
        "areas": snapshot.get("areas", []),
        "modules": snapshot.get("modules", []),
        "agent_log": ["Capability snapshot"],
    }


def _infer_response_status(payload: dict) -> str:
    explanation = _normalize_text(payload.get("explanation", ""))
    rows = payload.get("rows")
    if payload.get("error"):
        return "error"
    if payload.get("is_greeting"):
        return "guardrail"
    if isinstance(rows, list):
        return "success" if rows else "no_data"
    return "success" if payload.get("sql") else "guardrail"


# Campos internos que solo ADMINISTRADOR puede ver: el SQL generado y todo lo
# que explica cómo se calculó una respuesta. Exponerlos a cualquier rol revela
# nombres reales de vistas y tablas (VIS_ALUMNO, tb_cabmov, rol_pago...) y la
# lógica interna del pipeline (poda semántica, vistas de respaldo, etc.).
_CAMPOS_PRIVADOS_SQL = (
    "sql", "agent_log", "business_analysis",
    "pensamiento_analitico", "sql_explanation",
)


def _redactar_campos_privados(payload: dict, current_user: dict) -> dict:
    """
    Quita SQL y trazabilidad del payload para cualquier rol que no sea
    ADMINISTRADOR.

    Bug real (30/08/2026, defecto grave detectado en pruebas): hasta
    esta fecha, CUALQUIER usuario logueado (CONTABILIDAD, RRHH, LOGISTICA,
    Invitado) recibía el SQL completo y el `agent_log` en la respuesta de
    `/query`. El frontend solo OCULTABA la pestaña "SQL"/"Cómo se calculó" con
    CSS — el payload de red seguía trayendo todo, visible con cualquier
    inspector de red del navegador (F12 → Network). Ocultar un botón no es
    control de acceso: el dato tiene que dejar de viajar, no solo dejar de
    mostrarse.

    Se llama SIEMPRE desde `finalize_response`, el único punto por donde
    salen todas las respuestas de `/query` (IA, caché, métricas certificadas,
    guardarraíles) — así que basta este único punto para cubrir el endpoint
    completo, incluido `/query/stream` (que reenvía el mismo payload).
    """
    if str(current_user.get("role") or "").strip().upper() == "ADMINISTRADOR":
        return payload
    resultado = dict(payload)
    for campo in _CAMPOS_PRIVADOS_SQL:
        resultado.pop(campo, None)
    return resultado


def _validar_motor_ia(motor_pedido: str, current_user: dict) -> tuple[str, str | None]:
    """
    Revalida el motor de IA que pidió el cliente contra lo que el backend
    sabe que ese usuario puede usar — mismo principio que
    `_redactar_campos_privados`: el valor que manda el cliente nunca es la
    fuente de verdad de un permiso.

    Devuelve `(motor_validado, advertencia_o_none)`. `motor_validado` es
    `""` (Flash, el default) si el pedido está vacío, no está en el
    catálogo, o el usuario no lo tiene permitido — nunca lanza ni bloquea
    la consulta por esto, solo degrada en silencio (con una línea de
    `agent_log` para quien audite después).
    """
    from main import _modelos_permitidos_de

    pedido = (motor_pedido or "").strip().lower()
    if not pedido:
        return "", None

    permitidos = _modelos_permitidos_de(current_user)
    if pedido in permitidos:
        return pedido, None
    return "", f"⚠️ Motor '{pedido}' no está permitido para este usuario — usando Flash por defecto."


def _safe_record_query_event(event: dict) -> None:
    try:
        record_query_event(event)
    except Exception:
        pass


# ─── Rol INVITADO (rol técnico "GUEST") — Demo Mode ─────────────────────────
#
# Un Invitado nunca se conecta a una base real: no tiene módulos (ver
# security_config.json → roles.GUEST.modules == []). En vez de bloquearlo con
# un error, esta función lo atiende COMPLETA — saludo, solicitud de acceso,
# instrucciones de conexión y cualquier pregunta de negocio — usando el
# dataset de ejemplo en backend/data/demo_dataset.json. Está separada de
# `execute_query` a propósito: así queda claro, con solo leer las primeras
# líneas de la función, que el Invitado no toca connector, esquema ni SQL.
_CTA_INVITADO = [
    "Ver una demostración con datos de ejemplo",
    "Solicitar acceso a datos reales",
    "Conectar mi base de datos",
]


def _construir_datos_demo(prompt: str, dataset: dict) -> dict | None:
    """Arma rows/columns/visualization_type deterministas desde DEMO_DATASET
    para las preguntas típicas del Invitado (incluyendo el botón "Ver una
    demostración..."). Si la pregunta no calza con ningún patrón, retorna
    None y el Invitado sigue viendo solo texto (comportamiento actual)."""
    norm = _normalize_text(prompt)
    ventas = dataset.get("ventas") or []
    compras = dataset.get("compras") or []
    clientes = dataset.get("clientes") or []
    empleados = dataset.get("empleados") or []
    productos = dataset.get("productos") or []

    # Disparador del botón "Ver una demostración con datos de ejemplo":
    # vista por defecto pedida por el usuario — torta de ventas por mes 2026.
    # El resto de tipos de gráfica (barras/línea/área/radar) ya están
    # disponibles en el selector integrado de DataVisualizer.jsx — no hace
    # falta generarlos aparte.
    if "demostracion" in norm or "demostración" in norm:
        return {"columns": ["mes", "total"], "rows": ventas, "visualization_type": "pie"}

    if any(p in norm for p in ("comparar", "comparacion", "versus", " vs ")):
        por_mes = {}
        for v in ventas:
            por_mes.setdefault(v["mes"], {"mes": v["mes"]})["ventas"] = v["total"]
        for c in compras:
            por_mes.setdefault(c["mes"], {"mes": c["mes"]})["compras"] = c["total"]
        return {"columns": ["mes", "ventas", "compras"], "rows": list(por_mes.values()), "visualization_type": "bar"}

    if "cliente" in norm:
        return {"columns": ["nombre", "estado", "ventas_totales", "ultima_compra"], "rows": clientes, "visualization_type": "table"}

    if any(p in norm for p in ("empleado", "nomina", "personal")):
        return {"columns": ["nombre", "cargo", "salario", "departamento"], "rows": empleados, "visualization_type": "table"}

    if "producto" in norm or "catalogo" in norm:
        viz = "bar" if ("top" in norm or "mejor" in norm) else "table"
        return {"columns": ["nombre", "categoria", "precio_unitario", "stock"], "rows": productos, "visualization_type": viz}

    if "compra" in norm and "venta" not in norm:
        return {"columns": ["mes", "total", "cantidad_ordenes", "proveedores_activos"], "rows": compras, "visualization_type": "bar"}

    if any(p in norm for p in ("venta", "ingreso", "factura")):
        viz = "line" if any(p in norm for p in ("tendencia", "evolucion")) else "bar"
        return {"columns": ["mes", "total", "cantidad_facturas", "clientes_activos"], "rows": ventas, "visualization_type": viz}

    return None


_FRASES_SOLICITAR_ACCESO = (
    "solicitar acceso", "quiero acceso", "pedir acceso", "necesito acceso",
    "acceso a datos reales", "dame acceso", "quiero datos reales",
)

_FRASES_CONECTAR_BD = (
    "conectar mi base", "conectar base de datos", "conectar mi bd",
    "conectar bd", "conectar sql", "conectar servidor", "conectar mi propia base",
    "solo sql server", "solo a sql server", "que motor", "que base de datos soporta",
)


def _responder_invitado(req, prompt: str, current_user: dict, finalize_response):
    """Atiende TODA la conversación de un usuario con rol GUEST (Invitado)."""
    from config import DEEPSEEK_API_KEY, DEMO_DATASET, DEMO_DATASET_LOADED
    from core.deepseek_client import DeepSeekClient, _is_greeting

    norm = _normalize_text(prompt)

    if _is_greeting(prompt):
        return finalize_response({
            "explanation": (
                "¡Hola! Soy VicMar Data AI, tu asistente de Inteligencia de Negocios.\n\n"
                "Eres usuario **Invitado** — todavía no tienes una base de datos real conectada.\n\n"
                "🎬 Puedo mostrarte cómo trabajo con una **demostración** (datos de ejemplo, "
                "con gráficos, tablas y análisis — igual que con datos reales).\n\n"
                "📋 También puedes **solicitar acceso** a datos reales, o "
                "🔌 **conectar tu propia base de datos**.\n\n"
                "Elige una opción abajo, o simplemente hazme cualquier pregunta de negocio "
                "(ventas, compras, clientes, empleados...) y te respondo con la demostración."
            ),
            "is_greeting": True,
            "visualization_type": "text",
            "quick_questions": _CTA_INVITADO,
            "agent_log": ["Invitado: bienvenida con opciones de demo/solicitud/conexión"],
        })

    if any(frase in norm for frase in _FRASES_SOLICITAR_ACCESO):
        return finalize_response({
            "explanation": (
                "📋 **Solicitud de acceso a datos reales**\n\n"
                f"Tu usuario es **{current_user.get('sub', '')}**, con rol **Invitado**.\n\n"
                "Para ver datos reales, pide a un administrador que:\n\n"
                "• Entre a **Gestión de Usuarios**\n"
                "• Edite tu cuenta y te asigne un rol con módulos (por ejemplo CONTABILIDAD, "
                "RRHH o ADMINISTRADOR)\n"
                "• O active para ti una conexión en **Bases de Datos**\n\n"
                "Mientras tanto, sigo disponible para mostrarte cómo funciona todo con la demostración."
            ),
            "visualization_type": "text",
            "quick_questions": _CTA_INVITADO,
            "agent_log": ["Invitado: instrucciones de solicitud de acceso"],
        })

    if any(frase in norm for frase in _FRASES_CONECTAR_BD):
        return finalize_response({
            "explanation": (
                "🔌 **Conectar tu base de datos**\n\n"
                "Ve a la sección **Bases de Datos** en el menú lateral. Ahí ingresas el servidor, "
                "usuario y contraseña de tu instancia.\n\n"
                "**¿Solo se puede conectar a SQL Server?** En la práctica, sí: VicMar Data AI está "
                "construido y probado para conectarse a **SQL Server** vía driver ODBC, y es el "
                "único motor que la pantalla de conexión ofrece hoy. El conector interno también "
                "entiende cadenas de conexión de SQLite y PostgreSQL a nivel de código, pero esa "
                "ruta no está expuesta todavía en la interfaz — si tu empresa usa otro motor, "
                "coméntaselo al administrador para evaluar ese caso puntual.\n\n"
                "Mientras conectas tu base, puedo mostrarte la demostración."
            ),
            "visualization_type": "text",
            "quick_questions": _CTA_INVITADO,
            "agent_log": ["Invitado: instrucciones para conectar base de datos"],
        })

    # Cualquier otra pregunta (incluida "ver demostración" o una pregunta de
    # negocio directa) se responde SIEMPRE con el dataset de demostración.
    # Nunca se deja al Invitado sin respuesta.
    if not DEMO_DATASET_LOADED:
        return finalize_response({
            "explanation": (
                "⚠️ La demostración no está disponible en este momento (el dataset de ejemplo "
                "no se pudo cargar). Puedes solicitar acceso a datos reales o conectar tu "
                "propia base de datos mientras tanto."
            ),
            "visualization_type": "text",
            "quick_questions": _CTA_INVITADO,
            "agent_log": ["Invitado: dataset de demostración no disponible"],
        }, status="error")

    historial = "\n".join(f"{m.type}: {m.content}" for m in (req.history or [])[-6:])
    cliente_ia = DeepSeekClient(api_key=DEEPSEEK_API_KEY)
    salida = cliente_ia.responder_demo(question=prompt, dataset=DEMO_DATASET, history=historial)

    datos_demo = _construir_datos_demo(prompt, DEMO_DATASET)
    if datos_demo and datos_demo.get("rows"):
        salida["columns"] = datos_demo["columns"]
        salida["rows"] = datos_demo["rows"]
        salida["visualization_type"] = datos_demo["visualization_type"]

    salida.setdefault("visualization_type", "text")
    salida.setdefault("quick_questions", _CTA_INVITADO)
    salida.setdefault("agent_log", ["Invitado: respuesta sobre dataset de demostración"])
    return finalize_response(salida)


def get_router() -> APIRouter:
    """
    Factory del router.
    Mantiene una sola instancia declarativa para `main.py`.
    """

    @router.post("/query")
    def execute_query(req: QueryRequest, current_user: dict = Depends(get_token_data)):
        """
        ORDEN DE INGENIERÍA: SISTEMA MULTI-TENANT, CACHÉ SEMÁNTICO Y TRADUCTOR HUMANO
        Pipeline principal con arquitectura Stateless.
        """
        started_at = time.perf_counter()
        agent_log: list[str] = []
        query_id = f"qc_{uuid.uuid4().hex[:12]}"
        # Enlazados aquí (antes de definir finalize_response) para que el
        # closure siempre encuentre estos nombres, incluso en los caminos de
        # retorno temprano (ej. capability probe) que aún no llegan al punto
        # donde se resuelve el conector real ni la empresa activa.
        #
        # Bug real (30/08/2026): `selected_company_code` faltaba en esta
        # lista. `finalize_response` la usa en `_safe_record_query_event`, y
        # el rol Invitado (`_responder_invitado`) llama a `finalize_response`
        # ANTES de que la sección "1. ARQUITECTURA STATELESS" la asigne más
        # abajo — así que CUALQUIER mensaje de un usuario Invitado, incluido
        # un simple "hola", crasheaba con
        # "NameError: cannot access free variable 'selected_company_code'".
        # Mismo patrón, misma solución: se enlaza aquí para que el closure
        # nunca dependa de qué camino se tomó para llegar a él.
        connector = None
        active_company_code = ""
        db_label = ""
        selected_company_code = ""
        
        # FunciOn auxiliar para finalizar respuestas de forma consistente
        def finalize_response(
            payload: dict,
            *,
            status: str | None = None,
            bank_id: str = "",
            auto_corrected: bool = False,
            cache_hit: bool = False,
            sql_text: str = "",
            rows_data=None,
            error_msg: str = "",
        ):
            response_payload = dict(payload)
            response_payload.setdefault("query_id", query_id)
            resolved_rows = response_payload.get("rows") if rows_data is None else rows_data
            resolved_status = status or _infer_response_status(response_payload)
            response_payload.setdefault("status", resolved_status)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 1)

            # ── Bloqueo de integridad (Fase 3 — C1, dinámico desde 14/08/2026) ──
            # Se revisa aquí, en el único punto por donde pasan TODAS las
            # respuestas (métrica certificada, caché e IA), para que ninguna
            # ruta pueda entregar un dato de talento humano sin pasar por
            # este control.
            #
            # Antes esto era un interruptor global: si ficha_trabajador o
            # rol_pago aparecían en el SQL, se bloqueaba para TODAS las
            # empresas por igual. Confirmado el 14/08/2026: para AGRINAG
            # (la única empresa cuyos datos SÍ viven en la base "RRHH") el
            # dato es correcto — bloquearlo también ahí era un falso
            # positivo. Ahora se verifica en vivo, por empresa: se lee la
            # definición ACTUAL de la vista y se compara contra la base
            # conectada en este momento (vista_aislada_para_empresa). Si en
            # el futuro se corrige el SP o se filtra por empresa, el
            # desbloqueo ocurre solo, sin tocar este código.
            sql_para_revisar = sql_text or str(response_payload.get("sql") or "")
            vistas_en_riesgo = vistas_no_aisladas_en_sql(sql_para_revisar)
            if vistas_en_riesgo:
                # Bug real detectado en pruebas internas (28/08/2026): la
                # primera versión de este blindaje bloqueaba con "no pude
                # construir la consulta" CUALQUIER pregunta que tocara una
                # vista de la lista de riesgo (que incluye Ventas, Compras y
                # VIS_ALUMNO, NO solo nómina) en cuanto la pregunta no fuera
                # de nómina — sin comprobar antes si esa vista estaba
                # realmente aislada. Resultado: casi ninguna pregunta de
                # ventas/compras llegaba a responderse, aunque la vista
                # estuviera perfectamente aislada para la empresa activa.
                # El orden correcto es: primero confirmar en vivo cuáles
                # vistas NO están aisladas ahora mismo; si ninguna, no hay
                # nada que bloquear.
                #
                # CAUSA RAÍZ CONFIRMADA (29/08/2026, reportada por el usuario
                # como "la IA no da información"): este chequeo leía la
                # definición de la vista con `target_db=db_label`, y db_label
                # es la base FÍSICA de la empresa (ej. "MONT"), no CHAT — pero
                # las vistas viven en CHAT. execute_query con target_db hace
                # `USE [MONT]`, así que OBJECT_ID('Ventas') devolvía NULL ahí y
                # la vista se marcaba "no aislada" SIEMPRE: la IA generaba bien,
                # ejecutaba bien, obtenía datos reales, y este bloque los tiraba
                # para responder con el aviso pregrabado de sincronización.
                # La verificación debe correr contra CHAT (target_db="CHAT"),
                # igual que _vista_confiable_o_none y mirror_manager. La
                # seguridad NO cambia: si la vista de CHAT apunta a otra empresa
                # (condición de carrera real), sus referencias no son subconjunto
                # de la empresa activa y el bloqueo sigue aplicando.
                no_aisladas = [
                    v for v in vistas_en_riesgo
                    if not vista_aislada_para_empresa(connector, v, active_company_code, target_db="CHAT")
                ]
                if no_aisladas:
                    resolucion = resolver_aviso_integridad(no_aisladas, prompt, active_company_code)
                    logger.warning(
                        "[INTEGRIDAD] Vista(s) no aisladas %s para %s (motivo: %s) — pregunta: %r",
                        no_aisladas, active_company_code, resolucion.get("_motivo_log"), prompt,
                    )
                    response_payload.pop("integrity_warning", None)
                    if "integrity_warning" in resolucion:
                        response_payload["integrity_warning"] = resolucion["integrity_warning"]
                    response_payload["explanation"] = resolucion["explanation"]
                    if "sql" in resolucion:
                        response_payload["sql"] = resolucion["sql"]
                    response_payload["rows"] = []
                    response_payload["columns"] = []
                    response_payload["visualization_type"] = "text"
                    response_payload.pop("business_analysis", None)
                    response_payload["status"] = resolucion["status"]
                    resolved_rows = []

            _safe_record_query_event({
                "query_id": query_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "user_id": user_id,
                "company_code": selected_company_code,
                "prompt": prompt,
                "status": resolved_status,
                "cache_hit": cache_hit,
                "duration_ms": duration_ms,
                "rows_count": len(resolved_rows) if isinstance(resolved_rows, list) else 0,
                "sql_present": bool(sql_text or response_payload.get("sql")),
                "error": error_msg or response_payload.get("error", ""),
            })

            # ── APRENDIZAJE AUTOMÁTICO (memoria de largo plazo por empresa) ──
            # Va aquí, en el mismo embudo por el que salen TODAS las respuestas,
            # para que aprenda igual venga la respuesta de la IA, del caché o de
            # una métrica certificada.
            #
            # Solo se dispara cuando el mensaje del usuario corrige, precisa o
            # instruye (ver core/aprendizaje.py): de una consulta rutinaria
            # respondida y aceptada no sale ninguna regla, y analizarlas todas
            # sería pagar una llamada al modelo por cada pregunta.
            #
            # Corre en un hilo aparte: el usuario ya tiene su respuesta y no
            # debe esperar a que se guarde una nota. Si falla, no afecta nada.
            try:
                if active_company_code and resolved_status != "error":
                    from core.aprendizaje import aprender_en_segundo_plano

                    aprender_en_segundo_plano(
                        active_company_code,
                        prompt,
                        list(req.history or []),
                    )
            except Exception as exc:
                logger.warning("[MEMORIA] Aprendizaje omitido: %s", exc)

            # Blindaje: SQL y trazabilidad son solo para ADMINISTRADOR (ver
            # `_redactar_campos_privados` — es la ÚLTIMA operación antes de
            # devolver el payload, después de que auditoría/aprendizaje ya
            # usaron la versión completa).
            response_payload = _redactar_campos_privados(response_payload, current_user)

            return response_payload

        prompt = req.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="Falta el campo 'prompt'.")

        user_id = current_user.get("sub")
        session = SESSION_STORE.get_session(user_id)
        if not session:
            raise HTTPException(status_code=401, detail="Sesion invalida.")

        # ══════════════════════════════════════════════════════════════════
        # 0. USUARIO INVITADO (rol GUEST) — Demo Mode autocontenido
        # ══════════════════════════════════════════════════════════════════
        # Se intercepta AQUÍ, ANTES de leer `req.selected_company_code` o
        # tocar `session.context_db`/`session.connector`. Es deliberado: un
        # Invitado nunca debe depender de qué empresa haya seleccionada en el
        # navegador para poder usar la demostración.
        #
        # Bug real (30/08/2026): la primera versión de Demo Mode activaba
        # `active_company_code = "DEMO"` a mitad del pipeline, después de la
        # validación de conector. Un `connInfo.selected_company_code` residual
        # en el navegador (de una sesión anterior, de otro usuario, en la
        # MISMA pestaña) se colaba en la petición y desviaba el flujo hacia
        # `_prepare_chat_for_query` contra una empresa real, que fallaba con
        # "Este servidor no cuenta con el módulo de inteligencia activado" —
        # un error técnico sin sentido para alguien que solo quiere ver una
        # demostración. La lección: el modo Invitado no puede compartir NADA
        # del pipeline de conexión real; tiene que ser una rama aparte,
        # completa, resuelta antes de que el resto del código exista.
        #
        # También cumple el requisito: "el mensaje de bloqueo está
        # bien, pero solo debe desactivarse para invitado, que pueda usar el
        # área de consulta" — el Invitado nunca llega a la validación de
        # módulos (2.06) ni a ningún bloqueo: cualquier pregunta que escriba
        # se responde, siempre, con la demostración.
        if str(current_user.get("role") or "").strip().upper() == "GUEST":
            return _responder_invitado(req, prompt, current_user, finalize_response)

        # 1. ARQUITECTURA STATELESS: Identificar base activa
        selected_company_code = (req.selected_company_code or "").strip().upper()
        if not selected_company_code and getattr(session, "context_db", None):
            selected_company_code = str(session.context_db).strip().upper()
        if selected_company_code and selected_company_code != getattr(session, "context_db", ""):
            session.context_db = selected_company_code
            # FASE 3 — C3: reflejar el cambio de empresa en el estado persistido.
            SESSION_STORE.persist(user_id)
        selected_company_name = (req.selected_company_name or "").strip()
        db_label = selected_company_code or getattr(session, "context_db", "") or "CHAT"

        # ── Guardrail: nunca responder con el contexto de conexión "master" ──
        # Auditoría 09/09/2026 — bug real reproducido: el botón "Conectar" del
        # frontend SIEMPRE conecta primero a `master` para poder explorar las
        # bases del servidor (ver DataChannels.jsx::handleConnectButton), y
        # limpia `selected_company_code` a propósito para forzar al usuario a
        # elegir una empresa después. Si el usuario le pregunta algo al chat
        # ANTES de elegir empresa, no había ningún candado: el motor caía a
        # `session.context_db` (= "MASTER", lo último realmente conectado) y
        # respondía con lo que sea que esté visible sin filtrar en CHAT (ej.
        # `dim_estado_matricula`, una tabla compartida) — dando la impresión
        # falsa de que "no hay datos de alumnos" cuando sí los hay, solo que
        # en otra empresa. La IA no estaba mintiendo: respondía bien para un
        # contexto que nunca debió ser el activo.
        if db_label.strip().upper() in ("MASTER", "TEMPDB", "MODEL", "MSDB", ""):
            return finalize_response({
                "explanation": (
                    "Todavía no has seleccionado una empresa. Conectaste al servidor, "
                    "pero para consultar datos reales elige una base desde "
                    "**Orígenes de Datos → Bases Detectadas** (o el Catálogo de empresas) "
                    "y vuelve a preguntar."
                ),
                "visualization_type": "text",
                "agent_log": [f"Guardrail: contexto activo era '{db_label}', no una empresa real"],
            }, status="guardrail", error_msg="NO_COMPANY_SELECTED")

        # ══════════════════════════════════════════════════════════════════
        # 2.0 SEÑA DE DESARROLLADOR ("soy VM") — core/modo_desarrollador.py
        # ══════════════════════════════════════════════════════════════════
        # Va ANTES que todo lo demás (saludos, alcance, probe de capacidades)
        # porque es la única puerta que puede cambiar cómo se atiende el resto
        # del mensaje. El módulo decide si quien escribe tiene derecho a la
        # seña; aquí solo se ejecuta lo que él autorice.
        #
        # Historia: el 30/08/2026 la IA "reconoció" esta seña y prometió
        # privilegios que no existían — era texto del modelo, no una acción del
        # sistema. Además pidió una tabla de la base de datos donde escribir la
        # configuración. El registro vive en un archivo local del backend
        # justamente para no tocar las bases reales de las empresas: este
        # sistema es de SOLO LECTURA sobre ellas, y el modo desarrollador NO
        # cambia eso (sigue vigente el sanitizador que rechaza todo lo que no
        # sea SELECT). Lo único que se levanta es el guardarraíl CONVERSACIONAL.
        from core import modo_desarrollador as dev

        _rol_usuario = str(current_user.get("role") or "")
        _modo_dev = dev.esta_activo(user_id)
        _alias_dev = dev.alias_de(user_id) if _modo_dev else "VM"

        def _responder_libre(texto: str, encabezado: str = ""):
            """Conversación directa con el modelo, sin esquema ni alcance."""
            cliente_ia = getattr(session, "client", None)
            if not cliente_ia:
                # El modo libre no necesita conexión a ninguna empresa: se
                # puede conversar con la IA aunque todavía no se haya
                # seleccionado una base.
                from config import DEEPSEEK_API_KEY
                from core.deepseek_client import DeepSeekClient

                cliente_ia = DeepSeekClient(api_key=DEEPSEEK_API_KEY)

            historial = "\n".join(
                f"{m.type}: {m.content}" for m in (req.history or [])[-6:]
            )
            salida = cliente_ia.chat_libre(
                question=texto,
                history=historial,
                alias=_alias_dev,
                empresa=selected_company_name or selected_company_code or db_label,
            )
            if encabezado:
                salida["explanation"] = f"{encabezado}\n\n---\n\n{salida.get('explanation', '')}"
            salida.setdefault("visualization_type", "text")
            salida["modo_desarrollador"] = True
            return finalize_response(salida)

        # 2.0.a Salida del modo (solo tiene sentido si está activo).
        if _modo_dev and dev.es_frase_de_salida(prompt):
            dev.desactivar(user_id)
            return finalize_response({
                "explanation": (
                    "🔒 **Modo desarrollador cerrado.** Vuelvo al alcance normal: "
                    "solo los datos de la empresa activa.\n\n"
                    "Tu seña sigue registrada — escríbela cuando quieras volver a activarlo."
                ),
                "visualization_type": "text",
                "agent_log": ["Modo desarrollador desactivado por el usuario"],
            })

        # 2.0.b La seña. Si el mensaje trae algo DESPUÉS de ella
        # ("soy VM, explícame el pipeline"), se activa y se responde en el
        # mismo turno en vez de obligar a escribirlo dos veces.
        _es_sena, _resto_sena = dev.detectar_sena(prompt)
        if _es_sena:
            _ok_dev, _mensaje_dev = dev.activar(user_id, _rol_usuario)
            if _ok_dev:
                _modo_dev = True
                _alias_dev = dev.alias_de(user_id)
                if not _resto_sena:
                    return finalize_response({
                        "explanation": _mensaje_dev,
                        "visualization_type": "text",
                        "agent_log": ["Seña de desarrollador reconocida y registrada en disco"],
                    })
                return _responder_libre(_resto_sena, encabezado=_mensaje_dev)
            # Sin derecho a la seña no se delata que exista: el mensaje sigue
            # su curso normal por el pipeline, como cualquier otro texto.

        # 2.0.c Con el modo activo, la conversación libre se usa cuando el
        # usuario lo pide explícitamente ("vm: ...") o cuando el guardarraíl de
        # alcance habría cortado la pregunta. Las preguntas de negocio siguen
        # por el pipeline normal: el valor del sistema son los datos reales, y
        # el modo desarrollador no debe convertir una consulta de ventas en una
        # charla sin cifras.
        if _modo_dev:
            _forzar_libre, _texto_libre = dev.quitar_prefijo_libre(prompt)
            if _forzar_libre:
                return _responder_libre(_texto_libre or prompt)
            from core.alcance import es_fuera_de_alcance as _fuera_alcance_dev

            if _fuera_alcance_dev(prompt):
                return _responder_libre(prompt)

        # 2. SALUDOS DINÁMICOS (Prioridad Alta - No requieren SQL)
        from core.deepseek_client import _is_greeting
        if _is_greeting(prompt):
            # Mostramos el nombre comercial JUNTO al código de base. Antes se
            # mostraba solo uno de los dos, y como el encabezado de la pantalla
            # muestra el otro, el usuario leía "DELPYG S.A." arriba y "ALIM" en
            # el saludo, creyendo razonablemente que eran empresas distintas
            # cuando son la misma. Mostrar ambos elimina esa ambigüedad.
            if selected_company_name and selected_company_code and \
                    selected_company_name.upper() != selected_company_code.upper():
                company_info = f"{selected_company_name} ({selected_company_code})"
            else:
                company_info = selected_company_name or selected_company_code or db_label

            return finalize_response({
                "explanation": f"¡Hola! Soy VicMar Data AI. Estoy conectada a **{company_info}**. ¿Qué datos te gustaría analizar?",
                "is_greeting": True,
                "visualization_type": "text"
            })

        # 2.05 GUARDARRAIL DE ALCANCE (antes que cualquier otro atajo).
        #
        # Va DELIBERADAMENTE antes del probe de capacidades. El probe busca la
        # subcadena "puedo consultar", asi que "¿puedo consultar sobre la guerra
        # de Rusia?" lo disparaba y el sistema contestaba muy amablemente con el
        # catalogo de tablas, sin decir en ningun momento que ese tema no lo
        # cubre. El usuario se quedaba sin la unica respuesta que importaba.
        #
        # Tambien va antes que el catalogo de metricas y que la IA: si el tema
        # es ajeno al negocio, no hay metrica que valga ni token que gastar.
        from core.alcance import (
            es_fuera_de_alcance,
            modulo_no_disponible,
            respuesta_fuera_de_alcance,
            respuesta_modulo_no_disponible,
        )

        _empresa_label = selected_company_name or selected_company_code or db_label
        _esquema = getattr(session, "schema_dict", None)

        if es_fuera_de_alcance(prompt):
            return finalize_response({
                "explanation": respuesta_fuera_de_alcance(
                    _empresa_label, _esquema, semilla=prompt
                ),
                "visualization_type": "text",
                "agent_log": ["Guardarrail de alcance (pregunta fuera del dominio)"],
            })

        # 2.06 VALIDACIÓN DE MÓDULOS — restricción de acceso por rol
        #
        # Si el usuario tiene módulos restringidos (CONTABILIDAD→FINANZAS+VENTAS,
        # RRHH→RRHH, etc.), se detecta si está pidiendo datos de un módulo que
        # NO tiene y se bloquea con una respuesta útil — nunca un error silencioso.
        #
        # El rol GUEST (Invitado) NUNCA llega hasta aquí: se resuelve por
        # completo en `_responder_invitado`, al principio de `execute_query`,
        # así que esta sección solo aplica a roles reales con módulos parciales
        # (CONTABILIDAD, RRHH, LOGISTICA...).
        #
        # El filtrado en el frontend es la primera línea de defensa. Esta
        # validación en el servidor es la segunda línea.

        _modulos_permitidos = current_user.get("modules") or []
        _tiene_restriccion = (
            _rol_usuario.upper() != "ADMINISTRADOR"
            and _modulos_permitidos
            and isinstance(_modulos_permitidos, list)
        )

        if _tiene_restriccion:
            # Intentar detectar qué módulo pide el usuario, con la misma lógica
            # que _filter_questions_by_module. Si lo detecta y NO está permitido,
            # bloquear con una respuesta que enumera qué SÍ puede.
            _norm_prompt = _normalize_text(prompt)
            _modulos_detectados = {}

            # Mapeo de palabras clave a módulos (mismo que en _filter_questions_by_module)
            _keywords_modulo = {
                "RRHH": ["trabajador", "empleado", "nomina", "rol pago", "recurso humano"],
                "FINANZAS": ["asiento", "balance", "contab", "cuenta", "ingreso", "egreso", "flujo caja"],
                "VENTAS": ["venta", "factura", "cliente", "cobro", "pedido"],
                "OPERACIONES": ["compra", "proveedor", "orden", "inventario", "stock", "bodega"],
                "ACADEMICO": ["alumno", "estudiante", "curso", "matricula", "calificacion"],
            }

            for mod, palabras in _keywords_modulo.items():
                if any(p in _norm_prompt for p in palabras):
                    _modulos_detectados[mod] = True

            # Si detectó un módulo y NO está permitido, bloquear
            if _modulos_detectados:
                _modulo_pedido = list(_modulos_detectados.keys())[0]
                if _modulo_pedido not in _modulos_permitidos:
                    _otros_permitidos = ", ".join(_modulos_permitidos) or "ninguno"
                    return finalize_response({
                        "explanation": (
                            f"🔒 **Módulo no permitido para tu rol.**\n\n"
                            f"Tu rol tiene acceso a: **{_otros_permitidos}**.\n"
                            f"La pregunta que hiciste pide datos de **{_modulo_pedido}**, "
                            f"que no aparece en tu lista de permisos.\n\n"
                            f"📌 **Puedes preguntar sobre:**\n"
                            + "\n".join([f"• {m}" for m in _modulos_permitidos])
                            + "\n\n¿Hay algo sobre esos módulos que necesites?"
                        ),
                        "visualization_type": "text",
                        "agent_log": [f"Bloqueo de módulo: pedido {_modulo_pedido}, permitidos {_modulos_permitidos}"],
                    })

        # NOTA (27/08/2026): el aviso de "modulo inexistente en esta base" se
        # movio mas abajo, despues de _prepare_chat_for_query(). Antes usaba
        # `_esquema` = session.schema_dict, que es el esquema RAW de la base
        # fisica de la empresa (capturado en /api/connect y filtrado por
        # schema_resolver.py) — ahi los nombres son tb_cabmov/tb_detmov, no
        # las vistas de CHAT (Ventas, Compras, VIS_ALUMNO...). El guardarraíl
        # comparaba contra ese esquema raw y por eso declaraba a MONT sin
        # modulo de Ventas aunque MONT si factura: la arquitectura real de
        # este sistema es "TODO fluye por SP_MODIFICA_VISTA_IA" (ver mas abajo),
        # asi que el guardarraíl debe usar el MISMO esquema de CHAT que usa la
        # IA para generar el SQL, no un esquema distinto capturado antes.

        # NOTA (30/08/2026 — "expertos me recomendaron
        # que no puede haber respuestas grabadas con mucho tecnicismo,
        # siempre la IA tiene que responder"):
        #
        # Aquí existía un intercepto que, para preguntas tipo "¿qué puedo
        # consultar?", devolvía un texto ARMADO A MANO con f-strings
        # ("En SONG tengo mapeadas 214 entidades. No identifiqué dominios
        # espejo estándar...") en vez de dejar que la IA respondiera. Sonaba
        # a jerga interna del sistema, no a un asistente conversando.
        #
        # `_is_capability_probe()` sigue existiendo (se usa más abajo para
        # otras cosas y tiene sus propias pruebas), pero ya NO corta el flujo
        # aquí: estas preguntas ahora bajan como cualquier otra hasta la
        # generación real con el modelo (sección 5, "GENERACIÓN CON IA"),
        # que ya recibe el esquema real y el bloque `{alcance}` con los
        # módulos disponibles (REGLA 8 del SYSTEM_PROMPT ya cubre
        # explícitamente estas preguntas meta). El mensaje técnico
        # "Tuve un problema técnico al procesar tu pregunta con la IA..."
        # (más abajo, en el manejo de `gen_error`) es el ÚNICO que debe
        # aparecer, y solo si el motor de IA falla de verdad.

        # 3. VALIDACIÓN DE CONECTOR (Necesario para consultas de datos)
        connector = session.connector
        if not connector:
             raise HTTPException(
                 status_code=400, 
                 detail="Enlace de datos no detectado. Por favor, selecciona una empresa en 'Orígenes de Datos' para activar la conexión SQL."
             )

        # ═══════════════════════════════════════════════════════════════════════════════════
        # 🔄 ACTIVACIÓN: Preparar vistas CHAT (SP_MODIFICA_VISTA_IA → SELECT en CHAT)
        # ═══════════════════════════════════════════════════════════════════════════════════
        # ARQUITECTURA DEL INGENIERO: TODO fluye por SP_MODIFICA_VISTA_IA.
        # El SP configura las vistas de CHAT para la empresa seleccionada,
        # y luego la IA genera el SELECT directamente contra esas vistas.
        # db_label SIEMPRE = "CHAT". No hay bypass hacia la BD original.
        from main import _prepare_chat_for_query, execute_chat_query
        active_company_code = selected_company_code or getattr(session, "context_db", "") or (getattr(connector, "database", "") if connector else "") or "CHAT"

        # 2.5 CACHÉ DE RESPUESTA COMPLETA (Redis, aislado por empresa, TTL corto)
        # Clave = pregunta + active_company_code — NUNCA db_label, que casi
        # siempre es el "CHAT" compartido entre todas las empresas. Usar
        # active_company_code es el mismo aislamiento que ya usa SEMANTIC_PROC
        # y evita repetir la fuga de datos entre empresas ya documentada y
        # corregida (incidente de fuga de datos entre empresas del 27/07/2026). En un hit, nos
        # ahorramos incluso la preparación de vistas CHAT y la ida a la BD.
        # Resuelto AQUÍ (antes de cualquier atajo: caché, métrica certificada,
        # banco de preguntas) para poder saltarlos todos cuando el usuario
        # eligió un motor a propósito: elegir un motor debe hacer que ese
        # motor trabaje directo, sin mezclarse (defecto corregido el
        # 30/08/2026: esos atajos ignoraban en silencio el motor elegido).
        _motor_validado, _aviso_motor = _validar_motor_ia(req.motor_ia, current_user)
        if _aviso_motor:
            agent_log.append(_aviso_motor)

        # Memoria propia por motor (30/08/2026): la clave incluye el motor
        # elegido, así que Flash, Pro y cada proveedor nunca se
        # sirven la respuesta cacheada de otro — cada uno tiene su propia
        # memoria persistente. Preguntar lo mismo otro día, con el MISMO
        # motor, responde en segundos sin volver a generar nada; con OTRO
        # motor, no encuentra nada y genera de cero. Sigue siendo la IA la
        # que respondió esa memoria (nunca un texto enlatado): solo se evita
        # regenerar lo que ya se generó antes.
        _clave_motor = _motor_validado or "flash"
        full_cache_hit = get_cached(f"{_clave_motor}::{prompt}", active_company_code)
        if full_cache_hit and isinstance(full_cache_hit, dict) and full_cache_hit.get("rows"):
            agent_log.append("💾 Respuesta completa recuperada de caché (Redis, TTL corto) — sin IA ni consulta a BD")
            return finalize_response(
                dict(full_cache_hit),
                cache_hit=True,
                sql_text=full_cache_hit.get("sql", ""),
                rows_data=full_cache_hit.get("rows"),
            )

        sp_status = "ERROR"
        try:
            chat_schema_dict, chat_schema_text, query_target_db, sp_status = _prepare_chat_for_query(
                connector, active_company_code
            )
            agent_log.append(f"✅ CHAT activado para {active_company_code} — {len(chat_schema_dict)} vistas disponibles (Status: {sp_status})")
        except Exception as e:
            logger.error("[CHAT_SETUP] _prepare_chat_for_query falló: %s", e)
            agent_log.append(f"❌ CHAT no disponible en este servidor")
            return finalize_response({
                "explanation": (
                    "Este servidor no tiene habilitado el módulo de inteligencia de datos. "
                    "Para realizar consultas, por favor selecciona un servidor compatible "
                    "desde la sección **Bases de Datos** e intenta nuevamente."
                ),
                "visualization_type": "text",
                "agent_log": agent_log + ["CHAT no disponible en este servidor"]
            }, status="error", error_msg="CHAT_NOT_AVAILABLE")

        # REGLA DE ORO DE AISLAMIENTO:
        # Si SP_MODIFICA_VISTA_IA falló para esta empresa (sp_status != "OK"), las vistas
        # en CHAT no se reapuntaron. Para garantizar datos 100% reales y aislados,
        # conmutamos el target de consulta directamente a la BD de la empresa.
        use_chat_views = (str(sp_status or "").strip().upper() == "OK")
        if use_chat_views:
            db_label = "CHAT"
            effective_schema = chat_schema_dict
        else:
            # ORDEN ARQUITECTÓNICO (14/08/2026): la ruta correcta es siempre
            # CHAT → vistas. Las vistas ya traen los datos limpios, filtrados
            # por la empresa activa y en pocas entidades — por eso responden
            # rápido. Recorrer tabla por tabla la base física de la empresa NO
            # es una alternativa aceptable: son cientos de tablas con nombres
            # crípticos (tb_cabmov, tb_detmov...), la IA tiene que adivinar
            # relaciones, y el esquema resultante es tan grande que degrada
            # tanto la latencia como la calidad de la respuesta.
            #
            # Antes, si SP_MODIFICA_VISTA_IA no devolvía OK, este bloque hacía
            # get_schema() de TODA la base de la empresa y se lo entregaba a la
            # IA. Ahora se mantienen las vistas de CHAT como esquema (que es lo
            # que la IA sabe consultar) y solo se cambia la base destino a la
            # de la empresa para no arriesgar datos de otra compañía.
            db_label = active_company_code
            agent_log.append(
                f"⚠️ SP_MODIFICA_VISTA_IA no confirmó OK para {active_company_code}. "
                "Se mantienen las vistas de CHAT como esquema y se consulta contra "
                "la base de la empresa para preservar el aislamiento."
            )
            effective_schema = chat_schema_dict or (session.schema_dict or {})

        # 2.06 MODULO INEXISTENTE EN ESTA BASE.
        # Pedir compras en un colegio devolvia "No se encontraron registros",
        # que suena a problema de fechas o de filtros y empuja al usuario a
        # reformular una pregunta que nunca va a tener respuesta. Si el modulo
        # no existe, se dice claro y se ofrece lo que si hay.
        #
        # Usa `effective_schema` (las vistas de CHAT ya activadas arriba por
        # SP_MODIFICA_VISTA_IA para `active_company_code`), NO el esquema raw
        # de la base fisica de la empresa. Bug real (27/08/2026): con el
        # esquema raw, MONT aparecia sin modulo de Ventas porque sus tablas
        # fisicas son tb_cabmov/tb_detmov (sin la palabra "venta" ni
        # "factura"), aunque la vista CHAT.dbo.Ventas si tiene sus datos.
        _modulo_ausente = modulo_no_disponible(prompt, effective_schema)
        if _modulo_ausente:
            return finalize_response({
                "explanation": respuesta_modulo_no_disponible(
                    _modulo_ausente, _empresa_label, effective_schema
                ),
                "visualization_type": "text",
                "agent_log": agent_log + [f"Módulo '{_modulo_ausente}' no existe en la base activa (esquema CHAT)"],
            })

        # 4. CACHÉ SEMÁNTICO (Aislado estrictamente por empresa Y por motor)
        cached_result = SEMANTIC_PROC.get_cached_query(
            prompt, db_label, company_code=active_company_code, motor=_clave_motor
        )
        if cached_result:
            sql_to_run = cached_result["sql"]

            # Blindaje (29/08/2026): defecto detectado en pruebas — un
            # SQL cacheado que usa [Ventas]/[Compras] (nada de nómina) seguía
            # devolviendo el aviso de bloqueo cada vez que se repetía la
            # pregunta, porque esas vistas seguían sin estar aisladas para la
            # empresa activa EN ESE MOMENTO (condición de carrera de CHAT).
            # Sin este chequeo, esa MISMA entrada de caché se queda repitiendo
            # el mismo bloqueo para siempre — nunca se le da a la IA la
            # oportunidad de generar de nuevo con una vista que sí esté
            # disponible ahora. Se descarta el acierto de caché (no se
            # ejecuta ni se muestra) y se cae al flujo normal de generación.
            #
            # Nota (29/08/2026): la "condición de carrera" era el síntoma; la
            # causa raíz de que SIEMPRE se viera como no aislada era el mismo
            # target_db equivocado del bloqueo de finalize_response (se leía
            # OBJECT_DEFINITION en la base física de la empresa, donde la
            # vista de CHAT no existe). Corregido a target_db="CHAT": un SQL
            # cacheado con la vista apuntando a la empresa activa vuelve a
            # acertar, y solo se descarta si HOY apunta realmente a otra parte.
            vistas_riesgo_cache = vistas_no_aisladas_en_sql(sql_to_run)
            cache_comprometido = vistas_riesgo_cache and any(
                not vista_aislada_para_empresa(connector, v, active_company_code, target_db="CHAT")
                for v in vistas_riesgo_cache
            )

            if cache_comprometido:
                agent_log.append(
                    f"SQL de caché toca vista(s) no aisladas ahora mismo ({', '.join(vistas_riesgo_cache)}). "
                    "Descartando este acierto de caché y generando de nuevo con IA..."
                )
            else:
                agent_log.append("Memoria Semántica detectada + CHAT (Zero-LLM latency)")
                cols, rows, err = execute_chat_query(connector, sql_to_run, db_label, empresa=active_company_code)

                if not err:
                    return finalize_response({
                        "sql": sql_to_run,
                        "explanation": cached_result.get("explanation", ""),
                        "visualization_type": cached_result.get("viz_type", "table"),
                        "rows": rows,
                        "columns": cols,
                        "business_analysis": "### Respuesta Optimizada\nRecuperada instantáneamente desde el caché semántico multi-tenant.",
                        "agent_log": agent_log,
                        "answer_source": "cache_semantico",
                    }, cache_hit=True, sql_text=sql_to_run, rows_data=rows)
                else:
                    agent_log.append(f"SQL de caché falló: {err}. Procediendo con IA...")

        # 4.5 MÉTRICAS CERTIFICADAS (Fase 1 — Capa Semántica con Fallback Físico)
        # Se salta si el usuario eligió un motor a propósito: esas fórmulas
        # fijas ignorarían su elección.
        metric_hit = resolver_metrica(prompt) if not _motor_validado else None
        if metric_hit:
            metric_sql = metric_hit["sql"]

            # Bug real (28/08/2026): "total de ventas
            # por meses" y el resto de métricas de ventas/compras fallaban con
            # "objeto no válido" en CUALQUIER empresa que no fuera MONT (y a
            # veces ni en MONT). Causa: el SQL de estas métricas tiene escrito
            # literalmente "cabecera_factura"/"cabecera_compra", pero esas
            # vistas NO EXISTEN hoy en CHAT — confirmado por el usuario con el
            # árbol de vistas real del servidor: lo que existe es "Ventas" y
            # "Compras". CHAT es un namespace compartido por todo el servidor,
            # así que el nombre correcto puede variar con el tiempo — por eso
            # se detecta en vivo en cada consulta (core/vista_resolver.py) en
            # vez de sustituir por otro nombre fijo, que solo movería el mismo
            # problema a la próxima vez que el servidor cambie.
            # Defecto detectado en pruebas (29/08/2026): Indicadores SÍ
            # mostraba Ventas de mayo 2026 para AGGO, pero el chat decía "no
            # encontré una vista de ventas sincronizada" para la MISMA
            # empresa — un experto viendo eso concluye, con razón, que el
            # sistema no funciona. Causa: cuando cabecera_factura/compra
            # existen en CHAT pero esta verificación en vivo no las confirma
            # aisladas para la empresa activa AHORA MISMO (condición de
            # carrera de CHAT, no un problema de la empresa), el chat se
            # rendía y derivaba a la IA sin más. Indicadores (mirror_manager.
            # get_bi_pulse, tarjeta "Balance Comercial") YA resuelve esto
            # exactamente así: cuando la vista de CHAT no es confiable, cae a
            # las tablas FÍSICAS de la propia empresa (tb_cabmov/tb_detmov,
            # el ERP común a todas) en vez de rendirse — y por eso Indicadores
            # "nunca falla". Se replica aquí el mismo criterio: la IA pasa a
            # usar el mismo fallback físico, no otro camino distinto.
            necesita_fallback_fisico = not use_chat_views
            if use_chat_views and db_label.upper() == "CHAT":
                sql_lower = metric_sql.lower()
                if "cabecera_factura" in sql_lower:
                    vista_real = _vista_confiable_o_none(CANDIDATOS_VENTAS, "cabecera_factura", connector, active_company_code)
                    if vista_real:
                        if vista_real.lower() != "cabecera_factura":
                            metric_sql = re.sub(r"\bcabecera_factura\b", vista_real, metric_sql, flags=re.IGNORECASE)
                    else:
                        necesita_fallback_fisico = True
                if "cabecera_compra" in sql_lower:
                    vista_real = _vista_confiable_o_none(CANDIDATOS_COMPRAS, "cabecera_compra", connector, active_company_code)
                    if vista_real:
                        if vista_real.lower() != "cabecera_compra":
                            metric_sql = re.sub(r"\bcabecera_compra\b", vista_real, metric_sql, flags=re.IGNORECASE)
                    else:
                        necesita_fallback_fisico = True

            if necesita_fallback_fisico:
                # Base física destino: la de la empresa activa siempre — si
                # el SP falló globalmente `db_label` YA es esa base; si solo
                # esta vista puntual no es confiable, `db_label` sigue siendo
                # "CHAT" y hay que apuntar a `active_company_code` en su lugar
                # (exactamente como hace Indicadores: nunca las tablas físicas
                # de OTRA empresa).
                db_fisica_fallback = active_company_code if db_label.upper() == "CHAT" else db_label
                if "cabecera_factura" in metric_sql.lower():
                    v1_subquery = f"(SELECT mov_nummov AS NumeroFactura, mov_fecha AS Fecha, det_subtot AS Total, det_nomart AS Producto FROM [{db_fisica_fallback}].[dbo].[tb_cabmov] INNER JOIN [{db_fisica_fallback}].[dbo].[tb_detmov] ON mov_codcia = det_codcia AND mov_nummov = det_cabece WHERE mov_tipo='FA' AND mov_estado<>'AN') AS cabecera_factura"
                    metric_sql = re.sub(r"\bcabecera_factura\b", v1_subquery, metric_sql, flags=re.IGNORECASE)
                # Mismo fallback para compras — antes solo existía para ventas,
                # así que "total de compras por mes" con el SP caído quedaba sin
                # cubrir aunque el caso sea idéntico.
                if "cabecera_compra" in metric_sql.lower():
                    v1_subquery_compra = f"(SELECT mov_nummov AS NumeroFactura, mov_fecha AS Fecha, det_subtot AS Total, det_nomart AS Producto FROM [{db_fisica_fallback}].[dbo].[tb_cabmov] INNER JOIN [{db_fisica_fallback}].[dbo].[tb_detmov] ON mov_codcia = det_codcia AND mov_nummov = det_cabece WHERE mov_tipo='CO' AND mov_estado<>'AN') AS cabecera_compra"
                    metric_sql = re.sub(r"\bcabecera_compra\b", v1_subquery_compra, metric_sql, flags=re.IGNORECASE)
                if use_chat_views and db_label.upper() == "CHAT":
                    agent_log.append(
                        f"Métrica certificada {metric_hit['id']}: la vista de CHAT no está confirmada "
                        f"para la empresa activa ahora mismo — usando tablas físicas de {db_fisica_fallback} "
                        "(mismo criterio que Indicadores, nunca se rinde)."
                    )

            metric_sql, m_valid, m_msg = sanitize_pipeline(
                metric_sql, prompt,
                is_sqlite=getattr(connector, "is_sqlite", False)
            )
            if m_valid:
                m_cols, m_rows, m_err = execute_chat_query(connector, metric_sql, db_label, empresa=active_company_code)
                # Resultado vacío o escalar nulo/cero → esta empresa puede no tener
                # estos datos o usar otras etiquetas. Dejamos que el flujo de IA
                # investigue y construya una narrativa útil, en vez de un "0" seco.
                m_es_vacio = (not m_rows) or (
                    len(m_rows) == 1 and len(m_rows[0]) == 1
                    and (m_rows[0][0] is None or str(m_rows[0][0]).strip() in ("0", "0.0", "0,0", "None", ""))
                )
                if m_err:
                    # Antes este caso no dejaba ningún rastro: si la vista que
                    # usa la métrica no existe en esta empresa (ej. VIS_ALUMNO
                    # fuera de una institución educativa), la métrica fallaba en
                    # silencio y el usuario solo veía el resultado de la IA, sin
                    # forma de saber que una métrica certificada se había caído.
                    agent_log.append(
                        f"Métrica certificada {metric_hit['id']} falló en BD ({m_err}). Derivando a IA."
                    )
                    logger.warning(
                        "[METRICA] '%s' falló para %s: %s", metric_hit["id"], db_label, m_err
                    )
                elif m_es_vacio:
                    agent_log.append(
                        f"Métrica certificada {metric_hit['id']} sin datos en esta empresa. "
                        "Derivando a IA para diagnóstico."
                    )
                else:
                    agent_log.append(
                        f"📌 Métrica certificada: {metric_hit['id']} (afinidad {metric_hit['score']})"
                    )

                    # Por requisito explícito (30/08/2026): el texto
                    # que ve como respuesta NUNCA puede ser la descripción
                    # fija del catálogo repetida siempre igual — eso es
                    # "pregrabado" y ya no está permitido como camino
                    # normal. El SQL sigue siendo el certificado (número
                    # 100% exacto, eso NO cambia); lo que cambia es que la
                    # IA redacta la explicación usando los datos REALES que
                    # esa consulta devolvió. Tope de 8s: si la IA no
                    # responde a tiempo, recién ahí se usa la descripción
                    # fija del catálogo como respaldo — nunca antes.
                    from core.narrativa_rapida import narrar_resultado_rapido, proveedores_desde_config

                    texto_respaldo = (
                        f"📌 **Métrica certificada:** {metric_hit['nombre']}\n\n"
                        f"{metric_hit['descripcion']}"
                    )
                    explicacion_metrica = narrar_resultado_rapido(
                        pregunta=prompt,
                        nombre_metrica=metric_hit["nombre"],
                        columns=m_cols,
                        rows=m_rows,
                        respaldo=texto_respaldo,
                        proveedores=proveedores_desde_config(),
                    )
                    if explicacion_metrica != texto_respaldo:
                        agent_log.append("Explicación redactada por IA sobre datos reales (camino rápido)")

                    return finalize_response({
                        "sql": metric_sql,
                        "columns": m_cols,
                        "rows": m_rows,
                        "explanation": explicacion_metrica,
                        "visualization_type": metric_hit["visualization_type"],
                        # La procedencia (de dónde salió el número, no cómo se
                        # redactó la explicación) vive aquí — en "Cómo se
                        # calculó" — no en la respuesta principal.
                        "business_analysis": (
                            f"### Procedencia del dato\n"
                            f"**{metric_hit['nombre']}** — {metric_hit['descripcion']}\n\n"
                            "Este resultado proviene de una fórmula certificada por el equipo "
                            "(el SQL no lo generó la IA), garantizando exactitud y consistencia."
                        ),
                        "agent_log": agent_log,
                        "answer_source": "metrica_certificada",
                        "metric_id": metric_hit["id"],
                    }, sql_text=metric_sql, rows_data=m_rows)
                agent_log.append(f"Métrica certificada falló en BD ({m_err}). Continuando con IA...")
            else:
                agent_log.append(f"Métrica certificada bloqueada por sanitizador: {m_msg}")

        # 4.7 BANCO DE PREGUNTAS (identidad, seguridad, atajos SQL directos y
        # refuerzo de prompt para consultas gerenciales cotidianas). Corre
        # después de las métricas certificadas —que tienen prioridad
        # absoluta— y antes del traductor humano / generación con IA.
        bank_hit = buscar_en_banco(prompt) if not _motor_validado else None
        bank_prompt_override = None
        if bank_hit and bank_hit.get("bank_hit"):
            bank_id = bank_hit.get("bank_id", "")

            if bank_hit.get("pass_to_ai"):
                # No responde de inmediato: solo mejora la pregunta antes de
                # pasarla al LLM (atajo gerencial cotidiano ya validado).
                if bank_hit.get("rewritten_prompt"):
                    agent_log.append(f"📚 Banco de preguntas: prompt reforzado ({bank_id})")
                    bank_prompt_override = bank_hit["rewritten_prompt"]

            elif bank_hit.get("sql_hint"):
                # Atajo con SQL predefinido: mismo tratamiento que una
                # métrica certificada (sanitizar, ejecutar contra CHAT/BD
                # activa, devolver de inmediato si hay datos reales; si no,
                # dejar que continúe el flujo normal de IA).
                bank_sql = bank_hit["sql_hint"]
                # Mismo criterio que la métrica certificada (ver comentario
                # extenso ahí): si la vista de CHAT no es confiable AHORA
                # MISMO, se cae a las tablas físicas de la empresa activa —
                # igual que Indicadores — en vez de rendirse.
                necesita_fallback_fisico_bank = not use_chat_views
                if use_chat_views and db_label.upper() == "CHAT":
                    sql_lower_bank = bank_sql.lower()
                    if "cabecera_factura" in sql_lower_bank:
                        vista_real = _vista_confiable_o_none(CANDIDATOS_VENTAS, "cabecera_factura", connector, active_company_code)
                        if vista_real:
                            if vista_real.lower() != "cabecera_factura":
                                bank_sql = re.sub(r"\bcabecera_factura\b", vista_real, bank_sql, flags=re.IGNORECASE)
                        else:
                            necesita_fallback_fisico_bank = True
                    if "cabecera_compra" in sql_lower_bank:
                        vista_real = _vista_confiable_o_none(CANDIDATOS_COMPRAS, "cabecera_compra", connector, active_company_code)
                        if vista_real:
                            if vista_real.lower() != "cabecera_compra":
                                bank_sql = re.sub(r"\bcabecera_compra\b", vista_real, bank_sql, flags=re.IGNORECASE)
                        else:
                            necesita_fallback_fisico_bank = True

                if necesita_fallback_fisico_bank:
                    db_fisica_fallback_bank = active_company_code if db_label.upper() == "CHAT" else db_label
                    if "cabecera_factura" in bank_sql.lower():
                        v1_subquery = f"(SELECT mov_nummov AS NumeroFactura, mov_fecha AS Fecha, det_subtot AS Total, det_nomart AS Producto FROM [{db_fisica_fallback_bank}].[dbo].[tb_cabmov] INNER JOIN [{db_fisica_fallback_bank}].[dbo].[tb_detmov] ON mov_codcia = det_codcia AND mov_nummov = det_cabece WHERE mov_tipo='FA' AND mov_estado<>'AN') AS cabecera_factura"
                        bank_sql = re.sub(r"\bcabecera_factura\b", v1_subquery, bank_sql, flags=re.IGNORECASE)
                    if "cabecera_compra" in bank_sql.lower():
                        v1_subquery_compra = f"(SELECT mov_nummov AS NumeroFactura, mov_fecha AS Fecha, det_subtot AS Total, det_nomart AS Producto FROM [{db_fisica_fallback_bank}].[dbo].[tb_cabmov] INNER JOIN [{db_fisica_fallback_bank}].[dbo].[tb_detmov] ON mov_codcia = det_codcia AND mov_nummov = det_cabece WHERE mov_tipo='CO' AND mov_estado<>'AN') AS cabecera_compra"
                        bank_sql = re.sub(r"\bcabecera_compra\b", v1_subquery_compra, bank_sql, flags=re.IGNORECASE)

                bank_sql, b_valid, b_msg = sanitize_pipeline(
                    bank_sql, prompt,
                    is_sqlite=getattr(connector, "is_sqlite", False)
                )
                if b_valid:
                    b_cols, b_rows, b_err = execute_chat_query(connector, bank_sql, db_label, empresa=active_company_code)
                    b_es_vacio = (not b_rows) or (
                        len(b_rows) == 1 and len(b_rows[0]) == 1
                        and (b_rows[0][0] is None or str(b_rows[0][0]).strip() in ("0", "0.0", "0,0", "None", ""))
                    )
                    if not b_err and not b_es_vacio:
                        agent_log.append(f"📚 Banco de preguntas: atajo directo {bank_id}")

                        # Mismo criterio que la métrica certificada: el SQL es
                        # el atajo preconfigurado (número garantizado), pero
                        # el TEXTO lo redacta la IA sobre los datos reales —
                        # nunca la frase fija del banco repetida siempre
                        # igual. Respaldo de 8s si la IA no responde a tiempo.
                        from core.narrativa_rapida import narrar_resultado_rapido, proveedores_desde_config

                        texto_respaldo_bank = bank_hit.get("explanation", "")
                        explicacion_bank = narrar_resultado_rapido(
                            pregunta=prompt,
                            nombre_metrica=bank_id,
                            columns=b_cols,
                            rows=b_rows,
                            respaldo=texto_respaldo_bank,
                            proveedores=proveedores_desde_config(),
                        )
                        if explicacion_bank != texto_respaldo_bank:
                            agent_log.append("Explicación redactada por IA sobre datos reales (camino rápido)")

                        return finalize_response({
                            "sql": bank_sql,
                            "columns": b_cols,
                            "rows": b_rows,
                            "explanation": explicacion_bank,
                            "visualization_type": bank_hit.get("visualization_type", "table"),
                            "business_analysis": (
                                "### Procedencia del dato\n"
                                "Atajo gerencial preconfigurado y verificado por el equipo VicMar Data AI "
                                "(el SQL no lo generó la IA)."
                            ),
                            "agent_log": agent_log,
                            "answer_source": "banco_preguntas",
                            "bank_id": bank_id,
                        }, bank_id=bank_id, sql_text=bank_sql, rows_data=b_rows)
                    if b_err:
                        agent_log.append(f"Banco de preguntas: atajo {bank_id} falló en BD ({b_err}). Continuando con IA...")
                    else:
                        agent_log.append(f"Banco de preguntas: atajo {bank_id} sin datos en esta empresa. Derivando a IA.")
                else:
                    agent_log.append(f"Banco de preguntas: atajo {bank_id} bloqueado por sanitizador: {b_msg}")

            else:
                # Respuesta directa de texto (identidad, seguridad, fuera de alcance).
                agent_log.append(f"📚 Banco de preguntas: respuesta directa {bank_id}")
                return finalize_response({
                    "explanation": bank_hit.get("explanation", ""),
                    "is_greeting": bool(bank_hit.get("is_greeting", True)),
                    "visualization_type": bank_hit.get("visualization_type", "text"),
                    "agent_log": agent_log,
                    "answer_source": "banco_preguntas",
                    "bank_id": bank_id,
                }, bank_id=bank_id)

        # 4. TRADUCTOR HUMANO (Capa Semántica)
        intent_hint = SEMANTIC_PROC.translate_intent(prompt)
        prompt_for_ai = bank_prompt_override or prompt
        if intent_hint:
            agent_log.append(f"Traductor Humano mapeó a: {intent_hint} (NOTE: CHAT schema prioriza vistas actuales)")
            prompt_for_ai = f"(Intención detectada: {intent_hint}). {prompt}"

        # 4.6 PISTAS DE MÉTRICAS PARA EL LLM (si no hubo ejecución directa)
        # Inyectamos las fórmulas certificadas más afines para que el LLM
        # las use en lugar de inventar SQL desde cero.
        metric_hints = hints_para_prompt(prompt)
        if metric_hints:
            agent_log.append("Capa semántica: fórmulas certificadas inyectadas al prompt del LLM")
            prompt_for_ai = f"{prompt_for_ai}\n\n{metric_hints}"

        # 5. GENERACIÓN CON IA (Si no hubo caché)
        client = session.client
        # NOTA: effective_schema ya fue establecido desde CHAT en paso 3, no lo sobrescribimos
        # effective_schema se usa para el contexto del IA
        
        if not client:
            raise HTTPException(status_code=400, detail="Cliente IA no disponible para esta empresa.")

        if not effective_schema and connector:
            # Emergency: intentar fetch r\u00e1pido de esquema si a\u00fan no se sincronic\u00f3
            try:
                emergency_schema = connector.get_schema(database_override=db_label, empresa=active_company_code) or {}
                if emergency_schema:
                    effective_schema = emergency_schema
                    session.schema_dict = emergency_schema
                    if not hasattr(session, "schema_cache") or not isinstance(session.schema_cache, dict):
                        session.schema_cache = {}
                    session.schema_cache[db_label.upper()] = emergency_schema
                    agent_log.append("Schema obtenido por fetch de emergencia")
            except Exception as _esc_err:
                agent_log.append(f"Emergency schema fetch fall\u00f3: {_esc_err}")

        if not effective_schema:
            raise HTTPException(status_code=400, detail="Esquema no disponible. Espera un momento y vuelve a intentarlo.")

        # ═══════════════════════════════════════════════════════════════════════════════════
        # ✅ SCHEMA REAL DE CHAT (no plantillas)
        # ═══════════════════════════════════════════════════════════════════════════════════
        # Ahora que CHAT está activado (SP_MODIFICA_VISTA_IA ejecutado),
        # el effective_schema contiene las vistas REALES de CHAT para esta empresa.
        # La IA generará SQL consultando DIRECTAMENTE estas vistas (ej: SELECT * FROM VIS_ALUMNO)
        # NO usa templates precacheadas.
        
        # Preparar schema como contexto para la IA
        if not chat_schema_text:
            schema_entities = list(effective_schema.keys()) if effective_schema else []
            chat_schema_text = f"Vistas CHAT disponibles ({len(schema_entities)}): {', '.join(schema_entities[:15])}"

        agent_log.append(f"📊 Schema de CHAT cargado: {len(effective_schema)} tablas/vistas")
        
        # Pasar schema real (texto + tablas) a la IA
        client.set_schema(chat_schema_text, tables_dict=effective_schema)
        agent_log.append("Schema CHAT activado — IA consultará vistas dinámicas")

        # ── VISTAS REALES DETECTADAS EN VIVO (28/08/2026) ─────────────────────
        # El BI ya detecta en vivo qué vista de CHAT usar (vista_resolver +
        # aislamiento por empresa); el chat (IA generativa) no lo hacía, y por
        # eso la IA inventaba cabecera_factura/cabecera_compra (nombres que ya
        # no existen en el servidor) o usaba tb_cabmov/tb_detmov (lentas o
        # vacías para varias empresas). Se confirma en vivo el nombre REAL y se
        # le pasa por escrito al prompt, igual que el BI.
        _vista_ventas_real = _vista_confiable_o_none(
            CANDIDATOS_VENTAS, "ventas", connector, active_company_code
        )
        _vista_compras_real = _vista_confiable_o_none(
            CANDIDATOS_COMPRAS, "compras", connector, active_company_code
        )
        # Defecto detectado en pruebas (29/08/2026): cuando esta
        # verificación no confirmaba una vista de CHAT, el prompt le decía a
        # la IA "usa solo el esquema disponible" y la dejaba a su suerte —
        # resultado real: "no encontré una vista de ventas sincronizada"
        # mientras Indicadores, para la MISMA empresa y el MISMO momento, sí
        # mostraba el dato (mirror_manager.get_bi_pulse cae a las tablas
        # físicas tb_cabmov/tb_detmov de la propia empresa cuando pasa esto,
        # nunca se rinde). Se le da a la IA esa MISMA subconsulta de
        # respaldo, ya probada, en vez de dejarla reinventar la rueda cada
        # vez — mismo criterio que el fallback ya aplicado a métricas
        # certificadas y banco de preguntas más abajo en este archivo.
        def _subconsulta_fisica_respaldo(tipo_mov: str, alias: str) -> str:
            return (
                f"(SELECT m.mov_nummov AS NumeroFactura, m.mov_fecha AS Fecha, d.det_subtot AS Total, "
                f"d.det_nomart AS Producto FROM [{active_company_code}].[dbo].[tb_cabmov] m "
                f"INNER JOIN [{active_company_code}].[dbo].[tb_detmov] d ON m.mov_codcia = d.det_codcia "
                f"AND m.mov_nummov = d.det_cabece WHERE m.mov_tipo='{tipo_mov}' AND m.mov_estado<>'AN') AS {alias}"
            )

        _lineas_vistas_reales = []
        if _vista_ventas_real:
            _lineas_vistas_reales.append(
                f"- VISTA DE VENTAS confirmada en vivo para {active_company_code}: "
                f"[{_vista_ventas_real}]. Usa SIEMPRE esta vista para ventas/facturación."
            )
        else:
            _lineas_vistas_reales.append(
                f"- No se pudo confirmar en vivo una vista de VENTAS en CHAT para {active_company_code} "
                "ahora mismo (puede ser una activación concurrente de otra empresa). NO respondas que "
                "falta el dato ni inventes un nombre: usa esta subconsulta de respaldo, sobre las tablas "
                f"físicas propias de {active_company_code} (mismo criterio que usa el panel de "
                f"Indicadores en este caso), como si fuera una tabla más: "
                f"{_subconsulta_fisica_respaldo('FA', 'ventas_fisicas')}"
            )
        if _vista_compras_real:
            _lineas_vistas_reales.append(
                f"- VISTA DE COMPRAS confirmada en vivo para {active_company_code}: "
                f"[{_vista_compras_real}]. Usa SIEMPRE esta vista para compras/proveedores."
            )
        else:
            _lineas_vistas_reales.append(
                f"- No se pudo confirmar en vivo una vista de COMPRAS en CHAT para {active_company_code} "
                "ahora mismo. NO respondas que falta el dato ni inventes un nombre: usa esta subconsulta "
                f"de respaldo sobre las tablas físicas propias de {active_company_code}: "
                f"{_subconsulta_fisica_respaldo('CO', 'compras_fisicas')}"
            )
        vistas_reales_txt = (
            "VISTAS/FUENTES CONFIRMADAS PARA ESTA EMPRESA (úsalas, no inventes nombres ni digas que "
            "falta el dato sin antes intentar la subconsulta de respaldo indicada):\n"
            + "\n".join(_lineas_vistas_reales)
        )
        agent_log.append(
            f"🎯 Vistas en vivo para {active_company_code}: "
            f"ventas={_vista_ventas_real or 'N/A'}, compras={_vista_compras_real or 'N/A'}"
        )

        # Historial (últimos 3 mensajes)
        history_lines = []
        for msg in req.history[-3:]:
             history_lines.append(f"{msg.type}: {msg.content}")
        history_text = "\n".join(history_lines)
        # _motor_validado ya se resolvió arriba (antes de los atajos rápidos).

        llm_result, gen_error = client.generate_sql(
            question=prompt_for_ai,
            module=req.module or "GLOBAL",
            context_db=db_label,
            history=history_text,
            # La empresa real, no `db_label`: este ultimo vale "CHAT" para
            # todas (las consultas van contra las vistas de CHAT), asi que la
            # memoria aprendida se indexa por `active_company_code`, igual que
            # el cache semantico y el de respuesta completa.
            company_code=active_company_code,
            # El nombre real de las vistas de ventas/compras, confirmado en
            # vivo para esta empresa (evita que la IA use nombres obsoletos o
            # tablas físicas lentas).
            vistas_reales=vistas_reales_txt,
            modelo_forzado=_motor_validado,
        )

        if gen_error:
            # BUG REAL encontrado el 14/08/2026: este payload solo llevaba "error"
            # (un detalle técnico, nunca mostrado) y ninguna "explanation". Como el
            # endpoint de streaming solo sabe rellenar un mensaje genérico de "sin
            # datos" cuando explanation viene vacía, CUALQUIER fallo del motor IA
            # (timeout, error de red hacia el proveedor, respuesta no parseable,
            # etc.) se disfrazaba de "no se encontraron registros" — indistinguible
            # de una pregunta fuera de alcance o una consulta sin resultados. El
            # usuario no tenía forma de saber que en realidad fue un error técnico.
            #
            # MEJORA (30/08/2026): el error real (p.ej. HTTP 402 "Insufficient
            # Balance") se quedaba solo en el campo `error` del payload, que el
            # frontend jamás muestra — el usuario solo veía el mensaje genérico
            # "Tuve un problema técnico", indistinguible de un fallo de red, y
            # por eso insistía en que "los motores no funcionan" cuando el
            # problema real era la cuenta DeepSeek sin saldo. Se detecta el caso
            # concreto y se le da al usuario la causa real, accionable.
            logger.warning("[AI_ENGINE] generate_sql devolvió error: %s", gen_error)
            _texto_error = str(gen_error)
            _bajo_error = _texto_error.lower()
            if "402" in _texto_error or "insufficient balance" in _bajo_error:
                explicacion_error = (
                    "⚠️ Los motores de IA (Flash/Pro) no pueden responder en este "
                    "momento: la cuenta de DeepSeek no tiene saldo disponible "
                    "(error HTTP 402 Insufficient Balance).\n\n"
                    "No es un problema de tus datos ni de la conexión: es el crédito "
                    "de la cuenta de inteligencia artificial. Pídele al administrador "
                    "recargar la cuenta en https://platform.deepseek.com para que "
                    "Flash y Pro vuelvan a funcionar."
                )
            else:
                explicacion_error = (
                    "Tuve un problema técnico al procesar tu pregunta con la IA "
                    "(no fue por falta de datos). Intenta de nuevo en unos segundos; "
                    "si vuelve a pasar, avísame para revisarlo."
                )
            return finalize_response({
                "error": gen_error,
                "explanation": explicacion_error,
                "visualization_type": "text",
                "agent_log": agent_log + [f"Error del motor IA: {gen_error}"],
            }, status="error", error_msg=str(gen_error))

        sql = llm_result.get("sql", "")
        if not sql:
            # La IA respondió directamente sin SQL (pregunta conversacional, meta o general).
            # Garantizamos que el frontend recibe viz_type y explanation correctos.
            llm_result.setdefault("visualization_type", llm_result.get("viz_type", "text"))
            llm_result.setdefault("visualization_type", "text")
            if not llm_result.get("explanation"):
                llm_result["explanation"] = (
                    "Entendido. ¿Puedes reformular tu pregunta con más detalle? "
                    "Por ejemplo: *'Total de ventas de 2026'* o *'Empleados activos por área'*."
                )
            return finalize_response(llm_result)

        # 5.5 SANITIZACIÓN Y NORMALIZACIÓN (NUEVO: Corrección de espacios y seguridad)
        sql, is_valid, safety_msg = sanitize_pipeline(
            sql, 
            prompt, 
            is_sqlite=getattr(connector, "is_sqlite", False)
        )
        if not is_valid:
             return finalize_response({
                 "explanation": safety_msg,
                 "visualization_type": "text",
                 "agent_log": agent_log + ["Sanitizer: Bloqueo de seguridad o sintaxis"]
             }, status="error")

        # 6. EJECUCIÓN DIRECTA EN CHAT (sin inyección de ADN virtual)
        # ═════════════════════════════════════════════════════════════════════════════════
        # Las vistas CHAT YA contienen toda la lógica. El SQL se ejecuta directamente.
        # No necesitamos inyectar ADN Virtual (eso era para plantillas antiguas).
        final_sql = sql  # El SQL generado por la IA ya está listo para CHAT

        cols, rows, exec_error = execute_chat_query(connector, final_sql, db_label, empresa=active_company_code)

        if exec_error:
            # Intentar autocorrección rápida
            agent_log.append(f"Error ejecución en CHAT (corrigiendo)...")
            correction = client.generate_correction(sql, str(exec_error))
            sql_fixed = correction.get("sql", sql)
            final_sql = sql_fixed  # Sin ADN virtual
            cols, rows, retry_error = execute_chat_query(connector, final_sql, db_label, empresa=active_company_code)

            if retry_error:
                # Restaurar narrativa de negocio
                human_msg = client.generate_error_narrative(prompt_for_ai, str(retry_error))
                return finalize_response({
                    "explanation": human_msg,
                    "visualization_type": "text",
                    "agent_log": agent_log + ["Error humanizado — detalles técnicos omitidos"]
                }, status="no_data")
            agent_log.append("Autocorrección exitosa.")

        # 7. APRENDIZAJE: Guardar en Caché Semántico si fue exitoso
        #
        # Blindaje (28/08/2026): si el SQL toca ESPECÍFICAMENTE
        # ficha_trabajador/rol_pago para una pregunta que no es de nómina, es
        # un SQL mal generado (ver el mismo chequeo en finalize_response) y
        # nunca debe guardarse en caché. Ojo: esto NO debe extenderse a
        # Ventas/Compras/VIS_ALUMNO — esas SÍ son vistas correctas para
        # preguntas de negocio normales (están en la lista de riesgo solo por
        # el problema de aislamiento en vivo de CHAT, no porque su SQL esté
        # mal armado); un primer intento de este blindaje las incluyó por
        # error y eso bloqueaba casi toda pregunta de ventas/compras.
        _vistas_arriesgadas_en_sql = vistas_no_aisladas_en_sql(sql)
        _toca_solo_nomina_fuera_de_tema = (
            bool(_vistas_arriesgadas_en_sql)
            and all(v.lower() in ("ficha_trabajador", "rol_pago") for v in _vistas_arriesgadas_en_sql)
            and not pregunta_es_de_nomina(prompt)
        )
        if rows and not _toca_solo_nomina_fuera_de_tema:
            SEMANTIC_PROC.save_to_cache(
                prompt,
                sql,  # Guardamos el SQL original mapeado a la intención
                llm_result.get("viz_type", "table"),
                llm_result.get("explanation", ""),
                db_label,
                company_code=selected_company_code,  # aísla la entrada por empresa
                motor=_clave_motor,  # y por motor de IA — memoria propia por motor
            )

        # 8. MANEJO DE RESULTADOS VACÍOS O NULOS
        # Consideramos vacío si no hay filas, o si es una consulta escalar con valor Nulo/Cero
        is_empty_scalar = False
        if len(rows) == 1 and len(rows[0]) == 1:
            val = rows[0][0]
            if val is None or str(val).strip() in ('0', '0.0', '0,0', 'None', ''):
                is_empty_scalar = True

        if not rows or is_empty_scalar:
            explanation, business_analysis = _build_no_rows_narrative(prompt, connector, effective_schema)
            return finalize_response({
                "sql": final_sql,
                "columns": cols,
                "rows": rows if not is_empty_scalar else [], # Evitar pasar [None]
                "explanation": explanation,
                "business_analysis": business_analysis,
                "visualization_type": "text",
                "agent_log": agent_log + ["Sin coincidencias de negocio detectadas o resultado nulo"]
            }, status="no_data")

        try:
            # RAZONAMIENTO CONTEXTUAL: Ajustar narrativa segun cantidad real de datos
            explanation = llm_result.get("explanation", "")
            
            # Detectar si el usuario pidio una cantidad especifica (ej: "top 10")
            asked_count_match = re.search(r"\b(10|5|20|ranking)\b", prompt.lower())
            if asked_count_match and len(rows) > 0:
                if len(rows) == 1:
                    prefix = "Solo se encontró **1 registro** en la base de datos que coincide con tu solicitud:\n\n"
                    # Evitar que la IA diga "Aqui esta el ranking de los 10" si solo hay 1
                    explanation = prefix + re.sub(r"(?i)ranking de los \d+|los \d+ productos|los \d+ mejores", "el registro encontrado", explanation)
                elif len(rows) < 10 and "10" in prompt:
                    prefix = f"Se encontraron únicamente **{len(rows)} registros** disponibles para este análisis:\n\n"
                    explanation = prefix + explanation

            # VERIFICACIÓN DE CIFRAS (25/09/2026): la explicación se escribió
            # ANTES de ejecutar el SQL; si cita números que no están en el
            # resultado o marcadores sin rellenar, se redacta de nuevo sobre
            # los datos reales (con datos personales enmascarados). Nunca se
            # muestra una cifra que el resultado no respalda.
            from core.verificador_cifras import cifras_no_respaldadas, resumen_determinista
            _sospechosas = cifras_no_respaldadas(explanation, rows) if rows else []
            if _sospechosas:
                from core.narrativa_rapida import narrar_resultado_rapido, proveedores_desde_config
                agent_log.append(
                    f"La explicación citaba cifras o marcadores no respaldados por el resultado "
                    f"({', '.join(map(str, _sospechosas[:3]))}); se redacta de nuevo sobre los datos reales"
                )
                _respaldo = resumen_determinista(cols, rows)
                explanation = narrar_resultado_rapido(
                    pregunta=prompt, nombre_metrica="Consulta en lenguaje natural", columns=cols, rows=rows,
                    respaldo=_respaldo, proveedores=proveedores_desde_config(),
                )
                if cifras_no_respaldadas(explanation, rows):
                    explanation = _respaldo

            # DETERMINAR VIZ_TYPE CON HEURÍSTICA DE REFUERZO
            viz_type = llm_result.get("viz_type", "table")
            table_keywords = ["tabla", "listado", "detalle", "registros", "muestrame la tabla", "ver tabla", "muéstrame la tabla"]
            if any(tk in prompt.lower() for tk in table_keywords) and rows and len(rows) > 0:
                viz_type = "table"
            elif len(rows) > 1 and viz_type in ["text", "value"]:
                viz_type = "table"

            final_payload = {
                "sql": final_sql,
                "columns": cols,
                "rows": rows,
                "explanation": explanation,
                "visualization_type": viz_type,
                "agent_log": agent_log,
                "business_analysis": llm_result.get("pensamiento_analitico", ""),
                "answer_source": "ia_generativa",
            }

            # 7.5 APRENDIZAJE: guardar la RESPUESTA COMPLETA (no solo el SQL)
            # en el caché de corta duración, para que una repetición exacta
            # de esta pregunta se resuelva sin IA ni BD. Se cachea el payload
            # final (con la narrativa ya ajustada), aislado por empresa.
            try:
                set_cached(
                    f"{_clave_motor}::{prompt}",
                    active_company_code,
                    {k: v for k, v in final_payload.items() if k != "agent_log"},
                    ttl=FULL_RESPONSE_CACHE_TTL,
                )
            except Exception as _cache_err:
                logger.warning("[FULL_RESPONSE_CACHE] No se pudo guardar respuesta completa: %s", _cache_err)

            return finalize_response(final_payload, sql_text=final_sql, rows_data=rows)
        except Exception as e:
            import traceback
            err_details = traceback.format_exc()
            logger.error(f"CRASH en execute_query: {err_details}")
            _log_query_error(
                "execute_query_crash",
                prompt=prompt,
                empresa=selected_company_code,
                detalle=str(e),
                traza=err_details,
            )
            return finalize_response({
                "status": "error",
                "message": f"Error técnico en el motor: {str(e)}",
                "explanation": "El sistema encontró un problema al procesar los resultados. Estamos revisando la conexión.",
                "agent_log": agent_log + ["Crash detectado y capturado"]
            }, status="error")

    # ─── ENDPOINT DE STREAMING (SSE) ────────────────────────────────────────────
    @router.post("/query/stream")
    def execute_query_stream(req: QueryRequest, current_user: dict = Depends(get_token_data)):
        """
        Variante streaming de /query.
        DELEGA al pipeline COMPLETO de execute_query para garantizar 100% de paridad.
        Solo hace streaming de la explanation letra por letra mediante SSE.

        Protocolo SSE:
          - Evento "meta"   → JSON completo con sql, columns, rows, viz_type, etc.
          - Evento "token"  → chunk de texto de la explanation (4 chars)
          - Evento "done"   → señal de fin
          - Evento "error"  → mensaje de error si el pipeline falla

        LATIDO (30/08/2026, arreglo del "techo" de 25s en los 3 motores):
        `execute_query()` es una sola llamada bloqueante — nada llega al
        navegador mientras corre. El navegador corta la conexión si pasa
        INACTIVIDAD_MS (25s) sin recibir NINGÚN byte, así que una pregunta
        que al motor Experto le toma más de eso (perfectamente
        normal en una comparativa compleja) se abortaba SIEMPRE, sin importar
        qué tan bien estuviera funcionando el motor del otro lado — eso era
        el "techo" que reportó el usuario ("Pro tampoco funciona").
        La corrección de fondo, no un parche por modelo: `execute_query` se
        corre en un hilo aparte (es código síncrono, no async) y este
        generador manda un comentario SSE (`: latido`) cada pocos segundos
        MIENTRAS espera — el navegador ve bytes llegar y nunca activa el
        corte por inactividad, sin importar cuánto tarde el motor elegido.
        """

        async def event_generator():
            loop = asyncio.get_event_loop()
            tarea = loop.run_in_executor(None, execute_query, req, current_user)
            while not tarea.done():
                yield ": latido\n\n"
                try:
                    await asyncio.wait_for(asyncio.shield(tarea), timeout=4)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    # El error real se recoge abajo con tarea.result(); aquí
                    # solo se corta el "esperar con latidos" en cuanto la
                    # tarea termina, sea éxito o fallo.
                    break

            try:
                full_result = tarea.result()
            except HTTPException as http_exc:
                yield f"event: error\ndata: {_json.dumps({'message': http_exc.detail}, ensure_ascii=False)}\n\n"
                return
            except Exception as exc:
                # ── Traza persistente del 500 ──────────────────────────────
                # El log de uvicorn vive en la consola del lanzador (oculta),
                # así que un fallo aquí quedaba sin rastro. Se escribe también
                # a debug/query_error.log para poder diagnosticar sin reproducir.
                import traceback as _tb
                _log_query_error(
                    "stream_500",
                    prompt=getattr(req, "prompt", ""),
                    empresa=getattr(req, "selected_company_code", "") or "",
                    detalle=str(exc),
                    traza=_tb.format_exc(),
                )
                yield f"event: error\ndata: {_json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"
                return

            # ── Extraer explanation del resultado ────────────────────────────────
            explanation = (
                full_result.get("explanation") or
                full_result.get("message") or
                ""
            )

            # ── Construir payload meta con TODO el resultado ─────────────────────
            meta = {k: v for k, v in full_result.items() if k != "explanation"}
            yield f"event: meta\ndata: {_json.dumps(meta, ensure_ascii=False, default=str)}\n\n"

            # ── Si no hay explanation, generar mensaje contextual según lo que preguntó ────
            if not explanation:
                rows = full_result.get("rows") or []
                if rows:
                    explanation = f"Se encontraron **{len(rows)}** registros en la consulta."
                elif full_result.get("error"):
                    # Defensa en profundidad (14/08/2026): si en el futuro algún otro
                    # camino del pipeline deja "error" seteado pero olvida rellenar
                    # "explanation" (como pasaba antes aquí mismo), que se note como
                    # error técnico y no como "no hay datos" — evita que un fallo real
                    # del motor IA se disfrace de una consulta legítima sin resultados.
                    explanation = (
                        "⚠️ Tuve un problema técnico procesando esta pregunta. "
                        "Intenta de nuevo en unos segundos."
                    )
                else:
                    # Mensaje contextual según la pregunta
                    norm_empty = (req.prompt or "").strip().lower()
                    if any(w in norm_empty for w in ("grafico", "gráfico", "grafica", "barras", "torta", "lineas")):
                        explanation = "📊 No se encontraron datos suficientes para generar el gráfico solicitado. Prueba ajustando el período o los filtros de la consulta."
                    elif any(w in norm_empty for w in ("muestra", "dame", "necesito", "quiero")):
                        explanation = "🔍 No se encontraron registros para los criterios de tu búsqueda. Intenta reformular la pregunta o ampliar el rango de fechas."
                    else:
                        explanation = "ℹ️ No se identificaron datos disponibles para esta consulta en la empresa activa. Puede que el período no tenga registros o que la pregunta necesite ser reformulada."


            # ── Transmitir explanation letra por letra ────────────────────────────
            chunk_size = 4
            for i in range(0, len(explanation), chunk_size):
                chunk = explanation[i:i + chunk_size]
                yield f"event: token\ndata: {_json.dumps(chunk, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.012)

            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ── FASE 4 — punto 6: análisis de imágenes adjuntas (modelo Vision) ──────
    # Endpoint separado de /query y /query/stream a propósito: una pregunta
    # con imagen no pasa por SQL, esquema, caché semántico ni guardarraíl de
    # alcance — es una conversación directa con el modelo Vision sobre lo que
    # se ve en la imagen. Mezclarlo con el pipeline principal habría obligado
    # a ramificar ese pipeline entero solo para este caso.
    MAX_IMAGENES = 4
    # ~7MB de data URL en base64 ~= 5MB de imagen real; suficiente para una
    # captura de pantalla o foto de un reporte sin abrir la puerta a
    # payloads gigantes que tarden minutos en subir o procesar.
    MAX_TAMANO_IMAGEN_B64 = 7 * 1024 * 1024

    @router.post("/query/vision")
    def execute_vision_query(req: VisionQueryRequest, current_user: dict = Depends(get_token_data)):
        user_id = current_user.get("sub")
        session = SESSION_STORE.get_session(user_id)
        if not session:
            raise HTTPException(status_code=401, detail="Sesion invalida.")

        client = session.client
        if not client:
            raise HTTPException(
                status_code=400,
                detail="No hay una conexión activa. Selecciona una empresa antes de analizar imágenes.",
            )

        imagenes = [img for img in (req.images or []) if isinstance(img, str) and img.startswith("data:image/")]
        if not imagenes:
            raise HTTPException(status_code=400, detail="No se recibió ninguna imagen válida.")
        if len(imagenes) > MAX_IMAGENES:
            raise HTTPException(
                status_code=400,
                detail=f"Máximo {MAX_IMAGENES} imágenes por consulta. Enviaste {len(imagenes)}.",
            )
        for img in imagenes:
            if len(img) > MAX_TAMANO_IMAGEN_B64:
                raise HTTPException(
                    status_code=400,
                    detail="Una de las imágenes es demasiado grande. Prueba con una versión comprimida.",
                )

        query_id = f"qv_{uuid.uuid4().hex[:12]}"
        started_at = time.perf_counter()

        resultado = client.analyze_images(req.prompt, imagenes)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 1)
        return {
            "query_id": query_id,
            "explanation": resultado.get("explanation", ""),
            "visualization_type": resultado.get("visualization_type", "text"),
            "agent_log": resultado.get("agent_log", []),
            "status": "error" if resultado.get("error") else "success",
            "duration_ms": duration_ms,
            "images_count": len(imagenes),
        }

    # ── Voz con FAL AI (ElevenLabs Multilingual v2) ─────────────────────────
    #
    # Activado el 30/08/2026 por requisito explícito, que aceptó la
    # contrapartida de privacidad ya documentada en useLectura.js: el texto
    # que se lee en voz alta puede contener sueldos, totales de ventas o
    # nombres de proveedores, y con este endpoint SÍ sale hacia FAL AI (a
    # diferencia de la voz local del navegador, que nunca sale de la máquina).
    #
    # El backend hace de intermediario solo para no exponer FAL_KEY en el
    # frontend — no procesa el audio, solo reenvía la URL pública que FAL
    # genera. El frontend cae de vuelta a la voz local automáticamente si
    # este endpoint falla o si no hay FAL_KEY configurada (ver useLectura.js).
    @router.post("/query/speak")
    def sintetizar_voz_endpoint(req: SpeakRequest, current_user: dict = Depends(get_token_data)):
        from config import FAL_KEY
        from core.voz_fal import sintetizar_voz

        resultado = sintetizar_voz(req.text, api_key=FAL_KEY, voz=req.voice or "Rachel")
        if not resultado.get("ok"):
            raise HTTPException(status_code=502, detail=resultado.get("error") or "No se pudo generar el audio.")
        return {"audio_url": resultado["audio_url"]}

    # ── Memoria aprendida: consulta y borrado ───────────────────────────────
    # El aprendizaje es automatico, asi que el sistema puede llegar a guardar
    # una regla incorrecta. Sin una forma de ver y quitar lo aprendido, esa
    # regla se aplicaria en silencio a todas las consultas futuras de la
    # empresa y nadie podria saber de donde viene una respuesta rara. Estos
    # dos endpoints son lo que hace auditable la memoria.

    @router.get("/memoria/{empresa}")
    def listar_memoria(empresa: str, current_user: dict = Depends(get_token_data)):
        """Reglas que el sistema aprendio de esa empresa, con su origen y evidencia."""
        from core.memoria_empresa import reglas_de

        _ = current_user
        codigo = (empresa or "").strip().upper()
        reglas = reglas_de(codigo, solo_activas=False)
        return {
            "empresa": codigo,
            "total": len(reglas),
            "reglas": sorted(
                reglas, key=lambda r: r.get("actualizada", ""), reverse=True
            ),
        }

    @router.delete("/memoria/{empresa}/{regla_id}")
    def borrar_regla(
        empresa: str, regla_id: str, current_user: dict = Depends(get_token_data)
    ):
        """Elimina una regla concreta que el sistema aprendio mal."""
        from core.memoria_empresa import olvidar

        _ = current_user
        codigo = (empresa or "").strip().upper()
        if not olvidar(codigo, regla_id):
            raise HTTPException(
                status_code=404,
                detail=f"No existe la regla '{regla_id}' en la memoria de {codigo}.",
            )
        return {"empresa": codigo, "regla_id": regla_id, "eliminada": True}

    return router

