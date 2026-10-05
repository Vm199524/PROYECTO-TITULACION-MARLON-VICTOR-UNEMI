"""
Configuración central del backend.

Lee backend/.env y concentra en un solo lugar las variables de seguridad (JWT,
CORS), base de datos, caché, proveedores de IA y correo saliente, para no
escribir secretos en el código y poder desplegar por entorno.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import logging
import os
import pathlib

from dotenv import load_dotenv

_ENV_PATH = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# Rutas de trabajo para la caché y los diagnósticos locales. Se crean al
# importar el módulo para que siempre exista dónde escribir.
BASE_DIR = pathlib.Path(__file__).parent
CACHE_DIR = BASE_DIR / ".cache"
CACHE_FILE = CACHE_DIR / "qbi_cache.json"
DEBUG_DIR = BASE_DIR / "debug"

CACHE_DIR.mkdir(exist_ok=True)
DEBUG_DIR.mkdir(exist_ok=True)

# Base de datos principal de ejecución (vacía por defecto: se ingresa desde la interfaz).
EXECUTION_DB = os.getenv("QUERY_DATABASE", "")
DEFAULT_HOST = os.getenv("DB_HOST", "")

# El driver ODBC se detecta en la primera conexión (carga diferida) y no al
# importar el módulo, para no demorar el arranque.
_cached_driver = None

def get_best_driver():
    """Devuelve el driver ODBC de SQL Server a usar y lo memoriza.

    Prioridad: DB_DRIVER del .env; si no está, el primero instalado entre
    «SQL Server», «ODBC Driver 18» y «ODBC Driver 17»; si pyodbc no está
    disponible o no encuentra ninguno, «SQL Server».
    """
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

DEFAULT_DRIVER = "AUTO"  # Se resuelve con get_best_driver() al armar la conexión
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

# Bases de datos permitidas (vacía para permitir el descubrimiento dinámico por host).
ALLOWED_DATABASES = []

# Proveedor DeepSeek.
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# ── Cascada de respaldo gratuita (ver core/nl2sql_engine.py) ────────────────
# Si DeepSeek no tiene llave o falla, el motor cae en cascada:
# Gemini -> Groq -> NVIDIA NIM, usando la capa de compatibilidad OpenAI de
# cada proveedor (misma clase ChatOpenAI de LangChain, solo cambia base_url).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
# Modelo de NVIDIA NIM que cierra la cascada automática. Los modelos
# deepseek-v4-pro-0813 y deepseek-v4-flash-0731 ya no existen en NIM (HTTP 410
# Gone) y harían fallar siempre el último eslabón; por eso se usa kimi-k3.
# deepseek-v4.1-flash es el sucesor de los DeepSeek retirados.
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "moonshotai/kimi-k3")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Catálogo de modelos de NVIDIA NIM seleccionables uno por uno en el selector
# manual del chat, para probar cada modelo puntual. La misma llave
# NVIDIA_API_KEY sirve para todos; solo cambia el nombre del modelo.
# NVIDIA_MODEL (arriba) es el único que participa en la cascada automática.
NVIDIA_MODELOS_DISPONIBLES = {
    # Los alias «pro» y «flash» apuntan al mismo sucesor vigente porque los
    # DeepSeek originales (v4-pro-0813, v4-flash-0731) fueron retirados de NIM.
    "nvidia_deepseek_pro": "deepseek-ai/deepseek-v4.1-flash",
    "nvidia_deepseek_flash": "deepseek-ai/deepseek-v4.1-flash",
    "nvidia_kimi": "moonshotai/kimi-k3",
    "nvidia_nemotron": "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia_muse": "meta/muse-glimmer-30b",
}
# Los identificadores de modelo de DeepSeek distinguen mayúsculas y van siempre
# en minúsculas ("deepseek-v4-flash", "deepseek-v4-pro"). Un ID con otra
# capitalización en el .env (p. ej. "Deepseek-V4-Flash") hace que la API rechace
# cada llamada y deja la IA inutilizable en silencio: solo seguirían respondiendo
# las métricas certificadas y el banco de preguntas, que no pasan por el modelo.
# Por eso se normaliza aquí. Los nombres antiguos "deepseek-chat" y
# "deepseek-reasoner" están descontinuados y se traducen a su reemplazo.
#
# "deepseek-v4-pro-vision-exp" se conserva en la lista aunque no hay una fuente
# oficial de DeepSeek que lo confirme (el modelo de visión anunciado es
# "deepseek-v4-flash-vision-exp"); no es el valor por defecto de ningún cliente.
_MODELOS_DEEPSEEK_VIGENTES = {"deepseek-v4-flash", "deepseek-v4-pro",
                               "deepseek-v4-flash-vision-exp", "deepseek-v4-pro-vision-exp"}
_MODELOS_DEEPSEEK_DESCONTINUADOS = {"deepseek-chat": "deepseek-v4-flash",
                                    "deepseek-reasoner": "deepseek-v4-pro"}


def _normalizar_modelo_deepseek(nombre: str, etiqueta: str) -> str:
    """Normaliza un ID de modelo DeepSeek.

    Lo pasa a minúsculas, traduce los nombres descontinuados y avisa en el log
    si no reconoce el valor. Lo comparten los tres modelos (flash, pro y
    visión) para no triplicar esta validación.
    """
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
# Modelo "Visión" — preguntas que adjuntan una o más imágenes.
DEEPSEEK_MODEL_VISION = _normalizar_modelo_deepseek(
    os.getenv("DEEPSEEK_MODEL_VISION", "deepseek-v4-flash-vision-exp"), "DEEPSEEK_MODEL_VISION"
)

# Sentry: captura de excepciones en producción. Es opcional: si queda vacío, el
# backend funciona igual, solo que sin reportar errores. El DSN sale de un
# proyecto FastAPI/Python en sentry.io y se coloca en .env o en env.yaml.
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Llave de FAL AI para la lectura en voz alta (/api/query/speak). La
# autocorrección de SQL fallido no usa un proveedor aparte: la cubre
# DEEPSEEK_MODEL_PRO ("Experto").
FAL_KEY = os.getenv("FAL_KEY", "")

# Parámetros de inferencia del LLM.
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
# Tope de tokens de salida de Flash. El motor no pide texto suelto: pide un JSON
# con el SQL completo más la explicación en Markdown. Con un tope bajo (600), una
# consulta con varios JOIN o un CHOOSE de doce meses agota el presupuesto a mitad
# del JSON; la respuesta llega cortada, `_extract_json` no puede parsearla y el
# motor cae al camino de "Salida no estructurada" con texto crudo o a medias. Las
# preguntas largas o detalladas, que generan más SQL y más explicación, son las
# más afectadas. Configurable por entorno.
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1600"))
# Presupuesto propio del modelo "Experto" (Pro), más holgado que el de Flash.
# deepseek-v4-pro es un modelo de razonamiento: emite `reasoning_content`
# (cadena de pensamiento) antes del `content`, y ambos comparten el mismo tope
# de max_tokens. Con 1600, el razonamiento agota el presupuesto y el JSON final
# llega vacío o cortado. LangChain además descarta el reasoning_content, así que
# cada token de razonamiento se pierde para la salida. 3200 da margen para
# razonar y entregar el JSON sin tocar el presupuesto de Flash (LLM_MAX_TOKENS).
# Configurable por entorno.
LLM_MAX_TOKENS_PRO = int(os.getenv("LLM_MAX_TOKENS_PRO", "3200"))
HISTORY_DEPTH = int(os.getenv("HISTORY_DEPTH", "4"))

# ═══════════════════════════════════════════════════════════════════════════
# DATASET DE DEMOSTRACIÓN (para GUEST — Demo Mode)
# ═══════════════════════════════════════════════════════════════════════════
# Cuando un usuario GUEST consulta, el sistema usa estos datos de ejemplo en
# lugar de conectarse a una base real. La experiencia es la misma (gráficos,
# tablas y análisis), pero con datos de ejemplo realistas.

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

# Infraestructura de caché.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

# Entorno de ejecución. "development" por defecto para no romper los flujos
# locales; debe fijarse a "production" en despliegues reales (.env / env.yaml).
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

# Seguridad JWT.
_JWT_DEFAULT_SECRET = "change-me-v2-dev-default"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", _JWT_DEFAULT_SECRET)
JWT_ALGORITHM = os.getenv("ALGORITHM", "HS256")
JWT_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# Nunca se arranca en producción con el secreto JWT por defecto: el arranque se
# detiene aquí mismo (fail-fast) en lugar de emitir tokens inseguros.
if APP_ENV == "production" and JWT_SECRET_KEY == _JWT_DEFAULT_SECRET:
    raise RuntimeError(
        "JWT_SECRET_KEY sigue en su valor por defecto con APP_ENV=production. "
        "Define un JWT_SECRET_KEY propio en backend/.env antes de desplegar."
    )

# CORS cerrado a localhost por defecto; en producción se define ALLOWED_ORIGINS
# en .env. El rango 5173-5182 cubre el puerto que termine usando Vite: con varios
# proyectos corriendo en paralelo, el lanzador toma el primer puerto libre a
# partir de 5173, así que el origen del frontend no siempre es el mismo.
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

# Correo saliente (SMTP), usado por "Olvidé mi contraseña" en Mi Perfil. Con
# Gmail se usa una "contraseña de aplicación" (requiere la verificación en dos
# pasos activada en la cuenta de Google): https://myaccount.google.com/apppasswords
# Si SMTP_USER o SMTP_APP_PASSWORD quedan vacíos, core/email_service.py no envía
# nada y lo registra en el log; el resto del backend funciona igual.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "VicMar Data AI")
