"""
Pruebas de la detección en vivo de las vistas de ventas y compras en CHAT.

El SQL de las métricas certificadas de ventas/compras usa "cabecera_factura" y
"cabecera_compra", pero en CHAT las vistas desplegadas pueden llamarse
"Ventas" y "Compras"; con el nombre fijo, la consulta fallaría con "objeto no
válido". `core/vista_resolver.py` centraliza la detección en vivo que usan
core/mirror_manager.py, main.py y api/routes_query.py: prueba primero el
nombre nuevo y, si no existe, el genérico.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
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
    """Solo 'Ventas' existe en CHAT y 'cabecera_factura' no: se usa 'Ventas'."""
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
    """Doble mínimo de sqlalchemy.engine.Connection: .execute(text(sql)).fetchone()."""

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
