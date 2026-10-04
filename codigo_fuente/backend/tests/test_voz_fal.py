"""
Pruebas de core/voz_fal.py — lectura en voz alta con ElevenLabs vía FAL AI.

Contrato verificado en la documentación oficial de FAL antes de escribir el
código (no adivinado): POST https://fal.run/fal-ai/elevenlabs/tts/multilingual-v2
con {"text", "voice", "language_code"}, respuesta {"audio": {"url": "..."}}.

Estas pruebas no llaman a la red real (usan `monkeypatch` sobre
`requests.post`): verifican que el módulo arma la petición correctamente y
que SIEMPRE degrada a `{"ok": False, ...}` sin lanzar, sin importar la causa
del fallo — es la garantía que permite al frontend caer de vuelta a la voz
local del navegador sin que el usuario se quede sin lectura.
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


# ─── Regresión: el endpoint HTTP /query/speak (30/08/2026) ─────────────────
#
# Bug real: `SpeakRequest(BaseModel)` estaba definida DENTRO de `get_router()`
# (anidada en la función), y FastAPI no la reconocía como el cuerpo de la
# petición — la trataba como si `req` fuera un parámetro de query string
# obligatorio, así que CUALQUIER llamada real a /query/speak fallaba con
# 422 "Field required" antes de ejecutar una sola línea del endpoint. La
# función `sintetizar_voz()` en sí estaba bien probada (arriba), pero nunca
# se probó la ruta HTTP completa — por eso el bug pasó desapercibido. Se
# corrigió moviendo `SpeakRequest` a nivel de módulo, junto a `QueryRequest`
# y las demás que sí funcionaban. Esta prueba llama al endpoint real vía
# HTTP para que este tipo de bug no vuelva a colarse sin que un test lo note.


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
