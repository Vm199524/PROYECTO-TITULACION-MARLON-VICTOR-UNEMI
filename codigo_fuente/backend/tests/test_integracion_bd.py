# -*- coding: utf-8 -*-
"""
Pruebas de integración con SQL Server (se omiten si no hay almacén cargado).

Comprueban en el motor de base de datos, no en la aplicación, las garantías
que el documento declara: mínimo privilegio, aislamiento entre instituciones
y falla cerrada sin institución en la sesión.
"""
import json
from pathlib import Path

import pytest

from core import db
from core.config import CONFIG

pytestmark = pytest.mark.integracion
CATALOGO = json.loads((Path(__file__).resolve().parent.parent / 'nl2sql' / 'catalogo_metricas.json').read_text(encoding='utf-8'))
METRICAS = CATALOGO['metricas'] if isinstance(CATALOGO, dict) else CATALOGO


def _conexion(usuario, clave):
    return db._pyodbc().connect(db._cadena(usuario, clave, CONFIG.almacen), timeout=15, autocommit=True)


def _falla(cur, sql):
    with pytest.raises(Exception):
        cur.execute(sql)
        cur.fetchall()


def test_lector_no_lee_tablas_fisicas_ni_escribe():
    conn = _conexion(CONFIG.lector_usuario, CONFIG.lector_clave)
    cur = conn.cursor()
    _falla(cur, 'SELECT TOP 1 * FROM dbo.fact_matriculas')
    _falla(cur, 'SELECT TOP 1 * FROM dbo.dim_alumno')
    _falla(cur, "UPDATE dbo.fact_prediccion_abandono SET riesgo_categoria = 'BAJO'")
    _falla(cur, 'SELECT TOP 1 * FROM UNEMI_PRUEBAS.dbo.alumnos_prueba')
    conn.close()


def test_sin_institucion_las_vistas_no_devuelven_filas():
    conn = _conexion(CONFIG.lector_usuario, CONFIG.lector_clave)
    cur = conn.cursor()
    for vista in ('VIS_ALUMNO', 'VIS_PREDICCION_ABANDONO', 'VIS_SEGMENTO_CARRERA', 'VIS_REFERENTE_EXTERNO'):
        cur.execute(f'SELECT COUNT(*) FROM dbo.{vista}')
        assert cur.fetchone()[0] == 0, vista
    conn.close()


def test_la_institucion_de_la_sesion_no_se_puede_cambiar():
    with pytest.raises(db.ErrorBaseDatos):
        db.leer("EXEC sp_set_session_context @key = N'institucion_activa', @value = 'OULAD_UK'", 'UNEMI_PRUEBAS')


def test_aislamiento_entre_instituciones():
    # VIS_ALUMNO no expone el código de institución: el aislamiento se comprueba con
    # VIS_INSTITUCION y con los identificadores (los de OULAD empiezan por «OU»).
    _, unemi = db.leer('SELECT institucion_codigo FROM VIS_INSTITUCION', 'UNEMI_PRUEBAS')
    _, oulad = db.leer('SELECT institucion_codigo FROM VIS_INSTITUCION', 'OULAD_UK')
    assert unemi == [['UNEMI_PRUEBAS']] and oulad == [['OULAD_UK']]
    _, cruce_unemi = db.leer("SELECT COUNT(*) FROM VIS_ALUMNO WHERE cedula LIKE 'OU%'", 'UNEMI_PRUEBAS')
    _, cruce_oulad = db.leer("SELECT COUNT(*) FROM VIS_ALUMNO WHERE cedula NOT LIKE 'OU%'", 'OULAD_UK')
    assert cruce_unemi == [[0]] and cruce_oulad == [[0]]


def test_cuenta_de_seguimiento_solo_ejecuta_sus_procedimientos():
    conn = _conexion(CONFIG.seguimiento_usuario, CONFIG.seguimiento_clave)
    cur = conn.cursor()
    _falla(cur, 'SELECT TOP 1 * FROM dbo.VIS_ALUMNO')
    _falla(cur, 'SELECT TOP 1 * FROM dbo.fact_intervencion')
    conn.close()


@pytest.mark.parametrize('institucion', ['UNEMI_PRUEBAS', 'OULAD_UK'])
def test_metricas_certificadas_se_ejecutan(institucion):
    _, carreras = db.leer('SELECT TOP 1 carrera, facultad_nombre FROM VIS_ALUMNO', institucion)
    for m in METRICAS:
        sql, valores = m['sql'], []
        for nombre in m['parametros']:
            if nombre == 'riesgo':
                sql = sql.replace('(?*)', '(?)', 1)
                valores.append('ALTO')
            elif nombre == 'carrera':
                valores.append(carreras[0][0])
            elif nombre == 'facultad':
                valores.append(carreras[0][1])
            elif nombre == 'anio':
                valores.append(2024)
            elif nombre == 'n':
                valores.append(5)
            else:
                valores.append(None)
        db.leer(sql, institucion, tuple(valores))


def test_cada_activo_calificado_tiene_prediccion():
    _, filas = db.leer("SELECT COUNT(*) FROM VIS_PREDICCION_ABANDONO WHERE probabilidad IS NULL OR riesgo_categoria IS NULL",
                       'UNEMI_PRUEBAS')
    assert filas[0][0] == 0
