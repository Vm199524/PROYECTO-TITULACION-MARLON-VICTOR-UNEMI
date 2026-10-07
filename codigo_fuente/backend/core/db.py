# -*- coding: utf-8 -*-
"""
Acceso a SQL Server con tres cuentas de privilegio distinto.

  - Administración (DB_USER): solo para los procesos por lotes (carga de
    datos, ETL, entrenamiento, calificación). Nunca ejecuta SQL de la IA ni
    atiende peticiones de usuarios.
  - Lectura gobernada (chat_reader): atiende TODAS las lecturas de la API,
    tanto del panel como de la consulta conversacional. Antes de cada SELECT
    fija SESSION_CONTEXT('institucion_activa') en la MISMA conexión, de modo
    que las vistas VIS_* solo devuelven filas de esa institución. Si la cuenta
    no está configurada, la lectura se rechaza (falla cerrada): jamás se
    sustituye por la cuenta de administración.
  - Seguimiento (app_seguimiento): solo ejecuta los procedimientos que
    registran y cierran intervenciones de bienestar estudiantil.

Que el panel y el chat lean por la misma cuenta y las mismas vistas garantiza
que nunca muestren cifras distintas.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import datetime as dt
import decimal
import re
from contextlib import contextmanager
from typing import Any, Iterator

from core.config import CONFIG


class ErrorBaseDatos(RuntimeError):
    """Error de base de datos con un mensaje apto para el usuario final."""


class CuentaNoConfigurada(ErrorBaseDatos):
    """La cuenta requerida no tiene contraseña en backend/.env."""


_CODIGO_INSTITUCION = re.compile(r'^[A-Z0-9_]{2,30}$')


def _pyodbc():
    import pyodbc  # importación diferida: las pruebas unitarias no necesitan el driver
    return pyodbc


def _cadena(usuario: str, clave: str, base: str) -> str:
    return (f"DRIVER={{{CONFIG.db_driver}}};SERVER={CONFIG.db_host};DATABASE={base};"
            f"UID={usuario};PWD={clave};TrustServerCertificate=yes;Encrypt=no;")


def conectar_admin(base: str | None = None, autocommit: bool = False, tiempo: int = 30):
    """Conexión administrativa para procesos por lotes.

    Raises:
        CuentaNoConfigurada: si DB_PASSWORD no está en backend/.env.
    """
    if not CONFIG.db_clave_admin:
        raise CuentaNoConfigurada('Falta DB_PASSWORD en backend/.env (ver .env.example).')
    return _pyodbc().connect(_cadena(CONFIG.db_usuario_admin, CONFIG.db_clave_admin, base or CONFIG.almacen),
                             timeout=tiempo, autocommit=autocommit)


def validar_institucion(codigo: str) -> str:
    """Normaliza y valida un código de institución (solo A-Z, 0-9 y _)."""
    codigo = (codigo or '').strip().upper()
    if not _CODIGO_INSTITUCION.match(codigo):
        raise ErrorBaseDatos('Código de institución no válido.')
    return codigo


def _a_json(valor: Any) -> Any:
    """Convierte los tipos de pyodbc a tipos serializables en JSON."""
    if isinstance(valor, decimal.Decimal):
        return float(valor)
    if isinstance(valor, (dt.datetime, dt.date)):
        return valor.isoformat()
    if isinstance(valor, bytes):
        return valor.hex()
    return valor


def _traducir_error(exc: Exception) -> str:
    texto = str(exc)
    bajo = texto.lower()
    if 'timeout' in bajo or 'expired' in bajo:
        return (f'La consulta tardó más de {CONFIG.tiempo_maximo_consulta_s} segundos y se detuvo. '
                'Prueba acotarla a una carrera, un periodo o menos resultados.')
    if 'permission was denied' in bajo or 'denegado' in bajo or '229' in texto:
        return 'Permiso denegado: la consulta intentó leer un objeto que no está autorizado.'
    if 'login failed' in bajo or '18456' in texto:
        return 'No se pudo iniciar sesión en la base de datos con la cuenta de lectura.'
    if 'invalid column name' in bajo or 'nombre de columna' in bajo:
        return 'La consulta usa una columna que no existe en las vistas autorizadas.'
    if 'invalid object name' in bajo:
        return 'La consulta usa una tabla o vista que no existe o no está autorizada.'
    return 'La base de datos rechazó la consulta.'


@contextmanager
def _conexion_con_contexto(usuario: str, clave: str, institucion: str) -> Iterator[Any]:
    """Abre una conexión, fija la institución en SESSION_CONTEXT y la cierra al salir."""
    if not clave:
        raise CuentaNoConfigurada(
            f'La cuenta {usuario} no está configurada en backend/.env; por seguridad la '
            'operación no se ejecuta con otra cuenta.')
    institucion = validar_institucion(institucion)
    conn = _pyodbc().connect(_cadena(usuario, clave, CONFIG.almacen), timeout=15, autocommit=True)
    try:
        conn.timeout = CONFIG.tiempo_maximo_consulta_s
        cur = conn.cursor()
        # @read_only = 1: ninguna sentencia posterior de la misma conexión puede cambiar la institución.
        cur.execute("EXEC sp_set_session_context @key = N'institucion_activa', @value = ?, @read_only = 1", institucion)
        yield cur
    finally:
        conn.close()


def leer(sql: str, institucion: str, parametros: tuple | list = ()) -> tuple[list[str], list[list[Any]]]:
    """Ejecuta un SELECT con la cuenta de lectura gobernada.

    Returns:
        (columnas, filas) con valores serializables.

    Raises:
        CuentaNoConfigurada: si chat_reader no tiene contraseña configurada.
        ErrorBaseDatos: si la base rechaza la consulta (mensaje para el usuario).
    """
    try:
        with _conexion_con_contexto(CONFIG.lector_usuario, CONFIG.lector_clave, institucion) as cur:
            cur.execute(sql, *parametros) if parametros else cur.execute(sql)
            if cur.description is None:
                return [], []
            columnas = [c[0] for c in cur.description]
            filas = [[_a_json(v) for v in fila] for fila in cur.fetchall()]
            return columnas, filas
    except ErrorBaseDatos:
        raise
    except Exception as exc:  # noqa: BLE001 - se traduce para no filtrar detalles internos
        raise ErrorBaseDatos(_traducir_error(exc)) from exc


def leer_dicts(sql: str, institucion: str, parametros: tuple | list = ()) -> list[dict[str, Any]]:
    """Igual que leer(), pero devuelve una lista de diccionarios."""
    columnas, filas = leer(sql, institucion, parametros)
    return [dict(zip(columnas, f)) for f in filas]


def ejecutar_seguimiento(procedimiento: str, institucion: str, parametros: tuple) -> list[dict[str, Any]]:
    """Ejecuta uno de los dos procedimientos del registro de seguimiento."""
    if procedimiento not in ('dbo.sp_registrar_intervencion', 'dbo.sp_cerrar_intervencion'):
        raise ErrorBaseDatos('Procedimiento no autorizado.')
    marcadores = ', '.join('?' for _ in parametros)
    try:
        with _conexion_con_contexto(CONFIG.seguimiento_usuario, CONFIG.seguimiento_clave, institucion) as cur:
            cur.execute(f'EXEC {procedimiento} {marcadores}', *parametros)
            if cur.description is None:
                return []
            columnas = [c[0] for c in cur.description]
            return [dict(zip(columnas, [_a_json(v) for v in fila])) for fila in cur.fetchall()]
    except ErrorBaseDatos:
        raise
    except Exception as exc:  # noqa: BLE001
        mensaje = str(exc)
        if any(codigo in mensaje for codigo in ('50001', '50002', '50003', '50004')):
            m = re.search(r'\[SQL Server\](.*?)\s*\(\d+\)', mensaje)
            raise ErrorBaseDatos(m.group(1).strip() if m else 'Operación rechazada por la base de datos.') from exc
        raise ErrorBaseDatos(_traducir_error(exc)) from exc
