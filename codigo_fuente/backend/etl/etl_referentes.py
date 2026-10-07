# -*- coding: utf-8 -*-
"""
Carga de los referentes externos de abandono.

Solo se aceptan cifras publicadas en fuentes académicas con DOI y verificadas
en el texto completo (la tabla o el párrafo exacto queda anotado en
`definicion_indicador`). Cada cifra declara qué mide, en qué país y
modalidad, y su nivel de comparabilidad con la institución propia (Lepori y
Bornmann, 2026: comparar pares con pares):
    ALTA   mismo país y nivel (pregrado)
    MEDIA  pregrado presencial o mixto en otro país
    BAJA   otra modalidad (a distancia) u otra unidad de medida

El archivo CSV versionado es auditable: cada fila dice de dónde salió. Este
cargador lo valida completo antes de escribir y recarga de forma idempotente.

Uso:
    cd backend
    python -m etl.etl_referentes

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RUTA_CSV = Path(__file__).resolve().parent / 'fuentes_externas' / 'referentes_abandono.csv'
OBLIGATORIAS = ['referente_codigo', 'nombre', 'tipo', 'indicador_codigo', 'valor', 'unidad', 'definicion_indicador',
                'pais', 'modalidad', 'nivel_comparabilidad', 'fuente', 'doi']
NIVELES = {'ALTA', 'MEDIA', 'BAJA'}


def leer_csv(ruta: Path = RUTA_CSV) -> list[dict]:
    """Lee y valida el CSV; cualquier fila incompleta detiene la carga."""
    with open(ruta, encoding='utf-8-sig', newline='') as f:
        filas = list(csv.DictReader(f))
    for i, fila in enumerate(filas, 2):
        faltan = [c for c in OBLIGATORIAS if not (fila.get(c) or '').strip()]
        if faltan:
            raise ValueError(f'Fila {i}: faltan {faltan}. Toda cifra debe declarar qué mide, su fuente y su DOI.')
        if fila['nivel_comparabilidad'] not in NIVELES:
            raise ValueError(f'Fila {i}: nivel_comparabilidad debe ser uno de {sorted(NIVELES)}.')
        float(fila['valor'])
    return filas


def main() -> int:
    filas = leer_csv()
    from core.db import conectar_admin
    conn = conectar_admin()
    cur = conn.cursor()
    cur.execute('DELETE FROM dbo.fact_referente_externo')
    cur.execute('DELETE FROM dbo.dim_referente')
    vistos: set[str] = set()
    for f in filas:
        codigo = f['referente_codigo'].strip()
        if codigo not in vistos:
            vistos.add(codigo)
            cur.execute('INSERT INTO dbo.dim_referente (referente_codigo, nombre, tipo) VALUES (?, ?, ?)',
                        codigo, f['nombre'], f['tipo'])
        cur.execute("""INSERT INTO dbo.fact_referente_externo (referente_codigo, indicador_codigo, valor, unidad, anio,
                       definicion_indicador, pais, modalidad, nivel_comparabilidad, fuente, doi, url_fuente)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    codigo, f['indicador_codigo'], float(f['valor']), f['unidad'],
                    int(f['anio']) if f.get('anio') else None, f['definicion_indicador'], f['pais'], f['modalidad'],
                    f['nivel_comparabilidad'], f['fuente'], f['doi'], f.get('url_fuente') or None)
    conn.commit()
    conn.close()
    print(f'Cargados {len(vistos)} referentes y {len(filas)} indicadores con DOI.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
