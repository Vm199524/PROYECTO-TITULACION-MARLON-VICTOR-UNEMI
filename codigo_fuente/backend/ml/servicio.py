# -*- coding: utf-8 -*-
"""
Acceso del API a los modelos entrenados y a sus reportes.

Carga cada modelo una sola vez por proceso y lo recarga si el archivo cambia
(por ejemplo, tras reentrenar). También entrega las métricas, la segmentación
y el monitoreo guardados por los procesos por lotes.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.calificar import categoria
from ml.explicacion import contribuciones, detalle, factores

RAIZ_MODELOS = Path(__file__).resolve().parent / 'modelos'
_cache: dict[str, tuple[float, dict]] = {}
_candado = threading.Lock()


def paquete(institucion: str) -> dict | None:
    """Modelo, calibrador, columnas y umbrales de la institución (None si no hay modelo)."""
    ruta = RAIZ_MODELOS / institucion / 'modelo_abandono.joblib'
    if not ruta.exists():
        return None
    marca = ruta.stat().st_mtime
    with _candado:
        guardado = _cache.get(institucion)
        if guardado and guardado[0] == marca:
            return guardado[1]
    cargado = joblib.load(ruta)
    with _candado:
        _cache[institucion] = (marca, cargado)
    return cargado


def reporte(institucion: str, nombre: str) -> dict | None:
    """Lee un JSON de resultados (metricas, segmentacion, monitoreo, prospectiva) de la institución."""
    ruta = RAIZ_MODELOS / institucion / f'{nombre}.json'
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding='utf-8'))


def predecir(paq: dict, caracteristicas: dict) -> dict:
    """Probabilidad calibrada, categoría y explicación para un vector de variables."""
    columnas = paq['columnas']
    X = pd.DataFrame([[caracteristicas.get(c, np.nan) for c in columnas]], columns=columnas, dtype=float)
    crudo = paq['modelo'].predict_proba(X)[:, 1]
    prob = float(paq['calibrador'].predict(crudo)[0])
    contrib = contribuciones(paq['modelo'], X)[0]
    return {'probabilidad': round(prob, 4), 'categoria': categoria(prob, paq['umbral_alto'], paq['umbral_medio']),
            'factores': [f for f in factores(contrib, X.iloc[0]) if f], 'explicacion': detalle(contrib, X.iloc[0])}
