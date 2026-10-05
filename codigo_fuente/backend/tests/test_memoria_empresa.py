"""
Pruebas de la memoria de largo plazo por empresa y del aprendizaje automático.

Cubren tres condiciones para que la memoria sea útil y segura: lo aprendido en
una empresa NUNCA aparece en otra (una memoria mal aislada sería una fuga de
datos entre empresas, como la de una clave de caché global); la corrección del
usuario se guarda y se inyecta en el prompt de una consulta posterior, en vez
de responder "he registrado" sin escribir nada; y el aprendizaje se dispara con
correcciones y NO con consultas rutinarias, para no pagar una llamada al
modelo por cada pregunta.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import memoria_empresa  # noqa: E402
from core.aprendizaje import (  # noqa: E402
    _formatear_conversacion,
    extraer_y_recordar,
    hay_senal_de_aprendizaje,
)


@pytest.fixture(autouse=True)
def memoria_aislada(tmp_path, monkeypatch):
    """Cada prueba escribe en su propio archivo: nunca en la memoria real."""
    monkeypatch.setattr(memoria_empresa, "MEMORIA_FILE", tmp_path / "memoria.json")
    yield


# ─── 1. Aislamiento por empresa (lo innegociable) ────────────────────────────


def test_lo_aprendido_en_una_empresa_no_se_filtra_a_otra():
    memoria_empresa.recordar("MONT", "Advertir que 5 alumnos no tienen curso asignado.")

    assert memoria_empresa.reglas_de("MONT")
    assert memoria_empresa.reglas_de("AGGO") == []
    assert memoria_empresa.bloque_para_prompt("AGGO") == ""
    assert "alumnos" not in memoria_empresa.bloque_para_prompt("AGGO").lower()


def test_el_codigo_de_empresa_no_distingue_mayusculas_ni_espacios():
    memoria_empresa.recordar("mont", "Los alumnos retirados no cuentan en matricula vigente.")
    assert len(memoria_empresa.reglas_de(" MONT ")) == 1


def test_empresa_vacia_no_guarda_nada():
    assert memoria_empresa.recordar("", "una regla cualquiera bien larga") is None
    assert memoria_empresa.recordar(None, "otra regla cualquiera bien larga") is None


# ─── 2. La corrección sobrevive al chat ──────────────────────────────────────


def test_la_regla_persiste_y_llega_al_prompt():
    memoria_empresa.recordar(
        "MONT",
        "Al mostrar alumnos por curso, aclarar que 5 alumnos estan sin curso asignado "
        "(1.033 con curso + 5 = 1.038).",
        origen="automatico",
        evidencia="graba que faltan 5 alumnos por contabilizar",
    )
    bloque = memoria_empresa.bloque_para_prompt("MONT")
    assert "5 alumnos" in bloque
    assert "MONT" in bloque


def test_sin_memoria_el_prompt_queda_exactamente_igual_que_antes():
    # Importa que devuelva cadena vacía y no un encabezado suelto: si no,
    # cada empresa nueva arrastraría ruido inútil en todas sus consultas.
    assert memoria_empresa.bloque_para_prompt("EMPRESA_NUEVA") == ""


def test_la_regla_guardada_conserva_su_origen_y_evidencia():
    memoria_empresa.recordar(
        "MONT",
        "Excluir del conteo a los alumnos en estado retirado.",
        origen="automatico",
        evidencia="no me diste el detalle de los retirados",
        tema="alumnos",
    )
    regla = memoria_empresa.reglas_de("MONT")[0]
    assert regla["origen"] == "automatico"
    assert "retirados" in regla["evidencia"]
    assert regla["tema"] == "alumnos"
    assert regla["id"]


def test_una_regla_equivalente_no_se_duplica_sino_que_se_refuerza():
    memoria_empresa.recordar("MONT", "Advertir que 5 alumnos estan sin curso asignado.")
    memoria_empresa.recordar("MONT", "Advertir que 5 alumnos estan sin curso asignado hoy.")
    reglas = memoria_empresa.reglas_de("MONT")
    assert len(reglas) == 1
    assert reglas[0]["refuerzos"] == 2


def test_se_puede_olvidar_una_regla_aprendida_mal():
    regla = memoria_empresa.recordar("MONT", "Una conclusion equivocada que hay que borrar.")
    assert memoria_empresa.olvidar("MONT", regla["id"]) is True
    assert memoria_empresa.reglas_de("MONT") == []
    assert memoria_empresa.olvidar("MONT", regla["id"]) is False


def test_olvidar_todo_limpia_solo_esa_empresa():
    memoria_empresa.recordar("MONT", "Regla academica de la unidad educativa.")
    memoria_empresa.recordar("AGGO", "Regla comercial de la empresa agricola.")
    assert memoria_empresa.olvidar_todo("MONT") == 1
    assert memoria_empresa.reglas_de("MONT") == []
    assert len(memoria_empresa.reglas_de("AGGO")) == 1


def test_el_tope_por_empresa_conserva_las_reglas_mas_reforzadas():
    memoria_empresa.recordar("MONT", "Regla importante que el usuario repitio varias veces.")
    memoria_empresa.recordar("MONT", "Regla importante que el usuario repitio varias veces.")
    for i in range(memoria_empresa.MAX_REGLAS_POR_EMPRESA + 5):
        memoria_empresa.recordar("MONT", f"Regla de relleno numero {i} sobre un tema distinto {i}.")

    reglas = memoria_empresa.reglas_de("MONT")
    assert len(reglas) <= memoria_empresa.MAX_REGLAS_POR_EMPRESA
    assert any(r["refuerzos"] == 2 for r in reglas)


def test_un_archivo_corrupto_no_tumba_la_consulta():
    memoria_empresa.MEMORIA_FILE.write_text("{esto no es json", encoding="utf-8")
    assert memoria_empresa.reglas_de("MONT") == []
    assert memoria_empresa.bloque_para_prompt("MONT") == ""


# ─── 3. Cuándo se dispara el aprendizaje automático ──────────────────────────


@pytest.mark.parametrize(
    "mensaje",
    [
        "nuevamente no me diste una respuesta bien detallada en el contexto que faltan 5",
        "graba en memoria que faltan 5 alumnos por contabilizar",
        "deberias decir que hay 5 alumnos sin curso asignado",
        "eso esta mal, en realidad los retirados no cuentan",
        "porque tienen un estado de sin curso asignado",
        "a la proxima incluye el total por nivel tambien",
        "ten en cuenta que el periodo escolar arranca en mayo",
    ],
)
def test_detecta_correcciones_y_precisiones(mensaje):
    assert hay_senal_de_aprendizaje(mensaje) is True


@pytest.mark.parametrize(
    "mensaje",
    [
        "total de alumnos por cursos",
        "muestrame el listado de alumnos matriculados",
        "total de ventas por meses",
        "dame una tabla con las compras del 2026",
        "hola",
        "",
    ],
)
def test_las_consultas_rutinarias_no_disparan_el_aprendizaje(mensaje):
    # Cada disparo cuesta una llamada al modelo: activarlo en el tráfico normal
    # sería pagar por cada pregunta sin obtener ninguna regla a cambio.
    assert hay_senal_de_aprendizaje(mensaje) is False


# ─── 4. Extracción con el modelo (doble, sin red) ────────────────────────────


class LLMFalso:
    """Doble del modelo: devuelve el JSON que se le indique."""

    def __init__(self, respuesta: str):
        self.respuesta = respuesta
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)

        class R:
            content = self.respuesta

        return R()


def test_extrae_la_regla_y_la_guarda_en_la_empresa_correcta():
    llm = LLMFalso(
        json.dumps(
            {
                "aprender": True,
                "regla": "Al presentar alumnos por curso, advertir que 5 alumnos estan sin curso asignado.",
                "tema": "alumnos",
            }
        )
    )
    regla = extraer_y_recordar(
        "MONT",
        "graba que faltan 5 alumnos por contabilizar, tienen estado sin curso",
        [{"type": "user", "content": "total de alumnos por cursos"}],
        llm=llm,
    )
    assert regla is not None
    assert "5 alumnos" in regla["texto"]
    assert memoria_empresa.reglas_de("MONT")
    assert memoria_empresa.reglas_de("AGGO") == []


def test_si_el_modelo_dice_que_no_hay_nada_que_aprender_no_escribe():
    llm = LLMFalso(json.dumps({"aprender": False, "regla": "", "tema": "general"}))
    assert extraer_y_recordar("MONT", "un mensaje cualquiera", [], llm=llm) is None
    assert memoria_empresa.reglas_de("MONT") == []


def test_una_respuesta_ilegible_del_modelo_no_revienta_ni_escribe():
    llm = LLMFalso("lo siento, no puedo ayudarte con eso")
    assert extraer_y_recordar("MONT", "un mensaje cualquiera", [], llm=llm) is None
    assert memoria_empresa.reglas_de("MONT") == []


def test_un_fallo_del_modelo_no_propaga_la_excepcion():
    class LLMQueFalla:
        def invoke(self, prompt):
            raise RuntimeError("timeout contra el proveedor")

    # La consulta del usuario ya fue respondida: el aprendizaje no puede
    # convertirse en un error visible.
    assert extraer_y_recordar("MONT", "graba esto por favor", [], llm=LLMQueFalla()) is None


def test_el_prompt_de_extraccion_lleva_la_conversacion_y_la_empresa():
    llm = LLMFalso(json.dumps({"aprender": False, "regla": "", "tema": ""}))
    extraer_y_recordar(
        "MONT",
        "deberias aclarar los 5 sin curso",
        [
            {"type": "user", "content": "total de alumnos por cursos"},
            {"type": "ai", "content": "TOTAL 1.033"},
        ],
        llm=llm,
    )
    prompt = llm.prompts[0]
    assert "MONT" in prompt
    assert "USUARIO: total de alumnos por cursos" in prompt
    assert "ASISTENTE: TOTAL 1.033" in prompt


def test_el_historial_admite_objetos_y_diccionarios():
    class Msg:
        def __init__(self, type, content):
            self.type = type
            self.content = content

    texto = _formatear_conversacion([Msg("user", "hola"), {"type": "ai", "content": "buenas"}])
    assert "USUARIO: hola" in texto
    assert "ASISTENTE: buenas" in texto


def test_historial_vacio_no_revienta():
    assert _formatear_conversacion([]) == "(sin historial previo)"
    assert _formatear_conversacion(None) == "(sin historial previo)"
