# -*- coding: utf-8 -*-
"""
Ejecución de archivos .sql por lotes sin depender de sqlcmd.

Ejecuta un archivo .sql (estilo sqlcmd: lotes separados por 'GO' en su
propia línea) contra el servidor, sin depender de que sqlcmd esté instalado
en el host (el contenedor Docker de SQL Server tampoco trae mssql-tools).

Soporta variables estilo sqlcmd ($(nombre)) vía --var nombre=valor.

Si no se pasa --var chat_reader_password, se toma CHAT_READER_PASSWORD de
backend/.env (así la contraseña no queda en el historial de la terminal).

Uso:
    cd backend
    python scripts/run_sql_file.py ../base_de_datos/crear_chat_academico.sql

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pyodbc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402


def dividir_en_lotes(sql_text: str) -> list[str]:
    """Divide el script en lotes por las líneas que solo contienen GO y descarta los vacíos."""
    lotes, actual = [], []
    for linea in sql_text.splitlines():
        if linea.strip().upper() == 'GO':
            if actual:
                lotes.append('\n'.join(actual))
                actual = []
        else:
            actual.append(linea)
    if actual:
        lotes.append('\n'.join(actual))
    return [l for l in (b.strip() for b in lotes) if l]


def main() -> int:
    """Sustituye las variables y ejecuta los lotes en orden con autocommit.

    Ante un error muestra el lote que falló y vuelve a lanzar la excepción.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sql_file')
    parser.add_argument('--host', default=None)
    parser.add_argument('--driver', default=None)
    parser.add_argument('--user', default=None)
    parser.add_argument('--password', default=None)
    parser.add_argument('--database', default='master')
    parser.add_argument('--var', action='append', default=[], help='nombre=valor, sustituye $(nombre)')
    args = parser.parse_args()

    variables = dict(v.split('=', 1) for v in args.var)
    if 'chat_reader_password' not in variables and os.getenv('CHAT_READER_PASSWORD'):
        variables['chat_reader_password'] = os.getenv('CHAT_READER_PASSWORD')

    with open(args.sql_file, encoding='utf-8') as f:
        sql_text = f.read()
    for nombre, valor in variables.items():
        sql_text = sql_text.replace(f'$({nombre})', valor)

    conn = conectar_admin(args.database, host=args.host, user=args.user, password=args.password,
                          driver=args.driver, autocommit=True)
    cur = conn.cursor()

    lotes = dividir_en_lotes(sql_text)
    print(f"Ejecutando {len(lotes)} lotes de {args.sql_file} ...")
    for i, lote in enumerate(lotes, 1):
        try:
            cur.execute(lote)
            while cur.nextset():
                pass
        except pyodbc.Error as e:
            msg = f"ERROR en lote {i}:\n{lote[:300]}\n-> {e}"
            sys.stdout.buffer.write(msg.encode('utf-8', errors='replace') + b'\n')
            raise
    print("Listo.")
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
