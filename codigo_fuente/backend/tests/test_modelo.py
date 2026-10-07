# -*- coding: utf-8 -*-
"""Entrenamiento, calibración, umbrales, explicación y simulador (CRISP-DM: modelado y evaluación)."""
import numpy as np
import pandas as pd
import pytest

from ml.calibracion import CalibradorPlatt
from ml.calificar import calificar_panel, categoria, psi
from ml.caracteristicas import construir_panel, grupos_disponibles, matriz
from ml.entrenar import entrenar_panel, particion_temporal, referencia_psi, umbral_para_recall
from ml.explicacion import recomendaciones
from ml.simulacion import recalcular, simulables


@pytest.fixture(scope='module')
def entrenado(historial):
    panel = construir_panel(historial)
    grupos = grupos_disponibles(historial)
    paquete, metricas, predicciones, oof = entrenar_panel(panel, 'PRUEBA', grupos, intentos_rf=1, pruebas_optuna=1,
                                                          registrar=lambda *_: None)
    return panel, paquete, metricas, predicciones, oof


def test_particion_temporal_reserva_los_periodos_mas_recientes(historial):
    etiquetado = construir_panel(historial)
    etiquetado = etiquetado[etiquetado['y'].notna()].reset_index(drop=True)
    mascara, periodos = particion_temporal(etiquetado)
    assert 0 < mascara.sum() < len(etiquetado)
    assert etiquetado.loc[mascara, 'fecha_inicio'].min() > etiquetado.loc[~mascara, 'fecha_inicio'].max()
    assert periodos == sorted(periodos)


def test_entrenamiento_compara_cuatro_candidatos(entrenado):
    _, paquete, metricas, predicciones, oof = entrenado
    assert set(metricas['comparacion_cv']) == {'RF_PONDERADO', 'RF_SMOTE', 'LOGISTICA', 'LIGHTGBM'}
    assert metricas['modelo_final'] == paquete['nombre_modelo']
    assert 0.5 < metricas['validacion_temporal']['roc_auc'] <= 1.0
    assert len(predicciones) == metricas['panel']['prueba'] and len(oof) == metricas['panel']['entrenamiento']


def test_umbrales_ordenados_y_con_el_recall_pedido(entrenado):
    _, paquete, _, _, oof = entrenado
    assert 0 < paquete['umbral_medio'] <= paquete['umbral_alto'] < 1
    y, p = oof['y'].to_numpy(), oof['probabilidad'].to_numpy()
    assert ((p >= paquete['umbral_medio']) & (y == 1)).sum() / y.sum() >= 0.80 - 1e-9


def test_calificacion_de_activos(entrenado):
    panel, paquete, _, _, _ = entrenado
    activos = calificar_panel(panel, paquete)
    assert len(activos) == int(panel['para_calificar'].sum())
    assert activos['probabilidad'].between(0, 1).all()
    assert set(activos['riesgo_categoria']) <= {'ALTO', 'MEDIO', 'BAJO'}
    fila = activos.iloc[0]
    assert len(fila['explicacion']) > 0 and '_estado' in fila['caracteristicas']


def test_simulador_sin_cambios_reproduce_las_variables(entrenado):
    """Con los valores actuales, el simulador debe reconstruir exactamente lo que vio el modelo."""
    panel, paquete, _, _, _ = entrenado
    activos = calificar_panel(panel, paquete)
    for _, fila in activos.head(25).iterrows():
        caract = {k: v for k, v in fila['caracteristicas'].items() if k != '_estado'}
        estado = fila['caracteristicas']['_estado']
        cambios = {'promedio': estado['promedio_actual'], 'asistencia_pct': estado['asistencia_pct_actual'],
                   'saldo_pendiente': estado.get('saldo_pendiente_actual') or 0.0}
        nuevo = recalcular(caract, estado, cambios)
        for clave, valor in caract.items():
            if valor is None:
                continue
            tolerancia = 0.08 if clave.endswith('pct_cohorte') else 1e-4
            assert nuevo[clave] == pytest.approx(valor, abs=tolerancia), clave


def test_simulador_mejorar_asistencia_no_sube_el_riesgo(entrenado):
    panel, paquete, _, _, _ = entrenado
    activos = calificar_panel(panel, paquete).sort_values('probabilidad', ascending=False)
    fila = activos.iloc[0]
    caract = {k: v for k, v in fila['caracteristicas'].items() if k != '_estado'}
    estado = fila['caracteristicas']['_estado']
    mejor = recalcular(caract, estado, {'asistencia_pct': 100, 'promedio': 10})
    X0 = pd.DataFrame([caract])[paquete['columnas']].astype(float)
    X1 = pd.DataFrame([mejor])[paquete['columnas']].astype(float)
    p0 = paquete['calibrador'].predict(paquete['modelo'].predict_proba(X0)[:, 1])[0]
    p1 = paquete['calibrador'].predict(paquete['modelo'].predict_proba(X1)[:, 1])[0]
    assert p1 <= p0 + 0.02


def test_simulables_segun_grupos():
    assert set(simulables(['promedio_t', 'en_mora_t'])) == {'promedio', 'asistencia_pct', 'saldo_pendiente'}


def test_calibrador_platt_es_monotono():
    rng = np.random.default_rng(1)
    puntaje = rng.random(2000)
    y = (rng.random(2000) < puntaje ** 2).astype(int)
    cal = CalibradorPlatt().fit(puntaje, y)
    p = cal.predict(np.linspace(0.01, 0.99, 50))
    assert np.all(np.diff(p) >= -1e-12) and p.min() >= 0 and p.max() <= 1


def test_umbral_para_recall():
    y = np.array([0, 0, 1, 1, 0, 1, 0, 1])
    p = np.array([0.1, 0.2, 0.9, 0.8, 0.3, 0.6, 0.4, 0.7])
    u = umbral_para_recall(y, p, 0.75)
    assert ((p >= u) & (y == 1)).sum() / y.sum() >= 0.75


@pytest.mark.parametrize('p,esperado', [(0.9, 'ALTO'), (0.3, 'MEDIO'), (0.05, 'BAJO')])
def test_categoria(p, esperado):
    assert categoria(p, umbral_alto=0.5, umbral_medio=0.2) == esperado


def test_psi_detecta_deriva():
    rng = np.random.default_rng(3)
    base = pd.DataFrame({'x': rng.normal(0, 1, 5000)})
    ref = referencia_psi(base, ['x'])['x']
    assert psi(ref, pd.Series(rng.normal(0, 1, 3000))) < 0.1
    assert psi(ref, pd.Series(rng.normal(1.5, 1, 3000))) > 0.25


def test_recomendaciones_por_factor():
    detalle = [{'variable': 'asistencia_t', 'descripcion': 'asistencia', 'contribucion': 0.4, 'valor': 52.0},
               {'variable': 'en_mora_t', 'descripcion': 'mora', 'contribucion': 0.2, 'valor': 1.0},
               {'variable': 'promedio_t', 'descripcion': 'promedio', 'contribucion': -0.1, 'valor': 8.0}]
    tipos = [r['tipo'] for r in recomendaciones(detalle)]
    assert tipos == ['ASISTENCIA', 'ECONOMICO']  # lo que baja el riesgo no genera recomendación
