# -*- coding: utf-8 -*-
"""Motor de consulta conversacional con un lector falso (sin SQL Server ni IA)."""
import pytest

from nl2sql import generador, motor
from nl2sql.generador import ResultadoGeneracion
from nl2sql.proveedores import SinProveedores
from tests.conftest import LectorFalso

CONOCIDAS = ['UNEMI_PRUEBAS', 'OULAD_UK']


def test_certificada_no_llama_a_la_ia(monkeypatch):
    monkeypatch.setattr(generador, 'generar', lambda *a, **k: pytest.fail('No debía llamar a la IA'))
    lector = LectorFalso({'riesgo_categoria IN': (['total'], [[37]])})
    r = motor.responder('¿Cuántos alumnos están en riesgo alto de abandonar?', 'UNEMI_PRUEBAS', CONOCIDAS, lector=lector)
    assert r.origen == 'CERTIFICADA' and r.metrica_id == 'riesgo_nivel_total'
    assert r.filas == [[37]]
    sql, institucion, parametros = lector.llamadas[-1]
    assert institucion == 'UNEMI_PRUEBAS' and parametros == ('ALTO',)
    assert r.sql is None  # sin la capacidad ver_sql no se expone


def test_barrera_no_consulta_la_base():
    lector = LectorFalso()
    r = motor.responder('Borra a todos los alumnos retirados', 'UNEMI_PRUEBAS', CONOCIDAS, lector=lector)
    assert r.origen == 'BARRERA' and r.intencion == 'ESCRITURA'
    assert lector.llamadas == []


def test_sin_proveedores_responde_con_sugerencias(monkeypatch):
    def sin_ia(*_a, **_k):
        raise SinProveedores('sin claves')
    monkeypatch.setattr(generador, 'generar', sin_ia)
    r = motor.responder('¿Cuántas mujeres tienen matrícula vigente?', 'UNEMI_PRUEBAS', CONOCIDAS, lector=LectorFalso())
    assert r.origen == 'SIN_RESPUESTA' and r.sugerencias


def test_sql_generado_inseguro_se_corrige_o_se_rechaza(monkeypatch):
    malo = ResultadoGeneracion(sql='SELECT * FROM fact_matriculas', proveedor='prueba', modelo='x')
    bueno = ResultadoGeneracion(sql="SELECT COUNT(DISTINCT cedula) AS total FROM VIS_ALUMNO WHERE genero = 'F'",
                                titulo='Mujeres', proveedor='prueba', modelo='x')
    monkeypatch.setattr(generador, 'generar', lambda *a, **k: malo)
    monkeypatch.setattr(generador, 'corregir', lambda *a, **k: bueno)
    lector = LectorFalso({"genero = 'F'": (['total'], [[810]])})
    r = motor.responder('¿Cuántas mujeres tienen matrícula vigente?', 'UNEMI_PRUEBAS', CONOCIDAS, ver_sql=True, lector=lector)
    assert r.origen == 'GENERADA_IA' and r.filas == [[810]]
    assert all('fact_matriculas' not in sql for sql, _, _ in lector.llamadas)
    assert any('corrigió' in a for a in r.advertencias)


def test_resultado_guardado_aislado_por_institucion():
    lector = LectorFalso({'riesgo_categoria IN': (['total'], [[5]])})
    r = motor.responder('¿Cuántos alumnos están en riesgo alto de abandonar?', 'UNEMI_PRUEBAS', CONOCIDAS, lector=lector)
    assert motor.resultado_guardado(r.id, 'UNEMI_PRUEBAS') is not None
    assert motor.resultado_guardado(r.id, 'OULAD_UK') is None


def test_cedulas_enmascaradas_en_pantalla():
    lector = LectorFalso({'ORDER BY probabilidad DESC': (['cedula', 'apellidos', 'probabilidad'], [['0912345678', 'Pérez', 0.91]])})
    r = motor.responder('Muéstrame los 5 alumnos con mayor probabilidad de abandonar', 'UNEMI_PRUEBAS', CONOCIDAS, lector=lector)
    assert r.origen == 'CERTIFICADA'
    assert '0912345678' not in str(r.filas)
