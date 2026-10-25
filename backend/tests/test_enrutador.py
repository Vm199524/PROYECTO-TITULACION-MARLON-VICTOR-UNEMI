# -*- coding: utf-8 -*-
"""Enrutador de métricas certificadas: las preguntas frecuentes no dependen de la IA."""
import json
from pathlib import Path

import pytest

from nl2sql import enrutador
from tests.conftest import CARRERAS, FACULTADES

CATALOGO = json.loads((Path(__file__).resolve().parent.parent / 'nl2sql' / 'catalogo_metricas.json').read_text(encoding='utf-8'))


def elegir(pregunta):
    return enrutador.elegir(enrutador.extraer_entidades(pregunta, CARRERAS, FACULTADES))


def test_catalogo_tiene_40_metricas_unicas():
    metricas = CATALOGO['metricas'] if isinstance(CATALOGO, dict) else CATALOGO
    ids = [m['id'] for m in metricas]
    assert len(ids) >= 40 and len(ids) == len(set(ids))


def test_cada_sql_certificado_pasa_el_validador():
    from nl2sql.validador import validar
    metricas = CATALOGO['metricas'] if isinstance(CATALOGO, dict) else CATALOGO
    for m in metricas:
        sql = m['sql'].replace('(?*)', '(?)')
        r = validar(sql.replace('?', "'X'"))
        assert r.valido, (m['id'], r.problemas)


@pytest.mark.parametrize('pregunta,metrica', [
    ('¿Cuántos alumnos están en riesgo alto de abandonar?', 'riesgo_nivel_total'),
    ('¿Cuántos alumnos hay en cada nivel de riesgo de abandono?', 'riesgo_distribucion'),
    ('¿Cuál es la tasa de abandono de la institución?', 'tasa_abandono'),
    ('¿Qué carreras necesitan atención prioritaria?', 'segmentos_prioritarios'),
    ('¿Qué modelo de predicción se eligió como modelo final?', 'modelo_final'),
    ('¿Cuántos alumnos con matrícula vigente hay en cada sede?', 'activos_por_sede'),
])
def test_preguntas_frecuentes_van_a_su_metrica(pregunta, metrica):
    c = elegir(pregunta)
    assert c is not None and c.metrica['id'] == metrica


def test_extrae_carrera_con_errores_de_tipeo():
    e = enrutador.extraer_entidades('probabilidad promedio de abandono en enfermeria', CARRERAS, FACULTADES)
    assert e.carrera == 'Enfermería'


def test_no_certifica_si_quedan_terminos_sin_cubrir():
    # «mujeres» no está en la métrica de activos: debe ir a la IA, no a una cifra equivocada.
    assert elegir('¿Cuántas mujeres tienen matrícula vigente?') is None


def test_normalizar_quita_tildes_y_mayusculas():
    assert enrutador.normalizar('¿Cuántos ALUMNOS de Psicología?') == enrutador.normalizar('cuantos alumnos de psicologia')


def test_sinonimos_de_abandono_llegan_a_la_metrica():
    # «dejar la carrera» y «estudiantes» se llevan a la forma del catálogo.
    c = elegir('cuantos estudiantes estan en riesgo alto de dejar la carrera')
    assert c is not None and c.metrica['id'] == 'riesgo_nivel_total'


def test_carrera_nombrada_no_usa_metrica_institucional():
    # Con una carrera en la pregunta, la cifra de toda la institución sería incorrecta.
    c = elegir('¿Cuántos estudiantes de Enfermería tienen riesgo medio?')
    assert c is None or 'carrera' in c.metrica['parametros']


def test_promedio_sin_riesgo_no_va_a_metricas_del_modelo():
    # «el promedio de los activos» habla de calificaciones, no de probabilidad de abandono.
    c = elegir('¿cuál es el promedio de los estudiantes activos de Enfermería?')
    assert c is None or 'probabilidad' not in c.metrica['sql'].lower()
