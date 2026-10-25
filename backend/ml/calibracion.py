# -*- coding: utf-8 -*-
"""
Calibración de probabilidades (escalado de Platt).

Los clasificadores con clases desbalanceadas (y más aún si se entrenan con
ponderación de clases o SMOTE) entregan puntajes que ordenan bien a los
estudiantes pero no son frecuencias: un 0,40 no significa que 4 de cada 10
abandonen. El escalado de Platt ajusta una regresión logística sobre el logit
del puntaje, usando solo predicciones fuera de pliegue, y convierte el puntaje
en una probabilidad interpretable por una autoridad. Es estrictamente
creciente: no altera el orden de los estudiantes ni crea empates (la
calibración isotónica sí los crea, y con ellos los umbrales ALTO y MEDIO
podían coincidir).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

EPS = 1e-6


def _logit(p) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p)).reshape(-1, 1)


class CalibradorPlatt:
    """Regresión logística sobre el logit del puntaje del modelo."""

    def __init__(self) -> None:
        self.regresion = LogisticRegression(C=1e6, max_iter=1000)

    def fit(self, puntajes, y) -> 'CalibradorPlatt':
        self.regresion.fit(_logit(puntajes), np.asarray(y).astype(int))
        return self

    def predict(self, puntajes) -> np.ndarray:
        return self.regresion.predict_proba(_logit(puntajes))[:, 1]
