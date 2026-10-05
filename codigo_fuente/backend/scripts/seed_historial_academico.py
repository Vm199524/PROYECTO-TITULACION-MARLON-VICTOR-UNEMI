# -*- coding: utf-8 -*-
"""
Carga del historial académico de prueba en UNEMI_PRUEBAS.

Carga historial_matriculas.csv (trayectoria alumno-periodo, generada por
codigo_fuente/base_de_datos/datos_de_prueba/generate_historial.py) en
UNEMI_PRUEBAS.dbo.historial_matriculas; la tabla se recrea en cada
ejecución. Usa pyodbc con fast_executemany, igual que el resto de
backend/scripts/*.py.

Uso:
    cd backend
    python scripts/seed_historial_academico.py

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402

CSV_PATH = str(Path(__file__).resolve().parents[2] / 'base_de_datos' / 'datos_de_prueba' / 'historial_matriculas.csv')

CREATE_SQL = """
IF OBJECT_ID('dbo.historial_matriculas', 'U') IS NOT NULL DROP TABLE dbo.historial_matriculas;
CREATE TABLE dbo.historial_matriculas (
    id                 INT IDENTITY(1,1) PRIMARY KEY,
    cedula             VARCHAR(15) NOT NULL,
    periodo_num        TINYINT NOT NULL,
    es_ultimo_periodo  BIT NOT NULL,
    facultad_codigo    VARCHAR(20) NOT NULL,
    facultad_nombre    NVARCHAR(200) NOT NULL,
    carrera            NVARCHAR(150) NOT NULL,
    sede_codigo        VARCHAR(20) NOT NULL,
    sede_nombre        NVARCHAR(100) NOT NULL,
    canal_codigo       VARCHAR(20) NOT NULL,
    semestre           TINYINT NOT NULL,
    estado_matricula   VARCHAR(20) NOT NULL,
    promedio           DECIMAL(4,2) NOT NULL,
    asistencia_pct     DECIMAL(5,2) NOT NULL,
    fecha_matricula    DATE NOT NULL,
    monto_matricula    DECIMAL(10,2) NOT NULL,
    beca_porcentaje    TINYINT NOT NULL,
    saldo_pendiente    DECIMAL(10,2) NOT NULL
);
CREATE INDEX IX_historial_cedula ON dbo.historial_matriculas(cedula);
"""

INSERT_SQL = """
INSERT INTO dbo.historial_matriculas
    (cedula, periodo_num, es_ultimo_periodo, facultad_codigo, facultad_nombre,
     carrera, sede_codigo, sede_nombre, canal_codigo, semestre, estado_matricula,
     promedio, asistencia_pct, fecha_matricula, monto_matricula, beca_porcentaje,
     saldo_pendiente)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def cargar_csv(path: str) -> list[tuple]:
    """Lee el CSV y convierte cada fila a los tipos de dbo.historial_matriculas, en el orden de INSERT_SQL."""
    filas = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            filas.append((
                r['cedula'],
                int(r['periodo_num']),
                int(r['es_ultimo_periodo']),
                r['facultad_codigo'],
                r['facultad_nombre'],
                r['carrera'],
                r['sede_codigo'],
                r['sede_nombre'],
                r['canal_codigo'],
                int(r['semestre']),
                r['estado_matricula'],
                float(r['promedio']),
                float(r['asistencia_pct']),
                date.fromisoformat(r['fecha_matricula']),
                float(r['monto_matricula']),
                int(r['beca_porcentaje']),
                float(r['saldo_pendiente']),
            ))
    return filas


def main() -> int:
    """Recrea dbo.historial_matriculas y la llena desde el CSV."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default=None)
    parser.add_argument('--driver', default=None)
    parser.add_argument('--user', default=None)
    parser.add_argument('--password', default=None)
    parser.add_argument('--database', default='UNEMI_PRUEBAS')
    parser.add_argument('--csv', default=CSV_PATH)
    args = parser.parse_args()

    print(f"Conectando a {args.database} ...")
    conn = conectar_admin(args.database, host=args.host, user=args.user,
                          password=args.password, driver=args.driver)
    cur = conn.cursor()

    print("Creando tabla dbo.historial_matriculas ...")
    for stmt in CREATE_SQL.strip().split(';'):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    conn.commit()

    print(f"Leyendo {args.csv} ...")
    filas = cargar_csv(args.csv)
    print(f"  {len(filas)} filas a insertar.")

    cur.fast_executemany = True
    cur.executemany(INSERT_SQL, filas)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM dbo.historial_matriculas")
    total = cur.fetchone()[0]
    print(f"Cargado. Filas en dbo.historial_matriculas: {total}")

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
