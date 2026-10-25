# -*- coding: utf-8 -*-
"""
ETL académico: de la base operativa de una institución al almacén.

Extrae con el SELECT del perfil (etl/perfiles.py), valida el contrato y las
reglas de calidad, y recarga los datos de ESA institución:

  - Dimensiones con altas idempotentes (MERGE): institución, periodos,
    sedes, carreras y estudiantes. Los estudiantes conservan su clave entre
    recargas, para no romper el registro de seguimiento de bienestar.
  - Hechos con recarga completa de la institución: se borran sus
    predicciones, segmentos y trayectoria, y se inserta la trayectoria nueva
    por lotes. Nunca se toca lo de otra institución.

Es una recarga completa, no incremental (CDC): suficiente para el volumen y
la cadencia de un prototipo; el incremental queda como evolución futura.

Uso:
    cd backend
    python -m etl.etl_academico --perfil UNEMI_PRUEBAS

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.perfiles import (COLUMNAS_OPCIONALES, PerfilInstitucion, obtener_perfil,  # noqa: E402
                          validar_columnas, validar_filas)

LOTE = 20_000


def extraer(conn, perfil: PerfilInstitucion) -> list[dict]:
    """Ejecuta el SELECT del perfil y devuelve las filas como diccionarios."""
    cur = conn.cursor()
    cur.execute(perfil.sql_origen)
    columnas = [c[0] for c in cur.description]
    validar_columnas(columnas, perfil)
    return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def _fecha(v) -> dt.date:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v)[:10])


def _opcional(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _mapa(cur, sql: str, *parametros) -> dict:
    cur.execute(sql, *parametros)
    return {tuple(f[:-1]) if len(f) > 2 else f[0]: f[-1] for f in cur.fetchall()}


def cargar(conn, filas: list[dict], perfil: PerfilInstitucion) -> int:
    """Recarga en el almacén los datos de la institución. Devuelve las filas insertadas."""
    inst = perfil.codigo
    cur = conn.cursor()
    cur.fast_executemany = True

    cur.execute("""
        MERGE dbo.dim_institucion AS d USING (SELECT ? AS c, ? AS n, ? AS p, ? AS t, ? AS u) AS s
        ON d.institucion_codigo = s.c
        WHEN MATCHED THEN UPDATE SET nombre = s.n, pais = s.p, tipo_datos = s.t, unidad_periodo = s.u,
                                     fecha_carga = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN INSERT (institucion_codigo, nombre, pais, tipo_datos, unidad_periodo)
                              VALUES (s.c, s.n, s.p, s.t, s.u);""",
                inst, perfil.nombre, perfil.pais, perfil.tipo_datos, perfil.unidad_periodo)

    # Recarga de hechos de esta institución (orden obligado por las llaves foráneas).
    for tabla in ('fact_prediccion_abandono', 'fact_segmento_carrera', 'fact_matriculas'):
        cur.execute(f'DELETE FROM dbo.{tabla} WHERE institucion_codigo = ?', inst)
    conn.commit()

    # Periodos académicos: el inicio es el menor declarado para ese código.
    periodos: dict[str, dt.date] = {}
    for f in filas:
        cod, ini = str(f['periodo_academico']), _fecha(f['inicio_periodo'])
        periodos[cod] = min(ini, periodos.get(cod, ini))
    for cod, ini in periodos.items():
        cur.execute("""IF NOT EXISTS (SELECT 1 FROM dbo.dim_periodo_academico WHERE institucion_codigo = ? AND periodo_codigo = ?)
                         INSERT INTO dbo.dim_periodo_academico (institucion_codigo, periodo_codigo, fecha_inicio) VALUES (?, ?, ?)
                       ELSE UPDATE dbo.dim_periodo_academico SET fecha_inicio = ? WHERE institucion_codigo = ? AND periodo_codigo = ?""",
                    inst, cod, inst, cod, ini, ini, inst, cod)
    for (cod, nombre) in {(f['sede_codigo'], f['sede_nombre']) for f in filas}:
        cur.execute("""IF NOT EXISTS (SELECT 1 FROM dbo.dim_sede WHERE institucion_codigo = ? AND sede_codigo = ?)
                         INSERT INTO dbo.dim_sede (institucion_codigo, sede_codigo, sede_nombre) VALUES (?, ?, ?)""",
                    inst, cod, inst, cod, nombre)
    for (carrera, fac, fac_nom) in {(f['carrera'], f['facultad_codigo'], f['facultad_nombre']) for f in filas}:
        cur.execute("""IF NOT EXISTS (SELECT 1 FROM dbo.dim_carrera WHERE institucion_codigo = ? AND carrera = ? AND facultad_codigo = ?)
                         INSERT INTO dbo.dim_carrera (institucion_codigo, carrera, facultad_codigo, facultad_nombre) VALUES (?, ?, ?, ?)""",
                    inst, carrera, fac, inst, carrera, fac, fac_nom)
    fechas = {_fecha(f['fecha_corte']) for f in filas}
    cur.execute('SELECT fecha FROM dbo.dim_tiempo')
    existentes = {_fecha(r[0]) for r in cur.fetchall()}
    nuevas = [(d, d.year, d.month, (d.month - 1) // 3 + 1) for d in sorted(fechas - existentes)]
    if nuevas:
        cur.executemany('INSERT INTO dbo.dim_tiempo (fecha, anio, mes, trimestre) VALUES (?, ?, ?, ?)', nuevas)
    conn.commit()

    # Estudiantes: alta o actualización conservando la clave (MERGE desde una tabla temporal).
    alumnos: dict[str, tuple] = {}
    for f in filas:
        alumnos.setdefault(str(f['cedula']), (inst, str(f['cedula']), f['apellidos'], f['nombres'],
                                              str(f['genero'])[:1], f['ciudad_residencia']))
    cur.execute("""CREATE TABLE #alumnos (institucion_codigo VARCHAR(30), cedula VARCHAR(15), apellidos NVARCHAR(100),
                   nombres NVARCHAR(100), genero CHAR(1), ciudad_residencia NVARCHAR(50))""")
    lista = list(alumnos.values())
    for i in range(0, len(lista), LOTE):
        cur.executemany('INSERT INTO #alumnos VALUES (?, ?, ?, ?, ?, ?)', lista[i:i + LOTE])
    cur.execute("""
        MERGE dbo.dim_alumno AS d USING #alumnos AS s
        ON d.institucion_codigo = s.institucion_codigo AND d.cedula = s.cedula
        WHEN MATCHED THEN UPDATE SET apellidos = s.apellidos, nombres = s.nombres, genero = s.genero,
                                     ciudad_residencia = s.ciudad_residencia
        WHEN NOT MATCHED THEN INSERT (institucion_codigo, cedula, apellidos, nombres, genero, ciudad_residencia)
                              VALUES (s.institucion_codigo, s.cedula, s.apellidos, s.nombres, s.genero, s.ciudad_residencia);
        DROP TABLE #alumnos;""")
    conn.commit()

    id_alumno = _mapa(cur, 'SELECT cedula, alumno_id FROM dbo.dim_alumno WHERE institucion_codigo = ?', inst)
    id_periodo = _mapa(cur, 'SELECT periodo_codigo, periodo_id FROM dbo.dim_periodo_academico WHERE institucion_codigo = ?', inst)
    id_sede = _mapa(cur, 'SELECT sede_codigo, sede_id FROM dbo.dim_sede WHERE institucion_codigo = ?', inst)
    id_carrera = _mapa(cur, 'SELECT carrera, facultad_codigo, carrera_id FROM dbo.dim_carrera WHERE institucion_codigo = ?', inst)
    cur.execute('SELECT fecha, tiempo_id FROM dbo.dim_tiempo')
    id_tiempo = {_fecha(r[0]): r[1] for r in cur.fetchall()}

    registros = []
    for f in filas:
        registros.append((
            inst, id_alumno[str(f['cedula'])], id_carrera[(f['carrera'], f['facultad_codigo'])],
            id_sede[f['sede_codigo']], f['modalidad'], id_periodo[str(f['periodo_academico'])],
            id_tiempo[_fecha(f['fecha_corte'])], f['estado_matricula'], int(f['nivel']), int(f['corte']),
            round(float(f['promedio']), 2), round(float(f['asistencia_pct']), 2),
            *[_opcional(f.get(c)) for c in COLUMNAS_OPCIONALES], bool(f['es_ultimo_periodo']),
        ))
    columnas = (['institucion_codigo', 'alumno_id', 'carrera_id', 'sede_id', 'modalidad_codigo', 'periodo_id',
                 'tiempo_id', 'estado_codigo', 'nivel', 'corte', 'promedio', 'asistencia_pct']
                + COLUMNAS_OPCIONALES + ['es_ultimo_periodo'])
    sql = f"INSERT INTO dbo.fact_matriculas ({', '.join(columnas)}) VALUES ({', '.join('?' * len(columnas))})"
    for i in range(0, len(registros), LOTE):
        cur.executemany(sql, registros[i:i + LOTE])
        conn.commit()
    return len(registros)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--perfil', required=True)
    args = parser.parse_args()
    perfil = obtener_perfil(args.perfil)

    from core.db import conectar_admin
    inicio = time.time()
    origen = conectar_admin(perfil.base_origen, tiempo=120)
    print(f"Extrayendo con el perfil '{perfil.codigo}' desde {perfil.base_origen} ...")
    filas = extraer(origen, perfil)
    origen.close()
    print(f'  {len(filas)} filas extraídas.')
    problemas = validar_filas(filas)
    if problemas:
        for p in problemas:
            print('  ERROR de calidad:', p)
        return 1
    destino = conectar_admin(tiempo=120)
    n = cargar(destino, filas, perfil)
    destino.close()
    print(f'  {n} filas cargadas en fact_matriculas para {perfil.codigo} en {time.time() - inicio:.1f} s.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
