"""
core/password_reset.py — Códigos de un solo uso para "Olvidé mi contraseña".

No existe una tabla de usuarios en base de datos: security_config.json ES el
almacén de usuarios (ver main.py: _load_security_config/_save_security_config).
Por eso tampoco hay una tabla de tokens de recuperación — se guardan en un
JSON pequeño en el mismo directorio de caché que ya usa el resto del backend
(memoria_empresa.py, query_cache.py...).

Cada código es numérico de 6 dígitos, vive 15 minutos, es de un solo uso y se
guarda hasheado (SHA-256): igual que la contraseña real nunca se guarda en
texto plano, tampoco este código que la controla.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time

from config import CACHE_DIR

_ARCHIVO = CACHE_DIR / "password_reset_codes.json"
_LOCK = threading.Lock()

CODIGO_TTL_SEG = 15 * 60
REENVIO_MIN_SEG = 60
MAX_INTENTOS = 5


def _hash(codigo: str) -> str:
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()


def _clave(username: str) -> str:
    return str(username or "").strip().lower()


def _leer() -> dict:
    if not _ARCHIVO.exists():
        return {}
    try:
        with open(_ARCHIVO, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except Exception:
        return {}


def _escribir(datos: dict) -> None:
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        with open(_ARCHIVO, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def puede_reenviar(username: str) -> bool:
    """¿Ya pasó el tiempo mínimo desde el último código emitido a este
    usuario? Evita que alguien reenvíe códigos en bucle."""
    entrada = _leer().get(_clave(username))
    if not entrada:
        return True
    return (time.time() - entrada.get("emitido_en", 0)) >= REENVIO_MIN_SEG


def generar_codigo(username: str) -> str:
    """Genera y persiste un código nuevo de 6 dígitos para `username`.
    Devuelve el código en claro solo para enviarlo por correo — nunca se
    vuelve a leer en claro desde el archivo."""
    clave = _clave(username)
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    with _LOCK:
        datos = _leer()
        datos[clave] = {
            "hash": _hash(codigo),
            "expira_en": time.time() + CODIGO_TTL_SEG,
            "emitido_en": time.time(),
            "intentos": 0,
        }
        _escribir(datos)
    return codigo


def verificar_y_consumir(username: str, codigo: str) -> tuple[bool, str]:
    """
    Valida el código para `username`. Si es correcto lo invalida de
    inmediato (un solo uso) y devuelve (True, ""). Si no, devuelve
    (False, motivo) sin revelar más detalle del necesario.
    """
    clave = _clave(username)
    codigo_limpio = str(codigo or "").strip()
    with _LOCK:
        datos = _leer()
        entrada = datos.get(clave)
        if not entrada:
            return False, "No hay un código de recuperación pendiente para este usuario."
        if time.time() > entrada.get("expira_en", 0):
            datos.pop(clave, None)
            _escribir(datos)
            return False, "El código expiró. Solicita uno nuevo."
        if entrada.get("intentos", 0) >= MAX_INTENTOS:
            datos.pop(clave, None)
            _escribir(datos)
            return False, "Demasiados intentos fallidos. Solicita un código nuevo."
        if _hash(codigo_limpio) != entrada.get("hash"):
            entrada["intentos"] = entrada.get("intentos", 0) + 1
            _escribir(datos)
            return False, "El código no es correcto."

        datos.pop(clave, None)
        _escribir(datos)
        return True, ""
