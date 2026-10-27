# -*- coding: utf-8 -*-
"""
Deriva de los datos con Evidently (y PSI propio como respaldo).

Un modelo de abandono se entrena con la trayectoria de cohortes pasadas y se
aplica a los estudiantes activos de hoy. Si las variables de entrada cambian de
distribución (otra forma de evaluar, una nueva plataforma virtual, una
pandemia), las probabilidades dejan de ser confiables aunque el código no
cambie. Este módulo compara, variable por variable, la distribución de
referencia (filas con las que se entrenó el modelo) con la actual (estudiantes
que se califican) usando el informe DataDriftPreset de Evidently:

  - prueba K-S o distancia de Wasserstein normalizada para variables numéricas,
    según el tamaño de la muestra (la elección es del propio Evidently);
  - una variable «deriva» si supera el umbral de su método;
  - el conjunto deriva si al menos la mitad de las variables derivan.

El informe HTML interactivo queda en ml/modelos/<INSTITUCION>/deriva_evidently.html
(no se versiona: se regenera en cada calificación) y el resumen en deriva.json,
que lee la página «Calidad del modelo». El PSI de las 10 variables más
importantes (ml/calificar.py) se mantiene como segunda medida, con los
umbrales habituales de 0,10 (vigilar) y 0,25 (deriva).

Requerimientos que implementa: RF-13 (calidad del modelo), RF-17 (calificación
    por lotes y deriva).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import numpy as np
import pandas as pd

MAX_REFERENCIA = 20000   # muestra de la referencia (el informe pesa menos y es igual de estable)
SEMILLA = 20260909


def _muestra(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return df if len(df) <= n else df.sample(n=n, random_state=SEMILLA)


def _columnas_utiles(ref: pd.DataFrame, act: pd.DataFrame) -> list[str]:
    """Variables con datos y con más de un valor en ambas muestras."""
    return [c for c in ref.columns
            if ref[c].notna().mean() > 0.5 and act[c].notna().mean() > 0.5
            and ref[c].nunique() > 1 and act[c].nunique() > 1]


def _psi(ref: pd.Series, act: pd.Series, bins: int = 10) -> float | None:
    ref, act = ref.dropna(), act.dropna()
    if ref.nunique() < 3 or act.empty:
        return None
    cortes = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(cortes) < 3:
        return None
    cortes[0], cortes[-1] = -np.inf, np.inf
    p = np.histogram(ref, bins=cortes)[0] / len(ref)
    q = np.histogram(act, bins=cortes)[0] / len(act)
    p, q = np.clip(p, 1e-6, None), np.clip(q, 1e-6, None)
    return float(np.sum((q - p) * np.log(q / p)))


def informe_deriva(referencia: pd.DataFrame, actual: pd.DataFrame, institucion: str,
                   destino_html: Path | None = None, importancia: dict | None = None) -> dict:
    """Compara referencia y actual con Evidently y devuelve el resumen por variable.

    Args:
        referencia: matriz de entrada con la que se entrenó el modelo.
        actual: matriz de entrada de los estudiantes que se califican.
        importancia: importancia por permutación de cada variable (para ordenar el resumen).
    """
    columnas = _columnas_utiles(referencia, actual)
    ref = _muestra(referencia[columnas].astype(float), MAX_REFERENCIA).reset_index(drop=True)
    act = actual[columnas].astype(float).reset_index(drop=True)
    importancia = importancia or {}
    resumen = {'institucion': institucion, 'fecha': dt.datetime.now().isoformat(timespec='seconds'),
               'filas_referencia': int(len(ref)), 'filas_actuales': int(len(act)), 'variables': []}
    try:
        from evidently import Report, __version__ as version_evidently
        from evidently.presets import DataDriftPreset
        snapshot = Report([DataDriftPreset()]).run(current_data=act, reference_data=ref)
        datos = snapshot.dict()
        if destino_html is not None:
            Path(destino_html).parent.mkdir(parents=True, exist_ok=True)
            snapshot.save_html(str(destino_html))
        resumen['motor'] = f'Evidently {version_evidently} (DataDriftPreset)'
        for m in datos['metrics']:
            nombre = m.get('metric_name', '')
            config = m.get('config', {})
            if nombre.startswith('DriftedColumnsCount'):
                resumen['variables_con_deriva'] = int(m['value']['count'])
                resumen['proporcion_con_deriva'] = round(float(m['value']['share']), 4)
                resumen['umbral_conjunto'] = config.get('drift_share', 0.5)
            elif nombre.startswith('ValueDrift'):
                columna = config.get('column')
                umbral = float(config.get('threshold'))
                metodo = config.get('method', '')
                valor = float(m['value'])
                # K-S y chi-cuadrado devuelven un valor p (deriva si p < umbral);
                # las distancias (Wasserstein, PSI, Jensen-Shannon) derivan si superan el umbral.
                es_p = bool(re.search(r'p_value|K-S|chi-square|Z-test', metodo, re.I))
                deriva = valor < umbral if es_p else valor > umbral
                resumen['variables'].append({'variable': columna, 'metodo': metodo, 'valor': round(valor, 4),
                                             'umbral': umbral, 'deriva': bool(deriva)})
    except ImportError:
        resumen['motor'] = 'PSI (Evidently no está instalado)'
    psi = {c: _psi(ref[c], act[c]) for c in columnas}
    if not resumen['variables']:
        for c in columnas:
            if psi[c] is not None:
                resumen['variables'].append({'variable': c, 'metodo': 'PSI', 'valor': round(psi[c], 4),
                                             'umbral': 0.25, 'deriva': psi[c] > 0.25})
        n = sum(v['deriva'] for v in resumen['variables'])
        resumen['variables_con_deriva'] = n
        resumen['proporcion_con_deriva'] = round(n / max(len(resumen['variables']), 1), 4)
        resumen['umbral_conjunto'] = 0.5
    for v in resumen['variables']:
        v['psi'] = None if psi.get(v['variable']) is None else round(psi[v['variable']], 4)
        v['importancia'] = importancia.get(v['variable'])
    resumen['variables'].sort(key=lambda v: (-(v['importancia'] or 0), v['variable']))
    importantes = [v for v in resumen['variables'] if (v['importancia'] or 0) > 0][:10]
    resumen['importantes_con_deriva'] = [v['variable'] for v in importantes if v['deriva']]
    resumen['conjunto_con_deriva'] = resumen['proporcion_con_deriva'] >= resumen['umbral_conjunto']
    resumen['lectura'] = (
        'La distribución de entrada cambió en la mayoría de variables: revisar los datos y reentrenar.'
        if resumen['conjunto_con_deriva'] else
        f"{resumen['variables_con_deriva']} de {len(resumen['variables'])} variables cambian de distribución; "
        'el conjunto se considera estable. Las variables marcadas se vigilan en el siguiente corte.')
    return resumen
