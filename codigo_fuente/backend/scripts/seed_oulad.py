# -*- coding: utf-8 -*-
"""
seed_oulad.py — carga el Open University Learning Analytics Dataset (OULAD;
Kuzilek, Hlosta & Zdrahal, 2017, Scientific Data 4:170171, CC BY 4.0) como
SEGUNDA institución del sistema (OULAD_UK), en la base operativa
OULAD_PRUEBAS.dbo.historial_bloques.

Por qué: el documento afirma que la arquitectura se extiende a otra
institución "agregando únicamente un perfil de mapeo, sin reescribir el
motor predictivo", y que el aislamiento entre instituciones se verifica a
nivel del motor de base de datos. Con una sola institución cargada ninguna
de las dos afirmaciones se puede demostrar. OULAD además aporta datos REALES
(anonimizados en origen por la Open University), a diferencia del dataset
sintético de UNEMI_PRUEBAS.

Transformación a la forma del warehouse (una fila por alumno-periodo):
  - Cada matrícula (estudiante x módulo x presentación) se divide en
    BLOQUES de 28 días desde el inicio de la presentación (día 0). El bloque
    es el "periodo" de OULAD, igual que el semestre lo es en UNEMI.
  - asistencia_pct: días con actividad en el aula virtual (studentVle) dentro
    del bloque / días del bloque x 100. Es la actividad en el LMS como
    predictor (Marcolino et al., 2025; Vaarma & Li, 2024).
  - promedio: media (0-10) de las evaluaciones del módulo cuyo plazo ya
    venció al cierre del bloque; una evaluación no entregada a esa fecha
    cuenta como 0. Si todavía no vence ninguna, se registra 0 para todos los
    estudiantes del módulo (valor constante, sin información individual).
    Solo se usa información disponible al cierre del bloque: sin fuga.
  - estado: ACTIVO hasta el bloque que contiene date_unregistration, que
    pasa a RETIRADO y es el último; quien completa queda GRADUADO
    (Pass/Distinction) o REPROBADO (Fail). Retiros antes del día 0 o sin fecha
    quedan como una sola fila RETIRADO en el bloque 1 (no anticipables).
  - Variables financieras (monto, beca, saldo): OULAD no las tiene -> 0.
  - Identidad: cédula = "OU<id_student>" (el dataset ya es anónimo);
    nombres/apellidos = seudónimo. facultad = dominio del módulo según la
    Tabla 1 de Kuzilek et al. (2017); carrera = código del módulo.

Corte "en curso": la presentación más reciente (2014J) se carga solo hasta
el bloque --corte (por defecto 3, es decir, 12 semanas), como si estuviera en
marcha: quien sigue matriculado a esa fecha queda ACTIVO y es a quien el
modelo califica. Lo que realmente ocurrió después se guarda en
dbo.verdad_futura (NO pasa al warehouse CHAT) para una evaluación
prospectiva honesta del modelo (ml/reporte_validacion.py).

Uso:
    cd backend
    python scripts/seed_oulad.py [--dir "../../datos/externos/oulad"] [--corte 3]
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402

DIR_POR_DEFECTO = Path(__file__).resolve().parents[3] / 'datos' / 'externos' / 'oulad'
DIAS_BLOQUE = 28
PRESENTACION_EN_CURSO = '2014J'

# Tabla 1 de Kuzilek et al. (2017), verificada en el texto completo (PMC5704676).
DOMINIO = {
    'AAA': ('SOC', 'Social Sciences'), 'BBB': ('SOC', 'Social Sciences'), 'GGG': ('SOC', 'Social Sciences'),
    'CCC': ('STEM', 'Science, Technology, Engineering and Mathematics'),
    'DDD': ('STEM', 'Science, Technology, Engineering and Mathematics'),
    'EEE': ('STEM', 'Science, Technology, Engineering and Mathematics'),
    'FFF': ('STEM', 'Science, Technology, Engineering and Mathematics'),
}


def inicio_presentacion(codigo: str) -> date:
    """B = presentación que inicia en febrero, J = en octubre (OULAD.names).
    El día exacto no se publica: se usa el día 1 del mes (aproximación
    documentada)."""
    return date(int(codigo[:4]), 2 if codigo[4] == 'B' else 10, 1)


def _num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors='coerce')


def dias_activos_por_bloque(directorio: Path) -> pd.DataFrame:
    """(module, presentation, student, bloque) -> días distintos con clics.
    studentVle tiene 10,6 M de filas: se lee por partes."""
    partes = []
    for trozo in pd.read_csv(directorio / 'studentVle.csv',
                             usecols=['code_module', 'code_presentation', 'id_student', 'date'],
                             dtype={'code_module': 'category', 'code_presentation': 'category',
                                    'id_student': 'int32', 'date': 'int16'},
                             chunksize=2_000_000):
        partes.append(trozo.drop_duplicates())
    vle = pd.concat(partes, ignore_index=True).drop_duplicates()
    vle['bloque'] = (vle['date'].clip(lower=0) // DIAS_BLOQUE + 1).astype('int16')
    return (vle.groupby(['code_module', 'code_presentation', 'id_student', 'bloque'], observed=True)
               .size().rename('dias_activos').reset_index())


def promedio_por_bloque(directorio: Path, matriculas: pd.DataFrame, n_bloques: dict) -> pd.DataFrame:
    ev = pd.read_csv(directorio / 'assessments.csv')
    ev = ev[ev['assessment_type'] != 'Exam'].copy()
    ev['date'] = _num(ev['date'])
    ev = ev.dropna(subset=['date'])
    sa = pd.read_csv(directorio / 'studentAssessment.csv')
    sa['score'] = _num(sa['score'])
    sa['date_submitted'] = _num(sa['date_submitted'])

    filas = []
    for (mod, pres), grupo in matriculas.groupby(['code_module', 'code_presentation']):
        ev_mp = ev[(ev.code_module == mod) & (ev.code_presentation == pres)]
        entregas = sa[sa.id_assessment.isin(ev_mp.id_assessment)]
        estudiantes = grupo['id_student'].unique()
        for b in range(1, n_bloques[(mod, pres)] + 1):
            fin = b * DIAS_BLOQUE
            vencidas = ev_mp[ev_mp['date'] < fin]['id_assessment']
            if vencidas.empty:
                prom = pd.Series(0.0, index=estudiantes)
            else:
                ok = entregas[entregas.id_assessment.isin(vencidas) & (entregas.date_submitted < fin)]
                suma = ok.groupby('id_student')['score'].sum()
                prom = (suma.reindex(estudiantes, fill_value=0.0) / len(vencidas) / 10.0).clip(0, 10)
            filas.append(pd.DataFrame({'code_module': mod, 'code_presentation': pres,
                                       'id_student': estudiantes, 'bloque': b,
                                       'promedio': prom.values.round(2)}))
    return pd.concat(filas, ignore_index=True)


def construir_historial(directorio: Path, corte: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    info = pd.read_csv(directorio / 'studentInfo.csv')
    reg = pd.read_csv(directorio / 'studentRegistration.csv')
    cursos = pd.read_csv(directorio / 'courses.csv')
    reg['date_unregistration'] = _num(reg['date_unregistration'])
    m = info.merge(reg, on=['code_module', 'code_presentation', 'id_student'], how='left')
    m = m.merge(cursos, on=['code_module', 'code_presentation'], how='left')
    m['n_bloques'] = np.ceil(m['module_presentation_length'] / DIAS_BLOQUE).astype(int)
    n_bloques = {(r.code_module, r.code_presentation): math.ceil(r.module_presentation_length / DIAS_BLOQUE)
                 for r in cursos.itertuples()}

    retirado = m['final_result'] == 'Withdrawn'
    du = m['date_unregistration']
    m['ultimo_bloque'] = m['n_bloques']
    m.loc[retirado, 'ultimo_bloque'] = np.where(
        du[retirado] >= 0, (du[retirado] // DIAS_BLOQUE + 1).clip(upper=m.loc[retirado, 'n_bloques']), 1
    ).astype(int)
    m['estado_final'] = np.select(
        [retirado, m['final_result'].isin(['Pass', 'Distinction'])],
        ['RETIRADO', 'GRADUADO'], default='REPROBADO',
    )

    # Verdad futura de la presentación "en curso" (no pasa al warehouse).
    en_curso = m['code_presentation'] == PRESENTACION_EN_CURSO
    verdad = m.loc[en_curso, ['code_module', 'code_presentation', 'id_student',
                              'ultimo_bloque', 'estado_final']].copy()
    verdad.columns = ['code_module', 'code_presentation', 'id_student', 'bloque_final_real', 'estado_final_real']

    # Expandir a una fila por bloque.
    m['bloques_cargados'] = np.where(en_curso, np.minimum(m['ultimo_bloque'], corte), m['ultimo_bloque'])
    filas = m.loc[m.index.repeat(m['bloques_cargados'])].copy()
    filas['bloque'] = filas.groupby(level=0).cumcount() + 1
    filas = filas.reset_index(drop=True)
    es_ultimo = filas['bloque'] == filas['bloques_cargados']
    termino_aqui = filas['bloque'] == filas['ultimo_bloque']
    filas['es_ultimo_periodo'] = es_ultimo.astype(int)
    filas['estado_matricula'] = np.where(es_ultimo & termino_aqui, filas['estado_final'], 'ACTIVO')

    print('  Calculando días activos por bloque (studentVle, 10,6 M filas) ...')
    act = dias_activos_por_bloque(directorio)
    act['code_module'] = act['code_module'].astype(str)
    act['code_presentation'] = act['code_presentation'].astype(str)
    filas = filas.merge(act, on=['code_module', 'code_presentation', 'id_student', 'bloque'], how='left')
    filas['dias_activos'] = filas['dias_activos'].fillna(0)
    dias_del_bloque = np.minimum(DIAS_BLOQUE,
                                 filas['module_presentation_length'] - (filas['bloque'] - 1) * DIAS_BLOQUE).clip(lower=1)
    filas['asistencia_pct'] = (filas['dias_activos'] / dias_del_bloque * 100).clip(0, 100).round(2)

    print('  Calculando promedio acumulado por bloque (studentAssessment) ...')
    prom = promedio_por_bloque(directorio, m, n_bloques)
    filas = filas.merge(prom, on=['code_module', 'code_presentation', 'id_student', 'bloque'], how='left')
    filas['promedio'] = filas['promedio'].fillna(0.0)

    inicio = filas['code_presentation'].map(lambda c: inicio_presentacion(c))
    filas['fecha_matricula'] = [i + timedelta(days=(b - 1) * DIAS_BLOQUE) for i, b in zip(inicio, filas['bloque'])]
    filas['cedula'] = 'OU' + filas['id_student'].astype(str)
    filas['apellidos'] = 'Estudiante OU'
    filas['nombres'] = filas['id_student'].astype(str)
    filas['facultad_codigo'] = filas['code_module'].map(lambda c: DOMINIO[c][0])
    filas['facultad_nombre'] = filas['code_module'].map(lambda c: DOMINIO[c][1])
    filas['carrera'] = 'Modulo ' + filas['code_module']
    filas['genero'] = filas['gender']
    filas['ciudad_residencia'] = filas['region'].str.slice(0, 50)

    columnas = ['cedula', 'apellidos', 'nombres', 'genero', 'ciudad_residencia',
                'code_module', 'code_presentation', 'bloque', 'es_ultimo_periodo',
                'facultad_codigo', 'facultad_nombre', 'carrera', 'estado_matricula',
                'promedio', 'asistencia_pct', 'fecha_matricula']
    return filas[columnas], verdad


CREATE_SQL = [
    "IF OBJECT_ID('dbo.historial_bloques', 'U') IS NOT NULL DROP TABLE dbo.historial_bloques",
    """CREATE TABLE dbo.historial_bloques (
        id                 INT IDENTITY(1,1) PRIMARY KEY,
        cedula             VARCHAR(15) NOT NULL,
        apellidos          NVARCHAR(100) NOT NULL,
        nombres            NVARCHAR(100) NOT NULL,
        genero             CHAR(1) NOT NULL,
        ciudad_residencia  NVARCHAR(50) NOT NULL,
        code_module        VARCHAR(3) NOT NULL,
        code_presentation  VARCHAR(5) NOT NULL,
        bloque             TINYINT NOT NULL,
        es_ultimo_periodo  BIT NOT NULL,
        facultad_codigo    VARCHAR(20) NOT NULL,
        facultad_nombre    NVARCHAR(200) NOT NULL,
        carrera            NVARCHAR(150) NOT NULL,
        estado_matricula   VARCHAR(20) NOT NULL,
        promedio           DECIMAL(4,2) NOT NULL,
        asistencia_pct     DECIMAL(5,2) NOT NULL,
        fecha_matricula    DATE NOT NULL
    )""",
    "IF OBJECT_ID('dbo.verdad_futura', 'U') IS NOT NULL DROP TABLE dbo.verdad_futura",
    """CREATE TABLE dbo.verdad_futura (
        code_module        VARCHAR(3) NOT NULL,
        code_presentation  VARCHAR(5) NOT NULL,
        cedula             VARCHAR(15) NOT NULL,
        bloque_final_real  TINYINT NOT NULL,
        estado_final_real  VARCHAR(20) NOT NULL,
        PRIMARY KEY (code_module, code_presentation, cedula)
    )""",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', default=str(DIR_POR_DEFECTO))
    parser.add_argument('--corte', type=int, default=3, help='Bloques de 28 días cargados de la presentación en curso')
    parser.add_argument('--solo-resumen', action='store_true', help='Construye y resume, sin escribir en la base')
    args = parser.parse_args()

    directorio = Path(args.dir)
    print(f'Leyendo OULAD desde {directorio} ...')
    hist, verdad = construir_historial(directorio, args.corte)
    ultimos = hist[hist.es_ultimo_periodo == 1]
    print(f'  {len(hist)} filas alumno-bloque; {hist.cedula.nunique()} estudiantes; '
          f'{len(ultimos)} matrículas.')
    print('  Estado en la última fila de cada matrícula:', ultimos.estado_matricula.value_counts().to_dict())
    if args.solo_resumen:
        return 0

    conn = conectar_admin('master', autocommit=True)
    conn.cursor().execute("IF DB_ID('OULAD_PRUEBAS') IS NULL CREATE DATABASE OULAD_PRUEBAS")
    conn.close()

    conn = conectar_admin('OULAD_PRUEBAS', timeout=60)
    cur = conn.cursor()
    for sql in CREATE_SQL:
        cur.execute(sql)
    conn.commit()

    cur.fast_executemany = True
    registros = list(hist.itertuples(index=False, name=None))
    for i in range(0, len(registros), 50_000):
        cur.executemany(
            """INSERT INTO dbo.historial_bloques
               (cedula, apellidos, nombres, genero, ciudad_residencia, code_module, code_presentation,
                bloque, es_ultimo_periodo, facultad_codigo, facultad_nombre, carrera, estado_matricula,
                promedio, asistencia_pct, fecha_matricula)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], int(r[7]), int(r[8]), r[9], r[10], r[11], r[12],
              float(r[13]), float(r[14]), r[15]) for r in registros[i:i + 50_000]],
        )
        conn.commit()
    cur.executemany(
        "INSERT INTO dbo.verdad_futura VALUES (?, ?, ?, ?, ?)",
        [(r.code_module, r.code_presentation, f'OU{r.id_student}', int(r.bloque_final_real), r.estado_final_real)
         for r in verdad.itertuples()],
    )
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM dbo.historial_bloques')
    print(f'Cargado. OULAD_PRUEBAS.dbo.historial_bloques = {cur.fetchone()[0]} filas; '
          f'verdad_futura = {len(verdad)} matrículas de {PRESENTACION_EN_CURSO}.')
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
