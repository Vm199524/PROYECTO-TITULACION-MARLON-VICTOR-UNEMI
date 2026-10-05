"""
Pruebas de la clasificación de preguntas entre los modelos DeepSeek.

Prueban el patrón `_RE_MODELO_EXPERTO` (armado con `_PATRONES_MODELO_EXPERTO`),
que indica si una pregunta corresponde al modelo "Instant" (deepseek-v4-flash,
la mayoría del tráfico) o al "Experto" (deepseek-v4-pro: pronósticos,
comparativas entre períodos, finanzas). Hay más casos de "debe ser Instant",
porque es fácil clasificar de más hacia el modelo caro, que cuesta y tarda más.
También verifican que ningún cliente LLM quede sin un tiempo de espera acotado.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Se importa solo la clase, sin instanciarla (evita requerir credenciales
# DeepSeek reales o dependencias pesadas como sqlalchemy en el entorno de pruebas).
from core.nl2sql_engine import NL2SQLEngine  # noqa: E402


def _es_experto(pregunta: str) -> bool:
    return bool(NL2SQLEngine._RE_MODELO_EXPERTO.search(pregunta.lower()))


@pytest.mark.parametrize(
    "pregunta",
    [
        "predice las ventas de agosto a diciembre segun enero a julio",
        "proyeccion de ingresos para el proximo semestre",
        "cual es el pronostico de ventas del cuarto trimestre",
        "compara el margen entre ventas y compras del año pasado",
        "cual es la rentabilidad del negocio este trimestre",
        "muestra el balance general del ultimo año",
        "cual es el flujo de caja de los ultimos 6 meses",
        "por que bajaron las ventas en marzo",
        "por que subieron las compras el mes pasado",
        "cual es el roi de la campaña de octubre",
        "calcula el punto de equilibrio del negocio",
        "compara las ventas de este año contra el año pasado",
    ],
)
def test_preguntas_complejas_van_a_modelo_experto(pregunta):
    assert _es_experto(pregunta) is True


@pytest.mark.parametrize(
    "pregunta",
    [
        "total de ventas por mes",
        "total de alumnos por curso",
        "cuanto hemos vendido este mes",
        "muestra una tabla con el total de trabajadores por area",
        "hola",
        "total de compras por proveedor",
        "ranking de clientes por facturacion",
        "muestra una grafica de barras con las ventas de julio",
        "cual es el total de productos en inventario",
        "que empresa esta activa",
    ],
)
def test_preguntas_simples_van_a_modelo_instant(pregunta):
    assert _es_experto(pregunta) is False


class TestTimeoutDeLosTresModelos:
    """
    Los tres clientes ChatOpenAI (flash/pro/vision) deben tener `timeout`
    propio: sin él heredan el valor por defecto del SDK de OpenAI (600
    segundos, más reintentos automáticos) y una pregunta puede quedarse
    pensando sin responder nunca. Construir un ChatOpenAI no hace ninguna
    llamada de red, así que se instancia sin credenciales reales y se
    comprueba el valor configurado en el cliente HTTP subyacente, no solo que
    el argumento se pasó.
    """

    # Tope por modelo. El motor Experto (Pro) razona antes de responder y una
    # comparativa compleja con el prompt completo no cabe en 45 s (ver
    # `_LLM_TIMEOUT_PRO_SEG` en core/nl2sql_engine.py), por eso su tope es mayor.
    #
    # Lo que esta prueba protege no es un número concreto: es que ningún
    # cliente herede los 600 s del SDK y deje al usuario esperando en silencio.
    # Los modelos rápidos quedan atados en corto y el experto tiene su margen,
    # pero ninguno queda sin límite. El flujo de despliegue ejecuta esta prueba
    # antes de publicar, así que un tope desalineado bloquearía los despliegues.
    TOPES_SEG = {"flash": 120, "pro": 180, "vision": 120}

    def test_los_tres_modelos_tienen_timeout_acotado(self):
        engine = NL2SQLEngine(api_key="fake-key-solo-para-test", database_name="TEST")
        for nombre, llm in (("flash", engine.llm_flash), ("pro", engine.llm_pro), ("vision", engine.llm_vision)):
            tope = self.TOPES_SEG[nombre]
            timeout = llm.request_timeout
            assert timeout is not None, f"llm_{nombre} no tiene timeout — heredaría el default de 600s del SDK"
            assert timeout <= tope, f"llm_{nombre} tiene un timeout de {timeout}s (tope {tope}s), demasiado alto para no sentirse como un cuelgue"
            assert llm.max_retries <= 1, f"llm_{nombre} reintenta {llm.max_retries} veces — cada reintento repite la espera completa"
