"""
Pruebas de la exportación a Excel con varias hojas de Reportes BI.

Cubren las funciones auxiliares puras (validación del nombre de la base, que
evita inyección SQL, y formato de fecha y dinero) y el libro completo con un
conector simulado que responde las 5 consultas SQL: confirman que las hojas
salen en el orden correcto, con los encabezados correctos, y que "Cartera"
solo aparece para empresas educativas.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import openpyxl
import pytest

from core.excel_exporter import (
    _f,
    _fecha_str,
    _validar_db,
    generar_reporte_excel,
)


# ─── Helpers puros ────────────────────────────────────────────────────────


def test_validar_db_acepta_nombre_normal():
    assert _validar_db("mont") == "MONT"
    assert _validar_db(" song ") == "SONG"


@pytest.mark.parametrize("malicioso", ["MONT; DROP TABLE x", "MONT]--", "", None, "mo nt"])
def test_validar_db_rechaza_nombres_invalidos(malicioso):
    with pytest.raises(ValueError):
        _validar_db(malicioso)


def test_f_redondea_y_tolera_none():
    assert _f(10.456) == 10.46
    assert _f(None) == 0.0
    assert _f("no es numero", default=-1.0) == -1.0


def test_fecha_str_formatea_dd_mm_aaaa():
    assert _fecha_str(date(2026, 8, 28)) == "28/08/2026"
    assert _fecha_str(None) == ""


# ─── Libro completo, con conector simulado ───────────────────────────────


class FakeConnectorReportes:
    """
    Doble de core.db_connector: execute_query(sql, target_db) -> (cols, rows, err).

    Reconoce las consultas por una palabra clave distintiva en el SQL (la
    tabla o vista principal que consulta cada función de excel_exporter.py)
    y devuelve filas sintéticas con la forma exacta que cada consulta espera.
    """

    def __init__(self, es_educativa: bool):
        self.es_educativa = es_educativa
        self.calls = []

    def execute_query(self, sql, execution_timeout=40, target_db=None):
        self.calls.append(sql)
        s = sql.lower()

        if "sys.objects" in s:
            if "edu_alumno" in s or "tb_cabmovt" in s:
                return [""], [[1 if self.es_educativa else 0]], None
            if "vis_cobalu" in s:
                return [""], [[0]], None  # sin cobros disponibles, camino degradado
            return [""], [[0]], None

        if "group by m.mov_numdoc" in s:  # facturas
            return (
                ["factura"],
                [["F001", date(2026, 1, 5), "Cliente Uno", "0900000001", 3, 150.5, 3.0, "PENSIONES"]],
                None,
            )
        if "det_preuni as precio, d.det_canti as cantidad" in s and "group by" not in s:  # detalle items
            return (
                ["factura"],
                [["F001", date(2026, 1, 5), "0900000001", "Cliente Uno", "Pensión Enero", "PENSIONES", 50.0, 3.0, 150.5]],
                None,
            )
        if "group by d.det_nomart" in s:  # productos
            return (
                ["producto"],
                [["Pensión Enero", "PENSIONES", 61.0, 17377.68, 284.88, 284.88, 61, date(2026, 1, 13)]],
                None,
            )
        if "group by c.cli_ruccli" in s:  # clientes
            return (
                ["cedula"],
                [["0900000001", "Cliente Uno", 3, 450.0, date(2026, 3, 1), date(2026, 1, 5)]],
                None,
            )
        if "tb_cabmovt" in s and "mov_viaent" in s:  # cartera por rubro
            return (
                ["rubro"],
                [["PEN", 10240, 3160710.58, 0]],
                None,
            )
        return [], [], None


def test_libro_generico_no_tiene_hoja_cartera():
    conn = FakeConnectorReportes(es_educativa=False)
    buf, filename = generar_reporte_excel(conn, "SONG")

    assert filename.startswith("reporte_SONG_")
    wb = openpyxl.load_workbook(buf)
    assert wb.sheetnames == ["Facturas", "Detalle Items", "Productos", "Clientes"]


def test_libro_educativo_incluye_hoja_cartera():
    conn = FakeConnectorReportes(es_educativa=True)
    buf, _ = generar_reporte_excel(conn, "MONT")

    wb = openpyxl.load_workbook(buf)
    assert wb.sheetnames == ["Facturas", "Detalle Items", "Productos", "Clientes", "Cartera"]

    ws = wb["Cartera"]
    assert [c.value for c in ws[1]] == ["#", "Rubro", "Registros", "Facturado ($)", "Cobrado ($)", "Saldo ($)"]
    assert [c.value for c in ws[2]] == [1, "Pensiones", 10240, 3160710.58, 0, 3160710.58]


def test_hoja_facturas_tiene_los_encabezados_del_proyecto_origen():
    """La hoja Facturas usa los encabezados del formato de referencia y fechas dd/mm/aaaa."""
    conn = FakeConnectorReportes(es_educativa=False)
    buf, _ = generar_reporte_excel(conn, "SONG")
    wb = openpyxl.load_workbook(buf)
    ws = wb["Facturas"]
    assert [c.value for c in ws[1]] == [
        "#", "Factura", "Fecha", "Cédula / RUC", "Cliente", "Línea", "Ítems", "Unidades", "Total ($)",
    ]
    assert ws[2][2].value == "05/01/2026"  # fecha formateada dd/mm/aaaa


def test_nombre_de_base_se_valida_antes_de_consultar():
    conn = FakeConnectorReportes(es_educativa=False)
    with pytest.raises(ValueError):
        generar_reporte_excel(conn, "SONG; DROP TABLE x")
    assert conn.calls == []  # nunca llegó a ejecutar nada contra la base
