"""
cache/query_cache.py — Sistema de Caché Inteligente (v2 Gold)
Gestiona el aprendizaje del sistema mediante el almacenamiento de consultas exitosas.
Utiliza un sistema híbrido: Redis para velocidad extrema y JSON para persistencia local.
Garantiza que el cerebro no trabaje dos veces en la misma lógica SQL.
"""
import json
import unicodedata
import re
import pathlib
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

# Configuración y Almacén (v2)
from config import CACHE_FILE
from cache.redis_manager import REDIS_STORE


def normalize_key(question: str, db_name: str) -> str:
    """
    Genera una clave de caché reproducible:
    - Sin acentos, sin puntuación, minúsculas
    - Prefijada por nombre de BD para que dos BD diferentes no colisionen
    """
    # Quitar acentos
    s = ''.join(
        c for c in unicodedata.normalize('NFD', question)
        if unicodedata.category(c) != 'Mn'
    )
    # Quitar puntuación
    s = re.sub(r'[?!¿¡.,;:]', '', s)
    s = s.lower().strip()
    return f"{db_name}__{s}"


def _json_default(o):
    """Serializa tipos no-JSON (Decimal, fechas) que vienen en datos SQL."""
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def load_cache() -> dict:
    """Carga el caché desde disco. Retorna dict vacío si no existe o está corrupto."""
    try:
        if pathlib.Path(CACHE_FILE).exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[CACHE] Error cargando caché: {e}")
    return {}


def save_cache(data: dict) -> None:
    """Persiste el caché en disco de forma segura."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)
    except Exception as e:
        print(f"[CACHE] Error guardando caché: {e}")


def get_cached(question: str, db_name: str) -> Optional[dict]:
    """
    Busqueda multinivel:
    1. Intenta Redis (Caché caliente).
    2. Si falla o no está disponible, intenta JSON (Caché fría).
    """
    key = normalize_key(question, db_name)
    
    # Intento 1: REDIS (v2 Gold)
    # Es la vía más rápida, ideal para sistemas distribuidos.
    if REDIS_STORE.ensure_connected():
        entry = REDIS_STORE.get(key)
        if entry:
            print(f"[CACHE HIT REDIS] '{question[:40]}...'")
            return entry

    # Intento 2: JSON (Fallback / Legacy)
    # Útil para entornos de desarrollo o sin infraestructura pesada.
    cache = load_cache()
    entry = cache.get(key)
    if entry:
        print(f"[CACHE HIT JSON] '{question[:40]}...'")
    return entry


def set_cached(question: str, db_name: str, entry: dict, ttl: int = None) -> None:
    """
    Persistencia de aprendizaje:
    - Siempre escribe en Redis si está activo.
    - Sincroniza con JSON solo si Redis está deshabilitado para reducir I/O.
    - `ttl` (segundos) permite a un llamador pedir una expiración más corta
      que la de config.CACHE_TTL — útil para respuestas completas de negocio
      que no deberían quedar "congeladas" tanto tiempo como un SQL aprendido.
    """
    key = normalize_key(question, db_name)

    # Escritura en REDIS (v2 Gold)
    if REDIS_STORE.ensure_connected():
        REDIS_STORE.set(key, entry, ttl=ttl)
        print(f"[CACHE SAVED REDIS] Aprendido: '{question[:40]}'")
    else:
        # Solo escribir en disco si no tenemos la potencia de Redis
        cache = load_cache()
        cache[key] = entry
        save_cache(cache)
        print(f"[CACHE SAVED JSON] Aprendido: '{question[:40]}'")


def clear_cache() -> int:
    """Limpia todo el caché. Retorna cantidad de entradas eliminadas."""
    cache = load_cache()
    count = len(cache)
    save_cache({})
    print(f"[CACHE CLEARED] {count} entradas eliminadas.")
    return count


def invalidate_key(question: str, db_name: str) -> bool:
    """Elimina una entrada específica del caché."""
    key = normalize_key(question, db_name)
    cache = load_cache()
    if key in cache:
        del cache[key]
        save_cache(cache)
        return True
    return False
    
