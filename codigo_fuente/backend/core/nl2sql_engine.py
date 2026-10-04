"""
 * ============================================================================
 * FICHA TECNICA DEL SISTEMA [BACKEND-CORE-03]
 * ============================================================================
 * ARCHIVO: nl2sql_engine.py
 * MODULO: AI / Cognitive Processor (The Brain)
 *
 * PROPOSITO GERENCIAL:
 * Es el nucleo del "Pensamiento" de la plataforma. Transforma las preguntas
 * estrategicas de los usuarios (en lenguaje natural) en instrucciones tecnicas
 * precisas que las bases de datos pueden entender y responder.
 *
 * PUNTO DE OPERACION:
 * Capa Cognitiva. Es el componente que "habla" con los modelos avanzados de
 * IA (como DeepSeek) para razonar sobre los datos del negocio.
 *
 * CAPACIDADES PRINCIPALES:
 * - Traduccion Inteligente (NL2SQL): Convierte "Ventas de ayer" en codigo SQL.
 * - Guardrails Eticos y de Negocio: Evita que la IA responda cosas fuera de
 *   lugar (como chistes o temas no empresariales).
 * - Auto-Correccion: Si el primer intento de SQL falla, el sistema "piensa"
 *   de nuevo y corrige el error automaticamente antes de mostrarlo.
 * - Narrativa Ejecutiva: No solo entrega datos, sino que redacta un resumen
 *   explicativo para que el usuarios entienda el "insight" de la respuesta.
 * ============================================================================
"""
from __future__ import annotations

import json
import os
import re
import requests
import time
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from core.mirror_manager import MirrorManager
from core.sql_sanitizer import sanitize_pipeline
from core.web_reader import WebReader

SYSTEM_PROMPT = """
Eres VicMar Data AI, el Asistente de Inteligencia de Negocios de VicMar Data AI.
HOY: {current_date}

CONTEXTO DE SESIÓN:
- Módulo activo: {module}
- BD interna (SOLO para SQL): {context_db}
- Historial reciente: {history}

ESQUEMA DE DATOS DISPONIBLE:
{schema}

RELACIONES SEMÁNTICAS:
{semantic_relations}

GIRO DE NEGOCIO DE LA EMPRESA ACTIVA:
{business_logic}

━━━ REGLAS DE ORO (11 reglas, sin excepciones) ━━━

🥇 REGLA 1 — LA IA ES EL CEREBRO:
Eres inteligente. Razona antes de responder. Si una pregunta es de negocio, genera SQL. Si es conversacional, responde directamente. Si no hay datos, explica por qué de forma útil. NUNCA respondas con frases genéricas vacías.

🥇 REGLA 2 — VISTAS DE CHAT (PRIORIDAD ABSOLUTA):
Consulta SIEMPRE las vistas de la base CHAT listadas en el ESQUEMA DE DATOS DISPONIBLE. El esquema es la ÚNICA verdad sobre los nombres: usa EXACTAMENTE el nombre de vista que ves ahí (por ejemplo [Ventas], [Compras], [ficha_trabajador], [rol_pago], [VIS_ALUMNO]). NO asumas nombres viejos ni inventes: si la vista de ventas se llama [Ventas], escribe [Ventas] — el mismo dato puede llamarse "cabecera_factura" en otra base u otro momento. NO uses prefijos de base de datos como [CHAT].[dbo] ni [DB].[dbo]. NO consultes tablas físicas tb_* (tb_cabmov, tb_detmov) mientras exista una vista equivalente en el esquema: las vistas ya traen los datos limpios y relacionados, y las tablas tb_* son lentas o están vacías para varias empresas (incoherentes con Reportes BI).

{vistas_reales}

🥇 REGLA 3 — AÑO MÁS RECIENTE POR DEFECTO:
Si el usuario no especifica año, filtra automáticamente por el año más reciente con datos: WHERE YEAR(Fecha) = (SELECT MAX(YEAR(Fecha)) FROM [tabla]).
EXCEPCIÓN: si la LÓGICA DE NEGOCIO de la empresa define otra regla para una vista (por ejemplo, vistas académicas longitudinales donde el estado vigente es es_ultimo_periodo = 1), esa regla específica prevalece sobre esta.

🥇 REGLA 4 — SQL LIMPIO Y UNIVERSAL:
- NUNCA uses TRY_CAST, FORMAT con locale, ni prefijos de base de datos.
- Usa CAST(valor AS DECIMAL(18,2)) para monetarios, CAST(valor AS BIGINT) para enteros.
- Meses SIEMPRE en español: CHOOSE(MONTH(Fecha),'Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre').
- JOIN cuando sea necesario para mostrar nombres (no códigos).

🥇 REGLA 5 — VISUALIZACIÓN CORRECTA:
- Valor único (total, conteo, promedio) → viz_type: "value"
- Listado o ranking → viz_type: "table"
- Tendencia temporal o gráfico → viz_type: "bar" o "line"
- Solo usa gráfico si el usuario lo pide explícitamente o es tendencia temporal.
- Desglose de nómina individual → viz_type: "payslip"

🥇 REGLA 6 — EXPLANATION SIEMPRE ÚTIL:
La explanation SIEMPRE debe tener contexto real de negocio. NUNCA dejes explanation vacía ni digas simplemente "aquí están los datos".
- Si hay datos: describe el hallazgo principal con contexto (período, empresa, tendencia).
- Si NO hay datos: explica de forma empática por qué y sugiere una alternativa específica. NO digas "No se identificaron registros". Di: "No encontré [X] para [criterio]. Esto puede deberse a [razón]. Prueba con [sugerencia]."
- Si es conversacional/meta: responde directamente como un asistente inteligente.

🥇 REGLA 7 — IDIOMA Y FORMATO ESPAÑOL:
Todo en español. IDs y RUC/Cédulas como texto puro (sin puntos de miles). GROUP BY para evitar duplicados en rankings.

🥇 REGLA 8 — ALCANCE ACOTADO (NO ERES UN CHATBOT GENERAL):
Eres un asistente de Inteligencia de Negocios, NO un buscador ni un asistente de propósito general. Tu único dominio son los datos de la empresa activa.

{alcance}

- SÍ respondes: cualquier pregunta sobre los módulos listados arriba (cifras, rankings, tendencias, comparativas, explicaciones de negocio).
- SÍ respondes: preguntas meta sobre el propio sistema — qué empresa está activa, qué módulos hay, qué preguntó el usuario antes, cómo se calculó una cifra, qué puede preguntarte. Usa el historial y el contexto.
- NO respondes: noticias, política, geopolítica, deportes, clima, farándula, cultura general, recetas, traducciones, criptomonedas, bolsa ni ningún tema ajeno a los datos de la empresa. NO inventes, NO improvises y NO uses conocimiento externo.

🥇 REGLA 9 — NUNCA INVENTAR NI PROYECTAR DATOS SIN QUE SE PIDA:
Toda cifra que muestres debe salir de una consulta SQL real contra el ESQUEMA DE DATOS DISPONIBLE — nunca de una estimación, extrapolación o "relleno" tuyo. Si el usuario pide un dato histórico (ventas, compras, un mes, un año), el SQL debe traer EXACTAMENTE lo que existe en la base, ni un mes de más ni de menos: no completes meses faltantes con promedios ni repitas el último valor conocido. Genera una proyección, pronóstico o estimación SOLO si el usuario la pide explícitamente con palabras como "proyecta", "predice", "estima" o "pronóstico" — nunca por iniciativa propia ante una pregunta de datos históricos simples. Un CEO que descubre una cifra inventada deja de confiar en el sistema por completo: ante la duda, muestra menos datos (o explica que faltan) en vez de inventar los que faltan.

🥇 REGLA 10 — FORMATO DE RESPUESTA (SE LEE EN MARKDOWN, BREVE Y SIN JERGA TÉCNICA):
El campo explanation se renderiza como Markdown en pantalla, así que escríbelo como un mensaje bien maquetado, no como un párrafo plano:
- **Negritas** SOLO en la cifra o el hallazgo que importa. Nunca cursiva.
- Viñetas cuando enumeres más de dos cosas, una idea por viñeta.
- Emojis con criterio para abrir una sección o una viñeta clave (✅ dato confirmado, ⚠️ advertencia, 🔍 hallazgo, 📊 cifra o tendencia, 💡 recomendación, 🔒 restricción). Uno por bloque como máximo: son señales de lectura, no decoración — nunca un emoji en cada frase ni al final de cada línea.
- Nada de muletillas de relleno ni disculpas largas: al grano, cordial y profesional.
- NUNCA escribas marcadores de posición como $[TotalVentas], [VALOR] o {{cifra}} dentro de explanation. Si el número lo produce el SQL, describe el resultado en palabras ("el total facturado del período") y deja que la tarjeta de datos muestre la cifra; jamás dejes un hueco sin rellenar a la vista del usuario.
- PROHIBIDO nombrar vistas, tablas, columnas o cualquier término técnico de la base de datos dentro de explanation — nada de `[Ventas]`, `VIS_ALUMNO`, `cabecera_factura` ni similares, ni siquiera entre backticks. Eso es información privada del sistema (vive en la pestaña técnica, no en la respuesta). Habla siempre de "los datos de ventas", "el registro de alumnos", "la información de nómina" — en términos de NEGOCIO, nunca de esquema.
- Extensión: ni un texto plano de una sola frase vacía, ni un ensayo. Una respuesta directa trae el hallazgo en 1-3 frases o viñetas cortas; solo se extiende más si la pregunta pidió explícitamente un análisis profundo (comparativas, "por qué", recomendaciones). El objetivo es contexto preciso y conciso, no relleno.

🥇 REGLA 11 — MENSAJES LARGOS: LÉELOS COMPLETOS Y RESPÓNDELOS COMPLETOS:
Si el usuario escribe un mensaje largo, con varios párrafos o varias preguntas encadenadas, NO te quedes con la primera línea ni respondas con una plantilla genérica de capacidades. Identifica cada punto que planteó y respóndelos TODOS, en orden, uno por uno. Si el mensaje mezcla una instrucción con una consulta de datos, atiende la instrucción y además genera el SQL de la consulta. Un mensaje largo es la señal de que el usuario está siendo específico: merece más atención, no menos.

Si la pregunta sale del alcance: sql: "", viz_type: "text", y en explanation di con naturalidad (varía la frase, no repitas siempre la misma) que eso queda fuera de lo que puedes consultar, y enumera los módulos disponibles de arriba para reorientar al usuario. Sé breve, cordial y profesional; nunca cortante.

IMPORTANTE sobre los módulos: menciona SOLO los que aparecen listados arriba. Cada base tiene su propio alcance — una institución académica puede no tener compras ni nómina, y una comercial puede no tener alumnos. Nunca prometas un módulo que no esté en esa lista.

{db_insights}

{memoria_aprendida}

PREGUNTA DEL USUARIO:
{question}

RESPONDE SOLO JSON VÁLIDO:
{{
  "pensamiento_analitico": "Análisis interno breve (invisible al usuario)",
  "sql": "SELECT ... (vacío si no aplica SQL)",
  "explanation": "Respuesta principal para el usuario. Siempre útil, siempre con contexto.",
  "viz_type": "value|table|bar|line|pie|text|payslip",
  "viz_config": {{"title": "Título descriptivo con período", "x": "...", "y": "..."}}
}}
"""


SYSTEM_PROMPT_PRO = """
Eres VicMar Data AI, el Analista Ejecutivo de Inteligencia de Negocios de VicMar Data AI.
Modo EXPERTO: tus respuestas incluyen análisis de negocio, insights y recomendaciones accionables, no solo el dato.

HOY: {current_date}
MÓDULO: {module}
BD interna (solo para SQL): {context_db}
Historial: {history}

ESQUEMA DE DATOS DISPONIBLE:
{schema}

GIRO DE NEGOCIO DE LA EMPRESA ACTIVA:
{business_logic}

{vistas_reales}

REGLAS ESENCIALES:
1. Genera SQL SOLO de lectura (SELECT) contra las vistas del esquema, sin prefijos [DB].[dbo] ni tablas tb_*. Si el usuario no especifica año, filtra al más reciente: WHERE YEAR(Fecha) = (SELECT MAX(YEAR(Fecha)) FROM [vista]) — salvo que la LÓGICA DE NEGOCIO de la empresa defina otra regla (ej. vistas académicas longitudinales: estado vigente = es_ultimo_periodo = 1), que prevalece. Meses en español con CHOOSE(MONTH(Fecha),'Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'). CAST(AS DECIMAL(18,2)) para monetarios, CAST(AS BIGINT) para enteros. JOIN para mostrar nombres, no códigos.
2. NUNCA inventes ni proyectes datos: el SQL trae EXACTAMENTE lo que existe. Proyecciones/estimaciones SOLO si el usuario pide "proyecta", "predice", "estima" o "pronóstico". Ante la duda, muestra menos datos o explica que faltan.
3. {alcance}
4. viz_type: "value" (valor único), "table" (listado/ranking), "bar" o "line" (tendencia temporal), "text" (sin SQL), "payslip" (nómina individual).
5. explanation en ESPAÑOL, markdown breve y profesional. PROHIBIDO nombrar vistas/tablas/columnas (nada de [Ventas], VIS_ALUMNO, cabecera_factura) ni jerga técnica ni placeholders como [VALOR]. Emojis con criterio (✅ dato, ⚠️ advertencia, 🔍 hallazgo, 📊 cifra, 💡 recomendación), uno por bloque. Todo en español.

DIFERENCIA CLAVE DEL MODO EXPERTO — la explanation DEBE incluir:
- El hallazgo principal con cifra y contexto (período, empresa, tendencia).
- Un insight de negocio: qué significa ese dato para la empresa activa.
- Una recomendación accionable (💡) cuando aplique.
- En comparativas: qué cambió entre períodos y por qué importa.
- Extensión: 2-4 frases o 3-5 viñetas. Nunca un ensayo ni una frase suelta.

{memoria_aprendida}

PREGUNTA DEL USUARIO:
{question}

RESPONDE SOLO JSON VÁLIDO:
{{
  "pensamiento_analitico": "Análisis interno breve (invisible al usuario)",
  "sql": "SELECT ... (vacío si no aplica SQL)",
  "explanation": "Respuesta EXPERTO: hallazgo + insight + recomendación accionable",
  "viz_type": "value|table|bar|line|pie|text|payslip",
  "viz_config": {{"title": "Título descriptivo con período", "x": "...", "y": "..."}}
}}
"""


CORRECTION_PROMPT = """
Eres el sistema de auto-correccion SQL de VicMar Data AI.
Debes corregir una consulta fallida conservando la intencion de negocio.

SQL fallido:
{failed_sql}

Error recibido:
{error_msg}

Schema:
{schema}

Relaciones semanticas:
{semantic_relations}

Reglas:
- Solo lectura (SELECT / WITH + SELECT).
- No inventar tablas o columnas fuera del schema.
- SQL UNIVERSAL: Evita funciones como `TRY_CONVERT`. Usa `CAST(col AS date)` o similar.
- Responde SOLO en JSON valido:
{{
  "pensamiento_analitico": "Análisis interno de la corrección",
  "sql": "SELECT corregido...",
  "explanation": "Resumen ejecutivo de la corrección aplicada"
}}
"""

EXPLANATION_PROMPT = """
Eres Asistente Inteligente de VicMar Data AI en modo resumen ejecutivo.

Pregunta:
{question}

SQL usado:
{sql}

Resultados (preview):
{results}

Modulo:
{module}

FORMATO (igual que el resto de VicMar Data AI): Markdown limpio, **negritas** en la
cifra o el hallazgo que importa (nunca cursiva), viñetas si enumeras varias
cosas, un emoji de apertura por bloque como máximo (📊 cifra, 🔍 hallazgo, 💡
recomendación) — nunca decorando cada frase. Español, directo, sin relleno.
Breve: 1-3 frases o viñetas cortas, salvo que la pregunta pida explícitamente
un análisis profundo. El SQL de arriba es solo tu contexto para razonar —
PROHIBIDO mencionar nombres de vistas, tablas o columnas en la explicación
(nada de `[Ventas]`, `VIS_ALUMNO`, etc.): habla en términos de negocio.

Genera SOLO JSON valido:
{{
  "explanation": "Síntesis ejecutiva precisa para gerencia. Si no hay datos, explica que no existen registros en el sistema para ese periodo.",
  "visualization_type": "text|value|table|bar|line|pie|area|radar",
  "agent_log": ["Ejecución de consulta", "Validación de integridad"]
}}
"""


# ─── Carga de configuracion segura ─────────────────────────────────────────
# Siempre intentamos config.py primero. Si falla (ej: tests aislados),
# leemos las variables directamente del entorno.
try:
    from config import (
        DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_MODEL_PRO, DEEPSEEK_MODEL_VISION,
        LLM_MAX_TOKENS, LLM_MAX_TOKENS_PRO, LLM_TEMPERATURE,
        GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL,
        GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL,
        NVIDIA_API_KEY, NVIDIA_MODEL, NVIDIA_BASE_URL, NVIDIA_MODELOS_DISPONIBLES,
    )
except ImportError:
    load_dotenv()
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-pro-0813")
    NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODELOS_DISPONIBLES = {
        "nvidia_deepseek_pro": "deepseek-ai/deepseek-v4-pro-0813",
        "nvidia_deepseek_flash": "deepseek-ai/deepseek-v4-flash-0731",
        "nvidia_kimi": "moonshotai/kimi-k3",
        "nvidia_nemotron": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia_muse": "meta/muse-glimmer-30b",
    }
    DEEPSEEK_BASE_URL  = os.getenv("DEEPSEEK_BASE_URL",  "https://api.deepseek.com/v1")
    # OJO: este camino de respaldo se salta la normalización de config.py, así
    # que el valor por defecto tiene que ser un modelo VIGENTE. Estaba en
    # "deepseek-chat", descontinuado el 24/07/2026: si config.py no se podía
    # importar (p. ej. por el orden de PYTHONPATH en el contenedor), el motor
    # arrancaba apuntando a un modelo inexistente y TODA consulta a la IA
    # fallaba, aunque el .env o env.yaml tuvieran el modelo correcto.
    _descontinuados = {"deepseek-chat": "deepseek-v4-flash",
                       "deepseek-reasoner": "deepseek-v4-pro"}

    def _norm_fallback(env_var: str, default: str) -> str:
        val = os.getenv(env_var, default).strip().lower()
        return _descontinuados.get(val, val)

    DEEPSEEK_MODEL         = _norm_fallback("DEEPSEEK_MODEL", "deepseek-v4-flash")
    DEEPSEEK_MODEL_PRO     = _norm_fallback("DEEPSEEK_MODEL_PRO", "deepseek-v4-pro")
    DEEPSEEK_MODEL_VISION  = _norm_fallback("DEEPSEEK_MODEL_VISION", "deepseek-v4-flash-vision-exp")
    LLM_MAX_TOKENS     = int(os.getenv("LLM_MAX_TOKENS", "600"))
    LLM_MAX_TOKENS_PRO = int(os.getenv("LLM_MAX_TOKENS_PRO", "3200"))
    LLM_TEMPERATURE    = float(os.getenv("LLM_TEMPERATURE", "0.1"))


# ─── Motor Principal ────────────────────────────────────────────────────────
def _salida_degenerada(texto: str) -> bool:
    """Vacía o sin contenido real (ej. "!!!!!!!!!!!!", solo signos): el
    proveedor respondió 200 pero no generó una respuesta utilizable."""
    t = (texto or "").strip()
    if not t:
        return True
    alfanumericos = sum(ch.isalnum() for ch in t)
    return alfanumericos < max(5, len(t) * 0.2)


class NL2SQLEngine:
    """Motor de conversión de lenguaje natural a SQL con una cascada de proveedores de LLM
    (Gemini → Groq → NVIDIA NIM → DeepSeek)."""

    def __init__(self, api_key: str, database_name: str = "CHAT", business_name: str = None) -> None:
        from langchain_openai import ChatOpenAI

        # ChatOpenAI revienta en la CONSTRUCCIÓN (no al invocar) si recibe una
        # api_key vacía ("Missing credentials"). Con la cascada de respaldo,
        # DeepSeek puede legítimamente no tener llave (este proyecto la dejó
        # vacía a propósito) y aun así queremos que el motor arranque y caiga
        # a Gemini/Groq/NVIDIA. Un placeholder no vacío deja que construya
        # bien; la llamada real fallará por auth (401) recién al invocar,
        # que es justo lo que dispara `.with_fallbacks()`.
        api_key = api_key or "sin-clave-configurada"

        # FASE 4 — punto 6: tres modelos DeepSeek, cada uno para un tipo de
        # pregunta distinto, en vez de un único cliente fijo para todo.
        # Reemplaza al Motor 2 (Qwen/Together AI): ese cliente se instanciaba
        # pero _select_llm() para la generación principal SIEMPRE devolvía
        # DeepSeek — el único uso real que tenía Qwen era la autocorrección de
        # SQL fallido (generate_correction), y ese caso es exactamente
        # "razonamiento complejo", así que ahora lo cubre el modelo Pro de
        # DeepSeek en vez de mantener una cuenta/API key aparte solo para eso.

        # Defecto detectado en pruebas (29/08/2026): "total de ventas por
        # meses 2026" (sin "del") se quedó pensando sin responder NUNCA. Causa
        # raíz: ninguno de los tres clientes tenía `timeout` propio, así que
        # heredaban el default del SDK de OpenAI — 600 segundos, más hasta 2
        # reintentos automáticos (o sea, hasta 30 minutos en el peor caso) — en
        # vez de fallar rápido y dejar que el manejo de errores que YA existe
        # (más abajo, `except Exception as exc: return None, f"Error del motor
        # DeepSeek: {exc}"`) le devuelva al usuario un mensaje claro. Con esto
        # el peor caso pasa a ser ~90s (45s × 2 intentos) en vez de 30 minutos.
        # Mismo orden de magnitud que el timeout de 40s ya usado para SQL en
        # db_connector.execute_query — nunca debe quedar "pensando" en silencio.
        # ── Cascada de respaldo gratuita ─────────────────────────────────────
        # Orden: Gemini (más generoso/capaz) -> Groq (más rápido) -> NVIDIA NIM
        # (catálogo amplio, estable). DeepSeek sigue siendo el modelo PRIMARIO
        # de cada rol (flash/pro); si no tiene llave o falla (429/503/timeout),
        # LangChain's `.with_fallbacks()` prueba el siguiente automáticamente,
        # sin que el resto del pipeline (parseo, sanitizador) note diferencia.
        # Solo se agregan al respaldo los proveedores con llave configurada.
        # Bug real (25/09/2026): kimi-k3 (NVIDIA NIM) en modo razonamiento a
        # veces deja TODA la respuesta dentro de `reasoning_content`, campo que
        # LangChain descarta: el contenido llegaba vacío ("No se pudo
        # estructurar la salida del modelo") aunque el modelo sí respondió.
        # Verificado en vivo: con thinking=False la respuesta llega en
        # `content`. NIM ignora esta opción en los modelos que no la soportan.
        _SIN_RAZONAMIENTO_NVIDIA = {"chat_template_kwargs": {"thinking": False}}

        def _proveedores_gratuitos(temperature: float, max_tokens: int, timeout: int) -> dict:
            """Dict (no lista) para poder pedir UNO puntual por nombre — ver
            `_motor_individual` — además de usarlos todos en orden para la
            cascada automática de `_construir_cascada`.

            Bug real (25/09/2026, detectado por eval/evaluar_nl2sql.py): los
            modelos de la cascada (kimi-k3, gpt-oss) son de RAZONAMIENTO —
            gastan tokens pensando antes de escribir la respuesta. Con el tope
            de 600 tokens del rol Flash (pensado para DeepSeek, que no razona)
            el razonamiento agotaba el presupuesto y la respuesta llegaba
            VACÍA ("No se pudo estructurar la salida del modelo"). Se garantiza
            un mínimo propio para la cascada."""
            max_tokens = max(max_tokens, int(os.getenv("LLM_MAX_TOKENS_CASCADA", "3000")))
            disponibles = {}
            if GEMINI_API_KEY:
                disponibles["gemini"] = ChatOpenAI(
                    model=GEMINI_MODEL, api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL,
                    temperature=temperature, max_tokens=max_tokens, timeout=timeout, max_retries=0,
                )
            if GROQ_API_KEY:
                disponibles["groq"] = ChatOpenAI(
                    model=GROQ_MODEL, api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL,
                    temperature=temperature, max_tokens=max_tokens, timeout=timeout, max_retries=0,
                )
            if NVIDIA_API_KEY:
                disponibles["nvidia"] = ChatOpenAI(
                    model=NVIDIA_MODEL, api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL,
                    temperature=temperature, max_tokens=max_tokens, timeout=timeout, max_retries=0,
                    extra_body=_SIN_RAZONAMIENTO_NVIDIA,
                )
            return disponibles

        def _cascada_respaldo(temperature: float, max_tokens: int, timeout: int):
            return list(_proveedores_gratuitos(temperature, max_tokens, timeout).values())

        def _motor_individual(proveedor: str, temperature: float, max_tokens: int, timeout: int):
            """
            Selector manual (09/09/2026): probar UN
            proveedor/modelo gratuito puntual por su nombre — incluye los 5
            modelos de NVIDIA NIM por separado (mismo catálogo del selector
            del chat: nvidia_deepseek_pro, nvidia_deepseek_flash, nvidia_kimi,
            nvidia_nemotron, nvidia_muse — ver config.py::NVIDIA_MODELOS_DISPONIBLES),
            no solo un "nvidia" genérico. Igual que en la cascada automática,
            si ESE proveedor falla, cae al resto de los gratuitos (Gemini,
            Groq, NVIDIA genérico) como red de seguridad — elegir uno para
            probarlo no debe dejar al usuario sin respuesta.
            """
            respaldo = _proveedores_gratuitos(temperature, max_tokens, timeout)

            if proveedor in NVIDIA_MODELOS_DISPONIBLES:
                if not NVIDIA_API_KEY:
                    return None
                principal = ChatOpenAI(
                    model=NVIDIA_MODELOS_DISPONIBLES[proveedor], api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL,
                    temperature=temperature, max_tokens=max_tokens, timeout=timeout, max_retries=0,
                    extra_body=_SIN_RAZONAMIENTO_NVIDIA,
                )
                # El respaldo NVIDIA genérico de la cascada apunta al mismo
                # modelo si el usuario eligió justo "nvidia_deepseek_pro"
                # (es el que usa NVIDIA_MODEL por defecto) — no tiene sentido
                # reintentar el mismo modelo dos veces.
                if NVIDIA_MODELOS_DISPONIBLES[proveedor] == NVIDIA_MODEL:
                    respaldo.pop("nvidia", None)
            else:
                principal = respaldo.pop(proveedor, None)
                if principal is None:
                    return None

            resto = list(respaldo.values())
            return principal.with_fallbacks(resto) if resto else principal

        def _construir_cascada(modelo_deepseek: str, temperature: float, max_tokens: int, timeout: int, max_retries: int):
            """
            Auditoría 09/09/2026 (#7): antes SIEMPRE se probaba DeepSeek primero
            aunque DEEPSEEK_API_KEY estuviera vacío (con un placeholder para que
            ChatOpenAI no reventara en la construcción) — cada pregunta pagaba
            una llamada HTTP condenada a fallar (401) antes de caer recién ahí a
            Gemini/Groq/NVIDIA. Si no hay llave real de DeepSeek, se arma la
            cascada saltándoselo del todo: el primer proveedor CON llave pasa a
            ser el principal.
            """
            proveedores = []
            if DEEPSEEK_API_KEY:
                proveedores.append(ChatOpenAI(
                    model=modelo_deepseek, api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL,
                    temperature=temperature, max_tokens=max_tokens, streaming=True,
                    timeout=timeout, max_retries=max_retries,
                ))
            proveedores.extend(_cascada_respaldo(temperature, max_tokens, timeout))

            if not proveedores:
                # Nadie configurado (ni DeepSeek ni la cascada de respaldo):
                # mismo comportamiento de siempre — un cliente "vacío" que
                # falla al invocarse y deja al sistema en modo seguro.
                return ChatOpenAI(
                    model=modelo_deepseek, api_key=api_key, base_url=DEEPSEEK_BASE_URL,
                    temperature=temperature, max_tokens=max_tokens, streaming=True,
                    timeout=timeout, max_retries=max_retries,
                )
            principal, *respaldos = proveedores
            return principal.with_fallbacks(respaldos) if respaldos else principal

        _LLM_TIMEOUT_SEG = 45
        # Pro razona ANTES de responder (emite reasoning_content): una pregunta
        # comparativa compleja con el prompt completo puede tardar más de 45s.
        # Con un timeout propio más alto, el motor Experto completa su
        # razonamiento en vez de reintentar/fallar por premura.
        _LLM_TIMEOUT_PRO_SEG = 150
        _LLM_MAX_REINTENTOS = 1

        # "Instant" — conversación cotidiana, consultas simples de una métrica.
        self.llm_flash = _construir_cascada(DEEPSEEK_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, _LLM_TIMEOUT_SEG, _LLM_MAX_REINTENTOS)
        self.llm_deepseek = self.llm_flash  # alias retrocompatible: código existente referencia este nombre

        # Selector manual por proveedor puntual (09/09/2026): mismos parámetros
        # de "Instant"/Flash. `None` si ese proveedor no tiene llave — se
        # valida en `_select_llm` antes de usarlo.
        self.llm_gemini = _motor_individual("gemini", LLM_TEMPERATURE, LLM_MAX_TOKENS, _LLM_TIMEOUT_SEG)
        self.llm_groq = _motor_individual("groq", LLM_TEMPERATURE, LLM_MAX_TOKENS, _LLM_TIMEOUT_SEG)
        # Los 5 modelos de NVIDIA NIM seleccionables por separado (ver
        # config.py::NVIDIA_MODELOS_DISPONIBLES) — cada atributo queda como
        # self.llm_nvidia_deepseek_pro, self.llm_nvidia_kimi, etc.
        for _motor_id in NVIDIA_MODELOS_DISPONIBLES:
            setattr(self, f"llm_{_motor_id}", _motor_individual(_motor_id, LLM_TEMPERATURE, LLM_MAX_TOKENS, _LLM_TIMEOUT_SEG))

        # "Experto" — forecast, comparativas multi-módulo, autocorrección de
        # SQL, preguntas de finanzas/contabilidad que requieren más razonamiento.
        # max_tokens propio (LLM_MAX_TOKENS_PRO > LLM_MAX_TOKENS): este modelo
        # razona ANTES de responder (emite reasoning_content que LangChain
        # ignora y que consume el mismo tope de tokens). Con el tope de Flash,
        # el razonamiento se comía todo el presupuesto y el JSON llegaba
        # vacío/cortado — "Pro no se activa del todo" (bug real 30/08/2026).
        self.llm_pro = _construir_cascada(DEEPSEEK_MODEL_PRO, LLM_TEMPERATURE, LLM_MAX_TOKENS_PRO, _LLM_TIMEOUT_PRO_SEG, _LLM_MAX_REINTENTOS)

        # "Vision" — preguntas que adjuntan imágenes. Se instancia siempre
        # (no cuesta nada hasta que se invoca) para que el endpoint de
        # adjuntar imagen lo tenga disponible sin reconstruir el motor.
        # Timeout más alto: procesar imágenes tarda más que texto plano.
        self.llm_vision = ChatOpenAI(
            model=DEEPSEEK_MODEL_VISION,
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            streaming=True,
            timeout=_LLM_TIMEOUT_SEG * 2,
            max_retries=_LLM_MAX_REINTENTOS,
        )

        # "Libre" — SOLO para el modo desarrollador (ver core/modo_desarrollador.py).
        # Es el mismo proveedor, pero con dos diferencias que importan:
        # max_tokens muy por encima de LLM_MAX_TOKENS (600 es correcto para una
        # explicación de negocio de tres líneas y ridículo para explicar una
        # arquitectura, que es justo lo que se le va a pedir aquí) y temperatura
        # más alta, porque no está produciendo SQL sino conversación.
        self.llm_libre = ChatOpenAI(
            model=DEEPSEEK_MODEL_PRO,
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.6,
            max_tokens=3000,
            streaming=True,
            timeout=_LLM_TIMEOUT_PRO_SEG,
            max_retries=_LLM_MAX_REINTENTOS,
        )

        self.database_name = database_name
        self.business_name = business_name or database_name
        self.schema_text = ""
        self.schema_tables = {}
        self.semantic_relations = ""
        self.db_insights = self._load_db_insights()

    def _load_db_insights(self) -> str:
        """Carga el conocimiento previo sobre tablas con datos y sin datos."""
        try:
            path = os.path.join(os.path.dirname(__file__), "..", "data", "db_insights.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                lines = ["\nINSIGHTS DE DATOS REALES (Discovery Mode):"]
                for db, info in data.items():
                    ready = info.get("ready_tables", [])
                    empty = info.get("empty_tables", [])
                    mappings = info.get("custom_mappings", {})
                    
                    if ready or empty or mappings:
                        lines.append(f"Base de Datos: {db}")
                        if mappings:
                            lines.append(f"  - Mapeos Críticos: {json.dumps(mappings)}")
                        if ready:
                            lines.append(f"  - Tablas LISTAS (con datos): {', '.join(ready[:10])}")
                        if empty:
                            lines.append(f"  - Tablas VACIAS (ignorar): {', '.join(empty[:5])}...")
                return "\n".join(lines)
        except Exception:
            pass
        return ""

    # Señales de pregunta "compleja": forecast/predicción, comparativas
    # multi-período, o finanzas/contabilidad avanzada. Deliberadamente en
    # positivo (whitelist) y no al revés: es más seguro que una pregunta
    # compleja caiga por defecto en "Instant" (respuesta más simple pero
    # correcta) que forzar "Experto" de más y pagar/tardar sin necesidad.
    _PATRONES_MODELO_EXPERTO = (
        r"\bpredi[cg]", r"\bproyecta", r"\bproyeccion", r"\bpron[oó]stico",
        r"\bforecast\b", r"\bestima(?:cion)?\b.*\b(ventas|ingresos|demanda)\b",
        r"\btendencia futura\b", r"\bque pasara\b", r"\bcuanto se vendera\b",
        r"\bcompara\b.*\by\b", r"\bcomparaci[oó]n\b", r"\bversus\b", r"\bvs\.?\b",
        # Bug real (29/08/2026): "año contra año"/"año vs año" exigían las dos
        # palabras pegadas, pero una frase natural dice "año CONTRA EL año" o
        # "este año VS el año pasado" — con algo en medio. Se permite hasta 20
        # caracteres entre "año" y "contra"/"vs", y de ahí hasta el segundo "año".
        r"\btrimestre a trimestre\b",
        r"\ba[ñn]o\b.{0,20}\bcontra\b.{0,20}\ba[ñn]o\b", r"\ba[ñn]o\b.{0,20}\bvs\.?\b.{0,20}\ba[ñn]o\b",
        r"\bmargen\b.*\bentre\b", r"\bbalance general\b", r"\bflujo de caja\b",
        r"\brentabilidad\b", r"\broi\b", r"\bpunto de equilibrio\b",
        r"\bamortizaci[oó]n\b", r"\bdepreciaci[oó]n\b", r"\bestado de resultados\b",
        # "por que bajaron/subieron/cayeron/aumentaron/disminuyeron las ventas":
        # raíces sin fijar el final de la palabra para cubrir conjugaciones
        # (bajo/bajó/bajaron, subio/subió/subieron, etc.)
        r"\bpor qu[eé]\b.*\b(baj|subi|cay|ca[yi]|aument|disminuy)",
    )
    _RE_MODELO_EXPERTO = re.compile("|".join(_PATRONES_MODELO_EXPERTO))

    def _requiere_modelo_experto(self, question: str) -> bool:
        """True si la pregunta pide razonamiento más allá de una consulta
        directa: predicción, comparativas, o finanzas/contabilidad avanzada."""
        texto = re.sub(r"\s+", " ", (question or "").lower()).strip()
        return bool(self._RE_MODELO_EXPERTO.search(texto))

    def _select_llm(self, module: str = "GLOBAL", question: str = "", modelo_forzado: str | None = None) -> Any:
        """
        Selector de motor: el usuario elige el motor de forma explícita; no hay
        enrutamiento automático por heurística.

          · Sin `modelo_forzado` (caso normal) → Instant/Flash: rápido y sin
            costo externo; suficiente para consultas directas.
          · `modelo_forzado="pro"` → Experto, solo si el usuario lo elige en el
            selector para esa consulta.
          · Un id de proveedor puntual (Gemini, Groq, NVIDIA…) → ese proveedor,
            para comparar las API por separado.
          · `modelo_forzado="vision"` → reservado para el endpoint de imagen.

        La seguridad no depende del modelo que escribió el SQL: el sanitizador
        que bloquea todo lo que no sea SELECT se aplica siempre después.
        `_requiere_modelo_experto()` se conserva como utilidad, pero no decide
        el enrutamiento.
        """
        motor = (modelo_forzado or "").strip().lower()
        if motor == "pro":
            return self.llm_pro
        # Selector manual por proveedor puntual (09/09/2026): para PROBAR cada
        # API gratuita por separado. Si ese proveedor no tiene llave
        # configurada (self.llm_x es None), cae a Flash (cascada completa) en
        # vez de reventar — un motor de prueba sin llave nunca debe dejar al
        # usuario sin respuesta.
        if motor == "gemini" or motor == "groq" or motor in NVIDIA_MODELOS_DISPONIBLES:
            especifico = getattr(self, f"llm_{motor}", None)
            if especifico is not None:
                return especifico
        return self.llm_flash

    def get_table_candidates(self, question: str, limit: int = 15) -> list[str]:
        """
        Identifica los nombres de las tablas candidatas usando Sinonimos de Negocio.
        Esencial para la Poda Semantica y el JIT.
        """
        q_norm = re.sub(r'[^a-z0-9]', ' ', question.lower()).split()
        if not q_norm or not self.schema_tables:
            return list(self.schema_tables.keys())[:limit]

        # Mapa de Sinonimos de Negocio (Universal) con Inyección de Tablas Core Sin Guiones Bajos (por el match estricto)
        synonyms = {
            "estudiante": ["alumno", "educacion", "aula", "matricula", "inscripcion", "academico", "VIS_ALUMNO"],
            "compras": ["gasto", "inversion", "proveedor", "compra", "orden", "ingreso", "cabecera_compra"],
            "ventas": ["factura", "ingreso", "cliente", "pedido", "pago", "vendedor", "cabecera_factura"],
            "nomina": ["rrhh", "personal", "trabajador", "sueldo", "pago", "empleado", "rol", "rol_pago", "VIS_HISNOVTRABAJADOR"],
            "personal": ["empleado", "rrhh", "trabajador", "ficha_trabajador"],
            "inventario": ["stock", "kardex", "producto", "bodega", "medida", "item"]
        }
        
        # Expandir q_norm con sinonimos
        expanded_q = list(q_norm)
        for word in q_norm:
            for master, syn_list in synonyms.items():
                if word == master or word in syn_list:
                    expanded_q.extend(syn_list)
                    expanded_q.append(master)

        scored = []
        for name, info in self.schema_tables.items():
            s = 0
            n = name.lower().replace("_", " ")
            
            # 1. Match de Palabras (Score Base)
            for w in set(expanded_q):
                if len(w) > 2 and w in n:
                    s += 10
            
            # 2. PRIORIDAD MAESTRA: Si es una Vista de Negocio (VIS_ o V_), gran bonus
            # `db_connector` etiqueta las vistas como "VISTA" (no "VIEW"), asi
            # que se aceptan ambas: si no, vistas de CHAT sin prefijo
            # (cabecera_factura, rol_pago, ficha_trabajador) perdian este bonus.
            if name.startswith(("VIS_", "V_")) or str(info.get("type", "")).upper() in ("VIEW", "VISTA"):
                s += 20
                
            # 3. Bonus por tablas conocidas que tienen datos reales (Discovery)
            if s > 0 and info.get("row_count", 0) > 0:
                s += 5
                
            if s > 0: scored.append((s, name))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t[1] for t in scored[:limit]]

    def _prune_schema(self, question: str, limit: int = 20) -> str:
        """
        TECNICA AVANZADA: Poda Semantica Universal con Inyeccion de sinonimos.
        Filtra cientos de tablas para enviar solo las mas relevantes al LLM.
        """
        relevant_names = self.get_table_candidates(question, limit=limit)
        
        if not relevant_names:
             relevant_names = list(self.schema_tables.keys())[:15]

        # Reconstruir REPRESENTACION TEXTUAL REDUCIDA
        pruned_lines = [f"=== ESQUEMA SEMANTICO SELECCIONADO (Identificadas {len(relevant_names)} entidades relevantes) ===\n"]
        for name in relevant_names:
            info = self.schema_tables.get(name)
            if not info: continue
            
            obj_type = info.get("type", "TABLA")
            pruned_lines.append(f"{obj_type}: [{name}]")
            
            row_count = info.get("row_count", 0)
            if row_count > 0:
                pruned_lines.append(f"  [STAT: {row_count} filas con datos reales]")
            
            cols = info.get("columns", [])
            if cols:
                # Mostramos solo las primeras 30 columnas
                for col in cols[:30]:
                    name_ptr = col.get('name') if isinstance(col, dict) else col
                    type_ptr = col.get('type', 'varchar') if isinstance(col, dict) else ""
                    type_str = f" ({type_ptr})" if type_ptr else ""
                    pruned_lines.append(f"  - {name_ptr}{type_str}")
                if len(cols) > 30:
                    pruned_lines.append(f"  ... (+ {len(cols)-30} columnas mas)")
            else:
                pruned_lines.append("COLUMNAS: (Sincronización JIT en progreso...)")
            pruned_lines.append("")
        
        return "\n".join(pruned_lines)

    def _get_static_response(self) -> str:
        """Genera saludo DINÁMICO basado ÚNICAMENTE en lo que existe en la BD conectada."""
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Buenos días"
        elif hour < 19:
            greeting = "Buenas tardes"
        else:
            greeting = "Buenas noches"
        
        # NO inventar dominios. Solo mencionar la BD conectada.
        db_label = f"**{self.database_name.upper()}**" if self.database_name else "la base de datos"
        
        # Si hay schema, mencionar SOLO las tablas reales detectadas (max 3 ejemplos)
        if self.schema_text and hasattr(self, 'schema_tables') and self.schema_tables:
            table_samples = list(self.schema_tables.keys())[:3]
            if table_samples:
                examples_hint = f"Tengo acceso a {len(self.schema_tables)} tablas incluyendo {', '.join(table_samples)}. "
            else:
                examples_hint = ""
        else:
            examples_hint = ""
        
        return (
            f"{greeting}. Soy Aura, tu asistente inteligente conectado a {db_label}. "
            f"{examples_hint}"
            "¿Qué información te gustaría consultar hoy?"
        )

    def _extract_json(self, raw_text: str) -> dict | None:
        """
        Extrae el primer objeto JSON válido de la respuesta cruda del modelo.

        Defecto corregido (30/08/2026): la versión anterior tomaba la primera
        "{" y la ÚLTIMA "}" del texto entero. Algunos modelos devuelven solo el
        JSON, pero otros son más "conversacionales": pueden envolverlo con
        una frase antes/después, o el propio SQL/explanation puede contener
        llaves (una CTE, un ejemplo). Con la última "}" del texto entero, el
        recorte agarraba de más y `json.loads` fallaba con el JSON entero
        bien formado adentro — el usuario veía "Análisis completado" (JSON
        parseado pero sin las claves esperadas) o "No se pudo estructurar la
        salida del modelo" (ni eso).

        Ahora se cuenta profundidad de llaves desde el PRIMER "{" hasta que
        vuelve a cero: el primer objeto JSON completo y válido, sin importar
        qué haya después en el texto.
        """
        cleaned = re.sub(r"```(?:json|sql)?\s*", "", raw_text, flags=re.IGNORECASE)
        cleaned = re.sub(r"```", "", cleaned).strip()
        start_idx = cleaned.find("{")
        if start_idx == -1:
            return None

        profundidad = 0
        dentro_de_cadena = False
        escape = False
        for i in range(start_idx, len(cleaned)):
            ch = cleaned[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                dentro_de_cadena = not dentro_de_cadena
                continue
            if dentro_de_cadena:
                continue
            if ch == "{":
                profundidad += 1
            elif ch == "}":
                profundidad -= 1
                if profundidad == 0:
                    payload = cleaned[start_idx : i + 1]
                    try:
                        return json.loads(payload)
                    except Exception:
                        break

        # Respaldo: el intento anterior (primera "{" / última "}") por si el
        # texto trae un JSON genuinamente mal balanceado que aun así el
        # parser tolera (ej. una llave suelta dentro de una cadena mal
        # escapada). Nunca deja de intentar antes de rendirse.
        end_idx = cleaned.rfind("}")
        if end_idx == -1:
            return None
        try:
            return json.loads(cleaned[start_idx : end_idx + 1])
        except Exception:
            return None

    def set_schema(self, schema_text: str, semantic_relations: str | None = None, tables_dict: dict = None) -> None:
        """Configura el schema y EXTRAE las tablas reales y virtuales disponibles."""
        self.schema_text = schema_text or ""
        if semantic_relations is not None:
            self.semantic_relations = semantic_relations or "Sin relaciones semanticas adicionales."
        
        # 1. Cargar tablas base
        self.schema_tables = tables_dict if tables_dict is not None else {}
        
        # 2. PARSEO DE EMERGENCIA / VIRTUAL: Extraer vistas del schema_text
        if self.schema_text:
            lines = self.schema_text.split("\n")
            current_table = None
            for line in lines:
                line = line.strip()
                # Soporte para formato estandar: TABLE: [Nombre] o VISTA: [Nombre]
                if line.startswith(("TABLE:", "TABLA:", "VISTA:")):
                    current_table = line.split(":")[1].strip().replace("[", "").replace("]", "")
                    if current_table not in self.schema_tables:
                        self.schema_tables[current_table] = {"columns": []}
                # Soporte para ADN VIRTUAL: CREATE VIEW [Nombre] (Col1, Col2...)
                elif line.startswith("CREATE VIEW "):
                    match = re.search(r"CREATE VIEW \[?(\w+)\]?\s*\((.*?)\)", line)
                    if match:
                        current_table = match.group(1)
                        cols = [c.strip().replace("[", "").replace("]", "") for c in match.group(2).split(",")]
                        self.schema_tables[current_table] = {"columns": [{"name": c} for c in cols], "type": "VIEW"}
                # Soporte para listado de columnas bajo TABLE:
                elif line.startswith("- ") and current_table:
                    col_info = line[2:].strip()
                    # Si ya existe la tabla pero sin columnas (o si es nueva)
                    if current_table in self.schema_tables:
                        if not self.schema_tables[current_table].get("columns"):
                            self.schema_tables[current_table]["columns"] = []
                        
                        col_name = ""
                        if ":" in col_info: col_name = col_info.split(":")[0].strip()
                        elif "(" in col_info: col_name = col_info.split("(")[0].strip()
                        else: col_name = col_info
                        
                        if col_name and not any(c.get("name") == col_name for c in self.schema_tables[current_table]["columns"]):
                            self.schema_tables[current_table]["columns"].append({"name": col_name})


        # Si el text schema venía vacío (ej: fase 0 rápida lograda solo con diccionario), 
        # auto-generamos la representación textual para el LLM.
        if not self.schema_text and self.schema_tables:
            lines = ["=== ESQUEMA DE DATOS (AUTO-GENERADO) ===\n"]
            for table, info in self.schema_tables.items():
                obj_type = info.get("type", "TABLA")
                lines.append(f"{obj_type}: [{table}]")
                row_count = info.get("row_count", 0)
                if row_count > 0:
                    lines.append(f"  [STAT: {row_count} filas de datos pre-calculadas]")
                
                cols = info.get("columns", [])
                if cols:
                    lines.append("COLUMNAS:")
                    for col in cols:
                        if isinstance(col, dict):
                            col_name = col.get("name", "")
                            col_type = col.get("type", "varchar")
                            nullable = "" if col.get("nullable", True) else " NOT NULL"
                            lines.append(f"  - {col_name} ({col_type}){nullable}")
                        else:
                            lines.append(f"  - {col}")
                else:
                    lines.append("COLUMNAS: (Sincronizando en background...)")
                lines.append("")
            self.schema_text = "\n".join(lines)

        print(f"[NL2SQL] Schema cargado: {len(self.schema_tables)} tablas detectadas")

    def generate_sql(
        self,
        question: str,
        module: str = "GLOBAL",
        context_db: str = "CHAT",
        history: str = "",
        company_code: str = "",
        vistas_reales: str = "",
        modelo_forzado: str | None = None,
    ) -> tuple[Any, str | None]:
        prompt_input = (question or "").strip()
        
        # DETECCION MEJORADA DE SALUDOS: Responder naturalmente sin requerir schema
        from core.deepseek_client import _is_greeting
        if _is_greeting(prompt_input):
            hour = datetime.now().hour
            if hour < 12:
                greeting = "Buenos días"
            elif hour < 19:
                greeting = "Buenas tardes"
            else:
                greeting = "Buenas noches"
            
            display_name = self.business_name.upper() if self.business_name else self.database_name.upper()
            db_info = f" a **{display_name}**" if display_name and display_name != "CHAT" else ""
            return {
                "pensamiento_analitico": "Saludo natural detectado - respondiendo de forma cordial",
                "sql": "",
                "explanation": f"{greeting}. Soy VicMar Data AI. Estoy conectada a **{display_name}** y lista para analizar tus datos. ¿En qué puedo ayudarte hoy?",
                "viz_type": "text",
                "viz_config": {},
                "business_analysis": "",
                "sql_explanation": "",
                "agent_log": ["Greeting natural"],
            }, None
        
        # GUARDARRAIL DE ALCANCE (primera linea, deterministica).
        # Se evalua ANTES de tocar el esquema y ANTES de gastar un token: si la
        # pregunta es inequivocamente ajena al negocio (noticias, geopolitica,
        # deportes...), se responde con la guia de modulos reales y se corta.
        # Antes de esto, la REGLA 8 decia "puedes responder CUALQUIER pregunta"
        # y el motor inyectaba titulares de Google News: preguntar por la guerra
        # de Ucrania devolvia un boletin desde una herramienta de BI conectada a
        # la base de un colegio. El filtro es conservador a proposito (ver
        # core/alcance.py): ante la duda deja pasar y decide la IA.
        from core.alcance import (
            bloque_alcance_para_prompt,
            es_fuera_de_alcance,
            respuesta_fuera_de_alcance,
        )
        from core.memoria_empresa import bloque_para_prompt as bloque_memoria_para_prompt

        # La memoria SIEMPRE se indexa por codigo de empresa, nunca por
        # `context_db`: en esta arquitectura `context_db` llega como "CHAT"
        # para TODAS las empresas (las consultas van a las vistas de CHAT), asi
        # que usarlo mezclaria en un mismo saco lo aprendido de MONT, AGGO y el
        # resto. Es la misma clave global que ya provoco una fuga de datos
        # entre empresas en el cache semantico (incidente de fuga de datos entre empresas del 27/07/2026).
        empresa_memoria = (company_code or "").strip().upper()
        if not empresa_memoria or empresa_memoria == "CHAT":
            empresa_memoria = str(self.database_name or "").strip().upper()

        if es_fuera_de_alcance(prompt_input):
            return {
                "pensamiento_analitico": "Pregunta fuera del dominio de negocio; se reorienta al usuario.",
                "sql": "",
                "explanation": respuesta_fuera_de_alcance(
                    self.business_name or self.database_name,
                    self.schema_tables,
                    semilla=prompt_input,
                ),
                "viz_type": "text",
                "viz_config": {},
                "business_analysis": "",
                "sql_explanation": "",
                "agent_log": ["Guardarrail de alcance (pregunta fuera del dominio)"],
            }, None

        # Validacion CRITICA: sin esquema no hay nada que consultar.
        # Ya NO se cae al radar web: eso era justo lo que convertia el asistente
        # en un lector de noticias cuando la base aun no estaba sincronizada.
        if not self.schema_text:
            return None, "Schema no cargado. Sincroniza la base de datos primero."

        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            llm = self._select_llm(module, question=prompt_input, modelo_forzado=modelo_forzado)
            from core.business_logic import get_business_logic

            # PODA SEMANTICA: Filtramos el esquema segun la pregunta
            effective_context_schema = self._prune_schema(prompt_input)

            variables_prompt = {
                    "schema": effective_context_schema,
                    "semantic_relations": self.semantic_relations,
                    # Mismo motivo que la memoria: `context_db` llega como "CHAT"
                    # para todas las empresas, y "CHAT" no esta en el mapa de
                    # business_logic.json, asi que la IA recibia SIEMPRE la
                    # descripcion generica por defecto y nunca sabia si estaba
                    # ante una unidad educativa o una comercial.
                    "business_logic": get_business_logic(
                        empresa_memoria or context_db, self.business_name or ""
                    ),
                    "question": prompt_input,
                    "history": history,
                    "module": module,
                    "context_db": context_db,
                    "current_date": datetime.now().strftime("%Y-%m-%d"),
                    # Segunda linea de defensa: el modelo recibe por escrito cual
                    # es su alcance y que modulos REALES tiene esta base, para que
                    # el rechazo sea concreto ("no tengo compras, sí alumnos") en
                    # lugar de un "no puedo" generico.
                    "alcance": bloque_alcance_para_prompt(
                        self.business_name or self.database_name, self.schema_tables
                    ),
                    "db_insights": self.db_insights if context_db in str(self.db_insights) else "",
                    # Memoria de largo plazo: correcciones y precisiones que el
                    # usuario dio en conversaciones ANTERIORES de esta misma
                    # empresa. Es lo que hace que una correccion no haya que
                    # repetirla en cada chat nuevo. Devuelve "" cuando no hay
                    # nada aprendido, dejando el prompt igual que antes.
                    "memoria_aprendida": bloque_memoria_para_prompt(empresa_memoria),
                    # Vistas reales detectadas en vivo (28/08/2026): evita que la
                    # IA invente cabecera_factura/cabecera_compra (nombres que ya
                    # no existen en el servidor) o use tb_cabmov/tb_detmov
                    # (lentas/vacías para varias empresas).
                    "vistas_reales": vistas_reales or (
                        "Vistas confirmadas en vivo: usa las que aparecen en el "
                        "ESQUEMA DE DATOS DISPONIBLE."
                    ),
            }

            # Pro usa su propio prompt de sistema (SYSTEM_PROMPT_PRO): más
            # compacto (reduce el razonamiento → menos latencia) y orientado
            # a producir insights ejecutivos visibles (hallazgo + recomendación),
            # de modo que la respuesta se distinga de Flash y justifique la
            # elección del motor Experto.
            _prompt_sistema = SYSTEM_PROMPT_PRO if llm is self.llm_pro else SYSTEM_PROMPT
            prompt = ChatPromptTemplate.from_template(_prompt_sistema)
            chain = prompt | llm | StrOutputParser()
            raw_response = chain.invoke(variables_prompt).strip()
            # 25/09/2026 (detectado por eval/evaluar_nl2sql.py): los
            # proveedores gratuitos a veces devuelven una salida vacía o
            # degenerada ("!!!!!!!!") sin lanzar error, así que la cascada
            # `.with_fallbacks()` no salta al siguiente. Se reintenta UNA
            # vez: para entonces el límite por minuto del proveedor que
            # falló suele haberse liberado o responde otro de la cascada.
            if _salida_degenerada(raw_response):
                time.sleep(3)
                raw_response = chain.invoke(variables_prompt).strip()

            if raw_response.startswith("CHAT:"):
                return raw_response, None

            parsed = self._extract_json(raw_response)
            if parsed is not None:
                # Inyectamos log de poda para transparencia
                if "agent_log" not in parsed or not isinstance(parsed["agent_log"], list):
                    parsed["agent_log"] = []
                parsed["agent_log"].append("Poda Semántica Universal Activa (Contexto optimizado)")
                return parsed, None

            return {
                "pensamiento_analitico": "Salida no estructurada; se mantiene fallback seguro.",
                "sql": "",
                "explanation": raw_response or "No se pudo estructurar la salida del modelo.",
                "viz_type": "text",
                "viz_config": {},
            }, None
        except Exception as exc:
            return None, f"Error del motor DeepSeek: {exc}"

    def generate_sql_with_retry(
        self,
        question: str,
        session,
        module: str = "GLOBAL",
        context_db: str = "CHAT",
        history: str = "",
        company_code: str = "",
        vistas_reales: str = "",
    ) -> tuple[Any, str | None]:
        response, error = self.generate_sql(
            question=question,
            module=module,
            context_db=context_db,
            history=history,
            company_code=company_code,
            vistas_reales=vistas_reales,
        )
        if error or not isinstance(response, dict):
            return response, error
        if not response.get("sql") or not session or not getattr(session, "connector", None):
            return response, None

        sql_preview, is_valid, _ = sanitize_pipeline(
            response.get("sql", ""),
            question,
            is_sqlite=getattr(session.connector, "is_sqlite", False),
        )
        response["correction_attempted"] = False
        if not is_valid:
            return response, None

        preview_sql = sql_preview
        try:
            source_db = context_db or getattr(session, "context_db", context_db)
            mirror = MirrorManager(session.connector)
            dna = mirror.get_virtual_dna_block(source_db, getattr(session, "schema_dict", {}) or {})
            if dna:
                preview_sql = mirror.compose_sql_with_virtual_dna(dna, sql_preview)
        except Exception:
            preview_sql = sql_preview

        _cols, _rows, db_error = session.connector.execute_query(preview_sql)
        if not db_error:
            return response, None

        # Si hay error, intentar corregir con la IA
        correction = self.generate_correction(response.get("sql", ""), str(db_error))
        response["sql"] = correction.get("sql", response.get("sql"))
        response["pensamiento_analitico"] = correction.get("pensamiento_analitico", "")
        response["correction_attempted"] = True
        
        return response, None

    def generate_correction(self, failed_sql: str, error_msg: str) -> dict:
        try:
            # Autocorregir SQL fallido es razonamiento complejo por definición
            # (hay que entender por qué falló y reescribir preservando la
            # intención de negocio) — antes esto lo hacía Qwen/Together AI si
            # estaba disponible; ahora lo cubre el modelo "Experto" de DeepSeek.
            llm = self.llm_pro
            prompt = ChatPromptTemplate.from_template(CORRECTION_PROMPT)
            chain = prompt | llm | StrOutputParser()
            raw = chain.invoke(
                {
                    "schema": self.schema_text,
                    "semantic_relations": self.semantic_relations,
                    "failed_sql": failed_sql,
                    "error_msg": error_msg,
                }
            ).strip()
            parsed = self._extract_json(raw)
            if parsed is not None:
                return parsed
            return {
                "pensamiento_analitico": "No se pudo parsear la correccion del modelo.",
                "sql": failed_sql,
                "explanation": "Se mantiene SQL original por seguridad.",
            }
        except Exception as exc:
            return {
                "pensamiento_analitico": "Error en auto-correccion.",
                "sql": failed_sql,
                "explanation": f"No se pudo corregir automaticamente: {exc}",
            }

    # Límite defensivo: DeepSeek Vision soporta más, pero más de 4 imágenes
    # por consulta degrada mucho la latencia sin aportar demasiado — el
    # usuario mismo lo anticipó al pedir esta función.
    MAX_IMAGENES_POR_CONSULTA = 4

    def analyze_images(self, question: str, images_b64: list[str]) -> dict:
        """
        FASE 4 — punto 6: análisis de imágenes adjuntas con el modelo Vision.

        `images_b64` son data URLs completas (ej. "data:image/png;base64,...."),
        tal como las produce `FileReader.readAsDataURL()` en el navegador — así
        el frontend no tiene que separar el mime type del contenido.

        Usa el formato de mensaje multimodal estándar (compatible OpenAI, que
        es el que expone DeepSeek para deepseek-v4-flash-vision-exp): una
        lista de bloques de contenido mezclando texto e `image_url`.
        """
        from langchain_core.messages import HumanMessage

        imagenes = [img for img in (images_b64 or []) if img][: self.MAX_IMAGENES_POR_CONSULTA]
        if not imagenes:
            return {
                "explanation": "No recibí ninguna imagen válida para analizar.",
                "visualization_type": "text",
                "agent_log": ["Vision: sin imágenes"],
            }

        pregunta = (question or "").strip() or (
            "Analiza esta imagen en el contexto del negocio y describe lo más "
            "relevante que encuentres (cifras, tendencias, texto legible)."
        )

        content = [{"type": "text", "text": pregunta}]
        for img in imagenes:
            content.append({"type": "image_url", "image_url": {"url": img}})

        try:
            mensaje = HumanMessage(content=content)
            respuesta = self.llm_vision.invoke([mensaje])
            texto = getattr(respuesta, "content", None) or str(respuesta)
            return {
                "explanation": texto.strip() or "No pude extraer información útil de la imagen.",
                "visualization_type": "text",
                "agent_log": [f"Vision: {len(imagenes)} imagen(es) analizada(s) con {DEEPSEEK_MODEL_VISION}"],
            }
        except Exception as exc:
            return {
                "explanation": (
                    "Tuve un problema técnico al analizar la imagen "
                    f"(no fue por falta de datos): {exc}"
                ),
                "visualization_type": "text",
                "agent_log": ["Vision: error técnico"],
                "error": str(exc),
            }

    # ── Conversación libre (exclusiva del modo desarrollador) ───────────────
    #
    # Este canal existe SOLO para la seña de desarrollador (ver
    # core/modo_desarrollador.py). Para cualquier otro usuario el guardarraíl
    # de alcance sigue intacto: VicMar Data AI no es un chatbot de propósito general
    # y responder noticias desde una herramienta de BI conectada a la base de
    # un colegio fue justamente el bug que originó core/alcance.py.
    #
    # No usa ChatPromptTemplate a propósito. Esa plantilla interpreta `{...}`
    # como variables, y aquí el texto del usuario es libre: pegar un JSON, un
    # bloque de código o un diccionario de Python reventaría el render con un
    # KeyError. Se arman los mensajes a mano y el texto llega intacto.
    PROMPT_LIBRE = (
        "Eres el motor de IA de VicMar Data AI hablando en MODO DESARROLLADOR con "
        "{alias}, quien construyó este sistema y se identificó con su seña "
        "privada.\n\n"
        "En este modo NO tienes el alcance acotado a los datos de la empresa "
        "activa: puedes conversar de cualquier tema, razonar sobre "
        "arquitectura, código, decisiones de producto o lo que te pregunte, "
        "usando tu conocimiento general.\n\n"
        "CONTEXTO TÉCNICO (por si es relevante):\n"
        "- VicMar Data AI es una plataforma de Inteligencia de Negocios "
        "multiempresa. Backend FastAPI + SQL Server, frontend React.\n"
        "- Empresa activa en esta sesión: {empresa}.\n"
        "- Fecha de hoy: {fecha}.\n\n"
        "LÍMITES QUE SIGUEN VIGENTES (no negociables, ni siquiera aquí):\n"
        "- Solo lectura sobre las bases de datos. Nunca ofrezcas ni simules "
        "escribir, editar o borrar datos, tablas o vistas.\n"
        "- Si te preguntan por cifras de la empresa, dilo claro: en modo libre "
        "no estás consultando la base, así que no inventes números. Pídele que "
        "haga la pregunta de negocio directamente para que pase por el motor "
        "SQL.\n\n"
        "FORMATO DE RESPUESTA:\n"
        "- Markdown claro: **negritas** para lo que importa, viñetas para "
        "enumerar, `código` cuando menciones archivos o identificadores.\n"
        "- Emojis con criterio al inicio de secciones o viñetas clave "
        "(✅ ⚠️ 🔍 📊 🔒 💡), nunca decorando cada frase.\n"
        "- Directo y completo. Si el mensaje es largo y trae varios puntos, "
        "respóndelos TODOS, uno por uno, sin resumirlos en una sola frase.\n"
        "- Español, con tildes correctas."
    )

    def chat_libre(
        self,
        question: str,
        history: str = "",
        alias: str = "VM",
        empresa: str = "",
    ) -> dict:
        """Responde directamente con el modelo, sin esquema, SQL ni alcance."""
        from langchain_core.messages import HumanMessage, SystemMessage

        pregunta = (question or "").strip()
        if not pregunta:
            return {
                "explanation": f"👋 Aquí estoy, {alias}. Dime qué necesitas.",
                "visualization_type": "text",
                "agent_log": ["Modo desarrollador — mensaje vacío"],
            }

        sistema = self.PROMPT_LIBRE.format(
            alias=alias or "VM",
            empresa=(empresa or self.business_name or self.database_name or "—"),
            fecha=datetime.now().strftime("%Y-%m-%d"),
        )

        mensajes = [SystemMessage(content=sistema)]
        if history:
            mensajes.append(
                SystemMessage(content=f"Historial reciente de la conversación:\n{history}")
            )
        mensajes.append(HumanMessage(content=pregunta))

        try:
            respuesta = self.llm_libre.invoke(mensajes)
            texto = (getattr(respuesta, "content", None) or str(respuesta)).strip()
            if not texto:
                raise ValueError("respuesta vacía del modelo")
            return {
                "explanation": texto,
                "visualization_type": "text",
                "sql": "",
                "agent_log": [f"Modo desarrollador — conversación libre ({DEEPSEEK_MODEL_PRO})"],
            }
        except Exception as exc:
            return {
                "explanation": (
                    "⚠️ No pude completar la respuesta en modo libre: "
                    f"{exc}\n\nEl resto del sistema sigue operativo; vuelve a "
                    "intentarlo en unos segundos."
                ),
                "visualization_type": "text",
                "agent_log": ["Modo desarrollador — error del proveedor IA"],
                "error": str(exc),
            }

    # ── Modo Invitado (Demo) ─────────────────────────────────────────────
    #
    # Un usuario con rol GUEST no tiene base de datos real conectada. En vez
    # de bloquearlo, se le responde con un dataset de ejemplo pequeño
    # (backend/data/demo_dataset.json) que cabe entero en el prompt — no hace
    # falta SQL ni esquema: el modelo razona directo sobre el JSON, igual que
    # si fuera una tabla más. Así el Invitado puede preguntar CUALQUIER cosa
    # de negocio ("ventas de marzo", "quién es mi mejor cliente", "compara
    # ventas contra compras") y obtiene una respuesta con el mismo formato
    # que tendría con datos reales.
    PROMPT_DEMO = (
        "Eres VicMar Data AI, el Asistente de Inteligencia de Negocios, respondiendo "
        "en MODO DEMOSTRACIÓN para un usuario Invitado que todavía no tiene una "
        "base de datos real conectada.\n\n"
        "Tienes un conjunto de datos de EJEMPLO (no reales) en JSON. Respóndele "
        "exactamente como responderías con datos reales: cifras concretas "
        "sacadas de ese JSON, tablas en Markdown cuando enumeres varios "
        "registros, y un breve análisis de negocio.\n\n"
        "DATASET DE EJEMPLO (JSON):\n{dataset}\n\n"
        "REGLAS:\n"
        "- Usa SOLO los datos del JSON. No inventes cifras que no estén ahí.\n"
        "- Si la pregunta no se puede responder con este dataset, dilo con "
        "claridad y ofrece lo más parecido que sí tengas ahí dentro.\n"
        "- Markdown limpio: negritas en las cifras clave, tabla en Markdown "
        "para listados de varios registros, un emoji de apertura por sección "
        "(📊 cifra, 🔍 hallazgo, 💡 recomendación) — nunca más de uno por bloque.\n"
        "- Termina SIEMPRE con una línea breve recordando que son datos de "
        "ejemplo (nunca dos veces, nunca como advertencia legal — un tono "
        "ligero: \"✨ Esto fue con datos de ejemplo\").\n"
        "- Español, cordial y profesional. Sin muletillas de relleno.\n\n"
        "Historial reciente de la conversación:\n{history}\n\n"
        "PREGUNTA DEL INVITADO:\n{question}"
    )

    def responder_demo(self, question: str, dataset: dict, history: str = "") -> dict:
        """Responde preguntas de un usuario Invitado usando el dataset de demo."""
        from langchain_core.messages import HumanMessage

        pregunta = (question or "").strip()
        if not pregunta:
            return {
                "explanation": (
                    "👋 Pregúntame algo como \"¿cuáles fueron las ventas de marzo?\" "
                    "o \"¿quién es mi mejor cliente?\" y te muestro cómo respondo con datos."
                ),
                "visualization_type": "text",
            }

        try:
            dataset_json = json.dumps(dataset or {}, ensure_ascii=False, indent=2)
        except Exception:
            dataset_json = "{}"

        texto = self.PROMPT_DEMO.format(
            dataset=dataset_json[:6000],
            history=history or "(sin historial previo)",
            question=pregunta,
        )

        try:
            respuesta = self.llm_flash.invoke([HumanMessage(content=texto)])
            salida = (getattr(respuesta, "content", None) or str(respuesta)).strip()
            if not salida:
                raise ValueError("respuesta vacía del modelo")
            return {
                "explanation": salida,
                "visualization_type": "text",
                "agent_log": ["Invitado: respuesta generada sobre dataset de demostración"],
            }
        except Exception as exc:
            # Nunca dejar al Invitado sin respuesta: si el modelo falla, un
            # resumen determinista sacado del propio dataset sigue siendo
            # útil y no depende de ninguna llamada externa.
            indicadores = (dataset or {}).get("indicadores_clave", {})
            resumen = "\n".join(f"- **{k}**: {v}" for k, v in indicadores.items()) or (
                "Sin indicadores de ejemplo disponibles."
            )
            return {
                "explanation": (
                    "✨ **Demostración de VicMar Data AI** (datos de ejemplo)\n\n"
                    "No pude generar una respuesta detallada a tu pregunta en este momento, "
                    f"pero aquí tienes un resumen de la empresa de ejemplo:\n\n{resumen}\n\n"
                    "Intenta preguntar de otra forma, o solicita acceso a datos reales."
                ),
                "visualization_type": "text",
                "agent_log": ["Invitado: fallback determinista (error del modelo)"],
                "error": str(exc),
            }

    def generate_error_narrative(self, question: str, error_msg: str) -> str:
        """
        Genera narrativa legible para errores de ejecucion SQL.
        OPTIMIZACION: Version ligera sin llamar a la IA para reducir latencia.
        """
        error_lower = error_msg.lower()
        
        # Mapeo directo de errores comunes (sin IA = 0ms de latencia)
        if "invalid column name" in error_lower or "column" in error_lower:
            return "La consulta referencia una columna que no existe. Verifica los nombres de columnas disponibles."
        if "invalid object name" in error_lower or "table" in error_lower:
            return "La tabla consultada no existe o no esta disponible en el esquema actual."
        if "timeout" in error_lower or "expired" in error_lower:
            return "La consulta tardo demasiado. Intenta con filtros mas especificos o un periodo menor."
        if "syntax error" in error_lower or "near" in error_lower:
            return "Error de sintaxis SQL. Reformula la pregunta con terminos mas claros."
        if "permission" in error_lower or "denied" in error_lower:
            # Auditoría 09/09/2026: no es un problema del usuario/rol — ver la
            # nota igual en core/deepseek_client.py::generate_error_narrative.
            return "No se pudo completar esa consulta por una restricción interna de acceso a datos. Intenta reformular la pregunta de forma más específica."
        if "connection" in error_lower or "network" in error_lower:
            return "Error de conexion con la base de datos. Verifica el servidor."
        
        # Fallback generico
        return f"Error al ejecutar la consulta: {error_msg[:150]}"
