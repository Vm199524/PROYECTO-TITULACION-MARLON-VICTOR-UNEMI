"""
Pruebas del rol Invitado (GUEST) y su modo de demostración.

Contexto (30/08/2026): la primera versión de "Demo Mode" activaba
`active_company_code = "DEMO"` a mitad del pipeline de `execute_query`,
después de la validación de conector. Un valor residual de
`selected_company_code` (de una sesión anterior en el mismo navegador) se
colaba en la petición y desviaba el flujo hacia `_prepare_chat_for_query`
contra una empresa real, que fallaba con "servidor no cuenta con módulo de
inteligencia activado" — dejando al Invitado sin poder ni siquiera saludar.

La solución: `_responder_invitado()` en api/routes_query.py resuelve TODA la
conversación del Invitado de forma autocontenida, sin tocar connector, esquema
ni `selected_company_code`. Estas pruebas verifican que:
  1. El saludo, "solicitar acceso" y "conectar BD" respondan sin ninguna
     conexión a base de datos.
  2. Cualquier otra pregunta se responde SIEMPRE (nunca vacío, nunca error
     silencioso) usando el dataset de demostración.
  3. El texto visible dice "Invitado", nunca el código técnico "GUEST".
  4. Las 3 opciones viajan como `quick_questions` (botones reales), no como
     texto Markdown con corchetes.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeReq:
    history = []


class FakeFinalize:
    """Sustituye a `finalize_response`: solo captura el payload devuelto."""

    def __call__(self, payload, **kwargs):
        return {"payload": payload, "kwargs": kwargs}


@pytest.fixture
def fin():
    return FakeFinalize()


@pytest.fixture
def current_user():
    return {"sub": "manuko", "role": "GUEST", "modules": []}


@pytest.fixture
def invitado_almacen():
    """Da de alta en el almacén (solo en memoria) los usuarios Invitado de
    prueba que usan los tests HTTP, y limpia la caché al terminar.

    Necesario desde que `get_token_data` revalida contra el almacén central
    (ver backend/core/user_store.py y backend/security.py): un token cuyo
    `sub` no exista como usuario activo ya no se acepta. El login real
    garantiza que el usuario existe; estos tests emiten el token a mano, así
    que deben registrar al usuario igual que lo haría un login.
    """
    import core.user_store as us

    base = us.cargar_config(forzar=True)
    base["users"] = [
        u
        for u in base["users"]
        if str(u.get("username", "")).lower()
        not in ("test_invitado_regresion", "test_invitado_regresion2")
    ]
    base["users"].extend(
        [
            {
                "username": "test_invitado_regresion",
                "name": "Test",
                "role": "GUEST",
                "active": True,
                # El password nunca se usa: el token se emite a mano, sin login.
                "password": "$2b$12$invalido",
            },
            {
                "username": "test_invitado_regresion2",
                "name": "Test",
                "role": "GUEST",
                "active": True,
                "password": "$2b$12$invalido",
            },
        ]
    )
    us._cache = base
    yield
    us.invalidar_cache()


def test_saludo_nunca_toca_conector_ni_empresa(fin, current_user):
    """El saludo de Invitado no requiere `req.selected_company_code`."""
    from api.routes_query import _responder_invitado

    r = _responder_invitado(FakeReq(), "hola", current_user, fin)
    explicacion = r["payload"]["explanation"]
    assert "Invitado" in explicacion
    assert explicacion.count("GUEST") == 0
    assert r["payload"]["is_greeting"] is True


def test_saludo_trae_las_3_opciones_como_quick_questions(fin, current_user):
    from api.routes_query import _CTA_INVITADO, _responder_invitado

    r = _responder_invitado(FakeReq(), "hola", current_user, fin)
    assert r["payload"]["quick_questions"] == _CTA_INVITADO
    assert len(_CTA_INVITADO) == 3
    # Nada de placeholders tipo "[Ver Demostración]" en el texto: las
    # opciones reales viajan en quick_questions, no como Markdown con corchetes.
    assert "[Ver" not in r["payload"]["explanation"]


def test_solicitar_acceso_explica_como_pedirlo_al_administrador(fin, current_user):
    from api.routes_query import _responder_invitado

    r = _responder_invitado(FakeReq(), "quiero solicitar acceso a datos reales", current_user, fin)
    explicacion = r["payload"]["explanation"].lower()
    assert "administrador" in explicacion
    assert "gestión de usuarios" in explicacion or "gestion de usuarios" in explicacion
    # Debe identificar al usuario para que el admin sepa a quién promover.
    assert "manuko" in r["payload"]["explanation"]


def test_conectar_bd_responde_la_pregunta_de_sql_server(fin, current_user):
    """
    El usuario preguntó explícitamente "solo a SQL Server podemos
    conectarnos???" — la respuesta debe abordarlo directamente, sin evasivas.
    """
    from api.routes_query import _responder_invitado

    r = _responder_invitado(FakeReq(), "conectar mi base de datos", current_user, fin)
    explicacion = r["payload"]["explanation"]
    assert "SQL Server" in explicacion
    assert "Bases de Datos" in explicacion


def test_pregunta_de_negocio_libre_nunca_se_queda_sin_respuesta(fin, current_user):
    """
    Requisito explícito del usuario: "Nunca una pregunta se puede quedar
    sin respuesta o bugueada NUNCA asi sea que solo sea el de guest."
    """
    from api.routes_query import _responder_invitado

    preguntas = [
        "cuales fueron las ventas de enero",
        "quien es mi mejor cliente",
        "compara ventas contra compras",
        "una pregunta totalmente rara sobre xyz123",
    ]
    for pregunta in preguntas:
        r = _responder_invitado(FakeReq(), pregunta, current_user, fin)
        explicacion = r["payload"].get("explanation", "")
        assert explicacion.strip(), f"Respuesta vacía para: {pregunta!r}"
        assert r["payload"].get("quick_questions")


def test_respuesta_libre_siempre_trae_las_opciones_de_seguimiento(fin, current_user):
    from api.routes_query import _CTA_INVITADO, _responder_invitado

    r = _responder_invitado(FakeReq(), "dame un resumen del negocio", current_user, fin)
    assert r["payload"]["quick_questions"] == _CTA_INVITADO


def test_dataset_demo_existe_y_tiene_las_tablas_esperadas():
    from config import DEMO_DATASET, DEMO_DATASET_LOADED

    assert DEMO_DATASET_LOADED is True
    for clave in ("ventas", "clientes", "compras", "empleados", "productos", "indicadores_clave"):
        assert clave in DEMO_DATASET


def test_dataset_no_cargado_no_deja_al_invitado_sin_respuesta(fin, current_user, monkeypatch):
    """Si el dataset falla al cargar, se avisa con claridad — nunca un crash."""
    import api.routes_query as rq

    monkeypatch.setattr("config.DEMO_DATASET_LOADED", False)
    r = rq._responder_invitado(FakeReq(), "dame las ventas", current_user, fin)
    assert r["payload"]["explanation"].strip()
    assert r["kwargs"].get("status") == "error"


# ─── Regresión: crash real vía HTTP (30/08/2026) ─────────────────────────────
#
# Bug real: `finalize_response` (closure dentro de `execute_query`) usa
# `selected_company_code` en `_safe_record_query_event`. Esa variable se
# asigna en la sección "1. ARQUITECTURA STATELESS", que el rol Invitado NUNCA
# alcanza (retorna antes, desde `_responder_invitado`). Python trata el
# nombre como local de `execute_query` por esa asignación posterior, así que
# referenciarlo antes de que se ejecute esa línea lanza
# "NameError: cannot access free variable 'selected_company_code'" — un
# usuario Invitado no podía ni siquiera saludar. Se prueba con una petición
# HTTP real (TestClient), no solo llamando a `_responder_invitado` en
# aislamiento, porque el bug estaba específicamente en cómo esa función se
# conecta con el resto de `execute_query` — una prueba unitaria de
# `_responder_invitado` sola no lo habría detectado.


def test_invitado_puede_saludar_sin_crashear_via_http(invitado_almacen):
    from fastapi.testclient import TestClient

    import main
    from core.session_manager import SESSION_STORE
    from security import create_access_token

    SESSION_STORE.create_session("test_invitado_regresion", "GUEST", "Test", [])
    token = create_access_token(
        {"sub": "test_invitado_regresion", "role": "GUEST", "name": "Test", "modules": []},
    )

    client = TestClient(main.app)
    r = client.post(
        "/api/query",
        json={"prompt": "hola"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "Invitado" in data.get("explanation", "")
    assert data.get("quick_questions")


def test_invitado_puede_preguntar_algo_de_negocio_sin_crashear_via_http(invitado_almacen):
    from fastapi.testclient import TestClient

    import main
    from core.session_manager import SESSION_STORE
    from security import create_access_token

    SESSION_STORE.create_session("test_invitado_regresion2", "GUEST", "Test", [])
    token = create_access_token(
        {"sub": "test_invitado_regresion2", "role": "GUEST", "name": "Test", "modules": []},
    )

    client = TestClient(main.app)
    r = client.post(
        "/api/query",
        json={"prompt": "cuales fueron las ventas de enero"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("explanation", "").strip()


# ─── responder_demo (motor de IA) ────────────────────────────────────────────


def test_responder_demo_nunca_lanza_excepcion_sin_motor(monkeypatch):
    """
    Doble red de seguridad: si el motor no está disponible (sin engine
    inicializado), el cliente arma un resumen determinista en vez de
    propagar el error. Se fuerza `_engine = None` y se neutraliza el
    reintento de inicialización para no depender de si este entorno tiene
    una API key real configurada (la tiene, y si dejáramos que
    `_try_init_engine` corriera de nuevo, la prueba llamaría al proveedor
    real por la red — lento e innecesario para probar el camino de fallback).
    """
    from core.deepseek_client import DeepSeekClient

    cliente = DeepSeekClient(api_key="")
    monkeypatch.setattr(cliente, "_try_init_engine", lambda: None)
    cliente._engine = None
    cliente._engine_error = "sin motor (simulado para la prueba)"

    dataset = {"indicadores_clave": {"ingresos_total_semestre": 845700}}
    resultado = cliente.responder_demo(question="ventas de enero", dataset=dataset, history="")

    assert resultado["explanation"].strip()
    assert "845700" in resultado["explanation"]
    assert resultado["visualization_type"] == "text"


# ─── Etiquetas de rol (GUEST -> Invitado) ────────────────────────────────────


def test_role_labels_frontend_map_guest_a_invitado():
    """
    El código técnico del rol no cambia (JWT, security_config.json), pero
    el texto que ve el usuario en el header y en Gestión de Usuarios sí.
    Se verifica leyendo el archivo fuente (no hay runtime JS en pytest).
    """
    ruta = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "frontend", "src", "utils", "roles.js",
    )
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    assert "GUEST: 'Invitado'" in contenido
