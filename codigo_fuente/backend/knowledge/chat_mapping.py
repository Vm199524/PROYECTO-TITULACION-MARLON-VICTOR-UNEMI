"""
Enrutador de contexto semántico del motor NL2SQL.

Reduce el esquema que se entrega al LLM a las tablas o vistas más probables
según las palabras clave de la pregunta: menos contexto, prompts más cortos
y menos confusión entre entidades. Acepta tanto las vistas espejo de CHAT
como las tablas base cuando esas vistas aún no existen.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import unicodedata


def _normalize(value: str) -> str:
    """Pasa a minúsculas, quita tildes y deja solo letras y dígitos, para comparar nombres."""
    raw =unicodedata.normalize("NFD", str(value or "").strip().lower())
    raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in raw if ch.isalnum())


def _find_existing_name(full_schema_dict: dict, candidates: tuple[str, ...]) -> str | None:
    """Devuelve el nombre real del esquema que coincide con algún candidato, o None."""
    candidate_set = {_normalize(name) for name in candidates}
    for schema_name in full_schema_dict:
        if _normalize(schema_name) in candidate_set:
            return schema_name
    return None


# Palabras clave separadas por "|" -> (entidad principal, entidades relacionadas).
# Cada entidad es una tupla de nombres alternativos (vista de CHAT o tabla
# base); se usa el que exista en el esquema conectado.
VIEW_MAP = {
    "trabajador|empleado|personal|staff|funcionario|recurso|cargo|area|departamento|activo|inactivo": (
        ("V_Ficha_Maestra", "ficha_trabajador"),
        [
            ("V_Resumen_Nomina", "rol_pago"),
            ("V_Historial_Novedades", "VIS_HISNOVTRABAJADOR"),
        ],
    ),
    "novedad|vacacion|permiso|ausencia|licencia|historial|dias|falta": (
        ("V_Historial_Novedades", "VIS_HISNOVTRABAJADOR"),
        [("V_Ficha_Maestra", "ficha_trabajador")],
    ),
    "pago|rol|sueldo|salario|nomina|remuner|beneficio|bono|decimo|utilidad|quincenal|mensual|prestamo|anticipo|retencion|descuento|rubro|iess": (
        ("V_Resumen_Nomina", "rol_pago"),
        [("V_Ficha_Maestra", "ficha_trabajador")],
    ),
    "factura|venta|vendedor|cliente|cobro|comercial|nota|credito|debito|ingreso|revenue|facturacion": (
        ("Ventas", "V_Ventas_Cabecera", "cabecera_factura", "facturas", "ventas_cabecera"),
        [
            ("V_Ventas_Detalle", "ventas_detalle", "detalle_factura", "factura_detalle"),
            ("V_Ficha_Maestra", "ficha_trabajador"),
        ],
    ),
    "compra|proveedor|orden|gasto|egreso|adquisicion|suministro|cuentas por pagar": (
        ("Compras", "V_Compras_Cabecera", "cabecera_compra", "compras_cabecera"),
        [
            ("V_Compras_Detalle", "compras_detalle", "detalle_compra"),
            ("V_Inventario_Stock", "inventario", "productos", "items"),
        ],
    ),
    "stock|inventario|existencia|bodega|reorden|minimo|minima|critico": (
        ("V_Inventario_Stock", "inventario", "productos", "producto", "items"),
        [
            ("V_Ventas_Detalle", "ventas_detalle", "detalle_factura"),
            ("V_Compras_Detalle", "compras_detalle", "detalle_compra"),
            ("V_Compras_Cabecera", "cabecera_compra"),
        ],
    ),
    "comparativa|vs|versus|balance|ingresos vs egresos|flujo de caja|rentabilidad|utilidad": (
        ("V_Ventas_Cabecera", "cabecera_factura"),
        [
            ("V_Compras_Cabecera", "cabecera_compra"),
            ("V_Resumen_Nomina", "rol_pago"),
        ],
    ),
    "alumno|estudiante|academico|matricula|calificacion|nota|curso|carrera|grado": (
        ("V_Registro_Academico", "VIS_ALUMNO", "alumnos", "matriculas"),
        [],
    ),
}

# Si ninguna palabra clave coincide se envían estas entidades y, si tampoco
# existen, las primeras _MAX_FALLBACK del esquema. _MAX_TOTAL acota lo que
# llega al LLM.
_FALLBACK_GROUPS = (
    ("Ventas", "V_Ventas_Cabecera", "cabecera_factura", "ventas_cabecera"),
    ("V_Ficha_Maestra", "ficha_trabajador"),
    ("V_Resumen_Nomina", "rol_pago"),
)
_MAX_FALLBACK = 3
_MAX_TOTAL = 6


def get_relevant_schema(question: str, full_schema_dict: dict) -> str:
    """Devuelve como texto compacto solo las tablas o vistas relevantes para la pregunta.

    Busca en la pregunta (en minúsculas) las palabras clave de VIEW_MAP y
    agrega la entidad principal y sus relacionadas que existan en el
    esquema; sin coincidencias, usa las entidades de respaldo. Cada entidad
    se describe con su tipo y sus columnas con tipo de dato.

    Args:
        question: pregunta del usuario.
        full_schema_dict: {nombre: {"type": ..., "columns": [{"name", "type"}]}}.
    """
    q = (question or "").lower()
    matched_views: list[str] = []

    def add_candidate_group(candidates: tuple[str, ...]) -> None:
        resolved = _find_existing_name(full_schema_dict, candidates)
        if resolved and resolved not in matched_views:
            matched_views.append(resolved)

    for pattern, (main_candidates, related_groups) in VIEW_MAP.items():
        keywords = pattern.split("|")
        if any(kw in q for kw in keywords):
            add_candidate_group(main_candidates)
            for related_candidates in related_groups:
                add_candidate_group(related_candidates)

    if not matched_views:
        for group in _FALLBACK_GROUPS:
            add_candidate_group(group)
        if not matched_views:
            matched_views = list(full_schema_dict.keys())[:_MAX_FALLBACK]

    matched_views = matched_views[:_MAX_TOTAL]

    lines = []
    for table_name in sorted(matched_views):
        info = full_schema_dict.get(table_name)
        if not info:
            continue
        obj_type = info.get("type", "VISTA")
        lines.append(f"{obj_type}: {table_name}")
        cols = info.get("columns", [])
        col_strs = [f"{c['name']} ({c['type']})" for c in cols]
        lines.append("Columnas: " + ", ".join(col_strs))
        lines.append("")

    return "\n".join(lines)
