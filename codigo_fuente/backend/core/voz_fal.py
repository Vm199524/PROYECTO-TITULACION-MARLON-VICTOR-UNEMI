"""
voz_fal.py — Lectura en voz alta con ElevenLabs vía FAL AI.

PROBLEMA QUE RESUELVE
----------------------
`frontend/src/hooks/useLectura.js` lee las respuestas con `window.speechSynthesis`
del navegador: voz gratis y 100% local (el texto nunca sale de la máquina),
pero de calidad ambigua — depende de qué voces tenga instalado Windows/Chrome
en cada equipo, así que un usuario la oye natural y otro metálica.

El 30/08/2026 el usuario, con crédito disponible en su cuenta de FAL AI,
aceptó explícitamente la contrapartida de privacidad (el texto leído SÍ puede
contener sueldos, totales de ventas, nombres de proveedores) a cambio de una
voz consistente y de mucha mejor calidad. Este módulo es esa vía: ElevenLabs
Multilingual v2, servido por FAL, que sí soporta español de forma nativa.

CONTRATO REAL DE LA API (verificado en la documentación de FAL antes de
escribir este código, no adivinado):

    POST https://fal.run/fal-ai/elevenlabs/tts/multilingual-v2
    Headers: Authorization: Key <FAL_KEY>, Content-Type: application/json
    Body:    {"text": "...", "voice": "Rachel", "language_code": "es"}
    Respuesta: {"audio": {"url": "https://v3.fal.media/files/.../audio.mp3"}}

Es una llamada SÍNCRONA (fal.run, no la cola fal.subscribe/queue.fal.run):
la respuesta llega directo con la URL del audio ya generado, sin necesidad de
sondear un job. Costo confirmado en la documentación: $0.10 por cada 1000
caracteres — con $7.27 de crédito, unos 72.700 caracteres, sobra para probar
la función ampliamente.

QUÉ NO HACE
-----------
No descarga ni reenvía el audio: el navegador reproduce directo la URL que
devuelve FAL (es un enlace público de su CDN, de vida corta). El backend solo
hace de intermediario para no exponer FAL_KEY en el frontend.
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger("VozFAL")

_URL_TTS = "https://fal.run/fal-ai/elevenlabs/tts/multilingual-v2"

# Tope defensivo: una tabla completa leída en voz alta sería interminable Y
# cara ($0.10 cada 1000 caracteres). `useLectura.js` ya resume las respuestas
# largas antes de pedir la lectura, pero este tope es la última barrera si
# algo se cuela sin resumir.
MAX_CARACTERES = 2000


def sintetizar_voz(texto: str, api_key: str, voz: str = "Rachel", idioma: str = "es") -> dict:
    """
    Pide a FAL (ElevenLabs Multilingual v2) el audio de `texto`.

    Devuelve `{"ok": True, "audio_url": "..."}` en éxito, o
    `{"ok": False, "error": "..."}` en cualquier fallo — nunca lanza. Quien
    llama debe caer de vuelta a la voz local del navegador si `ok` es False:
    esta función es una MEJORA opcional, nunca una dependencia para que la
    lectura en voz alta funcione.
    """
    limpio = str(texto or "").strip()
    if not limpio:
        return {"ok": False, "error": "Texto vacío."}
    if not api_key:
        return {"ok": False, "error": "FAL_KEY no configurada."}

    limpio = limpio[:MAX_CARACTERES]

    try:
        resp = requests.post(
            _URL_TTS,
            json={"text": limpio, "voice": voz, "language_code": idioma},
            headers={
                "Authorization": f"Key {api_key}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        audio_url = (data.get("audio") or {}).get("url")
        if not audio_url:
            return {"ok": False, "error": "FAL no devolvió una URL de audio."}
        return {"ok": True, "audio_url": audio_url}
    except Exception as exc:
        logger.warning("[VOZ FAL] Fallo generando audio: %s", exc)
        return {"ok": False, "error": str(exc)}
