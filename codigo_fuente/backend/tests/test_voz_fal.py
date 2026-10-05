"""
Pruebas de la lectura en voz alta con ElevenLabs vía FAL AI (core/voz_fal.py).

El contrato sigue la documentación oficial de FAL: POST
https://fal.run/fal-ai/elevenlabs/tts/multilingual-v2 con {"text", "voice",
"language_code"} y respuesta {"audio": {"url": "..."}}. Las pruebas no llaman
a la red real (usan `monkeypatch` sobre `requests.post`): verifican que la
petición se arma bien y que el módulo SIEMPRE degrada a `{"ok": False, ...}`
sin lanzar, sea cual sea el fallo, para que el frontend recurra a la voz local
del navegador y el usuario no se quede sin lectura.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.voz_fal import MAX_CARACTERES, sintetizar_voz  # noqa: E402


def test_sin_texto_no_llama_a_la_red(monkeypatch):
    llamado = {"veces": 0}
    monkeypatch.setattr("requests.post", lambda *a, **k: llamado.update(veces=llamado["veces"] + 1))

    resultado = sintetizar_voz("   ", api_key="fal-fake")
    assert resultado == {"ok": False, "error": "Texto vacío."}
    assert llamado["veces"] == 0


def test_sin_api_key_no_llama_a_la_red(monkeypatch):
    llamado = {"veces": 0}
    monkeypatch.setattr("requests.post", lambda *a, **k: llamado.update(veces=llamado["veces"] + 1))

    resultado = sintetizar_voz("hola", api_key="")
    assert resultado["ok"] is False
    assert llamado["veces"] == 0


def test_peticion_bien_formada(monkeypatch):
    capturado = {}

    class _RespuestaFalsa:
        def raise_for_status(self):
            pass

        def json(self):
            return {"audio": {"url": "https://v3.fal.media/files/zebra/audio.mp3"}}

    def _post_falso(url, json, headers, timeout):
        capturado["url"] = url
        capturado["json"] = json
        capturado["headers"] = headers
        capturado["timeout"] = timeout
        return _RespuestaFalsa()

    monkeypatch.setattr("requests.post", _post_falso)

    resultado = sintetizar_voz("Hola, esto es una prueba.", api_key="fal-clave-secreta", voz="Rachel")

    assert resultado == {"ok": True, "audio_url": "https://v3.fal.media/files/zebra/audio.mp3"}
    assert capturado["url"] == "https://fal.run/fal-ai/elevenlabs/tts/multilingual-v2"
    assert capturado["json"]["text"] == "Hola, esto es una prueba."
    assert capturado["json"]["voice"] == "Rachel"
    assert capturado["json"]["language_code"] == "es"
    assert capturado["headers"]["Authorization"] == "Key fal-clave-secreta"


def test_texto_largo_se_recorta(monkeypatch):
    capturado = {}

    class _RespuestaFalsa:
        def raise_for_status(self):
            pass

        def json(self):
            return {"audio": {"url": "https://ejemplo/audio.mp3"}}

    def _post_falso(url, json, headers, timeout):
        capturado["texto"] = json["text"]
        return _RespuestaFalsa()

    monkeypatch.setattr("requests.post", _post_falso)

    texto_larguisimo = "a" * (MAX_CARACTERES + 500)
    sintetizar_voz(texto_larguisimo, api_key="fal-fake")
    assert len(capturado["texto"]) == MAX_CARACTERES


def test_respuesta_sin_audio_url_no_lanza(monkeypatch):
    class _RespuestaSinAudio:
        def raise_for_status(self):
            pass

        def json(self):
            return {"algo_inesperado": True}

    monkeypatch.setattr("requests.post", lambda *a, **k: _RespuestaSinAudio())

    resultado = sintetizar_voz("hola", api_key="fal-fake")
    assert resultado["ok"] is False
    assert "audio" in resultado["error"].lower()


def test_error_de_red_nunca_se_propaga(monkeypatch):
    def _post_que_falla(*a, **k):
        raise ConnectionError("simulado: sin red")

    monkeypatch.setattr("requests.post", _post_que_falla)

    resultado = sintetizar_voz("hola", api_key="fal-fake")
    assert resultado == {"ok": False, "error": "simulado: sin red"}


def test_error_http_4xx_5xx_nunca_se_propaga(monkeypatch):
    class _RespuestaConError:
        def raise_for_status(self):
            raise Exception("401 Unauthorized")

    monkeypatch.setattr("requests.post", lambda *a, **k: _RespuestaConError())

    resultado = sintetizar_voz("hola", api_key="fal-fake-invalida")
    assert resultado["ok"] is False
    assert "401" in resultado["error"]


# ─── El endpoint HTTP /query/speak ─────────────────────────────────────────
#
# `SpeakRequest(BaseModel)` debe estar definida a nivel de módulo, junto a
# `QueryRequest`: si se anidara dentro de `get_router()`, FastAPI no la
# reconocería como cuerpo de la petición y trataría `req` como un parámetro
# obligatorio de la cadena de consulta, así que toda llamada a /query/speak
# fallaría con 422 "Field required" antes de ejecutar el endpoint. Probar solo
# `sintetizar_voz()` (arriba) no detecta ese fallo; por eso esta prueba llama
# al endpoint real vía HTTP.


def test_endpoint_speak_acepta_el_body_via_http(monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from security import create_access_token

    monkeypatch.setattr("config.FAL_KEY", "fal-fake-key")
    monkeypatch.setattr(
        "core.voz_fal.sintetizar_voz",
        lambda texto, api_key, voz="Rachel", idioma="es": {"ok": True, "audio_url": "https://ejemplo/audio.mp3"},
    )

    monkeypatch.setattr("security.user_store.usuario_activo", lambda _u: True)
    token = create_access_token({"sub": "test_speak_http", "role": "ADMINISTRADOR"})
    client = TestClient(main.app)

    r = client.post(
        "/api/query/speak",
        json={"text": "hola"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["audio_url"] == "https://ejemplo/audio.mp3"
