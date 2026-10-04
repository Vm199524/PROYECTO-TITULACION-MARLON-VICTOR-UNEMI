"""
Pruebas de la memoria persistente por motor (30/08/2026).

El caché semántico (core/semantic_processor.py) ya guardaba en disco sin
TTL — perfecto para "responder en 2 segundos al día siguiente". Lo único
que faltaba: separar la clave por motor de IA, para que Flash, Pro y Gemini
nunca se sirvan la respuesta cacheada de otro. Sigue siendo la IA la que
respondió esa memoria (nunca un texto enlatado): solo se evita regenerar
lo que ya se generó antes, para el MISMO motor.
"""

import os
import sys
import tempfile
import pathlib

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sp(monkeypatch):
    from core.semantic_processor import SemanticProcessor

    instancia = SemanticProcessor.__new__(SemanticProcessor)
    instancia.base_dir = pathlib.Path(tempfile.mkdtemp())
    instancia.cache_path = instancia.base_dir / "test_cache.json"
    instancia.dict_path = instancia.base_dir / "noexiste.json"
    instancia.dictionary = {"mappings": []}
    instancia._ensure_cache_exists()
    return instancia


def test_misma_pregunta_dos_motores_no_se_cruzan(sp):
    sp.save_to_cache("total de ventas", "SELECT 1", "value", "Respuesta FLASH", "CHAT", company_code="MONT", motor="flash")
    sp.save_to_cache("total de ventas", "SELECT 2", "value", "Respuesta PRO", "CHAT", company_code="MONT", motor="pro")

    assert sp.get_cached_query("total de ventas", "CHAT", company_code="MONT", motor="flash")["explanation"] == "Respuesta FLASH"
    assert sp.get_cached_query("total de ventas", "CHAT", company_code="MONT", motor="pro")["explanation"] == "Respuesta PRO"
    assert sp.get_cached_query("total de ventas", "CHAT", company_code="MONT", motor="gemini") is None


def test_sin_motor_especificado_usa_flash_por_defecto(sp):
    sp.save_to_cache("hola", "SELECT 1", "text", "Respuesta default", "CHAT", company_code="MONT")
    assert sp.get_cached_query("hola", "CHAT", company_code="MONT", motor="flash")["explanation"] == "Respuesta default"
    assert sp.get_cached_query("hola", "CHAT", company_code="MONT")["explanation"] == "Respuesta default"


def test_sigue_aislado_por_empresa_ademas_de_por_motor(sp):
    sp.save_to_cache("total de ventas", "SELECT 1", "value", "Respuesta MONT", "CHAT", company_code="MONT", motor="pro")
    assert sp.get_cached_query("total de ventas", "CHAT", company_code="SONG", motor="pro") is None
    assert sp.get_cached_query("total de ventas", "CHAT", company_code="MONT", motor="pro")["explanation"] == "Respuesta MONT"
