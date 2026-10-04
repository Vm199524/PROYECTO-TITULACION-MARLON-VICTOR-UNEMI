# -*- coding: utf-8 -*-
"""
conexion_admin.py — conexión ADMINISTRATIVA para los procesos por lotes
(seed, ETL, entrenamiento, calificación, clustering, benchmarking).

Antes cada script tenía su propia función `conectar()` con la contraseña de
`sa` escrita como valor por defecto "por si no hay .env". Eso dejaba la
credencial en el código fuente (y en el historial de git) y, peor, hacía que
un script corriera en silencio contra el servidor equivocado. Ahora hay una
sola función: lee backend/.env (vía config.py) y, si falta la contraseña,
se detiene con un mensaje claro en vez de adivinar.

Esta conexión NUNCA se usa para ejecutar SQL generado por la IA — eso pasa
siempre por la cuenta de solo lectura chat_reader (main.py::execute_chat_query).
"""
from __future__ import annotations

import os

import pyodbc

from config import DEFAULT_HOST, DEFAULT_PASSWORD, DEFAULT_USER

DRIVER_POR_DEFECTO = 'ODBC Driver 18 for SQL Server'


class CredencialesFaltantes(RuntimeError):
    pass


def _driver() -> str:
    env = (os.getenv('DB_DRIVER') or '').strip()
    return env if env and env.upper() != 'AUTO' else DRIVER_POR_DEFECTO


def resolver_credenciales(host: str | None = None, user: str | None = None,
                          password: str | None = None) -> tuple[str, str, str]:
    host = host or DEFAULT_HOST or 'localhost,1433'
    user = user or DEFAULT_USER or 'sa'
    password = password or DEFAULT_PASSWORD
    if not password:
        raise CredencialesFaltantes(
            "No hay contraseña de base de datos. Define DB_PASSWORD en backend/.env "
            "(ver backend/.env.example) o pásala con --password."
        )
    return host, user, password


def conectar_admin(database: str, host: str | None = None, user: str | None = None,
                   password: str | None = None, driver: str | None = None,
                   timeout: int = 15, autocommit: bool = False) -> pyodbc.Connection:
    host, user, password = resolver_credenciales(host, user, password)
    conn_str = (
        f"DRIVER={{{driver or _driver()}}};SERVER={host};DATABASE={database};"
        f"UID={user};PWD={password};TrustServerCertificate=yes;Encrypt=no;"
    )
    return pyodbc.connect(conn_str, timeout=timeout, autocommit=autocommit)
