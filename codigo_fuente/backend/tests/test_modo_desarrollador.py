"""
Pruebas de la seña de desarrollador y del detector de sondeo de capacidades.

La seña (core/modo_desarrollador.py) debe ser una acción del sistema y no texto
del modelo: se registra DE VERDAD en disco y sobrevive a un chat nuevo o a un
reinicio. Lo más importante es lo que NO puede hacer: activarse desde una
cuenta que no es su dueña. El detector de sondeo de capacidades no debe
confundir un mensaje largo con "qué puedo consultar" y responder con el
catálogo de áreas de negocio en vez de atender lo que se pidió.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def dev(tmp_path, monkeypatch):
    """
    Módulo recargado con su archivo de registro en un directorio temporal.

    Sin esto, las pruebas escribirían en el `.cache` real del backend y podrían
    dejar registrada una seña de un usuario ficticio en la instalación del
    desarrollador.
    """
    monkeypatch.delenv("TRIPLEA_USUARIO_DEV", raising=False)
    monkeypatch.delenv("TRIPLEA_SENA_DEV", raising=False)

    import core.modo_desarrollador as modulo

    modulo = importlib.reload(modulo)
    monkeypatch.setattr(modulo, "ARCHIVO", tmp_path / "modo_desarrollador.json")
    return modulo


# ─── Reconocimiento de la seña ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "texto",
    ["Soy VM", "soy vm", "SOY VM.", "  soy   vm  ", "¡Soy VM!"],
)
def test_reconoce_la_sena_con_cualquier_grafia(dev, texto):
    encontrada, resto = dev.detectar_sena(texto)
    assert encontrada is True
    assert resto == ""


def test_la_sena_admite_una_pregunta_en_el_mismo_mensaje(dev):
    encontrada, resto = dev.detectar_sena("Soy VM, explícame el pipeline de consultas")
    assert encontrada is True
    # El resto conserva tildes y mayúsculas: es lo que se le manda al modelo.
    assert resto == "explícame el pipeline de consultas"


@pytest.mark.parametrize(
    "texto",
    [
        "soy vendedor de la empresa",
        "quien soy",
        "dame el total de ventas",
        "",
        "vm",
    ],
)
def test_no_confunde_texto_normal_con_la_sena(dev, texto):
    encontrada, _ = dev.detectar_sena(texto)
    assert encontrada is False


def test_la_sena_es_configurable_por_entorno(dev, monkeypatch):
    monkeypatch.setenv("TRIPLEA_SENA_DEV", "codigo aurora")
    assert dev.detectar_sena("Código Aurora")[0] is True
    assert dev.detectar_sena("Soy VM")[0] is False


# ─── Quién puede usarla ─────────────────────────────────────────────────────


def test_el_primer_administrador_reclama_la_sena(dev):
    ok, mensaje = dev.activar("victor", "ADMINISTRADOR")
    assert ok is True
    assert "registrada" in mensaje.lower()
    assert dev.dueno_registrado() == "victor"


def test_un_usuario_sin_rol_admin_no_puede_reclamarla(dev):
    ok, mensaje = dev.activar("contadora", "USUARIO")
    assert ok is False
    assert mensaje == ""
    assert dev.dueno_registrado() == ""
    assert dev.esta_activo("contadora") is False


def test_una_vez_registrada_solo_sirve_para_su_dueno(dev):
    dev.activar("victor", "ADMINISTRADOR")
    # Otro administrador de la misma instalación NO hereda la seña.
    ok, _ = dev.activar("otro_admin", "ADMINISTRADOR")
    assert ok is False
    assert dev.esta_activo("otro_admin") is False
    assert dev.esta_activo("victor") is True


def test_el_dueno_puede_fijarse_por_entorno(dev, monkeypatch):
    monkeypatch.setenv("TRIPLEA_USUARIO_DEV", "victor")
    ok, _ = dev.activar("otro_admin", "ADMINISTRADOR")
    assert ok is False
    assert dev.activar("victor", "ADMINISTRADOR")[0] is True


# ─── Persistencia en disco ──────────────────────────────────────────────────


def test_el_reconocimiento_sobrevive_al_reinicio_del_backend(dev, monkeypatch):
    dev.activar("victor", "ADMINISTRADOR")
    archivo = dev.ARCHIVO
    assert archivo.exists(), "la seña debe quedar escrita en disco, no en memoria"

    # Simula un reinicio: el módulo se recarga de cero y solo conserva lo que
    # esté en el archivo.
    import core.modo_desarrollador as modulo

    recargado = importlib.reload(modulo)
    monkeypatch.setattr(recargado, "ARCHIVO", archivo)
    assert recargado.esta_activo("victor") is True
    assert recargado.dueno_registrado() == "victor"


def test_se_puede_salir_del_modo_sin_perder_el_registro(dev):
    dev.activar("victor", "ADMINISTRADOR")
    assert dev.desactivar("victor") is True
    assert dev.esta_activo("victor") is False
    # La seña sigue siendo suya: puede volver a entrar cuando quiera.
    assert dev.dueno_registrado() == "victor"
    assert dev.activar("victor", "ADMINISTRADOR")[0] is True


@pytest.mark.parametrize(
    "texto", ["modo normal", "salir de modo VM", "Desactiva modo VM", "ya no soy VM"]
)
def test_frases_de_salida(dev, texto):
    assert dev.es_frase_de_salida(texto) is True


def test_una_consulta_normal_no_es_frase_de_salida(dev):
    assert dev.es_frase_de_salida("dame las ventas del mes normal") is False


def test_un_archivo_corrupto_no_tumba_el_chat(dev):
    dev.ARCHIVO.write_text("{esto no es json", encoding="utf-8")
    assert dev.esta_activo("victor") is False
    assert dev.dueno_registrado() == ""


# ─── Prefijo explícito de conversación libre ────────────────────────────────


def test_prefijo_vm_fuerza_conversacion_libre(dev):
    forzado, texto = dev.quitar_prefijo_libre("vm: explícame los JWT")
    assert forzado is True
    assert texto == "explícame los JWT"


def test_sin_prefijo_el_texto_queda_intacto(dev):
    forzado, texto = dev.quitar_prefijo_libre("total de ventas de julio")
    assert forzado is False
    assert texto == "total de ventas de julio"


# ─── Sondeo de capacidades: mensajes largos ─────────────────────────────────


def _probe():
    from api.routes_query import _is_capability_probe

    return _is_capability_probe


def test_pregunta_corta_de_capacidades_sigue_detectandose():
    assert _probe()("¿qué puedo consultar?") is True
    assert _probe()("qué datos tiene esta empresa") is True


def test_cuenta_protegida_por_su_marca_en_el_archivo():
    import main

    assert main._es_usuario_protegido({"username": "adminvm", "protected": True}) is True
    assert main._es_usuario_protegido({"username": "contador"}) is False
    assert main._es_usuario_protegido({}) is False


def test_el_dueno_de_la_sena_queda_protegido_aunque_le_quiten_la_marca(monkeypatch):
    """
    Defensa en profundidad: si alguien edita security_config.json a mano y
    borra `protected`, la cuenta que posee la seña de desarrollador sigue sin
    poder eliminarse.
    """
    import main

    monkeypatch.setattr(
        "core.modo_desarrollador.dueno_registrado", lambda: "adminvm"
    )
    assert main._es_usuario_protegido({"username": "adminvm"}) is True
    assert main._es_usuario_protegido({"username": "admin"}) is False


def test_la_bandera_protected_llega_al_frontend():
    import main

    publico = main._usuario_publico({"username": "adminvm", "protected": True})
    assert publico["protected"] is True
    assert "password" not in publico


def test_mensaje_largo_ya_no_cae_en_la_respuesta_por_defecto():
    """
    Este texto contiene de paso 'alcance', 'detecta' y 'puedo consultar', pero
    no es un sondeo de capacidades: debe atenderse lo que el usuario pide, no
    responder con el catálogo de áreas de negocio.
    """
    mensaje = (
        "Quiero que revises el alcance del módulo de ventas porque el sistema "
        "detecta facturas anuladas y las está sumando al total; además necesito "
        "que me digas si eso mismo puedo consultar para compras, y que compares "
        "el resultado con lo que muestra el panel de Indicadores para el mismo "
        "período, porque ahí las cifras no coinciden y necesito entender por qué."
    )
    assert _probe()(mensaje) is False
