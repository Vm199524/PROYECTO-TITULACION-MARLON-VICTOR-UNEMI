"""
core/excel_exporter.py — Exportación a Excel estructurado y multi-hoja.

ORIGEN
------
Portado desde el proyecto hermano `TripleA_VentasIA` (app/reports/routes.py,
app/erp/queries.py, app/erp/educativo.py) el 28/08/2026, tomando como
referencia ese exportador (5 hojas con formato real: Facturas, Detalle
Items, Productos, Clientes, Cartera) para reemplazar el CSV plano y ambiguo
de Reportes BI por algo equivalente aquí.

Ese proyecto había llegado, de forma independiente, a las MISMAS correcciones
que este backend aplicó el 28/08/2026: consultar la base FÍSICA de la
empresa directamente (nunca las vistas de CHAT, que son un espejo compartido
por todo el servidor y pueden mezclar empresas — la propia razón por la que
`TripleA_VentasIA` dejó de usarlas: "la vista original cruzaba facturas de
SONG contra clientes de MONT"), y convertir `mov_fecha` con
`CAST(... AS date)` en vez de comparar el string crudo ('AAAA/MM/DD' no es
comparable como texto con '-' como separador). Ambos hallazgos ya estaban
aplicados en este backend antes de leer el otro proyecto — coincidencia que
confirma que el diagnóstico de esta sesión fue correcto.

QUÉ EXPORTA
-----------
  1. Facturas       — cabecera con cliente, línea de negocio y totales.
  2. Detalle Items  — cada línea de cada factura (producto, cantidad, precio).
  3. Productos      — ranking de productos con precio máx/mín e ingresos.
  4. Clientes       — historial acumulado por cliente.
  5. Cartera        — SOLO si la empresa es educativa (tb_cabmovT existe):
                       facturado/cobrado/saldo por tipo de rubro (pensión,
                       matrícula, admisión...), igual que en TripleA_VentasIA.

TODO se consulta contra la base física de la empresa (tb_cabmov, tb_detmov,
tb_client, tb_item, tb_linea — el ERP genérico), nunca contra CHAT.
"""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import date, datetime

logger = __import__("logging").getLogger(__name__)

_NOMBRE_DB_VALIDO = re.compile(r"^[A-Za-z0-9_]+$")


def _validar_db(nombre: str) -> str:
    safe = str(nombre or "").strip().upper()
    if not safe or not _NOMBRE_DB_VALIDO.match(safe):
        raise ValueError(f"Nombre de base de datos inválido: {nombre!r}")
    return safe


def _f(valor, default: float = 0.0) -> float:
    try:
        return round(float(valor), 2)
    except (TypeError, ValueError):
        return default


def _fecha_str(v) -> str:
    if not v:
        return ""
    if isinstance(v, (datetime, date)):
        return v.strftime("%d/%m/%Y")
    return str(v)


def _existe_objeto(connector, safe_db: str, nombre_objeto: str) -> bool:
    try:
        _cols, rows, err = connector.execute_query(
            f"SELECT COUNT(*) FROM [{safe_db}].sys.objects "
            f"WHERE name = '{nombre_objeto}' AND type IN ('U', 'V')"
        )
        return not err and bool(rows and rows[0] and rows[0][0])
    except Exception:
        return False


def _rango_fecha_sql(alias_fecha: str, start, end) -> tuple[str, list[str]]:
    clauses = []
    if start:
        clauses.append(f"{alias_fecha} >= '{start}'")
    if end:
        clauses.append(f"{alias_fecha} <= '{end}'")
    return (" AND " + " AND ".join(clauses) if clauses else ""), []


# ─── Consultas contra la base física de la empresa ──────────────────────────

_FECHA = "CAST(m.mov_fecha AS date)"
_VIGENTE = "m.mov_tipo = 'FA' AND m.mov_estado <> 'AN'"


def _consultar_facturas(connector, safe_db: str, start, end, limite: int = 5000) -> list[dict]:
    filtro_fecha, _ = _rango_fecha_sql(_FECHA, start, end)
    sql = (
        f"SELECT TOP {int(limite)} LTRIM(RTRIM(m.mov_numdoc)) AS factura, {_FECHA} AS fecha, "
        "LTRIM(RTRIM(c.cli_nomcom)) AS cliente, LTRIM(RTRIM(c.cli_ruccli)) AS cedula, "
        "COUNT(*) AS lineas, ISNULL(SUM(d.det_subtot), 0) AS total, "
        "ISNULL(SUM(d.det_canti), 0) AS unidades, "
        "MAX(ISNULL(NULLIF(LTRIM(RTRIM(l.lin_nombre)), ''), '')) AS linea "
        f"FROM [{safe_db}].[dbo].[tb_cabmov] m "
        f"INNER JOIN [{safe_db}].[dbo].[tb_client] c ON m.mov_provee = c.cli_codigo "
        f"INNER JOIN [{safe_db}].[dbo].[tb_detmov] d ON m.mov_codcia = d.det_codcia AND m.mov_nummov = d.det_cabece "
        f"LEFT JOIN [{safe_db}].[dbo].[tb_item] i ON d.det_codart = i.ite_codigo "
        f"LEFT JOIN [{safe_db}].[dbo].[tb_linea] l ON i.lin_codigo = l.lin_codigo "
        f"WHERE {_VIGENTE}{filtro_fecha} "
        "GROUP BY m.mov_numdoc, m.mov_fecha, c.cli_nomcom, c.cli_ruccli "
        f"ORDER BY {_FECHA} DESC, m.mov_numdoc DESC"
    )
    _cols, rows, err = connector.execute_query(sql, target_db=safe_db)
    if err:
        logger.warning("[EXCEL_EXPORT] Facturas falló para %s: %s", safe_db, err)
        return []
    return [
        {
            "factura": r[0], "fecha": r[1], "cliente": r[2], "cedula": r[3],
            "lineas": int(r[4] or 0), "total": _f(r[5]), "unidades": _f(r[6]),
            "linea": r[7] or "—",
        }
        for r in rows
    ]


def _consultar_detalle_items(connector, safe_db: str, start, end, limite: int = 20000) -> list[dict]:
    filtro_fecha, _ = _rango_fecha_sql(_FECHA, start, end)
    sql = (
        f"SELECT TOP {int(limite)} LTRIM(RTRIM(m.mov_numdoc)) AS factura, {_FECHA} AS fecha, "
        "LTRIM(RTRIM(c.cli_ruccli)) AS cedula, LTRIM(RTRIM(c.cli_nomcom)) AS cliente, "
        "LTRIM(RTRIM(d.det_nomart)) AS producto, "
        "ISNULL(NULLIF(LTRIM(RTRIM(l.lin_nombre)), ''), '') AS linea, "
        "d.det_preuni AS precio, d.det_canti AS cantidad, d.det_subtot AS total "
        f"FROM [{safe_db}].[dbo].[tb_cabmov] m "
        f"INNER JOIN [{safe_db}].[dbo].[tb_client] c ON m.mov_provee = c.cli_codigo "
        f"INNER JOIN [{safe_db}].[dbo].[tb_detmov] d ON m.mov_codcia = d.det_codcia AND m.mov_nummov = d.det_cabece "
        f"LEFT JOIN [{safe_db}].[dbo].[tb_item] i ON d.det_codart = i.ite_codigo "
        f"LEFT JOIN [{safe_db}].[dbo].[tb_linea] l ON i.lin_codigo = l.lin_codigo "
        f"WHERE {_VIGENTE}{filtro_fecha} "
        f"ORDER BY {_FECHA} DESC, m.mov_numdoc DESC"
    )
    _cols, rows, err = connector.execute_query(sql, target_db=safe_db)
    if err:
        logger.warning("[EXCEL_EXPORT] Detalle Items falló para %s: %s", safe_db, err)
        return []
    return [
        {
            "factura": r[0], "fecha": r[1], "cedula": r[2], "cliente": r[3],
            "producto": r[4], "linea": r[5] or "—", "precio": _f(r[6]),
            "cantidad": _f(r[7]), "total": _f(r[8]),
        }
        for r in rows
    ]


def _consultar_productos(connector, safe_db: str, start, end, limite: int = 2000) -> list[dict]:
    filtro_fecha, _ = _rango_fecha_sql(_FECHA, start, end)
    sql = (
        f"SELECT TOP {int(limite)} LTRIM(RTRIM(d.det_nomart)) AS producto, "
        "MAX(ISNULL(NULLIF(LTRIM(RTRIM(l.lin_nombre)), ''), '')) AS linea, "
        "ISNULL(SUM(d.det_canti), 0) AS unidades, ISNULL(SUM(d.det_subtot), 0) AS ingresos, "
        "MAX(d.det_preuni) AS precio_max, MIN(d.det_preuni) AS precio_min, "
        "COUNT(DISTINCT m.mov_numdoc) AS facturas, "
        f"MAX({_FECHA}) AS ultima "
        f"FROM [{safe_db}].[dbo].[tb_cabmov] m "
        f"INNER JOIN [{safe_db}].[dbo].[tb_detmov] d ON m.mov_codcia = d.det_codcia AND m.mov_nummov = d.det_cabece "
        f"LEFT JOIN [{safe_db}].[dbo].[tb_item] i ON d.det_codart = i.ite_codigo "
        f"LEFT JOIN [{safe_db}].[dbo].[tb_linea] l ON i.lin_codigo = l.lin_codigo "
        f"WHERE {_VIGENTE}{filtro_fecha} "
        "GROUP BY d.det_nomart ORDER BY SUM(d.det_subtot) DESC"
    )
    _cols, rows, err = connector.execute_query(sql, target_db=safe_db)
    if err:
        logger.warning("[EXCEL_EXPORT] Productos falló para %s: %s", safe_db, err)
        return []
    return [
        {
            "name": r[0], "linea": r[1] or "—", "qty": _f(r[2]), "revenue": _f(r[3]),
            "precio_max": _f(r[4]), "precio_min": _f(r[5]), "invoices": int(r[6] or 0),
            "ultima": r[7],
        }
        for r in rows
    ]


def _consultar_clientes(connector, safe_db: str, start, end, limite: int = 3000) -> list[dict]:
    filtro_fecha, _ = _rango_fecha_sql(_FECHA, start, end)
    sql = (
        f"SELECT TOP {int(limite)} LTRIM(RTRIM(c.cli_ruccli)) AS cedula, "
        "MAX(LTRIM(RTRIM(c.cli_nomcom))) AS cliente, "
        "COUNT(DISTINCT m.mov_numdoc) AS facturas, ISNULL(SUM(d.det_subtot), 0) AS total, "
        f"MAX({_FECHA}) AS ultima, MIN({_FECHA}) AS primera "
        f"FROM [{safe_db}].[dbo].[tb_cabmov] m "
        f"INNER JOIN [{safe_db}].[dbo].[tb_client] c ON m.mov_provee = c.cli_codigo "
        f"INNER JOIN [{safe_db}].[dbo].[tb_detmov] d ON m.mov_codcia = d.det_codcia AND m.mov_nummov = d.det_cabece "
        f"WHERE {_VIGENTE}{filtro_fecha} "
        "GROUP BY c.cli_ruccli ORDER BY SUM(d.det_subtot) DESC"
    )
    _cols, rows, err = connector.execute_query(sql, target_db=safe_db)
    if err:
        logger.warning("[EXCEL_EXPORT] Clientes falló para %s: %s", safe_db, err)
        return []
    resultado = []
    for r in rows:
        facturas = int(r[2] or 0)
        total = _f(r[3])
        resultado.append({
            "cedula": r[0], "name": r[1], "invoices": facturas, "total": total,
            "ultima": r[4], "primera": r[5],
            "ticket": round(total / facturas, 2) if facturas else 0.0,
        })
    return resultado


# Nombres legibles de los tipos de rubro que factura un ERP educativo — mismo
# catálogo que TripleA_VentasIA (app/erp/educativo.py::RUBROS).
_RUBROS_EDUCATIVOS = {
    "PEN": "Pensiones", "MAT": "Matrículas", "ADM": "Admisiones",
    "RES": "Reserva de matrícula", "VAR": "Varios", "VAR2": "Varios 2",
}


def _es_educativa(connector, safe_db: str) -> bool:
    """Ídem TripleA_VentasIA::educativo.disponible — requiere AMBAS tablas."""
    return _existe_objeto(connector, safe_db, "edu_alumno") and _existe_objeto(connector, safe_db, "tb_cabmovT")


def _consultar_cartera_por_rubro(connector, safe_db: str) -> list[dict]:
    """
    Facturado/cobrado/saldo por rubro, del período lectivo con más volumen
    (el vigente). Requiere tb_cabmovT + edu_alumno + edu_period; VIS_COBALU es
    opcional — sin ella se informa el facturado con cobrado en 0 (igual que
    TripleA_VentasIA cuando "cobro_disponible" es False).
    """
    hay_cobro = _existe_objeto(connector, safe_db, "VIS_COBALU")
    join_cobro = (
        f"LEFT JOIN [{safe_db}].[dbo].[VIS_COBALU] v "
        "ON t.mov_codcia = v.mov_codcia AND t.mov_nummov = v.det_nrolot "
        if hay_cobro else ""
    )
    cobro_expr = "ISNULL(SUM(ISNULL(v.Valor, 0)), 0)" if hay_cobro else "0"

    sql = (
        "SELECT LTRIM(RTRIM(ISNULL(t.mov_viaent, ''))) AS rubro, COUNT(*) AS n, "
        f"ISNULL(SUM(t.mov_total), 0) AS facturado, {cobro_expr} AS cobrado "
        f"FROM [{safe_db}].[dbo].[tb_cabmovT] t "
        f"INNER JOIN [{safe_db}].[dbo].[edu_alumno] a ON t.mov_produc = a.alu_codigo_alu "
        f"INNER JOIN [{safe_db}].[dbo].[edu_period] p ON a.alu_period = p.per_codigo "
        f"{join_cobro}"
        "WHERE t.mov_estado <> 'AN' AND t.mov_total > 0 "
        "AND LTRIM(RTRIM(p.per_nombre)) = ("
        "  SELECT TOP 1 LTRIM(RTRIM(p2.per_nombre)) "
        f"  FROM [{safe_db}].[dbo].[tb_cabmovT] t2 "
        f"  INNER JOIN [{safe_db}].[dbo].[edu_alumno] a2 ON t2.mov_produc = a2.alu_codigo_alu "
        f"  INNER JOIN [{safe_db}].[dbo].[edu_period] p2 ON a2.alu_period = p2.per_codigo "
        "  WHERE t2.mov_estado <> 'AN' AND t2.mov_total > 0 "
        "  GROUP BY LTRIM(RTRIM(p2.per_nombre)) ORDER BY SUM(t2.mov_total) DESC"
        ") "
        "GROUP BY LTRIM(RTRIM(ISNULL(t.mov_viaent, ''))) "
        "ORDER BY SUM(t.mov_total) DESC"
    )
    _cols, rows, err = connector.execute_query(sql, target_db=safe_db)
    if err:
        logger.warning("[EXCEL_EXPORT] Cartera por rubro falló para %s: %s", safe_db, err)
        return []
    resultado = []
    for r in rows:
        codigo = (r[0] or "").strip()
        facturado, cobrado = _f(r[2]), _f(r[3])
        resultado.append({
            "rubro": _RUBROS_EDUCATIVOS.get(codigo, codigo or "Sin clasificar"),
            "n": int(r[1] or 0), "facturado": facturado, "cobrado": cobrado,
            "saldo": round(facturado - cobrado, 2),
        })
    return resultado


# ─── Construcción del libro de Excel ─────────────────────────────────────────

# Cabeceras que nunca se totalizan en las hojas del reporte multi-hoja
# (emparejan por palabra completa, minúsculas y sin acentos).
_COL_NO_TOTAL = {
    "#", "factura", "fecha", "cedula / ruc", "cedula", "ruc", "cliente",
    "producto", "linea", "rubro", "ultima venta", "ultima compra",
    "primera compra", "primera venta", "usuario", "nombre", "accion",
    "entidad", "descripcion", "detalle", "ip", "codigo", "documento",
}
# Cabeceras de columnas monetarias (además de las que contengan "($)").
_COL_MONEDA = {
    "total", "ingresos", "facturado", "cobrado", "saldo", "ticket prom.", "ticket",
}
# Límite de seguridad por hoja: si una consulta devolviera más filas de las
# que una hoja de Excel puede manejar cómodamente, el libro trunca de forma
# segura en vez de agotar memoria (OPT #4). Por lo general nunca se alcanza
# porque las consultas ya llevan su propio TOP.
_MAX_FILAS_HOJA = 50_000


def _norm_encabezado(v) -> str:
    """Normaliza un texto de cabecera para comparar: minúsculas y sin acentos."""
    s = unicodedata.normalize("NFD", str(v or "")).lower()
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").strip()


def generar_reporte_excel(connector, source_db: str, start=None, end=None) -> tuple[io.BytesIO, str]:
    """
    Genera el libro de Excel completo para `source_db` y devuelve
    (buffer_bytesio, nombre_de_archivo_sugerido).

    `start`/`end`: strings 'YYYY-MM-DD' o None (sin acotar por fecha).
    Afectan Facturas, Detalle Items, Productos y Clientes — las 4 hojas que
    se arman a partir de movimientos con fecha. Cartera es la única
    excepción: se calcula sobre el "período lectivo vigente" (un concepto
    académico, no un rango de fechas de calendario — un período lectivo
    puede abarcar varios meses), así que sigue siendo siempre el período
    lectivo con más facturación, igual que en TripleA_VentasIA.
    Defecto detectado en pruebas (28/08/2026): Productos y Clientes se
    dejaron sin filtro al portar este módulo, así que el Excel mezclaba el
    detalle acotado al período elegido con rankings de TODO el histórico en
    esas dos hojas — además de ser mucho más lento, porque esas consultas
    agregaban sobre la tabla completa sin importar qué período se pidiera.

    Rendimiento (08/09/2026, OPT #4 y #7): el libro se arma con openpyxl en
    modo write_only=True (streaming, sin materializar cientos de miles de
    objetos de celda en RAM) y el formato de cada celda se aplica AL ESCRIBIRLA,
    no en una pasada posterior sobre todas las celdas. Cada hoja trunca de
    forma segura a _MAX_FILAS_HOJA filas. El resultado visual es idéntico al
    anterior (5 hojas, cabecera verde, filas alternadas, auto-filtro, fila de
    TOTALES, formato de moneda, bordes, freeze de la primera fila).
    """
    import openpyxl
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    safe_db = _validar_db(source_db)

    facturas = _consultar_facturas(connector, safe_db, start, end)
    detalle = _consultar_detalle_items(connector, safe_db, start, end)
    productos = _consultar_productos(connector, safe_db, start, end)
    clientes = _consultar_clientes(connector, safe_db, start, end)
    rubros = _consultar_cartera_por_rubro(connector, safe_db) if _es_educativa(connector, safe_db) else []

    # write_only=True: el libro se escribe en streaming y NUNCA se materializan
    # los cientos de miles de objetos de celda de un libro normal (la causa del
    # fallo por memória con 20k+ items). El formato de cada celda se aplica al
    # escribirla (WriteOnlyCell), no en una pasada posterior (OPT #4 + #7).
    wb = openpyxl.Workbook(write_only=True)

    hdr_fill = PatternFill("solid", fgColor="0E7A4A")
    hdr_font = Font(color="FFFFFF", bold=True, size=11)
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    alt_fill = PatternFill("solid", fgColor="F0F2F5")
    money_fmt = "#,##0.00"
    thin = Side(border_style="thin", color="D0D7E3")
    brd = Border(left=thin, right=thin, top=thin, bottom=thin)
    ctr = Alignment(horizontal="center", vertical="center")
    total_fill = PatternFill("solid", fgColor="E6F4EA")
    total_border = Border(
        left=thin, right=thin,
        top=Side(border_style="medium", color="D0D7E3"), bottom=thin,
    )

    def _escribir_hoja(title, headers, widths, filas):
        """Crea una hoja y escribe el encabezado verde, las filas de datos (con
        el formato aplicado a cada celda AL escribirla, sin una pasada posterior)
        y la fila de TOTALES + auto-filtro. `filas` es un iterable de listas de
        tuplas (valor, es_moneda, centrado).

        Los totales se acumulan sobre los valores ya tipados de cada fila con
        las mismas reglas que antes (_totales_hoja): las cabeceras excluidas de
        _COL_NO_TOTAL y las columnas con algún valor no numérico no se totalizan.
        """
        ws = wb.create_sheet(title=title)
        ws.freeze_panes = "A2"
        ws.row_dimensions[1].height = 30

        # En write_only los anchos de columna deben fijarse ANTES del primer
        # append(); si se fijan después, openpyxl los descarta (queda el default).
        for ci, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(ci)].width = w

        hdr = [WriteOnlyCell(ws, value=h) for h in headers]
        for c in hdr:
            c.fill, c.font, c.alignment, c.border = hdr_fill, hdr_font, hdr_align, brd
        ws.append(hdr)

        ncols = len(headers)
        nombres = [_norm_encabezado(h) for h in headers]
        acum = [0.0] * (ncols + 1)
        hay_num = [False] * (ncols + 1)
        hay_texto = [False] * (ncols + 1)

        n = 0
        for valores in filas:
            row = []
            for ci, (val, money, center) in enumerate(valores, 1):
                c = WriteOnlyCell(ws, value=val)
                c.border = brd
                if n % 2 == 1:            # fila 2, 4, 6… → fondo alterno
                    c.fill = alt_fill
                if money:
                    c.number_format = money_fmt
                if center:
                    c.alignment = ctr
                row.append(c)
                if val is None or val == "":
                    continue
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    hay_texto[ci] = True
                else:
                    acum[ci] += val
                    hay_num[ci] = True
            ws.append(row)
            n += 1

        if n:
            totales = [None] * (ncols + 1)
            for ci in range(2, ncols + 1):
                if nombres[ci - 1] in _COL_NO_TOTAL:
                    continue
                if hay_num[ci] and not hay_texto[ci]:
                    totales[ci] = round(acum[ci], 2)

            fila_total = [None] * ncols
            for ci in range(1, ncols + 1):
                c = WriteOnlyCell(ws, value=None)
                c.font = Font(bold=True)
                c.fill = total_fill
                c.border = total_border
                if ci == 1:
                    c.value = "TOTAL"
                elif totales[ci] is not None:
                    c.value = totales[ci]
                    c.number_format = (
                        money_fmt if ("($)" in nombres[ci - 1] or nombres[ci - 1] in _COL_MONEDA)
                        else "#,##0"
                    )
                fila_total[ci - 1] = c
            ws.append(fila_total)
            ws.auto_filter.ref = f"A1:{get_column_letter(ncols)}{n + 1}"
        return ws

    # ══ HOJA 1 — Facturas ═══════════════════════════════════════════
    _escribir_hoja(
        "Facturas",
        ["#", "Factura", "Fecha", "Cédula / RUC", "Cliente", "Línea", "Ítems", "Unidades", "Total ($)"],
        [5, 14, 13, 18, 40, 28, 8, 10, 14],
        (
            [
                (i, False, True), (f["factura"], False, True), (_fecha_str(f["fecha"]), False, True),
                (f["cedula"], False, False), (f["cliente"], False, False),
                (f["linea"], False, False), (f["lineas"], False, True),
                (f["unidades"], False, True), (f["total"], True, False),
            ]
            for i, f in enumerate(facturas[:_MAX_FILAS_HOJA], 1)
        ),
    )

    # ══ HOJA 2 — Detalle de líneas ══════════════════════════════════
    _escribir_hoja(
        "Detalle Items",
        ["#", "Factura", "Fecha", "Cédula / RUC", "Cliente", "Producto", "Línea", "Cantidad", "Precio Unit. ($)", "Total ($)"],
        [5, 14, 13, 18, 40, 46, 28, 10, 16, 14],
        (
            [
                (i, False, True), (l["factura"], False, True), (_fecha_str(l["fecha"]), False, True),
                (l["cedula"], False, False), (l["cliente"], False, False),
                (l["producto"], False, False), (l["linea"], False, False),
                (l["cantidad"], False, True), (l["precio"], True, False), (l["total"], True, False),
            ]
            for i, l in enumerate(detalle[:_MAX_FILAS_HOJA], 1)
        ),
    )

    # ══ HOJA 3 — Productos ══════════════════════════════════════════
    _escribir_hoja(
        "Productos",
        ["#", "Producto", "Línea", "Unidades", "Facturas", "Precio Máx. ($)", "Precio Mín. ($)", "Ingresos ($)", "Última venta"],
        [5, 48, 28, 11, 11, 16, 16, 16, 14],
        (
            [
                (i, False, True), (p["name"], False, False), (p["linea"], False, False),
                (p["qty"], False, True), (p["invoices"], False, True),
                (p["precio_max"], True, False), (p["precio_min"], True, False),
                (p["revenue"], True, False), (_fecha_str(p["ultima"]), False, True),
            ]
            for i, p in enumerate(productos[:_MAX_FILAS_HOJA], 1)
        ),
    )

    # ══ HOJA 4 — Clientes ═══════════════════════════════════════════
    _escribir_hoja(
        "Clientes",
        ["#", "Cédula / RUC", "Cliente", "Facturas", "Total ($)", "Ticket Prom. ($)", "Primera compra", "Última compra"],
        [5, 18, 44, 11, 16, 16, 15, 15],
        (
            [
                (i, False, True), (c["cedula"], False, False), (c["name"], False, False),
                (c["invoices"], False, True), (c["total"], True, False),
                (c["ticket"], True, False), (_fecha_str(c["primera"]), False, True),
                (_fecha_str(c["ultima"]), False, True),
            ]
            for i, c in enumerate(clientes[:_MAX_FILAS_HOJA], 1)
        ),
    )

    # ══ HOJA 5 — Cartera (solo instituciones educativas) ════════════
    if rubros:
        _escribir_hoja(
            "Cartera",
            ["#", "Rubro", "Registros", "Facturado ($)", "Cobrado ($)", "Saldo ($)"],
            [5, 28, 12, 18, 18, 18],
            (
                [
                    (i, False, True), (r["rubro"], False, False), (r["n"], False, True),
                    (r["facturado"], True, False), (r["cobrado"], True, False), (r["saldo"], True, False),
                ]
                for i, r in enumerate(rubros[:_MAX_FILAS_HOJA], 1)
            ),
        )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    nombre = f"reporte_{safe_db}_{date.today().isoformat()}.xlsx"
    return buf, nombre


def exportar_tabla_excel(columns, rows, titulo: str = "datos") -> tuple[io.BytesIO, str]:
    """
    Exporta una tabla GENÉRICA (columnas + filas, tal como llega en una
    respuesta del chat) a un libro .xlsx de UNA hoja con el mismo formato
    profesional que generar_reporte_excel (cabecera verde esmeralda con letra
    blanca, bordes, filas alternadas, congelado de cabecera y auto-filtro).

    Requisito (29/08/2026): el botón "CSV" de las tarjetas de
    respuesta del chat pasa a "Excel" y usa este formato en vez del CSV plano.

    `columns`: lista de etiquetas de columna YA en el orden final (también se
        aceptan dicts con clave "label"/"key", por compatibilidad con el
        contrato del endpoint).
    `rows`: lista de filas; cada fila es una lista con un valor por columna
        (en el mismo orden). Los números llegan como int/float (pyodbc los
        devuelve así y el JSON los conserva), así que se escriben como número
        con formato de miles; los strings se dejan como texto para no
        mutilar cédulas/RUC con ceros a la izquierda ni IDs largos.

    Devuelve (buffer_bytesio_listo_para_stream, nombre_de_archivo_sugerido).
    """
    cols: list[str] = []
    for c in columns or []:
        if isinstance(c, dict):
            cols.append(str(c.get("label") or c.get("key") or ""))
        else:
            cols.append(str(c))
    cols = [c.strip() or f"Columna {i + 1}" for i, c in enumerate(cols)]
    if not cols:
        raise ValueError("No hay columnas para exportar.")
    if len(cols) > 300:
        cols = cols[:300]

    filas = [list(r) for r in (rows or [])]
    if len(filas) > 200_000:
        filas = filas[:200_000]

    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30

    hdr_fill = PatternFill("solid", fgColor="0E7A4A")
    hdr_font = Font(color="FFFFFF", bold=True, size=11)
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    alt_fill = PatternFill("solid", fgColor="F0F2F5")
    thin = Side(border_style="thin", color="D0D7E3")
    brd = Border(left=thin, right=thin, top=thin, bottom=thin)

    def _ancho_estimado(v, base: int) -> int:
        s = str(v) if v is not None else ""
        return min(60, max(base, len(s) + 2))

    anchos = [_ancho_estimado(h, 12) for h in cols]

    for ci, h in enumerate(cols, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill, c.font, c.alignment, c.border = hdr_fill, hdr_font, hdr_align, brd

    for ri, fila in enumerate(filas, 2):
        for ci in range(len(cols)):
            v = fila[ci] if ci < len(fila) else None
            c = ws.cell(row=ri, column=ci + 1)
            if isinstance(v, bool):
                c.value = "Sí" if v else "No"
            elif isinstance(v, (int, float)):
                c.value = v
                c.number_format = "#,##0.00" if isinstance(v, float) else "#,##0"
            elif isinstance(v, (datetime, date)):
                c.value = _fecha_str(v)
            else:
                s = "" if v is None else str(v)
                c.value = s.replace("​", "")  # marcador invisible de ApexCharts
            c.border = brd
            if ri % 2 == 0:
                c.fill = alt_fill
            anchos[ci] = max(anchos[ci], _ancho_estimado(c.value, 0))

    for ci, w in enumerate(anchos, 1):
        ws.column_dimensions[ws.cell(row=1, column=ci).column_letter].width = w

    # El frontend puede enviar como ÚLTIMA fila una fila de totales con la
    # primera celda "TOTAL" (sumas numéricas en columnas numéricas y "" en las
    # demás). Si aparece, se estiliza y se excluye del auto-filtro.
    es_total = (
        isinstance(ws.cell(row=ws.max_row, column=1).value, str)
        and ws.cell(row=ws.max_row, column=1).value.strip().upper() == "TOTAL"
    )
    if es_total:
        fila_total = ws.max_row
        for ci in range(1, len(cols) + 1):
            c = ws.cell(row=fila_total, column=ci)
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor="E6F4EA")
            # Se conservan border y number_format ya asignados en el bucle.
        try:
            ws.auto_filter.ref = f"A1:{ws.cell(row=1, column=len(cols)).column_letter}{fila_total - 1}"
        except Exception:
            pass
    else:
        try:
            ws.auto_filter.ref = ws.dimensions
        except Exception:
            pass

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    safe_titulo = re.sub(r"[^A-Za-z0-9_-]+", "_", str(titulo)).strip("_") or "datos"
    nombre = f"{safe_titulo}.xlsx"
    return buf, nombre
