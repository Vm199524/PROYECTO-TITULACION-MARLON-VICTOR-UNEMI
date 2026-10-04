"""
knowledge/semantic_relations.py - Relaciones semanticas para el motor NL2SQL.
Construye una "dieta de datos" compacta a partir del esquema activo.
Prioriza uniones reales y nombres de columnas presentes en la base conectada.
"""
from __future__ import annotations

import unicodedata


def _normalize(value: str) -> str:
    raw = unicodedata.normalize("NFD", str(value or "").strip().lower())
    raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in raw if ch.isalnum())


def _find_table(schema_dict: dict, aliases: tuple[str, ...]) -> str | None:
    alias_set = {_normalize(alias) for alias in aliases}
    for table_name in schema_dict:
        if _normalize(table_name) in alias_set:
            return table_name
    return None


def _find_column(schema_dict: dict, table_name: str | None, aliases: tuple[str, ...]) -> str | None:
    if not table_name:
        return None
    columns = schema_dict.get(table_name, {}).get("columns", [])
    alias_set = {_normalize(alias) for alias in aliases}
    for col in columns:
        col_name = str(col.get("name", "")).strip()
        if _normalize(col_name) in alias_set:
            return col_name
    return None


def _build_relation_line(
    schema_dict: dict,
    source_tables: tuple[str, ...],
    source_cols: tuple[str, ...],
    target_tables: tuple[str, ...],
    target_cols: tuple[str, ...],
    explanation: str,
) -> str | None:
    source_table = _find_table(schema_dict, source_tables)
    target_table = _find_table(schema_dict, target_tables)
    source_col = _find_column(schema_dict, source_table, source_cols)
    target_col = _find_column(schema_dict, target_table, target_cols)
    if not all((source_table, target_table, source_col, target_col)):
        return None
    return (
        f"- {source_table}.{source_col} se une con "
        f"{target_table}.{target_col} ({explanation})."
    )


def build_semantic_relations(schema_dict: dict) -> str:
    """
    Produce un bloque de relaciones semanticas a partir del esquema real.
    Si no encuentra coincidencias fuertes, devuelve guias conservadoras.
    """
    relations: list[str] = []

    candidates = (
        (
            ("V_Resumen_Nomina", "rol_pago"),
            ("Cedula", "cedula", "identificacion"),
            ("V_Ficha_Maestra", "ficha_trabajador"),
            ("Cedula", "cedula", "identificacion"),
            "para roles de pago, nombres, cargo y area del trabajador",
        ),
        (
            ("V_Historial_Novedades", "VIS_HISNOVTRABAJADOR"),
            ("Cedula", "cedula", "identificacion"),
            ("V_Ficha_Maestra", "ficha_trabajador"),
            ("Cedula", "cedula", "identificacion"),
            "para historial laboral, permisos, ausencias y novedades del personal",
        ),
        (
            ("ventas_detalle", "detalle_factura", "factura_detalle"),
            ("Id_Factura", "idfactura", "factura_id", "codfactura", "secuencia"),
            ("cabecera_factura", "V_Ventas_Cabecera", "facturas", "ventas_cabecera"),
            ("Id_Factura", "idfactura", "factura_id", "codfactura", "secuencia"),
            "para bajar de la cabecera comercial al detalle de productos vendidos",
        ),
        (
            ("cabecera_factura", "V_Ventas_Cabecera", "facturas", "ventas_cabecera"),
            ("Id_Cliente", "cliente_id", "codcliente", "cliente", "codigo_cliente"),
            ("clientes", "cliente"),
            ("Id_Cliente", "cliente_id", "codcliente", "codigo", "id"),
            "para mostrar razon social, cartera y deudas de clientes",
        ),
        (
            ("compras_detalle", "detalle_compra"),
            ("Id_Compra", "idcompra", "compra_id", "codcompra", "secuencia"),
            ("cabecera_compra", "V_Compras_Cabecera", "compras_cabecera"),
            ("Id_Compra", "idcompra", "compra_id", "codcompra", "secuencia"),
            "para bajar de la cabecera de compras al detalle de items",
        ),
        (
            ("cabecera_compra", "V_Compras_Cabecera", "compras_cabecera"),
            ("Id_Proveedor", "proveedor_id", "codproveedor", "proveedor", "codigo_proveedor"),
            ("proveedores", "proveedor"),
            ("Id_Proveedor", "proveedor_id", "codproveedor", "codigo", "id"),
            "para mostrar nombre comercial y saldos por proveedor",
        ),
        (
            ("ventas_detalle", "detalle_factura", "factura_detalle"),
            ("Id_Producto", "producto_id", "codproducto", "item", "codigo_producto"),
            ("productos", "producto", "inventario", "items"),
            ("Id_Producto", "producto_id", "codproducto", "codigo", "id"),
            "para mostrar descripcion y rentabilidad por producto",
        ),
        (
            ("V_Inventario_Stock", "inventario", "productos", "producto", "items"),
            ("Id_Producto", "producto_id", "codproducto", "codigo", "id"),
            ("productos", "producto", "items"),
            ("Id_Producto", "producto_id", "codproducto", "codigo", "id"),
            "para evaluar stock actual, stock minimo y punto de reorden por producto",
        ),
        (
            ("matriculas", "V_Registro_Academico"),
            ("Id_Alumno", "alumno_id", "idestudiante", "cedula", "id"),
            ("alumnos", "estudiantes", "VIS_ALUMNO"),
            ("Id_Alumno", "alumno_id", "idestudiante", "cedula", "id"),
            "para matriculas, notas y seguimiento academico por estudiante",
        ),
    )

    for candidate in candidates:
        relation_line = _build_relation_line(schema_dict, *candidate)
        if relation_line:
            relations.append(relation_line)

    if not relations:
        relations = [
            "- V_Resumen_Nomina.Cedula se une con V_Ficha_Maestra.Cedula para enriquecer roles de pago.",
            "- rol_pago.Cedula se une con ficha_trabajador.Cedula cuando trabajes directo sobre tablas base.",
            "- Prioriza vistas semanticas V_ cuando existan; usa tablas base solo si la vista no esta disponible.",
        ]

    # Inyeccion de Reglas Estrictas de Negocio para el Prompt de la IA
    strict_rules = """
REGLAS ESTRICTAS DE JOIN Y NOMBRES (OBLIGATORIO):
1. REGLA DE NOMBRES (VENTAS): Nunca uses la columna 'Cliente' de la cabecera_factura o Ejemplo_Ventas para mostrar el nombre. DEBES hacer un JOIN obligatoriamente con la tabla de clientes (ej. Clientes o MAE_CLIENTES) usando el ID (ej. ID_Cliente) para traer el NOMBRE REAL del cliente.
2. REGLA DE NOMINA: DEBES buscar la tabla maestra de empleados (ej. Empleados o FICHA_TRABAJADOR) y unirla por Codigo_Empleado/Cedula para traer los NOMBRES COMPLETOS. La columna 'Empresa' no existe en rol_pago; verifica en el esquema cual es la correcta (ej. 'Razon_Social' o 'Nombre') en la tabla maestra.
3. REGLA DE INVENTARIO: Para "stock critico" o "punto de reorden" solo respondas si el esquema actual contiene columnas equivalentes a stock actual y stock minimo/reorden. Si no existen, informa explicitamente que falta sincronizar inventario.
4. REGLA DE ORO PRO: Si no encuentras la tabla maestra en el esquema actual para realizar estos JOINs (ej. no existe tabla Clientes ni Empleados), INFORMA explicitamente al usuario en el campo 'explanation' que "Falta sincronizar la tabla de Clientes/Empleados para poder mostrar nombres reales en lugar de codigos."
"""
    relations.append(strict_rules)

    # Inyeccion de Glosario de Lenguaje Natural del Usuario Final
    # Necesario para que la IA traduzca preguntas cortas y coloquiales directamente a la logica correcta.
    # REGLA CRITICA (28/08/2026): ventas/compras/clientes se consultan SIEMPRE
    # sobre las vistas de CHAT listadas en el esquema (Ventas/Compras), NUNCA
    # sobre las tablas físicas tb_cabmov/tb_detmov/tb_client: son lentas, no
    # existen para todas las empresas (MONT factura en tb_cabmovT, no en
    # tb_cabmov) y rompen la consistencia con Reportes BI. El nombre exacto de
    # la vista se confirma en vivo y llega en el bloque VISTAS CONFIRMADAS.
    natural_language_glossary = """
GLOSARIO DE INTENCION (OBLIGATORIO - Lenguaje del usuario real):
El usuario NUNCA escribe nombres técnicos de tablas. Siempre usa lenguaje coloquial.
Debes mapear AUTOMATICAMENTE las siguientes expresiones a sus tablas correctas:

REGLAS GENERALES DE FUENTE (OBLIGATORIAS):
- Consulta SIEMPRE las vistas de CHAT que aparecen en el ESQUEMA DE DATOS DISPONIBLE (p. ej. [Ventas], [Compras], [ficha_trabajador], [rol_pago]). El esquema es la UNICA verdad sobre los nombres.
- NUNCA uses tablas físicas tb_* (tb_cabmov, tb_detmov, tb_client...) para ventas, compras o clientes: son lentas, algunas empresas facturan en otras tablas y no coinciden con Reportes BI.
- Si la vista de ventas/compras no esta en el esquema, informa al usuario que el dominio no esta sincronizado para esta empresa, en vez de inventar una tabla.

VENTAS / FACTURACION:
- Palabras clave: "ventas", "venta", "vendimos", "facturamos", "facturas", "facturado", "ingresos", "lo que vendí", "cuanto vendimos", "cuanto generamos", "balance comercial", "lo que entró"
- Acción: Usar la vista de ventas de CHAT indicada (Ventas o cabecera_factura, la que liste el esquema / VISTAS CONFIRMADAS), filtrando por su columna de fecha y sumando el monto (ej. SUM(Total)). Lee los nombres de columnas del esquema, no los inventes.

COMPRAS / PROVEEDORES:
- Palabras clave: "compras", "compramos", "lo que compramos", "gasto en proveedor", "proveedores pagados"
- Acción: Usar la vista de compras de CHAT indicada (Compras o cabecera_compra, la que liste el esquema / VISTAS CONFIRMADAS), filtrando por su columna de fecha y sumando el monto. Lee los nombres de columnas del esquema.

CLIENTES (cuando se pide "quién me compró"):
- Palabras clave: "clientes", "mejores clientes", "quien compro", "top compradores"
- Acción: Si el esquema expone una vista/tabla de clientes, únela por el id de cliente de la vista de ventas. Si no existe, explica que falta sincronizar la tabla de clientes.

PERIODOS DE TIEMPO (Ecuador usa español coloquial):
- "este mes", "del mes" → MONTH(mov_fecha)=MONTH(GETDATE()) AND YEAR(mov_fecha)=YEAR(GETDATE())
- "este año", "del año" → YEAR(mov_fecha)=YEAR(GETDATE())  
- "abril", "mayo", "enero"... → el mes correspondiente + año actual/mencionado
- "hoy" → CAST(mov_fecha AS date) = CAST(GETDATE() AS date)

EDUCACION / ACADEMICO (Base DAUN):
- "alumnos", "estudiantes", "inscritos", "matriculados", "activos", "matricula vigente" → Usar tabla [edu_alumno] filtrando SIEMPRE por WHERE LTRIM(RTRIM(alu_estado)) = '' AND alu_period = 1 (Esta es la realidad actual: 505 alumnos)
- "cursos", "grados", "niveles" → Usar [edu_cursos] y [edu_nivel] (Excluir cur_nombre LIKE '%NO USAR%')
- "periodos", "año lectivo" → Usar [edu_period] (Periodo actual es ID 1: 2025-2026)
- "notas", "calificaciones" → Usar [edu_notas] o similares segun esquema
"""
    relations.append(natural_language_glossary)

    return "\n".join(relations)
