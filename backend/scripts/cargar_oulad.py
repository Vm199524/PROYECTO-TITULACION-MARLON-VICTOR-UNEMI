# -*- coding: utf-8 -*-
"""
Carga de OULAD como segunda institución (datos reales anonimizados).

Open University Learning Analytics Dataset (Kuzilek, Hlosta y Zdrahal, 2017,
Scientific Data 4:170171, licencia CC BY 4.0). Se carga en la base
operativa OULAD_PRUEBAS.dbo.historial_bloques, con la forma de su propio
sistema académico; el ETL la lleva al almacén con el perfil OULAD_UK.

Transformación (solo información disponible al cierre de cada corte):
  - Periodo académico = presentación del módulo (2013B, 2013J, 2014B, 2014J).
    Cada presentación se divide en cortes de seguimiento de 28 días.
  - asistencia_pct: días con actividad en el aula virtual dentro del corte /
    días del corte x 100.
  - clics: interacciones en el aula virtual dentro del corte.
  - dias_sin_actividad: días transcurridos desde la última actividad hasta el
    cierre del corte.
  - evaluaciones: con plazo vencido al cierre del corte (sin el examen
    final), entregadas hasta esa fecha, entregadas fuera de plazo y nota
    media de las entregadas (0 a 10).
  - promedio: media (0 a 10) de las evaluaciones vencidas, donde una no
    entregada cuenta 0 (si aún no vence ninguna, 0 para todo el módulo).
  - creditos (studied_credits), intentos previos (num_of_prev_attempts) y
    día de registro respecto al inicio (date_registration).
  - estado: ACTIVO hasta el corte que contiene la fecha de retiro, que pasa a
    RETIRADO y es el último; quien completa queda GRADUADO (Pass o
    Distinction) o REPROBADO (Fail). Los retiros antes del día 0 quedan como
    una sola fila RETIRADO en el corte 1 (no anticipables).

Presentación "en curso": la más reciente (2014J) se carga solo hasta el
corte --corte (3 por defecto, 12 semanas), como si estuviera en marcha: quien
sigue matriculado queda ACTIVO y es a quien el modelo califica. Lo que pasó
después se guarda en dbo.verdad_futura, que NO pasa al almacén, para una
evaluación prospectiva honesta.

Uso:
    cd backend
    python -m scripts.cargar_oulad [--dir ../datos/externos/oulad] [--corte 3]

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
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

DIR_POR_DEFECTO = Path(__file__).resolve().parents[2] / 'datos' / 'externos' / 'oulad'
DIAS_CORTE = 28
PRESENTACION_EN_CURSO = '2014J'

# Tabla 1 de Kuzilek et al. (2017).
DOMINIO = {
    'AAA': ('SOC', 'Social Sciences'), 'BBB': ('SOC', 'Social Sciences'), 'GGG': ('SOC', 'Social Sciences'),
    'CCC': ('STEM', 'Science, Technology, Engineering and Mathematics'),
    'DDD': ('STEM', 'Science, Technology, Engineering and Mathematics'),
    'EEE': ('STEM', 'Science, Technology, Engineering and Mathematics'),
    'FFF': ('STEM', 'Science, Technology, Engineering and Mathematics'),
}
CLAVE = ['code_module', 'code_presentation', 'id_student']


def inicio_presentacion(codigo: str) -> date:
    """Inicio aproximado de una presentación: B = febrero, J = octubre (día 1; OULAD no publica el día)."""
    return date(int(codigo[:4]), 2 if codigo[4] == 'B' else 10, 1)


def _num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors='coerce')


def actividad_por_corte(directorio: Path) -> pd.DataFrame:
    """Días activos, clics y último día con actividad por estudiante, módulo y corte."""
    vle = pd.read_csv(directorio / 'studentVle.csv',
                      usecols=['code_module', 'code_presentation', 'id_student', 'date', 'sum_click'],
                      dtype={'code_module': 'category', 'code_presentation': 'category', 'id_student': 'int32',
                             'date': 'int16', 'sum_click': 'int32'})
    vle['corte'] = (vle['date'].clip(lower=0) // DIAS_CORTE + 1).astype('int16')
    g = vle.groupby(CLAVE + ['corte'], observed=True)
    salida = pd.concat([g['date'].nunique().rename('dias_activos'), g['sum_click'].sum().rename('clics'),
                        g['date'].max().rename('ultimo_dia')], axis=1).reset_index()
    for c in ('code_module', 'code_presentation'):
        salida[c] = salida[c].astype(str)
    return salida


def evaluaciones_por_corte(directorio: Path, cortes: pd.DataFrame) -> pd.DataFrame:
    """Evaluaciones vencidas, entregadas, tardías, nota media y promedio al cierre de cada corte."""
    ev = pd.read_csv(directorio / 'assessments.csv')
    ev = ev[ev['assessment_type'] != 'Exam'].copy()
    ev['date'] = _num(ev['date'])
    ev = ev.dropna(subset=['date'])
    sa = pd.read_csv(directorio / 'studentAssessment.csv')
    sa['score'] = _num(sa['score'])
    sa['date_submitted'] = _num(sa['date_submitted'])
    sa = sa.merge(ev[['id_assessment', 'code_module', 'code_presentation', 'date']], on='id_assessment')
    sa['tardia'] = (sa['date_submitted'] > sa['date']).astype(int)

    partes = []
    for (modulo, pres), grupo in cortes.groupby(['code_module', 'code_presentation']):
        ev_mp = ev[(ev.code_module == modulo) & (ev.code_presentation == pres)]
        sa_mp = sa[(sa.code_module == modulo) & (sa.code_presentation == pres)]
        for corte in sorted(grupo['corte'].unique()):
            fin = corte * DIAS_CORTE
            vencidas = ev_mp[ev_mp['date'] < fin]
            estudiantes = grupo.loc[grupo['corte'] == corte, 'id_student'].to_numpy()
            entregadas = sa_mp[sa_mp.id_assessment.isin(vencidas.id_assessment) & (sa_mp.date_submitted < fin)]
            agg = entregadas.groupby('id_student').agg(entregadas=('id_assessment', 'count'),
                                                       tardias=('tardia', 'sum'), nota=('score', 'mean'),
                                                       suma=('score', 'sum')).reindex(estudiantes)
            n_venc = len(vencidas)
            promedio = (agg['suma'].fillna(0.0) / n_venc / 10.0).clip(0, 10) if n_venc else pd.Series(0.0, index=agg.index)
            partes.append(pd.DataFrame({
                'code_module': modulo, 'code_presentation': pres, 'id_student': estudiantes, 'corte': corte,
                'evaluaciones_vencidas': n_venc, 'evaluaciones_entregadas': agg['entregadas'].fillna(0).to_numpy(),
                'evaluaciones_tardias': agg['tardias'].fillna(0).to_numpy(),
                'nota_evaluaciones': (agg['nota'] / 10.0).round(2).to_numpy(),
                'promedio': promedio.round(2).to_numpy(),
            }))
    return pd.concat(partes, ignore_index=True)


def construir_historial(directorio: Path, corte_en_curso: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Transforma OULAD en filas estudiante-corte con la forma de la base operativa.

    Returns:
        (filas para dbo.historial_bloques, verdad futura de la presentación en curso).
    """
    info = pd.read_csv(directorio / 'studentInfo.csv')
    reg = pd.read_csv(directorio / 'studentRegistration.csv')
    cursos = pd.read_csv(directorio / 'courses.csv')
    reg['date_registration'] = _num(reg['date_registration'])
    reg['date_unregistration'] = _num(reg['date_unregistration'])
    m = info.merge(reg, on=CLAVE, how='left').merge(cursos, on=['code_module', 'code_presentation'], how='left')
    m['n_cortes'] = np.ceil(m['module_presentation_length'] / DIAS_CORTE).astype(int)

    retirado = m['final_result'] == 'Withdrawn'
    du = m['date_unregistration']
    m['ultimo_corte'] = m['n_cortes']
    m.loc[retirado, 'ultimo_corte'] = np.where(
        du[retirado] >= 0, (du[retirado] // DIAS_CORTE + 1).clip(upper=m.loc[retirado, 'n_cortes']), 1).astype(int)
    m['estado_final'] = np.select([retirado, m['final_result'].isin(['Pass', 'Distinction'])],
                                  ['RETIRADO', 'GRADUADO'], default='REPROBADO')

    en_curso = m['code_presentation'] == PRESENTACION_EN_CURSO
    verdad = m.loc[en_curso, CLAVE + ['ultimo_corte', 'estado_final']].copy()
    verdad.columns = CLAVE + ['corte_final_real', 'estado_final_real']

    m['cortes_cargados'] = np.where(en_curso, np.minimum(m['ultimo_corte'], corte_en_curso), m['ultimo_corte'])
    filas = m.loc[m.index.repeat(m['cortes_cargados'])].copy()
    filas['corte'] = filas.groupby(level=0).cumcount() + 1
    filas = filas.reset_index(drop=True)
    es_ultimo = filas['corte'] == filas['cortes_cargados']
    filas['es_ultimo_periodo'] = es_ultimo.astype(int)
    filas['estado_matricula'] = np.where(es_ultimo & (filas['corte'] == filas['ultimo_corte']),
                                         filas['estado_final'], 'ACTIVO')

    print('  Actividad en el aula virtual por corte (studentVle, 10,6 M filas) ...')
    act = actividad_por_corte(directorio)
    filas = filas.merge(act, on=CLAVE + ['corte'], how='left')
    filas['dias_activos'] = filas['dias_activos'].fillna(0)
    filas['clics'] = filas['clics'].fillna(0).astype(int)
    dias_corte = np.minimum(DIAS_CORTE, filas['module_presentation_length'] - (filas['corte'] - 1) * DIAS_CORTE).clip(lower=1)
    filas['asistencia_pct'] = (filas['dias_activos'] / dias_corte * 100).clip(0, 100).round(2)
    filas = filas.sort_values(CLAVE + ['corte'])
    ultimo = filas.groupby(CLAVE)['ultimo_dia'].ffill()
    filas['dias_sin_actividad'] = (filas['corte'] * DIAS_CORTE - 1 - ultimo).fillna(filas['corte'] * DIAS_CORTE)
    filas['dias_sin_actividad'] = filas['dias_sin_actividad'].clip(lower=0).astype(int)

    print('  Evaluaciones y promedio por corte (studentAssessment) ...')
    evals = evaluaciones_por_corte(directorio, filas[CLAVE + ['corte']])
    filas = filas.merge(evals, on=CLAVE + ['corte'], how='left')
    filas['promedio'] = filas['promedio'].fillna(0.0)

    inicio = filas['code_presentation'].map(inicio_presentacion)
    filas['inicio_presentacion'] = inicio
    filas['fecha_corte'] = [i + timedelta(days=(c - 1) * DIAS_CORTE) for i, c in zip(inicio, filas['corte'])]
    filas['cedula'] = 'OU' + filas['id_student'].astype(str)
    filas['apellidos'] = 'Estudiante OU'
    filas['nombres'] = filas['id_student'].astype(str)
    filas['genero'] = filas['gender']
    filas['ciudad_residencia'] = filas['region'].str.slice(0, 50)
    filas['facultad_codigo'] = filas['code_module'].map(lambda c: DOMINIO[c][0])
    filas['facultad_nombre'] = filas['code_module'].map(lambda c: DOMINIO[c][1])
    filas['carrera'] = 'Modulo ' + filas['code_module']
    filas['creditos'] = filas['studied_credits'].astype(int)
    filas['intentos_previos'] = filas['num_of_prev_attempts'].astype(int)
    filas['dia_registro'] = filas['date_registration'].round().astype('Int64')

    columnas = ['cedula', 'apellidos', 'nombres', 'genero', 'ciudad_residencia', 'code_module', 'code_presentation',
                'inicio_presentacion', 'corte', 'es_ultimo_periodo', 'facultad_codigo', 'facultad_nombre', 'carrera',
                'estado_matricula', 'promedio', 'asistencia_pct', 'fecha_corte', 'creditos', 'intentos_previos',
                'dia_registro', 'clics', 'dias_sin_actividad', 'evaluaciones_vencidas', 'evaluaciones_entregadas',
                'evaluaciones_tardias', 'nota_evaluaciones']
    return filas[columnas].reset_index(drop=True), verdad


TABLAS_SQL = [
    "IF OBJECT_ID('dbo.historial_bloques', 'U') IS NOT NULL DROP TABLE dbo.historial_bloques",
    """CREATE TABLE dbo.historial_bloques (
        id INT IDENTITY(1,1) PRIMARY KEY, cedula VARCHAR(15) NOT NULL, apellidos NVARCHAR(100) NOT NULL,
        nombres NVARCHAR(100) NOT NULL, genero CHAR(1) NOT NULL, ciudad_residencia NVARCHAR(50) NOT NULL,
        code_module VARCHAR(3) NOT NULL, code_presentation VARCHAR(5) NOT NULL, inicio_presentacion DATE NOT NULL,
        corte TINYINT NOT NULL, es_ultimo_periodo BIT NOT NULL, facultad_codigo VARCHAR(20) NOT NULL,
        facultad_nombre NVARCHAR(200) NOT NULL, carrera NVARCHAR(150) NOT NULL, estado_matricula VARCHAR(20) NOT NULL,
        promedio DECIMAL(4,2) NOT NULL, asistencia_pct DECIMAL(5,2) NOT NULL, fecha_corte DATE NOT NULL,
        creditos SMALLINT NOT NULL, intentos_previos TINYINT NOT NULL, dia_registro SMALLINT NULL, clics INT NOT NULL,
        dias_sin_actividad SMALLINT NOT NULL, evaluaciones_vencidas SMALLINT NOT NULL,
        evaluaciones_entregadas SMALLINT NOT NULL, evaluaciones_tardias SMALLINT NOT NULL,
        nota_evaluaciones DECIMAL(4,2) NULL)""",
    "IF OBJECT_ID('dbo.verdad_futura', 'U') IS NOT NULL DROP TABLE dbo.verdad_futura",
    """CREATE TABLE dbo.verdad_futura (
        code_module VARCHAR(3) NOT NULL, code_presentation VARCHAR(5) NOT NULL, cedula VARCHAR(15) NOT NULL,
        corte_final_real TINYINT NOT NULL, estado_final_real VARCHAR(20) NOT NULL,
        PRIMARY KEY (code_module, code_presentation, cedula))""",
]


def _valor(v):
    if v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    return v


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dir', default=str(DIR_POR_DEFECTO))
    parser.add_argument('--corte', type=int, default=3, help='Cortes cargados de la presentación en curso')
    parser.add_argument('--solo-resumen', action='store_true')
    args = parser.parse_args()

    directorio = Path(args.dir)
    print(f'Leyendo OULAD desde {directorio} ...')
    hist, verdad = construir_historial(directorio, args.corte)
    ultimos = hist[hist.es_ultimo_periodo == 1]
    print(f'  {len(hist)} filas estudiante-corte; {hist.cedula.nunique()} estudiantes; {len(ultimos)} matrículas.')
    print('  Estado final:', ultimos.estado_matricula.value_counts().to_dict())
    if args.solo_resumen:
        return 0

    from core.db import conectar_admin
    conn = conectar_admin('master', autocommit=True)
    conn.cursor().execute("IF DB_ID('OULAD_PRUEBAS') IS NULL CREATE DATABASE OULAD_PRUEBAS")
    conn.close()
    conn = conectar_admin('OULAD_PRUEBAS', tiempo=120)
    cur = conn.cursor()
    for sql in TABLAS_SQL:
        cur.execute(sql)
    conn.commit()
    columnas = list(hist.columns)
    cur.fast_executemany = True
    registros = [tuple(_valor(v) for v in fila) for fila in hist.itertuples(index=False, name=None)]
    sql = f"INSERT INTO dbo.historial_bloques ({', '.join(columnas)}) VALUES ({', '.join('?' * len(columnas))})"
    for i in range(0, len(registros), 50_000):
        cur.executemany(sql, registros[i:i + 50_000])
        conn.commit()
    cur.executemany('INSERT INTO dbo.verdad_futura VALUES (?, ?, ?, ?, ?)',
                    [(r.code_module, r.code_presentation, f'OU{r.id_student}', int(r.corte_final_real),
                      r.estado_final_real) for r in verdad.itertuples()])
    conn.commit()
    conn.close()
    print(f'Cargado: {len(registros)} filas en OULAD_PRUEBAS.dbo.historial_bloques; '
          f'{len(verdad)} matrículas de {PRESENTACION_EN_CURSO} en verdad_futura.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
