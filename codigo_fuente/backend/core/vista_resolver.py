"""
Detección en vivo del nombre real de una vista del esquema CHAT.

CHAT es un espacio de vistas compartido por todo el servidor y el procedimiento
SP_MODIFICA_VISTA_IA (fuera de este repositorio) puede desplegar la vista de
ventas como «Ventas» o «cabecera_factura» según la empresa o el momento. Fijar
un nombre en el código solo cambia cuál se rompe; por eso se prueba en cada uso
qué candidato responde. Centraliza la lógica que usan mirror_manager.py,
main.py y api/routes_query.py.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

# Hay dos variantes de detección porque el proyecto habla con la base de dos
# formas: con una Connection de SQLAlchemy ya abierta (mirror_manager.py,
# main.py) o con el connector de alto nivel (api/routes_query.py).
#
# «Ventas»/«Compras» van primero porque son los nombres que el servidor tiene
# desplegados actualmente. «cabecera_factura»/«cabecera_compra» quedan como
# segundo intento por si el servidor vuelve a desplegar el nombre genérico; un
# SQL con un nombre inexistente falla con «objeto no válido».
CANDIDATOS_VENTAS = ("Ventas", "cabecera_factura")
CANDIDATOS_COMPRAS = ("Compras", "cabecera_compra")


def detectar_vista_sqlalchemy(connection, candidatos: tuple[str, ...], target_db: str = "CHAT") -> str | None:
    """Devuelve el primer nombre de `candidatos` que responde en `target_db`, o None.

    Usa una Connection de SQLAlchemy ya abierta.
    """
    from sqlalchemy import text

    for candidato in candidatos:
        try:
            connection.execute(text(f"SELECT TOP 1 1 FROM [{target_db}].[dbo].[{candidato}]")).fetchone()
            return candidato
        except Exception:
            continue
    return None


def detectar_vista_connector(connector, candidatos: tuple[str, ...], target_db: str = "CHAT") -> str | None:
    """Hace la misma detección que `detectar_vista_sqlalchemy` vía connector.execute_query."""
    if connector is None:
        return None
    for candidato in candidatos:
        try:
            _cols, _rows, err = connector.execute_query(
                f"SELECT TOP 1 1 FROM [{target_db}].[dbo].[{candidato}]", target_db=target_db
            )
            if not err:
                return candidato
        except Exception:
            continue
    return None
