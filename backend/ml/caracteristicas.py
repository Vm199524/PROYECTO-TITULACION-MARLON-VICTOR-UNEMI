# -*- coding: utf-8 -*-
"""
Panel alumno-periodo y variables del modelo de abandono.

Unidad de análisis: el estudiante en un periodo académico (y corte de
seguimiento) determinado. Cada fila del panel responde: «con lo que se sabe
del estudiante hasta este periodo, ¿abandonará en el siguiente?». Las
variables solo usan información disponible hasta el periodo t; la etiqueta
es el estado del periodo t+1 dentro de la misma trayectoria.

Una TRAYECTORIA es la secuencia de periodos de un estudiante en una carrera
hasta una fila con es_ultimo_periodo = 1. El mismo código sirve para una
universidad por semestres (UNEMI) y para una por módulos con cortes de 28
días (OULAD).

Grupos de variables:
  - Base (toda institución): rendimiento y asistencia, con su nivel, cambio,
    rezagos, media móvil, media acumulada, peor valor, pendiente, racha de
    asistencia baja y posición frente a su cohorte (misma carrera, periodo y
    corte). La cohorte compara al estudiante con sus pares del mismo momento,
    no con el futuro.
  - Opcionales (si la institución los registra): financieras, de matrícula,
    de aula virtual y de evaluaciones. Si un grupo no existe en una
    institución, sus columnas se omiten y el modelo de esa institución no lo
    usa.

Una sola función arma el panel para entrenar y para calificar: si ambos lo
calcularan distinto, el modelo se descalibraría sin aviso.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

UMBRAL_ASISTENCIA_BAJA = 20.0
EPS = 1e-6

VARIABLES_BASE = [
    'nivel', 'corte', 'n_periodos_cursados', 'avance_relativo',
    'promedio_t', 'promedio_delta', 'promedio_lag1', 'promedio_lag2', 'promedio_media_movil',
    'promedio_media_acum', 'promedio_minimo_hist', 'promedio_pendiente',
    'asistencia_t', 'asistencia_delta', 'asistencia_lag1', 'asistencia_lag2', 'asistencia_media_movil',
    'asistencia_media_acum', 'asistencia_minima_hist', 'asistencia_pendiente', 'racha_asistencia_baja',
    'promedio_rel_cohorte', 'promedio_pct_cohorte', 'asistencia_rel_cohorte', 'asistencia_pct_cohorte',
]

GRUPOS_OPCIONALES: dict[str, dict[str, list[str]]] = {
    'financieras': {
        'fuente': ['saldo_pendiente'],
        'variables': ['en_mora_t', 'saldo_pendiente_t', 'pct_periodos_con_mora', 'beca_porcentaje'],
    },
    'matricula': {
        'fuente': ['numero_matricula'],
        'variables': ['creditos_matriculados', 'numero_matricula', 'dias_anticipacion_matricula'],
    },
    'aula_virtual': {
        'fuente': ['actividad_lms'],
        'variables': ['actividad_lms_log', 'actividad_lms_acum_log', 'actividad_lms_delta',
                      'actividad_rel_cohorte', 'dias_sin_actividad'],
    },
    'evaluaciones': {
        'fuente': ['evaluaciones_vencidas'],
        'variables': ['evaluaciones_vencidas', 'pct_entregadas', 'pct_tardias', 'nota_evaluaciones'],
    },
}

COLUMNAS_OPCIONALES_FUENTE = [
    'monto_matricula', 'beca_porcentaje', 'saldo_pendiente', 'creditos_matriculados', 'numero_matricula',
    'dias_anticipacion_matricula', 'actividad_lms', 'dias_sin_actividad', 'evaluaciones_vencidas',
    'evaluaciones_entregadas', 'evaluaciones_tardias', 'nota_evaluaciones',
]

DESCRIPCION = {
    'nivel': 'nivel o semestre que cursa',
    'corte': 'corte de seguimiento dentro del periodo',
    'n_periodos_cursados': 'periodos cursados en la carrera',
    'avance_relativo': 'avance respecto a la duración de la carrera',
    'promedio_t': 'promedio del periodo actual',
    'promedio_delta': 'cambio del promedio frente al periodo anterior',
    'promedio_lag1': 'promedio del periodo anterior',
    'promedio_lag2': 'promedio de hace dos periodos',
    'promedio_media_movil': 'promedio de los últimos tres periodos',
    'promedio_media_acum': 'promedio de toda su trayectoria',
    'promedio_minimo_hist': 'peor promedio de su trayectoria',
    'promedio_pendiente': 'tendencia del promedio en los últimos periodos',
    'asistencia_t': 'asistencia del periodo actual',
    'asistencia_delta': 'cambio de la asistencia frente al periodo anterior',
    'asistencia_lag1': 'asistencia del periodo anterior',
    'asistencia_lag2': 'asistencia de hace dos periodos',
    'asistencia_media_movil': 'asistencia de los últimos tres periodos',
    'asistencia_media_acum': 'asistencia de toda su trayectoria',
    'asistencia_minima_hist': 'peor asistencia de su trayectoria',
    'asistencia_pendiente': 'tendencia de la asistencia en los últimos periodos',
    'racha_asistencia_baja': 'periodos seguidos con asistencia muy baja',
    'promedio_rel_cohorte': 'promedio frente a sus compañeros de cohorte',
    'promedio_pct_cohorte': 'posición del promedio en su cohorte',
    'asistencia_rel_cohorte': 'asistencia frente a sus compañeros de cohorte',
    'asistencia_pct_cohorte': 'posición de la asistencia en su cohorte',
    'en_mora_t': 'tiene saldo pendiente en el periodo actual',
    'saldo_pendiente_t': 'saldo pendiente actual',
    'pct_periodos_con_mora': 'proporción de periodos con saldo pendiente',
    'beca_porcentaje': 'porcentaje de beca',
    'creditos_matriculados': 'créditos matriculados en el periodo',
    'numero_matricula': 'número de matrícula (repetición)',
    'dias_anticipacion_matricula': 'días de anticipación de la matrícula',
    'actividad_lms_log': 'actividad en el aula virtual en el periodo',
    'actividad_lms_acum_log': 'actividad acumulada en el aula virtual',
    'actividad_lms_delta': 'cambio de la actividad en el aula virtual',
    'actividad_rel_cohorte': 'actividad en el aula virtual frente a su cohorte',
    'dias_sin_actividad': 'días sin actividad en el aula virtual',
    'evaluaciones_vencidas': 'evaluaciones con plazo vencido',
    'pct_entregadas': 'proporción de evaluaciones entregadas',
    'pct_tardias': 'proporción de entregas tardías',
    'nota_evaluaciones': 'nota media de las evaluaciones entregadas',
}


def _num(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors='coerce').astype(float)


def grupos_disponibles(hist: pd.DataFrame, minimo: float = 0.5) -> list[str]:
    """Grupos opcionales con datos en al menos `minimo` de las filas de la institución."""
    disponibles = []
    for grupo, spec in GRUPOS_OPCIONALES.items():
        fuente = spec['fuente'][0]
        if fuente in hist.columns and _num(hist[fuente]).notna().mean() >= minimo:
            disponibles.append(grupo)
    return disponibles


def variables_modelo(grupos: list[str]) -> list[str]:
    """Lista ordenada de variables que usa el modelo con esos grupos opcionales."""
    columnas = list(VARIABLES_BASE)
    for grupo in grupos:
        columnas += GRUPOS_OPCIONALES[grupo]['variables']
    return columnas


def _rel_y_pct(h: pd.DataFrame, valor: str, claves: list[str]) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """Posición de cada fila frente a su cohorte: z (diferencia en desviaciones) y percentil."""
    grupo = h.groupby(claves, sort=False)[valor]
    media = grupo.transform('mean')
    desv = grupo.transform('std').fillna(0.0)
    rel = (h[valor] - media) / (desv + EPS)
    pct = grupo.rank(pct=True, method='average')
    return rel, pct, pd.DataFrame({'media': media, 'desv': desv})


def construir_panel(hist: pd.DataFrame) -> pd.DataFrame:
    """Construye el panel alumno-periodo a partir de la trayectoria leída del almacén.

    Espera, por fila: matricula_id, alumno_id, carrera_id, periodo_id, fecha,
    nivel, corte, estado_codigo, es_ultimo_periodo, promedio, asistencia_pct
    y, si existen, las columnas opcionales de COLUMNAS_OPCIONALES_FUENTE.

    Returns:
        Una fila por periodo con las variables, la etiqueta `y` (1 si el
        periodo siguiente de la trayectoria es RETIRADO, 0 si no, NaN si no hay
        siguiente) y `para_calificar` (1 en el periodo vigente de quien sigue
        ACTIVO). Es una transformación pura, sin base de datos.
    """
    if hist.empty:
        return pd.DataFrame(columns=['matricula_id', 'alumno_id', 'y', 'para_calificar'] + VARIABLES_BASE)

    h = hist.sort_values(['alumno_id', 'carrera_id', 'fecha', 'matricula_id']).reset_index(drop=True).copy()
    h['es_ultimo_periodo'] = h['es_ultimo_periodo'].astype(int)
    for c in ['promedio', 'asistencia_pct', 'nivel', 'corte'] + [c for c in COLUMNAS_OPCIONALES_FUENTE if c in h]:
        h[c] = _num(h[c])

    # Trayectorias: una nueva empieza después de cada fila de cierre.
    previo = h.groupby(['alumno_id', 'carrera_id'], sort=False)['es_ultimo_periodo'].shift(fill_value=0)
    h['trayectoria'] = previo.groupby([h['alumno_id'], h['carrera_id']], sort=False).cumsum()
    h['tray_id'] = h.groupby(['alumno_id', 'carrera_id', 'trayectoria'], sort=False).ngroup()
    g = h.groupby('tray_id', sort=False)
    n = g.cumcount() + 1
    h['n_periodos_cursados'] = n

    for base, valor in (('promedio', 'promedio'), ('asistencia', 'asistencia_pct')):
        v = h[valor]
        lag1, lag2 = g[valor].shift(1), g[valor].shift(2)
        h[f'{base}_t'] = v
        h[f'{base}_delta'] = (v - lag1).fillna(0.0)
        h[f'{base}_lag1'] = lag1.fillna(v)
        h[f'{base}_lag2'] = lag2.fillna(h[f'{base}_lag1'])
        suma = v + lag1.fillna(0.0) + lag2.fillna(0.0)
        cuenta = 1 + lag1.notna().astype(int) + lag2.notna().astype(int)
        h[f'{base}_media_movil'] = suma / cuenta
        h[f'{base}_media_acum'] = g[valor].cumsum() / n
        nombre_minimo = 'promedio_minimo_hist' if base == 'promedio' else 'asistencia_minima_hist'
        h[nombre_minimo] = g[valor].cummin()
        h[f'{base}_pendiente'] = (v - h[f'{base}_lag2']) / 2.0

    baja = (h['asistencia_pct'] < UMBRAL_ASISTENCIA_BAJA).astype(int)
    tramo = (baja == 0).astype(int).groupby(h['tray_id'], sort=False).cumsum()
    h['racha_asistencia_baja'] = baja.groupby([h['tray_id'], tramo], sort=False).cumsum()

    duracion = h.groupby('carrera_id')['nivel'].transform(lambda s: max(float(s.quantile(0.95)), 1.0))
    h['avance_relativo'] = (h['nivel'] / duracion).clip(upper=1.5)

    cohorte = ['carrera_id', 'periodo_id', 'corte']
    h['promedio_rel_cohorte'], h['promedio_pct_cohorte'], _ = _rel_y_pct(h, 'promedio', cohorte)
    h['asistencia_rel_cohorte'], h['asistencia_pct_cohorte'], _ = _rel_y_pct(h, 'asistencia_pct', cohorte)

    if 'saldo_pendiente' in h and h['saldo_pendiente'].notna().any():
        h['en_mora_t'] = (h['saldo_pendiente'].fillna(0) > 0).astype(int)
        h['saldo_pendiente_t'] = h['saldo_pendiente']
        h['pct_periodos_con_mora'] = h.groupby('tray_id', sort=False)['en_mora_t'].cumsum() / n
    if 'actividad_lms' in h and h['actividad_lms'].notna().any():
        h['actividad_lms_log'] = np.log1p(h['actividad_lms'].clip(lower=0))
        acumulada = h['actividad_lms'].fillna(0).clip(lower=0).groupby(h['tray_id'], sort=False).cumsum()
        h['actividad_lms_acum_log'] = np.log1p(acumulada)
        anterior = h.groupby('tray_id', sort=False)['actividad_lms_log'].shift(1)
        h['actividad_lms_delta'] = (h['actividad_lms_log'] - anterior).fillna(0.0)
        h['actividad_rel_cohorte'], _, _ = _rel_y_pct(h, 'actividad_lms_log', cohorte)
    if 'evaluaciones_vencidas' in h and h['evaluaciones_vencidas'].notna().any():
        vencidas = h['evaluaciones_vencidas']
        entregadas = h.get('evaluaciones_entregadas', pd.Series(np.nan, index=h.index))
        tardias = h.get('evaluaciones_tardias', pd.Series(np.nan, index=h.index))
        h['pct_entregadas'] = np.where(vencidas > 0, entregadas / vencidas.replace(0, np.nan), 1.0)
        h['pct_tardias'] = np.where(entregadas > 0, tardias / entregadas.replace(0, np.nan), 0.0)

    # Etiqueta: estado del periodo siguiente dentro de la misma trayectoria.
    siguiente = g['estado_codigo'].shift(-1)
    h['y'] = np.where(siguiente.isna(), np.nan, (siguiente == 'RETIRADO').astype(float))
    h['para_calificar'] = ((h['es_ultimo_periodo'] == 1) & (h['estado_codigo'] == 'ACTIVO')).astype(int)
    return h


def matriz(panel: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Matriz de entrada del modelo con exactamente esas columnas (NaN si faltan)."""
    X = pd.DataFrame(index=panel.index)
    for c in columnas:
        X[c] = _num(panel[c]) if c in panel else np.nan
    return X.reset_index(drop=True)


def describir(variable: str) -> str:
    """Nombre de una variable en lenguaje natural, para una autoridad sin perfil técnico."""
    return DESCRIPCION.get(variable, variable.replace('_', ' '))


def _coma(texto: str) -> str:
    """Decimal con coma (es-EC): 4.51 → 4,51. Solo entre dígitos, para no tocar otros puntos."""
    return re.sub(r'(?<=\d)\.(?=\d)', ',', texto)


def formatear_valor(variable: str, valor: float | None) -> str:
    """Valor de una variable en unidades legibles (%, nota sobre 10, días, sí/no)."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return 'sin dato'
    v = float(valor)
    if variable.startswith('asistencia') and 'cohorte' not in variable:
        return _coma(f'{v:+.1f} puntos' if variable.endswith(('delta', 'pendiente')) else f'{v:.1f} %')
    if variable.startswith('promedio') and 'cohorte' not in variable:
        return _coma(f'{v:+.2f}' if variable.endswith(('delta', 'pendiente')) else f'{v:.2f} / 10')
    if variable.endswith('rel_cohorte'):
        return _coma(f'{v:+.1f} desviaciones' if abs(v) < 50 else 'fuera de rango')
    if variable.endswith('pct_cohorte'):
        return _coma(f'percentil {v * 100:.0f}')
    if variable in ('pct_periodos_con_mora', 'pct_entregadas', 'pct_tardias'):
        return _coma(f'{v * 100:.0f} %')
    if variable == 'en_mora_t':
        return 'sí' if v >= 0.5 else 'no'
    if variable == 'saldo_pendiente_t':
        return f'${v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    if variable in ('dias_sin_actividad', 'dias_anticipacion_matricula'):
        return _coma(f'{v:.0f} días')
    if variable == 'nota_evaluaciones':
        return _coma(f'{v:.2f} / 10')
    if variable == 'avance_relativo':
        return _coma(f'{v * 100:.0f} % de la carrera')
    if variable.startswith('actividad_lms') and variable.endswith('log'):
        return f'{np.expm1(v):,.0f} interacciones'.replace(',', '.')
    if variable == 'beca_porcentaje':
        return _coma(f'{v:.0f} %')
    return _coma(f'{v:.0f}' if float(v).is_integer() else f'{v:.2f}')


def _cuantiles_cohorte(panel: pd.DataFrame, valor: str, claves: list[str], filas: pd.DataFrame) -> dict:
    """Media, desviación y 21 cuantiles de `valor` en la cohorte de cada fila pedida."""
    necesarias = filas[claves].drop_duplicates()
    sub = panel.merge(necesarias, on=claves, how='inner')
    salida = {}
    for clave, grupo in sub.groupby(claves, sort=False):
        s = grupo[valor].dropna().to_numpy(dtype=float)
        if len(s) == 0:
            continue
        salida[clave if isinstance(clave, tuple) else (clave,)] = {
            'media': float(s.mean()), 'desv': float(s.std(ddof=1)) if len(s) > 1 else 0.0,
            'cuantiles': [float(q) for q in np.quantile(s, np.linspace(0, 1, 21))]}
    return salida


def estado_simulacion(panel: pd.DataFrame, filas: pd.DataFrame) -> list[dict]:
    """Lo necesario para recalcular las variables de una fila si cambian sus valores actuales.

    Lo usa el simulador de la ficha (ml/simulacion.py): con los rezagos, los
    acumulados previos y la distribución de la cohorte, recalcula exactamente
    las mismas variables que construir_panel() sin volver a leer el almacén.
    """
    g = panel.groupby('tray_id', sort=False)
    previos = pd.DataFrame(index=panel.index)
    for valor in ('promedio', 'asistencia_pct'):
        anterior = g[valor].shift(1)
        previos[f'{valor}_lag1'] = anterior
        previos[f'{valor}_lag2'] = g[valor].shift(2)
        previos[f'{valor}_min_previo'] = anterior.groupby(panel['tray_id'], sort=False).cummin()
        previos[f'{valor}_suma_previa'] = g[valor].cumsum() - panel[valor]
    previos['racha_previa'] = g['racha_asistencia_baja'].shift(1).fillna(0)
    if 'en_mora_t' in panel:
        previos['mora_previa'] = g['en_mora_t'].cumsum() - panel['en_mora_t']
    if 'actividad_lms_log' in panel:
        previos['actividad_lag1_log'] = g['actividad_lms_log'].shift(1)
        previos['actividad_acum_previa'] = (panel['actividad_lms'].fillna(0).clip(lower=0)
                                            .groupby(panel['tray_id'], sort=False).cumsum()
                                            - panel['actividad_lms'].fillna(0).clip(lower=0))
    cohorte = ['carrera_id', 'periodo_id', 'corte']
    cuantiles = {v: _cuantiles_cohorte(panel, v, cohorte, filas)
                 for v in ('promedio', 'asistencia_pct', 'actividad_lms_log') if v in panel}

    def limpio(x):
        return None if x is None or (isinstance(x, float) and np.isnan(x)) else float(x)

    estados = []
    for idx, fila in filas.iterrows():
        clave = tuple(fila[c] for c in cohorte)
        e = {'n': int(fila['n_periodos_cursados'])}
        for col in previos.columns:
            e[col] = limpio(previos.at[idx, col])
        for v, mapa in cuantiles.items():
            e[f'cohorte_{v}'] = mapa.get(clave)
        for col in ('evaluaciones_vencidas', 'evaluaciones_entregadas', 'evaluaciones_tardias', 'saldo_pendiente',
                    'actividad_lms', 'dias_sin_actividad', 'promedio', 'asistencia_pct'):
            if col in fila:
                e[f'{col}_actual'] = limpio(fila[col])
        estados.append(e)
    return estados
