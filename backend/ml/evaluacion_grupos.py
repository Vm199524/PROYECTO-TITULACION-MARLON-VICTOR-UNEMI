# -*- coding: utf-8 -*-
"""
Validación desagregada del modelo: por periodo académico, por carrera y con
origen móvil (backtesting).

Una sola cifra global de ROC-AUC puede ocultar que el modelo funciona bien en
un periodo y mal en otro, o que acierta en una carrera y falla en otra. Este
módulo reporta el desempeño de cada periodo y de cada carrera por separado y
repite la validación temporal con origen móvil: para cada periodo P de los más
recientes se entrena solo con los periodos anteriores a P y se evalúa en P,
como si el sistema se hubiera puesto en marcha en esa fecha. En cada origen,
la calibración y los umbrales se ajustan solo con el pasado (predicciones fuera
de pliegue agrupadas por estudiante), así ninguna decisión usa el periodo que
se evalúa.

Son funciones puras: reciben DataFrames y no tocan la base de datos.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import average_precision_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from ml.calibracion import CalibradorPlatt

MINIMO_FILAS = 100
MINIMO_POSITIVOS = 10


def _r(x, d: int = 4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


def _metricas(y: np.ndarray, p: np.ndarray, umbral_medio: float, umbral_alto: float) -> dict:
    """ROC-AUC, PR-AUC y recall/precisión en los dos umbrales de una porción de la prueba."""
    y = np.asarray(y).astype(int)
    p = np.asarray(p, dtype=float)
    medio, alto = (p >= umbral_medio).astype(int), (p >= umbral_alto).astype(int)
    evaluable = len(y) >= MINIMO_FILAS and MINIMO_POSITIVOS <= y.sum() < len(y)
    return {
        'n': int(len(y)), 'positivos': int(y.sum()), 'prevalencia': _r(y.mean() if len(y) else None),
        'roc_auc': _r(roc_auc_score(y, p)) if evaluable else None,
        'pr_auc': _r(average_precision_score(y, p)) if evaluable else None,
        'recall_medio': _r(recall_score(y, medio, zero_division=0)) if y.sum() else None,
        'precision_medio': _r(precision_score(y, medio, zero_division=0)),
        'tasa_alerta_medio': _r(medio.mean()),
        'recall_alto': _r(recall_score(y, alto, zero_division=0)) if y.sum() else None,
        'precision_alto': _r(precision_score(y, alto, zero_division=0)),
        'evaluable': bool(evaluable),
    }


def metricas_por_grupo(prueba: pd.DataFrame, columna: str, umbral_medio: float, umbral_alto: float,
                       orden: list | None = None) -> list[dict]:
    """Desempeño en cada valor de `columna` (periodo, carrera...) de la prueba temporal.

    `prueba` debe tener las columnas `y`, `probabilidad` (calibrada) y `columna`.
    Los grupos con menos de 100 filas o 10 abandonos se reportan sin AUC
    (evaluable = False): con tan pocos casos la cifra no es estable.
    """
    if columna not in prueba or prueba.empty:
        return []
    filas = []
    for valor, g in prueba.groupby(columna, sort=False):
        filas.append({'grupo': str(valor), **_metricas(g['y'].to_numpy(), g['probabilidad'].to_numpy(),
                                                     umbral_medio, umbral_alto)})
    if orden:
        posicion = {str(v): i for i, v in enumerate(orden)}
        filas.sort(key=lambda f: posicion.get(f['grupo'], len(posicion)))
    else:
        filas.sort(key=lambda f: -f['n'])
    return filas


def _umbral_para_recall(y, p, objetivo: float) -> float:
    from sklearn.metrics import precision_recall_curve
    _, recall, umbrales = precision_recall_curve(y, p)
    validos = [u for u, r in zip(umbrales, recall[:-1]) if r >= objetivo]
    return float(max(validos)) if validos else float(np.min(umbrales))


def validacion_origen_movil(etiquetado: pd.DataFrame, columnas: list[str], modelo,
                            matriz: Callable[[pd.DataFrame, list[str]], pd.DataFrame],
                            recall_medio: float = 0.80, recall_alto: float = 0.50,
                            origenes: int = 4, minimo_periodos_entrenamiento: int = 2,
                            semilla: int = 20260909, registrar=print) -> list[dict]:
    """Backtesting con origen móvil sobre los `origenes` periodos más recientes con etiqueta.

    Para cada periodo P: entrena con los periodos que empezaron antes que P,
    calibra (Platt) y fija los umbrales con predicciones fuera de pliegue de ese
    entrenamiento (3 pliegues agrupados por estudiante), reentrena con todo el
    pasado y evalúa una sola vez en P.

    Args:
        etiquetado: panel con `y` conocida, `periodo_codigo`, `fecha_inicio` y `alumno_id`.
        modelo: estimador sin entrenar (el algoritmo y los hiperparámetros elegidos).
        matriz: función que arma la matriz de entrada (ml.caracteristicas.matriz).
    """
    periodos = (etiquetado.groupby('periodo_codigo')['fecha_inicio'].min().sort_values())
    codigos = list(periodos.index)
    candidatos = codigos[minimo_periodos_entrenamiento:][-origenes:]
    resultados = []
    for codigo in candidatos:
        inicio = periodos[codigo]
        pasado = etiquetado[etiquetado['fecha_inicio'] < inicio].reset_index(drop=True)
        actual = etiquetado[etiquetado['periodo_codigo'] == codigo].reset_index(drop=True)
        if pasado['y'].sum() < 30 or actual.empty:
            continue
        X_tr, y_tr, g_tr = matriz(pasado, columnas), pasado['y'].astype(int), pasado['alumno_id']
        oof = np.zeros(len(y_tr))
        cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=semilla)
        for tr, te in cv.split(X_tr, y_tr, g_tr):
            oof[te] = clone(modelo).fit(X_tr.iloc[tr], y_tr.iloc[tr]).predict_proba(X_tr.iloc[te])[:, 1]
        calibrador = CalibradorPlatt().fit(oof, y_tr)
        oof_cal = calibrador.predict(oof)
        u_medio = _umbral_para_recall(y_tr, oof_cal, recall_medio)
        u_alto = max(_umbral_para_recall(y_tr, oof_cal, recall_alto), u_medio)
        ajustado = clone(modelo).fit(X_tr, y_tr)
        p = calibrador.predict(ajustado.predict_proba(matriz(actual, columnas))[:, 1])
        fila = {'periodo': codigo, 'periodos_entrenamiento': int(pasado['periodo_codigo'].nunique()),
                'filas_entrenamiento': int(len(pasado)), 'umbral_medio': _r(u_medio), 'umbral_alto': _r(u_alto),
                **_metricas(actual['y'].to_numpy(), p, u_medio, u_alto)}
        resultados.append(fila)
        registrar(f"    Origen {codigo}: entrena con {fila['periodos_entrenamiento']} periodos "
                  f"({fila['filas_entrenamiento']} filas) | ROC-AUC {fila['roc_auc']} | "
                  f"recall MEDIO {fila['recall_medio']} | recall ALTO {fila['recall_alto']}")
    return resultados


def resumen_origen_movil(filas: list[dict]) -> dict:
    """Media, mínimo y máximo de ROC-AUC y recall MEDIO entre los orígenes evaluables."""
    aucs = [f['roc_auc'] for f in filas if f.get('roc_auc') is not None]
    recalls = [f['recall_medio'] for f in filas if f.get('recall_medio') is not None]
    if not aucs:
        return {}
    return {'origenes': len(aucs), 'roc_auc_media': _r(np.mean(aucs)), 'roc_auc_min': _r(min(aucs)),
            'roc_auc_max': _r(max(aucs)), 'recall_medio_media': _r(np.mean(recalls)) if recalls else None,
            'recall_medio_min': _r(min(recalls)) if recalls else None}
