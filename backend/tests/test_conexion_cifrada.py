# -*- coding: utf-8 -*-
"""
Pruebas de la cadena de conexión a SQL Server.

Comprueban que el canal siempre se pide cifrado (Encrypt=yes) y que aceptar
el certificado autofirmado del contenedor depende solo de la variable
DB_TRUST_SERVER_CERT, con un valor por defecto seguro en producción. No
necesitan SQL Server: solo arman la cadena.

Verifica: RNF-02 (mínimo privilegio y aislamiento).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import dataclasses

import pytest

from core import config, db


def _cadena_con(monkeypatch, confiar: bool) -> str:
    monkeypatch.setattr(db, 'CONFIG', dataclasses.replace(config.CONFIG, db_confiar_certificado=confiar))
    return db._cadena('usuario_prueba', 'clave_prueba', 'ALMACEN_PRUEBA')


def test_la_cadena_siempre_pide_cifrado(monkeypatch):
    for confiar in (True, False):
        cadena = _cadena_con(monkeypatch, confiar)
        assert 'Encrypt=yes;' in cadena
        assert 'Encrypt=no' not in cadena


def test_confiar_en_el_certificado_depende_de_la_variable(monkeypatch):
    assert 'TrustServerCertificate=yes;' in _cadena_con(monkeypatch, True)
    cadena = _cadena_con(monkeypatch, False)
    assert 'TrustServerCertificate=no;' in cadena
    assert 'TrustServerCertificate=yes' not in cadena


@pytest.mark.parametrize('valor, esperado', [
    ('yes', True), ('true', True), ('1', True), ('YES', True),
    ('no', False), ('false', False), ('0', False),
])
def test_db_trust_server_cert_se_respeta(monkeypatch, valor, esperado):
    monkeypatch.setenv('DB_TRUST_SERVER_CERT', valor)
    assert config.Configuracion().db_confiar_certificado is esperado


@pytest.mark.parametrize('entorno, esperado', [('development', True), ('production', False)])
def test_sin_variable_el_defecto_depende_del_entorno(monkeypatch, entorno, esperado):
    monkeypatch.delenv('DB_TRUST_SERVER_CERT', raising=False)
    monkeypatch.setenv('APP_ENV', entorno)
    assert config.Configuracion().db_confiar_certificado is esperado
