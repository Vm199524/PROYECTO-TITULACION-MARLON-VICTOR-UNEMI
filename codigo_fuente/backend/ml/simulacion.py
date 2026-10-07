# -*- coding: utf-8 -*-
"""
Simulador de escenarios («¿qué pasaría si…?») de la ficha del estudiante.

Bienestar estudiantil puede preguntar, por ejemplo: «si este estudiante sube
su asistencia al 85 % y regulariza su saldo, ¿cuánto bajaría su riesgo?».
El simulador cambia los valores del periodo actual, recalcula exactamente las
mismas variables que usa el modelo (rezagos, medias, tendencia, posición en
la cohorte) y vuelve a predecir con el modelo y el calibrador guardados.

Advertencia que la interfaz muestra siempre: el modelo es predictivo, no
causal. El resultado indica cómo cambiaría la estimación del modelo, no
garantiza que una intervención produzca ese efecto.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import math

import numpy as np

from ml.caracteristicas import EPS, UMBRAL_ASISTENCIA_BAJA

VARIABLES_SIMULABLES = {
    'promedio': {'grupo': 'base', 'min': 0.0, 'max': 10.0, 'etiqueta': 'Promedio del periodo (0-10)'},
    'asistencia_pct': {'grupo': 'base', 'min': 0.0, 'max': 100.0, 'etiqueta': 'Asistencia del periodo (%)'},
    'saldo_pendiente': {'grupo': 'financieras', 'min': 0.0, 'max': 100000.0, 'etiqueta': 'Saldo pendiente ($)'},
    'actividad_lms': {'grupo': 'aula_virtual', 'min': 0.0, 'max': 100000.0,
                      'etiqueta': 'Interacciones en el aula virtual'},
    'dias_sin_actividad': {'grupo': 'aula_virtual', 'min': 0.0, 'max': 400.0,
                           'etiqueta': 'Días sin actividad en el aula virtual'},
    'evaluaciones_entregadas': {'grupo': 'evaluaciones', 'min': 0.0, 'max': 100.0,
                                'etiqueta': 'Evaluaciones entregadas'},
}


def _pct_cohorte(valor: float, cohorte: dict | None) -> float | None:
    if not cohorte:
        return None
    q = np.asarray(cohorte['cuantiles'])
    return float(np.interp(valor, q, np.linspace(0, 1, len(q))))


def _rel_cohorte(valor: float, cohorte: dict | None) -> float | None:
    if not cohorte:
        return None
    return (valor - cohorte['media']) / (cohorte['desv'] + EPS)


def _serie(prefijo: str, nuevo: float, e: dict, base: str, c: dict) -> None:
    """Recalcula las variables de rendimiento o asistencia con el nuevo valor del periodo."""
    n = e['n']
    lag1, lag2 = e.get(f'{base}_lag1'), e.get(f'{base}_lag2')
    c[f'{prefijo}_t'] = nuevo
    c[f'{prefijo}_delta'] = 0.0 if lag1 is None else nuevo - lag1
    c[f'{prefijo}_lag1'] = nuevo if lag1 is None else lag1
    c[f'{prefijo}_lag2'] = c[f'{prefijo}_lag1'] if lag2 is None else lag2
    valores = [v for v in (nuevo, lag1, lag2) if v is not None]
    c[f'{prefijo}_media_movil'] = sum(valores) / len(valores)
    c[f'{prefijo}_media_acum'] = ((e.get(f'{base}_suma_previa') or 0.0) + nuevo) / n
    minimo = nuevo if e.get(f'{base}_min_previo') is None else min(e[f'{base}_min_previo'], nuevo)
    c['promedio_minimo_hist' if prefijo == 'promedio' else 'asistencia_minima_hist'] = minimo
    c[f'{prefijo}_pendiente'] = (nuevo - c[f'{prefijo}_lag2']) / 2.0
    cohorte = e.get(f'cohorte_{base}')
    if cohorte:
        c[f'{prefijo}_rel_cohorte'] = _rel_cohorte(nuevo, cohorte)
        c[f'{prefijo}_pct_cohorte'] = _pct_cohorte(nuevo, cohorte)


def recalcular(caracteristicas: dict, estado: dict, cambios: dict) -> dict:
    """Devuelve las variables del modelo tras aplicar `cambios` a los valores del periodo actual.

    Solo se recalculan las variables que dependen de lo que cambió; el resto
    queda exactamente como lo vio el modelo al calificar.
    """
    c = dict(caracteristicas)
    e = estado
    n = e['n']
    for variable, valor in cambios.items():
        if variable not in VARIABLES_SIMULABLES or valor is None:
            continue
        spec = VARIABLES_SIMULABLES[variable]
        valor = float(min(max(float(valor), spec['min']), spec['max']))
        if variable == 'promedio':
            _serie('promedio', valor, e, 'promedio', c)
        elif variable == 'asistencia_pct':
            _serie('asistencia', valor, e, 'asistencia_pct', c)
            c['racha_asistencia_baja'] = (e.get('racha_previa') or 0) + 1 if valor < UMBRAL_ASISTENCIA_BAJA else 0
        elif variable == 'saldo_pendiente' and 'en_mora_t' in c:
            mora = int(valor > 0)
            c['en_mora_t'] = mora
            c['saldo_pendiente_t'] = valor
            c['pct_periodos_con_mora'] = ((e.get('mora_previa') or 0) + mora) / n
        elif variable == 'actividad_lms' and 'actividad_lms_log' in c:
            log = math.log1p(valor)
            c['actividad_lms_log'] = log
            c['actividad_lms_acum_log'] = math.log1p((e.get('actividad_acum_previa') or 0.0) + valor)
            previo = e.get('actividad_lag1_log')
            c['actividad_lms_delta'] = 0.0 if previo is None else log - previo
            rel = _rel_cohorte(log, e.get('cohorte_actividad_lms_log'))
            if rel is not None:
                c['actividad_rel_cohorte'] = rel
        elif variable == 'dias_sin_actividad' and 'dias_sin_actividad' in c:
            c['dias_sin_actividad'] = valor
        elif variable == 'evaluaciones_entregadas' and 'pct_entregadas' in c:
            vencidas = e.get('evaluaciones_vencidas_actual') or 0.0
            entregadas = min(valor, vencidas) if vencidas else valor
            c['pct_entregadas'] = entregadas / vencidas if vencidas > 0 else 1.0
            tardias = min(e.get('evaluaciones_tardias_actual') or 0.0, entregadas)
            c['pct_tardias'] = tardias / entregadas if entregadas > 0 else 0.0
    return c


def simulables(columnas_modelo: list[str]) -> dict:
    """Variables que se pueden simular con el modelo de una institución."""
    disponibles = {}
    for variable, spec in VARIABLES_SIMULABLES.items():
        requisito = {'base': 'promedio_t', 'financieras': 'en_mora_t', 'aula_virtual': 'actividad_lms_log',
                     'evaluaciones': 'pct_entregadas'}[spec['grupo']]
        if requisito in columnas_modelo:
            disponibles[variable] = spec
    return disponibles
