"""
Redacción con IA de la explicación para respuestas del camino rápido.

Las métricas certificadas (metric_catalog.py), la caché y el banco de preguntas
entregan la cifra con un SQL fijo y aprobado; este módulo solo pide a la IA que
explique en palabras el resultado real, en lugar de repetir una descripción fija.
Prueba una cascada de proveedores (gratuitos primero, como
nl2sql_engine._construir_cascada) y nunca lanza ni devuelve vacío: si ninguno
responde a tiempo, devuelve el texto de respaldo de quien llama.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

from __future__ import annotations

import json
import logging

import requests

from core.privacidad import enmascarar_filas

logger = logging.getLogger("NarrativaRapida")

# Se usa una llamada HTTP directa en lugar de los clientes de NL2SQLEngine
# (timeout de 45 s y un reintento, adecuados para generar SQL desde cero). Aquí
# el dato ya está calculado, así que no conviene hacer esperar al usuario más
# de unos segundos solo para pulir la redacción; tras este tope se usa el
# respaldo.
TIMEOUT_SEG = 8


def narrar_resultado_rapido(
    pregunta: str,
    nombre_metrica: str,
    columns: list,
    rows: list,
    respaldo: str,
    *,
    proveedores: list[dict] | None = None,
    # Compatibilidad: si se llama con un solo proveedor (api_key, base_url y
    # modelo sueltos), se envuelve en la lista.
    api_key: str | None = None,
    base_url: str | None = None,
    modelo: str | None = None,
) -> str:
    """Redacta con IA la explicación de un resultado ya obtenido por un camino rápido.

    El camino rápido puede ser una métrica certificada, la caché o el banco de
    preguntas. La cifra no cambia: viene del SQL certificado, la IA solo la
    explica.

    Args:
        proveedores: lista de dicts {api_key, base_url, modelo, nombre} en el
            orden en que deben probarse (gratuitos primero, de pago al final).
            Se descartan los que no tienen api_key.
        respaldo: texto que se devuelve si no hay filas, no hay proveedores o
            ninguno responde dentro de TIMEOUT_SEG.

    Returns:
        El texto redactado por el primer proveedor que responde, o `respaldo`.
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
    """Hace un solo intento contra un proveedor compatible con la API de OpenAI.

    Envía como máximo 8 filas enmascaradas. Devuelve None si falla, para que
    quien llama siga con el siguiente proveedor de la cascada.
    """
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
    """Devuelve la cascada estándar de proveedores leída de config.

    Primero los gratuitos (Gemini, Groq, NVIDIA NIM) y al final DeepSeek, de
    pago, con el mismo principio que `core/nl2sql_engine.py::_construir_cascada`.
    """
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
