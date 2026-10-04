"""
Pruebas de las TRES capas de seguridad del motor conversacional (criterio de
éxito c del documento: "el aislamiento de datos por institución se verifica a
nivel del motor de base de datos").

  Capa 3 (aplicación)  core/sql_sanitizer.py rechaza todo lo que no sea lectura.
  Capa 2 (semántica)   el LLM solo ve y consulta vistas VIS_*.
  Capa 1 (motor BD)    la cuenta chat_reader solo tiene SELECT sobre VIS_*,
                       y cada vista filtra por SESSION_CONTEXT('empresa_activa').

Las pruebas de la capa 1 son de INTEGRACIÓN: usan el SQL Server real con dos
instituciones cargadas (UNEMI_PRUEBAS y OULAD_UK) y se omiten si la base no
está disponible. Son la evidencia de que la garantía no depende del código de
la aplicación: aunque el sanitizador fallara, el motor rechaza la operación.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sql_sanitizer import sanitize_pipeline, validate_readonly  # noqa: E402

pyodbc = pytest.importorskip("pyodbc")


# ── Capa 3: sanitizador (sin base de datos) ────────────────────────────────
@pytest.mark.parametrize("sql", [
    "DELETE FROM VIS_ALUMNO",
    "UPDATE VIS_ALUMNO SET promedio = 10",
    "DROP TABLE fact_matriculas",
    "INSERT INTO VIS_ALUMNO (cedula) VALUES ('1')",
    "EXEC xp_cmdshell 'dir'",
    "SELECT 1; DROP TABLE fact_matriculas",
    "EXEC sp_set_session_context @key=N'empresa_activa', @value=N'OULAD_UK'",
    "TRUNCATE TABLE dim_alumno",
])
def test_sanitizador_rechaza_escritura_y_ejecucion(sql):
    ok, _ = validate_readonly(sql)
    assert not ok


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(DISTINCT cedula) FROM VIS_ALUMNO WHERE es_ultimo_periodo = 1",
    "WITH r AS (SELECT carrera, COUNT(*) n FROM VIS_PREDICCION_ABANDONO GROUP BY carrera) SELECT * FROM r",
])
def test_sanitizador_acepta_lectura(sql):
    ok, _ = validate_readonly(sql)
    assert ok
    _, valido, _ = sanitize_pipeline(sql, "pregunta de prueba")
    assert valido


# ── Capa 1: motor de base de datos (integración) ───────────────────────────
def _conectar_chat_reader():
    from config import DEFAULT_HOST
    user, pwd = os.getenv("CHAT_READER_USER"), os.getenv("CHAT_READER_PASSWORD")
    if not user or not pwd:
        pytest.skip("CHAT_READER_USER/PASSWORD no configurados en backend/.env")
    cs = (f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DEFAULT_HOST or 'localhost,1433'};"
          f"DATABASE=CHAT;UID={user};PWD={pwd};TrustServerCertificate=yes;Encrypt=no;")
    try:
        return pyodbc.connect(cs, autocommit=True, timeout=5)
    except pyodbc.Error as e:
        pytest.skip(f"SQL Server no disponible: {e.args[0] if e.args else e}")


@pytest.fixture
def lector():
    conn = _conectar_chat_reader()
    yield conn
    conn.close()


def _contexto(cur, empresa):
    cur.execute("EXEC sp_set_session_context @key=N'empresa_activa', @value=?", empresa)


def _denegado(cur, sql) -> bool:
    try:
        cur.execute(sql)
        cur.fetchall()
        return False
    except pyodbc.Error:
        return True


@pytest.mark.integracion
@pytest.mark.parametrize("sql", [
    "SELECT TOP 1 * FROM UNEMI_PRUEBAS.dbo.alumnos_prueba",       # base operativa
    "SELECT TOP 1 * FROM OULAD_PRUEBAS.dbo.historial_bloques",     # base operativa de la otra IES
    "SELECT TOP 1 * FROM dbo.fact_matriculas",                     # tabla física del warehouse
    "SELECT TOP 1 * FROM dbo.dim_alumno",
    "SELECT TOP 1 * FROM dbo.fact_prediccion_abandono",
])
def test_chat_reader_no_puede_leer_fuera_de_las_vistas(lector, sql):
    cur = lector.cursor()
    _contexto(cur, "UNEMI_PRUEBAS")
    assert _denegado(cur, sql), f"chat_reader PUDO ejecutar: {sql}"


@pytest.mark.integracion
@pytest.mark.parametrize("sql", [
    "INSERT INTO dbo.VIS_EVALUACION_MODELO (componente) VALUES ('X')",
    "UPDATE dbo.VIS_CLUSTER_CARRERA SET cluster_label = 'X'",
    "DELETE FROM dbo.VIS_BENCHMARK_EXTERNO",
    "CREATE TABLE dbo.tmp_ataque (x INT)",
])
def test_chat_reader_no_puede_escribir(lector, sql):
    assert _denegado(lector.cursor(), sql), f"chat_reader PUDO ejecutar: {sql}"


@pytest.mark.integracion
def test_aislamiento_entre_dos_instituciones(lector):
    cur = lector.cursor()
    _contexto(cur, "UNEMI_PRUEBAS")
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN cedula LIKE 'OU%' THEN 1 ELSE 0 END) FROM dbo.VIS_ALUMNO")
    total_unemi, filas_oulad = cur.fetchone()
    assert total_unemi > 0 and (filas_oulad or 0) == 0

    _contexto(cur, "OULAD_UK")
    cur.execute("SELECT COUNT(*), SUM(CASE WHEN cedula LIKE 'OU%' THEN 1 ELSE 0 END) FROM dbo.VIS_ALUMNO")
    total_oulad, solo_oulad = cur.fetchone()
    assert total_oulad > 0 and solo_oulad == total_oulad

    for vista in ("VIS_PREDICCION_ABANDONO", "VIS_EVALUACION_MODELO", "VIS_CLUSTER_CARRERA"):
        _contexto(cur, "UNEMI_PRUEBAS")
        cur.execute(f"SELECT COUNT(*) FROM dbo.{vista}")
        a = cur.fetchone()[0]
        _contexto(cur, "OULAD_UK")
        cur.execute(f"SELECT COUNT(*) FROM dbo.{vista}")
        b = cur.fetchone()[0]
        assert a > 0 and b > 0, f"{vista} debería tener datos en ambas instituciones"


@pytest.mark.integracion
def test_sin_contexto_no_se_ve_ninguna_institucion():
    conn = _conectar_chat_reader()  # conexión nueva: sin SESSION_CONTEXT
    try:
        cur = conn.cursor()
        for vista in ("VIS_ALUMNO", "VIS_PREDICCION_ABANDONO", "VIS_CLUSTER_CARRERA", "VIS_EVALUACION_MODELO"):
            cur.execute(f"SELECT COUNT(*) FROM dbo.{vista}")
            assert cur.fetchone()[0] == 0, f"{vista} devolvió filas sin institución activa"
    finally:
        conn.close()


@pytest.mark.integracion
def test_execute_chat_query_es_fail_closed(monkeypatch):
    """Si chat_reader no está disponible, la consulta NO se ejecuta con la
    cuenta del usuario (antes caía en silencio a la sesión admin)."""
    import main

    monkeypatch.setattr(main, "_get_chat_reader_connector", lambda: None)
    monkeypatch.delenv("CHAT_READER_OBLIGATORIO", raising=False)

    class ConectorAdmin:
        llamado = False

        def execute_query(self, *a, **k):
            ConectorAdmin.llamado = True
            return ["x"], [[1]], None

    cols, rows, err = main.execute_chat_query(ConectorAdmin(), "SELECT 1", "CHAT", empresa="UNEMI_PRUEBAS")
    assert err and not rows and not ConectorAdmin.llamado
