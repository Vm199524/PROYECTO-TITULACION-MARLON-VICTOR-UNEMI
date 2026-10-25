# -*- coding: utf-8 -*-
"""Validador del SQL generado: solo lecturas sobre las vistas gobernadas VIS_* (RNF de seguridad)."""
import pytest

from nl2sql.validador import LIMITE_FILAS, validar

LEGITIMAS = [
    "SELECT COUNT(*) AS total FROM VIS_PREDICCION_ABANDONO WHERE riesgo_categoria = 'ALTO'",
    "SELECT carrera, COUNT(DISTINCT cedula) AS alumnos FROM VIS_ALUMNO WHERE es_ultimo_periodo = 1 GROUP BY carrera",
    "WITH base AS (SELECT carrera, probabilidad FROM VIS_PREDICCION_ABANDONO) "
    "SELECT carrera, AVG(probabilidad) AS media FROM base GROUP BY carrera",
    "SELECT TOP 5 apellidos, nombres, probabilidad FROM VIS_PREDICCION_ABANDONO ORDER BY probabilidad DESC",
    "SELECT segmento, COUNT(*) AS carreras FROM VIS_SEGMENTO_CARRERA GROUP BY segmento "
    "UNION ALL SELECT 'Total', COUNT(*) FROM VIS_SEGMENTO_CARRERA",
]

MALICIOSAS = {
    'escritura': "DELETE FROM VIS_ALUMNO WHERE estado_matricula = 'RETIRADO'",
    'definicion': 'DROP VIEW VIS_ALUMNO',
    'tabla_fisica': 'SELECT * FROM fact_matriculas',
    'select_into': 'SELECT * INTO copia FROM VIS_ALUMNO',
    'otra_base': 'SELECT * FROM UNEMI_PRUEBAS.dbo.alumnos_prueba',
    'catalogo': 'SELECT name FROM sys.tables',
    'procedimiento': "EXEC sp_set_session_context 'institucion_activa', 'OULAD_UK'",
    'varias_sentencias': 'SELECT 1 AS a FROM VIS_ALUMNO; DROP TABLE dim_alumno',
    'openrowset': "SELECT * FROM OPENROWSET('SQLNCLI', 'Server=x;', 'SELECT 1')",
    'columna_inexistente': 'SELECT clave_secreta FROM VIS_ALUMNO',
    'actualizacion': "UPDATE VIS_PREDICCION_ABANDONO SET riesgo_categoria = 'BAJO'",
}


@pytest.mark.parametrize('sql', LEGITIMAS)
def test_acepta_lecturas_sobre_vistas(sql):
    r = validar(sql)
    assert r.valido, r.problemas
    assert all(v.upper().startswith('VIS_') for v in r.vistas)


@pytest.mark.parametrize('caso,sql', MALICIOSAS.items())
def test_rechaza_sql_peligroso(caso, sql):
    assert not validar(sql).valido, caso


def test_agrega_limite_de_filas():
    r = validar('SELECT cedula, carrera FROM VIS_ALUMNO')
    assert r.valido
    assert f'TOP {LIMITE_FILAS}' in r.sql.upper()


def test_respeta_limite_propio():
    r = validar('SELECT TOP 5 cedula FROM VIS_ALUMNO')
    assert r.valido and 'TOP 5' in r.sql.upper() and f'TOP {LIMITE_FILAS}' not in r.sql.upper()


def test_ignora_cercas_markdown():
    assert validar("```sql\nSELECT COUNT(*) AS total FROM VIS_ALUMNO;\n```").valido


def test_comentarios_no_esconden_escritura():
    assert not validar('SELECT 1 AS a FROM VIS_ALUMNO /* */; DELETE FROM VIS_ALUMNO').valido
