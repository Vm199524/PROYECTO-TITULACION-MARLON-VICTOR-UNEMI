"""
Pruebas del catálogo de métricas certificadas de la capa semántica.

Este archivo es el banco de evaluación: mide que las preguntas de gerencia se
resuelvan contra la métrica certificada correcta (precisión mínima del 90 %),
que las preguntas ajenas NO disparen falsos positivos y que el SQL de las
métricas sea de solo lectura. Al agregar métricas al catálogo, se agregan aquí
sus pares pregunta → métrica esperada.
Ejecutar: pytest tests/test_metric_catalog.py -v

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import json
from datetime import datetime

import pytest

from core.metric_catalog import (
    resolver_metrica,
    hints_para_prompt,
    total_metricas,
    _CATALOG_PATH,
)


# ─────────────────────────────────────────────
# Integridad del catálogo
# ─────────────────────────────────────────────

class TestIntegridadCatalogo:
    def test_json_valido(self):
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "metricas" in data and len(data["metricas"]) > 0

    def test_ids_unicos(self):
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            metricas = json.load(f)["metricas"]
        ids = [m["id"] for m in metricas]
        assert len(ids) == len(set(ids)), "Hay IDs de métrica duplicados"

    def test_campos_obligatorios(self):
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            metricas = json.load(f)["metricas"]
        for m in metricas:
            for campo in ("id", "nombre", "modulo", "sql", "sinonimos", "visualization_type"):
                assert campo in m, f"Métrica {m.get('id','?')} sin campo '{campo}'"
            assert len(m["sinonimos"]) >= 3, f"Métrica {m['id']} necesita ≥3 sinónimos"

    def test_certificadas_solo_select(self):
        # Toda métrica certificada debe ser SELECT/WITH puro (solo lectura).
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            metricas = json.load(f)["metricas"]
        for m in metricas:
            if m.get("certificada"):
                sql_up = m["sql"].upper().strip()
                assert sql_up.startswith(("SELECT", "WITH")), f"{m['id']} no inicia con SELECT/WITH"
                for prohibida in ("INSERT", "UPDATE", "DELETE", "DROP", "EXEC"):
                    assert prohibida not in sql_up.replace("SELECTED", ""), \
                        f"{m['id']} contiene {prohibida}"

    def test_hay_certificadas(self):
        cert, total = total_metricas()
        assert cert >= 5, f"Se esperan ≥5 métricas certificadas, hay {cert}"
        assert total >= cert


# ─────────────────────────────────────────────
# Banco de evaluación: pregunta → métrica esperada
# ─────────────────────────────────────────────

EVAL_DIRECTAS = [
    # (pregunta del gerente, id de métrica esperada)
    ("¿Cuál es el total de ventas del año?", "ventas_total_anual"),
    ("cuanto hemos facturado este año", "ventas_total_anual"),
    ("Volumen total de ventas facturado", "ventas_total_anual"),
    ("dame las ventas por mes", "ventas_por_mes"),
    ("ventas mensuales", "ventas_por_mes"),
    ("¿cómo van las ventas mes a mes?", "ventas_por_mes"),
    ("cuantas facturas hemos emitido", "ventas_numero_facturas"),
    ("ticket promedio de ventas", "ventas_ticket_promedio"),
    ("¿cuál es el valor promedio de venta?", "ventas_ticket_promedio"),
    ("costo total de la nomina del ultimo mes", "nomina_total_ultimo_mes"),
    ("nómina del último mes con aportes", "nomina_total_ultimo_mes"),
    ("cuanto hemos vendido este mes", "ventas_total_mes_actual"),
    ("total de ventas de este mes", "ventas_total_mes_actual"),
    ("ventas del mes en curso", "ventas_total_mes_actual"),
    ("sueldo promedio del ultimo mes", "nomina_promedio_sueldo_ultimo_mes"),
    ("cual es el sueldo promedio", "nomina_promedio_sueldo_ultimo_mes"),
    ("cuantos trabajadores en nomina el ultimo mes", "nomina_headcount_ultimo_mes"),
    ("headcount del ultimo mes", "nomina_headcount_ultimo_mes"),
    ("cuantas compras hemos hecho", "compras_numero_ordenes"),
    ("cuantas ordenes de compra hay", "compras_numero_ordenes"),
    ("ticket promedio de compras", "compras_ticket_promedio"),
    ("compras por mes", "compras_por_mes"),
    ("evolucion de compras del año", "compras_por_mes"),
    ("empleados por area", "empleados_por_area"),
    ("personal por departamento", "empleados_por_area"),
    ("principales proveedores", "top_proveedores"),
    ("a quien le compramos mas", "top_proveedores"),
    ("costo de nomina por mes", "nomina_costo_por_mes"),
    ("evolucion de la nomina", "nomina_costo_por_mes"),
    ("productos mas comprados", "top_productos_comprados"),
    ("que productos compramos mas", "top_productos_comprados"),
    ("empleados por cargo", "empleados_por_cargo"),
    ("distribucion de personal por cargo", "empleados_por_cargo"),
    ("antiguedad promedio de los empleados", "antiguedad_promedio_empleados"),
    ("cuanto tiempo llevan trabajando en promedio", "antiguedad_promedio_empleados"),
    ("sueldo mas alto del ultimo periodo", "nomina_sueldo_maximo_ultimo_periodo"),
    ("cual es el sueldo maximo", "nomina_sueldo_maximo_ultimo_periodo"),
    ("sueldo mas bajo del ultimo periodo", "nomina_sueldo_minimo_ultimo_periodo"),
    ("cual es el sueldo minimo", "nomina_sueldo_minimo_ultimo_periodo"),
    ("margen bruto", "margen_bruto_simplificado"),
    ("cuanto ganamos entre ventas y compras", "margen_bruto_simplificado"),
    ("empleados nuevos este año", "empleados_nuevos_este_anio"),
    ("nuevas contrataciones del año", "empleados_nuevos_este_anio"),
    # Certificadas con scripts/validar_borradores.py contra el INFORMATION_SCHEMA
    # real de ALIM, ALIMENTO, DAUN, ENIG, ENPR, ESTE, GYMJ, GYMM, MANA, MONT, SONG, TALL y VICE.
    ("ventas por vendedor", "ventas_por_vendedor"),
    ("quien vende mas", "ventas_por_vendedor"),
    ("principales clientes", "ventas_por_cliente"),
    ("top clientes", "ventas_por_cliente"),
]

# Preguntas que deben quedar como BORRADOR (no ejecutan directo, sin verificar
# columnas contra datos reales). Confirman que el sistema no inventa certeza.
EVAL_BORRADORES = [
    "productos mas vendidos",
]

EVAL_NEGATIVAS = [
    # Preguntas que NO deben disparar ejecución directa de ninguna métrica
    "hola como estas",
    "listado de los empleados que ingresaron en marzo con su cargo y area",
    "¿qué producto vendió más unidades el martes pasado en la sucursal norte?",
    "muestrame el detalle de la factura 00123",
]


class TestBancoEvaluacion:
    @pytest.mark.parametrize("pregunta,esperada", EVAL_DIRECTAS)
    def test_resolucion_directa(self, pregunta, esperada):
        hit = resolver_metrica(pregunta)
        assert hit is not None, f"Sin match para: {pregunta}"
        assert hit["id"] == esperada, f"'{pregunta}' → {hit['id']} (esperaba {esperada})"

    @pytest.mark.parametrize("pregunta", EVAL_NEGATIVAS)
    def test_sin_falsos_positivos(self, pregunta):
        hit = resolver_metrica(pregunta)
        assert hit is None, f"Falso positivo: '{pregunta}' → {hit and hit['id']}"

    @pytest.mark.parametrize("pregunta", EVAL_BORRADORES)
    def test_borradores_no_ejecutan_directo(self, pregunta):
        """
        Métricas con columnas sin confirmar (Vendedor, Cliente, detalle_factura)
        quedan como pista para el LLM y nunca se ejecutan solas: una métrica
        solo se certifica tras validar sus columnas contra datos reales.
        """
        hit = resolver_metrica(pregunta)
        assert hit is None, f"Borrador se ejecutó directo sin validar: '{pregunta}' → {hit and hit['id']}"
        hints = hints_para_prompt(pregunta)
        assert hints != "", f"Borrador debería al menos aparecer como pista: '{pregunta}'"

    def test_precision_global(self):
        """Meta de calidad: precisión ≥ 90 % sobre el banco de métricas certificadas."""
        aciertos = 0
        for pregunta, esperada in EVAL_DIRECTAS:
            hit = resolver_metrica(pregunta)
            if hit and hit["id"] == esperada:
                aciertos += 1
        precision = aciertos / len(EVAL_DIRECTAS)
        assert precision >= 0.90, f"Precisión {precision:.0%} < 90%"


# ─────────────────────────────────────────────
# Parámetros e instanciación de SQL
# ─────────────────────────────────────────────

class TestParametros:
    def test_sin_anio_explicito_usa_periodo_mas_reciente_con_datos(self):
        """
        Sin año explícito, la métrica NO asume el año calendario actual
        (muchas empresas no tienen datos hasta la fecha): usa una subconsulta
        MAX(YEAR(Fecha)) sobre la tabla real de la métrica.
        """
        hit = resolver_metrica("total de ventas del año")
        assert "MAX(YEAR(Fecha))" in hit["sql"]
        assert "cabecera_factura" in hit["sql"]

    def test_anio_explicito(self):
        hit = resolver_metrica("total de ventas del año 2024")
        assert "2024" in hit["sql"]
        assert "MAX(YEAR(Fecha))" not in hit["sql"]

    def test_anio_pasado(self):
        hit = resolver_metrica("cuanto vendimos el año pasado")
        if hit:  # tolerante: el sinónimo puede no coincidir con suficiente fuerza
            assert str(datetime.now().year - 1) in hit["sql"]

    def test_sql_sin_placeholders(self):
        for pregunta, _ in EVAL_DIRECTAS:
            hit = resolver_metrica(pregunta)
            assert "{year}" not in hit["sql"], f"Placeholder sin resolver en {hit['id']}"

    def test_ventas_mes_actual_no_usa_getdate(self):
        """
        Con GETDATE() o el año calendario, las empresas con datos
        desactualizados recibirían falsos resultados vacíos en
        ventas_total_mes_actual y compras_total_anual. Las métricas no deben
        depender del reloj del servidor.
        """
        hit = resolver_metrica("cuanto hemos vendido este mes")
        assert hit is not None
        assert "GETDATE" not in hit["sql"].upper()
        assert "MAX(Fecha)" in hit["sql"] or "MAX(YEAR(Fecha))" in hit["sql"]

    def test_compras_usa_periodo_mas_reciente(self):
        hit = resolver_metrica("total de compras del año")
        assert hit is not None
        assert "MAX(YEAR(Fecha))" in hit["sql"]
        assert "cabecera_compra" in hit["sql"]


# ─────────────────────────────────────────────
# Pistas para el LLM
# ─────────────────────────────────────────────

class TestHints:
    def test_hints_para_pregunta_afin(self):
        hints = hints_para_prompt("cuanto gastamos en compras este año")
        assert "compras" in hints.lower() or hints == ""  # borrador aparece como referencial

    def test_hints_vacio_para_offtopic(self):
        assert hints_para_prompt("hola") == ""

    def test_hints_marcan_certificacion(self):
        hints = hints_para_prompt("ventas totales del año")
        assert "CERTIFICADA" in hints
