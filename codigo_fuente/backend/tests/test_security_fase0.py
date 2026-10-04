"""
tests/test_security_fase0.py — Suite de seguridad (Fase 0).
Cubre: verify_password (bcrypt estricto), validate_query (security.py)
y validate_readonly / sanitize_pipeline (core/sql_sanitizer.py).
Incluye casos de evasión conocidos.

Ejecutar: pytest tests/test_security_fase0.py -v
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import pytest

from security import verify_password, get_password_hash, validate_query
from core.sql_sanitizer import validate_readonly, sanitize_pipeline


# ─────────────────────────────────────────────
# verify_password — bcrypt estricto, sin fallback
# ─────────────────────────────────────────────

class TestVerifyPassword:
    def test_hash_valido_coincide(self):
        h = get_password_hash("MiClave$egura123")
        assert verify_password("MiClave$egura123", h) is True

    def test_hash_valido_no_coincide(self):
        h = get_password_hash("clave-correcta")
        assert verify_password("clave-incorrecta", h) is False

    def test_texto_plano_almacenado_rechazado(self):
        # Regresión crítica: antes un password almacenado en texto plano
        # era aceptado por el fallback. Ahora debe rechazarse SIEMPRE.
        assert verify_password("admin@123", "admin@123") is False

    def test_hash_invalido_rechazado(self):
        assert verify_password("clave", "no-es-un-hash") is False
        assert verify_password("clave", "$2b$corrupto") is False

    def test_valores_none_o_vacios(self):
        assert verify_password(None, None) is False
        assert verify_password("clave", "") is False
        assert verify_password("", get_password_hash("")) is True  # vacia hasheada es valida


# ─────────────────────────────────────────────
# security.validate_query — guardrail read-only
# ─────────────────────────────────────────────

class TestValidateQuery:
    @pytest.mark.parametrize("sql", [
        "SELECT * FROM clientes",
        "select nombre, total from ventas where anio = 2026",
        "WITH cte AS (SELECT 1 AS x) SELECT x FROM cte",
    ])
    def test_selects_validos(self, sql):
        ok, _ = validate_query(sql)
        assert ok is True

    @pytest.mark.parametrize("sql", [
        "DELETE FROM clientes",
        "DROP TABLE ventas",
        "UPDATE usuarios SET rol='ADMIN'",
        "INSERT INTO leads VALUES (1)",
        "TRUNCATE TABLE facturas",
        "EXEC sp_configure",
        "SELECT * FROM x; DROP TABLE y",          # inyección encadenada
        "SELECT * FROM x WHERE 1=1; DELETE FROM y",
        "SELECT nombre FROM usuarios; EXEC xp_cmdshell 'dir'",
        "",
        "   ",
    ])
    def test_operaciones_bloqueadas(self, sql):
        ok, _ = validate_query(sql)
        assert ok is False

    def test_keywords_en_minusculas_bloqueados(self):
        ok, _ = validate_query("select 1; delete from ventas")
        assert ok is False


# ─────────────────────────────────────────────
# core.sql_sanitizer — validate_readonly + pipeline
# ─────────────────────────────────────────────

class TestValidateReadonly:
    def test_select_simple_ok(self):
        ok, msg = validate_readonly("SELECT TOP 10 * FROM [CHAT].[dbo].[ventas]")
        assert ok is True and msg == "OK"

    def test_cte_ok(self):
        ok, _ = validate_readonly("WITH v AS (SELECT 1 AS n) SELECT n FROM v")
        assert ok is True

    @pytest.mark.parametrize("sql", [
        "UPDATE ventas SET total = 0",
        "DELETE FROM empleados",
        "DROP DATABASE CHAT",
        "CREATE TABLE hack (id INT)",
        "SELECT 1; TRUNCATE TABLE ventas",
        "EXEC sp_who",
        "SELECT * FROM t; EXECUTE xp_cmdshell 'whoami'",
    ])
    def test_mutaciones_bloqueadas(self, sql):
        ok, _ = validate_readonly(sql)
        assert ok is False

    @pytest.mark.parametrize("sql", [
        # Evasión con comentarios: el sanitizador debe limpiarlos antes de validar
        "SELECT * FROM t /* comentario */; DROP /*x*/ TABLE y",
        "-- comentario\nDELETE FROM ventas",
    ])
    def test_evasion_con_comentarios(self, sql):
        # El pipeline completo (que limpia comentarios) debe rechazarlas
        _, ok, _ = sanitize_pipeline(sql, question="ventas totales")
        assert ok is False

    def test_no_select_rechazado(self):
        ok, _ = validate_readonly("SHUTDOWN")
        assert ok is False


class TestSanitizePipeline:
    def test_pipeline_select_valido(self):
        sql, ok, msg = sanitize_pipeline(
            "SELECT nombre , total FROM [CHAT] . [dbo] . [ventas]",
            question="total de ventas",
        )
        assert ok is True
        assert ".[dbo]." in sql or "[dbo]" in sql  # espacios alrededor de puntos corregidos

    def test_pipeline_bloquea_dml(self):
        _, ok, _ = sanitize_pipeline("UPDATE t SET x=1", question="cualquiera")
        assert ok is False
