"""
core/mirror_manager.py - Gestor del ADN Maestro Dinámico (v4.5)
================================================================
ARQUITECTURA CLAVE: Las vistas usan {DB} como marcador dinámico.
Cuando el usuario selecciona ACUA, SONG, AGRINAG o cualquier empresa,
{DB} se reemplaza automáticamente. El mismo código funciona para TODOS.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from config import DEBUG_DIR

logger = logging.getLogger(__name__)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _validate_identifier(value: str, label: str) -> str:
    candidate = (value or "").strip()
    if not candidate or not _IDENTIFIER_RE.fullmatch(candidate):
        raise ValueError(f"Identificador invalido para {label}: '{candidate}'")
    return candidate


def _q(identifier: str) -> str:
    return f"[{identifier}]"


# =============================================================================
# PLANTILLAS DINÁMICAS - El marcador {DB} se sustituye por la BD seleccionada
# =============================================================================

_VIEW_TEMPLATES: dict[str, str] = {

    # ─── VENTAS / FACTURACION ──────────────────────────────────────────────────
    "cabecera_factura": (
        "SELECT cli_ruccli AS Cedula, cli_nomcom AS Cliente, "
        "mov_numdoc AS NumeroFactura, det_nomart AS Producto, "
        "det_preuni AS Precio, det_canti AS Cantidad, "
        "CAST(mov_fecha AS date) AS Fecha, det_subtot AS Total, "
        "det_coscif AS Costo, ven_nombre AS Vendedor, sub_descri AS Subcentro "
        "FROM [{DB}].[dbo].[tb_cabmov] "
        "INNER JOIN [{DB}].[dbo].[tb_client] ON mov_provee = cli_codigo "
        "INNER JOIN [{DB}].[dbo].[tb_detmov] ON mov_codcia = det_codcia AND mov_nummov = det_cabece "
        "LEFT JOIN [{DB}].[dbo].[tb_vended] ON mov_compra = [{DB}].[dbo].[tb_vended].ven_codigo "
        "LEFT JOIN [{DB}].[dbo].[tb_subcos] ON mov_subcen = sub_codigo "
        "WHERE mov_tipo = 'FA' AND mov_estado <> 'AN'"
    ),

    # ─── COMPRAS ──────────────────────────────────────────────────────────────
    "cabecera_compra": (
        "SELECT [{DB}].[dbo].[tb_provee].clp_ruccli AS Cedula, "
        "[{DB}].[dbo].[tb_provee].clp_nomcom AS Proveedor, "
        "[{DB}].[dbo].[tb_cabmov1].mov_numdoc AS NumeroFactura, "
        "[{DB}].[dbo].[tb_item].ite_descor AS Producto, "
        "[{DB}].[dbo].[tb_detmov1].det_preuni AS Precio, "
        "[{DB}].[dbo].[tb_detmov1].det_canti AS Cantidad, "
        "CAST([{DB}].[dbo].[tb_cabmov1].mov_fecha AS date) AS Fecha, "
        "[{DB}].[dbo].[tb_detmov1].det_subtot AS Total "
        "FROM [{DB}].[dbo].[tb_cabmov1] "
        "INNER JOIN [{DB}].[dbo].[tb_provee] "
        "  ON [{DB}].[dbo].[tb_cabmov1].mov_provee = [{DB}].[dbo].[tb_provee].clp_codigo "
        "INNER JOIN [{DB}].[dbo].[tb_detmov1] "
        "  ON [{DB}].[dbo].[tb_cabmov1].mov_codcia = [{DB}].[dbo].[tb_detmov1].det_codcia "
        "  AND [{DB}].[dbo].[tb_cabmov1].mov_nummov = [{DB}].[dbo].[tb_detmov1].det_cabece "
        "INNER JOIN [{DB}].[dbo].[tb_item] "
        "  ON [{DB}].[dbo].[tb_detmov1].det_codart = [{DB}].[dbo].[tb_item].ite_codigo "
        "WHERE [{DB}].[dbo].[tb_cabmov1].mov_tipo = 'CO' "
        "AND [{DB}].[dbo].[tb_cabmov1].mov_estado <> 'AN'"
    ),

    # ─── RRHH: FICHA DEL TRABAJADOR ───────────────────────────────────────────
    "ficha_trabajador": (
        "SELECT [{DB}].[dbo].[tb_trabaj].trb_cedula AS Cedula, "
        "RTRIM([{DB}].[dbo].[tb_trabaj].trb_apell1) + ' ' + "
        "RTRIM([{DB}].[dbo].[tb_trabaj].trb_apell2) + ' ' + "
        "RTRIM([{DB}].[dbo].[tb_trabaj].trb_nombr1) + ' ' + "
        "RTRIM([{DB}].[dbo].[tb_trabaj].trb_nombr2) AS Nombres, "
        "[{DB}].[dbo].[tb_trabaj].trb_fecing AS [Fecha Ingreso], "
        "CASE WHEN trb_estado IN (2,3,8) THEN trb_fecsal ELSE '' END AS [Fecha Salida], "
        "(SELECT tco_altern FROM [{DB}].[dbo].[rh_tipcontrato] "
        "  WHERE tco_codigo = [{DB}].[dbo].[tb_trabaj].trb_tipcon) AS Contrato, "
        "ISNULL((SELECT tip_altern FROM [{DB}].[dbo].[tb_tipemp] "
        "  WHERE tip_codigo = [{DB}].[dbo].[tb_trabaj].trb_tipemp), '') AS [Tipo de Rol], "
        "CASE WHEN ISNULL(LEFT(tur_horent,2),6) > 18 THEN 'NOCTURNO' ELSE 'DIURNO' END AS Jornada, "
        "[{DB}].[dbo].[tb_cargo].cgo_descri AS Cargo, "
        "CASE trb_sexo WHEN 'M' THEN 'MASCULINO' ELSE 'FEMENINO' END AS Sexo, "
        "CASE trb_estciv "
        "  WHEN 'S' THEN 'SOLTERO' WHEN 'C' THEN 'CASADO' "
        "  WHEN 'D' THEN 'DIVORCIADO' WHEN 'V' THEN 'VIUDO' WHEN 'U' THEN 'UNION LIBRE' "
        "END AS [Estado Civil], "
        "[{DB}].[dbo].[tb_trabaj].trb_fecnac AS [Fecha Nacimiento], "
        "[{DB}].[dbo].[tb_seccion].sec_alterno AS Area, "
        "[{DB}].[dbo].[tb_trabaj].trb_email AS Email, "
        "[{DB}].[dbo].[tb_empres].emp_nomcor AS Empresa, "
        "[{DB}].[dbo].[tb_cencos].cen_alterno AS [Sucursal], "
        "[{DB}].[dbo].[tb_estemp].est_descri AS Estado "
        "FROM [{DB}].[dbo].[tb_trabaj] "
        "LEFT JOIN [{DB}].[dbo].[pr_turnos] "
        "  ON [{DB}].[dbo].[tb_trabaj].trb_codcgo = [{DB}].[dbo].[pr_turnos].tur_codigo "
        "INNER JOIN [{DB}].[dbo].[tb_empres] "
        "  ON [{DB}].[dbo].[tb_empres].emp_codigo = [{DB}].[dbo].[tb_trabaj].trb_empre "
        "INNER JOIN [{DB}].[dbo].[tb_cencos] "
        "  ON [{DB}].[dbo].[tb_cencos].cen_codigo = [{DB}].[dbo].[tb_trabaj].trb_ccosto "
        "INNER JOIN [{DB}].[dbo].[tb_seccion] "
        "  ON [{DB}].[dbo].[tb_seccion].sec_coddiv = [{DB}].[dbo].[tb_trabaj].trb_coddiv "
        "  AND [{DB}].[dbo].[tb_seccion].sec_codare = [{DB}].[dbo].[tb_trabaj].trb_codare "
        "  AND [{DB}].[dbo].[tb_seccion].sec_coddep = [{DB}].[dbo].[tb_trabaj].trb_coddep "
        "  AND [{DB}].[dbo].[tb_seccion].sec_codigo  = [{DB}].[dbo].[tb_trabaj].trb_codsec "
        "INNER JOIN [{DB}].[dbo].[tb_cargo] "
        "  ON [{DB}].[dbo].[tb_cargo].cgo_codigo = [{DB}].[dbo].[tb_trabaj].trb_codcgo "
        "LEFT JOIN [{DB}].[dbo].[tb_discap] "
        "  ON [{DB}].[dbo].[tb_trabaj].trb_discap = [{DB}].[dbo].[tb_discap].dis_codigo "
        "INNER JOIN [{DB}].[dbo].[tb_estemp] "
        "  ON [{DB}].[dbo].[tb_trabaj].trb_estado = [{DB}].[dbo].[tb_estemp].est_codigo"
    ),
    
    # ─── RRHH: ROL DE PAGO ───────────────────────────────────────────────────
    "rol_pago": (
        "SELECT tb_cabpre.cro_numero AS Rol, "
        "tb_cabpre.cro_fecini AS [Fecha Inicio], "
        "tb_cabpre.cro_fecfin AS [Fecha Fin], "
        "YEAR(tb_cabpre.cro_fecini) AS [Año], "
        "CASE MONTH(cro_fecini) "
        "  WHEN 1 THEN 'Enero' WHEN 2 THEN 'Febrero' WHEN 3 THEN 'Marzo' "
        "  WHEN 4 THEN 'Abril' WHEN 5 THEN 'Mayo' WHEN 6 THEN 'Junio' "
        "  WHEN 7 THEN 'Julio' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Septiembre' "
        "  WHEN 10 THEN 'Octubre' WHEN 11 THEN 'Noviembre' WHEN 12 THEN 'Diciembre' "
        "END AS Mes, "
        "tb_prerol.rol_dia AS Dias, tb_rubros.rub_codigo AS [Rubro Codigo], "
        "tb_rubros.rub_descri AS Descripcion, "
        "CASE tb_rubros.rub_tipo "
        "  WHEN 'E' THEN 'Egresos' WHEN 'I' THEN 'Ingresos' ELSE 'Provision' "
        "END AS Rubro, "
        "tb_trabaj.trb_codigo AS Codigo, "
        "RTRIM(tb_trabaj.trb_apell1) + ' ' + RTRIM(tb_trabaj.trb_apell2) + ' ' + "
        "RTRIM(tb_trabaj.trb_nombr1) + ' ' + RTRIM(tb_trabaj.trb_nombr2) AS Nombres, "
        "ISNULL(tb_area.are_descri, '') AS Area, "
        "tb_trabaj.trb_fecemp AS [Fecha Ingreso], "
        "[{DB}].[dbo].[tb_acutra].acu_valor AS Sueldo, "
        "tb_trabaj.trb_cedula AS Cedula, "
        "ISNULL([{DB}].[dbo].[tb_cargo].cgo_descri, '') AS Cargo, "
        "RTRIM(tb_trabaj.trb_tipcta) + '-' + RTRIM(tb_trabaj.trb_ctaban) AS Cuenta, "
        "[{DB}].[dbo].[tb_tipemp].tip_descri AS [Tipo Trabajador], "
        "SUM(CASE rub_tipo "
        "  WHEN 'I' THEN ROUND(CONVERT(numeric(14,4), tb_prerol.rol_valor), 2) "
        "  WHEN 'E' THEN ROUND(CONVERT(numeric(14,4), tb_prerol.rol_valor), 2) * -1 "
        "  WHEN 'P' THEN ROUND(CONVERT(numeric(14,4), tb_prerol.rol_valor), 2) "
        "END) AS Valor, "
        "ISNULL([{DB}].[dbo].[tb_empres].emp_nombre, '') AS Empresa "
        "FROM [{DB}].[dbo].[tb_cabrol] AS tb_cabpre "
        "INNER JOIN [{DB}].[dbo].[tb_detrol] AS tb_prerol "
        "  ON tb_cabpre.cro_numero = tb_prerol.rol_numero "
        "INNER JOIN [{DB}].[dbo].[tb_trabaj] AS tb_trabaj "
        "  ON tb_prerol.rol_codtra = tb_trabaj.trb_codigo "
        "INNER JOIN [{DB}].[dbo].[tb_rubros] AS tb_rubros "
        "  ON tb_prerol.rol_codrub = tb_rubros.rub_codigo "
        "INNER JOIN [{DB}].[dbo].[tb_departamento] AS tb_dep "
        "  ON tb_trabaj.trb_coddep = tb_dep.dep_codigo "
        "  AND tb_trabaj.trb_coddiv = tb_dep.dep_coddiv "
        "  AND tb_trabaj.trb_codare = tb_dep.dep_codare "
        "INNER JOIN [{DB}].[dbo].[tb_area] AS tb_area "
        "  ON tb_dep.dep_codcia = tb_area.are_codcia "
        "  AND tb_dep.dep_codare = tb_area.are_codigo "
        "  AND tb_dep.dep_coddiv = tb_area.are_coddiv "
        "INNER JOIN [{DB}].[dbo].[tb_acutra] "
        "  ON tb_trabaj.trb_codigo = [{DB}].[dbo].[tb_acutra].acu_codtra "
        "INNER JOIN [{DB}].[dbo].[tb_cargo] "
        "  ON [{DB}].[dbo].[tb_cargo].cgo_codigo = tb_trabaj.trb_codcgo "
        "INNER JOIN [{DB}].[dbo].[tb_cencos] "
        "  ON tb_trabaj.trb_ccosto = [{DB}].[dbo].[tb_cencos].cen_codigo "
        "LEFT JOIN [{DB}].[dbo].[tb_subcen] "
        "  ON tb_trabaj.trb_ccosto = [{DB}].[dbo].[tb_subcen].cen_codigo "
        "  AND tb_trabaj.trb_subcco = [{DB}].[dbo].[tb_subcen].sub_codigo "
        "INNER JOIN [{DB}].[dbo].[tb_tipemp] "
        "  ON tb_trabaj.trb_tipemp = [{DB}].[dbo].[tb_tipemp].tip_codigo "
        "LEFT JOIN [{DB}].[dbo].[tb_seccion] "
        "  ON tb_trabaj.trb_codsec = [{DB}].[dbo].[tb_seccion].sec_codigo "
        "  AND tb_trabaj.trb_coddiv = [{DB}].[dbo].[tb_seccion].sec_coddiv "
        "  AND tb_trabaj.trb_codare = [{DB}].[dbo].[tb_seccion].sec_codare "
        "  AND tb_trabaj.trb_coddep = [{DB}].[dbo].[tb_seccion].sec_coddep "
        "LEFT JOIN [{DB}].[dbo].[tb_empres] "
        "  ON tb_cabpre.cro_empre = [{DB}].[dbo].[tb_empres].emp_codigo "
        "WHERE ([{DB}].[dbo].[tb_acutra].acu_codrub = '4') AND ("
        "  (tb_rubros.rub_concep = 'S' AND tb_rubros.rub_tipcal NOT IN ('SD','SI')) OR "
        "  (tb_rubros.rub_concep = 'S' AND tb_rubros.rub_tipcal = 'FA' AND tb_prerol.rol_valor > 0) OR "
        "  (tb_rubros.rub_concep = 'N' AND tb_rubros.rub_tipcal = 'FA' AND tb_prerol.rol_valor > 0 AND tb_rubros.rub_tipo = 'E')"
        ") "
        "GROUP BY tb_cabpre.cro_numero, tb_cabpre.cro_fecini, tb_cabpre.cro_fecfin, "
        "tb_prerol.rol_dia, tb_rubros.rub_codigo, tb_rubros.rub_tipo, tb_rubros.rub_descri, "
        "tb_trabaj.trb_codigo, tb_trabaj.trb_nombr1, tb_trabaj.trb_nombr2, "
        "tb_trabaj.trb_apell1, tb_trabaj.trb_apell2, tb_area.are_descri, "
        "[{DB}].[dbo].[tb_cencos].cen_nombre, [{DB}].[dbo].[tb_subcen].sub_nombre, "
        "tb_trabaj.trb_fecemp, [{DB}].[dbo].[tb_acutra].acu_valor, "
        "[{DB}].[dbo].[tb_seccion].sec_descri, tb_trabaj.trb_cedula, "
        "tb_rubros.rub_tipcal, tb_prerol.rol_covid, tb_trabaj.trb_codcgo, "
        "[{DB}].[dbo].[tb_cargo].cgo_descri, tb_trabaj.trb_tipcta, "
        "tb_trabaj.trb_ctaban, [{DB}].[dbo].[tb_tipemp].tip_descri, "
        "tb_cabpre.cro_empre, [{DB}].[dbo].[tb_empres].emp_nombre"
    ),

    # ─── RRHH: HISTORIAL DE NOVEDADES ─────────────────────────────────────────
    "VIS_HISNOVTRABAJADOR": (
        "SELECT TOP (100) PERCENT "
        "[{DB}].[dbo].[rh_repmovrrh].mrh_codtra AS [CODIGO DE TRABAJADOR], "
        "[{DB}].[dbo].[tb_trabaj].trb_nombr1 AS [NOMBRE 1], "
        "[{DB}].[dbo].[tb_trabaj].trb_nombr2 AS [NOMBRE 2], "
        "[{DB}].[dbo].[tb_trabaj].trb_apell1 AS [APELLIDO 1], "
        "[{DB}].[dbo].[tb_trabaj].trb_apell2 AS [APELLIDO 2], "
        "[{DB}].[dbo].[rh_repmovrrh].mrh_codrub AS [COD RUBRO], "
        "[{DB}].[dbo].[tb_rubros].rub_descri AS Rubro, "
        "[{DB}].[dbo].[rh_repmovrrh].mrh_total AS Valor, "
        "[{DB}].[dbo].[rh_repmovrrh].mrh_concep AS Observacion, "
        "[{DB}].[dbo].[rh_repmovrrh].mrh_tipmov AS [Tipo de Movimiento], "
        "[{DB}].[dbo].[rh_repmovrrh].mrh_fecnov AS [Fecha Movimiento], "
        "[{DB}].[dbo].[tb_trabaj].trb_codigo "
        "FROM [{DB}].[dbo].[rh_repmovrrh] "
        "INNER JOIN [{DB}].[dbo].[tb_rubros] "
        "  ON [{DB}].[dbo].[rh_repmovrrh].mrh_codrub = [{DB}].[dbo].[tb_rubros].rub_codigo "
        "INNER JOIN [{DB}].[dbo].[tb_trabaj] "
        "  ON [{DB}].[dbo].[rh_repmovrrh].mrh_codtra = [{DB}].[dbo].[tb_trabaj].trb_codigo "
        "ORDER BY [CODIGO DE TRABAJADOR], [COD RUBRO], [Fecha Movimiento]"
    ),

    # ─── EDUCACION / ACADEMICO ────────────────────────────────────────────────
    "VIS_ALUMNO": (
        "SELECT [{DB}].[dbo].[edu_alumno].alu_codigo_alu AS CODIGO, "
        "[{DB}].[dbo].[edu_alumno].alu_nombree AS NOMBRE, "
        "[{DB}].[dbo].[edu_alumno].alu_apepate AS [APELLIDO PATERNO], "
        "[{DB}].[dbo].[edu_alumno].alu_apemate AS [APELLIDO MATERNO], "
        "[{DB}].[dbo].[edu_alumno].alu_sexo AS SEXO, "
        "[{DB}].[dbo].[edu_alumno].alu_fecnac AS [FECHA NAC], "
        "[{DB}].[dbo].[edu_alumno].alu_telefoe AS TELEFONO, "
        "[{DB}].[dbo].[edu_alumno].alu_correoe AS CORREO, "
        "[{DB}].[dbo].[edu_period].per_nombre AS PERIODO, "
        "[{DB}].[dbo].[edu_alumno].alu_nrocede AS CEDULA, "
        "[{DB}].[dbo].[edu_alumno].alu_matric AS MATRICULA, "
        "[{DB}].[dbo].[edu_nivel].niv_nombre AS NIVEL, "
        "[{DB}].[dbo].[edu_cursos].cur_nombre AS CURSO, "
        "[{DB}].[dbo].[edu_alumno].alu_estado AS ESTADO "
        "FROM [{DB}].[dbo].[edu_alumno] "
        "INNER JOIN [{DB}].[dbo].[edu_period] "
        "  ON [{DB}].[dbo].[edu_alumno].alu_period = [{DB}].[dbo].[edu_period].per_codigo "
        "  AND [{DB}].[dbo].[edu_alumno].alu_codcia = [{DB}].[dbo].[edu_period].per_codcia "
        "INNER JOIN [{DB}].[dbo].[edu_nivel] "
        "  ON [{DB}].[dbo].[edu_alumno].alu_nivel = [{DB}].[dbo].[edu_nivel].niv_codigo "
        "  AND [{DB}].[dbo].[edu_alumno].alu_codcia = [{DB}].[dbo].[edu_nivel].niv_codcia "
        "INNER JOIN [{DB}].[dbo].[edu_cursos] "
        "  ON [{DB}].[dbo].[edu_alumno].alu_codcia = [{DB}].[dbo].[edu_cursos].cur_codcia "
        "  AND [{DB}].[dbo].[edu_alumno].alu_curso = [{DB}].[dbo].[edu_cursos].cur_codigo"
    ),

    # ─── VISTAS RESUMEN (DINÁMICAS) ───────────────────────────────────────────
    "V_Resumen_Nomina": (
        "SELECT RTRIM(Cedula) AS Cedula, Nombres, Cargo, Area, Sueldo, "
        "Rubro, Descripcion, Valor, Mes, [Año], Estado "
        "FROM [rol_pago]"
    ),
    "V_Ficha_Maestra": (
        "SELECT RTRIM(Cedula) AS Cedula, Nombres, Cargo, Area, Estado, "
        "[Fecha Ingreso], [Fecha Nacimiento] "
        "FROM [ficha_trabajador]"
    ),
    "V_Ventas_Cabecera": "SELECT * FROM [cabecera_factura]",
    "V_Compras_Cabecera": "SELECT * FROM [cabecera_compra]",
    "V_Historial_Novedades": "SELECT * FROM [VIS_HISNOVTRABAJADOR]",
    "V_Registro_Academico": "SELECT * FROM [VIS_ALUMNO]",
}


_VIEW_DEPENDENCIES = {
    "cabecera_factura": "tb_cabmov",
    "cabecera_compra": "tb_cabmov1",
    "ficha_trabajador": "tb_trabaj",
    "rol_pago": "tb_cabrol",
    "VIS_HISNOVTRABAJADOR": "rh_repmovrrh",
    "VIS_ALUMNO": "edu_alumno",
    "V_Resumen_Nomina": "tb_cabrol",
    "V_Ficha_Maestra": "tb_trabaj",
    "V_Ventas_Cabecera": "tb_cabmov",
    "V_Compras_Cabecera": "tb_cabmov1",
    "V_Historial_Novedades": "rh_repmovrrh",
    "V_Registro_Academico": "edu_alumno"
}

_VIEW_REQUIRED_TABLES: dict[str, set[str]] = {
    "cabecera_factura": {"tb_cabmov", "tb_client", "tb_detmov", "tb_vended", "tb_subcos"},
    "cabecera_compra": {"tb_cabmov1", "tb_provee", "tb_detmov1", "tb_item"},
    "ficha_trabajador": {
        "tb_trabaj",
        "pr_turnos",
        "tb_empres",
        "tb_cencos",
        "tb_seccion",
        "tb_cargo",
        "tb_discap",
        "tb_estemp",
        "rh_tipcontrato",
        "tb_tipemp",
    },
    "rol_pago": {
        "tb_cabrol",
        "tb_detrol",
        "tb_trabaj",
        "tb_rubros",
        "tb_departamento",
        "tb_area",
        "tb_acutra",
        "tb_cargo",
        "tb_cencos",
        "tb_subcen",
        "tb_tipemp",
        "tb_seccion",
        "tb_empres",
    },
    "VIS_HISNOVTRABAJADOR": {"rh_repmovrrh", "tb_rubros", "tb_trabaj"},
    "VIS_ALUMNO": {"edu_alumno", "edu_period", "edu_nivel", "edu_cursos"},
}

_VIEW_REQUIRED_VIEWS: dict[str, set[str]] = {
    "V_Resumen_Nomina": {"rol_pago"},
    "V_Ficha_Maestra": {"ficha_trabajador"},
    "V_Ventas_Cabecera": {"cabecera_factura"},
    "V_Compras_Cabecera": {"cabecera_compra"},
    "V_Historial_Novedades": {"VIS_HISNOVTRABAJADOR"},
    "V_Registro_Academico": {"VIS_ALUMNO"},
}


_CAPABILITY_DOMAINS = (
    {
        "id": "rrhh",
        "name": "Recursos Humanos",
        "module": "RRHH",
        "description": "Trabajadores, cargos, áreas, estados y movimientos de personal.",
        "views": ("ficha_trabajador", "V_Ficha_Maestra", "VIS_HISNOVTRABAJADOR", "V_Historial_Novedades"),
        "quick_questions": (
            "Muestra una tabla con los trabajadores activos por area",
            "Dame una lista de los cargos con mas personal",
            "Muestra el historial de novedades del trabajador con cedula X",
        ),
    },
    {
        "id": "nomina",
        "name": "Nómina",
        "module": "NOMINA",
        "description": "Roles de pago, rubros, sueldos y costos laborales.",
        "views": ("rol_pago", "V_Resumen_Nomina"),
        "quick_questions": (
            "Muestra el costo total de nomina por area del mes o año actual",
            "Dame una lista con los 5 sueldos mas altos y sus cargos",
            "Muestra una grafica de torta con ingresos y egresos",
        ),
    },
    {
        "id": "finanzas",
        "name": "Finanzas y Compras",
        "module": "FINANZAS",
        "description": "Compras a proveedores, cuentas por pagar y flujo financiero operativo.",
        "views": ("cabecera_compra", "V_Compras_Cabecera"),
        "quick_questions": (
            "Muestra una tabla con los 10 proveedores con mas facturas",
            "Dame una lista de compras por mes del ultimo año",
            "Muestra una grafica de barras con el total de compras por proveedor",
        ),
    },
    {
        "id": "ventas",
        "name": "Comercial",
        "module": "VENTAS",
        "description": "Facturación, clientes, vendedores, productos y comportamiento comercial.",
        "views": ("cabecera_factura", "V_Ventas_Cabecera"),
        "quick_questions": (
            "Muestra una tabla con los 10 productos mas vendidos",
            "Dame un ranking de vendedores por total facturado",
            "Muestra una grafica de lineas de ventas de los ultimos 6 meses",
        ),
    },
    {
        "id": "operaciones",
        "name": "Operaciones",
        "module": "OPERACIONES",
        "description": "Catalogo de articulos, abastecimiento e inventario con trazabilidad fisica de productos.",
        "views": ("cabecera_compra", "V_Compras_Cabecera"),
        "extra_dependency": "tb_item",
        "raw_tokens": ("tb_bodega", "tb_inventario", "tb_stock"),
        "quick_questions": (
            "Muestra una tabla de los articulos comprados recientemente",
            "Dame un ranking de proveedores por volumen de compras",
            "Muestra el catalogo de productos disponibles con sus codigos",
        ),
    },
    {
        "id": "academico",
        "name": "Académico",
        "module": "ACADEMICO",
        "priority": 100, # Prioridad maxima para el rol de negocio
        "description": "Alumnos, matrículas, cursos, niveles y analítica educativa.",
        "views": ("VIS_ALUMNO", "V_Registro_Academico"),
        "quick_questions": (
            "Muestra una tabla con el total de estudiantes por cursos",
            "Dame una lista de alumnos matriculados por jornada",
            "Muestra una grafica de torta de alumnos por genero y nivel",
        ),
    },
)

# Mapeo de tablas nucleares para verificacion de existencia de DATOS (no solo esquema)
_DOMAIN_CORE_PROBES = {
    "rrhh": "tb_trabaj",
    "nomina": "tb_cabrol",
    "finanzas": "tb_cabmov1", # Compras/Gastos
    "ventas": "tb_cabmov",    # Facturacion
    "operaciones": "tb_detmov1", # Movimientos de Inventario (Realidad operativa)
    "academico": "edu_alumno"
}


def filtrar_pulso_por_modulos(pulse: dict, allowed_modules: list) -> dict:
    """
    Acota un pulso BI a los módulos habilitados del rol (JWT → allowed_modules).

    Extraído del bloque final de `get_bi_pulse` para poder aplicarlo TAMBIÉN
    cuando se sirve un snapshot precacheados (Capa 2): el snapshot de una
    empresa se guarda SIN filtrar (un solo snapshot sirve a cualquier rol) y
    aquí se filtra por rol en el momento de servir. Los ítems sin módulo o
    "GENERAL" (métricas transversales) se conservan siempre.

    Devuelve el mismo dict mutado, para encadenar.
    """
    if not isinstance(pulse, dict) or not allowed_modules:
        return pulse
    allowed_set = {str(m).strip().upper() for m in allowed_modules if str(m).strip()}
    if not allowed_set:
        return pulse

    def _visible(item):
        mod = str((item or {}).get("module") or "").strip().upper()
        return (not mod) or mod == "GENERAL" or mod in allowed_set

    for _key in ("cards", "charts", "tables", "alerts", "focus_areas"):
        _arr = pulse.get(_key)
        if isinstance(_arr, list):
            pulse[_key] = [it for it in _arr if _visible(it)]

    # Los módulos/áreas anunciados también se acotan al rol: el perfil y el
    # contexto no deben anunciar módulos que este usuario no puede consultar.
    pulse["modules"] = [
        m for m in (pulse.get("modules") or [])
        if str(m).strip().upper() in allowed_set
    ]
    _profile = pulse.setdefault("profile", {})
    if isinstance(_profile.get("modules"), list):
        _profile["modules"] = [
            m for m in _profile["modules"]
            if str(m).strip().upper() in allowed_set
        ]
    if isinstance(pulse.get("areas"), list):
        pulse["areas"] = [
            a for a in pulse["areas"]
            if str((a or {}).get("id") or "").strip().upper() in allowed_set
        ]
    return pulse


class MirrorManager:
    """
    Gestiona el ADN Virtual (Sin Estado).
    Ya no usa una BD física, inyecta CTEs en la consulta en tiempo real.
    """

    def __init__(self, connector):
        self.connector = connector
        self.engine = connector.engine

    @staticmethod
    def compose_sql_with_virtual_dna(dna_block: str, sql: str) -> str:
        dna = str(dna_block or "").strip()
        query = str(sql or "").strip()
        if not dna:
            return query
        if not query:
            return dna

        if query.upper().startswith("WITH "):
            dna_body = re.sub(r"^\s*WITH\s+", "", dna, count=1, flags=re.IGNORECASE).strip().rstrip(",")
            query_body = re.sub(r"^\s*WITH\s+", "", query, count=1, flags=re.IGNORECASE).strip()
            return f"WITH {dna_body},\n{query_body}"
        return f"{dna}\n{query}"

    def _available_virtual_views(self, schema_dict: dict | None = None, source_db: str | None = None) -> set[str]:
        """
        Siguiendo el mandato gerencial: Las vistas virtuales (ADN del Negocio) 
        están alojadas en la base de datos CHAT y deben estar disponibles 
        INDEPENDIENTEMENTE de la base de datos cruda conectada, ya que la base 
        CHAT abstrae y unifica toda la estructura.
        """
        return set(_VIEW_TEMPLATES.keys())

    def get_capability_snapshot(self, source_db: str, schema_dict: dict | None = None) -> dict:
        db_label = str(source_db or "").strip() or "ACTIVA"
        available_views = self._available_virtual_views(schema_dict, source_db=source_db)
        raw_tables = {str(name or "").strip().lower() for name in (schema_dict or {}).keys()}

        areas = []
        modules = []
        quick_questions = []
        ready_domain_names = []

        # 0. Sonda de Datos (Data Probe)
        # Verificamos si las tablas nucleares o vistas equivalentes tienen al menos 1 registro
        data_presence = {}
        _PROBE_MAP = {
            "rrhh": ("tb_trabaj", "ficha_trabajador"),
            "nomina": ("tb_cabrol", "rol_pago"),
            "finanzas": ("tb_cabmov1", "cabecera_compra"),
            "ventas": ("tb_cabmov", "cabecera_factura"),
            "operaciones": ("tb_detmov1", "cabecera_compra"),
            "academico": ("edu_alumno", "vis_alumno")
        }
        
        # Para bases académicas conocidas (ej. MONT), forzar presencia académica
        if any(w in db_label.lower() for w in ("mont", "daun", "edu", "colegio", "escuela", "instituto", "unidad")):
            data_presence["academico"] = True

        try:
            probe_queries = []
            probe_keys = []
            for d_id, table_opts in _PROBE_MAP.items():
                if d_id in data_presence:
                    continue
                matched = None
                for t in table_opts:
                    if t.lower() in raw_tables:
                        matched = t
                        break
                if matched:
                    probe_queries.append(f"(SELECT TOP 1 1 FROM [{matched}]) AS {d_id}")
                    probe_keys.append(d_id)
            
            if probe_queries:
                full_probe_sql = f"SELECT {', '.join(probe_queries)}"
                _, p_rows, p_err = self.connector.execute_query(full_probe_sql)
                if not p_err and p_rows:
                    p_row = p_rows[0]
                    for idx, key in enumerate(probe_keys):
                        # p_row[idx] sera 1 si hay datos, None si esta vacia
                        data_presence[key] = (p_row[idx] == 1)
                elif p_err:
                    logger.error("[MIRROR] Error ejecución sonda en %s: %s", db_label, p_err)
        except Exception as _e:
            logger.warning("[MIRROR] Fallo estructural sonda en %s: %s", db_label, _e)

        for domain in _CAPABILITY_DOMAINS:
            domain_id = domain["id"]
            domain_views = domain.get("views", ())
            extra_dep = str(domain.get("extra_dependency", "")).strip().lower()

            # REGLA DE DETECCION REALISTA:
            ready = False
            for v_name in domain_views:
                if v_name in available_views:
                    dep_table = _VIEW_DEPENDENCIES.get(v_name, "").lower()
                    if dep_table and dep_table in raw_tables:
                        # Si hay dependencia extra (ej: tb_item para operaciones), verificarla
                        if extra_dep and extra_dep not in raw_tables:
                            continue 
                        
                        # VERIFICACION DE DATOS OBLIGATORIA
                        # Si el dominio tiene sonda definida, DEBE haber devuelto True
                        if domain_id in _DOMAIN_CORE_PROBES:
                            if not data_presence.get(domain_id, False):
                                continue # No hay datos en la tabla nuclear, area no lista

                        ready = True
                        break

            # Fallback por tokens (solo si no se detecto por vistas)
            if not ready:
                raw_tokens = domain.get("raw_tokens", ())
                has_tables = any(token.lower() in raw_tables for token in raw_tokens)
                if has_tables:
                    # En fallback tambien exigimos que haya datos si hay sonda definida
                    if domain_id in _DOMAIN_CORE_PROBES:
                        if not data_presence.get(domain_id, False):
                            ready = False
                        else:
                            ready = True
                    else:
                        ready = True

            if ready:
                ready_domain_names.append(domain["name"])
                modules.append(domain["module"])
                quick_questions.extend(domain.get("quick_questions", ()))
            
            areas.append(
                {
                    "id": domain["id"],
                    "name": domain["name"],
                    "desc": domain["description"],
                    "status": "ready" if ready else "locked",
                }
            )

        # REGLA DE EXCLUSION: Si es un colegio (Academico), desactivamos Operaciones
        # a menos que existan tablas explicitas de bodega/stock (tb_bodega, tb_stock).
        # Esto evita que una escuela con tb_item active el dominio de inventario.
        is_school = "ACADEMICO" in modules
        has_real_stock_tables = any(t in raw_tables for t in ("tb_bodega", "tb_stock", "tb_inventario"))

        # Bug real (28/08/2026): la sonda de "finanzas"
        # solo comprueba "existe al menos 1 fila en cabecera_compra" — un colegio
        # que alguna vez compró útiles de oficina activaba TODO el bloque de
        # preguntas sugeridas de "proveedores"/"compras por mes", aunque esa no
        # sea en absoluto su giro de negocio (Montessori: alumnos, pensiones,
        # matrículas). El usuario lo dijo explícito: "Prueba preguntando" debe
        # corresponder SIEMPRE a la lógica de negocio real de la empresa activa.
        # A diferencia de "operaciones" (que sí tiene tablas exclusivas de stock
        # para distinguir "compra real" de "compra ocasional"), no existe una
        # señal de tabla equivalente para compras — cualquier colegio con AL
        # MENOS una compra registrada ya cumplía la sonda existente. Por eso
        # aquí se excluye sin condición: para una institución académica,
        # proveedores/compras no es un tema que deba sugerirse proactivamente,
        # sin importar cuántos registros sueltos existan.
        # Preguntas de "ventas" reescritas para una institución académica: la
        # exclusión de "finanzas" (arriba) ya reconoce que un colegio no vive
        # de comprar a proveedores, pero el dominio "ventas" SÍ debe seguir
        # activo (un colegio factura pensiones y matrículas) — lo que estaba
        # mal era el TEXTO de sus preguntas sugeridas, heredado tal cual de un
        # negocio retail ("10 productos más vendidos", "ranking de
        # vendedores"), que no tiene sentido para un colegio (no vende
        # productos ni tiene vendedores). Defecto detectado en pruebas
        # 29/08/2026: "Prueba preguntando" debe reflejar SIEMPRE el giro real
        # de la empresa activa, no solo esconder lo que no aplica.
        _VENTAS_PREGUNTAS_COLEGIO = (
            "Muestra el total facturado por mes",
            "Dame un listado de pagos de pensión o matrícula del período más reciente",
            "Muestra una grafica de lineas de facturación de los ultimos 6 meses",
        )

        final_areas = []
        final_questions = []
        for a in areas:
            if a["id"] == "operaciones" and is_school and not has_real_stock_tables:
                continue # Ocultar operaciones en colegios sin stock real
            if a["id"] == "finanzas" and is_school:
                continue # Ocultar compras/proveedores en instituciones academicas
            final_areas.append(a)
            if a["status"] == "ready":
                # Recuperar preguntas solo de áreas que quedaron
                d_obj = next((d for d in _CAPABILITY_DOMAINS if d["id"] == a["id"]), {})
                if a["id"] == "ventas" and is_school:
                    final_questions.extend(_VENTAS_PREGUNTAS_COLEGIO)
                else:
                    final_questions.extend(d_obj.get("quick_questions", ()))

        areas = final_areas
        quick_questions = final_questions
        ready_domain_names = [a["name"] for a in areas if a["status"] == "ready"]
        modules = [domain["module"] for domain in _CAPABILITY_DOMAINS if domain["name"] in ready_domain_names]

        quick_questions = list(dict.fromkeys(quick_questions))[:6]
        modules = list(dict.fromkeys(modules))
        entities_count = len(schema_dict or {})
        # Contar solo los Datos Maestros que realmente están soportados por la BD física
        supported_views_count = sum(
            1 for v_name in available_views
            if _VIEW_DEPENDENCIES.get(v_name, "").lower() in raw_tables
        )
        # Si por alguna razón ninguna coincide pero hay vistas, mostrar al menos 1 para no dejar en 0 si hay áreas
        if supported_views_count == 0 and ready_domain_names:
            supported_views_count = len(ready_domain_names)
            
        virtual_view_count = supported_views_count

        if ready_domain_names:
            # Determinar rol principal basado en prioridad definida en el dominio
            primary_domain = max(_CAPABILITY_DOMAINS, key=lambda d: d.get("priority", 0) if d["name"] in ready_domain_names else -1)
            business_role = "Entidad Comercial" # Default
            
            if primary_domain.get("id") == "academico":
                business_role = "Institución Educativa"
            elif "tb_produccion" in raw_tables:
                business_role = "Planta Industrial / Producción"
            elif "tb_paciente" in raw_tables:
                business_role = "Centro de Salud / Hospital"

            # Resumen Ejecutivo más honesto
            summary = (
                f"La base {db_label} opera como {business_role} y está conectada exitosamente. "
                f"VicMar Data AI ha identificado soporte para: "
                + ", ".join(ready_domain_names)
                + f". El sistema tiene acceso a {entities_count} tablas del ERP para extraer cualquier dato solicitado."
            )
        elif entities_count > 0:
            summary = (
                f"La base conectada {db_label} cuenta con {entities_count} entidades mapeadas temporalmente. "
                f"VicMar Data AI puede analizar cualquier tabla o catálogo disponible en el servidor en modo puro."
            )
        else:
            summary = (
                f"VicMar Data AI no ha logrado extraer la estructura de tablas de la base {db_label}. "
                "Evita ejecutar operaciones matemáticas en este entorno hasta que exista conexión efectiva."
            )

        details = [
            f"Base activa: {db_label}",
            f"Entidades detectadas: {entities_count}",
            f"Datos Maestros identificados: {virtual_view_count}",
        ]
        if ready_domain_names:
            details.append("Dominios listos: " + ", ".join(ready_domain_names))
        elif entities_count > 0:
            details.append("Dominios listos: Exploracion libre de esquema")
        else:
            details.append("Dominios listos: Metadata pendiente de carga")

        return {
            "database": db_label,
            "summary": summary,
            "details": details,
            "modules": modules or ["GENERAL"],
            "areas": areas,
            "quick_questions": quick_questions,
            "metrics": {
                "entities_count": entities_count,
                "master_data_count": virtual_view_count,
                "ready_domains": len(ready_domain_names),
            },
        }

    def _load_db_insights(self) -> dict:
        """Carga mapeos personalizados desde db_insights.json."""
        try:
            from pathlib import Path
            import json
            path = Path(__file__).parent.parent / "data" / "db_insights.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def get_virtual_dna_block(self, source_db: str, schema_dict: dict = None, sql_query: str = "") -> str:
        """
        Genera el bloque CTE de ADN Virtual con soporte para mapeos dinámicos.
        Si se provee sql_query, filtra y retorna SOLAMENTE las vistas virtuales necesarias.
        """
        database = (source_db or "").strip().upper()
        if not database:
            return ""

        insights = self._load_db_insights()
        db_insights = insights.get(database, {})
        custom_mappings = db_insights.get("custom_mappings", {})

        dna_blocks = []
        valid_templates = self._available_virtual_views(schema_dict, source_db=database)

        # Usar mayúsculas para la búsqueda sin case sensitivity
        sql_upper = (sql_query or "").upper()

        for view_name, template in _VIEW_TEMPLATES.items():
            if view_name not in valid_templates:
                continue
                
            # OPTIMIZACION: Si tenemos el query, solo inyectamos las vistas mencionadas
            if sql_upper:
                view_upper = view_name.upper()
                if f"[{view_upper}]" not in sql_upper and f" {view_upper}" not in sql_upper:
                    continue

            try:
                sql = template.format(DB=database)
            except:
                sql = template.replace("{DB}", database)
            
            # Siempre se utilizan las Vistas Maestras del sistema
            dna_blocks.append(f"[{view_name}] AS (\n{sql}\n)")

        if not dna_blocks:
            return ""

        return "WITH " + ",\n".join(dna_blocks) + "\n"

    def get_chat_schema(self, schema_dict: dict = None, source_db: str | None = None) -> str:
        """
        Genera el esquema de texto de las Vistas Virtuales para que la IA sepa qué consultar.
        """
        header = '''
-- ========================================================
-- ADN VIRTUAL DE NEGOCIO (VISTAS MAESTRAS EN TIEMPO REAL)
-- Usa estos nombres de tabla DIRECTAMENTE en el FROM de tu query.
-- NO USES PREFIJOS. EJEMPLO: SELECT * FROM [ficha_trabajador]
-- ========================================================'''
        
        valid_templates = self._available_virtual_views(schema_dict, source_db=source_db)
        if not valid_templates:
            return ""

        lines = [header]
        
        for view_name in _VIEW_TEMPLATES.keys():
            if view_name not in valid_templates:
                continue
            if view_name == "cabecera_factura": lines.append("CREATE VIEW [cabecera_factura] (Cedula, Cliente, NumeroFactura, Producto, Precio, Cantidad, Fecha, Total, Costo, Vendedor, Subcentro) AS -- Ventas y facturación")
            elif view_name == "cabecera_compra": lines.append("CREATE VIEW [cabecera_compra] (Cedula, Proveedor, NumeroFactura, Producto, Precio, Cantidad, Fecha, Total) AS -- Compras y proveedores")
            elif view_name == "ficha_trabajador": lines.append("CREATE VIEW [ficha_trabajador] (Cedula, Nombres, [Fecha Ingreso], [Fecha Salida], Contrato, [Tipo de Rol], Jornada, Cargo, Sexo, [Estado Civil], [Fecha Nacimiento], Area, Email, Empresa, Sucursal, Estado) AS -- Empleados, RH, informacion personal")
            elif view_name == "rol_pago": lines.append("CREATE VIEW [rol_pago] (Rol, [Fecha Inicio], [Fecha Fin], [Año], Mes, Dias, [Rubro Codigo], Descripcion, Rubro, Codigo, Nombres, Area, [Fecha Ingreso], Sueldo, Cedula, Cargo, Cuenta, [Tipo Trabajador], Valor) AS -- Nominas y sueldos")
            elif view_name == "VIS_HISNOVTRABAJADOR": lines.append("CREATE VIEW [VIS_HISNOVTRABAJADOR] ([CODIGO DE TRABAJADOR], [NOMBRE 1], [NOMBRE 2], [APELLIDO 1], [APELLIDO 2], [COD RUBRO], Rubro, Valor, Observacion, [Tipo de Movimiento], [Fecha Movimiento]) AS -- Historial de novedades RH")
            elif view_name == "VIS_ALUMNO": lines.append("CREATE VIEW [VIS_ALUMNO] (CODIGO, NOMBRE, [APELLIDO PATERNO], [APELLIDO MATERNO], SEXO, [FECHA NAC], TELEFONO, CORREO, PERIODO, CEDULA, MATRICULA, NIVEL, CURSO, ESTADO) AS -- Registro académico")
            elif view_name == "V_Resumen_Nomina": lines.append("CREATE VIEW [V_Resumen_Nomina] (Cedula, Nombres, Cargo, Area, Sueldo, Rubro, Descripcion, Valor, Mes, [Año], Estado) AS -- Resumen simplificado de nóminas")
            elif view_name == "V_Ficha_Maestra": lines.append("CREATE VIEW [V_Ficha_Maestra] (Cedula, Nombres, Cargo, Area, Estado, [Fecha Ingreso], [Fecha Nacimiento]) AS -- Resumen simplificado de empleados")
            elif view_name == "V_Ventas_Cabecera": lines.append("CREATE VIEW [V_Ventas_Cabecera] (Cedula, Cliente, NumeroFactura, Producto, Precio, Cantidad, Fecha, Total, Costo, Vendedor, Subcentro) AS -- Resumen de ventas")
            elif view_name == "V_Compras_Cabecera": lines.append("CREATE VIEW [V_Compras_Cabecera] (Cedula, Proveedor, NumeroFactura, Producto, Precio, Cantidad, Fecha, Total) AS -- Resumen de compras")
            elif view_name == "V_Registro_Academico": lines.append("CREATE VIEW [V_Registro_Academico] (CODIGO, NOMBRE, [APELLIDO PATERNO], [APELLIDO MATERNO], SEXO, [FECHA NAC], TELEFONO, CORREO, PERIODO, CEDULA, MATRICULA, NIVEL, CURSO, ESTADO) AS -- Resumen académico")
            elif view_name == "V_Historial_Novedades": lines.append("CREATE VIEW [V_Historial_Novedades] ([CODIGO DE TRABAJADOR], [NOMBRE 1], [NOMBRE 2], [APELLIDO 1], [APELLIDO 2], [COD RUBRO], Rubro, Valor, Observacion, [Tipo de Movimiento], [Fecha Movimiento]) AS -- Resumen novedades")
            
        return "\n".join(lines) + "\n"

    @staticmethod
    def _bi_int(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _bi_float(value) -> float:
        try:
            return round(float(value or 0), 2)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _bi_period_label(year_value, month_value) -> str:
        month_names = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
        year_num = MirrorManager._bi_int(year_value)
        month_num = MirrorManager._bi_int(month_value)
        if year_num and month_num in month_names:
            return f"{month_names[month_num]} {year_num}"
        if year_num: return str(year_num)
        return "Actual"

    @staticmethod
    def _append_bi_card(cards: list, **kwargs) -> None:
        cards.append(kwargs)

    @staticmethod
    def _append_focus_area(focus_areas: list, **kwargs) -> None:
        focus_areas.append(kwargs)

    @staticmethod
    def _append_warning(warnings: list, **kwargs) -> None:
        warnings.append(kwargs)

    @staticmethod
    def _is_domain_ready(snapshot: dict, area_id: str) -> bool:
        for area in snapshot.get("areas", []):
            if area.get("id") == area_id:
                return area.get("status") == "ready"
        return False

    def _scalar(self, connection, sql: str):
        return connection.execute(text(sql)).scalar()

    def _vista_confiable_para(self, vista: str, safe_db: str) -> bool:
        """
        Verificación EN VIVO antes de confiar en una vista de CHAT para esta
        empresa (Reportes BI — regla fija: solo datos de la empresa activa).

        Bug real (28/08/2026): con SONG activa, "Ingresos por Línea de
        Negocio" y "Top 5 Productos" mostraron datos reales de MONT (pensiones
        de colegio en una empresa agrícola). Causa: CHAT es un namespace de
        vistas COMPARTIDO por todo el servidor (no por sesión) — otra petición
        concurrente había re-apuntado sus vistas a MONT justo antes de que
        este pulso corriera para SONG. Las tarjetas que leen CHAT directamente
        (Balance Comercial, académico, estas dos tablas) construyen su propio
        SQL a mano y por eso NO pasaban por la verificación que sí protege a
        las métricas del catálogo genérico — este método cierra ese hueco.

        Devuelve False (no confiar) ante cualquier duda, igual que
        `vista_aislada_para_empresa`, de la que es un atajo.
        """
        from core.integridad_vistas import vista_aislada_para_empresa

        return vista_aislada_para_empresa(self.connector, vista, safe_db, target_db="CHAT")

    def get_bi_pulse(
        self,
        source_db: str,
        schema_dict: dict = None,
        sp_status: str = "OK",
        anio: int = None,
        mes: int = None,
        allowed_modules: list = None,
    ) -> dict:
        """
        Genera el Pulso BI completo en tiempo real para una base de datos.

        `allowed_modules`: módulos que el rol del usuario tiene habilitados
        (viene del JWT vía el endpoint). Si viene no-vacío, las tarjetas,
        gráficos, tablas, alertas y áreas cuyo módulo NO esté en la lista se
        omiten del resultado (ej. un rol CONTABILIDAD no recibe tarjetas de
        ACADEMICO). Si viene vacío/None (ADMIN sin restricción, GUEST demo o
        token sin módulos) NO se filtra nada y se mantiene el comportamiento
        actual completo.

        `anio`: si se pasa (ej. desde el selector de año del dashboard), las
        métricas del catálogo que usan {year} (ventas/compras por factura y
        por mes) se recalculan para ese año en vez del más reciente con datos.
        El resto de tarjetas de catálogo (que ya usan su propia lógica de
        "período más reciente", ej. nómina, antigüedad) no cambian con esto —
        son cálculos de "estado actual", no de un año específico.

        `mes`: acota ADEMÁS a un mes concreto de ese año. Solo lo respetan las
        tarjetas escritas a mano en este archivo que dicen explícitamente
        "admite mes" en su comentario (Balance Comercial, Ingresos por Línea
        de Negocio, Top 5 Productos) — las métricas del catálogo genérico
        (`metricas_dashboard`) siguen siendo de año completo, ya que extender
        las ~30 métricas existentes a granularidad de mes es un cambio propio
        y no se hizo en este pase para no tocar SQL certificado que ya
        funciona en producción.
        """
        try:
            safe_db = _validate_identifier(source_db, "source_db")
        except ValueError:
            return {"status": "error", "message": "Base invalida."}

        snapshot = self.get_capability_snapshot(safe_db, schema_dict)
        schema_tables_lower = {k.lower() for k in (schema_dict or {}).keys()}
        
        results = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "db": safe_db,
            "cards": [],
            "charts": [],
            "tables": [],
            "alerts": [],
            "data": {},
            "warnings": [],
            "focus_areas": [],
            "modules": snapshot.get("modules", ["GENERAL"]),
            "areas": snapshot.get("areas", []),
            "quick_questions": snapshot.get("quick_questions", []),
            "metrics": snapshot.get("metrics", {}),
            "summary": snapshot.get("summary", ""),
            "profile": {
                "business_name": safe_db,
                "modules": snapshot.get("modules", ["GENERAL"]),
                "ready_domains": [a["name"] for a in snapshot.get("areas", []) if a["status"] == "ready"],
            },
            "sync_state": "live"
        }

        try:
            with self.engine.connect() as connection:
                # ── DETECCIÓN DINÁMICA DE VISTAS CHAT ──────────────────────────────
                # Comprobamos si la base de datos CHAT y sus vistas inteligentes existen
                # y son accesibles en el servidor actual, Y si el SP se ejecutó con éxito.
                use_chat_views = False
                if str(sp_status or "").strip().upper() == "OK":
                    try:
                        connection.execute(text("SELECT TOP 1 1 FROM [CHAT].[dbo].[cabecera_factura]")).fetchone()
                        use_chat_views = True
                        logger.info("[BI_PULSE] Vistas inteligentes de CHAT detectadas y funcionales en el servidor. Se utilizarán para Reportes BI.")
                    except Exception as e:
                        logger.info("[BI_PULSE] Vistas inteligentes de CHAT no detectadas o inaccesibles (%s). Usando tablas físicas directas.", e)
                else:
                    logger.warning("[BI_PULSE] SP_MODIFICA_VISTA_IA falló o no se ejecutó previamente (Status: %s). Forzando fallback seguro a tablas físicas del ERP.", sp_status)

                # Bug real (28/08/2026): la tarjeta academica usaba este MISMO
                # `use_chat_views`, que se calcula probando [CHAT].[cabecera_factura]
                # — una vista de VENTAS, sin ninguna relacion con VIS_ALUMNO. Para
                # MONT, la vista de ventas en CHAT esta desplegada con OTRO nombre
                # ("Ventas", no "cabecera_factura" — ver hallazgo del 28/08/2026),
                # asi que esa prueba fallaba y la tarjeta de alumnos caia SIEMPRE al
                # fallback de tabla fisica sin filtro de periodo (969 alumnos con
                # alu_estado='MA' de TODOS los periodos a la vez), nunca a VIS_ALUMNO
                # con el filtro correcto (882). Se prueba VIS_ALUMNO de forma
                # independiente, no se asume que "ventas funciona" implica "alumnos
                # funciona".
                academic_chat_ready = False
                if str(sp_status or "").strip().upper() == "OK":
                    try:
                        connection.execute(text("SELECT TOP 1 1 FROM [CHAT].[dbo].[VIS_ALUMNO]")).fetchone()
                        # Regla fija: Reportes BI solo muestra datos de la empresa
                        # activa. Igual que cabecera_factura, VIS_ALUMNO se reapunta
                        # bien por empresa pero vive en el namespace COMPARTIDO de
                        # CHAT — sin esta verificacion en vivo, una activacion
                        # concurrente de otra empresa academica puede dejarla
                        # apuntando a otra base justo cuando este pulso corre.
                        academic_chat_ready = self._vista_confiable_para("VIS_ALUMNO", safe_db)
                        if not academic_chat_ready:
                            logger.warning(
                                "[BI_PULSE] VIS_ALUMNO no aislada para %s ahora mismo; "
                                "tarjeta académica usa tabla física para no arriesgar datos de otra empresa.",
                                safe_db,
                            )
                    except Exception as e:
                        logger.info("[BI_PULSE] VIS_ALUMNO no detectada o inaccesible en CHAT (%s). Usando tabla física edu_alumno.", e)
                # ──────────────────────────────────────────────────────────────────

                # VENTAS Y COMPRAS (Soporte extendido para tb_cabmov y tb_cabmov1)
                has_v1 = "tb_cabmov" in schema_tables_lower
                has_v2 = "tb_cabmov1" in schema_tables_lower
                
                if has_v1 or has_v2:
                    sales_total = 0.0
                    purch_total = 0.0

                    # 1. Determinar el período más reciente con datos (Ventas o Compras)
                    now = datetime.now()
                    last_yr, last_mo = now.year, now.month
                    # Si el usuario eligio mes+año explicitos en el filtro global del
                    # dashboard, van directo — se salta la autodeteccion de abajo (que
                    # solo tiene sentido para "el periodo mas reciente con datos").
                    periodo_forzado = bool(anio and mes)
                    if periodo_forzado:
                        last_yr, last_mo = int(anio), int(mes)

                    # Regla fija: Reportes BI solo muestra datos de la empresa
                    # activa. cabecera_factura/cabecera_compra SE reapuntan bien
                    # por empresa, pero CHAT es compartido por todo el servidor
                    # — sin esta verificacion en vivo, una activacion concurrente
                    # de OTRA empresa puede dejarlas apuntando a otra base justo
                    # cuando este pulso corre (ver _vista_confiable_para).
                    ventas_chat_confiable = use_chat_views and self._vista_confiable_para("cabecera_factura", safe_db)
                    if use_chat_views and not ventas_chat_confiable:
                        logger.warning(
                            "[BI_PULSE] cabecera_factura no aislada para %s ahora mismo; "
                            "Balance Comercial usa tablas físicas para no arriesgar datos de otra empresa.",
                            safe_db,
                        )

                    if ventas_chat_confiable:
                        if not periodo_forzado:
                            # Buscar último período con datos usando vistas inteligentes de CHAT
                            v1_last = None
                            try:
                                v1_last = connection.execute(text(
                                    "SELECT TOP 1 YEAR(Fecha), MONTH(Fecha) FROM [CHAT].[dbo].[cabecera_factura] ORDER BY Fecha DESC"
                                )).fetchone()
                            except Exception:
                                pass

                            v2_last = None
                            try:
                                v2_last = connection.execute(text(
                                    "SELECT TOP 1 YEAR(Fecha), MONTH(Fecha) FROM [CHAT].[dbo].[cabecera_compra] ORDER BY Fecha DESC"
                                )).fetchone()
                            except Exception:
                                pass

                            # Quedarse con el más reciente de los dos
                            if v1_last and not v2_last:
                                last_yr, last_mo = v1_last[0], v1_last[1]
                            elif v2_last and not v1_last:
                                last_yr, last_mo = v2_last[0], v2_last[1]
                            elif v1_last and v2_last:
                                # Comparación simple de fecha (Y * 100 + M)
                                if (v1_last[0] * 100 + v1_last[1]) >= (v2_last[0] * 100 + v2_last[1]):
                                    last_yr, last_mo = v1_last[0], v1_last[1]
                                else:
                                    last_yr, last_mo = v2_last[0], v2_last[1]

                        period_label_ccial = self._bi_period_label(last_yr, last_mo)

                        # 2. Calcular totales para ese período específico sobre CHAT
                        try:
                            sales_total = self._bi_float(self._scalar(connection, f"SELECT SUM(Total) FROM [CHAT].[dbo].[cabecera_factura] WHERE YEAR(Fecha)={last_yr} AND MONTH(Fecha)={last_mo}"))
                        except Exception:
                            pass
                        try:
                            purch_total = self._bi_float(self._scalar(connection, f"SELECT SUM(Total) FROM [CHAT].[dbo].[cabecera_compra] WHERE YEAR(Fecha)={last_yr} AND MONTH(Fecha)={last_mo}"))
                        except Exception:
                            pass
                    else:
                        # Fallback a tablas físicas directas
                        if not periodo_forzado:
                            try:
                                # Buscar último movimiento en V1
                                v1_last = None
                                if has_v1:
                                    v1_last = connection.execute(text(
                                        f"SELECT TOP 1 YEAR(mov_fecha), MONTH(mov_fecha) FROM [{safe_db}].[dbo].[tb_cabmov] WHERE mov_tipo IN ('FA','CO') AND mov_estado<>'AN' ORDER BY mov_fecha DESC"
                                    )).fetchone()

                                # Buscar último movimiento en V2
                                v2_last = None
                                if has_v2:
                                    v2_last = connection.execute(text(
                                        f"SELECT TOP 1 YEAR(mov_fecha), MONTH(mov_fecha) FROM [{safe_db}].[dbo].[tb_cabmov1] WHERE mov_tipo='CO' AND mov_estado<>'AN' ORDER BY mov_fecha DESC"
                                    )).fetchone()

                                # Quedarse con el más reciente de los dos
                                if v1_last and not v2_last:
                                    last_yr, last_mo = v1_last[0], v1_last[1]
                                elif v2_last and not v1_last:
                                    last_yr, last_mo = v2_last[0], v2_last[1]
                                elif v1_last and v2_last:
                                    # Comparación simple de fecha (Y * 100 + M)
                                    if (v1_last[0] * 100 + v1_last[1]) >= (v2_last[0] * 100 + v2_last[1]):
                                        last_yr, last_mo = v1_last[0], v1_last[1]
                                    else:
                                        last_yr, last_mo = v2_last[0], v2_last[1]
                            except Exception:
                                pass

                        period_label_ccial = self._bi_period_label(last_yr, last_mo)
                        
                        # 2. Calcular totales para ese período específico sobre ERP físico
                        if has_v1:
                            sales_total = self._bi_float(self._scalar(connection, f"SELECT SUM(det_subtot) FROM [{safe_db}].[dbo].[tb_cabmov] INNER JOIN [{safe_db}].[dbo].[tb_detmov] ON mov_codcia = det_codcia AND mov_nummov = det_cabece WHERE mov_tipo='FA' AND mov_estado<>'AN' AND YEAR(mov_fecha)={last_yr} AND MONTH(mov_fecha)={last_mo}"))
                            purch_total = self._bi_float(self._scalar(connection, f"SELECT SUM(det_subtot) FROM [{safe_db}].[dbo].[tb_cabmov] INNER JOIN [{safe_db}].[dbo].[tb_detmov] ON mov_codcia = det_codcia AND mov_nummov = det_cabece WHERE mov_tipo='CO' AND mov_estado<>'AN' AND YEAR(mov_fecha)={last_yr} AND MONTH(mov_fecha)={last_mo}"))
                        
                        if has_v2:
                            purch_v2 = self._bi_float(self._scalar(connection, f"SELECT SUM(det_subtot) FROM [{safe_db}].[dbo].[tb_cabmov1] INNER JOIN [{safe_db}].[dbo].[tb_detmov1] ON mov_nummov = det_cabece WHERE mov_tipo='CO' AND mov_estado<>'AN' AND YEAR(mov_fecha)={last_yr} AND MONTH(mov_fecha)={last_mo}"))
                            purch_total = max(purch_total, purch_v2)
    
                    self._append_bi_card(
                        results["cards"], 
                        id="sales_purchases", 
                        title="Balance Comercial", 
                        value=sales_total, 
                        unit="$", 
                        module="VENTAS", 
                        accent="cyan", 
                        primary_label="Ventas",
                        secondary_value=purch_total,
                        secondary_label="Compras",
                        period_label=period_label_ccial,
                        hint=f"Datos del período {period_label_ccial}. Corresponde al total acumulado de facturación y adquisiciones ingresadas físicamente en el sistema ERP (criterio transaccional de caja)."
                    )

                # ── PANEL FINANCIERO GRANULAR (28/08/2026) ──
                # Ventas Hoy / Este Mes / Acumulado del año / Cartera por Cobrar /
                # Clientes / Productos / Cobrado en el Período — reorganiza Reportes
                # BI con la estructura que el usuario mostró como referencia.
                #
                # Deliberadamente NO usa CHAT: van todas contra las tablas físicas
                # de `safe_db` (tb_cabmov/tb_detmov/CLIDOCU), el mismo patrón ya
                # usado por RRHH ("van directo a las tablas físicas de la empresa
                # activa"). Es más simple Y más seguro — el bug de fuga entre
                # empresas del 28/08/2026 fue justo por depender de CHAT (un
                # namespace compartido); las tablas físicas de `safe_db` no tienen
                # ese riesgo en absoluto, cada empresa vive en su propia base.
                #
                # `mov_fecha` y `CLIDOCU.Fecha` son CHAR con formato 'YYYY/MM/DD'
                # (confirmado en vivo, 28/08/2026), no un tipo DATE real — todas las
                # comparaciones usan CAST(... AS date) en vez de comparar el string
                # crudo, que con separadores distintos ('-' vs '/') compara mal.
                if has_v1:
                    hoy = datetime.now()
                    _anio_panel = int(anio) if anio else hoy.year
                    _filtro_mes_panel = f" AND MONTH(CAST(mov_fecha AS date)) = {int(mes)}" if (anio and mes) else ""

                    try:
                        fila_hoy = connection.execute(text(
                            f"SELECT COUNT(*), ISNULL(SUM(mov_total),0) FROM [{safe_db}].[dbo].[tb_cabmov] "
                            f"WHERE mov_tipo='FA' AND mov_estado<>'AN' AND CAST(mov_fecha AS date) = CAST(GETDATE() AS date)"
                        )).fetchone()
                        facturas_hoy, total_hoy = int(fila_hoy[0] or 0), self._bi_float(fila_hoy[1])

                        hint_hoy = f"Facturación de hoy ({hoy.strftime('%d de %B de %Y')})."
                        if facturas_hoy == 0:
                            ultimo = connection.execute(text(
                                f"SELECT TOP 1 CAST(mov_fecha AS date), mov_total FROM [{safe_db}].[dbo].[tb_cabmov] "
                                f"WHERE mov_tipo='FA' AND mov_estado<>'AN' ORDER BY CAST(mov_fecha AS date) DESC"
                            )).fetchone()
                            if ultimo:
                                hint_hoy = (
                                    f"Sin facturación registrada hoy. Último movimiento en el ERP: "
                                    f"{ultimo[0].strftime('%d/%m/%Y')} (${self._bi_float(ultimo[1]):,.2f})."
                                )

                        self._append_bi_card(
                            results["cards"], id="ventas_hoy", title="Ventas Hoy", value=total_hoy, unit="$",
                            module="VENTAS", accent="cyan", secondary_value=facturas_hoy, secondary_label="Facturas", secondary_unit="",
                            period_label=hoy.strftime("%d/%m/%Y"), hint=hint_hoy,
                        )
                    except Exception as e:
                        logger.info("[BI_PULSE] Tarjeta 'Ventas Hoy' omitida: %s", e)

                    try:
                        mes_ref = int(mes) if (anio and mes) else hoy.month
                        anio_ref = _anio_panel
                        fila_mes = connection.execute(text(
                            f"SELECT COUNT(*), ISNULL(SUM(mov_total),0), ISNULL(AVG(mov_total),0) "
                            f"FROM [{safe_db}].[dbo].[tb_cabmov] WHERE mov_tipo='FA' AND mov_estado<>'AN' "
                            f"AND YEAR(CAST(mov_fecha AS date))={anio_ref} AND MONTH(CAST(mov_fecha AS date))={mes_ref}"
                        )).fetchone()
                        facturas_mes, total_mes, ticket_mes = int(fila_mes[0] or 0), self._bi_float(fila_mes[1]), self._bi_float(fila_mes[2])
                        _nombre_mes = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"][mes_ref - 1]
                        self._append_bi_card(
                            results["cards"], id="ventas_mes", title="Este Mes", value=total_mes, unit="$",
                            module="VENTAS", accent="emerald", secondary_value=facturas_mes, secondary_label="Facturas", secondary_unit="",
                            period_label=f"{_nombre_mes} {anio_ref}",
                            hint=f"{facturas_mes} facturas · ticket promedio ${ticket_mes:,.2f}.",
                        )
                    except Exception as e:
                        logger.info("[BI_PULSE] Tarjeta 'Este Mes' omitida: %s", e)

                    try:
                        fila_anio = connection.execute(text(
                            f"SELECT COUNT(*), ISNULL(SUM(mov_total),0), ISNULL(AVG(mov_total),0) "
                            f"FROM [{safe_db}].[dbo].[tb_cabmov] WHERE mov_tipo='FA' AND mov_estado<>'AN' "
                            f"AND YEAR(CAST(mov_fecha AS date))={_anio_panel}"
                        )).fetchone()
                        facturas_anio, total_anio, ticket_anio = int(fila_anio[0] or 0), self._bi_float(fila_anio[1]), self._bi_float(fila_anio[2])
                        self._append_bi_card(
                            results["cards"], id="ventas_acumulado", title=f"Acumulado {_anio_panel}", value=total_anio, unit="$",
                            module="VENTAS", accent="amber", secondary_value=facturas_anio, secondary_label="Facturas", secondary_unit="",
                            period_label=f"Año {_anio_panel}",
                            hint=f"{facturas_anio} facturas · ticket promedio ${ticket_anio:,.2f}.",
                        )
                    except Exception as e:
                        logger.info("[BI_PULSE] Tarjeta 'Acumulado' omitida: %s", e)

                    try:
                        clientes = self._bi_int(self._scalar(
                            connection,
                            f"SELECT COUNT(DISTINCT mov_provee) FROM [{safe_db}].[dbo].[tb_cabmov] "
                            f"WHERE mov_tipo='FA' AND mov_estado<>'AN'"
                        ))
                        if clientes > 0:
                            self._append_bi_card(
                                results["cards"], id="clientes_activos", title="Clientes", value=clientes, unit="",
                                module="VENTAS", accent="cyan", period_label="HISTÓRICO",
                                hint="Clientes distintos con al menos una factura registrada (histórico completo).",
                            )
                    except Exception as e:
                        logger.info("[BI_PULSE] Tarjeta 'Clientes' omitida: %s", e)

                    try:
                        productos = self._bi_int(self._scalar(
                            connection,
                            f"SELECT COUNT(DISTINCT d.det_codart) FROM [{safe_db}].[dbo].[tb_detmov] d "
                            f"INNER JOIN [{safe_db}].[dbo].[tb_cabmov] c ON c.mov_codcia=d.det_codcia AND c.mov_nummov=d.det_cabece "
                            f"WHERE c.mov_tipo='FA' AND c.mov_estado<>'AN'"
                        ))
                        if productos > 0:
                            self._append_bi_card(
                                results["cards"], id="productos_facturados", title="Productos", value=productos, unit="",
                                module="VENTAS", accent="violet", period_label="HISTÓRICO",
                                hint="Rubros/productos distintos con al menos una factura registrada (histórico completo).",
                            )
                    except Exception as e:
                        logger.info("[BI_PULSE] Tarjeta 'Productos' omitida: %s", e)

                # ── CARTERA POR COBRAR Y COBRADO EN EL PERÍODO (28/08/2026) ──
                # Fuente: CLIDOCU, el libro auxiliar de cuentas por cobrar (tabla
                # física de `safe_db`, confirmada real en SONG y MONT). DEBCRED=1
                # es cargo (factura, aumenta lo adeudado), DEBCRED=2 es abono
                # (cobro, lo reduce) — mismo criterio que usa la vista nativa
                # CLIDOCUSALDO del propio ERP para calcular saldos pendientes.
                if "clidocu" in schema_tables_lower:
                    try:
                        cartera = self._bi_float(self._scalar(
                            connection,
                            f"SELECT ISNULL(SUM(CASE WHEN DEBCRED=1 THEN Total ELSE 0 END),0) "
                            f"- ISNULL(SUM(CASE WHEN DEBCRED=2 THEN Total ELSE 0 END),0) "
                            f"FROM [{safe_db}].[dbo].[CLIDOCU] WHERE Empresa='{safe_db}' AND Estado<>'AN'"
                        ))
                        facturado_hist = self._bi_float(self._scalar(
                            connection,
                            f"SELECT ISNULL(SUM(Total),0) FROM [{safe_db}].[dbo].[CLIDOCU] "
                            f"WHERE Empresa='{safe_db}' AND DEBCRED=1 AND Estado<>'AN'"
                        )) or 0.0
                        cobrado_hist = self._bi_float(self._scalar(
                            connection,
                            f"SELECT ISNULL(SUM(Total),0) FROM [{safe_db}].[dbo].[CLIDOCU] "
                            f"WHERE Empresa='{safe_db}' AND DEBCRED=2 AND Estado<>'AN'"
                        )) or 0.0
                        pct_recaudado = round((cobrado_hist / facturado_hist) * 100, 1) if facturado_hist else 0.0

                        self._append_bi_card(
                            results["cards"], id="cartera_por_cobrar", title="Cartera por Cobrar", value=cartera, unit="$",
                            module="FINANZAS", accent="rose", period_label="HISTÓRICO",
                            hint=f"{pct_recaudado}% recaudado de ${facturado_hist:,.2f} facturado histórico (libro CLIDOCU).",
                        )
                    except Exception as e:
                        logger.info("[BI_PULSE] Tarjeta 'Cartera por Cobrar' omitida: %s", e)

                    try:
                        _anio_cob = int(anio) if anio else datetime.now().year
                        if anio and mes:
                            _cond_fecha = f"YEAR(CAST(Fecha AS date))={_anio_cob} AND MONTH(CAST(Fecha AS date))={int(mes)}"
                            _label_cob = f"{['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'][int(mes)-1]} {_anio_cob}"
                        else:
                            _cond_fecha = f"YEAR(CAST(Fecha AS date))={_anio_cob}"
                            _label_cob = f"Año {_anio_cob}"
                        fila_cobrado = connection.execute(text(
                            f"SELECT COUNT(*), ISNULL(SUM(Total),0) FROM [{safe_db}].[dbo].[CLIDOCU] "
                            f"WHERE Empresa='{safe_db}' AND DEBCRED=2 AND Estado<>'AN' AND {_cond_fecha}"
                        )).fetchone()
                        rubros_cobro, total_cobrado = int(fila_cobrado[0] or 0), self._bi_float(fila_cobrado[1])
                        self._append_bi_card(
                            results["cards"], id="cobrado_periodo", title="Cobrado en el Período", value=total_cobrado, unit="$",
                            module="FINANZAS", accent="emerald", period_label=_label_cob.upper(),
                            hint=f"{rubros_cobro} rubros de cobro emitidos en {_label_cob} (libro CLIDOCU).",
                        )
                    except Exception as e:
                        logger.info("[BI_PULSE] Tarjeta 'Cobrado en el Período' omitida: %s", e)

                # ACADÉMICO (Diferenciación Crítica DAUN vs MONT)
                # Auditoría 09/09/2026 (#6): "unemi_pruebas" no matcheaba
                # ningún alias de la lista, y `schema_tables_lower` es el
                # esquema de la base OPERATIVA (tiene "alumnos_prueba", no
                # "vis_alumno" — esa vive en CHAT). Se agrega "unemi" al
                # heurístico de nombre y una detección genérica por
                # substring "alumno" en cualquier tabla del esquema.
                is_academic_db = any(w in safe_db.lower() for w in ("mont", "daun", "edu", "colegio", "escuela", "instituto", "unidad", "unemi"))
                has_academic = (
                    is_academic_db
                    or "edu_alumno" in schema_tables_lower
                    or "vis_alumno" in schema_tables_lower
                    or any("alumno" in t for t in schema_tables_lower)
                )
                if has_academic:
                    # Auditoría 09/09/2026: VIS_ALUMNO ahora filtra por
                    # SESSION_CONTEXT('empresa_activa') en vez de por un ALTER
                    # VIEW global (ver auditoría interna del 09/09/2026 #2). Esta
                    # `connection` es la de administrador (no la de chat_reader
                    # con aislamiento del lado del motor de IA), así que aquí
                    # hay que fijar el contexto a mano antes de consultar la
                    # vista, o siempre devolvería 0 filas.
                    try:
                        connection.execute(text(
                            "EXEC sp_set_session_context @key = N'empresa_activa', @value = :empresa"
                        ), {"empresa": safe_db})
                    except Exception as e:
                        logger.warning("[BI_PULSE] No se pudo fijar SESSION_CONTEXT para %s: %s", safe_db, e)
                    # Bug real (28/08/2026): esta tarjeta tenia su PROPIO filtro,
                    # duplicado y desincronizado del de knowledge/metric_catalog.json.
                    # Filtraba por codigos ('AN','RE','PR','PRE') que VIS_ALUMNO ya no
                    # devuelve — la vista entrega el estado en texto largo via
                    # VIS_ESTALU (MATRICULADO, GRADUADO, RETIRADO...) — asi que el
                    # filtro no excluia nada, y ademas sumaba TODOS los periodos
                    # lectivos de la vista a la vez (2023-2024 a 2027-2028). Verificado
                    # contra la base real de MONT: "matriculados" (ESTADO='MATRICULADO'
                    # del periodo vigente) son 882; sumando tambien a los que estan
                    # graduados/en admision/en tramite de ese mismo periodo da 941;
                    # sumando ademas todos los periodos historicos da 1.038. Son tres
                    # cifras reales y distintas, no un error de redondeo, asi que la
                    # tarjeta ahora muestra las dos primeras (la que un director
                    # espera ver como matricula) y deja la tercera para quien pida
                    # explicitamente el historico completo.
                    matriculados = 0
                    registrados = 0
                    periodo_vigente = ""
                    try:
                        if academic_chat_ready:
                            # Auditoría 09/09/2026: adaptado al esquema nuevo de
                            # VIS_ALUMNO (anio/estado_matricula en vez del
                            # PERIODO/ESTADO del esquema de colegios K-12
                            # original — ver auditoría interna del 09/09/2026 #6).
                            periodo_vigente = str(self._scalar(
                                connection,
                                "SELECT TOP 1 CAST(anio AS VARCHAR(4)) FROM [CHAT].[dbo].[VIS_ALUMNO] "
                                "GROUP BY anio ORDER BY COUNT(*) DESC"
                            ) or "").strip()
                            if periodo_vigente:
                                safe_periodo = periodo_vigente.replace("'", "''")
                                matriculados = self._bi_int(self._scalar(
                                    connection,
                                    "SELECT COUNT(*) FROM [CHAT].[dbo].[VIS_ALUMNO] "
                                    f"WHERE estado_matricula = 'ACTIVO' AND anio = '{safe_periodo}'"
                                ))
                                registrados = self._bi_int(self._scalar(
                                    connection,
                                    "SELECT COUNT(*) FROM [CHAT].[dbo].[VIS_ALUMNO] "
                                    f"WHERE anio = '{safe_periodo}'"
                                ))
                        if academic_chat_ready and matriculados == 0 and registrados == 0:
                            registrados = self._bi_int(self._scalar(connection, "SELECT COUNT(*) FROM [CHAT].[dbo].[VIS_ALUMNO]"))
                            matriculados = registrados

                        if matriculados == 0 and registrados == 0:
                            # Fallback a la tabla fisica: alu_estado usa codigos cortos
                            # ('MA' = matriculado), no el texto largo de VIS_ESTALU.
                            matriculados = self._bi_int(self._scalar(connection, f"SELECT COUNT(*) FROM [{safe_db}].[dbo].[edu_alumno] WHERE RTRIM(alu_estado) = 'MA'"))
                            registrados = matriculados or self._bi_int(self._scalar(connection, f"SELECT COUNT(*) FROM [{safe_db}].[dbo].[edu_alumno]"))

                    except Exception as e:
                        logger.warning("[MIRROR] Error en conteo académico de alumnos: %s", e)
                        matriculados = 0
                        registrados = 0

                    total_cursos = 0
                    try:
                        if academic_chat_ready and periodo_vigente:
                            safe_periodo = periodo_vigente.replace("'", "''")
                            # "Cursos" en el esquema original (K-12) equivale aquí a
                            # "carreras" (educación universitaria) — no hay un
                            # concepto de curso/paralelo en el dataset académico
                            # actual, ver auditoría interna del 09/09/2026 #6.
                            total_cursos = self._bi_int(self._scalar(
                                connection,
                                "SELECT COUNT(DISTINCT carrera) FROM [CHAT].[dbo].[VIS_ALUMNO] "
                                f"WHERE ISNULL(carrera,'') <> '' AND anio = '{safe_periodo}'"
                            ))

                        if total_cursos == 0:
                            total_cursos = self._bi_int(self._scalar(connection, f"SELECT COUNT(*) FROM [{safe_db}].[dbo].[edu_cursos] WHERE (cur_estado LIKE 'A%' OR cur_estado = '') AND cur_nombre NOT LIKE '%NO USAR%'"))
                    except Exception:
                        total_cursos = 0

                    total_niveles = 0
                    try:
                        if academic_chat_ready and periodo_vigente:
                            safe_periodo = periodo_vigente.replace("'", "''")
                            total_niveles = self._bi_int(self._scalar(
                                connection,
                                "SELECT COUNT(DISTINCT NIVEL) FROM [CHAT].[dbo].[VIS_ALUMNO] "
                                f"WHERE ISNULL(NIVEL,'') <> '' AND RTRIM(PERIODO) = '{safe_periodo}'"
                            ))

                        if total_niveles == 0:
                            total_niveles = self._bi_int(self._scalar(connection, f"SELECT COUNT(*) FROM [{safe_db}].[dbo].[edu_nivel]"))
                    except Exception:
                        total_niveles = 0

                    # 1. Tarjeta dedicada: Total Alumnos (Matriculados + Registrados)
                    periodo_pill = f"PERIODO {periodo_vigente} · ACTIVO" if periodo_vigente else "REGISTRO ACTIVO"
                    self._append_bi_card(
                        results["cards"],
                        id="academic_alumnos",
                        title="Alumnos Matriculados",
                        value=matriculados,
                        unit="estud.",
                        module="ACADEMICO",
                        accent="cyan",
                        primary_label="Matriculados",
                        secondary_value=registrados if registrados != matriculados else None,
                        secondary_label="Registrados",
                        period_label=periodo_pill,
                        hint=(
                            f"Matrícula activa (estado_matricula='ACTIVO') del año lectivo "
                            f"{periodo_vigente or 'vigente'}. \"Registrados\" suma además a los "
                            "graduados, retirados y egresados de ese mismo año. No incluye "
                            "años lectivos anteriores."
                        )
                    )

                    # 2. Tarjeta dedicada: Carreras Ofertadas (antes "Cursos
                    # Ofertados" — el esquema original era de colegios K-12 con
                    # paralelos/cursos; este dataset es universitario, la
                    # dimensión equivalente es la carrera).
                    if total_cursos > 0:
                        self._append_bi_card(
                            results["cards"],
                            id="academic_cursos",
                            title="Carreras Ofertadas",
                            value=total_cursos,
                            unit="carreras",
                            module="ACADEMICO",
                            accent="emerald",
                            period_label="REGISTRO ACTIVO",
                            hint="Carreras con alumnos matriculados en el período vigente."
                        )

                    # 3. Tarjeta dedicada: Niveles Educativos
                    if total_niveles > 0:
                        self._append_bi_card(
                            results["cards"],
                            id="academic_niveles",
                            title="Niveles Educativos",
                            value=total_niveles,
                            unit="niveles",
                            module="ACADEMICO",
                            accent="purple",
                            period_label="REGISTRO ACTIVO",
                            hint="Niveles de enseñanza detectados (Inicial, E.G.B., Bachillerato)."
                        )

                # ── INGRESOS POR LÍNEA DE NEGOCIO Y TOP 5 PRODUCTOS (28/08/2026) ──
                # dos tarjetas de TABLA (no de valor único) para
                # Reportes BI. Ambas admiten mes+año del filtro global del dashboard.
                #
                # Hallazgo real al construirlas: la vista de ventas de CHAT NO se llama
                # igual en todas las empresas. El resto de este archivo asume
                # "cabecera_factura" (el nombre del template en _MIRROR_TEMPLATES), pero
                # para MONT el SP_MODIFICA_VISTA_IA desplegado en el servidor la crea
                # como "Ventas" — con una columna extra "Linea" (línea de negocio) que
                # "cabecera_factura" no tiene. Por eso estas dos tarjetas detectan en
                # vivo cuál de los dos nombres responde, en vez de asumir uno fijo.
                # "Ingresos por Línea de Negocio" requiere ademas que la vista tenga la
                # columna Linea: si no la tiene (empresas que sí usan el template
                # genérico), la tarjeta se omite en vez de mostrar un error o un dato
                # inventado — no hay clasificación de línea de negocio que mostrar ahí.
                # "Ventas" va primero: es la que trae la columna Linea (necesaria
                # para la tarjeta de linea de negocio); "cabecera_factura" es el
                # nombre generico y no siempre la tiene. Si ambas existen para la
                # misma empresa, se prefiere la mas completa.
                from core.vista_resolver import CANDIDATOS_VENTAS, detectar_vista_sqlalchemy

                vista_ventas_detectada = detectar_vista_sqlalchemy(connection, CANDIDATOS_VENTAS, target_db="CHAT")

                # Regla fija: Reportes BI solo muestra datos de la empresa activa.
                # Bug real (28/08/2026): con SONG activa, estas dos tarjetas
                # mostraron datos reales de MONT (pensiones de colegio en una
                # empresa agrícola) — CHAT es un namespace de vistas compartido
                # por todo el servidor, y otra petición concurrente lo había
                # re-apuntado a MONT justo antes de que este pulso corriera para
                # SONG. Sin esta verificación en vivo, detectar que la vista
                # EXISTE no dice nada sobre a qué empresa apunta AHORA MISMO.
                if vista_ventas_detectada and not self._vista_confiable_para(vista_ventas_detectada, safe_db):
                    logger.warning(
                        "[BI_PULSE] %s no aislada para %s ahora mismo; se omiten "
                        "'Ingresos por Línea de Negocio' y 'Top 5 Productos' para no "
                        "arriesgar datos de otra empresa.",
                        vista_ventas_detectada, safe_db,
                    )
                    vista_ventas_detectada = None

                if vista_ventas_detectada:
                    _meses_es = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
                    _anio_tablas = int(anio) if anio else datetime.now().year
                    _filtro_mes = f" AND MONTH(Fecha) = {int(mes)}" if mes else ""
                    _periodo_tablas = (
                        f"{_meses_es[int(mes) - 1]} {_anio_tablas}" if mes and 1 <= int(mes) <= 12
                        else f"año {_anio_tablas}"
                    )

                    # 1. Ingresos por Línea de Negocio
                    try:
                        filas = connection.execute(text(
                            "SELECT ISNULL(NULLIF(RTRIM(Linea),''), 'SIN CLASIFICAR') AS Linea, "
                            "COUNT(DISTINCT NumeroFactura) AS Facturas, "
                            "CAST(SUM(Total) AS DECIMAL(18,2)) AS Ingresos "
                            f"FROM [CHAT].[dbo].[{vista_ventas_detectada}] "
                            f"WHERE YEAR(Fecha) = {_anio_tablas}{_filtro_mes} "
                            "GROUP BY RTRIM(Linea) ORDER BY SUM(Total) DESC"
                        )).fetchall()
                        if filas:
                            results["tables"].append({
                                "id": "ingresos_por_linea",
                                "title": "Ingresos por Línea de Negocio",
                                "module": "VENTAS",
                                "columns": ["Línea", "Facturas", "Ingresos"],
                                "column_types": ["text", "number", "currency"],
                                "rows": [[str(f[0]), self._bi_int(f[1]), self._bi_float(f[2])] for f in filas],
                                "period_label": _periodo_tablas.upper(),
                                "hint": (
                                    f"Facturación del {_periodo_tablas} agrupada por línea de negocio "
                                    f"({vista_ventas_detectada}). No incluye períodos anteriores."
                                ),
                            })
                    except Exception as e:
                        logger.info("[BI_PULSE] Tabla 'Ingresos por Línea de Negocio' omitida (probable falta de columna Linea): %s", e)

                    # 2. Top 5 Productos por ingreso
                    try:
                        filas = connection.execute(text(
                            "SELECT TOP 5 Producto, "
                            "CAST(SUM(TRY_CAST(Cantidad AS FLOAT)) AS DECIMAL(18,2)) AS Unidades, "
                            "CAST(SUM(Total) AS DECIMAL(18,2)) AS Ingresos "
                            f"FROM [CHAT].[dbo].[{vista_ventas_detectada}] "
                            f"WHERE YEAR(Fecha) = {_anio_tablas}{_filtro_mes} AND Producto IS NOT NULL "
                            "GROUP BY Producto ORDER BY SUM(Total) DESC"
                        )).fetchall()
                        if filas:
                            results["tables"].append({
                                "id": "top5_productos",
                                "title": "Top 5 Productos",
                                "module": "VENTAS",
                                "columns": ["Producto", "Unidades", "Ingresos"],
                                "column_types": ["text", "number", "currency"],
                                "rows": [[str(f[0]).strip(), self._bi_float(f[1]), self._bi_float(f[2])] for f in filas],
                                "period_label": _periodo_tablas.upper(),
                                "hint": (
                                    f"Los 5 productos/conceptos de mayor ingreso del {_periodo_tablas} "
                                    f"({vista_ventas_detectada}). \"Unidades\" es la cantidad facturada "
                                    "de ese producto, no alumnos: no existe en esta base una relación "
                                    "directa entre cada factura y un curso o alumno específico."
                                ),
                            })
                    except Exception as e:
                        logger.info("[BI_PULSE] Tabla 'Top 5 Productos' omitida: %s", e)

                # RRHH
                # NOTA (Fase 3 — C1): [CHAT].[dbo].[ficha_trabajador] y
                # [CHAT].[dbo].[rol_pago] NO se reapuntan al cambiar de empresa
                # (verificado sobre 13 empresas reales, ver
                # core/integridad_vistas.py) — a diferencia de las vistas
                # comerciales, esto pasa SIEMPRE, sin importar si el SP tuvo
                # éxito (use_chat_views). Por eso estas dos tarjetas ya NO
                # intentan CHAT primero: van directo a las tablas físicas de
                # la empresa activa, que sí son confiables.
                if "tb_trabaj" in schema_tables_lower:
                    active = 0
                    try:
                        active = self._bi_int(self._scalar(connection, f"SELECT COUNT(*) FROM [{safe_db}].[dbo].[tb_trabaj] WHERE trb_estado = 1"))
                    except Exception:
                        pass

                    self._append_bi_card(results["cards"], id="hr_headcount", title="Empleados activos", value=active, unit="pers.", module="RRHH", accent="emerald")

                    if "tb_cabrol" in schema_tables_lower and "tb_detrol" in schema_tables_lower:
                        latest = None
                        try:
                            latest = connection.execute(text(f"SELECT TOP 1 YEAR(cro_fecini), MONTH(cro_fecini) FROM [{safe_db}].[dbo].[tb_cabrol] ORDER BY cro_fecini DESC")).fetchone()
                        except Exception:
                            pass

                        if latest:
                            py = latest[0]
                            pm_val = latest[1]
                            
                            _MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
                            
                            if isinstance(pm_val, str):
                                pm_str = pm_val
                                try:
                                    pm = _MESES_ES.index(pm_str) + 1
                                except ValueError:
                                    pm = 1
                            else:
                                pm = pm_val
                                pm_str = _MESES_ES[pm - 1]
                                
                            pl = self._bi_period_label(py, pm)
                            cost = 0.0

                            # Directo al ERP físico de esta empresa — CHAT.rol_pago
                            # nunca aísla correctamente, así que no vale la pena
                            # intentarlo primero (ver nota arriba).
                            try:
                                sql_light = (
                                    f"SELECT SUM(CASE r.rub_tipo WHEN 'I' THEN d.rol_valor WHEN 'E' THEN d.rol_valor * -1 ELSE 0 END) "
                                    f"FROM [{safe_db}].[dbo].[tb_detrol] d "
                                    f"INNER JOIN [{safe_db}].[dbo].[tb_rubros] r ON d.rol_codrub = r.rub_codigo "
                                    f"INNER JOIN [{safe_db}].[dbo].[tb_cabrol] c ON d.rol_numero = c.cro_numero "
                                    f"WHERE YEAR(c.cro_fecini) = {py} AND MONTH(c.cro_fecini) = {pm} "
                                    f"AND (r.rub_concep = 'S' OR (r.rub_concep = 'N' AND r.rub_tipo = 'E'))"
                                )
                                cost = self._bi_float(self._scalar(connection, sql_light))
                            except Exception:
                                pass


                            if cost > 0:
                                self._append_bi_card(results["cards"], id="hr_payroll_cost", title="Costo nómina", value=cost, unit="$", module="FINANZAS", period_label=pl, accent="emerald", wide=True)
                                self._append_focus_area(results["focus_areas"], area_id="nomina", module="FINANZAS", title="Corte de nómina listo", description=f"Último periodo: {pl}.", recommendation="Consulta cargos y sueldos.")

                # ── TARJETAS DEL CATÁLOGO DE MÉTRICAS CERTIFICADAS (Fase 2 — dashboards vivos) ──
                # A diferencia de los bloques anteriores (SQL fijo por tabla detectada), estas
                # tarjetas vienen de knowledge/metric_catalog.json ("dashboard_card": true).
                # Marlon puede sumar o quitar tarjetas del dashboard editando el JSON, sin tocar
                # este archivo. Solo se agregan si CHAT está activo (mismas vistas que usa el chat).
                if use_chat_views:
                    from core.metric_catalog import metricas_dashboard, series_dashboard
                    from core.integridad_vistas import vistas_no_aisladas_en_sql, vista_aislada_para_empresa
                    _accent_por_modulo = {
                        "VENTAS": "cyan", "OPERACIONES": "amber",
                        "RRHH": "emerald", "FINANZAS": "violet",
                    }
                    # El SQL del catálogo usa nombres de tabla SIN prefijo (cabecera_factura,
                    # rol_pago, ficha_trabajador...) porque esas son vistas que solo existen
                    # dentro de la base CHAT — igual que hace connector.execute_query(target_db="CHAT")
                    # en api/routes_query.py. Sin este USE, todas las consultas fallan con
                    # "objeto no válido" (silenciosamente, por el try/except de abajo).
                    try:
                        # NO re-ejecutar SP_MODIFICA_VISTA_IA aquí. El SP recrea vistas (DDL) y
                        # toma bloqueos de esquema sobre CHAT: mientras corre, TODA otra consulta
                        # contra esas vistas espera — incluido el chat. Se probó llamarlo aquí
                        # como defensa contra datos mezclados entre empresas y el costo fue
                        # inaceptable: dos DDL por carga de dashboard + uno por cada pregunta del
                        # chat = contención generalizada y lentitud en todo el sistema.
                        # El endpoint ya activó CHAT una vez antes de llegar aquí; con eso basta.
                        # La protección contra mezcla vive ahora en el frontend (no se lanzan dos
                        # peticiones de /bi/pulse a la vez) y en la caché del endpoint.
                        connection.execute(text("USE [CHAT]"))
                        # Espera máxima por bloqueos. Son ~16 consultas seguidas: con 4s cada una
                        # el peor caso eran 64s de espera. 1.5s falla rápido y la tarjeta
                        # problemática simplemente se omite en vez de frenar toda la página.
                        connection.execute(text("SET LOCK_TIMEOUT 1500"))
                    except Exception as e:
                        logger.warning("[BI_PULSE] No se pudo cambiar a la base CHAT para tarjetas de catálogo: %s", e)

                    has_rrhh_tables = "tb_trabaj" in schema_tables_lower or "tb_cabrol" in schema_tables_lower

                    for metrica in metricas_dashboard(anio=anio):
                        if metrica.get("modulo") == "RRHH" and not has_rrhh_tables:
                            continue  # Omitir tarjetas de RRHH si la empresa no maneja RRHH en su BD física
                        _vistas_riesgo = vistas_no_aisladas_en_sql(metrica["sql"])
                        if _vistas_riesgo and not all(
                            vista_aislada_para_empresa(self.connector, v, safe_db, target_db="CHAT")
                            for v in _vistas_riesgo
                        ):
                            # Fase 3 — C1/dinámico: antes esto se mostraba igual, solo con
                            # una bandera "integrity_warning" que el frontend nunca llegó
                            # a leer ni mostrar — en la práctica, un número que puede
                            # pertenecer a OTRA empresa se veía como si fuera normal.
                            # Mejor omitir la tarjeta que arriesgar una decisión mal
                            # tomada. Se verifica en vivo (ver core/integridad_vistas.py):
                            # se reactiva sola en cuanto la vista quede aislada para esta
                            # empresa, sin tocar código.
                            logger.info(
                                "[BI_PULSE] Tarjeta '%s' omitida: usa vista no aislada por empresa.",
                                metrica.get("id"),
                            )
                            continue
                        try:
                            cursor = connection.execute(text(metrica["sql"]))
                            key_list = list(cursor.keys())
                            row = cursor.fetchone()
                            label = key_list[0] if key_list else metrica["nombre"]
                            valor = row[0] if row else None
                            if valor is None:
                                continue  # sin datos en este período/empresa: se omite, no se muestra en 0 falso
                            self._append_bi_card(
                                results["cards"],
                                id=f"metric_{metrica['id']}",
                                title=metrica["nombre"],
                                value=self._bi_float(valor) if isinstance(valor, (int, float)) else valor,
                                unit="$" if "sueldo" in metrica["id"] or "ticket" in metrica["id"] or "margen" in metrica["id"] else "",
                                module=metrica["modulo"],
                                accent=_accent_por_modulo.get(metrica["modulo"], "cyan"),
                                primary_label=label,
                                period_label="Último período con datos",
                                hint=metrica["descripcion"],
                            )
                        except Exception as e:
                            logger.info("[BI_PULSE] Métrica de catálogo '%s' omitida: %s", metrica.get("id"), e)

                    # ── SERIES MENSUALES REALES (gráficos, no solo tarjetas de valor) ──
                    _MESES_CORTOS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
                    for serie in series_dashboard(anio=anio):
                        if serie.get("modulo") == "RRHH" and not has_rrhh_tables:
                            continue  # Omitir gráficos de RRHH si la empresa no maneja RRHH en su BD física
                        _vistas_riesgo_serie = vistas_no_aisladas_en_sql(serie["sql"])
                        if _vistas_riesgo_serie and not all(
                            vista_aislada_para_empresa(self.connector, v, safe_db, target_db="CHAT")
                            for v in _vistas_riesgo_serie
                        ):
                            # Fase 3 — C1/dinámico: mismo criterio que las tarjetas de
                            # arriba — un gráfico con datos que pueden ser de otra
                            # empresa no se muestra, aunque sea "solo un gráfico".
                            logger.info(
                                "[BI_PULSE] Gráfico '%s' omitido: usa vista no aislada por empresa.",
                                serie.get("id"),
                            )
                            continue
                        try:
                            cursor = connection.execute(text(serie["sql"]))
                            filas = cursor.fetchall()
                            if not filas:
                                continue

                            es_pie = serie.get("chart_type") == "pie"
                            labels, valores = [], []
                            for etiqueta, valor in filas:
                                if es_pie:
                                    # Distribución por categoría (área, cargo, proveedor...):
                                    # la etiqueta ya es el texto real, no un número de mes.
                                    labels.append(str(etiqueta or "Sin dato"))
                                else:
                                    # Las series de mes ahora devuelven el texto ya formado
                                    # ("Ene 2026") para que el eje muestre mes Y año — antes
                                    # devolvian solo el numero de mes (1-12) y se traducia
                                    # aqui. Se detectan ambos formatos: si `etiqueta` es un
                                    # numero puro se sigue traduciendo (compatibilidad con
                                    # cualquier metrica que aun no se haya migrado); si ya es
                                    # texto, se usa tal cual.
                                    texto_etiqueta = str(etiqueta or "").strip()
                                    if texto_etiqueta.isdigit() and 1 <= int(texto_etiqueta) <= 12:
                                        labels.append(_MESES_CORTOS[int(texto_etiqueta) - 1])
                                    else:
                                        labels.append(texto_etiqueta or "Sin dato")
                                valores.append(self._bi_float(valor))

                            # Tendencia: solo aplica a series temporales (bar). Una distribución
                            # por categoría (pie) no tiene "mes anterior" con qué compararse.
                            delta_pct = None
                            if not es_pie and len(valores) >= 2 and valores[-2]:
                                delta_pct = round(((valores[-1] - valores[-2]) / abs(valores[-2])) * 100, 1)

                                # ── ALERTAS AUTOMÁTICAS ──────────────────────────────────
                                # Umbral simple: caída (o alza) de 15% o más entre los dos
                                # últimos meses con datos, sobre una métrica certificada real
                                # (no una suposición de la IA). Así el usuario no tiene que
                                # revisar cada gráfico manualmente para notar un problema.
                                UMBRAL_ALERTA_PCT = 15.0
                                if abs(delta_pct) >= UMBRAL_ALERTA_PCT:
                                    es_caida = delta_pct < 0
                                    results.setdefault("alerts", []).append({
                                        "id": f"alert_{serie['id']}",
                                        "severity": "warning" if es_caida else "info",
                                        "module": serie["modulo"],
                                        "title": serie["nombre"],
                                        "message": (
                                            f"{serie['nombre']} {'cayó' if es_caida else 'subió'} "
                                            f"{abs(delta_pct)}% respecto al mes anterior "
                                            f"({labels[-2]} → {labels[-1]})."
                                        ),
                                        "delta_pct": delta_pct,
                                    })

                            results.setdefault("charts", []).append({
                                "id": serie["id"],
                                "title": serie["nombre"],
                                "module": serie["modulo"],
                                "chart_type": serie.get("chart_type", "bar"),
                                "accent": _accent_por_modulo.get(serie["modulo"], "cyan"),
                                "labels": labels,
                                "values": valores,
                                "delta_pct": delta_pct,
                                "hint": serie["descripcion"],
                            })
                        except Exception as e:
                            logger.info("[BI_PULSE] Serie de catálogo '%s' omitida: %s", serie.get("id"), e)
                # ──────────────────────────────────────────────────────────────────────────────

        except Exception as exc:
            logger.error("[BI_PULSE] Error: %s", exc)
            results["status"] = "partial_error"

        # ── FILTRO POR MÓDULOS PERMITIDOS (rol del usuario) ──────────────────
        # El pulso se construye según lo que el esquema REAL de la empresa
        # tiene (un colegio como MONT detecta el dominio académico), pero un
        # rol que no tiene habilitado ese módulo (ej. CONTABILIDAD) no debe
        # ver sus indicadores. Se filtra en el backend porque aquí es donde
        # está la fuente de verdad de permisos (JWT → allowed_modules). La
        # lógica vive en `filtrar_pulso_por_modulos` (función de módulo) para
        # poder reutilizarla al servir un snapshot precacheados (Capa 2).
        return filtrar_pulso_por_modulos(results, allowed_modules)
