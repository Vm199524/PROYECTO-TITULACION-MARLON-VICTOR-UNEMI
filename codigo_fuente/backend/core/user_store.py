"""
user_store.py — Almacén único de usuarios y roles de VicMar Data AI.

PROBLEMA QUE RESUELVE
---------------------
Hasta el 30/08/2026 los usuarios vivían únicamente en `backend/security_config.json`,
un archivo en el disco local, y `main.py` caía a una configuración por defecto
embebida en el propio código cuando ese archivo no existía. Eso produjo tres
problemas reales, detectados al preparar el despliegue central:

1. **La configuración por defecto traía cuentas que funcionaban.** El hash de
   `admin` está en el código fuente y su contraseña es débil, así que cualquiera
   con acceso al repositorio podía entrar a una instalación recién creada. Y como
   `.dockerignore` excluye `security_config.json` de la imagen, TODA imagen de
   Docker arrancaba precisamente en ese estado.
2. **En Cloud Run los cambios se perdían.** El disco de un contenedor es efímero:
   crear o desactivar un usuario desde "Gestión de Usuarios" duraba hasta el
   siguiente reinicio. Sin persistencia no hay control de acceso central, que es
   justamente lo que el administrador necesita para poder revocar a alguien.
3. **No había un punto único para consultar usuarios**, así que revalidar en cada
   petición (ver `security.get_current_user`) hubiera significado leer el archivo
   a mano desde varios sitios.

QUÉ HACE ESTE MÓDULO
--------------------
Centraliza la lectura y escritura del almacén, con dos backends intercambiables:

- **Archivo local** (por defecto): mismo `security_config.json` de siempre. El
  comportamiento en desarrollo no cambia en absoluto.
- **Google Cloud Storage** (opcional): se activa definiendo `USER_STORE_GCS_BUCKET`.
  Guarda EL MISMO JSON en un bucket, así que los cambios sobreviven a los
  reinicios de Cloud Run. Se eligió GCS y no una tabla en SQL Server a propósito:
  las bases de datos de las empresas son de solo lectura para este sistema y no
  se les debe agregar estructura.

Y aplica una política de **fallo cerrado**: si no hay almacén, NO se inventan
usuarios. Sin usuarios nadie entra, que es el comportamiento seguro. Para poder
arrancar una instalación nueva existe un bootstrap explícito por variables de
entorno (ver `_bootstrap_desde_entorno`), que no deja credenciales en el código.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

import bcrypt

logger = logging.getLogger(__name__)

# Carpeta de `backend/` (este archivo vive en backend/core/).
BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_LOCAL = BASE_DIR / "security_config.json"

# ── Configuración por entorno ───────────────────────────────────────────────
# Si GCS_BUCKET está definido, el almacén vive en Cloud Storage. Si no, en el
# archivo local de siempre.
GCS_BUCKET = (os.getenv("USER_STORE_GCS_BUCKET") or "").strip()
GCS_OBJETO = (os.getenv("USER_STORE_GCS_OBJECT") or "security_config.json").strip()

# Cuántos segundos se puede reutilizar la copia en memoria cuando el almacén es
# remoto. Es el retardo máximo con el que se propaga una revocación entre
# instancias de Cloud Run; con el archivo local no se usa (ahí se detecta el
# cambio por fecha de modificación y la revocación es inmediata).
TTL_CACHE_REMOTO_S = float(os.getenv("USER_STORE_CACHE_TTL", "15"))

# Bootstrap de una instalación nueva, SIN credenciales en el código.
BOOTSTRAP_USER = (os.getenv("TRIPLEA_BOOTSTRAP_ADMIN_USER") or "").strip()
BOOTSTRAP_PASSWORD = os.getenv("TRIPLEA_BOOTSTRAP_ADMIN_PASSWORD") or ""

# Los ROLES sí se pueden tener por defecto: describen permisos, no dan acceso a
# nadie por sí solos. Lo que nunca se rellena por defecto es la lista de usuarios.
ROLES_POR_DEFECTO = {
    "ADMINISTRADOR": {
        "level": 1,
        "description": "Acceso total a toda la inteligencia estratégica, financiera y operativa.",
        "scope": "GLOBAL",
        "modules": ["RRHH", "VENTAS", "FINANZAS", "OPERACIONES", "ACADEMICO"],
    },
    "CONTABILIDAD": {
        "level": 2,
        "description": "Acceso a reportes financieros, contables, ventas y compras de la empresa.",
        "scope": "FINANCIAL",
        "modules": ["FINANZAS", "VENTAS"],
    },
    "RRHH": {
        "level": 3,
        "description": "Acceso exclusivo al módulo de Capital Humano.",
        "scope": "HUMAN_CAPITAL",
        "modules": ["RRHH"],
    },
    "LOGISTICA": {
        "level": 4,
        "description": "Acceso a operaciones, compras, inventario y abastecimiento.",
        "scope": "OPERATIONS",
        "modules": ["OPERACIONES"],
    },
    "GUEST": {
        "level": 5,
        "description": "Solo lectura nivel demo.",
        "scope": "DEMO",
        "modules": [],
    },
}


def _config_vacia() -> dict:
    """Almacén sin ningún usuario: nadie puede entrar (fallo cerrado)."""
    return {"roles": dict(ROLES_POR_DEFECTO), "users": []}


# ── Caché en memoria ────────────────────────────────────────────────────────
# Necesaria porque `security.get_current_user` consulta el almacén en CADA
# petición autenticada. Sin caché, con backend remoto eso sería una llamada de
# red por request.
_lock = threading.Lock()
_cache: dict | None = None
_cache_ts: float = 0.0
_cache_mtime: float = 0.0


def usando_gcs() -> bool:
    return bool(GCS_BUCKET)


def _cliente_gcs():
    """Importación perezosa: una instalación local no necesita la librería."""
    from google.cloud import storage  # noqa: PLC0415

    return storage.Client()


def _leer_remoto() -> dict | None:
    try:
        blob = _cliente_gcs().bucket(GCS_BUCKET).blob(GCS_OBJETO)
        if not blob.exists():
            logger.warning(
                "[USER_STORE] gs://%s/%s todavía no existe.", GCS_BUCKET, GCS_OBJETO
            )
            return None
        return json.loads(blob.download_as_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        # Nunca se degrada a "sin usuarios" por un fallo de red: eso dejaría a
        # todo el mundo fuera. Se propaga como None y el llamador decide.
        logger.error("[USER_STORE] No se pudo leer de GCS: %s", exc)
        return None


def _escribir_remoto(config: dict) -> None:
    blob = _cliente_gcs().bucket(GCS_BUCKET).blob(GCS_OBJETO)
    blob.upload_from_string(
        json.dumps(config, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )


def _leer_local() -> dict | None:
    if not RUTA_LOCAL.exists():
        return None
    try:
        # utf-8-sig: el archivo puede venir con BOM si se editó en Windows.
        with open(RUTA_LOCAL, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        logger.error("[USER_STORE] No se pudo leer %s: %s", RUTA_LOCAL, exc)
        return None


def _escribir_local(config: dict) -> None:
    with open(RUTA_LOCAL, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _normalizar(config: dict | None) -> dict:
    """Deja la config siempre con la forma esperada por el resto del sistema."""
    if not isinstance(config, dict):
        return _config_vacia()
    if not isinstance(config.get("users"), list):
        config["users"] = []
    if not isinstance(config.get("roles"), dict) or not config["roles"]:
        config["roles"] = dict(ROLES_POR_DEFECTO)
    return config


def _bootstrap_desde_entorno(config: dict) -> dict:
    """
    Crea el primer administrador SOLO si el almacén está vacío y las variables
    de entorno lo piden explícitamente. Así una instalación nueva puede
    arrancar sin que existan credenciales conocidas en el código fuente.
    """
    if config.get("users"):
        return config
    if not BOOTSTRAP_USER or not BOOTSTRAP_PASSWORD:
        logger.warning(
            "[USER_STORE] El almacén no tiene usuarios y no hay bootstrap configurado. "
            "Nadie podrá iniciar sesión. Define TRIPLEA_BOOTSTRAP_ADMIN_USER y "
            "TRIPLEA_BOOTSTRAP_ADMIN_PASSWORD, o provee un security_config.json."
        )
        return config

    hash_pwd = bcrypt.hashpw(BOOTSTRAP_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    config["users"] = [
        {
            "username": BOOTSTRAP_USER,
            "password": hash_pwd,
            "name": BOOTSTRAP_USER,
            "role": "ADMINISTRADOR",
            "active": True,
        }
    ]
    logger.warning(
        "[USER_STORE] Almacén vacío: se creó el administrador inicial '%s' desde "
        "variables de entorno. Cambia su contraseña y retira esas variables.",
        BOOTSTRAP_USER,
    )
    try:
        guardar_config(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("[USER_STORE] No se pudo persistir el bootstrap: %s", exc)
    return config


def cargar_config(forzar: bool = False) -> dict:
    """
    Devuelve la configuración de seguridad (roles + usuarios).

    Usa una copia en memoria para no releer el almacén en cada petición. Con el
    archivo local la copia se invalida por fecha de modificación, así que un
    cambio se ve al instante; con GCS se invalida por tiempo (TTL_CACHE_REMOTO_S).
    """
    global _cache, _cache_ts, _cache_mtime

    with _lock:
        ahora = time.time()
        if _cache is not None and not forzar:
            if usando_gcs():
                if (ahora - _cache_ts) < TTL_CACHE_REMOTO_S:
                    return _cache
            else:
                try:
                    mtime = RUTA_LOCAL.stat().st_mtime if RUTA_LOCAL.exists() else 0.0
                except OSError:
                    mtime = 0.0
                if mtime == _cache_mtime:
                    return _cache

        crudo = _leer_remoto() if usando_gcs() else _leer_local()
        config = _normalizar(crudo)
        if crudo is None:
            config = _bootstrap_desde_entorno(config)

        _cache = config
        _cache_ts = ahora
        try:
            _cache_mtime = RUTA_LOCAL.stat().st_mtime if RUTA_LOCAL.exists() else 0.0
        except OSError:
            _cache_mtime = 0.0
        return config


def guardar_config(config: dict) -> None:
    """Persiste la configuración y refresca la copia en memoria."""
    global _cache, _cache_ts, _cache_mtime

    if usando_gcs():
        _escribir_remoto(config)
    else:
        _escribir_local(config)

    with _lock:
        _cache = config
        _cache_ts = time.time()
        try:
            _cache_mtime = RUTA_LOCAL.stat().st_mtime if RUTA_LOCAL.exists() else 0.0
        except OSError:
            _cache_mtime = 0.0


def buscar_usuario(username: str) -> dict | None:
    """Busca un usuario por nombre (sin distinguir mayúsculas) en el almacén vigente."""
    clave = str(username or "").strip().lower()
    if not clave:
        return None
    for u in cargar_config().get("users", []):
        if str(u.get("username", "")).strip().lower() == clave:
            return u
    return None


def usuario_activo(username: str) -> dict | None:
    """
    Devuelve el usuario solo si sigue existiendo y sigue activo.

    Es la comprobación que convierte "desactivar un usuario" en una revocación
    real: sin ella, el JWT ya emitido seguiría siendo válido hasta expirar
    (8 horas por defecto) aunque la cuenta estuviera desactivada.
    """
    usuario = buscar_usuario(username)
    if not usuario:
        return None
    if not usuario.get("active", True):
        return None
    return usuario


def invalidar_cache() -> None:
    """Fuerza la relectura del almacén en la próxima consulta (útil en pruebas)."""
    global _cache, _cache_ts, _cache_mtime
    with _lock:
        _cache = None
        _cache_ts = 0.0
        _cache_mtime = 0.0
