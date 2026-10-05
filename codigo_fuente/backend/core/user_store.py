"""
Almacén único de usuarios y roles.

Centraliza la lectura y escritura de security_config.json, que también usa
security.get_current_user para revalidar al usuario en cada petición. Tiene dos
backends: el archivo local (por defecto) o Google Cloud Storage si se define
USER_STORE_GCS_BUCKET, para que los cambios sobrevivan a los reinicios de Cloud
Run; se eligió GCS y no una tabla porque las bases de las empresas son de solo
lectura. Aplica fallo cerrado: sin almacén no hay usuarios y nadie entra.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
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
# Si GCS_BUCKET está definido, el almacén vive en Cloud Storage; si no, en el
# archivo local.
GCS_BUCKET = (os.getenv("USER_STORE_GCS_BUCKET") or "").strip()
GCS_OBJETO = (os.getenv("USER_STORE_GCS_OBJECT") or "security_config.json").strip()

# Cuántos segundos se puede reutilizar la copia en memoria cuando el almacén es
# remoto. Es el retardo máximo con el que se propaga una revocación entre
# instancias de Cloud Run; con el archivo local no se usa (ahí se detecta el
# cambio por fecha de modificación y la revocación es inmediata).
TTL_CACHE_REMOTO_S = float(os.getenv("USER_STORE_CACHE_TTL", "15"))

# Arranque de una instalación nueva sin credenciales en el código: el primer
# administrador se crea desde estas variables (ver _bootstrap_desde_entorno).
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
    "ACADEMICO": {
        "level": 3,
        "description": "Acceso exclusivo a la gestión académica: alumnos, matrículas, riesgo de abandono, "
                       "segmentos de carreras y referentes. No incluye datos financieros, de ventas ni de nómina.",
        "scope": "ACADEMIC",
        "modules": ["ACADEMICO"],
    },
    "GUEST": {
        "level": 5,
        "description": "Solo lectura nivel demo.",
        "scope": "DEMO",
        "modules": [],
    },
}


def _config_vacia() -> dict:
    """Devuelve un almacén sin usuarios, con el que nadie puede entrar (fallo cerrado).

    No hay cuentas por defecto porque un hash escrito en el código daría acceso
    a cualquiera con el repositorio, y la imagen de Docker no incluye
    security_config.json, así que toda instalación nueva quedaría expuesta.
    """
    return {"roles": dict(ROLES_POR_DEFECTO), "users": []}


# ── Caché en memoria ────────────────────────────────────────────────────────
# Necesaria porque `security.get_current_user` consulta el almacén en cada
# petición autenticada; sin caché, con el backend remoto habría una llamada de
# red por petición.
_lock = threading.Lock()
_cache: dict | None = None
_cache_ts: float = 0.0
_cache_mtime: float = 0.0


def usando_gcs() -> bool:
    """Indica si el almacén vive en Google Cloud Storage."""
    return bool(GCS_BUCKET)


def _cliente_gcs():
    """Crea el cliente de Cloud Storage con importación perezosa.

    Una instalación local no necesita tener instalada la biblioteca.
    """
    from google.cloud import storage  # noqa: PLC0415

    return storage.Client()


def _leer_remoto() -> dict | None:
    """Lee el JSON del bucket; devuelve None si no existe o si falla la lectura."""
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
    """Lee el security_config.json local; devuelve None si no existe o está dañado."""
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
    """Garantiza que la configuración tenga la forma que espera el resto del sistema."""
    if not isinstance(config, dict):
        return _config_vacia()
    if not isinstance(config.get("users"), list):
        config["users"] = []
    if not isinstance(config.get("roles"), dict) or not config["roles"]:
        config["roles"] = dict(ROLES_POR_DEFECTO)
    return config


def _bootstrap_desde_entorno(config: dict) -> dict:
    """Crea el primer administrador solo si el almacén está vacío y el entorno lo pide.

    Requiere TRIPLEA_BOOTSTRAP_ADMIN_USER y TRIPLEA_BOOTSTRAP_ADMIN_PASSWORD.
    Así una instalación nueva puede arrancar sin credenciales conocidas en el
    código fuente.
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
    """Devuelve la configuración de seguridad (roles y usuarios).

    Usa una copia en memoria para no releer el almacén en cada petición. Con el
    archivo local la copia se invalida por fecha de modificación, así que un
    cambio se ve al instante; con GCS se invalida por tiempo (TTL_CACHE_REMOTO_S).

    Args:
        forzar: si es True, ignora la copia en memoria y relee el almacén.
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
    """Devuelve el usuario solo si sigue existiendo y está activo.

    Esta comprobación convierte «desactivar un usuario» en una revocación real:
    sin ella, el JWT ya emitido seguiría siendo válido hasta expirar (8 horas
    por defecto) aunque la cuenta estuviera desactivada.
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
