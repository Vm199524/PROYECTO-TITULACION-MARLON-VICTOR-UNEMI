# -*- coding: utf-8 -*-
"""
Carga de la institución piloto UNEMI_PRUEBAS (datos sintéticos y anonimizados).

Crea la base operativa UNEMI_PRUEBAS con dos tablas, tal como las tendría el
sistema académico de una universidad: alumnos_prueba (padrón) e
historial_matriculas (una fila por estudiante y semestre). Los archivos CSV
están en base_de_datos/datos_de_prueba/; las cédulas y los
nombres son ficticios (anonimizar_padron.py) y la trayectoria es sintética
(generate_historial.py). Ningún dato personal real entra en la base.

Uso:
    cd backend
    python -m scripts.cargar_unemi

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DIR_DATOS = Path(__file__).resolve().parents[2] / 'base_de_datos' / 'datos_de_prueba'

TABLAS = """
IF OBJECT_ID('dbo.stg_padron_electoral_raw', 'U') IS NOT NULL DROP TABLE dbo.stg_padron_electoral_raw;
IF OBJECT_ID('dbo.historial_matriculas', 'U') IS NOT NULL DROP TABLE dbo.historial_matriculas;
IF OBJECT_ID('dbo.alumnos_prueba', 'U') IS NOT NULL DROP TABLE dbo.alumnos_prueba;
CREATE TABLE dbo.alumnos_prueba (
    no INT PRIMARY KEY, apellidos NVARCHAR(100) NOT NULL, nombres NVARCHAR(100) NOT NULL, cedula VARCHAR(15) NOT NULL UNIQUE,
    facultad_codigo VARCHAR(20) NOT NULL, facultad_nombre NVARCHAR(200) NOT NULL, carrera NVARCHAR(150) NOT NULL,
    semestre TINYINT NOT NULL, estado_matricula VARCHAR(20) NOT NULL, promedio DECIMAL(4,2) NOT NULL,
    fecha_matricula DATE NOT NULL, monto_matricula DECIMAL(10,2) NOT NULL, beca_porcentaje TINYINT NOT NULL,
    saldo_pendiente DECIMAL(10,2) NOT NULL, genero CHAR(1) NOT NULL, ciudad_residencia NVARCHAR(50) NOT NULL);
CREATE TABLE dbo.historial_matriculas (
    id INT IDENTITY(1,1) PRIMARY KEY, cedula VARCHAR(15) NOT NULL, periodo_num TINYINT NOT NULL,
    es_ultimo_periodo BIT NOT NULL, facultad_codigo VARCHAR(20) NOT NULL, facultad_nombre NVARCHAR(200) NOT NULL,
    carrera NVARCHAR(150) NOT NULL, sede_codigo VARCHAR(20) NOT NULL, sede_nombre NVARCHAR(100) NOT NULL,
    canal_codigo VARCHAR(20) NOT NULL, semestre TINYINT NOT NULL, estado_matricula VARCHAR(20) NOT NULL,
    promedio DECIMAL(4,2) NOT NULL, asistencia_pct DECIMAL(5,2) NOT NULL, fecha_matricula DATE NOT NULL,
    inicio_clases DATE NOT NULL, monto_matricula DECIMAL(10,2) NOT NULL, beca_porcentaje TINYINT NOT NULL,
    saldo_pendiente DECIMAL(10,2) NOT NULL, creditos_matriculados SMALLINT NOT NULL, numero_matricula TINYINT NOT NULL,
    dias_anticipacion_matricula SMALLINT NOT NULL, actividad_lms INT NOT NULL, dias_sin_actividad SMALLINT NOT NULL,
    evaluaciones_vencidas SMALLINT NOT NULL, evaluaciones_entregadas SMALLINT NOT NULL,
    evaluaciones_tardias SMALLINT NOT NULL, nota_evaluaciones DECIMAL(4,2) NULL);
CREATE INDEX IX_historial_cedula ON dbo.historial_matriculas(cedula);
"""


def leer_csv(nombre: str) -> list[dict]:
    with open(DIR_DATOS / nombre, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main() -> int:
    from core.db import conectar_admin
    for nombre in ('alumnos_prueba.csv', 'historial_matriculas.csv'):
        if not (DIR_DATOS / nombre).exists():
            print(f'ERROR: falta {DIR_DATOS / nombre}')
            return 1
    conn = conectar_admin('master', autocommit=True)
    conn.cursor().execute("IF DB_ID('UNEMI_PRUEBAS') IS NULL CREATE DATABASE UNEMI_PRUEBAS")
    conn.close()
    conn = conectar_admin('UNEMI_PRUEBAS', tiempo=120)
    cur = conn.cursor()
    cur.execute(TABLAS)
    conn.commit()
    cur.fast_executemany = True
    alumnos = [(int(r['no']), r['apellidos'], r['nombres'], r['cedula'], r['facultad_codigo'], r['facultad_nombre'],
                r['carrera'], int(r['semestre']), r['estado_matricula'], float(r['promedio']),
                date.fromisoformat(r['fecha_matricula']), float(r['monto_matricula']), int(r['beca_porcentaje']),
                float(r['saldo_pendiente']), r['genero'], r['ciudad_residencia']) for r in leer_csv('alumnos_prueba.csv')]
    cur.executemany('INSERT INTO dbo.alumnos_prueba VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', alumnos)
    historial = [(r['cedula'], int(r['periodo_num']), int(r['es_ultimo_periodo']), r['facultad_codigo'], r['facultad_nombre'],
                  r['carrera'], r['sede_codigo'], r['sede_nombre'], r['canal_codigo'], int(r['semestre']),
                  r['estado_matricula'], float(r['promedio']), float(r['asistencia_pct']),
                  date.fromisoformat(r['fecha_matricula']), date.fromisoformat(r['inicio_clases']),
                  float(r['monto_matricula']), int(r['beca_porcentaje']), float(r['saldo_pendiente']),
                  int(r['creditos_matriculados']), int(r['numero_matricula']), int(r['dias_anticipacion_matricula']),
                  int(r['actividad_lms']), int(r['dias_sin_actividad']), int(r['evaluaciones_vencidas']),
                  int(r['evaluaciones_entregadas']), int(r['evaluaciones_tardias']),
                  float(r['nota_evaluaciones']) if r['nota_evaluaciones'] else None)
                 for r in leer_csv('historial_matriculas.csv')]
    cur.executemany("""INSERT INTO dbo.historial_matriculas (cedula, periodo_num, es_ultimo_periodo, facultad_codigo,
                       facultad_nombre, carrera, sede_codigo, sede_nombre, canal_codigo, semestre, estado_matricula, promedio,
                       asistencia_pct, fecha_matricula, inicio_clases, monto_matricula, beca_porcentaje, saldo_pendiente,
                       creditos_matriculados, numero_matricula, dias_anticipacion_matricula, actividad_lms,
                       dias_sin_actividad, evaluaciones_vencidas, evaluaciones_entregadas, evaluaciones_tardias,
                       nota_evaluaciones)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", historial)
    conn.commit()
    conn.close()
    print(f'UNEMI_PRUEBAS cargada: {len(alumnos)} estudiantes y {len(historial)} filas de historial.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
