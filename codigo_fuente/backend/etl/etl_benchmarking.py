# -*- coding: utf-8 -*-
"""
etl_benchmarking.py — pipeline de integración de referentes EXTERNOS de
abandono al warehouse (CHAT.dbo.dim_institucion_externa /
fact_benchmark_externo).

Criterio de fuentes (Avance 2): solo cifras publicadas en fuentes
académicas con DOI y verificadas en el texto completo del artículo (tabla o
párrafo exacto anotado en `definicion_indicador`). Se retiraron las cifras
tomadas de prensa: una nota periodística no es una fuente verificable para
un trabajo de titulación. Cada fila declara además QUÉ mide exactamente, en
qué país y modalidad, y su nivel de comparabilidad con la institución propia
(Lepori & Bornmann, 2026: comparar pares con pares):
    ALTA   mismo país y nivel (pregrado)
    MEDIA  pregrado presencial o mixto en otro país
    BAJA   otra modalidad (a distancia) u otra unidad de medida (módulo)

Por qué un CSV curado y no un scraper: los organismos no publican una API
estable. El CSV versionado es auditable (cada fila dice de dónde salió) y
este loader lo recarga de forma idempotente. Proceso de actualización en
documentacion/tecnica/BENCHMARKING_INSTITUCIONAL.md.

Uso:
    cd backend
    python -m etl.etl_benchmarking
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pyodbc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402

CSV_PATH = Path(__file__).resolve().parent / 'fuentes_externas' / 'benchmark_educacion_superior_ecuador.csv'
COLUMNAS_OBLIGATORIAS = ['institucion_codigo', 'nombre', 'tipo', 'indicador_codigo', 'valor', 'unidad',
                         'definicion_indicador', 'pais', 'modalidad', 'nivel_comparabilidad', 'fuente']
NIVELES = {'ALTA', 'MEDIA', 'BAJA'}


def conectar() -> pyodbc.Connection:
    return conectar_admin('CHAT')


def cargar_csv(path: Path) -> list[dict]:
    with open(path, encoding='utf-8-sig', newline='') as f:
        filas = list(csv.DictReader(f))
    for i, fila in enumerate(filas, 2):
        faltan = [c for c in COLUMNAS_OBLIGATORIAS if not (fila.get(c) or '').strip()]
        if faltan:
            raise ValueError(f"Fila {i} del CSV sin {faltan}: toda cifra debe declarar qué mide y su fuente.")
        if fila['nivel_comparabilidad'] not in NIVELES:
            raise ValueError(f"Fila {i}: nivel_comparabilidad debe ser uno de {sorted(NIVELES)}.")
        if 'expreso' in (fila.get('fuente', '') + fila.get('url_fuente', '')).lower():
            raise ValueError(f"Fila {i}: las cifras de prensa no se aceptan como referente.")
    return filas


def main() -> int:
    print(f"Leyendo {CSV_PATH} ...")
    filas = cargar_csv(CSV_PATH)
    print(f"  {len(filas)} referentes externos.")

    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM dbo.fact_benchmark_externo")
    cur.execute("DELETE FROM dbo.dim_institucion_externa")
    conn.commit()

    vistas: set[str] = set()
    for f in filas:
        codigo = f['institucion_codigo'].strip()
        if codigo not in vistas:
            vistas.add(codigo)
            cur.execute("""
                INSERT INTO dbo.dim_institucion_externa (institucion_codigo, nombre, tipo, categoria_caces, fecha_evaluacion_caces)
                VALUES (?, ?, ?, NULL, NULL)
            """, codigo, f['nombre'], f['tipo'])
        cur.execute("""
            INSERT INTO dbo.fact_benchmark_externo
                (institucion_codigo, indicador_codigo, valor, unidad, anio, definicion_indicador,
                 pais, modalidad, nivel_comparabilidad, fuente, doi, url_fuente)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, codigo, f['indicador_codigo'], float(f['valor']), f['unidad'],
            int(f['anio']) if f.get('anio') else None, f['definicion_indicador'], f['pais'],
            f['modalidad'], f['nivel_comparabilidad'], f['fuente'], f.get('doi') or None,
            f.get('url_fuente') or None)
    conn.commit()
    conn.close()
    print(f"Cargados {len(vistas)} referentes y {len(filas)} indicadores externos.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
