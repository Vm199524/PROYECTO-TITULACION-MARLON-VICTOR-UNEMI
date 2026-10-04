"""
Pruebas del blindaje de SQL y trazabilidad (`_redactar_campos_privados`).

Defecto grave detectado en pruebas (30/08/2026): cualquier
usuario logueado, sin importar su rol (CONTABILIDAD, RRHH, LOGISTICA,
Invitado), recibía en la respuesta de `/query` el SQL generado y el
`agent_log` completo. El frontend solo ocultaba con CSS la pestaña
"SQL"/"Cómo se calculó" — el payload de red seguía trayendo todo, visible
abriendo el inspector de red del navegador. Eso no es control de acceso.

Estas pruebas verifican que la función que quita esos campos:
  1. Los quita para cualquier rol que no sea ADMINISTRADOR.
  2. Los conserva intactos para ADMINISTRADOR (incluida la cuenta protegida
     del desarrollador, cuyo rol también es ADMINISTRADOR).
  3. No modifica el diccionario original (evita efectos secundarios si el
     payload se reutiliza en otra parte del pipeline).
  4. No revienta si faltan campos o si el payload viene vacío.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routes_query import _CAMPOS_PRIVADOS_SQL, _redactar_campos_privados  # noqa: E402


def _payload_completo() -> dict:
    return {
        "explanation": "El total de ventas de junio fue de $50,000.",
        "sql": "SELECT SUM(Total) FROM [Ventas] WHERE MONTH(Fecha) = 6",
        "agent_log": [
            "✅ CHAT activado para MONT — 12 vistas disponibles (Status: OK)",
            "🎯 Vistas en vivo: ventas=Ventas, compras=Compras",
        ],
        "business_analysis": "### Resumen\nLas ventas de junio superaron el promedio.",
        "pensamiento_analitico": "El usuario pide un total mensual; se filtra por MONTH(Fecha).",
        "sql_explanation": "Se usa SUM sobre la vista Ventas filtrando por mes.",
        "visualization_type": "value",
        "rows": [{"Total": 50000}],
        "columns": ["Total"],
    }


@pytest.mark.parametrize(
    "rol",
    ["CONTABILIDAD", "RRHH", "LOGISTICA", "GUEST", "contabilidad", "  Rrhh  ", ""],
)
def test_roles_no_administrador_pierden_los_campos_privados(rol):
    payload = _payload_completo()
    resultado = _redactar_campos_privados(payload, {"role": rol})

    for campo in _CAMPOS_PRIVADOS_SQL:
        assert campo not in resultado, f"'{campo}' no debería llegar a un usuario con rol '{rol}'"

    # Lo que sí debe seguir viajando: la respuesta útil para el usuario.
    assert resultado["explanation"] == payload["explanation"]
    assert resultado["visualization_type"] == "value"
    assert resultado["rows"] == payload["rows"]
    assert resultado["columns"] == payload["columns"]


def test_administrador_conserva_todos_los_campos():
    payload = _payload_completo()
    resultado = _redactar_campos_privados(payload, {"role": "ADMINISTRADOR"})

    for campo in _CAMPOS_PRIVADOS_SQL:
        assert campo in resultado
        assert resultado[campo] == payload[campo]


def test_administrador_en_minusculas_o_con_espacios_tambien_conserva_los_campos():
    """La comparación de rol es case-insensitive y tolera espacios sueltos."""
    payload = _payload_completo()
    for variante in ("administrador", "  ADMINISTRADOR  ", "Administrador"):
        resultado = _redactar_campos_privados(payload, {"role": variante})
        assert "sql" in resultado, f"variante de rol '{variante}' debería seguir viendo el SQL"


def test_no_modifica_el_diccionario_original():
    payload = _payload_completo()
    original_sql = payload["sql"]

    _redactar_campos_privados(payload, {"role": "CONTABILIDAD"})

    # El payload original no debe mutarse: quien lo llamó puede seguir
    # usándolo (por ejemplo, `_safe_record_query_event` para auditoría).
    assert payload["sql"] == original_sql
    assert "sql" in payload


def test_payload_sin_campos_privados_no_falla():
    payload = {"explanation": "Hola", "visualization_type": "text"}
    resultado = _redactar_campos_privados(payload, {"role": "GUEST"})
    assert resultado == payload


def test_current_user_sin_role_se_trata_como_no_privilegiado():
    payload = _payload_completo()
    resultado = _redactar_campos_privados(payload, {})
    assert "sql" not in resultado
    assert "agent_log" not in resultado
