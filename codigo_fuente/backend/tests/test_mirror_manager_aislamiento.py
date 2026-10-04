"""
tests/test_mirror_manager_aislamiento.py — Verificación en vivo antes de que
Reportes BI confíe en una vista de CHAT.

CONTEXTO (bug real, 28/08/2026)
--------------------------------
Con SONG (FOODGARDEN S.A., empresa agrícola) como empresa activa, Reportes BI
mostró las tarjetas "Ingresos por Línea de Negocio" y "Top 5 Productos" con
datos reales de MONT (pensiones de colegio). Causa: CHAT es un namespace de
vistas COMPARTIDO por todo el servidor (no por sesión) — otra petición
concurrente había re-apuntado sus vistas a MONT justo antes de que el pulso
de SONG corriera. Las tres tarjetas afectadas (Balance Comercial, académica,
y las dos tablas nuevas) construyen su SQL a mano contra `[CHAT].[dbo].[...]`
y por eso no pasaban por la verificación que sí protege a las métricas del
catálogo genérico (ver tests/test_integridad_vistas.py).

`MirrorManager._vista_confiable_para` es el punto único donde se cerró ese
hueco: antes de leer cualquier vista de CHAT a mano, se confirma en vivo que
su definición ACTUAL apunta a la misma base que la empresa conectada. Esta
regla es fija: Reportes BI solo muestra datos de la empresa activa.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from core.mirror_manager import MirrorManager


class FakeConnector:
    """
    Mismo doble que usa tests/test_integridad_vistas.py: simula
    execute_query(sql, target_db) -> (columnas, filas, error), que es lo
    único que `vista_aislada_para_empresa` necesita del conector.
    """

    def __init__(self, definicion=None, err=None):
        self.definicion = definicion
        self.err = err
        self.calls = []
        self.engine = None  # MirrorManager.__init__ lo espera; no se usa aquí.

    def execute_query(self, sql, execution_timeout=40, target_db=None):
        self.calls.append((sql, target_db))
        if self.err:
            return [], [], self.err
        return ["col"], [[self.definicion]], None


def test_confia_cuando_la_vista_apunta_a_la_empresa_conectada():
    conn = FakeConnector("CREATE VIEW Ventas AS SELECT * FROM [SONG].[dbo].[tb_cabmov]")
    mm = MirrorManager(conn)
    assert mm._vista_confiable_para("Ventas", "SONG") is True


def test_no_confia_cuando_la_vista_apunta_a_otra_empresa():
    """Reproduce el bug exacto: CHAT.cabecera_factura apuntando a MONT con SONG activa."""
    conn = FakeConnector("CREATE VIEW cabecera_factura AS SELECT * FROM [MONT].[dbo].[tb_cabmov]")
    mm = MirrorManager(conn)
    assert mm._vista_confiable_para("cabecera_factura", "SONG") is False


def test_no_confia_ante_error_de_consulta():
    conn = FakeConnector(None, err="objeto no válido")
    mm = MirrorManager(conn)
    assert mm._vista_confiable_para("cabecera_factura", "SONG") is False


def test_consulta_siempre_contra_chat_no_contra_la_empresa():
    """La definición de la vista vive en CHAT, nunca en la base de la empresa."""
    conn = FakeConnector("CREATE VIEW VIS_ALUMNO AS SELECT * FROM [MONT].[dbo].[edu_alumno]")
    mm = MirrorManager(conn)
    mm._vista_confiable_para("VIS_ALUMNO", "MONT")
    assert conn.calls[-1][1] == "CHAT"
