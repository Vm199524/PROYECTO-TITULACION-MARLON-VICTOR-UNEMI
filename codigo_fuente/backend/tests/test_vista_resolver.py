"""
tests/test_vista_resolver.py — Detección en vivo del nombre real de la vista
de ventas/compras en CHAT.

CONTEXTO (bug real, 28/08/2026)
--------------------------------
"total de ventas por meses" y el resto de métricas certificadas de
ventas/compras fallaban con "objeto no válido" en cualquier empresa que no
fuera MONT (y a veces ni en esa). Causa: el SQL de esas métricas tiene
escrito literalmente "cabecera_factura"/"cabecera_compra", pero el usuario
confirmó con el árbol de vistas real del servidor que esas vistas NO EXISTEN
hoy en CHAT — lo desplegado es "Ventas" y "Compras". `core/vista_resolver.py`
centraliza la detección en vivo que ya se usaba (por separado, duplicada) en
core/mirror_manager.py y main.py, y ahora también en api/routes_query.py.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.vista_resolver import (
    CANDIDATOS_VENTAS,
    CANDIDATOS_COMPRAS,
    detectar_vista_sqlalchemy,
    detectar_vista_connector,
)


def test_candidatos_ventas_prueba_ventas_antes_que_cabecera_factura():
    assert CANDIDATOS_VENTAS == ("Ventas", "cabecera_factura")


def test_candidatos_compras_prueba_compras_antes_que_cabecera_compra():
    assert CANDIDATOS_COMPRAS == ("Compras", "cabecera_compra")


class FakeConnectorOk:
    """Doble de core.db_connector: execute_query(sql, target_db) -> (cols, rows, err)."""

    def __init__(self, nombres_que_existen: set[str]):
        self.nombres_que_existen = nombres_que_existen
        self.calls = []

    def execute_query(self, sql, execution_timeout=40, target_db=None):
        self.calls.append((sql, target_db))
        nombre = sql.split("[dbo].[")[1].split("]")[0]
        if nombre in self.nombres_que_existen:
            return ["col"], [[1]], None
        return [], [], "objeto no válido"


def test_detectar_vista_connector_encuentra_ventas_cuando_cabecera_factura_no_existe():
    """Reproduce el bug exacto: solo 'Ventas' existe en CHAT, 'cabecera_factura' no."""
    conn = FakeConnectorOk({"Ventas"})
    assert detectar_vista_connector(conn, CANDIDATOS_VENTAS, target_db="CHAT") == "Ventas"


def test_detectar_vista_connector_usa_cabecera_factura_si_es_lo_unico_que_existe():
    """Servidor con el nombre genérico desplegado en vez del nuevo: sigue funcionando."""
    conn = FakeConnectorOk({"cabecera_factura"})
    assert detectar_vista_connector(conn, CANDIDATOS_VENTAS, target_db="CHAT") == "cabecera_factura"


def test_detectar_vista_connector_ninguna_existe():
    conn = FakeConnectorOk(set())
    assert detectar_vista_connector(conn, CANDIDATOS_VENTAS, target_db="CHAT") is None


def test_detectar_vista_connector_connector_none():
    assert detectar_vista_connector(None, CANDIDATOS_VENTAS) is None


def test_detectar_vista_connector_consulta_siempre_contra_target_db():
    conn = FakeConnectorOk({"Ventas"})
    detectar_vista_connector(conn, CANDIDATOS_VENTAS, target_db="CHAT")
    assert conn.calls[0][1] == "CHAT"


def test_detectar_vista_compras():
    conn = FakeConnectorOk({"Compras"})
    assert detectar_vista_connector(conn, CANDIDATOS_COMPRAS, target_db="CHAT") == "Compras"


class FakeSqlAlchemyConnection:
    """Doble minimo de sqlalchemy.engine.Connection: .execute(text(sql)).fetchone()."""

    def __init__(self, nombres_que_existen: set[str]):
        self.nombres_que_existen = nombres_que_existen

    def execute(self, clause):
        sql = str(clause)
        nombre = sql.split("[dbo].[")[1].split("]")[0]
        if nombre not in self.nombres_que_existen:
            raise Exception("objeto no válido")
        return self

    def fetchone(self):
        return (1,)


def test_detectar_vista_sqlalchemy_mismo_comportamiento_que_connector():
    conn = FakeSqlAlchemyConnection({"Ventas"})
    assert detectar_vista_sqlalchemy(conn, CANDIDATOS_VENTAS, target_db="CHAT") == "Ventas"


def test_detectar_vista_sqlalchemy_ninguna_existe():
    conn = FakeSqlAlchemyConnection(set())
    assert detectar_vista_sqlalchemy(conn, CANDIDATOS_VENTAS, target_db="CHAT") is None
