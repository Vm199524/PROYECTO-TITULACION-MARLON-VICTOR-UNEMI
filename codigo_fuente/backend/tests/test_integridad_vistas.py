"""
Pruebas de la advertencia sobre vistas que no aíslan los datos por empresa.

`ficha_trabajador` y `rol_pago` leen siempre de una única base física RRHH, y
CHAT es un espacio de vistas compartido por todo el servidor: una petición
concurrente puede reapuntar `cabecera_factura`, `cabecera_compra`, `VIS_ALUMNO`
o "Ventas"/"Compras" a otra empresa justo antes de una consulta y mostrar datos
ajenos. Las pruebas protegen las dos capas: la detección estática marca SIEMPRE
esas vistas como de riesgo, y la verificación dinámica (`vista_aislada_para_empresa`)
decide en cada uso si apuntan a la base de la empresa conectada.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import pytest

from core.integridad_vistas import (
    sql_usa_vista_no_aislada,
    vistas_no_aisladas_en_sql,
    vista_aislada_para_empresa,
    todas_aisladas_para_empresa,
    mensaje_advertencia,
    mensaje_sincronizacion_pendiente,
    pregunta_es_de_nomina,
    resolver_aviso_integridad,
)


class FakeConnector:
    """Doble de prueba para core.db_connector.DatabaseConnector.execute_query:
    misma firma (sql, execution_timeout, target_db) -> (columnas, filas, error)."""

    def __init__(self, definicion=None, err=None):
        self.definicion = definicion
        self.err = err
        self.calls = []

    def execute_query(self, sql, execution_timeout=40, target_db=None):
        self.calls.append((sql, target_db))
        if self.err:
            return [], [], self.err
        return ["col"], [[self.definicion]], None


class TestDeteccionDeVistasAfectadas:
    @pytest.mark.parametrize("sql", [
        "SELECT COUNT(*) FROM ficha_trabajador",
        "SELECT * FROM [CHAT].[dbo].[ficha_trabajador]",
        "SELECT SUM(Valor) FROM rol_pago WHERE [Año] = 2026",
        "WITH Base AS (SELECT * FROM rol_pago) SELECT COUNT(*) FROM Base",
        "select cargo from FICHA_TRABAJADOR",  # insensible a mayúsculas
    ])
    def test_detecta_vistas_no_aisladas(self, sql):
        assert sql_usa_vista_no_aislada(sql) is True, (
            f"No se detectó una vista afectada en: {sql}"
        )
        assert vistas_no_aisladas_en_sql(sql), (
            f"vistas_no_aisladas_en_sql no encontró nada en: {sql}"
        )

    @pytest.mark.parametrize("sql", [
        "SELECT SUM(Total) FROM cabecera_factura",
        "SELECT COUNT(*) FROM cabecera_compra",
        "SELECT TOP 5 Proveedor FROM cabecera_compra GROUP BY Proveedor",
        "SELECT SUM(Total) FROM Ventas WHERE Linea = 'PENSIONES'",
        "SELECT COUNT(*) FROM VIS_ALUMNO WHERE ESTADO = 'MATRICULADO'",
    ])
    def test_vistas_comerciales_y_academicas_quedan_marcadas(self, sql):
        """
        Ventas/compras/alumnos se reapuntan bien POR EMPRESA, pero CHAT es un
        espacio de nombres compartido por todo el servidor y otra petición
        puede dejarlas apuntando a otra empresa. Por eso la detección estática
        las marca SIEMPRE; es la verificación dinámica (más abajo) la que
        decide si son confiables en cada uso concreto, no esta función.
        """
        assert sql_usa_vista_no_aislada(sql) is True, (
            f"Debería marcarse para verificación dinámica: {sql}"
        )
        assert vistas_no_aisladas_en_sql(sql)

    def test_marcarlas_no_es_bloquearlas_si_la_verificacion_dinamica_confia(self):
        """
        El sentido de la doble capa: una vista marcada NO se bloquea a ciegas.
        Con la vista apuntando de verdad a la empresa conectada, la
        verificación dinámica la confirma como confiable.
        """
        conn = FakeConnector("CREATE VIEW cabecera_factura AS SELECT * FROM [GYMM].[dbo].[tb_cabmov]")
        assert vistas_no_aisladas_en_sql("SELECT SUM(Total) FROM cabecera_factura")
        assert vista_aislada_para_empresa(conn, "cabecera_factura", "GYMM", target_db="CHAT") is True

    def test_la_fuga_real_queda_bloqueada(self):
        """
        SONG es la empresa activa, pero CHAT.cabecera_factura quedó apuntando
        a MONT por una activación concurrente. La verificación dinámica debe
        rechazarla.
        """
        conn = FakeConnector("CREATE VIEW cabecera_factura AS SELECT * FROM [MONT].[dbo].[tb_cabmov]")
        assert vista_aislada_para_empresa(conn, "cabecera_factura", "SONG", target_db="CHAT") is False

    def test_sql_vacio_no_rompe(self):
        assert sql_usa_vista_no_aislada("") is False
        assert sql_usa_vista_no_aislada(None) is False
        assert vistas_no_aisladas_en_sql("") == []
        assert vistas_no_aisladas_en_sql(None) == []

    def test_devuelve_los_nombres_encontrados(self):
        assert vistas_no_aisladas_en_sql(
            "SELECT * FROM ficha_trabajador f JOIN rol_pago r ON 1=1"
        ) == ["ficha_trabajador", "rol_pago"]


class TestFalsosPositivosPorTextoLibre:
    """
    "Ventas" y "Compras" son palabras comunes del español de negocio, así que
    aparecen todo el tiempo en texto que NO es una referencia a una tabla: un
    alias de columna legible o un valor de texto en un discriminador de UNION
    ALL. Esos casos no deben disparar el aviso de integridad para un SQL que
    ni siquiera toca esas vistas.
    """

    @pytest.mark.parametrize("sql", [
        "SELECT MONTH(Fecha) AS Mes, SUM(Total) AS [Total Ventas] FROM FACTURADOCOLEGIO GROUP BY MONTH(Fecha)",
        "SELECT Proveedor, SUM(Monto) AS [Compras del Mes] FROM PAGO_PROVEEDORES GROUP BY Proveedor",
    ])
    def test_alias_de_columna_no_cuenta_como_vista_tocada(self, sql):
        assert vistas_no_aisladas_en_sql(sql) == [], (
            f"El alias de columna disparó un falso positivo en: {sql}"
        )

    def test_literal_de_texto_en_union_all_no_cuenta_como_vista_tocada(self):
        sql = (
            "SELECT 'Ventas' AS Tipo, f.Factura, f.Fecha, CAST(f.Facturado AS DECIMAL(18,2)) AS Monto "
            "FROM FACTURADOCOLEGIO f "
            "UNION ALL "
            "SELECT 'Compra', p.Documento_de_pago, p.fecha_emision, CAST(p.monto_pagado AS DECIMAL(18,2)) "
            "FROM PAGO_PROVEEDORES p"
        )
        assert vistas_no_aisladas_en_sql(sql) == [], (
            "El literal de texto 'Ventas'/'Compra' disparó un falso positivo"
        )

    def test_referencia_real_a_la_vista_se_sigue_detectando_pese_al_filtro(self):
        # El filtro de ruido no debe volverse tan agresivo que oculte un caso
        # real: la vista referenciada de verdad (fuera de comillas/alias)
        # sigue detectándose.
        sql = "SELECT SUM(Total) AS [Total Ventas] FROM Ventas WHERE YEAR(Fecha) = 2026"
        assert vistas_no_aisladas_en_sql(sql) == ["Ventas"]


class TestMensaje:
    def test_el_mensaje_explica_y_orienta(self):
        """
        El aviso debe decir QUÉ pasa y QUÉ hacer. Un texto vago haría que el
        usuario lo ignore y tome decisiones sobre datos incorrectos igual.
        """
        msg = mensaje_advertencia()
        assert msg, "El mensaje de advertencia no puede estar vacío"
        assert "empresa" in msg.lower()
        assert "SP_MODIFICA_VISTA_IA" in msg, (
            "El mensaje debe nombrar el procedimiento involucrado en la solución"
        )
        assert "ventas" in msg.lower(), (
            "El mensaje debe aclarar qué datos SÍ son confiables, para no "
            "sembrar desconfianza sobre todo el sistema"
        )


class TestVerificacionDinamicaPorEmpresa:
    """
    vista_aislada_para_empresa consulta en vivo la definición de la vista y
    decide, por empresa, si sus datos son confiables HOY — sin depender de
    una lista fija ni de una fecha de verificación pasada.
    """

    def test_agrinag_confia_en_su_propia_vista_rrhh(self):
        # ficha_trabajador real: usa el atajo rrhh..tabla (sin 'dbo' explícito).
        conn = FakeConnector("CREATE VIEW ficha_trabajador AS SELECT * FROM rrhh..tb_trabaj")
        assert vista_aislada_para_empresa(conn, "ficha_trabajador", "RRHH", target_db="CHAT") is True
        # La definición se debe leer desde CHAT (donde vive la vista), no desde RRHH.
        assert conn.calls[0][1] == "CHAT"

    def test_otra_empresa_no_confia_en_la_misma_vista(self):
        conn = FakeConnector("CREATE VIEW ficha_trabajador AS SELECT * FROM rrhh..tb_trabaj")
        assert vista_aislada_para_empresa(conn, "ficha_trabajador", "MONT", target_db="CHAT") is False

    def test_rol_pago_forma_con_puntos_sin_corchetes(self):
        # Definición real de rol_pago: RRHH.dbo.tb_cabrol, RRHH.dbo.tb_detrol.
        conn = FakeConnector(
            "CREATE VIEW rol_pago AS SELECT * FROM RRHH.dbo.tb_cabrol "
            "INNER JOIN RRHH.dbo.tb_detrol ON 1=1"
        )
        assert vista_aislada_para_empresa(conn, "rol_pago", "RRHH", target_db="CHAT") is True
        assert vista_aislada_para_empresa(conn, "rol_pago", "ALIM", target_db="CHAT") is False

    def test_vista_corregida_en_el_futuro_queda_confiable_sin_tocar_codigo(self):
        """Si la vista pasa a filtrar por empresa y se reapunta correctamente,
        el mecanismo lo reconoce solo: ese es el sentido de verificar en vivo."""
        conn = FakeConnector(
            "CREATE VIEW ficha_trabajador AS SELECT * FROM [DAUN].[dbo].[tb_trabaj] WHERE trb_empre = 1"
        )
        assert vista_aislada_para_empresa(conn, "ficha_trabajador", "DAUN", target_db="CHAT") is True

    def test_ante_cualquier_duda_no_confia(self):
        assert vista_aislada_para_empresa(None, "ficha_trabajador", "RRHH") is False
        conn = FakeConnector("CREATE VIEW x AS SELECT * FROM rrhh..tb_trabaj")
        # Nombre de vista inválido: se rechaza antes de tocar la base.
        assert vista_aislada_para_empresa(conn, "vista; DROP TABLE x", "RRHH") is False
        conn_err = FakeConnector(None, err="objeto no válido")
        assert vista_aislada_para_empresa(conn_err, "ficha_trabajador", "SONG", target_db="CHAT") is False

    def test_todas_aisladas_requiere_unanimidad(self):
        conn = FakeConnector("CREATE VIEW x AS SELECT * FROM rrhh..tb_trabaj")
        assert todas_aisladas_para_empresa(
            conn, ["ficha_trabajador", "rol_pago"], "RRHH", target_db="CHAT"
        ) is True
        assert todas_aisladas_para_empresa(
            conn, ["ficha_trabajador", "rol_pago"], "ENIG", target_db="CHAT"
        ) is False
        assert todas_aisladas_para_empresa(conn, [], "RRHH") is True

    def test_resultado_se_cachea_por_empresa_vista_y_base_consultada(self):
        conn = FakeConnector("CREATE VIEW ficha_trabajador AS SELECT * FROM rrhh..tb_trabaj")
        vista_aislada_para_empresa(conn, "ficha_trabajador", "RRHH", target_db="CHAT")
        llamadas_previas = len(conn.calls)
        vista_aislada_para_empresa(conn, "ficha_trabajador", "RRHH", target_db="CHAT")
        assert len(conn.calls) == llamadas_previas, "debió usar la caché en vez de re-consultar"


class TestCatalogoDeMetricasAfectadas:
    def test_metricas_rrhh_del_catalogo_quedan_marcadas(self):
        """
        Recorre el catálogo real: toda métrica que consulte las vistas
        afectadas debe activar la advertencia. Una métrica nueva de RRHH queda
        cubierta automáticamente.
        """
        from core.metric_catalog import _cargar_catalogo

        afectadas = [
            m["id"] for m in _cargar_catalogo()
            if vistas_no_aisladas_en_sql(m.get("sql", ""))
        ]

        # Verificación de que el mecanismo realmente alcanza al catálogo real.
        assert len(afectadas) >= 5, (
            f"Se esperaban varias métricas de RRHH/nómina marcadas, hay {len(afectadas)}: {afectadas}"
        )
        for esperada in ("empleados_activos", "nomina_total_ultimo_mes"):
            assert esperada in afectadas, f"'{esperada}' deberia estar marcada"

    def test_metricas_comerciales_tambien_quedan_marcadas(self):
        """
        Lo comercial NO es sinónimo de "siempre confiable sin verificar":
        CHAT es compartido y puede quedar apuntando a otra empresa. Estas
        métricas se marcan igual que las de RRHH, para que finalize_response
        (api/routes_query.py) las verifique en vivo antes de responder.
        """
        from core.metric_catalog import _cargar_catalogo

        por_id = {m["id"]: m.get("sql", "") for m in _cargar_catalogo()}
        for id_metrica in ("ventas_total_anual", "compras_total_anual", "top_proveedores"):
            if id_metrica in por_id:
                assert vistas_no_aisladas_en_sql(por_id[id_metrica]), (
                    f"'{id_metrica}' consulta una vista de CHAT y debería marcarse "
                    "para verificación dinámica"
                )


class TestPreguntaEsDeNomina:
    """
    finalize_response llama a esta función siempre que el SQL toca una vista
    de riesgo, así que un error en ella (por ejemplo, un NameError por un
    módulo sin importar) rompería TODAS las consultas, no solo las de nómina.
    Por eso la prueba no solo verifica el resultado booleano: comprueba que la
    función se pueda llamar sin fallar con preguntas reales, incluidas las que
    llevan tildes.
    """

    @pytest.mark.parametrize("pregunta", [
        "total de ventas por meses del 2026",
        "muestrame el detalle de ventas y compras del período más reciente",
        "top 10 productos más vendidos",
        "",
    ])
    def test_preguntas_ajenas_a_nomina_no_fallan_y_dan_false(self, pregunta):
        assert pregunta_es_de_nomina(pregunta) is False

    @pytest.mark.parametrize("pregunta", [
        "rol de pago de agosto",
        "empleados activos por área",
        "cuántos trabajadores tiene la empresa",
        "detalle de nómina del mes",
        "sueldos del personal de ventas",
    ])
    def test_preguntas_de_nomina_dan_true(self, pregunta):
        assert pregunta_es_de_nomina(pregunta) is True


class TestResolverAvisoIntegridad:
    """
    `resolver_aviso_integridad` distingue TRES caminos. Un SQL que solo toca
    [Ventas]/[Compras] (por ejemplo, el de "muéstrame el detalle de ventas y
    compras del período más reciente", que no usa ficha_trabajador/rol_pago)
    con vistas no confirmadas como aisladas en ese momento recibe un aviso de
    sincronización, no el aviso fijo de "talento humano no disponible". Las
    vistas de nómina con una pregunta ajena son un fallo de generación, y con
    una pregunta de nómina reciben el aviso de integridad habitual.
    """

    def test_solo_ventas_compras_no_aisladas_da_mensaje_de_sincronizacion_no_de_nomina(self):
        resultado = resolver_aviso_integridad(
            ["Ventas", "Compras"],
            "muestrame el detalle de ventas y compras del periodo mas reciente",
            "AGGO",
        )
        assert resultado["status"] == "integrity_blocked"
        assert "talento humano" not in resultado["explanation"].lower()
        assert "ficha_trabajador" not in resultado["explanation"].lower()
        assert "sincroniz" in resultado["explanation"].lower()

    def test_vis_alumno_no_aislada_tambien_usa_mensaje_de_sincronizacion(self):
        resultado = resolver_aviso_integridad(["VIS_ALUMNO"], "cuantos alumnos hay matriculados", "MONT")
        assert resultado["status"] == "integrity_blocked"
        assert "talento humano" not in resultado["explanation"].lower()

    def test_nomina_no_aislada_con_pregunta_ajena_es_fallo_de_generacion(self):
        resultado = resolver_aviso_integridad(
            ["ficha_trabajador", "rol_pago"],
            "total de ventas por meses del 2026",
            "SONG",
        )
        assert resultado["status"] == "error"
        assert resultado["sql"] == ""
        assert "talento humano" not in resultado["explanation"].lower()

    def test_nomina_no_aislada_con_pregunta_de_nomina_usa_el_aviso_historico(self):
        resultado = resolver_aviso_integridad(
            ["ficha_trabajador"],
            "cuantos empleados activos hay por area",
            "SONG",
        )
        assert resultado["status"] == "integrity_blocked"
        assert resultado["explanation"] == mensaje_advertencia()

    def test_mensaje_sincronizacion_menciona_las_vistas_y_la_empresa(self):
        texto = mensaje_sincronizacion_pendiente(["Ventas", "Compras"], "AGGO")
        assert "AGGO" in texto
        assert "Compras" in texto and "Ventas" in texto
        assert "talento humano" not in texto.lower()
