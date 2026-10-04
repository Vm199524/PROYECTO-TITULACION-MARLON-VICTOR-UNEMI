"""
Archivo: bi_snapshot_store.py
Rol: almacén persistente de los snapshots del Pulso BI por empresa (Capa 2).
Recibe desde: main.py (endpoint /api/bi/pulse y job de refresco).
Se conecta con: la base CHAT del servidor (tabla propia [CHAT].[dbo].[tb_bi_snapshot])
y con config.py (cadencias). NUNCA escribe en las bases ERP (solo lectura allí).

Responsabilidades:
  - Guardar/actualizar el snapshot JSON de una empresa (upsert vía SP).
  - Marcar un fallo de captura para no reintentar en bucle empresas caídas.
  - Leer el snapshot más reciente de una empresa junto con su marca de captura.
  - Serializar los cálculos de pulso (las vistas de CHAT son un namespace
    compartido: dos cálculos concurrentes se pisarían entre sí).

Degradación: si la tabla/SP aún no existen (script SQL no ejecutado), todas
las funciones devuelven "no hay snapshot" y el endpoint calcula en vivo, sin
romper nada.
"""
import datetime as _dt
import json
import logging
import threading

from sqlalchemy import text

try:
    from config import (
        BI_SNAPSHOT_REFRESH_SECONDS,
        BI_SNAPSHOT_SERVE_MAX_AGE_SECONDS,
    )
except Exception:  # pragma: no cover - import independiente durante tests
    BI_SNAPSHOT_REFRESH_SECONDS = 900
    BI_SNAPSHOT_SERVE_MAX_AGE_SECONDS = 1800

logger = logging.getLogger(__name__)

# Un único cálculo de pulso a la vez por proceso. Protege el namespace
# compartido de vistas de CHAT que SP_MODIFICA_VISTA_IA re-apunta por empresa.
PULSE_COMPUTE_LOCK = threading.Lock()

_TABLA = "[CHAT].[dbo].[tb_bi_snapshot]"
_SP_UPSERT = "[CHAT].[dbo].[SP_BI_SNAPSHOT_UPSERT]"
_SP_MARK_FAIL = "[CHAT].[dbo].[SP_BI_SNAPSHOT_MARK_FAIL]"

_MAX_EMPRESA_LEN = 128


def _safe_empresa(empresa: str) -> str:
    """Normaliza el nombre de la empresa a un identificador seguro."""
    nombre = str(empresa or "").strip().upper()
    # Solo caracteres alfanuméricos y subrayado, acotado de largo.
    if not nombre or len(nombre) > _MAX_EMPRESA_LEN or not nombre.replace("_", "").isalnum():
        return ""
    return nombre


def guardar_snapshot(connector, empresa: str, payload: dict, duracion_ms: int = None) -> bool:
    """
    Upsert del snapshot de una empresa en la tabla de CHAT vía SP.
    Devuelve True si se persistió; False si falló (tabla/SP ausente, red, etc).
    """
    nombre = _safe_empresa(empresa)
    if not nombre or not isinstance(payload, dict):
        return False
    if connector is None or getattr(connector, "engine", None) is None:
        return False
    try:
        cuerpo = json.dumps(payload, ensure_ascii=False, default=str)
        # Se guarda SIEMPRE en UTC (naive) para que la edad calculada con
        # datetime.utcnow() sea correcta aunque el servidor SQL tenga otra TZ.
        capturado = _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        with connector.engine.connect() as conn:
            conn.execute(
                text(f"EXEC {_SP_UPSERT} :empresa, :payload, :capturado, :duracion_ms"),
                {
                    "empresa": nombre,
                    "payload": cuerpo,
                    "capturado": capturado,
                    "duracion_ms": int(duracion_ms) if duracion_ms is not None else None,
                },
            )
            conn.commit()
        return True
    except Exception as _e:
        logger.warning("[BI_SNAP] No se pudo guardar snapshot de '%s': %s", nombre, _e)
        return False


def marcar_snapshot_fallido(connector, empresa: str) -> None:
    """Incrementa intentos_fallidos de una empresa (best-effort)."""
    nombre = _safe_empresa(empresa)
    if not nombre or connector is None or getattr(connector, "engine", None) is None:
        return
    try:
        with connector.engine.connect() as conn:
            conn.execute(text(f"EXEC {_SP_MARK_FAIL} :empresa"), {"empresa": nombre})
            conn.commit()
    except Exception:
        pass


def leer_snapshot(connector, empresa: str):
    """
    Lee el snapshot más reciente de una empresa.

    Devuelve (payload_dict, capturado_en_datetime, intentos_fallidos) o
    (None, None, 0) si no existe / la tabla no está desplegada.
    """
    nombre = _safe_empresa(empresa)
    if not nombre or connector is None or getattr(connector, "engine", None) is None:
        return None, None, 0
    try:
        with connector.engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT payload, capturado_en, intentos_fallidos "
                    f"FROM {_TABLA} WITH (NOLOCK) WHERE empresa = :empresa"
                ),
                {"empresa": nombre},
            ).fetchone()
        if row is None:
            return None, None, 0
        capturado = row[1]
        fallos = int(row[2] or 0)
        try:
            payload = json.loads(row[0])
        except Exception:
            return None, capturado, fallos
        return (payload if isinstance(payload, dict) else None), capturado, fallos
    except Exception as _e:
        # La tabla aún no existe (script no corrido) o hubo un problema de red:
        # no es un error fatal, el endpoint calculará en vivo.
        logger.info("[BI_SNAP] Snapshot no disponible para '%s' (¿tabla sin desplegar?): %s", nombre, _e)
        return None, None, 0


def edad_snapshot_segundos(capturado_en) -> float | None:
    """Antigüedad del snapshot en segundos desde su captura. None si no hay dato."""
    if capturado_en is None:
        return None
    try:
        if isinstance(capturado_en, str):
            # Normaliza el posible 'YYYY-MM-DDTHH:MM:SS.mmm' devuelto por pyodbc.
            capturado_en = capturado_en.replace(" ", "T")
            if "." not in capturado_en:
                capturado_en += ".000"
            capturado_en = capturado_en[:23]
        import datetime as _dt

        # pyodbc suele entregar datetime ya; str es solo un salvavidas.
        if isinstance(capturado_en, str):
            capturado_en = _dt.datetime.fromisoformat(capturado_en)
        else:
            # Si llegó un datetime "naive", asumimos hora del servidor (UTC-ish igual
            # a time.time, que es epoch UTC) — consistente con cómo lo escribimos.
            if capturado_en.tzinfo is not None:
                capturado_en = capturado_en.replace(tzinfo=None)
        ahora = _dt.datetime.utcnow()
        return max(0.0, (ahora - capturado_en).total_seconds())
    except Exception:
        return None


def listar_snapshots(connector):
    """
    Devuelve una fila (empresa, capturado_en, intentos_fallidos, bytes_payload)
    por cada snapshot existente. Se usa en GET /api/bi/snapshots/status.
    Vacía si la tabla no está desplegada.
    """
    try:
        if connector is None or getattr(connector, "engine", None) is None:
            return []
        with connector.engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT empresa, capturado_en, intentos_fallidos, "
                    f"DATALENGTH(payload) AS bytes_payload FROM {_TABLA} WITH (NOLOCK)"
                )
            ).fetchall()
        return [(r[0], r[1], int(r[2] or 0), int(r[3] or 0)) for r in rows]
    except Exception as _e:
        logger.info("[BI_SNAP] No se pudo listar snapshots: %s", _e)
        return []


def necesita_refresco(connector, empresa: str, intervalo_seg: int = None) -> bool:
    """True si la empresa no tiene snapshot o tiene más de `intervalo_seg`."""
    intervalo_seg = intervalo_seg if intervalo_seg is not None else BI_SNAPSHOT_REFRESH_SECONDS
    _, capturado, fallos = leer_snapshot(connector, empresa)
    if capturado is None:
        # Sin snapshot previo: sí necesita refresco (a menos que lleve muchos
        # fallos seguidos, para no martillar una empresa caída).
        if fallos >= 5:
            logger.info("[BI_SNAP] '%s' lleva %d fallos; se omite hasta que un cálculo en vivo lo recupere.", empresa, fallos)
            return False
        return True
    edad = edad_snapshot_segundos(capturado)
    return edad is None or edad >= intervalo_seg
