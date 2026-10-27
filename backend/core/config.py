# -*- coding: utf-8 -*-
"""
Configuración central del backend.

Lee backend/.env una sola vez y expone valores tipados. Ningún secreto vive en
el código: si falta una contraseña, el componente que la necesita se detiene
con un mensaje claro (falla cerrada) en lugar de usar un valor por defecto.

Requerimientos que implementa: RNF-02 (mínimo privilegio y aislamiento), RNF-10
    (portabilidad).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ_BACKEND / '.env', override=False)


def _texto(nombre: str, defecto: str = '') -> str:
    return (os.getenv(nombre) or defecto).strip()


def _entero(nombre: str, defecto: int) -> int:
    try:
        return int(_texto(nombre, str(defecto)))
    except ValueError:
        return defecto


def _booleano(nombre: str, defecto: bool) -> bool:
    """Interpreta yes/no, true/false, si/no, 1/0; cualquier otro valor usa el defecto."""
    valor = _texto(nombre).lower()
    if valor in ('yes', 'true', 'si', 'sí', '1', 'on'):
        return True
    if valor in ('no', 'false', '0', 'off'):
        return False
    return defecto


def _decimal(nombre: str, defecto: float) -> float:
    try:
        return float(_texto(nombre, str(defecto)))
    except ValueError:
        return defecto


@dataclass(frozen=True)
class ProveedorIA:
    """Un proveedor de modelos de lenguaje con API compatible con OpenAI."""

    nombre: str
    clave: str
    url_base: str
    modelo: str

    @property
    def disponible(self) -> bool:
        return bool(self.clave and self.modelo)


@dataclass(frozen=True)
class Configuracion:
    """Valores de configuración del sistema, leídos de backend/.env."""

    entorno: str = field(default_factory=lambda: _texto('APP_ENV', 'development').lower())

    # SQL Server
    db_host: str = field(default_factory=lambda: _texto('DB_HOST', 'localhost,1433'))
    db_driver: str = field(default_factory=lambda: _texto('DB_DRIVER', 'ODBC Driver 18 for SQL Server'))
    db_usuario_admin: str = field(default_factory=lambda: _texto('DB_USER', 'sa'))
    db_clave_admin: str = field(default_factory=lambda: _texto('DB_PASSWORD'))
    # La conexión siempre va cifrada (Encrypt=yes). Aceptar el certificado
    # autofirmado del contenedor solo ocurre si DB_TRUST_SERVER_CERT lo permite;
    # sin la variable se acepta en desarrollo y se rechaza en producción.
    db_confiar_certificado: bool = field(default_factory=lambda: _booleano(
        'DB_TRUST_SERVER_CERT', _texto('APP_ENV', 'development').lower() != 'production'))
    almacen: str = field(default_factory=lambda: _texto('ALMACEN_DB', 'ALMACEN_ACADEMICO'))
    lector_usuario: str = field(default_factory=lambda: _texto('CHAT_READER_USER', 'chat_reader'))
    lector_clave: str = field(default_factory=lambda: _texto('CHAT_READER_PASSWORD'))
    seguimiento_usuario: str = field(default_factory=lambda: _texto('APP_SEGUIMIENTO_USER', 'app_seguimiento'))
    seguimiento_clave: str = field(default_factory=lambda: _texto('APP_SEGUIMIENTO_PASSWORD'))
    tiempo_maximo_consulta_s: int = field(default_factory=lambda: _entero('TIEMPO_MAXIMO_CONSULTA_S', 30))

    # Seguridad
    jwt_clave: str = field(default_factory=lambda: _texto('JWT_SECRET_KEY', 'solo-desarrollo-cambiar'))
    jwt_algoritmo: str = field(default_factory=lambda: _texto('ALGORITHM', 'HS256'))
    jwt_minutos: int = field(default_factory=lambda: _entero('ACCESS_TOKEN_EXPIRE_MINUTES', 480))
    origenes_permitidos: tuple[str, ...] = field(default_factory=lambda: tuple(
        o.strip() for o in _texto(
            'ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173').split(',')
        if o.strip()))
    ruta_usuarios: Path = field(default_factory=lambda: Path(
        _texto('RUTA_USUARIOS', str(RAIZ_BACKEND / 'datos_locales' / 'usuarios.json'))))
    ruta_auditoria: Path = field(default_factory=lambda: Path(
        _texto('RUTA_AUDITORIA', str(RAIZ_BACKEND / 'datos_locales' / 'auditoria.jsonl'))))

    # Modelos de lenguaje (cascada: el primero disponible responde)
    # CONSULTA_INTERPRETAR=0 deshabilita la lectura con IA de los resultados (las filas, aunque
    # seudonimizadas, no salen del país). Política de gobierno de datos, sección 7.
    interpretar_con_ia: bool = field(default_factory=lambda: _texto('CONSULTA_INTERPRETAR', '1') != '0')
    temperatura: float = field(default_factory=lambda: _decimal('LLM_TEMPERATURE', 0.0))
    max_tokens: int = field(default_factory=lambda: _entero('LLM_MAX_TOKENS', 1600))
    tiempo_maximo_llm_s: int = field(default_factory=lambda: _entero('TIEMPO_MAXIMO_LLM_S', 45))

    @property
    def proveedores_ia(self) -> list[ProveedorIA]:
        """Cascada de proveedores, en orden: gratuitos primero, de pago al final."""
        return [
            ProveedorIA('Gemini', _texto('GEMINI_API_KEY'),
                        'https://generativelanguage.googleapis.com/v1beta/openai/',
                        _texto('GEMINI_MODEL', 'gemini-3.8-flash')),
            ProveedorIA('Groq', _texto('GROQ_API_KEY'), 'https://api.groq.com/openai/v1',
                        _texto('GROQ_MODEL', 'openai/gpt-oss-120b')),
            ProveedorIA('NVIDIA NIM', _texto('NVIDIA_API_KEY'), 'https://integrate.api.nvidia.com/v1',
                        _texto('NVIDIA_MODEL', 'moonshotai/kimi-k3')),
            ProveedorIA('DeepSeek', _texto('DEEPSEEK_API_KEY'),
                        _texto('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'),
                        _texto('DEEPSEEK_MODEL', 'deepseek-v4-flash').lower()),
        ]

    def validar_produccion(self) -> None:
        """Impide arrancar en producción con la llave JWT de desarrollo."""
        if self.entorno == 'production' and self.jwt_clave in ('', 'solo-desarrollo-cambiar'):
            raise RuntimeError('Define JWT_SECRET_KEY en backend/.env antes de usar APP_ENV=production.')


CONFIG = Configuracion()
