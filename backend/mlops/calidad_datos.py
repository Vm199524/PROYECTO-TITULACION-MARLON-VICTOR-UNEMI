# -*- coding: utf-8 -*-
"""
Calidad de los datos con Great Expectations antes de entrenar o calificar.

Un modelo entrenado con datos defectuosos (promedios fuera de escala,
asistencias negativas, estados desconocidos, matrículas duplicadas) produce
alertas defectuosas sin avisar. Este módulo declara las expectativas que debe
cumplir la trayectoria de cada institución, tal como queda en el almacén
después del ETL, y las valida con Great Expectations (GX Core 1.x, contexto
efímero, sin archivos de configuración):

  - integridad: claves no nulas y matrícula única;
  - dominio: estado de matrícula, modalidad y marca de último periodo dentro
    de su catálogo;
  - rango: promedio entre 0 y 10, asistencia entre 0 y 100, nivel y corte
    positivos, saldos, becas y actividad no negativos;
  - volumen: un mínimo de filas, de estudiantes y de periodos para que el
    modelo sea estimable.

El resultado (cada expectativa con su porcentaje de filas que no la cumplen)
se guarda en ml/modelos/<INSTITUCION>/calidad_datos.json y se muestra en la
página «Calidad del modelo». Si una expectativa CRÍTICA falla, el
entrenamiento no debería ejecutarse: el pipeline lo informa.

Si Great Expectations no está instalado, las mismas reglas se evalúan con
pandas (motor = "pandas") para no dejar el control sin hacer.

Requerimientos que implementa: RF-02 (carga y transformación por perfil), RF-17
    (calificación por lotes y deriva), RNF-04 (calidad predictiva).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import datetime as dt
import logging
import os
from dataclasses import dataclass, field

import pandas as pd

ESTADOS = ['ACTIVO', 'RETIRADO', 'GRADUADO', 'EGRESADO', 'REPROBADO']
MODALIDADES = ['PRESENCIAL', 'HIBRIDA', 'EN LINEA']


@dataclass
class Regla:
    """Una expectativa declarada sobre la trayectoria."""
    tipo: str                      # nombre de la expectativa de GX
    columna: str | None
    descripcion: str
    critica: bool = True
    args: dict = field(default_factory=dict)


def reglas(df: pd.DataFrame) -> list[Regla]:
    """Expectativas aplicables a las columnas presentes en `df`."""
    r = [
        Regla('expect_table_row_count_to_be_between', None, 'Al menos 1 000 filas de trayectoria', True,
              {'min_value': 1000}),
        Regla('expect_column_values_to_be_unique', 'matricula_id', 'Cada matrícula aparece una sola vez'),
    ]
    for c in ('matricula_id', 'alumno_id', 'carrera_id', 'periodo_id', 'estado_codigo', 'fecha'):
        r.append(Regla('expect_column_values_to_not_be_null', c, f'{c} no puede estar vacío'))
    r += [
        Regla('expect_column_values_to_be_in_set', 'estado_codigo', 'Estado de matrícula dentro del catálogo',
              True, {'value_set': ESTADOS}),
        Regla('expect_column_values_to_be_in_set', 'es_ultimo_periodo', 'Marca de último periodo es 0 o 1',
              True, {'value_set': [0, 1]}),
        Regla('expect_column_values_to_be_between', 'promedio', 'Promedio en la escala 0 a 10', True,
              {'min_value': 0, 'max_value': 10}),
        Regla('expect_column_values_to_be_between', 'asistencia_pct', 'Asistencia entre 0 % y 100 %', True,
              {'min_value': 0, 'max_value': 100}),
        Regla('expect_column_values_to_be_between', 'nivel', 'Nivel o semestre positivo', True, {'min_value': 1}),
        Regla('expect_column_values_to_be_between', 'corte', 'Corte de evaluación positivo', True, {'min_value': 1}),
        Regla('expect_column_values_to_not_be_null', 'promedio', 'Promedio registrado (al menos 95 %)', False,
              {'mostly': 0.95}),
        Regla('expect_column_values_to_not_be_null', 'asistencia_pct', 'Asistencia registrada (al menos 95 %)',
              False, {'mostly': 0.95}),
        Regla('expect_column_values_to_be_in_set', 'modalidad_codigo', 'Modalidad dentro del catálogo', False,
              {'value_set': MODALIDADES}),
        Regla('expect_column_unique_value_count_to_be_between', 'periodo_id',
              'Al menos 3 periodos para la validación temporal', True, {'min_value': 3}),
        Regla('expect_column_unique_value_count_to_be_between', 'alumno_id', 'Al menos 300 estudiantes', True,
              {'min_value': 300}),
    ]
    for c, desc in (('saldo_pendiente', 'Saldo pendiente no negativo'), ('beca_porcentaje', 'Beca entre 0 % y 100 %'),
                    ('actividad_lms', 'Actividad en el aula virtual no negativa'),
                    ('dias_sin_actividad', 'Días sin actividad no negativos')):
        args = {'min_value': 0, 'max_value': 100} if c == 'beca_porcentaje' else {'min_value': 0}
        r.append(Regla('expect_column_values_to_be_between', c, desc, False, args))
    return [x for x in r if x.columna is None or x.columna in df.columns]


# ── Motor pandas (respaldo sin GX) ──────────────────────────────────────
def _evaluar_pandas(df: pd.DataFrame, regla: Regla) -> tuple[bool, dict]:
    a, c = regla.args, regla.columna
    if regla.tipo == 'expect_table_row_count_to_be_between':
        return len(df) >= a['min_value'], {'observado': len(df)}
    if regla.tipo == 'expect_column_unique_value_count_to_be_between':
        n = int(df[c].nunique())
        return n >= a['min_value'], {'observado': n}
    s = df[c]
    if regla.tipo == 'expect_column_values_to_not_be_null':
        malos = s.isna()
        base = len(s)
    else:
        validos = s.dropna()
        base = len(validos)
        if regla.tipo == 'expect_column_values_to_be_unique':
            malos = validos.duplicated(keep=False)
        elif regla.tipo == 'expect_column_values_to_be_in_set':
            malos = ~validos.isin(a['value_set'])
        else:
            v = pd.to_numeric(validos, errors='coerce')
            malos = v.isna()
            if 'min_value' in a:
                malos |= v < a['min_value']
            if 'max_value' in a:
                malos |= v > a['max_value']
    n_malos = int(malos.sum())
    pct = 100.0 * n_malos / base if base else 0.0
    ok = (1 - pct / 100) >= a.get('mostly', 1.0)
    return ok, {'filas': base, 'no_cumplen': n_malos, 'porcentaje_no_cumple': round(pct, 4)}


# ── Motor Great Expectations ────────────────────────────────────────────
def _evaluar_gx(df: pd.DataFrame, lista: list[Regla]) -> list[tuple[bool, dict]]:
    import great_expectations as gx
    logging.getLogger('great_expectations').setLevel(logging.ERROR)
    contexto = gx.get_context(mode='ephemeral')
    origen = contexto.data_sources.add_pandas('almacen_academico')
    lote = (origen.add_dataframe_asset('trayectoria').add_batch_definition_whole_dataframe('completa')
            .get_batch(batch_parameters={'dataframe': df}))
    suite = gx.ExpectationSuite(name='trayectoria_academica')
    for i, regla in enumerate(lista):
        clase = getattr(gx.expectations, ''.join(p.capitalize() for p in regla.tipo.split('_')))
        kwargs = dict(regla.args, meta={'regla': i})
        if regla.columna:
            kwargs['column'] = regla.columna
        suite.add_expectation(clase(**kwargs))
    resultado = lote.validate(suite, result_format='SUMMARY')
    # GX no garantiza el orden de los resultados: se emparejan por el índice guardado en `meta`.
    por_regla = {int(res.expectation_config.meta['regla']): res for res in resultado.results}
    salida = []
    for i, regla in enumerate(lista):
        res = por_regla[i]
        r = res.result or {}
        if regla.tipo.startswith(('expect_table', 'expect_column_unique')):
            detalle = {'observado': r.get('observed_value')}
        else:
            detalle = {'filas': r.get('element_count'), 'no_cumplen': r.get('unexpected_count'),
                       'porcentaje_no_cumple': round(float(r.get('unexpected_percent') or 0.0), 4)}
        salida.append((bool(res.success), detalle))
    return salida


def validar(df: pd.DataFrame, institucion: str, forzar_pandas: bool = False) -> dict:
    """Valida la trayectoria de una institución y devuelve el informe de calidad."""
    lista = reglas(df)
    motor = 'pandas'
    if not forzar_pandas:
        try:
            os.environ.setdefault('TQDM_DISABLE', '1')  # GX muestra barras de progreso con tqdm
            import great_expectations
            evaluados = _evaluar_gx(df, lista)
            motor = f'Great Expectations {great_expectations.__version__}'
        except ImportError:
            evaluados = [_evaluar_pandas(df, r) for r in lista]
    else:
        evaluados = [_evaluar_pandas(df, r) for r in lista]
    expectativas = [{'expectativa': r.tipo, 'columna': r.columna, 'descripcion': r.descripcion,
                     'critica': r.critica, 'cumple': ok, **detalle}
                    for r, (ok, detalle) in zip(lista, evaluados)]
    criticas_fallidas = [e for e in expectativas if e['critica'] and not e['cumple']]
    return {
        'institucion': institucion, 'fecha': dt.datetime.now().isoformat(timespec='seconds'), 'motor': motor,
        'filas': int(len(df)), 'evaluadas': len(expectativas),
        'cumplidas': sum(e['cumple'] for e in expectativas),
        'porcentaje_cumplimiento': round(100.0 * sum(e['cumple'] for e in expectativas) / max(len(expectativas), 1), 1),
        'apto_para_entrenar': not criticas_fallidas,
        'criticas_fallidas': [e['descripcion'] for e in criticas_fallidas],
        'expectativas': expectativas,
    }
