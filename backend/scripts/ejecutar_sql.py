# -*- coding: utf-8 -*-
"""
Ejecuta un archivo .sql por lotes (separados por GO) sin depender de sqlcmd.

Sustituye las variables $(chat_reader_password) y $(app_seguimiento_password)
con los valores de backend/.env, para que ninguna contraseña quede escrita en
el script ni en el historial de la terminal.

Uso:
    cd backend
    python -m scripts.ejecutar_sql ../base_de_datos/crear_almacen_academico.sql

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def dividir_en_lotes(texto: str) -> list[str]:
    """Divide por líneas que solo contienen GO y descarta lotes vacíos."""
    lotes, actual = [], []
    for linea in texto.splitlines():
        if linea.strip().upper() == 'GO':
            lotes.append('\n'.join(actual))
            actual = []
        else:
            actual.append(linea)
    lotes.append('\n'.join(actual))
    return [l.strip() for l in lotes if l.strip() and not all(x.strip().startswith('--') or not x.strip()
                                                                for x in l.splitlines())]


def main() -> int:
    from core.config import CONFIG
    from core.db import conectar_admin
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('archivo')
    args = parser.parse_args()
    texto = Path(args.archivo).read_text(encoding='utf-8')
    variables = {'chat_reader_password': CONFIG.lector_clave, 'app_seguimiento_password': CONFIG.seguimiento_clave}
    for nombre, valor in variables.items():
        if f'$({nombre})' in texto:
            if not valor:
                print(f'ERROR: defina {nombre.upper()} en backend/.env antes de ejecutar {args.archivo}.')
                return 1
            if "'" in valor:
                print(f'ERROR: {nombre.upper()} no puede contener comillas simples.')
                return 1
            texto = texto.replace(f'$({nombre})', valor)
    if re.search(r'\$\([a-z_]+\)', texto):
        print('ERROR: el script tiene variables sin valor:', set(re.findall(r'\$\(([a-z_]+)\)', texto)))
        return 1
    conn = conectar_admin('master', autocommit=True, tiempo=120)
    cur = conn.cursor()
    lotes = dividir_en_lotes(texto)
    for i, lote in enumerate(lotes, 1):
        try:
            cur.execute(lote)
            while cur.nextset():
                pass
        except Exception as exc:  # noqa: BLE001
            print(f'ERROR en el lote {i} de {len(lotes)}:\n{lote[:600]}\n---\n{exc}')
            return 1
    conn.close()
    print(f'{args.archivo}: {len(lotes)} lotes ejecutados.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
