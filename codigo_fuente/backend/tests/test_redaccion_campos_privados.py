"""
Pruebas del blindaje de SQL y trazabilidad (`_redactar_campos_privados`).

Ocultar con CSS la pestaña "SQL"/"Cómo se calculó" no es control de acceso: el
SQL generado y el `agent_log` seguirían visibles en el inspector de red del
navegador. Por eso el backend quita esos campos de la respuesta de `/query`
para cualquier rol que no sea ADMINISTRADOR y los conserva intactos para
ADMINISTRADOR (incluida la cuenta protegida del desarrollador). La función no
modifica el diccionario original, que se reutiliza en otras partes del
pipeline, y no falla si faltan campos o si el payload viene vacío.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
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
    """La comparación de rol no distingue mayúsculas y tolera espacios sueltos."""
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
