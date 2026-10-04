"""
config.py - Configuracion central del backend VicMar Data AI.
Concentra variables de entorno de seguridad, cache y motor IA.
Evita hardcodear secretos y permite despliegue por entorno.
"""
import logging
import os
import pathlib

from dotenv import load_dotenv

_ENV_PATH = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# Rutas de trabajo para cache y debug local.
# Se crean en startup para garantizar escritura de diagnosticos.
BASE_DIR = pathlib.Path(__file__).parent
CACHE_DIR = BASE_DIR / ".cache"
CACHE_FILE = CACHE_DIR / "qbi_cache.json"
DEBUG_DIR = BASE_DIR / "debug"

CACHE_DIR.mkdir(exist_ok=True)
DEBUG_DIR.mkdir(exist_ok=True)

# Base de datos principal de ejecucion (Vacio por defecto para ingreso manual)
EXECUTION_DB = os.getenv("QUERY_DATABASE", "")
DEFAULT_HOST = os.getenv("DB_HOST", "")

# OPTIMIZACION: Autodetectar el Driver ODBC en tiempo de ejecución (Lazy Load) para evitar demoras en el arranque.
_cached_driver = None

def get_best_driver():
    global _cached_driver
    if _cached_driver:
        return _cached_driver

    env_driver = os.getenv("DB_DRIVER")
    if env_driver:
        _cached_driver = env_driver
        return _cached_driver

    try:
        import pyodbc
        drivers = pyodbc.drivers()
        for d in ["SQL Server", "ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"]:
            if d in drivers:
                _cached_driver = d
                return _cached_driver
    except Exception:
        pass

    _cached_driver = "SQL Server"
    return _cached_driver

DEFAULT_DRIVER = "AUTO"  # Se reemplazará en ejecución
DEFAULT_USER = os.getenv("DB_USER", "")
DEFAULT_PASSWORD = os.getenv("DB_PASSWORD", "")

# ── Capa 2: snapshots precacheados del Pulso BI por empresa ─────────────────
# Los snapshots viven en una tabla propia de CHAT ([CHAT].[dbo].[tb_bi_snapshot])
# y se refrescan en segundo plano por un job (Cloud Scheduler → endpoint).
# Cadencia (segundos): cada empresa debe refrescarse al menos cada 15 min.
BI_SNAPSHOT_REFRESH_SECONDS = int(os.getenv("BI_SNAPSHOT_REFRESH_SECONDS", "900"))
# Ventana para servido rápido: un snapshot de hasta 30 min se sirve SIN tocar
# SQL; si es más viejo (o no existe) se recalcula en vivo al abrir.
BI_SNAPSHOT_SERVE_MAX_AGE_SECONDS = int(os.getenv("BI_SNAPSHOT_SERVE_MAX_AGE_SECONDS", "1800"))
# Máximo de empresas por invocación del job y presupuesto de segundos por llamada,
# para que cada invocación del Scheduler no se pase del timeout de Cloud Run.
BI_SNAPSHOT_MAX_PER_RUN = int(os.getenv("BI_SNAPSHOT_MAX_PER_RUN", "6"))
BI_SNAPSHOT_MAX_RUN_SECONDS = int(os.getenv("BI_SNAPSHOT_MAX_RUN_SECONDS", "55"))
# Secreto compartido que protege los endpoints internos del job
# (X-Scheduler-Token). Si está vacío, solo un ADMINISTRADOR con JWT puede invocarlos.
BI_SCHEDULER_TOKEN = os.getenv("BI_SCHEDULER_TOKEN", "")

# Bases de datos permitidas (Vacio para permitir descubrimiento dinamico por host)
ALLOWED_DATABASES = []

# Proveedor DeepSeek.
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# ── Cascada de respaldo gratuita (ver core/nl2sql_engine.py) ────────────────
# Si DeepSeek no tiene llave (caso actual) o falla, el motor cae en cascada:
# Gemini -> Groq -> NVIDIA NIM, usando la capa de compatibilidad OpenAI de
# cada proveedor (misma clase ChatOpenAI de LangChain, solo cambia base_url).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
# 25/09/2026: deepseek-v4-pro-0813 y deepseek-v4-flash-0731 fueron retirados
# de NVIDIA NIM el 14/09/2026 (HTTP 410 Gone) — desde entonces el último
# eslabón de la cascada fallaba siempre. kimi-k3 verificado en vivo (HTTP 200,
# ~8 s); deepseek-v4.1-flash es el sucesor de los DeepSeek retirados.
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "moonshotai/kimi-k3")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Catálogo de modelos NVIDIA NIM seleccionables uno por uno (09/09/2026): la
# misma llave NVIDIA_API_KEY sirve para todos, solo
# cambia el nombre del modelo). NVIDIA_MODEL (arriba) sigue siendo el que
# participa en la cascada AUTOMÁTICA; estos son para el selector manual del
# chat, para probar cada modelo puntual.
NVIDIA_MODELOS_DISPONIBLES = {
    # Los dos DeepSeek anteriores (v4-pro-0813, v4-flash-0731) fueron retirados
    # el 14/09/2026; ambos alias apuntan ahora a su sucesor vigente.
    "nvidia_deepseek_pro": "deepseek-ai/deepseek-v4.1-flash",
    "nvidia_deepseek_flash": "deepseek-ai/deepseek-v4.1-flash",
    "nvidia_kimi": "moonshotai/kimi-k3",
    "nvidia_nemotron": "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia_muse": "meta/muse-glimmer-30b",
}
# Los identificadores de modelo de DeepSeek son sensibles a mayúsculas y van
# SIEMPRE en minúsculas ("deepseek-v4-flash", "deepseek-v4-pro"). El .env tenía
# "Deepseek-V4-Flash" y la API lo rechazaba en CADA llamada, dejando la IA
# completamente inutilizable — solo respondían las métricas certificadas y el
# banco de preguntas, que no pasan por el modelo. Normalizar aquí evita que un
# error de tipeo en el .env vuelva a tumbar la IA de forma silenciosa.
# Nota: los nombres antiguos "deepseek-chat"/"deepseek-reasoner" quedaron
# descontinuados el 24/07/2026; el reemplazo directo es deepseek-v4-flash.
#
# AVISO: "deepseek-v4-pro-vision-exp" aparecía en versiones previas de esta
# lista pero NO se encontró ninguna fuente oficial de DeepSeek que lo
# confirme (agosto 2026) — el único modelo de visión anunciado oficialmente
# es "deepseek-v4-flash-vision-exp" (lanzado 21/08/2026). Se mantiene aquí
# solo por si DeepSeek lo publica más adelante; no se usa como default de
# ningún cliente.
_MODELOS_DEEPSEEK_VIGENTES = {"deepseek-v4-flash", "deepseek-v4-pro",
                               "deepseek-v4-flash-vision-exp", "deepseek-v4-pro-vision-exp"}
_MODELOS_DEEPSEEK_DESCONTINUADOS = {"deepseek-chat": "deepseek-v4-flash",
                                    "deepseek-reasoner": "deepseek-v4-pro"}


def _normalizar_modelo_deepseek(nombre: str, etiqueta: str) -> str:
    """Normaliza un ID de modelo DeepSeek: minusculas, traduce nombres
    descontinuados y avisa si no reconoce el valor. Compartido por los 3
    modelos (flash/pro/vision) para no triplicar esta logica de seguridad."""
    modelo = (nombre or "").strip().lower()
    if modelo in _MODELOS_DEEPSEEK_DESCONTINUADOS:
        reemplazo = _MODELOS_DEEPSEEK_DESCONTINUADOS[modelo]
        logging.getLogger("Config").warning(
            "[IA] %s='%s' fue descontinuado por DeepSeek el 24/07/2026. "
            "Usando '%s' en su lugar. Actualiza el .env para quitar este aviso.",
            etiqueta, modelo, reemplazo,
        )
        return reemplazo
    if modelo not in _MODELOS_DEEPSEEK_VIGENTES:
        logging.getLogger("Config").warning(
            "[IA] %s='%s' no está en la lista de modelos conocidos (%s). "
            "Si la IA deja de responder, revisa este valor: un ID inválido "
            "hace que TODA consulta a ese modelo falle.",
            etiqueta, modelo, ", ".join(sorted(_MODELOS_DEEPSEEK_VIGENTES)),
        )
    return modelo


# Modelo "Instant" — conversación cotidiana y consultas simples de una métrica.
DEEPSEEK_MODEL = _normalizar_modelo_deepseek(
    os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"), "DEEPSEEK_MODEL"
)
# Modelo "Experto" — razonamiento complejo: forecast, comparativas
# multi-módulo, autocorrección de SQL fallido, finanzas/contabilidad.
DEEPSEEK_MODEL_PRO = _normalizar_modelo_deepseek(
    os.getenv("DEEPSEEK_MODEL_PRO", "deepseek-v4-pro"), "DEEPSEEK_MODEL_PRO"
)
# Modelo "Vision" — preguntas que adjuntan una o más imágenes.
DEEPSEEK_MODEL_VISION = _normalizar_modelo_deepseek(
    os.getenv("DEEPSEEK_MODEL_VISION", "deepseek-v4-flash-vision-exp"), "DEEPSEEK_MODEL_VISION"
)

# Sentry (captura de excepciones en produccion, FASE 4 - punto 4 Nivel 2).
# Opcional: si queda vacio, el backend funciona exactamente igual, solo que
# sin reportar errores. Crear un proyecto FastAPI/Python en sentry.io y pegar
# el DSN aqui o en env.yaml.
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Together AI (Qwen) fue retirado (FASE 4 - punto 6): se comprobó que
# _select_llm() en nl2sql_engine.py siempre devolvía DeepSeek para la
# generación principal de SQL, y el único uso real que le quedaba
# (autocorrección de SQL fallido, en generate_correction) ahora lo cubre
# DEEPSEEK_MODEL_PRO ("Experto") en su lugar — mismo propósito, sin mantener
# una segunda cuenta/API key solo para eso.
FAL_KEY = os.getenv("FAL_KEY", "")

# Parametros de inferencia LLM.
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
# Subido de 600 a 1600 el 30/08/2026. El motor no pide texto suelto: pide un
# JSON que contiene el SQL COMPLETO mas la explicacion en Markdown. Con 600
# tokens, una consulta con varios JOIN o un CHOOSE de doce meses agotaba el
# presupuesto a mitad del JSON; la respuesta llegaba cortada, `_extract_json`
# no podia parsearla y el motor caia al camino de "Salida no estructurada",
# devolviendo texto crudo o una respuesta a medias. Ese era el sintoma que el
# usuario describia como "a veces se quiere bugear", y empeoraba justo con las
# preguntas largas o detalladas, que son las que mas SQL y mas explicacion
# generan. Sigue siendo configurable por entorno.
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1600"))
# Presupuesto propio del modelo "Experto" (Pro), más holgado que el de Flash.
# deepseek-v4-pro es un modelo de RAZONAMIENTO: emite `reasoning_content`
# (cadena de pensamiento) ANTES del `content`, y AMBOS comparten el mismo tope
# de max_tokens. Con 1600, el razonamiento se comía TODO el presupuesto y el
# JSON final llegaba vacío o cortado a mitad — el usuario lo veía como "Pro no
# se activa del todo" (bug real 30/08/2026). LangChain además ignora el
# reasoning_content, así que cada token pensado es "perdido" desde la salida.
# 3200 da margen para razonar Y entregar el JSON sin tocar el presupuesto de
# Flash (LLM_MAX_TOKENS). Configurable por entorno si hace falta.
LLM_MAX_TOKENS_PRO = int(os.getenv("LLM_MAX_TOKENS_PRO", "3200"))
HISTORY_DEPTH = int(os.getenv("HISTORY_DEPTH", "4"))

# ═══════════════════════════════════════════════════════════════════════════
# DATASET DE DEMOSTRACIÓN (para GUEST — Demo Mode)
# ═══════════════════════════════════════════════════════════════════════════
# Cuando un usuario GUEST consulta, el sistema usa estos datos de ejemplo
# en lugar de conectarse a una BD real. La experiencia es idéntica: gráficos,
# tablas, análisis — pero con datos inventados pero realistas.

try:
    DEMO_DATASET_PATH = BASE_DIR / "data" / "demo_dataset.json"
    if DEMO_DATASET_PATH.exists():
        import json
        with open(DEMO_DATASET_PATH, "r", encoding="utf-8") as f:
            DEMO_DATASET = json.load(f)
        DEMO_DATASET_LOADED = True
    else:
        DEMO_DATASET = {}
        DEMO_DATASET_LOADED = False
except Exception as e:
    logger.warning("[DEMO] No se pudo cargar demo_dataset.json: %s", e)
    DEMO_DATASET = {}
    DEMO_DATASET_LOADED = False

# Infraestructura de cache.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

# Entorno de ejecucion. "development" por defecto para no romper flujos locales;
# debe fijarse explicitamente a "production" en despliegues reales (.env / env.yaml).
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

# Seguridad JWT.
_JWT_DEFAULT_SECRET = "change-me-v2-dev-default"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", _JWT_DEFAULT_SECRET)
JWT_ALGORITHM = os.getenv("ALGORITHM", "HS256")
JWT_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# Regla de oro de seguridad: nunca arrancar en produccion con el secreto JWT por defecto.
# Si esto falla, el arranque se detiene aqui mismo (fail-fast) en lugar de emitir tokens inseguros.
if APP_ENV == "production" and JWT_SECRET_KEY == _JWT_DEFAULT_SECRET:
    raise RuntimeError(
        "JWT_SECRET_KEY sigue en su valor por defecto con APP_ENV=production. "
        "Define un JWT_SECRET_KEY propio en backend/.env antes de desplegar."
    )

# CORS con default cerrado a localhost.
# En produccion, definir ALLOWED_ORIGINS en .env.
# El rango 5173-5182 cubre el puerto que Vite termine usando: cuando hay varios
# proyectos corriendo en paralelo el lanzador busca el primer puerto libre a
# partir de 5173, asi que el origen del frontend no siempre es el mismo.
_DEV_FRONTEND_PORTS = range(5173, 5183)
_DEFAULT_ORIGINS = ",".join(
    [f"http://localhost:{port}" for port in _DEV_FRONTEND_PORTS]
    + [f"http://127.0.0.1:{port}" for port in _DEV_FRONTEND_PORTS]
    + ["http://localhost:3000"]
)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

# Correo saliente (SMTP) — hoy el único uso es "Olvidé mi contraseña" (Mi
# Perfil, Fase 5, 28/08/2026). Gmail con "contraseña de aplicación" (requiere
# verificación en 2 pasos activada en la cuenta de Google):
# https://myaccount.google.com/apppasswords
# Si SMTP_USER o SMTP_APP_PASSWORD quedan vacíos, core/email_service.py no
# envía nada y lo deja registrado en el log — el resto del backend sigue
# funcionando igual, solo sin poder mandar correos.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "VicMar Data AI")
