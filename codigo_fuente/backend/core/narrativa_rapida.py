"""
narrativa_rapida.py — Redacción con IA para respuestas de "camino rápido".

PROBLEMA QUE RESUELVE
----------------------
El 30/08/2026 el usuario marcó como regla dura, después de ver el texto de una
métrica certificada ("📌 Métrica certificada: Ventas por mes del año / Total
facturado agrupado por mes...") repetirse siempre igual: "todo contexto debe
ser generado por la IA, todo, nunca algo pregrabado — un mensaje pregrabado
solo si ya pasaron unos 8 segundos y la IA se cayó por algo".

Las métricas certificadas (`core/metric_catalog.py`) existen por una razón
legítima que NO se toca aquí: el SQL es fijo y pre-aprobado a propósito, para
garantizar que el NÚMERO sea siempre exacto — nunca se le pide a un LLM que
improvise el SQL de una fórmula de negocio ya validada. Lo que sí cambia es el
TEXTO que explica ese número: antes era la descripción fija del catálogo
("Total facturado agrupado por mes para el año indicado. Ideal para ver
tendencia."), la misma frase sin importar qué devolvió la consulta. Ahora se
le pide a la IA que redacte esa explicación usando los datos REALES ya
obtenidos — la cifra sigue siendo 100% confiable (viene del SQL certificado,
no de la IA), solo cambia quién la explica en palabras.

POR QUÉ UN CLIENTE HTTP PROPIO, SIN TOCAR NL2SQLEngine
-------------------------------------------------------
Los tres modelos de DeepSeek ya configurados en NL2SQLEngine (llm_flash,
llm_pro, llm_vision) tienen su propio timeout (45s) y hasta 1 reintento —
correcto para generar SQL desde cero, donde esperar vale la pena porque es la
ÚNICA respuesta que el usuario va a recibir. Aquí es distinto: el dato YA
está listo (el SQL certificado ya se ejecutó), así que no tiene sentido hacer
esperar al usuario más de unos segundos solo para pulir la redacción. Se usa
una llamada HTTP directa, independiente de esas tres instancias — no las
toca, no compite por sus reintentos, y tiene su propio tope corto (8s, el
mismo número que el usuario dijo que le parece aceptable esperar antes de
aceptar un mensaje de respaldo).

GARANTÍA
--------
`narrar_resultado_rapido()` NUNCA lanza y NUNCA devuelve vacío: si la IA no
responde a tiempo o falla, se devuelve el texto de respaldo que quien llama
proporcionó. La función solo MEJORA el texto cuando puede; nunca es la única
fuente de una respuesta.

CASCADA DE PROVEEDORES (corregido en la auditoría del 11/09/2026)
-------------------------------------------------------------------
Hasta esta corrección, la función solo recibía UNA credencial (DeepSeek).
Como `DEEPSEEK_API_KEY` está vacía en este proyecto (se usan las APIs
gratuitas), el resultado real era: SIEMPRE se devolvía `respaldo`, con la
misma forma de respuesta "exitosa" que si la IA sí hubiera redactado —
indistinguible desde afuera. Ahora recibe una LISTA de proveedores y
prueba cada uno en orden hasta que uno responda, con el mismo principio
de "APIs gratuitas primero" que ya usa el motor NL2SQL principal
(`core/nl2sql_engine.py::_construir_cascada`).
"""

from __future__ import annotations

import json
import logging

import requests

from core.privacidad import enmascarar_filas

logger = logging.getLogger("NarrativaRapida")

TIMEOUT_SEG = 8


def narrar_resultado_rapido(
    pregunta: str,
    nombre_metrica: str,
    columns: list,
    rows: list,
    respaldo: str,
    *,
    proveedores: list[dict] | None = None,
    # Compatibilidad hacia atrás: si alguien todavía llama con un solo
    # proveedor (api_key/base_url/modelo sueltos), se envuelve en la lista.
    api_key: str | None = None,
    base_url: str | None = None,
    modelo: str | None = None,
) -> str:
    """
    Redacta con IA la explicación de un resultado que YA se obtuvo por un
    camino rápido (métrica certificada, caché, banco de preguntas...).

    `proveedores` es una lista de dicts {api_key, base_url, modelo, nombre}
    en el orden en que deben probarse (gratuitas primero, de pago al final).
    Se intenta cada uno hasta que alguno responda dentro de TIMEOUT_SEG;
    si ninguno responde, se devuelve `respaldo` sin cambios.
    """
    if proveedores is None:
        proveedores = [{"api_key": api_key, "base_url": base_url, "modelo": modelo}] if api_key else []
    proveedores = [p for p in proveedores if p.get("api_key")]

    if not proveedores or not rows:
        return respaldo

    for proveedor in proveedores:
        texto = _intentar_proveedor(
            pregunta, nombre_metrica, columns, rows,
            api_key=proveedor["api_key"], base_url=proveedor["base_url"], modelo=proveedor["modelo"],
        )
        if texto:
            return texto
    logger.warning("[NARRATIVA RAPIDA] Los %d proveedores fallaron, usando respaldo fijo.", len(proveedores))
    return respaldo


def _intentar_proveedor(pregunta, nombre_metrica, columns, rows, *, api_key, base_url, modelo) -> str | None:
    """Un solo intento contra un proveedor. None si falla (para que el
    llamador siga con el siguiente de la cascada)."""
    try:
        # Minimización (LOPDP): el proveedor externo solo necesita las cifras
        # para redactar, no la identidad de las personas — ver core/privacidad.py.
        columns, filas_seguras = enmascarar_filas(columns, (rows or [])[:8])
        vista_previa = [dict(zip(columns or [], fila)) for fila in filas_seguras]
        datos_json = json.dumps(vista_previa, ensure_ascii=False, default=str)

        mensaje_sistema = (
            "Eres VicMar Data AI, redactando la explicación de un dato de negocio "
            "que ya se calculó con una fórmula certificada (el número es "
            "100% exacto, no lo estás calculando tú). Tu única tarea es "
            "explicarlo en palabras, con los datos reales que se te dan.\n\n"
            "Markdown limpio: **negritas** en la cifra clave (nunca cursiva), "
            "un emoji de apertura como máximo (📊), viñetas si hay varios "
            "valores. Español, directo, sin relleno. Una a tres frases — "
            "esto es una confirmación breve, no un ensayo. Habla en términos "
            "de negocio: nunca menciones nombres de vistas, tablas o "
            "columnas de la base de datos."
        )
        mensaje_usuario = (
            f"Pregunta del usuario: {pregunta}\n"
            f"Métrica: {nombre_metrica}\n"
            f"Datos reales obtenidos: {datos_json}\n\n"
            "Redacta la explicación."
        )

        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json={
                "model": modelo,
                "messages": [
                    {"role": "system", "content": mensaje_sistema},
                    {"role": "user", "content": mensaje_usuario},
                ],
                "temperature": 0.3,
                "max_tokens": 300,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT_SEG,
        )
        resp.raise_for_status()
        data = resp.json()
        texto = (
            data.get("choices", [{}])[0].get("message", {}).get("content", "")
        ).strip()
        return texto or None
    except Exception as exc:
        logger.warning("[NARRATIVA RAPIDA] Proveedor '%s' fallo, probando el siguiente: %s", modelo, exc)
        return None


def proveedores_desde_config() -> list[dict]:
    """Cascada estándar: gratuitas primero (Gemini, Groq, NVIDIA), DeepSeek
    (de pago) al final solo si las anteriores no están configuradas — mismo
    principio que `core/nl2sql_engine.py::_construir_cascada`."""
    from config import (
        DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
        GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL,
        GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL,
        NVIDIA_API_KEY, NVIDIA_BASE_URL,
    )
    from config import NVIDIA_MODELOS_DISPONIBLES
    nvidia_modelo = next(iter(NVIDIA_MODELOS_DISPONIBLES.values()), None)
    return [
        {"api_key": GEMINI_API_KEY, "base_url": GEMINI_BASE_URL, "modelo": GEMINI_MODEL},
        {"api_key": GROQ_API_KEY, "base_url": GROQ_BASE_URL, "modelo": GROQ_MODEL},
        {"api_key": NVIDIA_API_KEY, "base_url": NVIDIA_BASE_URL, "modelo": nvidia_modelo},
        {"api_key": DEEPSEEK_API_KEY, "base_url": DEEPSEEK_BASE_URL, "modelo": DEEPSEEK_MODEL},
    ]
