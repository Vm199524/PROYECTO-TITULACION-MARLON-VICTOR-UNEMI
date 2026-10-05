"""
Pruebas de la redacción con IA en los caminos rápidos (core/narrativa_rapida.py).

En las métricas certificadas y el banco de preguntas, el contexto lo redacta la
IA; el texto fijo de respaldo solo se usa si la IA no responde en unos 8 s. Se
verifica que con datos y clave se pide la redacción a la IA; que sin clave o
sin filas se usa el respaldo de inmediato (no hay nada que contarle a la IA);
que un fallo o tiempo agotado de la IA NUNCA se propaga, y que el tope de
tiempo es corto, no el de una generación de SQL completa.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.narrativa_rapida import TIMEOUT_SEG, narrar_resultado_rapido  # noqa: E402


def test_tope_de_tiempo_es_corto():
    assert TIMEOUT_SEG <= 10


def test_sin_api_key_usa_respaldo_de_inmediato(monkeypatch):
    llamado = {"veces": 0}
    monkeypatch.setattr("requests.post", lambda *a, **k: llamado.update(veces=llamado["veces"] + 1))

    resultado = narrar_resultado_rapido(
        pregunta="ventas de junio", nombre_metrica="Ventas por mes",
        columns=["Total"], rows=[[125000]], respaldo="Texto fijo del catálogo.",
        api_key="", base_url="https://api.deepseek.com/v1", modelo="deepseek-v4-flash",
    )
    assert resultado == "Texto fijo del catálogo."
    assert llamado["veces"] == 0


def test_sin_filas_usa_respaldo_de_inmediato(monkeypatch):
    llamado = {"veces": 0}
    monkeypatch.setattr("requests.post", lambda *a, **k: llamado.update(veces=llamado["veces"] + 1))

    resultado = narrar_resultado_rapido(
        pregunta="ventas de junio", nombre_metrica="Ventas por mes",
        columns=["Total"], rows=[], respaldo="Texto fijo del catálogo.",
        api_key="sk-fake", base_url="https://api.deepseek.com/v1", modelo="deepseek-v4-flash",
    )
    assert resultado == "Texto fijo del catálogo."
    assert llamado["veces"] == 0


def test_respuesta_exitosa_de_la_ia_reemplaza_el_respaldo(monkeypatch):
    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "📊 **Ventas de junio: $125,000**, el mejor mes."}}]}

    monkeypatch.setattr("requests.post", lambda *a, **k: _Resp())

    resultado = narrar_resultado_rapido(
        pregunta="ventas de junio", nombre_metrica="Ventas por mes",
        columns=["Total"], rows=[[125000]], respaldo="Texto fijo del catálogo.",
        api_key="sk-fake", base_url="https://api.deepseek.com/v1", modelo="deepseek-v4-flash",
    )
    assert resultado == "📊 **Ventas de junio: $125,000**, el mejor mes."
    assert resultado != "Texto fijo del catálogo."


def test_timeout_cae_al_respaldo_sin_lanzar(monkeypatch):
    import requests as requests_mod

    def _post_que_expira(*a, **k):
        raise requests_mod.exceptions.Timeout("simulado: tardó demasiado")

    monkeypatch.setattr("requests.post", _post_que_expira)

    resultado = narrar_resultado_rapido(
        pregunta="ventas de junio", nombre_metrica="Ventas por mes",
        columns=["Total"], rows=[[125000]], respaldo="Texto fijo del catálogo.",
        api_key="sk-fake", base_url="https://api.deepseek.com/v1", modelo="deepseek-v4-flash",
    )
    assert resultado == "Texto fijo del catálogo."


def test_error_http_cae_al_respaldo_sin_lanzar(monkeypatch):
    class _RespConError:
        def raise_for_status(self):
            raise Exception("500 Internal Server Error")

    monkeypatch.setattr("requests.post", lambda *a, **k: _RespConError())

    resultado = narrar_resultado_rapido(
        pregunta="ventas de junio", nombre_metrica="Ventas por mes",
        columns=["Total"], rows=[[125000]], respaldo="Texto fijo del catálogo.",
        api_key="sk-fake", base_url="https://api.deepseek.com/v1", modelo="deepseek-v4-flash",
    )
    assert resultado == "Texto fijo del catálogo."


def test_respuesta_vacia_de_la_ia_cae_al_respaldo(monkeypatch):
    class _RespVacia:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "   "}}]}

    monkeypatch.setattr("requests.post", lambda *a, **k: _RespVacia())

    resultado = narrar_resultado_rapido(
        pregunta="ventas de junio", nombre_metrica="Ventas por mes",
        columns=["Total"], rows=[[125000]], respaldo="Texto fijo del catálogo.",
        api_key="sk-fake", base_url="https://api.deepseek.com/v1", modelo="deepseek-v4-flash",
    )
    assert resultado == "Texto fijo del catálogo."


def test_llamada_real_con_clave_del_entorno():
    """
    Prueba de integración con la API real de DeepSeek (se salta si no hay
    clave configurada en este entorno).
    """
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

    if not DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY no configurada en este entorno")

    resultado = narrar_resultado_rapido(
        pregunta="cuales fueron las ventas de junio",
        nombre_metrica="Ventas por mes",
        columns=["Mes", "Total"],
        rows=[["Junio", 125000]],
        respaldo="Texto fijo del catálogo.",
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        modelo=DEEPSEEK_MODEL,
    )
    assert resultado.strip()
    assert resultado != "Texto fijo del catálogo."
