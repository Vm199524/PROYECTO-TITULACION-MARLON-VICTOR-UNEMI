"""
Pruebas de la verificación en vivo de las vistas de CHAT en Reportes BI.

CHAT es un espacio de vistas compartido por todo el servidor (no por sesión):
otra petición concurrente puede reapuntar sus vistas a otra empresa justo antes
de que Reportes BI las lea y mostrar, por ejemplo, pensiones de colegio en una
empresa agrícola. Las tarjetas que construyen su SQL a mano contra
`[CHAT].[dbo].[...]` no pasan por la verificación del catálogo genérico (ver
tests/test_integridad_vistas.py), así que `MirrorManager._vista_confiable_para`
confirma en vivo que la definición ACTUAL de la vista apunta a la base de la
empresa conectada. Reportes BI solo muestra datos de la empresa activa.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
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
    """CHAT.cabecera_factura apunta a MONT con SONG activa: la vista no es confiable."""
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
