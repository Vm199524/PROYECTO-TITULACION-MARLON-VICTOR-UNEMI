"""
Lectura en voz alta con ElevenLabs Multilingual v2 servido por FAL AI.

La voz local del navegador (window.speechSynthesis en useLectura.js) es
gratuita y privada, pero su calidad depende de las voces instaladas en cada
equipo. Esta vía ofrece una voz consistente en español a cambio de enviar el
texto (que puede incluir cifras sensibles) a un proveedor externo. El backend
solo intermedia para no exponer FAL_KEY; no descarga el audio, el navegador
reproduce la URL temporal que devuelve el CDN de FAL.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger("VozFAL")

# Contrato de la API según la documentación de FAL:
#   POST https://fal.run/fal-ai/elevenlabs/tts/multilingual-v2
#   Headers:   Authorization: Key <FAL_KEY>, Content-Type: application/json
#   Body:      {"text": "...", "voice": "Rachel", "language_code": "es"}
#   Respuesta: {"audio": {"url": "https://v3.fal.media/files/.../audio.mp3"}}
# Es una llamada síncrona (fal.run, no la cola queue.fal.run): la respuesta trae
# directamente la URL del audio generado, sin sondear un trabajo.
_URL_TTS = "https://fal.run/fal-ai/elevenlabs/tts/multilingual-v2"

# Tope defensivo: una tabla completa leída en voz alta sería interminable y
# costosa (FAL cobra 0,10 USD por cada 1000 caracteres). useLectura.js ya
# resume las respuestas largas antes de pedir la lectura; este tope es la
# última barrera si algo llega sin resumir.
MAX_CARACTERES = 2000


def sintetizar_voz(texto: str, api_key: str, voz: str = "Rachel", idioma: str = "es") -> dict:
    """Pide a FAL (ElevenLabs Multilingual v2) el audio de `texto`.

    Returns:
        `{"ok": True, "audio_url": "..."}` si tiene éxito, o
        `{"ok": False, "error": "..."}` ante cualquier fallo; nunca lanza.
        Si `ok` es False, quien llama debe usar la voz local del navegador:
        esta función es una mejora opcional, no una dependencia.
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
