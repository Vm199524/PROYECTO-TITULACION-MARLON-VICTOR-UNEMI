"""
Pruebas del selector manual de motor de IA.

Flash responde siempre por defecto; los demás motores solo se activan si el
usuario los elige explícitamente, y el motor elegido responde de principio a
fin, nunca un híbrido. Se prueban la resolución de modelos permitidos
(`_modelos_permitidos_de`: valor por rol, excepción por usuario y respaldo),
el enrutamiento de `_select_llm` y la revalidación en el servidor: el cliente
nunca decide a ciegas qué motor puede usar, igual que en el blindaje de SQL y
trazabilidad.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── _modelos_permitidos_de ──────────────────────────────────────────────────


def test_default_por_rol_administrador():
    import main

    assert main._modelos_permitidos_de({"role": "ADMINISTRADOR"}) == list(main.MODELOS_IA_VALIDOS)


def test_default_por_rol_contabilidad():
    import main

    assert main._modelos_permitidos_de({"role": "CONTABILIDAD"}) == ["flash", "pro"]


@pytest.mark.parametrize("rol", ["RRHH", "LOGISTICA", "GUEST"])
def test_default_por_rol_solo_flash(rol):
    import main

    assert main._modelos_permitidos_de({"role": rol}) == ["flash"]


def test_rol_desconocido_cae_a_flash():
    import main

    assert main._modelos_permitidos_de({"role": "ROL_QUE_NO_EXISTE"}) == ["flash"]


def test_override_manda_sobre_el_default_del_rol():
    """Un usuario puntual puede tener un motor adicional sin cambiar todo su rol."""
    import main

    usuario = {"role": "CONTABILIDAD", "modelos_permitidos": ["flash", "pro", "gemini"]}
    assert main._modelos_permitidos_de(usuario) == ["flash", "pro", "gemini"]


def test_override_con_modelos_invalidos_se_filtra():
    import main

    usuario = {"role": "RRHH", "modelos_permitidos": ["flash", "modelo_inventado"]}
    assert main._modelos_permitidos_de(usuario) == ["flash"]


def test_override_vacio_o_todo_invalido_cae_al_default_del_rol():
    import main

    assert main._modelos_permitidos_de({"role": "RRHH", "modelos_permitidos": []}) == ["flash"]
    assert main._modelos_permitidos_de(
        {"role": "CONTABILIDAD", "modelos_permitidos": ["algo_invalido"]}
    ) == ["flash", "pro"]


# ─── _select_llm: elegir un motor = ese motor responde solo ────────────────


@pytest.fixture
def motor_engine(monkeypatch):
    import core.nl2sql_engine as eng_mod

    return eng_mod.NL2SQLEngine(api_key="sk-test-fake", database_name="TEST")


def test_sin_forzar_siempre_flash_aunque_la_pregunta_sea_compleja(motor_engine):
    """
    Por defecto solo se consulta a Flash: una pregunta comparativa o de
    pronóstico NO se enruta automáticamente a Pro.
    """
    llm = motor_engine._select_llm(question="compara ventas y compras del año")
    assert llm is motor_engine.llm_flash

    llm2 = motor_engine._select_llm(question="proyecta las ventas del próximo trimestre")
    assert llm2 is motor_engine.llm_flash


def test_forzar_pro_usa_solo_pro(motor_engine):
    llm = motor_engine._select_llm(question="hola", modelo_forzado="pro")
    assert llm is motor_engine.llm_pro
    assert llm is not motor_engine.llm_flash


def test_motor_invalido_cae_a_flash(motor_engine):
    llm = motor_engine._select_llm(question="hola", modelo_forzado="motor_que_no_existe")
    assert llm is motor_engine.llm_flash


# ─── Revalidación en el servidor: el cliente nunca decide a ciegas ─────────


def test_validar_motor_ignora_motor_no_permitido_para_el_usuario():
    """
    Un usuario RRHH (solo Flash) pide 'gemini'. La validación del servidor
    debe IGNORARLO — nunca confiar en lo que mandó el cliente (mismo
    principio que `_redactar_campos_privados`).
    """
    from api.routes_query import _validar_motor_ia

    usuario_rrhh = {"role": "RRHH", "modules": ["RRHH"]}
    motor, aviso = _validar_motor_ia("gemini", usuario_rrhh)
    assert motor == ""
    assert aviso is not None and "gemini" in aviso.lower()


def test_validar_motor_acepta_lo_que_el_usuario_si_tiene():
    from api.routes_query import _validar_motor_ia

    usuario_admin = {"role": "ADMINISTRADOR"}
    motor, aviso = _validar_motor_ia("gemini", usuario_admin)
    assert motor == "gemini"
    assert aviso is None


def test_validar_motor_vacio_es_flash_sin_aviso():
    from api.routes_query import _validar_motor_ia

    motor, aviso = _validar_motor_ia("", {"role": "RRHH"})
    assert motor == ""
    assert aviso is None


def test_validar_motor_respeta_override_por_usuario():
    """Un usuario con override de un motor SÍ puede usarlo, aunque su rol no lo traiga por defecto."""
    from api.routes_query import _validar_motor_ia

    usuario_con_override = {"role": "CONTABILIDAD", "modelos_permitidos": ["flash", "pro", "gemini"]}
    motor, aviso = _validar_motor_ia("gemini", usuario_con_override)
    assert motor == "gemini"
    assert aviso is None


def test_validar_motor_desconocido_se_ignora():
    from api.routes_query import _validar_motor_ia

    motor, aviso = _validar_motor_ia("gpt5-turbo-max", {"role": "ADMINISTRADOR"})
    assert motor == ""
    assert aviso is not None


# ─── modelos_permitidos llega en el login (JWT y respuesta) ────────────────


def test_login_incluye_modelos_permitidos_en_jwt_y_respuesta():
    from fastapi.testclient import TestClient
    from jose import jwt as jose_jwt

    import main
    from config import JWT_ALGORITHM, JWT_SECRET_KEY

    from core import user_store

    if not user_store.usuario_activo("admin"):
        pytest.skip("Requiere el usuario local de prueba 'admin' (security_config.json no se versiona).")
    client = TestClient(main.app)
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["user"]["modelos_permitidos"] == list(main.MODELOS_IA_VALIDOS)

    payload = jose_jwt.decode(data["access_token"], JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    assert payload["modelos_permitidos"] == list(main.MODELOS_IA_VALIDOS)
