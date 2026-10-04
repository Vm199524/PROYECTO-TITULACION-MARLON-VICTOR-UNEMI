"""
core/audit_log.py — Registro de auditoría: quién hizo qué, cuándo y desde dónde.

ORIGEN
------
Portado del proyecto hermano TripleA_VentasIA (app/audit/models.py +
app/audit/utils.py, 28/08/2026). Ese proyecto usa una
tabla SQL (audit_logs) porque tiene una base de datos propia de aplicación.
VicMar Data AI no la tiene: `security_config.json` ES el almacén de usuarios (ver
main.py: _load_security_config/_save_security_config), así que este registro
sigue el mismo patrón de archivo JSON que ya usan memoria_empresa.py y
password_reset.py — de solo-anexado, con un tope de eventos para no crecer
sin límite.

ALMACENAMIENTO (30/08/2026)
---------------------------
Hasta el 30/08/2026 el registro vivía solo en `CACHE_DIR/audit_log.json`, un
archivo en el disco local del contenedor. En Cloud Run eso no sirve: el disco
es efímero (se pierde al escalar a cero) y cada instancia tiene el suyo
(los eventos se reparten entre instancias y quedan invisibles a medias).

Por eso ahora, igual que hace `user_store.py` con los usuarios, si se define
`AUDIT_GCS_BUCKET` (o `USER_STORE_GCS_BUCKET` como respaldo) el registro se
guarda en un objeto JSON de Google Cloud Storage: compartido entre instancias
y persistente entre reinicios. Si no hay bucket configurado, se sigue usando
el archivo local de siempre (desarrollo sin cambios).

QUÉ REGISTRA
------------
Login, creación/edición/eliminación de usuarios, cambios de perfil propio
(correo, contraseña, foto) y exportaciones — los mismos tipos de evento que
TripleA_VentasIA, con el mismo vocabulario en español (acción/entidad) para
que el registro se lea igual de claro.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone

from config import CACHE_DIR

logger = logging.getLogger(__name__)

# ── Almacén: GCS si hay bucket, archivo local si no ─────────────────────────
# Se reutiliza el mismo bucket de usuarios para no multiplicar infraestructura;
# el objeto de auditoría es distinto (`audit_log.json`). Se puede apuntar a un
# bucket dedicado con AUDIT_GCS_BUCKET si algún día se quiere separar.
GCS_BUCKET = (
    os.getenv("AUDIT_GCS_BUCKET")
    or os.getenv("USER_STORE_GCS_BUCKET")
    or ""
).strip()
GCS_OBJETO = (os.getenv("AUDIT_GCS_OBJECT") or "audit_log.json").strip()

# Cuántos segundos se puede reutilizar la copia en memoria del registro remoto.
# Con el archivo local no se usa: ahí se detecta el cambio por fecha de
# modificación y la lectura es directa.
TTL_CACHE_REMOTO_S = float(os.getenv("AUDIT_CACHE_TTL", "5"))

_ARCHIVO = CACHE_DIR / "audit_log.json"
_LOCK = threading.Lock()
MAX_EVENTOS = 5000

# Caché del registro remoto (GCS): {eventos, ts}. Sirve para no descargar el
# objeto en cada evento ni perder las escrituras hechas por esta misma instancia
# entre un guardado y el siguiente.
_cache = {"eventos": None, "ts": 0.0}

ENTIDAD_USUARIO = "usuario"
ENTIDAD_AUTH = "autenticación"
ENTIDAD_EMPRESA = "empresa"
ENTIDAD_VENTA = "venta"

ACCION_CREAR = "crear"
ACCION_EDITAR = "editar"
ACCION_ELIMINAR = "eliminar"
ACCION_ACTIVAR = "activar"
ACCION_DESACTIVAR = "desactivar"
ACCION_LOGIN = "login"
ACCION_LOGOUT = "logout"
ACCION_EXPORTAR = "exportar"
ACCION_CONSULTAR = "consultar"


def _cliente_gcs():
    """Cliente de Cloud Storage (import diferido: en local sin bucket no se
    instala/carga la librería y la app sigue arrancando sin ella)."""
    from google.cloud import storage

    return storage.Client()


def _descargar_remoto() -> list[dict]:
    bucket = _cliente_gcs().bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_OBJETO)
    datos = blob.download_as_bytes()
    if not datos:
        return []
    parsed = json.loads(datos.decode("utf-8"))
    return parsed if isinstance(parsed, list) else []


def _subir_remoto(eventos: list[dict]) -> None:
    bucket = _cliente_gcs().bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_OBJETO)
    blob.upload_from_string(
        json.dumps(eventos, ensure_ascii=False, indent=2),
        content_type="application/json",
    )


def _leer() -> list[dict]:
    """Devuelve los eventos. NO toma `_LOCK`: lo toma quien llama.

    `_LOCK` es un `threading.Lock` normal (no reentrante), así que si esta
    función lo pidiera por su cuenta, `registrar()` — que ya lo mantiene
    tomado mientras lee, anexa y escribe — se quedaría bloqueada para siempre
    contra sí misma. Mismo criterio que `user_store.py`: el candado vive en
    las funciones públicas, nunca en las auxiliares.
    """
    if GCS_BUCKET:
        ahora = time.time()
        if _cache["eventos"] is None or (ahora - _cache["ts"] > TTL_CACHE_REMOTO_S):
            try:
                _cache["eventos"] = _descargar_remoto()
            except Exception:
                # Sin red / sin objeto aún: el registro empieza vacío. La
                # auditoría nunca tumba la acción que está registrando.
                _cache["eventos"] = []
            _cache["ts"] = ahora
        return list(_cache["eventos"])
    if not _ARCHIVO.exists():
        return []
    try:
        with open(_ARCHIVO, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, list) else []
    except Exception:
        return []


def _escribir(eventos: list[dict]) -> None:
    """Persiste los eventos. Igual que `_leer`, NO toma `_LOCK`."""
    try:
        if GCS_BUCKET:
            _subir_remoto(eventos)
            _cache["eventos"] = list(eventos)
            _cache["ts"] = time.time()
            return
        CACHE_DIR.mkdir(exist_ok=True)
        with open(_ARCHIVO, "w", encoding="utf-8") as f:
            json.dump(eventos, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("[AUDIT] No se pudo persistir el registro")
        pass


def registrar(
    *,
    username: str,
    accion: str,
    entidad: str,
    nombre: str = "",
    entidad_id: str = "",
    entidad_desc: str = "",
    detalle: str = "",
    ip: str = "",
) -> None:
    """
    Anexa un evento. Nunca lanza: la auditoría no puede tumbar la acción real
    que está registrando (mismo criterio que log_action() en VentasIA, que
    envuelve todo en try/except).
    """
    try:
        evento = {
            "id": uuid.uuid4().hex[:12],
            "fecha": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "username": username or "sistema",
            "nombre": nombre or username or "Sistema",
            "accion": accion,
            "entidad": entidad,
            "entidad_id": entidad_id,
            "entidad_desc": entidad_desc,
            "detalle": detalle,
            "ip": ip or "",
        }
        with _LOCK:
            eventos = _leer()
            eventos.append(evento)
            if len(eventos) > MAX_EVENTOS:
                eventos = eventos[-MAX_EVENTOS:]
            _escribir(eventos)
    except Exception:
        pass


def listar(
    q: str = "",
    accion: str = "",
    entidad: str = "",
    desde: str = "",
    hasta: str = "",
    limite: int = 500,
) -> list[dict]:
    """Más reciente primero. `desde`/`hasta` son 'YYYY-MM-DD'."""
    with _LOCK:
        eventos = _leer()
    q_norm = q.strip().lower()

    def coincide(ev: dict) -> bool:
        if accion and ev.get("accion") != accion:
            return False
        if entidad and ev.get("entidad") != entidad:
            return False
        if desde and ev.get("fecha", "") < desde:
            return False
        if hasta and ev.get("fecha", "") > f"{hasta}T23:59:59":
            return False
        if q_norm:
            texto = " ".join([
                str(ev.get("username", "")), str(ev.get("nombre", "")),
                str(ev.get("entidad_desc", "")), str(ev.get("detalle", "")),
            ]).lower()
            if q_norm not in texto:
                return False
        return True

    filtrados = [ev for ev in eventos if coincide(ev)]
    filtrados.sort(key=lambda e: e.get("fecha", ""), reverse=True)
    return filtrados[:limite]


def estadisticas() -> dict:
    with _LOCK:
        eventos = _leer()
    return {
        "total": len(eventos),
        "creaciones": sum(1 for e in eventos if e.get("accion") == ACCION_CREAR),
        "ediciones": sum(1 for e in eventos if e.get("accion") == ACCION_EDITAR),
        "eliminaciones": sum(1 for e in eventos if e.get("accion") == ACCION_ELIMINAR),
        "logins": sum(1 for e in eventos if e.get("accion") == ACCION_LOGIN),
    }
