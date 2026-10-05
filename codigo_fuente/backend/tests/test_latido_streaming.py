"""
Pruebas del latido SSE en /query/stream.

`execute_query` es una llamada bloqueante y el navegador aborta la conexión si
pasan 25 s sin recibir NINGÚN byte (INACTIVIDAD_MS en App.jsx); sin latido,
cualquier motor (Flash, Pro u otro) se cortaría en una pregunta compleja. El
endpoint ejecuta `execute_query` en un hilo aparte y envía un comentario SSE
(": latido") cada 4 s mientras espera. La prueba verifica que una respuesta de
6 s llega completa con los tres motores.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _sesion_con_cliente_lento(username, segundos_demora):
    from core.session_manager import SESSION_STORE

    class _ClienteLento:
        def set_schema(self, *a, **k):
            pass

        def generate_sql(self, **kwargs):
            time.sleep(segundos_demora)
            return {
                "sql": "SELECT 1 AS Total",
                "explanation": "respuesta tras la demora",
                "viz_type": "value",
                "agent_log": [],
            }, None

        def generate_correction(self, *a, **k):
            return {"sql": "SELECT 1 AS Total"}

        def generate_error_narrative(self, *a, **k):
            return "error"

    class _ConectorFalso:
        is_sqlite = False
        is_postgres = False
        database = "MONT"

        def execute_query(self, sql, target_db=None):
            return ["Total"], [[100]], None

        def get_schema(self, database_override=None):
            return {"Ventas": {"type": "VISTA", "row_count": 1}}

    session = SESSION_STORE.create_session(username, "ADMINISTRADOR", "Test", [])
    session.connector = _ConectorFalso()
    session.client = _ClienteLento()
    session.schema_dict = {"Ventas": {"type": "VISTA", "row_count": 1}}
    session.context_db = "MONT"
    return session


@pytest.mark.parametrize("motor", ["", "pro", "gemini"])
def test_latido_mantiene_viva_una_respuesta_lenta_para_los_3_motores(monkeypatch, motor):
    """
    Con una respuesta simulada de 6s (más larga que un latido de 4s), la
    conexión debe seguir viva y entregar meta/done — sin importar el motor.
    """
    from unittest.mock import patch

    from starlette.testclient import TestClient

    import main
    from security import create_access_token

    # El usuario del token es ficticio: se marca como activo para que la
    # revalidación por petición (security.get_token_data) no lo rechace.
    monkeypatch.setattr("security.user_store.usuario_activo", lambda _u: True)
    username = f"test_latido_{motor or 'flash'}_{int(time.time() * 1000)}"
    _sesion_con_cliente_lento(username, segundos_demora=6)
    token = create_access_token({
        "sub": username, "role": "ADMINISTRADOR", "name": "Test",
        "modules": [], "modelos_permitidos": ["flash", "pro", "gemini"],
    })
    client = TestClient(main.app)

    with patch(
        "main._prepare_chat_for_query",
        return_value=({"Ventas": {"type": "VISTA", "row_count": 1}}, "esquema", "CHAT", "OK"),
    ):
        t0 = time.time()
        # Prompt único por motor: evita chocar con el caché de respuesta
        # completa (Redis) de una ejecución anterior de esta misma prueba.
        with client.stream(
            "POST", "/api/query/stream",
            json={"prompt": f"total de ventas {username}", "motor_ia": motor, "selected_company_code": "MONT"},
            headers={"Authorization": f"Bearer {token}"},
        ) as r:
            eventos = [line for line in r.iter_lines() if line]
            duracion = time.time() - t0

    assert r.status_code == 200
    assert any("latido" in l for l in eventos), "debió mandar al menos un latido durante la demora"
    assert any("event: meta" in l for l in eventos)
    assert any("event: done" in l for l in eventos)
    # La demora simulada (6 s) sí debe reflejarse: no se cortó antes de tiempo.
    assert duracion >= 5.5
