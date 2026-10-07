# -*- coding: utf-8 -*-
"""API web: autenticación, autorización por rol, aislamiento por institución y reportes."""
import pytest
from fastapi.testclient import TestClient

from core import db, usuarios

CLAVE = 'Prueba-API-2026'


def _leer_dicts_falso(sql, institucion, parametros=()):
    if 'FROM VIS_INSTITUCION' in sql:
        return [{'nombre': 'Universidad de prueba', 'pais': 'Ecuador', 'tipo_datos': 'SINTETICO', 'unidad_periodo': 'Semestre'}]
    if 'GROUP BY riesgo_categoria' in sql:
        return [{'riesgo_categoria': 'ALTO', 'n': 40, 'fecha': '2026-10-07', 'version': '3.0'},
                {'riesgo_categoria': 'MEDIO', 'n': 160, 'fecha': '2026-10-07', 'version': '3.0'},
                {'riesgo_categoria': 'BAJO', 'n': 800, 'fecha': '2026-10-07', 'version': '3.0'}]
    if 'AS retirados, COUNT(*) AS cerrados' in sql:
        return [{'retirados': 300, 'cerrados': 1000}]
    if 'SELECT metrica, valor' in sql:
        return [{'metrica': 'ROC_AUC', 'valor': 0.81}, {'metrica': 'RECALL_MEDIO', 'valor': 0.8},
                {'metrica': 'PRECISION_MEDIO', 'valor': 0.21}, {'metrica': 'CAPTURA_TOP_10', 'valor': 0.42}]
    if 'SELECT TOP 1 modelo' in sql:
        return [{'modelo': 'LIGHTGBM'}]
    if 'GROUP BY segmento, orden_segmento' in sql:
        return [{'segmento': 'Atención prioritaria', 'orden_segmento': 1, 'carreras': 3},
                {'segmento': 'Estable', 'orden_segmento': 2, 'carreras': 8}]
    if 'GROUP BY carrera' in sql and 'alto' in sql:
        return [{'carrera': 'Enfermería', 'alto': 12, 'medio': 30, 'activos': 210},
                {'carrera': 'Psicología', 'alto': 9, 'medio': 22, 'activos': 180}]
    if 'GROUP BY periodo_academico' in sql:
        return [{'periodo_academico': '2024-1', 'inicio': '2024-04-01', 'estudiantes': 900, 'retirados': 70},
                {'periodo_academico': '2024-2', 'inicio': '2024-10-01', 'estudiantes': 950, 'retirados': 64}]
    if 'SELECT TOP 6 cedula' in sql:
        return [{'cedula': '0912345678', 'apellidos': 'Pérez', 'nombres': 'Ana', 'carrera': 'Enfermería',
                 'probabilidad': 0.91, 'percentil_riesgo': 99.5, 'factor_1': 'asistencia baja'}]
    if 'AS en_alto' in sql:
        return [{'en_alto': 40, 'atendidos': 10}]
    if 'AS abiertas' in sql:
        return [{'abiertas': 7}]
    if 'SELECT TOP 300 cedula' in sql:
        return [{'cedula': '0912345678', 'apellidos': 'Pérez', 'nombres': 'Ana', 'carrera': 'Enfermería',
                 'probabilidad': 0.91, 'riesgo_categoria': 'ALTO', 'factor_1': 'asistencia baja', 'factor_2': None}]
    if 'FROM VIS_SEGMENTO_CARRERA' in sql:
        return [{'carrera': 'Enfermería', 'facultad_nombre': 'Salud', 'segmento': 'Atención prioritaria', 'estudiantes': 210,
                 'tasa_abandono_hist': 31.2, 'promedio_hist': 7.1, 'asistencia_hist': 78.0, 'riesgo_promedio': 0.22,
                 'activos_en_riesgo': 42}]
    return []


@pytest.fixture(scope='module')
def cliente():
    from main import app
    for usuario, rol, inst in (('autoridad.prueba', 'AUTORIDAD', ['UNEMI_PRUEBAS']),
                               ('bienestar.prueba', 'BIENESTAR', ['UNEMI_PRUEBAS']),
                               ('admin.prueba', 'ADMIN_TI', ['UNEMI_PRUEBAS', 'OULAD_UK'])):
        if not usuarios.buscar(usuario):
            usuarios.crear(usuario, usuario, '', rol, inst, CLAVE)
    return TestClient(app)


@pytest.fixture(autouse=True)
def base_falsa(monkeypatch):
    monkeypatch.setattr(db, 'leer_dicts', _leer_dicts_falso)


def _token(cliente, usuario):
    r = cliente.post('/api/auth/ingresar', json={'usuario': usuario, 'clave': CLAVE})
    assert r.status_code == 200, r.text
    return {'Authorization': f"Bearer {r.json()['token']}"}


def test_salud(cliente):
    r = cliente.get('/api/salud')
    assert r.status_code == 200
    assert r.headers.get('x-content-type-options') == 'nosniff'


def test_sin_token_no_hay_acceso(cliente):
    assert cliente.get('/api/panel/resumen').status_code == 401


def test_clave_incorrecta(cliente):
    assert cliente.post('/api/auth/ingresar', json={'usuario': 'autoridad.prueba', 'clave': 'mala'}).status_code == 401


def test_perfil_con_capacidades(cliente):
    r = cliente.get('/api/auth/yo', headers=_token(cliente, 'autoridad.prueba'))
    assert r.status_code == 200
    perfil = r.json()
    assert perfil['rol'] == 'AUTORIDAD' and 'ver_panel' in perfil['capacidades']
    assert 'hash' not in perfil


def test_panel_ejecutivo(cliente):
    r = cliente.get('/api/panel/resumen', headers=_token(cliente, 'autoridad.prueba'))
    assert r.status_code == 200
    datos = r.json()
    assert datos['indicadores']['alto'] == 40 and datos['indicadores']['tasa_abandono_hist'] == 30.0
    assert datos['indicadores']['cobertura_alto'] == 25.0
    alerta = datos['alertas'][0]
    assert '0912345678' not in str(alerta) and alerta['token']


def test_institucion_no_asignada_se_rechaza(cliente):
    cabeceras = {**_token(cliente, 'autoridad.prueba'), 'X-Institucion': 'OULAD_UK'}
    assert cliente.get('/api/panel/resumen', headers=cabeceras).status_code == 403


def test_autoridad_no_administra_cuentas(cliente):
    assert cliente.get('/api/admin/usuarios', headers=_token(cliente, 'autoridad.prueba')).status_code == 403


def test_admin_ti_si_administra_cuentas(cliente):
    r = cliente.get('/api/admin/usuarios', headers=_token(cliente, 'admin.prueba'))
    assert r.status_code == 200
    assert all('hash' not in c for c in r.json()['usuarios'])


def test_autoridad_no_registra_seguimiento(cliente):
    r = cliente.post('/api/seguimiento', headers=_token(cliente, 'autoridad.prueba'),
                     json={'token': 'x', 'tipo': 'TUTORIA', 'descripcion': 'Llamada al estudiante'})
    assert r.status_code == 403


def test_consulta_con_barrera(cliente):
    r = cliente.post('/api/consulta', headers=_token(cliente, 'autoridad.prueba'),
                     json={'pregunta': 'Elimina a todos los alumnos retirados'})
    assert r.status_code == 200
    assert r.json()['origen'] == 'BARRERA'


def test_reportes_ejecutivos(cliente):
    cabeceras = _token(cliente, 'autoridad.prueba')
    excel = cliente.get('/api/reportes/ejecutivo.xlsx', headers=cabeceras)
    assert excel.status_code == 200 and excel.content[:2] == b'PK'
    pdf = cliente.get('/api/reportes/ejecutivo.pdf', headers=cabeceras)
    assert pdf.status_code == 200 and pdf.content[:4] == b'%PDF'
    assert b'0912345678' not in excel.content


def test_auditoria_registra_los_ingresos(cliente):
    _token(cliente, 'bienestar.prueba')
    r = cliente.get('/api/admin/auditoria', headers=_token(cliente, 'admin.prueba'))
    assert r.status_code == 200
    eventos = r.json()['eventos'] if isinstance(r.json(), dict) else r.json()
    assert any(e.get('accion') == 'INGRESO' and e.get('usuario') == 'bienestar.prueba' for e in eventos)
