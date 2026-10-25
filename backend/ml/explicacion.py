# -*- coding: utf-8 -*-
"""
Explicación de cada predicción y recomendaciones de acompañamiento.

Para que una autoridad sin formación técnica confíe en una alerta, cada
estudiante en riesgo trae las razones del modelo en lenguaje natural:

  - Contribuciones SHAP (Lundberg y Lee): cuánto empuja cada variable la
    predicción de ESE estudiante hacia el abandono (+) o hacia la permanencia
    (−). En modelos de árboles (Random Forest, LightGBM) son exactas
    (TreeSHAP); en la regresión logística, coeficiente por valor
    estandarizado.
  - Recomendaciones por reglas, derivadas de las variables que más pesan.
    Son sugerencias para bienestar estudiantil, no decisiones automáticas.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.caracteristicas import describir, formatear_valor


def contribuciones(modelo, X: pd.DataFrame) -> np.ndarray:
    """Matriz (filas × variables) de contribuciones a la predicción en escala logit."""
    pasos = getattr(modelo, 'named_steps', None)
    if pasos is None and hasattr(modelo, 'booster_'):            # LightGBM
        return np.asarray(modelo.booster_.predict(X, pred_contrib=True))[:, :X.shape[1]]
    if pasos is None:                                            # Random Forest
        import shap
        valores = np.asarray(shap.TreeExplainer(modelo).shap_values(X, check_additivity=False))
        return valores[:, :, 1] if valores.ndim == 3 else valores
    if 'rf' in pasos:                                            # Random Forest con SMOTE
        import shap
        Xi = pd.DataFrame(pasos['imputar'].transform(X), columns=X.columns)
        valores = np.asarray(shap.TreeExplainer(pasos['rf']).shap_values(Xi, check_additivity=False))
        return valores[:, :, 1] if valores.ndim == 3 else valores
    # Regresión logística: coeficiente × valor estandarizado (solo columnas originales).
    imputador, escalador, logistica = list(pasos.values())
    Z = escalador.transform(imputador.transform(X))
    return (Z * logistica.coef_[0])[:, :X.shape[1]]


def frase(variable: str, valor) -> str:
    return f'{describir(variable)}: {formatear_valor(variable, valor)}'


def factores(fila_contrib: np.ndarray, fila_X: pd.Series, top: int = 3) -> list[str | None]:
    """Las `top` variables que más elevan el riesgo, redactadas para una autoridad."""
    orden = np.argsort(-fila_contrib)
    salida = [frase(fila_X.index[j], fila_X.iloc[j]) for j in orden[:top] if fila_contrib[j] > 0]
    return salida + [None] * (top - len(salida))


def detalle(fila_contrib: np.ndarray, fila_X: pd.Series, top: int = 8) -> list[dict]:
    """Contribuciones más relevantes en ambos sentidos, para la ficha del estudiante."""
    orden = np.argsort(-np.abs(fila_contrib))[:top]
    return [{'variable': fila_X.index[j], 'descripcion': describir(fila_X.index[j]),
             'valor': None if pd.isna(fila_X.iloc[j]) else round(float(fila_X.iloc[j]), 4),
             'valor_texto': formatear_valor(fila_X.index[j], fila_X.iloc[j]),
             'contribucion': round(float(fila_contrib[j]), 4)} for j in orden]


_REGLAS = [
    (('asistencia',), 'ASISTENCIA', 'Contactar al estudiante para conocer las causas de la baja asistencia y '
                                    'coordinar con sus docentes un plan de recuperación.'),
    (('promedio', 'nota_evaluaciones'), 'RENDIMIENTO', 'Derivar a tutoría académica en las asignaturas con menor '
                                                        'rendimiento y acordar metas por corte.'),
    (('mora', 'saldo'), 'ECONOMICO', 'Informar sobre becas, ayudas económicas o convenios de pago disponibles.'),
    (('actividad', 'dias_sin_actividad'), 'AULA_VIRTUAL', 'Contacto inmediato: su actividad en el aula virtual cayó. '
                                                           'Verificar acceso, conectividad y carga de trabajo.'),
    (('entregadas', 'tardias', 'evaluaciones_vencidas'), 'EVALUACIONES', 'Acompañar la entrega de las evaluaciones '
                                                                        'pendientes y revisar plazos con el docente.'),
    (('numero_matricula',), 'REPETICION', 'Seguimiento por repetición de asignaturas: revisar carga académica y '
                                          'prerrequisitos.'),
    (('creditos',), 'CARGA', 'Revisar si la carga de créditos del periodo es sostenible para el estudiante.'),
]


def recomendaciones(detalle_contrib: list[dict], maximo: int = 3) -> list[dict]:
    """Sugerencias de acompañamiento a partir de las variables que más elevan el riesgo."""
    salida, vistas = [], set()
    for item in detalle_contrib:
        if item['contribucion'] <= 0:
            continue
        for claves, tipo, texto in _REGLAS:
            if tipo not in vistas and any(c in item['variable'] for c in claves):
                vistas.add(tipo)
                salida.append({'tipo': tipo, 'texto': texto, 'motivo': item['descripcion']})
                break
        if len(salida) >= maximo:
            break
    if not salida:
        salida.append({'tipo': 'SEGUIMIENTO', 'texto': 'Mantener el seguimiento regular del estudiante.',
                       'motivo': 'sin factores de riesgo destacados'})
    return salida
