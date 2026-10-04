"""
cache/redis_manager.py — Almacén de Datos Calientes (v2 Gold)
Gestiona la conexión y operaciones con Redis para caché distribuida.
Si Redis no está disponible, el sistema degrada con elegancia a un estado local.
"""
import redis
import json
from datetime import date, datetime
from decimal import Decimal
from config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, CACHE_TTL


def _json_default(o):
    """Serializa tipos no-JSON (Decimal, fechas) que vienen en datos SQL."""
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


class RedisManager:
    """
    Controlador de Redis con patrón Singleton y manejo de fallos proactivo.
    """
    _instance = None

    def __new__(cls):
        # Singleton para mantener una sola conexion por proceso.
        # Evita reconexiones repetidas en cada llamada de cache.
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.enabled = False
            cls._instance._connect_attempted = False
        return cls._instance

    def ensure_connected(self) -> bool:
        """
        Inicializa Redis bajo demanda para no frenar el arranque del sistema.
        """
        if self.enabled:
            return True
        if self._connect_attempted:
            return False
        self._connect_attempted = True
        self._connect()
        return self.enabled

    def _connect(self):
        """
        Intenta establecer el enlace con el nodo de Redis.
        """
        if not str(REDIS_HOST or "").strip():
            self.client = None
            self.enabled = False
            print("[REDIS] Host no configurado. Cache distribuida deshabilitada.")
            return
        try:
            self.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=0.35,
                socket_timeout=0.6,
                retry_on_timeout=False,
                health_check_interval=30,
            )
            # Verificar latencia
            self.client.ping()
            self.enabled = True
            print(f"[REDIS] Enlace establecido en {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            self.client = None
            self.enabled = False
            print(f"[REDIS] Nodo no disponible. Continuando en modo 'Local-Memory Cache'. Error: {e}")

    def get(self, key: str):
        """Recupera un valor serializado."""
        if not self.ensure_connected():
            return None
        try:
            val = self.client.get(key)
            return json.loads(val) if val else None
        except:
            return None

    def set(self, key: str, value, ttl: int = None):
        """Almacena un objeto serializado con tiempo de vida."""
        if not self.ensure_connected():
            return False
        try:
            ttl = ttl or CACHE_TTL
            self.client.set(key, json.dumps(value, default=_json_default), ex=ttl)
            return True
        except:
            return False

    def delete(self, key: str):
        """Elimina una entrada de la caché."""
        if not self.ensure_connected():
            return
        try:
            self.client.delete(key)
        except:
            pass

# Instancia global para consumo del sistema
REDIS_STORE = RedisManager()
