# -*- coding: utf-8 -*-
"""
seed_alumnos_prueba.py — carga alumnos_prueba.csv (dataset base de 14.508
alumnos, ver codigo_fuente/base_de_datos/datos_de_prueba/) en
UNEMI_PRUEBAS.dbo.alumnos_prueba.

Protección de datos (Avance 2, RNF de privacidad — LOPDP): el CSV que se
carga aquí es el ANONIMIZADO por _extract/anonimizar_padron.py (cédulas y
nombres ficticios; el resto de columnas idéntico). La tabla de staging con
el padrón crudo (dbo.stg_padron_electoral_raw) ya no se crea: si quedó de
una carga anterior, este script la elimina, para que la base de pruebas no
conserve ningún dato personal real.

Este es el primer paso de la cadena de reconstrucción de la base de datos
(ver documentacion/tecnica/MANUAL_INSTALACION.md y codigo_fuente/scripts/demo_tesis.ps1).

Uso:
    cd backend
    python scripts/seed_alumnos_prueba.py
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402

EXTRACT_DIR = Path(__file__).resolve().parents[2] / 'base_de_datos' / 'datos_de_prueba'
FINAL_CSV = EXTRACT_DIR / 'alumnos_prueba.csv'

CREATE_FINAL_SQL = """
IF OBJECT_ID('dbo.stg_padron_electoral_raw', 'U') IS NOT NULL DROP TABLE dbo.stg_padron_electoral_raw;
IF OBJECT_ID('dbo.alumnos_prueba', 'U') IS NOT NULL DROP TABLE dbo.alumnos_prueba;
CREATE TABLE dbo.alumnos_prueba (
    no                 INT PRIMARY KEY,
    apellidos          NVARCHAR(100) NOT NULL,
    nombres            NVARCHAR(100) NOT NULL,
    cedula             VARCHAR(15) NOT NULL,
    facultad_codigo    VARCHAR(20) NOT NULL,
    facultad_nombre    NVARCHAR(200) NOT NULL,
    carrera            NVARCHAR(150) NOT NULL,
    semestre           TINYINT NOT NULL,
    estado_matricula   VARCHAR(20) NOT NULL,
    promedio           DECIMAL(4,2) NOT NULL,
    fecha_matricula    DATE NOT NULL,
    monto_matricula    DECIMAL(10,2) NOT NULL,
    beca_porcentaje    TINYINT NOT NULL,
    saldo_pendiente    DECIMAL(10,2) NOT NULL,
    genero             CHAR(1) NOT NULL,
    ciudad_residencia  NVARCHAR(50) NOT NULL
);
"""

INSERT_FINAL_SQL = """
INSERT INTO dbo.alumnos_prueba
    (no, apellidos, nombres, cedula, facultad_codigo, facultad_nombre, carrera,
     semestre, estado_matricula, promedio, fecha_matricula, monto_matricula,
     beca_porcentaje, saldo_pendiente, genero, ciudad_residencia)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _crear_base_si_falta() -> None:
    """UNEMI_PRUEBAS no la crea ningún otro script: se crea aquí para que la
    reconstrucción completa quede en un solo paso reproducible."""
    conn = conectar_admin('master', timeout=30, autocommit=True)
    conn.cursor().execute(
        "IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = 'UNEMI_PRUEBAS') "
        "CREATE DATABASE UNEMI_PRUEBAS;"
    )
    conn.close()


def main() -> int:
    if not FINAL_CSV.exists():
        print(f"ERROR: no se encontró {FINAL_CSV}")
        print("Genéralo con: python \"codigo_fuente/base_de_datos/datos_de_prueba/anonimizar_padron.py\"")
        return 1

    _crear_base_si_falta()
    conn = conectar_admin('UNEMI_PRUEBAS', timeout=30)
    cur = conn.cursor()

    print("Creando dbo.alumnos_prueba (y eliminando el staging del padrón si existía) ...")
    cur.execute(CREATE_FINAL_SQL)
    conn.commit()
    with open(FINAL_CSV, encoding='utf-8-sig', newline='') as f:
        filas = [(
            int(r['no']), r['apellidos'], r['nombres'], r['cedula'],
            r['facultad_codigo'], r['facultad_nombre'], r['carrera'],
            int(r['semestre']), r['estado_matricula'], float(r['promedio']),
            date.fromisoformat(r['fecha_matricula']), float(r['monto_matricula']),
            int(r['beca_porcentaje']), float(r['saldo_pendiente']),
            r['genero'], r['ciudad_residencia'],
        ) for r in csv.DictReader(f)]
    cur.fast_executemany = True
    cur.executemany(INSERT_FINAL_SQL, filas)
    conn.commit()
    print(f"  {len(filas)} filas cargadas en alumnos_prueba.")

    conn.close()
    print("Listo. Siguiente paso: python scripts/seed_historial_academico.py")
    return 0


if __name__ == '__main__':
    sys.exit(main())
