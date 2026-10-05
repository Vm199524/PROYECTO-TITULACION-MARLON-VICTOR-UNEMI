# -*- coding: utf-8 -*-
"""
Conexión administrativa para los procesos por lotes.

Única función de conexión de seed, ETL, entrenamiento, calificación, clustering
y benchmarking. Lee las credenciales solo de backend/.env (vía config.py) y, si
falta la contraseña, se detiene con un mensaje claro: un valor por defecto en el
código dejaría la credencial en el repositorio y podría hacer que un script
corra en silencio contra el servidor equivocado. Esta conexión nunca ejecuta SQL
generado por la IA; eso pasa por la cuenta de solo lectura chat_reader
(main.py::execute_chat_query).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import os

import pyodbc

from config import DEFAULT_HOST, DEFAULT_PASSWORD, DEFAULT_USER

DRIVER_POR_DEFECTO = 'ODBC Driver 18 for SQL Server'


class CredencialesFaltantes(RuntimeError):
    """Se lanza cuando no hay contraseña de base de datos configurada."""
    pass


def _driver() -> str:
    """Devuelve el driver de DB_DRIVER, o ODBC Driver 18 si falta o vale AUTO."""
    env = (os.getenv('DB_DRIVER') or '').strip()
    return env if env and env.upper() != 'AUTO' else DRIVER_POR_DEFECTO


def resolver_credenciales(host: str | None = None, user: str | None = None,
                          password: str | None = None) -> tuple[str, str, str]:
    """Completa host, usuario y contraseña con los valores de backend/.env.

    Sin host ni usuario usa 'localhost,1433' y 'sa'; la contraseña nunca tiene
    valor por defecto.

    Returns:
        Tupla (host, usuario, contraseña).

    Raises:
        CredencialesFaltantes: si no hay contraseña en los argumentos ni en el .env.
    """
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
    """Abre una conexión pyodbc a `database` con las credenciales administrativas.

    Los argumentos vacíos se completan con resolver_credenciales() y _driver().

    Raises:
        CredencialesFaltantes: si no hay contraseña configurada.
    """
    host, user, password = resolver_credenciales(host, user, password)
    conn_str = (
        f"DRIVER={{{driver or _driver()}}};SERVER={host};DATABASE={database};"
        f"UID={user};PWD={password};TrustServerCertificate=yes;Encrypt=no;"
    )
    return pyodbc.connect(conn_str, timeout=timeout, autocommit=autocommit)
