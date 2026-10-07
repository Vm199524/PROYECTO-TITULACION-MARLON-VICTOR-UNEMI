# -*- coding: utf-8 -*-
"""
Entrenamiento y validación del modelo de abandono de una institución.

Un modelo por institución: los datos de dos instituciones nunca se mezclan.
El procedimiento sigue este orden, y ningún paso usa los datos de prueba para
decidir nada:

  1. Partición temporal por cohortes: los periodos académicos más recientes,
     hasta reunir al menos el 25 % de las filas etiquetadas, quedan
     reservados como prueba. Así se simula el uso real: entrenar con el
     pasado y predecir el futuro.
  2. Validación cruzada agrupada por estudiante (StratifiedGroupKFold, 5
     pliegues) sobre el resto: un mismo estudiante nunca está a la vez en
     entrenamiento y prueba.
  3. Comparación, con los mismos pliegues, de cuatro algoritmos: Random Forest
     con ponderación de clases (técnica declarada en el Avance 1), Random
     Forest con SMOTE solo en el entrenamiento de cada pliegue, regresión
     logística (línea base interpretable) y LightGBM (gradient boosting).
     Los hiperparámetros de los dos más flexibles se ajustan con búsqueda
     aleatoria (Random Forest) y optimización bayesiana con Optuna (LightGBM),
     siempre dentro del entrenamiento.
  4. Se elige el de mayor ROC-AUC medio (desempate por PR-AUC).
  5. Calibración de Platt sobre las predicciones fuera de pliegue: la
     probabilidad que ve la autoridad se parece a una frecuencia observada,
     no a un puntaje arbitrario.
  6. Dos umbrales sobre esas predicciones calibradas: MEDIO detecta al menos
     el 80 % de los abandonos (no dejar pasar casos) y ALTO al menos el 50 %
     con mucha mayor precisión (dónde intervenir primero).
  7. Prueba temporal, una sola vez: ROC-AUC, PR-AUC, Brier, recall y
     precisión en cada umbral, captura del 10 % de mayor riesgo, curva de
     calibración, equidad por género y modalidad, e importancia por
     permutación.
  8. Modelo final reentrenado con todas las filas etiquetadas, guardado junto
     con su calibrador, umbrales y la distribución de referencia para vigilar
     la deriva de los datos.

Uso:
    cd backend
    python -m ml.entrenar --institucion UNEMI_PRUEBAS
    python -m ml.entrenar --institucion OULAD_UK --pruebas-optuna 20

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score,
                             roc_curve)
from sklearn.model_selection import ParameterSampler, StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.calibracion import CalibradorPlatt  # noqa: E402
from ml.caracteristicas import construir_panel, grupos_disponibles, matriz, variables_modelo  # noqa: E402

RAIZ_MODELOS = Path(__file__).resolve().parent / 'modelos'
VERSION = '3.0'
SEMILLA = 20260909
RECALL_MEDIO = 0.80
RECALL_ALTO = 0.50
FRACCION_PRUEBA = 0.25

ESPACIO_RF = {
    'n_estimators': [300, 400, 500],
    'max_depth': [8, 10, 12, 16, None],
    'min_samples_leaf': [2, 5, 10, 20],
    'max_features': ['sqrt', 0.3, 0.5],
}
# Valores de partida: regularización fuerte (pocas hojas, muchas muestras por hoja), lo que mejor
# funcionó con un abandono poco frecuente en la búsqueda exploratoria sobre OULAD.
LGBM_POR_DEFECTO = dict(n_estimators=600, learning_rate=0.015, num_leaves=12, min_child_samples=250,
                        subsample=0.7, subsample_freq=1, colsample_bytree=0.9, reg_lambda=0.5)


def _r(x, d: int = 4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


# ── Partición temporal ───────────────────────────────────────────────────
def particion_temporal(etiquetado: pd.DataFrame, fraccion: float = FRACCION_PRUEBA) -> tuple[np.ndarray, list[str]]:
    """Marca como prueba los periodos académicos más recientes (≥ `fraccion` de las filas).

    Returns:
        (máscara booleana de prueba, códigos de los periodos reservados).
    """
    periodos = (etiquetado.groupby(['periodo_id', 'periodo_codigo'])
                .agg(inicio=('fecha_inicio', 'min'), filas=('y', 'size'))
                .reset_index().sort_values('inicio', ascending=False))
    reservados, acumulado = [], 0
    for fila in periodos.itertuples():
        if acumulado >= fraccion * len(etiquetado):
            break
        reservados.append(fila.periodo_id)
        acumulado += fila.filas
    if len(reservados) == len(periodos):  # siempre debe quedar algo para entrenar
        reservados = reservados[:-1]
    mascara = etiquetado['periodo_id'].isin(reservados).to_numpy()
    codigos = periodos[periodos.periodo_id.isin(reservados)].sort_values('inicio')['periodo_codigo'].tolist()
    return mascara, codigos


# ── Modelos candidatos ───────────────────────────────────────────────────
def _lgbm(params: dict):
    import lightgbm as lgb
    return lgb.LGBMClassifier(**params, is_unbalance=True, random_state=SEMILLA, verbose=-1, n_jobs=-1)


def candidatos(params_rf: dict, params_lgbm: dict) -> dict:
    """Los cuatro algoritmos que se comparan, sin entrenar."""
    from imblearn.over_sampling import SMOTE
    from imblearn.pipeline import Pipeline as PipelineImb
    return {
        'RF_PONDERADO': RandomForestClassifier(class_weight='balanced_subsample', random_state=SEMILLA,
                                               n_jobs=-1, **params_rf),
        'RF_SMOTE': PipelineImb([
            ('imputar', SimpleImputer(strategy='median')),
            ('smote', SMOTE(random_state=SEMILLA)),
            ('rf', RandomForestClassifier(random_state=SEMILLA, n_jobs=-1, **params_rf)),
        ]),
        'LOGISTICA': make_pipeline(SimpleImputer(strategy='median', add_indicator=True), StandardScaler(),
                                   LogisticRegression(class_weight='balanced', max_iter=3000)),
        'LIGHTGBM': _lgbm(params_lgbm),
    }


def _auc_cv(modelo, X, y, grupos, pliegues: int = 3) -> float:
    cv = StratifiedGroupKFold(n_splits=pliegues, shuffle=True, random_state=SEMILLA)
    aucs = []
    for tr, te in cv.split(X, y, grupos):
        m = clone(modelo).fit(X.iloc[tr], y.iloc[tr])
        aucs.append(roc_auc_score(y.iloc[te], m.predict_proba(X.iloc[te])[:, 1]))
    return float(np.mean(aucs))


def ajustar_rf(X, y, grupos, intentos: int) -> tuple[dict, list]:
    """Búsqueda aleatoria de hiperparámetros del Random Forest (3 pliegues agrupados)."""
    historial, mejor, mejor_auc = [], dict(n_estimators=400, max_depth=12, min_samples_leaf=5, max_features='sqrt'), -1
    for params in ParameterSampler(ESPACIO_RF, n_iter=intentos, random_state=SEMILLA):
        auc = _auc_cv(RandomForestClassifier(class_weight='balanced_subsample', random_state=SEMILLA,
                                             n_jobs=-1, **params), X, y, grupos)
        historial.append({**{k: str(v) for k, v in params.items()}, 'roc_auc': round(auc, 4)})
        if auc > mejor_auc:
            mejor, mejor_auc = params, auc
    return mejor, historial


def ajustar_lgbm(X, y, grupos, pruebas: int) -> tuple[dict, list]:
    """Optimización bayesiana (Optuna, TPE) de LightGBM con 3 pliegues agrupados."""
    if pruebas <= 0:
        return dict(LGBM_POR_DEFECTO), []
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objetivo(trial):
        params = dict(
            n_estimators=trial.suggest_int('n_estimators', 300, 1200, step=100),
            learning_rate=trial.suggest_float('learning_rate', 0.01, 0.08, log=True),
            num_leaves=trial.suggest_int('num_leaves', 8, 64),
            min_child_samples=trial.suggest_int('min_child_samples', 30, 400, log=True),
            subsample=trial.suggest_float('subsample', 0.6, 1.0), subsample_freq=1,
            colsample_bytree=trial.suggest_float('colsample_bytree', 0.4, 1.0),
            reg_lambda=trial.suggest_float('reg_lambda', 1e-3, 10.0, log=True),
        )
        return _auc_cv(_lgbm(params), X, y, grupos)

    estudio = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=SEMILLA))
    estudio.enqueue_trial({k: v for k, v in LGBM_POR_DEFECTO.items() if k != 'subsample_freq'})
    estudio.optimize(objetivo, n_trials=pruebas)
    mejor = dict(estudio.best_params, subsample_freq=1)
    historial = [{'prueba': t.number, 'roc_auc': _r(t.value)} for t in estudio.trials]
    return mejor, historial


def evaluar_cv(modelo, X, y, grupos) -> tuple[dict, np.ndarray]:
    """Validación cruzada agrupada por estudiante (5 pliegues) con predicciones fuera de pliegue."""
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEMILLA)
    roc, pr, oof = [], [], np.zeros(len(y))
    for tr, te in cv.split(X, y, grupos):
        m = clone(modelo).fit(X.iloc[tr], y.iloc[tr])
        p = m.predict_proba(X.iloc[te])[:, 1]
        oof[te] = p
        roc.append(roc_auc_score(y.iloc[te], p))
        pr.append(average_precision_score(y.iloc[te], p))
    resumen = {
        'roc_auc': {'media': _r(np.mean(roc)), 'desviacion': _r(np.std(roc)), 'pliegues': [_r(v) for v in roc]},
        'pr_auc': {'media': _r(np.mean(pr)), 'desviacion': _r(np.std(pr)), 'pliegues': [_r(v) for v in pr]},
    }
    return resumen, oof


# ── Umbrales, calibración y métricas ─────────────────────────────────────
def umbral_para_recall(y, p, recall_objetivo: float) -> float:
    """El mayor umbral cuyo recall sigue siendo >= recall_objetivo (mejor precisión posible)."""
    precision, recall, umbrales = precision_recall_curve(y, p)
    validos = [u for u, r in zip(umbrales, recall[:-1]) if r >= recall_objetivo]
    return float(max(validos)) if validos else float(np.min(umbrales))


def calibrar(y, p_oof) -> CalibradorPlatt:
    """Escalado de Platt ajustado solo con predicciones fuera de pliegue (ver ml/calibracion.py)."""
    return CalibradorPlatt().fit(p_oof, y)


def curva_calibracion(y, p, bins: int = 10) -> list[dict]:
    """Probabilidad media predicha frente a frecuencia observada, por deciles de predicción."""
    df = pd.DataFrame({'y': np.asarray(y), 'p': np.asarray(p)})
    df['bin'] = pd.qcut(df['p'].rank(method='first'), q=bins, labels=False)
    return [{'predicha': _r(g['p'].mean()), 'observada': _r(g['y'].mean()), 'n': int(len(g))}
            for _, g in df.groupby('bin')]


def _submuestrear_curva(x, y, puntos: int = 120) -> list[list[float]]:
    idx = np.unique(np.linspace(0, len(x) - 1, min(puntos, len(x))).astype(int))
    return [[_r(x[i]), _r(y[i])] for i in idx]


def metricas_en_umbral(y, p, umbral: float) -> dict:
    """Recall, precisión, tasa de alerta y matriz de confusión en un umbral."""
    y = np.asarray(y).astype(int)
    pred = (np.asarray(p) >= umbral).astype(int)
    vn, fp, fn, vp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        'umbral': _r(umbral), 'recall': _r(recall_score(y, pred, zero_division=0)),
        'precision': _r(precision_score(y, pred, zero_division=0)),
        'tasa_alerta': _r(pred.mean()), 'fpr': _r(fp / max(fp + vn, 1)),
        'matriz_confusion': [[int(vn), int(fp)], [int(fn), int(vp)]],
    }


def captura_top(y, p, fraccion: float) -> float:
    """Proporción de los abandonos reales que cae en el `fraccion` de mayor riesgo."""
    y = np.asarray(y)
    k = max(1, int(round(len(p) * fraccion)))
    orden = np.argsort(-np.asarray(p))[:k]
    return float(y[orden].sum() / max(y.sum(), 1))


def evaluar_prueba(y, p_cal, p_raw, umbral_alto: float, umbral_medio: float) -> dict:
    """Métricas de la prueba temporal (una sola vez)."""
    y = np.asarray(y).astype(int)
    fpr, tpr, _ = roc_curve(y, p_cal)
    precision, recall, _ = precision_recall_curve(y, p_cal)
    return {
        'n': int(len(y)), 'positivos': int(y.sum()), 'prevalencia': _r(y.mean()),
        'roc_auc': _r(roc_auc_score(y, p_cal)), 'pr_auc': _r(average_precision_score(y, p_cal)),
        'brier_sin_calibrar': _r(brier_score_loss(y, np.clip(p_raw, 0, 1))),
        'brier_calibrado': _r(brier_score_loss(y, p_cal)),
        'captura_top_10': _r(captura_top(y, p_cal, 0.10)), 'captura_top_20': _r(captura_top(y, p_cal, 0.20)),
        'umbral_medio': metricas_en_umbral(y, p_cal, umbral_medio),
        'umbral_alto': metricas_en_umbral(y, p_cal, umbral_alto),
        'curva_roc': _submuestrear_curva(fpr, tpr), 'curva_pr': _submuestrear_curva(recall[::-1], precision[::-1]),
        'curva_calibracion': curva_calibracion(y, p_cal),
    }


def equidad(prueba: pd.DataFrame, p_cal: np.ndarray, umbral_medio: float) -> list[dict]:
    """Desempeño por subgrupo (género, modalidad, sede) en la prueba temporal."""
    filas = []
    for variable in ('genero', 'modalidad_codigo', 'sede_codigo'):
        if variable not in prueba or prueba[variable].nunique() < 2:
            continue
        for valor, idx in prueba.groupby(variable).groups.items():
            pos = prueba.index.get_indexer(idx)
            y = prueba['y'].to_numpy()[pos].astype(int)
            if len(y) < 200 or y.sum() < 10 or y.sum() == len(y):
                continue
            m = metricas_en_umbral(y, p_cal[pos], umbral_medio)
            filas.append({'variable': variable, 'grupo': str(valor), 'n': int(len(y)), 'prevalencia': _r(y.mean()),
                          'roc_auc': _r(roc_auc_score(y, p_cal[pos])), 'recall': m['recall'],
                          'precision': m['precision'], 'tasa_alerta': m['tasa_alerta'], 'fpr': m['fpr']})
    return filas


def referencia_psi(X: pd.DataFrame, columnas: list[str]) -> dict:
    """Cortes por deciles y proporciones de referencia para vigilar la deriva (PSI)."""
    ref = {}
    for c in columnas:
        s = X[c].dropna()
        if s.nunique() < 3:
            continue
        cortes = np.unique(np.quantile(s, np.linspace(0, 1, 11)))
        if len(cortes) < 3:
            continue
        conteo = np.histogram(s, bins=cortes)[0]
        ref[c] = {'cortes': [float(v) for v in cortes], 'proporciones': [float(v) for v in conteo / conteo.sum()]}
    return ref


# ── Orquestación (pura: recibe el panel, no toca la base) ───────────────
def entrenar_panel(panel: pd.DataFrame, institucion: str, grupos: list[str], intentos_rf: int = 10,
                   pruebas_optuna: int = 15, registrar=print) -> tuple[dict, dict, pd.DataFrame, pd.DataFrame]:
    """Entrena, valida y empaqueta el modelo de una institución a partir de su panel.

    Returns:
        (paquete para joblib, métricas para metricas.json, predicciones de la prueba temporal,
        predicciones fuera de pliegue del modelo elegido).
    """
    inicio = time.time()
    columnas = variables_modelo(grupos)
    etiquetado = panel[panel['y'].notna()].reset_index(drop=True)
    etiquetado['y'] = etiquetado['y'].astype(int)
    registrar(f'  Panel: {len(panel)} filas; {len(etiquetado)} etiquetadas; '
              f'{int(etiquetado.y.sum())} abandonos al periodo siguiente ({etiquetado.y.mean():.2%}).')
    if etiquetado['y'].sum() < 30:
        raise ValueError('Muy pocos abandonos etiquetados para entrenar de forma confiable.')

    es_prueba, periodos_prueba = particion_temporal(etiquetado)
    train, prueba = etiquetado[~es_prueba].reset_index(drop=True), etiquetado[es_prueba].reset_index(drop=True)
    X_tr, X_te = matriz(train, columnas), matriz(prueba, columnas)
    y_tr, y_te, grupos_tr = train['y'], prueba['y'], train['alumno_id']
    registrar(f'  Prueba temporal: periodos {periodos_prueba} ({len(prueba)} filas); entrenamiento {len(train)} filas.')

    registrar(f'  Ajuste de Random Forest ({intentos_rf} combinaciones) ...')
    params_rf, hist_rf = ajustar_rf(X_tr, y_tr, grupos_tr, intentos_rf)
    registrar(f'    {params_rf}')
    registrar(f'  Ajuste de LightGBM con Optuna ({pruebas_optuna} pruebas) ...')
    params_lgbm, hist_lgbm = ajustar_lgbm(X_tr, y_tr, grupos_tr, pruebas_optuna)
    registrar(f'    {params_lgbm}')

    comparacion, oofs = {}, {}
    for nombre, modelo in candidatos(params_rf, params_lgbm).items():
        comparacion[nombre], oofs[nombre] = evaluar_cv(modelo, X_tr, y_tr, grupos_tr)
        registrar(f"    {nombre:13s} ROC-AUC {comparacion[nombre]['roc_auc']['media']:.4f} ± "
                  f"{comparacion[nombre]['roc_auc']['desviacion']:.4f} | PR-AUC {comparacion[nombre]['pr_auc']['media']:.4f}")
    final = max(comparacion, key=lambda n: (comparacion[n]['roc_auc']['media'], comparacion[n]['pr_auc']['media']))
    registrar(f'  Modelo elegido: {final}')

    calibrador = calibrar(y_tr, oofs[final])
    oof_cal = calibrador.predict(oofs[final])
    umbral_medio = umbral_para_recall(y_tr, oof_cal, RECALL_MEDIO)
    umbral_alto = max(umbral_para_recall(y_tr, oof_cal, RECALL_ALTO), umbral_medio)

    modelo_temporal = clone(candidatos(params_rf, params_lgbm)[final]).fit(X_tr, y_tr)
    p_raw = modelo_temporal.predict_proba(X_te)[:, 1]
    p_cal = calibrador.predict(p_raw)
    temporal = evaluar_prueba(y_te, p_cal, p_raw, umbral_alto, umbral_medio)
    temporal['periodos'] = periodos_prueba
    registrar(f"  Prueba temporal: ROC-AUC {temporal['roc_auc']} | PR-AUC {temporal['pr_auc']} | "
              f"recall MEDIO {temporal['umbral_medio']['recall']} | captura top 10 % {temporal['captura_top_10']}")

    muestra = np.random.default_rng(SEMILLA).choice(len(X_te), size=min(len(X_te), 15000), replace=False)
    perm = permutation_importance(modelo_temporal, X_te.iloc[muestra], y_te.iloc[muestra],
                                  scoring='average_precision', n_repeats=3, random_state=SEMILLA, n_jobs=1)
    importancia = sorted(({'variable': c, 'media': _r(m), 'desviacion': _r(s)}
                          for c, m, s in zip(columnas, perm.importances_mean, perm.importances_std)),
                         key=lambda d: -(d['media'] or 0))

    X_todo = matriz(etiquetado, columnas)
    modelo_final = clone(candidatos(params_rf, params_lgbm)[final]).fit(X_todo, etiquetado['y'])

    paquete = {
        'modelo': modelo_final, 'nombre_modelo': final, 'calibrador': calibrador, 'columnas': columnas,
        'grupos': grupos, 'umbral_alto': umbral_alto, 'umbral_medio': umbral_medio, 'version': VERSION,
        'institucion': institucion, 'referencia_psi': referencia_psi(X_todo, columnas),
        'fecha': dt.datetime.now().isoformat(timespec='seconds'),
    }
    metricas = {
        'institucion': institucion, 'version': VERSION, 'fecha': paquete['fecha'],
        'horizonte': 'abandono en el periodo siguiente',
        'grupos_de_variables': ['base'] + grupos, 'n_variables': len(columnas),
        'panel': {'filas': int(len(panel)), 'etiquetadas': int(len(etiquetado)),
                  'positivos': int(etiquetado.y.sum()), 'prevalencia': _r(etiquetado.y.mean()),
                  'estudiantes': int(panel['alumno_id'].nunique()), 'para_calificar': int(panel['para_calificar'].sum()),
                  'entrenamiento': int(len(train)), 'prueba': int(len(prueba))},
        'hiperparametros': {'RF': {k: str(v) for k, v in params_rf.items()}, 'LIGHTGBM': params_lgbm},
        'busqueda': {'RF': hist_rf, 'LIGHTGBM': hist_lgbm},
        'comparacion_cv': comparacion, 'modelo_final': final,
        'calibracion': {'metodo': 'Platt (regresión logística sobre el logit, predicciones fuera de pliegue)'},
        'umbrales': {'alto': _r(umbral_alto), 'medio': _r(umbral_medio),
                     'recall_objetivo_alto': RECALL_ALTO, 'recall_objetivo_medio': RECALL_MEDIO},
        'validacion_temporal': temporal, 'equidad': equidad(prueba, p_cal, umbral_medio),
        'importancia_permutacion': importancia, 'segundos': round(time.time() - inicio, 1),
    }
    predicciones = pd.DataFrame({'y': y_te.to_numpy(), 'probabilidad': p_cal, 'puntaje': p_raw,
                                 'periodo': prueba['periodo_codigo'].to_numpy(), 'corte': prueba['corte'].to_numpy()})
    oof = pd.DataFrame({'y': y_tr.to_numpy(), 'puntaje': oofs[final], 'probabilidad': oof_cal})
    return paquete, metricas, predicciones, oof


# ── Persistencia ─────────────────────────────────────────────────────────
def filas_evaluacion(institucion: str, metricas: dict) -> list[tuple]:
    """Filas para fact_evaluacion_modelo a partir de las métricas del entrenamiento."""
    final, version = metricas['modelo_final'], metricas['version']
    filas = []
    for nombre, res in metricas['comparacion_cv'].items():
        for met in ('roc_auc', 'pr_auc'):
            filas.append((institucion, 'PREDICCION', nombre, 'CV_AGRUPADA_5', met.upper(),
                          res[met]['media'], res[met]['desviacion'], None, int(nombre == final), version))
    t = metricas['validacion_temporal']
    for clave, nombre in (('roc_auc', 'ROC_AUC'), ('pr_auc', 'PR_AUC'), ('brier_calibrado', 'BRIER'),
                          ('captura_top_10', 'CAPTURA_TOP_10'), ('prevalencia', 'PREVALENCIA')):
        filas.append((institucion, 'PREDICCION', final, 'TEMPORAL', nombre, t[clave], None, None, 1, version))
    for nivel in ('medio', 'alto'):
        m = t[f'umbral_{nivel}']
        for clave in ('recall', 'precision', 'umbral', 'tasa_alerta'):
            filas.append((institucion, 'PREDICCION', final, 'TEMPORAL', f'{clave.upper()}_{nivel.upper()}',
                          m[clave], None, None, 1, version))
    for e in metricas['equidad']:
        for clave in ('roc_auc', 'recall', 'precision', 'fpr'):
            if e[clave] is not None:
                filas.append((institucion, 'PREDICCION', final, 'EQUIDAD', clave.upper(), e[clave], None,
                              f"{e['variable']}={e['grupo']}", 1, version))
    return [f for f in filas if f[5] is not None]


def guardar(conn, institucion: str, paquete: dict, metricas: dict, predicciones: pd.DataFrame,
            oof: pd.DataFrame | None = None) -> Path:
    """Guarda el modelo, las métricas y las predicciones de prueba, y publica las métricas en el almacén."""
    destino = RAIZ_MODELOS / institucion
    destino.mkdir(parents=True, exist_ok=True)
    joblib.dump(paquete, destino / 'modelo_abandono.joblib', compress=3)
    (destino / 'metricas.json').write_text(json.dumps(metricas, indent=2, ensure_ascii=False, default=str),
                                          encoding='utf-8')
    predicciones.to_csv(destino / 'predicciones_prueba_temporal.csv', index=False)
    if oof is not None:
        oof.round(6).to_csv(destino / 'predicciones_validacion_cruzada.csv', index=False)
    if conn is not None:
        cur = conn.cursor()
        cur.execute("DELETE FROM dbo.fact_evaluacion_modelo WHERE institucion_codigo = ? AND componente = 'PREDICCION' "
                    "AND esquema_validacion IN ('CV_AGRUPADA_5', 'TEMPORAL', 'EQUIDAD')", institucion)
        cur.fast_executemany = True
        cur.executemany("""INSERT INTO dbo.fact_evaluacion_modelo
            (institucion_codigo, componente, modelo, esquema_validacion, metrica, valor, desviacion, grupo,
             es_modelo_final, modelo_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        filas_evaluacion(institucion, metricas))
        conn.commit()
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--institucion', required=True)
    parser.add_argument('--intentos-rf', type=int, default=10)
    parser.add_argument('--pruebas-optuna', type=int, default=15)
    args = parser.parse_args()
    institucion = args.institucion.strip().upper()

    from core.db import conectar_admin
    from ml.datos import leer_historial
    conn = conectar_admin()
    print(f"Leyendo la trayectoria de '{institucion}' ...")
    hist = leer_historial(conn, institucion)
    grupos = grupos_disponibles(hist)
    print(f'  {len(hist)} filas; grupos opcionales con datos: {grupos or "ninguno"}')
    panel = construir_panel(hist)
    paquete, metricas, predicciones, oof = entrenar_panel(panel, institucion, grupos, args.intentos_rf,
                                                          args.pruebas_optuna)
    destino = guardar(conn, institucion, paquete, metricas, predicciones, oof)
    conn.close()
    print(f'Modelo y métricas guardados en {destino} ({metricas["segundos"]} s).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
