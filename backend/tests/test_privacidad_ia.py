# -*- coding: utf-8 -*-
"""
Datos personales que salen hacia los proveedores de IA y bitácora de la
interpretación (LOPDP). Sin red: el proveedor se reemplaza por un doble que
guarda lo que recibiría.

Verifica: RNF-01 (protección de datos), RNF-03 (trazabilidad).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import json

import pytest
from fastapi.testclient import TestClient

from core import auditoria, usuarios
from core.privacidad import (depurar_texto, es_columna_personal, es_columna_texto_libre, filas_para_ia,
                             indice_nombres, restaurar_en_sql)
from nl2sql import generador, motor, proveedores, redactor
from nl2sql.proveedores import RespuestaIA, SinProveedores
from tests.conftest import LectorFalso

CONOCIDAS = ['UNEMI_PRUEBAS', 'OULAD_UK']
CLAVE = 'Prueba-IA-2026'
DATOS_PERSONALES = ('0912345678', 'ana.perez@unemi.edu.ec', '099 123 4567', 'Ana Lucía', 'Pérez Mora', 'Luis Vera')


class ProveedorFalso:
    """Doble de nl2sql.proveedores.completar: registra cada mensaje y responde un texto fijo."""

    def __init__(self, texto: str):
        self.texto = texto
        self.mensajes: list[str] = []

    def __call__(self, sistema: str, usuario: str, max_tokens=None, proveedores=None) -> RespuestaIA:
        self.mensajes.append(sistema + '\n' + usuario)
        return RespuestaIA(texto=self.texto, proveedor='doble', modelo='doble-1', segundos=0.0, intentos=[])


def _sin_datos_personales(texto: str) -> bool:
    return not any(d.lower() in texto.lower() for d in DATOS_PERSONALES)


# ── 1. Depuración de la pregunta ─────────────────────────────────────────
def test_depurar_texto_reemplaza_identificadores_y_nombres():
    indice = indice_nombres([('Pérez Mora', 'Ana Lucía'), ('Vera', 'Luis')])
    texto, reemplazos = depurar_texto('¿Qué riesgo tiene ana lucia perez mora (0912345678, ana.perez@unemi.edu.ec, '
                                      '099 123 4567)? ¿Y Luis Vera? Muestra 10 estudiantes del 2024', indice)
    assert _sin_datos_personales(texto)
    assert {'NOMBRE_1', 'NOMBRE_2', 'CEDULA_1', 'CORREO_1', 'TELEFONO_1'} <= set(texto.replace('?', ' ').replace(',', ' ')
                                                                                   .replace('(', ' ').replace(')', ' ').split())
    assert '10 estudiantes del 2024' in texto           # cantidades y años no se tocan
    assert reemplazos['CEDULA_1'] == '0912345678'


def test_restaurar_en_sql_escapa_comillas():
    sql = restaurar_en_sql("SELECT 1 FROM VIS_ALUMNO WHERE cedula = 'CEDULA_1' AND apellidos LIKE '%NOMBRE_1%'",
                           {'CEDULA_1': '0912345678', 'NOMBRE_1': "O'Neil"})
    assert "cedula = '0912345678'" in sql and "LIKE '%O''Neil%'" in sql


def test_generar_envia_la_pregunta_depurada_y_restaura_el_sql(monkeypatch):
    doble = ProveedorFalso('{"sql": "SELECT probabilidad FROM VIS_PREDICCION_ABANDONO WHERE cedula = \'CEDULA_1\'", '
                           '"visualizacion": "valor", "titulo": "Riesgo", "nota": ""}')
    monkeypatch.setattr(generador, 'completar', doble)
    indice = indice_nombres([('Pérez Mora', 'Ana Lucía'), ('Vera', 'Luis')])
    gen = generador.generar('¿Cuál es el riesgo de 0912345678, correo ana.perez@unemi.edu.ec?', [],
                            historial=[{'pregunta': '¿Y cómo va Luis Vera, teléfono 099 123 4567?'}], nombres=indice)
    enviado = doble.mensajes[0]
    assert _sin_datos_personales(enviado)
    assert 'CEDULA_1' in enviado and 'NOMBRE_1' in enviado and 'TELEFONO_1' in enviado
    assert "cedula = '0912345678'" in gen.sql            # el SQL local sí lleva el valor real


def test_corregir_no_reenvia_los_valores_restaurados(monkeypatch):
    doble = ProveedorFalso('{"sql": "SELECT 1"}')
    monkeypatch.setattr(generador, 'completar', doble)
    anterior = generador.ResultadoGeneracion(sql="SELECT x FROM VIS_ALUMNO WHERE cedula = '0912345678'",
                                             reemplazos={'CEDULA_1': '0912345678'})
    generador.corregir('Riesgo de 0912345678', anterior, "Columna x no existe (valor '0912345678')", [])
    assert '0912345678' not in doble.mensajes[0] and 'CEDULA_1' in doble.mensajes[0]


def test_motor_no_cambia_la_pregunta_original(monkeypatch):
    doble = ProveedorFalso('{"sql": "SELECT COUNT(*) AS total FROM VIS_ALUMNO", "visualizacion": "valor"}')
    monkeypatch.setattr(generador, 'completar', doble)
    monkeypatch.setattr(motor, '_cache_nombres', {})
    lector = LectorFalso({'SELECT DISTINCT apellidos, nombres': (['apellidos', 'nombres'], [['Pérez Mora', 'Ana Lucía']])})
    pregunta = '¿Cuántas materias reprobó Ana Lucía Pérez Mora con cédula 0912345678?'
    r = motor.responder(pregunta, 'UNEMI_PRUEBAS', CONOCIDAS, lector=lector)
    assert r.pregunta == pregunta                         # la pregunta guardada y mostrada no cambia
    assert r.origen == 'GENERADA_IA'
    assert _sin_datos_personales(doble.mensajes[0]) and 'NOMBRE_1' in doble.mensajes[0]


def _espiar_entidades(monkeypatch) -> list[str]:
    vistas: list[str] = []
    original = motor.enrutador.extraer_entidades

    def espia(pregunta, carreras, facultades):
        vistas.append(pregunta)
        return original(pregunta, carreras, facultades)

    monkeypatch.setattr(motor.enrutador, 'extraer_entidades', espia)
    return vistas


def test_ruta_certificada_usa_la_pregunta_original(monkeypatch):
    monkeypatch.setattr(generador, 'generar', lambda *a, **k: pytest.fail('No debía llamar a la IA'))
    vistas = _espiar_entidades(monkeypatch)
    lector = LectorFalso({'riesgo_categoria IN': (['total'], [[12]])})
    pregunta = '¿Cuántos alumnos están en riesgo alto de abandonar?'
    r = motor.responder(pregunta, 'UNEMI_PRUEBAS', CONOCIDAS, lector=lector)
    assert r.origen == 'CERTIFICADA' and vistas == [pregunta] and r.pregunta == pregunta


def test_filtro_de_entidades_recibe_la_pregunta_sin_depurar(monkeypatch):
    doble = ProveedorFalso('{"sql": "SELECT COUNT(*) AS total FROM VIS_ALUMNO", "visualizacion": "valor"}')
    monkeypatch.setattr(generador, 'completar', doble)
    monkeypatch.setattr(motor, '_cache_nombres', {})
    vistas = _espiar_entidades(monkeypatch)
    pregunta = '¿Cuántas materias reprobó en Enfermería el estudiante 0912345678?'
    motor.responder(pregunta, 'UNEMI_PRUEBAS', CONOCIDAS, lector=LectorFalso())
    assert vistas == [pregunta]                           # las entidades se buscan en la pregunta original
    assert '0912345678' not in doble.mensajes[0]          # solo lo que sale al proveedor va depurado


# ── 2. Columnas personales y texto libre ─────────────────────────────────
@pytest.mark.parametrize('columna', ['Nombre', 'NOMBRES', 'nombre', 'Nombre del estudiante', 'Nombres y apellidos',
                                     'Apellido', 'APELLIDOS', 'Cédula', 'CEDULA', 'cédula_estudiante', 'Correo',
                                     'E-mail', 'email', 'Teléfono', 'telefono_celular', 'Dirección', 'direccion_domicilio',
                                     'Estudiante', 'nombre_completo'])
def test_es_columna_personal_detecta_alias(columna):
    assert es_columna_personal(columna) is True


@pytest.mark.parametrize('columna', ['carrera', 'Nombre de la carrera', 'facultad_nombre', 'Estudiantes',
                                     'Total de estudiantes', 'probabilidad', 'riesgo_categoria', 'periodo'])
def test_es_columna_personal_no_marca_columnas_agregadas(columna):
    assert es_columna_personal(columna) is False


def test_texto_libre_del_seguimiento_no_sale_hacia_la_ia():
    assert es_columna_texto_libre('descripcion') and es_columna_texto_libre('Resultado')
    columnas = ['Nombre', 'cedula', 'tipo', 'descripcion', 'resultado', 'registrado_por', 'ciudad_residencia']
    filas = [['Ana Pérez', '0912345678', 'TUTORIA', 'Problemas de salud, llamar al 099 123 4567', 'Mejoró', 'tutor.uno', 'Milagro']]
    cols, salida = filas_para_ia(columnas, filas)
    assert cols == ['Nombre', 'cedula', 'tipo']
    assert salida == [['Estudiante 1', 'Estudiante 1', 'TUTORIA']]


def test_resultado_agregado_conserva_la_ciudad():
    cols, salida = filas_para_ia(['ciudad_residencia', 'estudiantes'], [['Milagro', 120]])
    assert cols == ['ciudad_residencia', 'estudiantes'] and salida == [['Milagro', 120]]


def test_interpretar_envia_filas_sin_texto_libre(monkeypatch):
    doble = ProveedorFalso('El resultado muestra un registro de tutoría.')
    monkeypatch.setattr(proveedores, 'completar', doble)
    r = redactor.interpretar('¿Qué seguimiento tiene 0912345678?', ['Nombres', 'tipo', 'descripcion'],
                             [['Ana Lucía', 'TUTORIA', 'Diagnóstico médico reservado']])
    enviado = doble.mensajes[0]
    assert r['verificada'] and r['filas_enviadas'] == 1 and len(r['huella']) == 16
    assert 'Diagnóstico' not in enviado and 'Ana Lucía' not in enviado and '0912345678' not in enviado


# ── 3. Bitácora de la interpretación ─────────────────────────────────────
@pytest.fixture(scope='module')
def cliente():
    from main import app
    if not usuarios.buscar('autoridad.ia'):
        usuarios.crear('autoridad.ia', 'autoridad.ia', '', 'AUTORIDAD', ['UNEMI_PRUEBAS'], CLAVE)
    return TestClient(app)


def _token(cliente):
    r = cliente.post('/api/auth/ingresar', json={'usuario': 'autoridad.ia', 'clave': CLAVE})
    assert r.status_code == 200, r.text
    return {'Authorization': f"Bearer {r.json()['token']}"}


def _ultimo_evento_interpretacion() -> dict:
    eventos = auditoria.consultar(limite=1, usuario='autoridad.ia', accion='INTERPRETACION')
    assert eventos, 'La interpretación no quedó en la bitácora'
    return eventos[0]


def test_interpretacion_queda_en_la_bitacora_sin_datos(cliente, monkeypatch):
    columnas = ['cedula', 'Nombre', 'descripcion', 'probabilidad']
    filas = [['0912345678', 'Ana Lucía Pérez Mora', 'Tratamiento médico', 0.91],
             ['0998765432', 'Luis Vera', 'Sin novedad', 0.83]]
    monkeypatch.setattr(motor, 'resultado_guardado', lambda i, inst: ('Riesgo de 0912345678', columnas, filas))
    monkeypatch.setattr(motor, 'nombres_institucion', lambda inst, lector=None: {})
    doble = ProveedorFalso('Hay dos estudiantes con probabilidad alta.')
    monkeypatch.setattr(proveedores, 'completar', doble)
    r = cliente.post('/api/consulta/abc123/interpretar', headers=_token(cliente))
    assert r.status_code == 200 and r.json()['verificada'] is True
    assert 'huella' not in r.json() and 'filas_enviadas' not in r.json()
    e = _ultimo_evento_interpretacion()
    assert e['institucion'] == 'UNEMI_PRUEBAS' and e['resultado'] == 'OK'
    d = e['detalle']
    assert d['proveedor'] == 'doble' and d['filas_enviadas'] == 2 and len(d['huella']) == 16
    registro = json.dumps(e, ensure_ascii=False)
    for dato in ('0912345678', 'Ana Lucía', 'Luis Vera', 'Tratamiento', '0,91', '0.91'):
        assert dato not in registro
    assert _sin_datos_personales(doble.mensajes[0])


def test_interpretacion_sin_proveedor_tambien_se_registra(cliente, monkeypatch):
    monkeypatch.setattr(motor, 'resultado_guardado', lambda i, inst: ('Total', ['total'], [[42]]))
    monkeypatch.setattr(motor, 'nombres_institucion', lambda inst, lector=None: {})

    def sin_proveedor(*a, **k):
        raise SinProveedores('No hay proveedores de IA configurados.')

    monkeypatch.setattr(proveedores, 'completar', sin_proveedor)
    r = cliente.post('/api/consulta/xyz789/interpretar', headers=_token(cliente))
    assert r.status_code == 200 and r.json()['verificada'] is False
    e = _ultimo_evento_interpretacion()
    assert e['resultado'] == 'SIN_PROVEEDOR' and e['detalle']['filas_enviadas'] == 0
    assert e['detalle']['id_respuesta'] == 'xyz789'
