"""
Pruebas del panel alumno-periodo (ml/features_abandono.py), sin base de datos.

Verifican las tres propiedades que sostienen la afirmación "el modelo
ANTICIPA el abandono" (sección 1.3 del documento):
  1. La etiqueta de la fila t es el estado del periodo t+1 (no el de t).
  2. Las características de t solo usan información hasta t (sin fuga).
  3. Dos trayectorias del mismo alumno (otra carrera, o una segunda
     matrícula del mismo módulo en OULAD) no se mezclan.
"""

import os
import sys
from datetime import date

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.features_abandono import (  # noqa: E402
    FEATURE_COLUMNS_NUMERICAS, construir_panel_desde_historial, informe_atipicos, matriz_X,
)


def _fila(fact_id, alumno, carrera, mes, sem, prom, asis, saldo, estado, ultimo):
    return {'fact_id': fact_id, 'alumno_id': alumno, 'carrera_id': carrera, 'cedula': str(alumno),
            'apellidos': 'X', 'nombres': 'Y', 'fecha': date(2024, mes, 1), 'anio': 2024,
            'semestre': sem, 'promedio': prom, 'asistencia_pct': asis, 'saldo_pendiente': saldo,
            'beca_porcentaje': 0, 'estado_codigo': estado, 'es_ultimo_periodo': ultimo,
            'facultad_codigo': 'F', 'facultad_nombre': 'Fac', 'carrera': 'C', 'sede_codigo': 'S1',
            'canal_codigo': 'PRESENCIAL'}


HIST = pd.DataFrame([
    # Alumno 1: se retira en el periodo 3.
    _fila(1, 1, 10, 1, 1, 8.0, 90, 0, 'ACTIVO', 0),
    _fila(2, 1, 10, 2, 2, 7.0, 60, 50, 'ACTIVO', 0),
    _fila(3, 1, 10, 3, 3, 5.0, 40, 80, 'RETIRADO', 1),
    # Alumno 2: sigue activo (su último periodo se califica).
    _fila(4, 2, 10, 1, 1, 9.0, 95, 0, 'ACTIVO', 0),
    _fila(5, 2, 10, 2, 2, 9.0, 94, 0, 'ACTIVO', 1),
    # Alumno 3: dos trayectorias del MISMO módulo (repite): la primera
    # termina reprobada, la segunda empieza de nuevo en el periodo 1.
    _fila(6, 3, 20, 1, 1, 4.0, 50, 0, 'ACTIVO', 0),
    _fila(7, 3, 20, 2, 2, 3.0, 45, 0, 'REPROBADO', 1),
    _fila(8, 3, 20, 3, 1, 6.0, 80, 0, 'ACTIVO', 0),
    _fila(9, 3, 20, 4, 2, 6.5, 82, 0, 'ACTIVO', 1),
])


def _panel():
    return construir_panel_desde_historial(HIST).set_index('fact_id')


def test_la_etiqueta_es_el_estado_del_periodo_siguiente():
    p = _panel()
    assert p.loc[2, 'y'] == 1      # el periodo 2 precede al retiro
    assert p.loc[1, 'y'] == 0
    assert np.isnan(p.loc[3, 'y'])  # la fila del retiro no tiene "siguiente"
    assert np.isnan(p.loc[5, 'y'])


def test_las_caracteristicas_solo_usan_el_pasado():
    p = _panel()
    assert p.loc[2, 'asistencia_t'] == 60
    assert p.loc[2, 'asistencia_delta'] == 60 - 90
    assert p.loc[2, 'asistencia_minima_hist'] == 60   # no ve el 40 del periodo 3
    assert p.loc[2, 'pct_periodos_con_mora'] == 0.5
    assert p.loc[1, 'promedio_delta'] == 0.0


def test_no_mezcla_trayectorias_del_mismo_alumno():
    p = _panel()
    assert p.loc[7, 'y'] != p.loc[7, 'y']             # cierre de la 1.a trayectoria: sin siguiente
    assert p.loc[8, 'n_periodos_cursados'] == 1         # la 2.a trayectoria empieza de cero
    assert p.loc[8, 'promedio_minimo_hist'] == 6.0      # no hereda el 3.0 de la anterior
    assert p.loc[8, 'asistencia_delta'] == 0.0


def test_solo_se_califican_trayectorias_activas():
    p = _panel()
    assert set(p.index[p['para_calificar'] == 1]) == {5, 9}


def test_matriz_x_reproduce_las_columnas_del_entrenamiento():
    p = construir_panel_desde_historial(HIST)
    X, cols = matriz_X(p)
    assert list(X.columns[:len(FEATURE_COLUMNS_NUMERICAS)]) == FEATURE_COLUMNS_NUMERICAS
    X2, _ = matriz_X(p.assign(sede_codigo='SEDE_NUEVA'), cols)
    assert list(X2.columns) == list(X.columns) and X2[cols].sum().sum() == len(p)  # canal sí coincide


def test_informe_de_atipicos_no_elimina_filas():
    p = construir_panel_desde_historial(HIST)
    inf = informe_atipicos(p)
    assert set(inf) == {'promedio_t', 'asistencia_t', 'saldo_pendiente_t'}
    assert len(p) == len(HIST)
