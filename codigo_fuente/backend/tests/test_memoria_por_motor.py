"""
Pruebas de la memoria persistente del caché semántico por motor de IA.

El caché semántico (core/semantic_processor.py) guarda en disco sin TTL para
responder en segundos una pregunta repetida, y separa la clave por motor para
que Flash, Pro y Gemini nunca se sirvan la respuesta cacheada de otro. La
respuesta guardada sigue siendo la que generó la IA (nunca un texto enlatado):
solo se evita regenerarla para el MISMO motor y la MISMA empresa.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
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
