# -*- coding: utf-8 -*-
"""Validación por periodo y carrera, origen móvil, calidad de datos, deriva, MLflow y anonimización."""
import json

import numpy as np
import pandas as pd
import pytest

from ml.caracteristicas import construir_panel, grupos_disponibles, matriz, variables_modelo
from ml.entrenar import _lgbm, LGBM_POR_DEFECTO, entrenar_panel, filas_evaluacion
from ml.evaluacion_grupos import metricas_por_grupo, resumen_origen_movil, validacion_origen_movil
from mlops.calidad_datos import validar
from mlops.deriva import informe_deriva
from mlops.registro_mlflow import parametros_y_metricas, registrar_entrenamiento
from scripts.anonimizar_carrera import anonimizar, seudonimo


@pytest.fixture(scope='module')
def entrenado(historial):
    panel = construir_panel(historial)
    paquete, metricas, predicciones, _ = entrenar_panel(panel, 'PRUEBA', grupos_disponibles(historial), intentos_rf=1,
                                                        pruebas_optuna=0, registrar=lambda *_: None, origenes=2)
    return panel, paquete, metricas, predicciones


# ── Validación desagregada ───────────────────────────────────────────────
def test_metricas_por_grupo_cubren_toda_la_prueba(entrenado):
    _, _, metricas, predicciones = entrenado
    assert sum(f['n'] for f in metricas['por_periodo']) == len(predicciones)
    assert sum(f['n'] for f in metricas['por_carrera']) == len(predicciones)
    assert [f['grupo'] for f in metricas['por_periodo']] == metricas['validacion_temporal']['periodos']


def test_grupo_pequeno_no_reporta_auc():
    df = pd.DataFrame({'y': [0, 1] * 20, 'probabilidad': np.linspace(0, 1, 40), 'g': 'A'})
    fila = metricas_por_grupo(df, 'g', 0.5, 0.8)[0]
    assert fila['evaluable'] is False and fila['roc_auc'] is None
    assert fila['recall_medio'] is not None


def test_recall_por_grupo_coincide_con_la_definicion():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 1000)
    p = np.clip(y * 0.3 + rng.random(1000) * 0.7, 0, 1)
    fila = metricas_por_grupo(pd.DataFrame({'y': y, 'probabilidad': p, 'g': 'X'}), 'g', 0.5, 0.8)[0]
    esperado = ((p >= 0.5) & (y == 1)).sum() / y.sum()
    assert fila['recall_medio'] == pytest.approx(esperado, abs=1e-4)


def test_origen_movil_entrena_solo_con_el_pasado(historial):
    panel = construir_panel(historial)
    etiquetado = panel[panel['y'].notna()].reset_index(drop=True)
    etiquetado['y'] = etiquetado['y'].astype(int)
    columnas = variables_modelo(grupos_disponibles(historial))
    filas = validacion_origen_movil(etiquetado, columnas, _lgbm(dict(LGBM_POR_DEFECTO, n_estimators=50)), matriz,
                                    origenes=2, registrar=lambda *_: None)
    assert filas, 'debe evaluar al menos un origen'
    orden = list(etiquetado.groupby('periodo_codigo')['fecha_inicio'].min().sort_values().index)
    for f in filas:
        assert f['periodos_entrenamiento'] == orden.index(f['periodo'])
        assert f['umbral_alto'] >= f['umbral_medio']
    assert resumen_origen_movil(filas)['origenes'] == sum(f['roc_auc'] is not None for f in filas)


def test_metricas_desagregadas_se_publican_en_el_almacen(entrenado):
    _, _, metricas, _ = entrenado
    esquemas = {f[3] for f in filas_evaluacion('PRUEBA', metricas)}
    assert {'POR_PERIODO', 'POR_CARRERA', 'TEMPORAL'} <= esquemas
    assert all(len(f[7] or '') <= 60 for f in filas_evaluacion('PRUEBA', metricas))


# ── Calidad de datos ─────────────────────────────────────────────────────
def test_calidad_aprueba_datos_validos(historial):
    informe = validar(historial, 'PRUEBA')
    assert informe['apto_para_entrenar'], informe['criticas_fallidas']
    assert informe['evaluadas'] >= 15


@pytest.mark.parametrize('forzar_pandas', [False, True])
def test_calidad_detecta_promedio_fuera_de_escala_y_duplicados(historial, forzar_pandas):
    malo = historial.copy()
    malo.loc[malo.index[:5], 'promedio'] = 15.0
    malo = pd.concat([malo, malo.iloc[:3]])
    informe = validar(malo, 'PRUEBA', forzar_pandas=forzar_pandas)
    assert not informe['apto_para_entrenar']
    fallidas = {e['descripcion'] for e in informe['expectativas'] if not e['cumple']}
    assert 'Promedio en la escala 0 a 10' in fallidas
    assert 'Cada matrícula aparece una sola vez' in fallidas


def test_motores_de_calidad_coinciden(historial):
    a = validar(historial, 'PRUEBA')
    b = validar(historial, 'PRUEBA', forzar_pandas=True)
    assert [e['cumple'] for e in a['expectativas']] == [e['cumple'] for e in b['expectativas']]


# ── Deriva ───────────────────────────────────────────────────────────────
def test_deriva_detecta_un_cambio_de_distribucion():
    rng = np.random.default_rng(3)
    ref = pd.DataFrame({'a': rng.normal(0, 1, 3000), 'b': rng.normal(0, 1, 3000)})
    act = pd.DataFrame({'a': rng.normal(1.5, 1, 1500), 'b': rng.normal(0, 1, 1500)})
    r = informe_deriva(ref, act, 'PRUEBA', importancia={'a': 0.2, 'b': 0.1})
    por_variable = {v['variable']: v for v in r['variables']}
    assert por_variable['a']['deriva'] and not por_variable['b']['deriva']
    assert por_variable['a']['psi'] > 0.25
    assert r['importantes_con_deriva'] == ['a']


# ── MLflow ───────────────────────────────────────────────────────────────
def test_metricas_se_aplanan_para_mlflow(entrenado):
    _, _, metricas, _ = entrenado
    params, met = parametros_y_metricas(metricas)
    assert params['modelo_final'] == metricas['modelo_final']
    assert met['temporal_roc_auc'] == metricas['validacion_temporal']['roc_auc']
    assert all(isinstance(v, float) for v in met.values())


def test_registro_en_mlflow(entrenado, tmp_path, monkeypatch):
    pytest.importorskip('mlflow')
    _, _, metricas, _ = entrenado
    monkeypatch.setenv('MLFLOW_TRACKING_URI', f'sqlite:///{(tmp_path / "m.db").as_posix()}')
    import mlops.registro_mlflow as reg
    monkeypatch.setattr(reg, 'DIR_MLFLOW', tmp_path)
    (tmp_path / 'metricas.json').write_text(json.dumps(metricas, default=str), encoding='utf-8')
    resumen = registrar_entrenamiento('PRUEBA', tmp_path, metricas, registrar=lambda *_: None)
    assert resumen and len(resumen['run_id']) == 32
    import mlflow
    run = mlflow.get_run(resumen['run_id'])
    assert run.data.metrics['temporal_roc_auc'] == pytest.approx(metricas['validacion_temporal']['roc_auc'])


# ── Anonimización de una carrera real ────────────────────────────────────
def _extracto(n=60):
    filas = []
    for i in range(n):
        for p in ('2024-1', '2024-2'):
            filas.append({'cedula': f'09{i:08d}', 'apellidos': 'Real', 'nombres': 'Persona', 'genero': 'F' if i % 2 else 'M',
                          'ciudad_residencia': 'Milagro' if i < n - 2 else f'Pueblo{i}', 'facultad_codigo': 'FACI',
                          'facultad_nombre': 'Ciencias e Ingeniería', 'carrera': 'TI', 'sede_codigo': 'MIL',
                          'sede_nombre': 'Milagro', 'modalidad': 'EN LINEA', 'periodo_academico': p,
                          'inicio_periodo': '2024-05-01', 'nivel': 1, 'corte': 1, 'estado_matricula': 'ACTIVO',
                          'promedio': 8.0, 'asistencia_pct': 90.0, 'fecha_corte': '2024-05-01', 'es_ultimo_periodo': 0,
                          'telefono': '0999999999', 'correo': 'x@unemi.edu.ec'})
    return pd.DataFrame(filas)


def test_anonimizacion_minimiza_y_seudonimiza():
    clave = b'clave-de-prueba-larga-123'
    df = _extracto()
    out, informe = anonimizar(df, clave, k=5, suprimir=True)
    assert 'telefono' not in out and 'correo' not in out
    assert set(informe['columnas_descartadas']) == {'telefono', 'correo'}
    assert not out['cedula'].isin(df['cedula']).any()
    assert (out['apellidos'] == 'Estudiante').all()
    assert out.groupby('cedula')['periodo_academico'].nunique().eq(2).all(), 'el seudónimo es estable entre periodos'
    assert informe['k_alcanzado'] >= 5
    assert 'Pueblo58' not in set(out['ciudad_residencia'])


def test_seudonimo_depende_de_la_clave():
    assert seudonimo('0912345678', b'a' * 20) != seudonimo('0912345678', b'b' * 20)
    assert len(seudonimo('0912345678', b'a' * 20)) == 10


def test_anonimizacion_exige_clave_larga():
    with pytest.raises(ValueError):
        anonimizar(_extracto(), b'corta')
