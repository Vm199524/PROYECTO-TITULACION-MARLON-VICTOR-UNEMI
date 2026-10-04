"""
core/question_bank.py - Banco estrategico de preguntas VicMar Data AI.
Centraliza identidad, seguridad y atajos gerenciales de alto uso.
Permite respuestas instantaneas o refuerzo de prompt para NL2SQL.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

SIMILARITY_THRESHOLD = 0.64


DIRECT_SQL_SHORTCUTS: tuple[dict, ...] = (
    {
        "id": "payroll_total_with_contributions",
        "keywords": (
            "cual es el costo total de la nomina del ultimo mes con aportes",
            "nomina del ultimo mes con aportes",
            "costo total de la nomina con aportes",
            "costo total nomina iess",
        ),
        "visualization_type": "value",
        "explanation": (
            "Calculando el costo total consolidado de nomina del ultimo periodo disponible."
        ),
        "sql_hint": (
            "WITH Base AS ("
            "  SELECT "
            "    TRY_CAST(rp.[Año] AS INT) AS anio_num, "
            "    CASE "
            "      WHEN TRY_CAST(rp.[Mes] AS INT) BETWEEN 1 AND 12 THEN TRY_CAST(rp.[Mes] AS INT) "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('ENERO','ENE') THEN 1 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('FEBRERO','FEB') THEN 2 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('MARZO','MAR') THEN 3 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('ABRIL','ABR') THEN 4 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('MAYO','MAY') THEN 5 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('JUNIO','JUN') THEN 6 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('JULIO','JUL') THEN 7 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('AGOSTO','AGO') THEN 8 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('SEPTIEMBRE','SETIEMBRE','SEP','SET') THEN 9 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('OCTUBRE','OCT') THEN 10 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('NOVIEMBRE','NOV') THEN 11 "
            "      WHEN UPPER(LTRIM(RTRIM(CAST(rp.[Mes] AS NVARCHAR(30))))) IN ('DICIEMBRE','DIC') THEN 12 "
            "      ELSE NULL "
            "    END AS mes_num, "
            "    TRY_CAST(rp.[Valor] AS FLOAT) AS valor_num "
            "  FROM rol_pago rp"
            "), "
            "PeriodoObjetivo AS ("
            "  SELECT TOP 1 anio_num, mes_num "
            "  FROM Base "
            "  WHERE anio_num IS NOT NULL AND mes_num IS NOT NULL "
            "  ORDER BY anio_num DESC, mes_num DESC"
            ") "
            "SELECT "
            "  CAST(SUM(CASE WHEN b.valor_num > 0 AND b.Descripcion = 'TOTAL INGRESOS' THEN b.valor_num ELSE 0 END) AS DECIMAL(18,2)) "
            "    AS [Costo Total Nomina con Aportes] "
            "FROM Base b "
            "JOIN PeriodoObjetivo p ON b.anio_num = p.anio_num AND b.mes_num = p.mes_num"
        ),
    },
    {
        "id": "payslip_lowest_salary",
        "keywords": (
            "rol de pago del trabajador con menor sueldo",
            "rol de pago menor sueldo",
            "ficha de pago del trabajador con menor sueldo",
            "payslip menor sueldo",
        ),
        "visualization_type": "payslip",
        "explanation": (
            "Generando rol de pago completo del trabajador con menor sueldo en el periodo mas reciente."
        ),
        "sql_hint": (
            "WITH PeriodoReciente AS ("
            "  SELECT TOP 1 [Año] AS anio, [Mes] AS mes "
            "  FROM rol_pago "
            "  ORDER BY [Año] DESC, [Fecha Inicio] DESC"
            "), "
            "TrabajadorObjetivo AS ("
            "  SELECT TOP 1 rp.[Cedula] AS cedula, pr.anio, pr.mes "
            "  FROM rol_pago rp "
            "  JOIN PeriodoReciente pr ON rp.[Año] = pr.anio AND rp.[Mes] = pr.mes "
            "  ORDER BY TRY_CAST(rp.[Sueldo] AS FLOAT) ASC"
            ") "
            "SELECT rp.* "
            "FROM rol_pago rp "
            "JOIN TrabajadorObjetivo t "
            "  ON rp.[Cedula] = t.cedula AND rp.[Año] = t.anio AND rp.[Mes] = t.mes"
        ),
    },
    {
        "id": "payslip_highest_salary",
        "keywords": (
            "rol de pago del trabajador con mayor sueldo",
            "rol de pago mayor sueldo",
            "ficha de pago del trabajador con mayor sueldo",
            "payslip mayor sueldo",
        ),
        "visualization_type": "payslip",
        "explanation": (
            "Generando rol de pago completo del trabajador con mayor sueldo en el periodo mas reciente."
        ),
        "sql_hint": (
            "WITH PeriodoReciente AS ("
            "  SELECT TOP 1 [Año] AS anio, [Mes] AS mes "
            "  FROM rol_pago "
            "  ORDER BY [Año] DESC, [Fecha Inicio] DESC"
            "), "
            "TrabajadorObjetivo AS ("
            "  SELECT TOP 1 rp.[Cedula] AS cedula, pr.anio, pr.mes "
            "  FROM rol_pago rp "
            "  JOIN PeriodoReciente pr ON rp.[Año] = pr.anio AND rp.[Mes] = pr.mes "
            "  ORDER BY TRY_CAST(rp.[Sueldo] AS FLOAT) DESC"
            ") "
            "SELECT rp.* "
            "FROM rol_pago rp "
            "JOIN TrabajadorObjetivo t "
            "  ON rp.[Cedula] = t.cedula AND rp.[Año] = t.anio AND rp.[Mes] = t.mes"
        ),
    },
)

MONTH_KEYWORDS: dict[int, tuple[str, ...]] = {
    1: ("enero", "ene", "1", "01"),
    2: ("febrero", "feb", "2", "02"),
    3: ("marzo", "mar", "3", "03"),
    4: ("abril", "abr", "4", "04"),
    5: ("mayo", "may", "5", "05"),
    6: ("junio", "jun", "6", "06"),
    7: ("julio", "jul", "7", "07"),
    8: ("agosto", "ago", "8", "08"),
    9: ("septiembre", "setiembre", "sep", "set", "9", "09"),
    10: ("octubre", "oct", "10"),
    11: ("noviembre", "nov", "11"),
    12: ("diciembre", "dic", "12"),
}

MONTH_NUM_TO_NAME: dict[int, str] = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def _extract_year(prompt_norm: str, current_year: int) -> tuple[int, bool]:
    # Priorizamos anio explicito; en su ausencia se usa anio actual.
    # Tambien interpretamos expresiones relativas comunes del negocio.
    year_match = re.search(r"\b(20\d{2})\b", prompt_norm)
    if year_match:
        return int(year_match.group(1)), True
    if "ano pasado" in prompt_norm or "anio pasado" in prompt_norm:
        return current_year - 1, True
    if "este ano" in prompt_norm or "ano actual" in prompt_norm or "anio actual" in prompt_norm:
        return current_year, True
    return current_year, False


def _extract_month(prompt_norm: str) -> tuple[int | None, bool]:
    # Detecta mes por nombre o por numero.
    # Si no aparece, la consulta debe caer al ultimo mes del anio objetivo.
    numeric_match = re.search(r"\bmes\s*(?:de\s*)?(0?[1-9]|1[0-2])\b", prompt_norm)
    if numeric_match:
        return int(numeric_match.group(1)), True

    for month_num, aliases in MONTH_KEYWORDS.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", prompt_norm):
                return month_num, True
    return None, False


def _month_case_sql(column_ref: str = "rp.[Mes]") -> str:
    clean = f"UPPER(LTRIM(RTRIM(CAST({column_ref} AS NVARCHAR(30)))))"
    return (
        "CASE "
        f"WHEN TRY_CAST({column_ref} AS INT) BETWEEN 1 AND 12 THEN TRY_CAST({column_ref} AS INT) "
        f"WHEN {clean} IN ('ENERO','ENE') THEN 1 "
        f"WHEN {clean} IN ('FEBRERO','FEB') THEN 2 "
        f"WHEN {clean} IN ('MARZO','MAR') THEN 3 "
        f"WHEN {clean} IN ('ABRIL','ABR') THEN 4 "
        f"WHEN {clean} IN ('MAYO','MAY') THEN 5 "
        f"WHEN {clean} IN ('JUNIO','JUN') THEN 6 "
        f"WHEN {clean} IN ('JULIO','JUL') THEN 7 "
        f"WHEN {clean} IN ('AGOSTO','AGO') THEN 8 "
        f"WHEN {clean} IN ('SEPTIEMBRE','SETIEMBRE','SEP','SET') THEN 9 "
        f"WHEN {clean} IN ('OCTUBRE','OCT') THEN 10 "
        f"WHEN {clean} IN ('NOVIEMBRE','NOV') THEN 11 "
        f"WHEN {clean} IN ('DICIEMBRE','DIC') THEN 12 "
        "ELSE NULL END"
    )


def _month_name_sql(column_ref: str = "mes_num") -> str:
    return (
        "CASE "
        f"WHEN {column_ref} = 1 THEN 'Enero' "
        f"WHEN {column_ref} = 2 THEN 'Febrero' "
        f"WHEN {column_ref} = 3 THEN 'Marzo' "
        f"WHEN {column_ref} = 4 THEN 'Abril' "
        f"WHEN {column_ref} = 5 THEN 'Mayo' "
        f"WHEN {column_ref} = 6 THEN 'Junio' "
        f"WHEN {column_ref} = 7 THEN 'Julio' "
        f"WHEN {column_ref} = 8 THEN 'Agosto' "
        f"WHEN {column_ref} = 9 THEN 'Septiembre' "
        f"WHEN {column_ref} = 10 THEN 'Octubre' "
        f"WHEN {column_ref} = 11 THEN 'Noviembre' "
        f"WHEN {column_ref} = 12 THEN 'Diciembre' "
        "ELSE '-' END"
    )


def _build_payroll_extreme_shortcut(prompt_norm: str) -> dict | None:
    payroll_scope = any(token in prompt_norm for token in ("rol", "nomina", "pago", "payslip", "ficha"))
    salary_scope = any(token in prompt_norm for token in ("sueldo", "salario", "remuneracion"))
    if not payroll_scope or not salary_scope:
        return None

    is_high = (
        ("mayor" in prompt_norm or "mas alto" in prompt_norm or "maximo" in prompt_norm or "mejor pagado" in prompt_norm)
        and salary_scope
    )
    is_low = (
        ("menor" in prompt_norm or "mas bajo" in prompt_norm or "minimo" in prompt_norm)
        and salary_scope
    )
    if not is_high and not is_low:
        return None

    current_year = datetime.now().year
    target_year, year_explicit = _extract_year(prompt_norm, current_year)
    target_month, month_explicit = _extract_month(prompt_norm)

    month_filter_sql = f"AND b.mes_num = {target_month}" if target_month else ""
    order_sql = "DESC" if is_high else "ASC"
    shortcut_id = "payslip_highest_salary_dynamic" if is_high else "payslip_lowest_salary_dynamic"
    descriptor = "mayor sueldo" if is_high else "menor sueldo"

    if month_explicit:
        period_label = f"{MONTH_NUM_TO_NAME.get(target_month or 0, 'mes')} {target_year}"
    elif year_explicit:
        period_label = f"ultimo mes disponible de {target_year}"
    else:
        period_label = f"ultimo mes del ano actual ({target_year})"

    month_case = _month_case_sql("rp.[Mes]")
    sql_hint = (
        "WITH Base AS ("
        "  SELECT rp.*, "
        "         TRY_CAST(rp.[Sueldo] AS FLOAT) AS sueldo_num, "
        "         TRY_CAST(rp.[Año] AS INT) AS anio_num, "
        f"         {month_case} AS mes_num "
        "  FROM rol_pago rp"
        "), "
        "PeriodoObjetivo AS ("
        "  SELECT TOP 1 b.anio_num, b.mes_num "
        "  FROM Base b "
        f"  WHERE b.anio_num = {target_year} "
        f"    {month_filter_sql} "
        "  ORDER BY b.anio_num DESC, b.mes_num DESC"
        "), "
        "TrabajadorObjetivo AS ("
        "  SELECT TOP 1 b.[Cedula] AS cedula "
        "  FROM Base b "
        "  JOIN PeriodoObjetivo p ON b.anio_num = p.anio_num AND b.mes_num = p.mes_num "
        f"  ORDER BY b.sueldo_num {order_sql}, b.[Cedula]"
        ") "
        "SELECT b.* "
        "FROM Base b "
        "JOIN PeriodoObjetivo p ON b.anio_num = p.anio_num AND b.mes_num = p.mes_num "
        "JOIN TrabajadorObjetivo t ON b.[Cedula] = t.cedula"
    )

    return {
        "bank_hit": True,
        "bank_id": shortcut_id,
        "is_greeting": False,
        "pass_to_ai": False,
        "sql_hint": sql_hint,
        "explanation": (
            f"Generando rol de pago del trabajador con {descriptor} para {period_label}. "
            "Si necesitas otro periodo, indica mes y anio explicitamente."
        ),
        "visualization_type": "payslip",
        "agent_log": [f"Atajo temporal de rol activado: {shortcut_id}"],
        "rows": [],
        "columns": [],
    }


def _normalize(text: str) -> str:
    # Normalizamos para comparar frases sin ruido de acentos o puntuacion.
    # Esto reduce falsos negativos en preguntas cortas del dia a dia.
    text = (text or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _contains_any(prompt: str, keywords: set[str]) -> str | None:
    for keyword in keywords:
        if keyword in prompt:
            return keyword
    return None


SECURITY_BLOCK_KEYWORDS = {
    "contrasena",
    "contrasenas",
    "password",
    "passwords",
    "token",
    "api key",
    "apikey",
    "credenciales",
    "descarga toda la base",
    "dump",
    "backup completo",
    "toda la base de datos",
    "tabla de usuarios",
}

OFF_TOPIC_KEYWORDS = set() # IA LIBRE: Permitir cualquier tema

WHAT_CAN_YOU_DO_PATTERNS = {
    "que sabes hacer",
    "que nomas te puedo preguntar",
    "que puedes hacer",
    "como me ayudas",
    "en que ayudas",
}

WHO_CREATED_YOU_PATTERNS = {
    "quien te creo",
    "de donde sacas la informacion",
    "quien te implemento",
    "de donde obtienes los datos",
}


@dataclass(frozen=True)
class PromptIntent:
    intent_id: str
    module: str
    question: str
    keywords: tuple[str, ...]
    boost: str


# Este bloque define preguntas cortas de alto valor para gerencia.
# Cada entrada genera un "prompt boost" para que NL2SQL responda con cualquier esquema activo.
DAY_TO_DAY_INTENTS: tuple[PromptIntent, ...] = (
    # RRHH / Capital Humano
    PromptIntent(
        "rrhh_001",
        "RRHH",
        "Cual es el headcount activo al dia de hoy?",
        ("headcount activo", "numero de empleados activo", "empleados activos hoy"),
        "Objetivo: contar personal activo. REGLA: Unir siempre con ficha_trabajador para validar estado laboral vigente. VIZ: value. NO usar tabla.",
    ),
    PromptIntent(
        "rrhh_002",
        "RRHH",
        "Top 5 de trabajadores con mayor salario bruto este ano.",
        ("top 5 salario bruto", "mayor salario bruto", "trabajadores con mayor salario"),
        "Objetivo: ranking top 5 por salario bruto. REGLA: Unir obligatoriamente con ficha_trabajador para mostrar Nombres Completos, no solo el ID.",
    ),
    PromptIntent(
        "rrhh_003",
        "RRHH",
        "Costo salarial promedio desglosado por departamento.",
        ("costo salarial promedio por departamento", "salario promedio por departamento"),
        "Objetivo: promedio salarial por departamento. REGLA: Usar nombres de departamento de ficha_trabajador.",
    ),
    PromptIntent(
        "rrhh_004",
        "RRHH",
        "Dias de vacaciones acumuladas y costo mensual asociado.",
        ("vacaciones acumuladas", "vacaciones pendientes costo"),
        "Objetivo: total de dias acumulados. REGLA: Unir con ficha_trabajador para identificar al personal por nombre.",
    ),
    PromptIntent(
        "rrhh_005",
        "RRHH",
        "Indice de rotacion de personal del ultimo trimestre.",
        ("indice de rotacion", "entradas vs salidas trimestre"),
        "Objetivo: calcular rotacion trimestral. REGLA: Comparar altas y bajas registradas en el sistema.",
    ),
    PromptIntent(
        "rrhh_006",
        "RRHH",
        "Reporte de ausentismo y permisos medicos del ultimo ano.",
        ("ausentismo ultimo ano", "permisos medicos", "subsidios medicos"),
        "Objetivo: consolidar ausencias. REGLA: Unir con ficha_trabajador para detallar nombres de empleados ausentes.",
    ),
    PromptIntent(
        "rrhh_007",
        "RRHH",
        "Empleados con mas de 10 anos de antiguedad.",
        ("mas de 10 anos antiguedad", "empleados antiguos"),
        "Objetivo: listar personal antiguo. REGLA: Unir con ficha_trabajador para mostrar nombres y cargo, no solo cedula.",
    ),
    PromptIntent(
        "rrhh_008",
        "RRHH",
        "Provision proyectada para decimotercera y decimocuarta remuneracion.",
        ("provision decimotercera", "provision decimocuarta"),
        "Objetivo: proyectar provision anual usando nomina historica.",
    ),
    PromptIntent(
        "rrhh_009",
        "RRHH",
        "Costo total de nomina con 12.15% de aporte patronal IESS.",
        (
            "nomina con iess patronal 12 15",
            "costo total nomina iess",
            "cual es el costo total de la nomina del ultimo mes con aportes",
            "nomina del ultimo mes con aportes",
            "costo total de la nomina con aportes",
        ),
        (
            "Objetivo: sumar la nomina del ultimo mes disponible mas el aporte patronal legal "
            "IESS del 12.15%. REGLA: usar el periodo mas reciente disponible cuando el usuario "
            "diga 'ultimo mes' o 'mes actual'."
        ),
    ),
    PromptIntent(
        "rrhh_010",
        "RRHH",
        "Comparativo de horas extras y suplementarias mes actual vs anterior.",
        ("horas extras vs mes anterior", "horas suplementarias comparativo"),
        "Objetivo: comparar montos de horas extras. REGLA: Desglosar por departamento de ficha_trabajador.",
    ),
    PromptIntent(
        "rrhh_011",
        "RRHH",
        "Empleados que empiezan a cobrar fondos de reserva este mes.",
        ("fondos de reserva este mes", "cumplen un ano antiguedad"),
        "Objetivo: detectar personal que cumple un año. REGLA: Mostrar nombres completos desde ficha_trabajador.",
    ),
    PromptIntent(
        "rrhh_012",
        "RRHH",
        "Total pagado en actas de finiquito en lo que va del ano.",
        ("actas de finiquito", "liquidaciones y desahucios"),
        "Objetivo: totalizar liquidaciones YTD por salida laboral.",
    ),

    # Compras / Proveedores
    PromptIntent(
        "compras_001",
        "OPERACIONES",
        "Top 10 de proveedores por volumen de compras este ano.",
        ("top 10 proveedores compras", "proveedores por volumen"),
        "Objetivo: ranking top 10 proveedores. REGLA: Unir con tabla de proveedores para mostrar la Razon Social/Nombre.",
    ),
    PromptIntent(
        "compras_002",
        "OPERACIONES",
        "Historial de compras del ultimo mes filtrado por proveedor.",
        ("historial compras ultimo mes", "compras por proveedor"),
        "Objetivo: detalle de compras. REGLA: Incluir nombre del proveedor (Razon Social) y descripciones de items.",
    ),
    PromptIntent(
        "compras_003",
        "OPERACIONES",
        "Ordenes de compra aprobadas con entrega retrasada.",
        ("ordenes aprobadas retrasadas", "oc con entrega retrasada"),
        "Objetivo: identificar deudas de entrega. REGLA: Mostrar nombre del proveedor responsable.",
    ),
    PromptIntent(
        "compras_004",
        "OPERACIONES",
        "Top 10 items con mayor rotacion de compra este ano.",
        ("items mayor rotacion compra", "top productos comprados"),
        "Objetivo: ranking top 10 items. REGLA: Mostrar descripcion completa del producto, no solo codigo.",
    ),
    PromptIntent(
        "inventario_001",
        "OPERACIONES",
        "Listado de productos con stock critico (punto de reorden).",
        (
            "listado de productos con stock critico",
            "stock critico punto de reorden",
            "productos con stock critico",
            "punto de reorden",
            "stock minimo",
        ),
        (
            "Objetivo: listar productos cuyo stock actual sea menor o igual al punto de reorden "
            "o stock minimo. REGLA: priorizar vistas o tablas de inventario/productos; mostrar "
            "nombre o descripcion real del producto, stock actual y punto de reorden. Si el "
            "esquema activo no tiene campos equivalentes a stock actual y punto de reorden, "
            "informar explicitamente que falta sincronizar inventario."
        ),
    ),
    PromptIntent(
        "compras_005",
        "OPERACIONES",
        "Proveedores con mayor deuda a mas de 30 dias.",
        ("proveedores deuda mas de 30 dias", "cuentas por pagar 30 dias"),
        "Objetivo: proveedores con saldos vencidos. REGLA: Mostrar Razon Social (Nombre) del proveedor.",
    ),
    PromptIntent(
        "compras_006",
        "OPERACIONES",
        "Retenciones en la fuente e IVA emitidas este mes.",
        ("retenciones fuente e iva", "retenciones emitidas este mes"),
        "Objetivo: total mensual de retenciones. REGLA: Desglosar por tipo de retencion y proveedor.",
    ),
    PromptIntent(
        "compras_007",
        "OPERACIONES",
        "Compras del mes: IVA 15% vs IVA 0%.",
        ("compras iva 15 vs iva 0", "desglose iva compras"),
        "Objetivo: desglose por tarifa IVA.",
    ),
    PromptIntent(
        "compras_008",
        "OPERACIONES",
        "Porcentaje de compras por importaciones vs proveedores locales.",
        ("importaciones vs proveedores locales", "compras nacionales vs importadas"),
        "Objetivo: participacion porcentual de importaciones.",
    ),
    PromptIntent(
        "compras_009",
        "OPERACIONES",
        "Notas de credito por devoluciones a proveedores del ultimo trimestre.",
        ("notas de credito devoluciones proveedores", "devoluciones ultimo trimestre"),
        "Objetivo: total de devoluciones. REGLA: Mostrar nombre del proveedor y motivo de NC.",
    ),
    PromptIntent(
        "compras_010",
        "OPERACIONES",
        "Ciclo promedio de pago real a proveedores en dias.",
        ("ciclo promedio de pago proveedores", "dias promedio pago proveedor"),
        "Objetivo: dias promedio de pago por proveedor.",
    ),

    # Ventas / Comercial
    PromptIntent(
        "ventas_001",
        "VENTAS",
        "Quien vendio mas este mes?",
        (
            "quien vendio mas este mes",
            "mejor vendedor del mes",
            "vendedor top",
        ),
        "Objetivo: mejor vendedor mensual. REGLA: Unir con vendedores para mostrar el Nombre del Vendedor, no el ID.",
    ),
    PromptIntent(
        "ventas_002",
        "VENTAS",
        "Ventas netas del ultimo mes desglosadas por vendedor.",
        ("ventas netas por vendedor", "desglose ventas por vendedor"),
        "Objetivo: ranking comercial. REGLA: Unir con vendedores para mostrar Nombres completos.",
    ),
    PromptIntent(
        "ventas_003",
        "VENTAS",
        "Top 10 clientes clave por facturacion acumulada anual.",
        (
            "clientes vip por facturacion",
            "top 10 clientes facturacion",
            "ranking de los 5 mejores clientes por volumen de facturacion",
            "mejores clientes por volumen de facturacion",
        ),
        "Objetivo: top 10 clientes. REGLA: Unir obligatoriamente con clientes para mostrar Razon Social/Nombres.",
    ),
    PromptIntent(
        "ventas_004",
        "VENTAS",
        "Comparativa de ventas YoY: trimestre actual vs mismo trimestre del ano pasado.",
        ("comparativa yoy trimestre", "trimestre vs ano pasado"),
        "Objetivo: analisis trimestral YoY.",
    ),
    PromptIntent(
        "ventas_005",
        "VENTAS",
        "Margen de rentabilidad bruta del top 5 de productos.",
        ("margen bruta top 5 productos", "rentabilidad top productos"),
        "Objetivo: rentabilidad bruta top 5. REGLA: Mostrar nombre/descripcion del producto.",
    ),
    PromptIntent(
        "ventas_006",
        "VENTAS",
        "Ranking mensual de cumplimiento de cuotas por vendedor.",
        ("cumplimiento de cuotas por vendedor", "ranking mensual cuotas"),
        "Objetivo: cumplimiento cuotas. REGLA: Unir para mostrar nombre del vendedor.",
    ),
    PromptIntent(
        "ventas_007",
        "VENTAS",
        "Cartera vencida con clientes a mas de 60 y 90 dias.",
        ("cartera vencida 60 90 dias", "clientes deben mas de 60 dias"),
        "Objetivo: cartera vencida. REGLA: Unir con clientes para mostrar Razon Social y contacto.",
    ),
    PromptIntent(
        "ventas_008",
        "VENTAS",
        "Mapa de calor de ventas por provincia.",
        ("mapa de calor ventas por provincia", "ventas por provincia"),
        "Objetivo: ventas por region geografica.",
    ),
    PromptIntent(
        "ventas_009",
        "VENTAS",
        "Porcentaje de facturacion por metodo de pago.",
        ("facturacion transferencia vs credito", "metodo de pago facturacion"),
        "Objetivo: participacion por forma de pago.",
    ),
    PromptIntent(
        "ventas_010",
        "VENTAS",
        "Dinero perdido por cheques protestados o devueltos este mes.",
        ("cheques protestados", "cheques devueltos este mes"),
        "Objetivo: cuantificar cheques protestados. REGLA: Identificar cliente asociado por nombre.",
    ),
    PromptIntent(
        "ventas_011",
        "VENTAS",
        "Impacto total de notas de credito en la facturacion bruta del mes.",
        ("impacto notas de credito en facturacion", "anulaciones descuentos del mes"),
        "Objetivo: medir impacto de NC sobre facturacion bruta.",
    ),

    # Registro academico
    PromptIntent(
        "acad_001",
        "ACADEMICO",
        "Total de alumnos o estudiantes matriculados y activos.",
        ("alumnos activos", "total alumnos", "estudiantes activos", "total estudiantes"),
        "Objetivo: contar poblacion estudiantil activa. REGLA: En MONT usar alu_estado='GE'. En DAUN usar alu_estado=''. No filtrar por periodo a menos que se pida.",
    ),
    PromptIntent(
        "acad_002",
        "ACADEMICO",
        "Cuadro de honor: top 10 alumnos por promedio general.",
        ("cuadro de honor top 10", "mejor promedio general"),
        "Objetivo: ranking top 10 estudiantes. REGLA: Unir con ficha_estudiante para mostrar Nombres Completos.",
    ),
    PromptIntent(
        "acad_003",
        "ACADEMICO",
        "Matriculas de primer ingreso vs reingresos del mes.",
        ("primer ingreso vs reingresos", "matriculas nuevos vs reingresos"),
        "Objetivo: comparar altas de ingreso.",
    ),
    PromptIntent(
        "acad_004",
        "ACADEMICO",
        "Poblacion estudiantil por carrera, facultad o nivel.",
        ("poblacion estudiantil por carrera", "alumnos por facultad"),
        "Objetivo: distribucion de alumnos por carrera.",
    ),
    PromptIntent(
        "acad_005",
        "ACADEMICO",
        "Tasa de desercion comparada con el ciclo anterior.",
        ("tasa de desercion", "desercion ciclo anterior"),
        "Objetivo: variacion de desercion estudiantil.",
    ),
    PromptIntent(
        "acad_006",
        "ACADEMICO",
        "Cartera vencida por pensiones atrasadas mayores a 1 mes.",
        ("cartera vencida pensiones", "pensiones atrasadas"),
        "Objetivo: pensiones vencidas. REGLA: Unir con estudiante para mostrar nombre del representante/alumno.",
    ),
    PromptIntent(
        "acad_007",
        "ACADEMICO",
        "Porcentaje de alumnos con beca y costo total de descuentos.",
        ("porcentaje alumnos con beca", "costo becas y descuentos"),
        "Objetivo: medicion de becas.",
    ),
    PromptIntent(
        "acad_008",
        "ACADEMICO",
        "Distribucion de matriculados por jornada.",
        ("matutina vespertina nocturna online", "jornada de alumnos"),
        "Objetivo: alumnos por jornada.",
    ),
    PromptIntent(
        "acad_009",
        "ACADEMICO",
        "Proyeccion de ingresos por matriculas para el proximo ciclo.",
        ("proyeccion ingresos matriculas", "proximo ciclo academico"),
        "Objetivo: ingresos proyectados ciclo futuro.",
    ),
    PromptIntent(
        "acad_010",
        "ACADEMICO",
        "Alumnos bloqueados por falta de pago o documentos.",
        ("alumnos bloqueados por falta de pago", "falta de documentos"),
        "Objetivo: alumnos bloqueados. REGLA: Mostrar nombres y motivo de bloqueo.",
    ),

    # CEO / bunker ejecutivo
    PromptIntent(
        "ceo_001",
        "FINANZAS",
        "Flujo de caja neto al dia de hoy.",
        ("flujo de caja neto hoy", "cash flow neto hoy"),
        "Objetivo: cash flow diario ingresos-egresos.",
    ),
    PromptIntent(
        "ceo_002",
        "FINANZAS",
        "Resumen ejecutivo mensual: facturado, comprado, nomina y saldo neto.",
        (
            "resumen ejecutivo del mes",
            "total facturado comprado nomina",
            "resumen ejecutivo mensual de ingresos y egresos operativos",
        ),
        "Objetivo: consolidar KPI ejecutivo (Facturado, Comprado, Nomina).",
    ),
    PromptIntent(
        "ceo_003",
        "FINANZAS",
        "Departamento o centro de costos con mayor consumo de presupuesto.",
        ("centro de costos mayor consumo", "departamento consume mayor presupuesto"),
        "Objetivo: centro de costo mayor gasto.",
    ),
    PromptIntent(
        "ceo_004",
        "FINANZAS",
        "Margen de utilidad operativa proyectado al cierre anual.",
        ("utilidad operativa proyectada", "margen cierre del ano"),
        "Objetivo: proyectar margen operativo anual.",
    ),
    PromptIntent(
        "ceo_005",
        "FINANZAS",
        "Cinco KPIs en rojo critico hoy.",
        ("5 kpis en rojo", "indicadores criticos hoy"),
        "Objetivo: detectar desviaciones criticas.",
    ),
    PromptIntent(
        "ceo_006",
        "FINANZAS",
        "Liquidez proyectada para cubrir SRI e impuestos y nomina de la proxima semana.",
        ("liquidez para sri e impuestos", "cubrir nomina proxima semana"),
        "Objetivo: caja disponible vs impuestos y nomina.",
    ),
    PromptIntent(
        "ceo_007",
        "FINANZAS",
        "Ratio de liquidez: cuentas por cobrar 30 dias vs por pagar 30 dias.",
        ("ratio liquidez 30 dias", "cxc vs cxp 30 dias"),
        "Objetivo: razon CxC30/CxP30.",
    ),
    PromptIntent(
        "ceo_008",
        "FINANZAS",
        "Provision del 15% participacion a trabajadores sobre utilidad acumulada.",
        ("provision 15 participacion trabajadores", "participacion trabajadores utilidad"),
        "Objetivo: provision 15% utilidades trabajadores.",
    ),
    PromptIntent(
        "ceo_009",
        "FINANZAS",
        "ICE, IVA y Retenciones: Carga tributaria total estimada del proximo mes.",
        ("carga tributaria estimada proximo mes", "ice iva retenciones"),
        "Objetivo: proyeccion carga tributaria SRI.",
    ),
    PromptIntent(
        "ceo_010",
        "VENTAS",
        "Evolucion del ticket promedio de venta en 6 meses vs inflacion.",
        ("ticket promedio 6 meses", "ticket promedio comparado inflacion"),
        "Objetivo: tendencia de ticket ventas.",
    ),

    # Bonus complejos para pruebas de razonamiento cruzado
    PromptIntent(
        "bonus_001",
        "VENTAS",
        "Cruce vendedores top en facturacion vs notas de credito generadas.",
        ("vendedores top vs notas de credito", "vende mucho pero devuelve mucho"),
        "Objetivo: cruce ventas vs devoluciones. REGLA: Unir para mostrar nombre del vendedor.",
    ),
    PromptIntent(
        "bonus_002",
        "FINANZAS",
        "Proyeccion de saldo si cobran cartera >60 dias y pagan proveedores vencidos.",
        ("si cobran cartera 60 dias y pagan proveedores", "saldo final proyectado"),
        "Objetivo: simulacion flujo de caja optimizado.",
    ),
    PromptIntent(
        "bonus_003",
        "RRHH",
        "Rendimiento de nomina: ventas brutas / costo total nomina con IESS.",
        ("dinero generado por dolar de nomina", "ventas sobre costo nomina iess"),
        "Objetivo: productividad ventas/nomina.",
    ),
    PromptIntent(
        "bonus_004",
        "OPERACIONES",
        "Proveedores con compras >10000 y facturas vencidas >45 dias.",
        ("compras mas de 10000 y deuda mayor 45 dias", "proveedores alto monto y vencidos"),
        "Objetivo: filtrar proveedores riesgo. REGLA: Unir para mostrar Razon Social del proveedor.",
    ),
)


def _intent_score(prompt_norm: str, intent: PromptIntent) -> float:
    score = _ratio(prompt_norm, _normalize(intent.question))
    for keyword in intent.keywords:
        keyword_norm = _normalize(keyword)
        if keyword_norm and keyword_norm in prompt_norm:
            score = max(score, 0.9)
        score = max(score, _ratio(prompt_norm, keyword_norm))
    return score


def _build_boosted_prompt(user_prompt: str, intent: PromptIntent) -> str:
    # El boost transforma preguntas cortas en instruccion analitica precisa.
    # Asi el motor IA responde mejor sobre bases grandes o pequenas sin hardcodear tablas.
    return (
        f"Consulta original del gerente: {user_prompt}\n"
        f"Intencion detectada ({intent.module}): {intent.question}\n"
        f"Instruccion estrategica: {intent.boost}\n"
        "Regla: usar solo entidades disponibles en el esquema activo y mantener SQL read-only."
    )


def buscar_en_banco(user_prompt: str) -> dict | None:
    """
    Retorna:
    - Respuesta directa para identidad/seguridad/off-topic.
    - Prompt reforzado para consultas cotidianas de gerencia.
    - None si no hay match y debe continuar el flujo normal.
    """
    prompt_norm = _normalize(user_prompt)
    if not prompt_norm:
        return None

    payroll_extreme = _build_payroll_extreme_shortcut(prompt_norm)
    if payroll_extreme:
        return payroll_extreme

    if any(
        phrase in prompt_norm
        for phrase in (
            "cual es el volumen total de ventas facturado",
            "volumen total de ventas facturado",
            "ventas facturado este ano",
            "ventas facturado este a o",
        )
    ):
        current_year = datetime.now().year
        return {
            "bank_hit": True,
            "bank_id": "ventas_total_anual",
            "is_greeting": False,
            "pass_to_ai": False,
            "sql_hint": (
                "SELECT "
                "  CAST(SUM(TRY_CAST(Total AS FLOAT)) AS DECIMAL(18,2)) AS [Total Ventas Facturado] "
                "FROM cabecera_factura "
                f"WHERE YEAR(Fecha) = {current_year}"
            ),
            "explanation": f"Calculando el total facturado acumulado de ventas para {current_year}.",
            "visualization_type": "value",
            "agent_log": ["Atajo SQL directo: ventas_total_anual"],
            "rows": [],
            "columns": [],
        }

    if any(
        phrase in prompt_norm
        for phrase in (
            "resumen ejecutivo mensual de ingresos y egresos operativos",
            "resumen ejecutivo del mes",
            "total facturado comprado nomina",
        )
    ):
        payroll_month_case = _month_case_sql("rp.[Mes]")
        payroll_month_name = _month_name_sql("Base.mes_num")
        return {
            "bank_hit": True,
            "bank_id": "ceo_resumen_mensual_operativo",
            "is_greeting": False,
            "pass_to_ai": False,
            "sql_hint": (
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
                "), Base AS ("
                "  SELECT anio, mes_num FROM facturado "
                "  UNION SELECT anio, mes_num FROM comprado "
                "  UNION SELECT anio, mes_num FROM nomina"
                ") "
                "SELECT TOP 12 "
                "  Base.anio AS [Año], "
                f"  {payroll_month_name} AS [Mes], "
                "  ISNULL(f.facturado, 0) AS [Facturado], "
                "  ISNULL(c.comprado, 0) AS [Comprado], "
                "  ISNULL(n.nomina, 0) AS [Nomina], "
                "  ISNULL(f.facturado, 0) - ISNULL(c.comprado, 0) - ISNULL(n.nomina, 0) AS [Saldo Neto] "
                "FROM Base "
                "LEFT JOIN facturado f ON Base.anio = f.anio AND Base.mes_num = f.mes_num "
                "LEFT JOIN comprado c ON Base.anio = c.anio AND Base.mes_num = c.mes_num "
                "LEFT JOIN nomina n ON Base.anio = n.anio AND Base.mes_num = n.mes_num "
                "WHERE Base.anio IS NOT NULL AND Base.mes_num IS NOT NULL "
                "ORDER BY Base.anio DESC, Base.mes_num DESC"
            ),
            "explanation": "Consolidando facturación, compras y nómina por mes para el tablero ejecutivo.",
            "visualization_type": "table",
            "agent_log": ["Atajo SQL directo: ceo_resumen_mensual_operativo"],
            "rows": [],
            "columns": [],
        }

    for shortcut in DIRECT_SQL_SHORTCUTS:
        if any(_normalize(k) in prompt_norm for k in shortcut["keywords"]):
            return {
                "bank_hit": True,
                "bank_id": shortcut["id"],
                "is_greeting": False,
                "pass_to_ai": False,
                "sql_hint": shortcut["sql_hint"],
                "explanation": shortcut["explanation"],
                "visualization_type": shortcut["visualization_type"],
                "agent_log": [f"Atajo SQL directo: {shortcut['id']}"],
                "rows": [],
                "columns": [],
            }

    blocked_keyword = _contains_any(prompt_norm, SECURITY_BLOCK_KEYWORDS)
    if blocked_keyword:
        return {
            "bank_hit": True,
            "bank_id": "shield_security",
            "is_greeting": True,
            "pass_to_ai": False,
            "sql_hint": None,
            "explanation": (
                "Por politicas de seguridad y confidencialidad corporativa, esa accion esta "
                "estrictamente bloqueada. Solo puedo entregar resumenes analiticos y metricas "
                "autorizadas segun tu nivel de acceso. Si requieres una auditoria de base de datos, "
                "por favor contacta al Arquitecto del Sistema o al Administrador de VicMar Data AI."
            ),
            "visualization_type": "text",
            "agent_log": [f"Escudo de seguridad activado: {blocked_keyword}"],
            "rows": [],
            "columns": [],
        }

    if any(p in prompt_norm for p in WHAT_CAN_YOU_DO_PATTERNS):
        return {
            "bank_hit": True,
            "bank_id": "identity_capabilities",
            "is_greeting": True,
            "pass_to_ai": False,
            "sql_hint": None,
            "explanation": (
                "Soy tu asistente financiero y operativo de VicMar Data AI. "
                "Puedo analizar en segundos miles de datos sobre Ventas, Compras, Recursos "
                "Humanos y Registro Academico. Puedes preguntarme cosas como: "
                "'Quien es el mejor vendedor del mes?', 'Cuanto nos deben los clientes?' o "
                "'Cual es el margen de ganancia de nuestros productos?'. "
                "Por donde empezamos?"
            ),
            "visualization_type": "text",
            "agent_log": ["Respuesta de identidad: capacidades"],
            "rows": [],
            "columns": [],
        }

    if any(p in prompt_norm for p in WHO_CREATED_YOU_PATTERNS):
        return {
            "bank_hit": True,
            "bank_id": "identity_origin",
            "is_greeting": True,
            "pass_to_ai": False,
            "sql_hint": None,
            "explanation": (
                "Fui implementado por el equipo de desarrollo de VicMar Data AI. "
                "Toda la informacion que te entrego proviene en tiempo real de la base de datos "
                "oficial y segura de tu empresa. Mis respuestas se basan 100% en los registros "
                "reales de tu operacion."
            ),
            "visualization_type": "text",
            "agent_log": ["Respuesta de identidad: origen"],
            "rows": [],
            "columns": [],
        }

    off_topic = _contains_any(prompt_norm, OFF_TOPIC_KEYWORDS)
    if off_topic:
        return {
            "bank_hit": True,
            "bank_id": "off_topic_guardrail",
            "is_greeting": True,
            "pass_to_ai": False,
            "sql_hint": None,
            "explanation": (
                "Mi base de conocimientos esta estrictamente conectada a los datos de la empresa "
                f"en VicMar Data AI. No tengo informacion sobre {off_topic}. "
                "Te gustaria que revisemos algun reporte de ventas o finanzas?"
            ),
            "visualization_type": "text",
            "agent_log": [f"Tema fuera de alcance detectado: {off_topic}"],
            "rows": [],
            "columns": [],
        }

    best_intent = None
    best_score = 0.0
    for intent in DAY_TO_DAY_INTENTS:
        score = _intent_score(prompt_norm, intent)
        if score > best_score:
            best_score = score
            best_intent = intent

    if best_intent and best_score >= SIMILARITY_THRESHOLD:
        return {
            "bank_hit": True,
            "bank_id": best_intent.intent_id,
            "bank_score": round(best_score, 3),
            "module": best_intent.module,
            "is_greeting": False,
            "pass_to_ai": True,
            "rewritten_prompt": _build_boosted_prompt(user_prompt, best_intent),
            "visualization_type": "table",
            "agent_log": [f"Atajo gerencial activado: {best_intent.intent_id}"],
        }

    return None


def listar_preguntas_por_modulo(modulo: str | None = None) -> list[str]:
    # Esta lista alimenta catálogos de ejemplos en frontend o soporte interno.
    # No ejecuta SQL ni altera el flujo productivo.
    if modulo:
        module_norm = (modulo or "").strip().upper()
        return [
            intent.question
            for intent in DAY_TO_DAY_INTENTS
            if intent.module.upper() == module_norm
        ]
    return [f"[{intent.module}] {intent.question}" for intent in DAY_TO_DAY_INTENTS]


def total_preguntas() -> int:
    return len(DAY_TO_DAY_INTENTS)


def modulos_disponibles() -> list[str]:
    return sorted({intent.module for intent in DAY_TO_DAY_INTENTS})
