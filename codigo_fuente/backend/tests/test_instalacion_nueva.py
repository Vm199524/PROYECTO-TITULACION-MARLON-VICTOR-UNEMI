"""
Pruebas de lo que necesita una instalación nueva para funcionar.

Cubren el rol ACADEMICO por defecto, la creación de los usuarios de prueba sin
un security_config.json previo, la correspondencia entre base operativa e
institución del almacén, el control de rol del módulo académico en el backend
y la cuenta de desarrollador sin contraseñas escritas en el código.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def _cargar_script(nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, BACKEND / "scripts" / f"{nombre}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_rol_academico_viene_por_defecto():
    from core.user_store import ROLES_POR_DEFECTO

    assert ROLES_POR_DEFECTO["ACADEMICO"]["modules"] == ["ACADEMICO"]
    assert "ACADEMICO" in ROLES_POR_DEFECTO["ADMINISTRADOR"]["modules"]


def test_usuarios_de_prueba_se_crean_sin_security_config(tmp_path, monkeypatch):
    script = _cargar_script("fijar_passwords_prueba")
    destino = tmp_path / "security_config.json"
    claves = tmp_path / "usuarios_prueba.local.json"
    claves.write_text(json.dumps({u: f"clave-de-prueba-{u}" for u in script.USUARIOS}), encoding="utf-8")
    monkeypatch.setattr(script, "ARCHIVO", destino)
    monkeypatch.setattr(script, "ARCHIVO_CLAVES", claves)

    assert script.main() == 0

    config = json.loads(destino.read_text(encoding="utf-8"))
    assert "ACADEMICO" in config["roles"]
    roles = {u["username"]: u["role"] for u in config["users"]}
    assert roles["acad"] == "ACADEMICO" and roles["clec"] == "ADMINISTRADOR"
    assert all(u["password"].startswith("$2") for u in config["users"])


@pytest.mark.parametrize("base, esperado", [
    ("OULAD_PRUEBAS", "OULAD_UK"),
    ("oulad_pruebas", "OULAD_UK"),
    ("UNEMI_PRUEBAS", "UNEMI_PRUEBAS"),
    ("OTRA_BASE", "OTRA_BASE"),
    ("", ""),
])
def test_institucion_de_base(base, esperado):
    from etl.perfiles import institucion_de_base

    assert institucion_de_base(base) == esperado


@pytest.mark.parametrize("usuario, permitido", [
    ({"sub": "acad", "role": "ACADEMICO", "modules": ["ACADEMICO"]}, True),
    ({"sub": "clec", "role": "ADMINISTRADOR", "modules": []}, True),
    ({"sub": "cont", "role": "CONTABILIDAD", "modules": ["FINANZAS", "VENTAS"]}, False),
    ({"sub": "demo", "role": "GUEST", "modules": []}, False),
])
def test_modulo_academico_exige_rol(usuario, permitido):
    import main

    if permitido:
        assert main._token_con_modulo_academico(usuario) == usuario
    else:
        with pytest.raises(HTTPException) as error:
            main._token_con_modulo_academico(usuario)
        assert error.value.status_code == 403


@pytest.mark.parametrize("ruta", [
    "/api/ml/prediccion-abandono",
    "/api/ml/evaluacion-modelo",
    "/api/ml/clusters-carrera",
    "/api/benchmarking/comparativo",
])
def test_rutas_academicas_responden_403_a_otros_roles(ruta):
    from fastapi.testclient import TestClient

    import main
    from security import get_token_data

    main.app.dependency_overrides[get_token_data] = lambda: {
        "sub": "cont", "role": "CONTABILIDAD", "modules": ["FINANZAS", "VENTAS"],
    }
    try:
        respuesta = TestClient(main.app).get(ruta, params={"target_db": "UNEMI_PRUEBAS"})
    finally:
        main.app.dependency_overrides.clear()
    assert respuesta.status_code == 403


def test_cuenta_de_desarrollador_exige_clave(tmp_path, monkeypatch, capsys):
    script = _cargar_script("crear_usuario_desarrollador")
    destino = tmp_path / "security_config.json"
    monkeypatch.setattr(script, "ARCHIVO_USUARIOS", destino)
    monkeypatch.delenv("TRIPLEA_BOOTSTRAP_ADMIN_PASSWORD", raising=False)
    monkeypatch.setattr(sys, "argv", ["crear_usuario_desarrollador.py"])

    assert script.main() == 1
    assert not destino.exists()
    assert "al menos 8 caracteres" in capsys.readouterr().out
    assert not hasattr(script, "CLAVE_POR_DEFECTO")
