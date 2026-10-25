# -*- coding: utf-8 -*-
"""
Lectura de la trayectoria de una institución desde el almacén académico.

Los procesos por lotes (entrenar, calificar, segmentar) leen las tablas
físicas con la cuenta de administración: no son consultas de un usuario y no
pasan por las vistas gobernadas. Cada lectura filtra por la institución.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import warnings

import pandas as pd

from ml.caracteristicas import COLUMNAS_OPCIONALES_FUENTE

SQL_HISTORIAL = f"""
SELECT fm.matricula_id, fm.alumno_id, fm.carrera_id, fm.periodo_id, dp.periodo_codigo, dp.fecha_inicio,
       dt.fecha, fm.nivel, fm.corte, fm.estado_codigo, fm.es_ultimo_periodo,
       fm.promedio, fm.asistencia_pct, {', '.join('fm.' + c for c in COLUMNAS_OPCIONALES_FUENTE)},
       da.cedula, da.apellidos, da.nombres, da.genero,
       dc.carrera, dc.facultad_codigo, dc.facultad_nombre,
       ds.sede_codigo, fm.modalidad_codigo
FROM dbo.fact_matriculas fm
JOIN dbo.dim_alumno da            ON da.alumno_id = fm.alumno_id
JOIN dbo.dim_tiempo dt            ON dt.tiempo_id = fm.tiempo_id
JOIN dbo.dim_periodo_academico dp ON dp.periodo_id = fm.periodo_id
JOIN dbo.dim_carrera dc           ON dc.carrera_id = fm.carrera_id
JOIN dbo.dim_sede ds              ON ds.sede_id = fm.sede_id
WHERE fm.institucion_codigo = ?
"""


def leer_historial(conn, institucion: str) -> pd.DataFrame:
    """Devuelve la trayectoria completa de la institución, una fila por periodo y corte."""
    with warnings.catch_warnings():
        # pandas advierte cuando recibe una conexión DBAPI que no es SQLAlchemy; es esperado.
        warnings.simplefilter('ignore', UserWarning)
        df = pd.read_sql(SQL_HISTORIAL, conn, params=[institucion])
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['fecha_inicio'] = pd.to_datetime(df['fecha_inicio'])
    return df


def leer_institucion(conn, institucion: str) -> dict:
    """Datos descriptivos de la institución (nombre, tipo de datos, unidad de periodo)."""
    cur = conn.cursor()
    cur.execute('SELECT nombre, pais, tipo_datos, unidad_periodo FROM dbo.dim_institucion '
                'WHERE institucion_codigo = ?', institucion)
    fila = cur.fetchone()
    if not fila:
        raise KeyError(f'La institución {institucion} no está cargada en el almacén. Ejecute primero el ETL.')
    return {'nombre': fila[0], 'pais': fila[1], 'tipo_datos': fila[2], 'unidad_periodo': fila[3]}
