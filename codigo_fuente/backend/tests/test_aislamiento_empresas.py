"""
Pruebas del aislamiento de datos entre empresas en el caché semántico.

Todas las consultas se ejecutan contra la base `CHAT` (el `active_db` es "CHAT"
para todas las empresas). Si la clave del caché fuera solo el texto de la
pregunta, una respuesta guardada en la empresa A se reutilizaría al preguntar
lo mismo en la empresa B y mostraría datos de otra empresa. Las pruebas
garantizan que la clave incluye la empresa y que las entradas sin empresa
asociada nunca se sirven.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import pytest

from core.semantic_processor import SemanticProcessor


@pytest.fixture
def proc(tmp_path, monkeypatch):
    """SemanticProcessor con un caché temporal, para no tocar el real."""
    p = SemanticProcessor()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / "semantic_query_cache.json"
    cache_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(p, "cache_path", cache_file)
    return p


class TestAislamientoCacheSemantico:
    def test_no_reutiliza_respuesta_de_otra_empresa(self, proc):
        """Lo que guarda la empresa A no se entrega estando activa la empresa B."""
        proc.save_to_cache(
            prompt="total de empleados registrados",
            sql="SELECT COUNT(*) FROM ficha_trabajador",
            viz_type="value",
            explanation="Total de empleados de la empresa A",
            active_db="CHAT",
            company_code="AGRINAG",
        )

        fuga = proc.get_cached_query(
            "total de empleados registrados", "CHAT", company_code="DELPYG"
        )
        assert fuga is None, (
            "FUGA DE DATOS: una respuesta guardada para AGRINAG se devolvió "
            "estando activa la empresa DELPYG"
        )

    def test_si_reutiliza_dentro_de_la_misma_empresa(self, proc):
        """El caché debe seguir sirviendo: aislar no es desactivar."""
        proc.save_to_cache(
            prompt="total de empleados registrados",
            sql="SELECT COUNT(*) FROM ficha_trabajador",
            viz_type="value",
            explanation="Total de empleados",
            active_db="CHAT",
            company_code="AGRINAG",
        )

        acierto = proc.get_cached_query(
            "total de empleados registrados", "CHAT", company_code="AGRINAG"
        )
        assert acierto is not None
        assert acierto["cache_hit"] is True

    def test_entradas_antiguas_sin_empresa_se_ignoran(self, proc):
        """
        Una entrada sin empresa asociada no tiene un origen verificable: se
        trata como no confiable y NO se devuelve nunca.
        """
        proc.cache_path.write_text(
            json.dumps({
                "total de empleados registrados": {
                    "sql": "SELECT COUNT(*) FROM ficha_trabajador",
                    "viz_type": "value",
                    "explanation": "Respuesta de origen desconocido",
                }
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        for empresa in ("AGRINAG", "DELPYG", "ALIM", ""):
            assert proc.get_cached_query(
                "total de empleados registrados", "CHAT", company_code=empresa
            ) is None, f"Entrada antigua sin empresa se sirvió a '{empresa}'"

    def test_la_clave_incluye_la_empresa(self, proc):
        """Verificación estructural directa de la clave."""
        clave_a = proc._clave_cache("ventas del año", "AGRINAG")
        clave_b = proc._clave_cache("ventas del año", "DELPYG")
        assert clave_a != clave_b
        assert "AGRINAG" in clave_a and "DELPYG" in clave_b

    def test_empresa_vacia_no_colisiona_con_empresa_real(self, proc):
        """Sin empresa identificada, tampoco debe mezclarse con una real."""
        proc.save_to_cache(
            prompt="ventas del año", sql="SELECT 1", viz_type="value",
            explanation="", active_db="CHAT", company_code="",
        )
        assert proc.get_cached_query("ventas del año", "CHAT", company_code="ALIM") is None
