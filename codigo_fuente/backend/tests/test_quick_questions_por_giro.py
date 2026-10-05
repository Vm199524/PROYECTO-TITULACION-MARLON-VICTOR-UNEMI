"""
Pruebas de las sugerencias "Prueba preguntando" según el giro de la empresa.

Las sugerencias deben corresponder SIEMPRE a la lógica de negocio de la empresa
activa. Un colegio que alguna vez compró útiles de oficina tiene filas en
cabecera_compra, pero proveedores y compras no son su negocio (sí lo son
alumnos, pensiones y matrículas). Por eso `get_capability_snapshot`
(core/mirror_manager.py) excluye el dominio "finanzas" cuando el dominio
"academico" está activo, igual que excluye "operaciones" en colegios sin
inventario real, y adapta al colegio el texto del dominio "ventas".

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.mirror_manager import MirrorManager


class FakeConnectorConSonda:
    """
    Doble de core.db_connector: solo necesita responder a la sonda de datos
    que get_capability_snapshot ejecuta como un único SELECT con subconsultas
    con alias (rrhh, nomina, finanzas, ventas, operaciones, academico).
    """

    def __init__(self, dominios_con_datos: set[str]):
        self.dominios_con_datos = dominios_con_datos
        self.engine = None

    def execute_query(self, sql, execution_timeout=40, target_db=None):
        # El SQL real es "SELECT (SELECT TOP 1 1 FROM [tabla]) AS dominio, ..."
        # Se extraen los alias en el mismo orden en que aparecen.
        import re

        alias_en_orden = re.findall(r"AS (\w+)", sql)
        fila = [1 if alias in self.dominios_con_datos else None for alias in alias_en_orden]
        return alias_en_orden, [fila], None


def _schema_colegio_con_alguna_compra():
    """
    Esquema físico de un colegio típico: tablas académicas reales, más
    edu_alumno/tb_cabmov1 (facturación) y un puñado de compras registradas
    (tb_cabmov1/tb_detmov1 existen), que es justo el caso que no debe activar
    las sugerencias de "finanzas".
    """
    tablas = [
        "edu_alumno", "vis_alumno", "tb_cabmov", "cabecera_factura",
        "tb_cabmov1", "cabecera_compra", "tb_detmov1", "tb_provee",
    ]
    return {t: {"type": "TABLA", "columns": [], "row_count": 5} for t in tablas}


def test_finanzas_no_aparece_en_sugerencias_de_un_colegio():
    schema = _schema_colegio_con_alguna_compra()
    # "finanzas" SÍ tiene datos (una compra de útiles), pero eso no basta para
    # sugerir proveedores/compras. "academico" y "ventas" también tienen datos.
    conn = FakeConnectorConSonda({"finanzas", "academico", "ventas"})
    mm = MirrorManager(conn)

    snap = mm.get_capability_snapshot("MONT", schema)

    ids_areas = {a["id"] for a in snap["areas"]}
    assert "finanzas" not in ids_areas, "finanzas no debe listarse como area para un colegio"

    texto_preguntas = " ".join(snap["quick_questions"]).lower()
    assert "proveedor" not in texto_preguntas
    assert "compra" not in texto_preguntas


def test_ventas_y_academico_si_aparecen_en_un_colegio():
    """La exclusión es específica a finanzas/compras, no a todo lo comercial:
    un colegio SÍ vive de facturar pensiones y matrículas (dominio ventas)."""
    schema = _schema_colegio_con_alguna_compra()
    conn = FakeConnectorConSonda({"finanzas", "academico", "ventas"})
    mm = MirrorManager(conn)

    snap = mm.get_capability_snapshot("MONT", schema)

    assert "ACADEMICO" in snap["modules"]
    assert "VENTAS" in snap["modules"]
    texto_preguntas = " ".join(snap["quick_questions"]).lower()
    assert "estudiantes" in texto_preguntas or "alumnos" in texto_preguntas


def test_ventas_usa_lenguaje_de_colegio_no_de_retail():
    """En un colegio el dominio "ventas" sigue activo (factura pensiones y
    matrículas), pero no debe sugerir "10 productos más vendidos" ni "ranking
    de vendedores": ocultar "finanzas" no basta, el texto de "ventas" también
    se adapta al giro académico."""
    schema = _schema_colegio_con_alguna_compra()
    conn = FakeConnectorConSonda({"finanzas", "academico", "ventas"})
    mm = MirrorManager(conn)

    snap = mm.get_capability_snapshot("MONT", schema)

    assert "VENTAS" in snap["modules"]
    texto_preguntas = " ".join(snap["quick_questions"]).lower()
    assert "producto" not in texto_preguntas
    assert "vendedor" not in texto_preguntas
    assert "facturado" in texto_preguntas or "pensión" in texto_preguntas or "pension" in texto_preguntas


def test_finanzas_si_aparece_en_una_empresa_no_academica():
    """La exclusión es SOLO para instituciones académicas — una empresa
    comercial normal sigue viendo sus preguntas de compras/proveedores."""
    tablas = ["tb_client", "tb_cabmov", "cabecera_factura",
              "tb_cabmov1", "cabecera_compra", "tb_detmov1", "tb_provee"]
    schema = {t: {"type": "TABLA", "columns": [], "row_count": 5} for t in tablas}
    conn = FakeConnectorConSonda({"finanzas", "ventas"})
    mm = MirrorManager(conn)

    snap = mm.get_capability_snapshot("SONG", schema)

    ids_areas = {a["id"] for a in snap["areas"]}
    assert "finanzas" in ids_areas
    texto_preguntas = " ".join(snap["quick_questions"]).lower()
    assert "proveedor" in texto_preguntas or "compra" in texto_preguntas
