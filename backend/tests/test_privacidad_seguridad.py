# -*- coding: utf-8 -*-
"""Protección de datos estudiantiles (LOPDP) y control de acceso por rol."""
import pytest

from core.privacidad import (cedula_desde_token, enmascarar_cedula, enmascarar_para_pantalla, es_columna_personal,
                             seudonimizar, token_estudiante)
from core.seguridad import CAPACIDADES_POR_ROL, crear_token, hash_clave, verificar_clave


def test_enmascarar_cedula():
    assert enmascarar_cedula('0912345678') == '******5678'
    assert enmascarar_cedula('') == '****'


def test_seudonimizar_antes_de_enviar_a_la_ia():
    columnas = ['cedula', 'apellidos', 'nombres', 'carrera', 'probabilidad']
    filas = [['0912345678', 'Pérez', 'Ana', 'Enfermería', 0.91],
             ['0998765432', 'Mora', 'Luis', 'Psicología', 0.83],
             ['0912345678', 'Pérez', 'Ana', 'Enfermería', 0.91]]
    _, salida = seudonimizar(columnas, filas)
    texto = str(salida)
    for dato in ('0912345678', 'Pérez', 'Ana', 'Mora', 'Luis'):
        assert dato not in texto
    assert salida[0][0] == salida[2][0] == 'Estudiante 1' and salida[1][0] == 'Estudiante 2'
    assert salida[0][3] == 'Enfermería' and salida[0][4] == 0.91


def test_seudonimizar_cedulas_dentro_de_textos():
    _, salida = seudonimizar(['nota'], [['revisar al 0912345678 urgente']])
    assert '0912345678' not in salida[0][0]


@pytest.mark.parametrize('columna,esperado', [('cedula', True), ('apellidos', True), ('correo', True),
                                              ('carrera', False), ('probabilidad', False)])
def test_columnas_personales(columna, esperado):
    assert es_columna_personal(columna) is esperado


def test_pantalla_enmascara_solo_la_identificacion():
    filas = enmascarar_para_pantalla(['cedula', 'carrera'], [['0912345678', 'Enfermería']])
    assert filas == [['******5678', 'Enfermería']]


def test_token_de_estudiante_es_opaco_y_reversible_solo_en_el_servidor():
    token = token_estudiante('0912345678')
    assert '0912345678' not in token
    assert cedula_desde_token(token) == '0912345678'
    assert cedula_desde_token(token[:-4] + 'AAAA') is None
    assert cedula_desde_token('no-es-un-token') is None


def test_contrasenas_con_bcrypt():
    h = hash_clave('Clave-Segura-2026')
    assert h.startswith('$2') and 'Clave' not in h
    assert verificar_clave('Clave-Segura-2026', h) and not verificar_clave('otra', h)
    assert not verificar_clave('texto', 'texto')  # nunca se compara contra texto plano


def test_matriz_de_capacidades():
    assert 'administrar_usuarios' not in CAPACIDADES_POR_ROL['AUTORIDAD']
    assert 'registrar_seguimiento' not in CAPACIDADES_POR_ROL['AUTORIDAD']
    assert 'registrar_seguimiento' in CAPACIDADES_POR_ROL['BIENESTAR']
    assert 'ver_sql' in CAPACIDADES_POR_ROL['ADMIN_TI'] and 'ver_sql' not in CAPACIDADES_POR_ROL['BIENESTAR']
    assert CAPACIDADES_POR_ROL['AUTORIDAD'] < CAPACIDADES_POR_ROL['ADMIN_TI']


def test_token_jwt_firmado():
    from jose import jwt
    from core.config import CONFIG
    datos = jwt.decode(crear_token('ana', 'AUTORIDAD'), CONFIG.jwt_clave, algorithms=[CONFIG.jwt_algoritmo])
    assert datos['sub'] == 'ana' and datos['rol'] == 'AUTORIDAD' and 'exp' in datos
