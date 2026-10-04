"""
core/vista_resolver.py — Detección en vivo del nombre real de una vista de CHAT.

PROBLEMA QUE RESUELVE
----------------------
Todo el sistema (metric_catalog.json, el fallback de Balance Comercial, las
tarjetas de Reportes BI) asumía que la vista de ventas de CHAT se llama
siempre "cabecera_factura" y la de compras "cabecera_compra". Confirmado en
vivo el 28/08/2026 (captura del árbol de vistas de CHAT del propio usuario):
hoy esas dos vistas NO EXISTEN en el servidor — lo que existe es "Ventas" y
"Compras". Cualquier SQL que mencione el nombre viejo falla con "objeto no
válido", y eso es justo lo que veía el usuario preguntando "total de ventas
por meses" en cualquier empresa que no fuera MONT (que a ratos sí tenía
"cabecera_factura", por la naturaleza compartida de CHAT — ver más abajo).

Por qué esto no es "arreglar una vez y ya": CHAT es un namespace de vistas
COMPARTIDO por todo el servidor (no por sesión), y `SP_MODIFICA_VISTA_IA` -que
vive en SQL Server, fuera de este repositorio- puede desplegar nombres
distintos según la empresa o según cambie con el tiempo. Hardcodear "Ventas"
en vez de "cabecera_factura" solo cambiaría CUÁL nombre fijo se rompe la
próxima vez. La solución robusta es probar en vivo, en cada uso, cuál de los
nombres candidatos responde de verdad — el mismo patrón ya validado en
core/mirror_manager.py y main.py para las tarjetas de Reportes BI, ahora
centralizado aquí para que el chat (api/routes_query.py) use la misma lógica
en vez de una tercera copia manual.

USO
---
Hay dos variantes porque el código del proyecto habla con la base de datos de
dos formas distintas:
  - `detectar_vista_sqlalchemy`: para código que ya tiene una `Connection` de
    SQLAlchemy abierta (mirror_manager.py, main.py).
  - `detectar_vista_connector`: para código que solo tiene el `connector` de
    alto nivel de la app (`connector.execute_query(...)`), como
    api/routes_query.py.
"""
from __future__ import annotations

# "Ventas"/"Compras" van primero: son los nombres confirmados en vivo el
# 28/08/2026 como los que el servidor realmente tiene desplegados hoy.
# "cabecera_factura"/"cabecera_compra" quedan como segundo intento por si el
# servidor vuelve a desplegarlos con el nombre genérico en el futuro — no se
# eliminan, se degradan a alternativa.
CANDIDATOS_VENTAS = ("Ventas", "cabecera_factura")
CANDIDATOS_COMPRAS = ("Compras", "cabecera_compra")


def detectar_vista_sqlalchemy(connection, candidatos: tuple[str, ...], target_db: str = "CHAT") -> str | None:
    """Primer nombre de `candidatos` que responde HOY en `target_db`, o None."""
    from sqlalchemy import text

    for candidato in candidatos:
        try:
            connection.execute(text(f"SELECT TOP 1 1 FROM [{target_db}].[dbo].[{candidato}]")).fetchone()
            return candidato
        except Exception:
            continue
    return None


def detectar_vista_connector(connector, candidatos: tuple[str, ...], target_db: str = "CHAT") -> str | None:
    """Misma detección que `detectar_vista_sqlalchemy`, vía connector.execute_query."""
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
