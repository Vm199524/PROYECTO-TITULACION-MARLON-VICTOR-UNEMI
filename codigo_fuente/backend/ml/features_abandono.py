# -*- coding: utf-8 -*-
"""
Ingeniería de características del modelo de abandono.

Compartida entre entrenar_abandono.py (entrenamiento) y predecir_abandono.py
(calificación). Se comparte a propósito: si entrenamiento y predicción
calcularan las características de forma distinta, el modelo quedaría mal
calibrado sin que nada lo avise (training/serving skew). Una sola función,
dos consumidores.

PANEL ALUMNO-PERIODO
--------------------
La unidad de análisis declarada en la sección 1.3 es "el alumno en un
periodo académico determinado", y el propósito es anticipar el abandono
ANTES de que ocurra. Por eso cada fila del panel es (alumno, carrera,
periodo t) y se construye SOLO con información disponible hasta t:

    X_t  = rendimiento, asistencia y mora hasta el periodo t (nivel, cambio
           respecto a t-1, media móvil, peor valor histórico)
    y_t  = 1 si en el periodo t+1 el alumno queda RETIRADO, 0 si sigue
           (o termina) — "¿abandonará el próximo periodo?"

No se usa una fila por alumno con el estado final como etiqueta: tomaría la
asistencia del MISMO periodo en que el alumno ya se retiró y detectaría el
abandono en lugar de anticiparlo.

  - Entrenamiento: filas con un periodo siguiente conocido.
  - Calificación: el periodo más reciente de cada trayectoria que sigue
    ACTIVA (predice el próximo periodo).
  - Arranque en frío: quien abandona en su primer periodo no tiene historia
    previa y no puede anticiparse con este enfoque (limitación declarada;
    ver Carballo-Mendívil et al., 2025, para el enfoque previo a la matrícula).

Una TRAYECTORIA es una secuencia de periodos de un alumno en una carrera que
termina en una fila con es_ultimo_periodo = 1. Así el mismo código sirve para
UNEMI (una carrera por alumno) y para OULAD (un estudiante puede cursar
varios módulos, o repetir uno en otra presentación).

Lee CHAT con la conexión administrativa: es un proceso por lotes, no una
consulta de un usuario del chat, así que no pasa por chat_reader.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pyodbc

FEATURE_COLUMNS_NUMERICAS = [
    'periodo',
    'n_periodos_cursados',
    'promedio_t',
    'promedio_delta',
    'promedio_media_movil',
    'promedio_minimo_hist',
    'asistencia_t',
    'asistencia_delta',
    'asistencia_media_movil',
    'asistencia_minima_hist',
    'en_mora_t',
    'saldo_pendiente_t',
    'pct_periodos_con_mora',
    'beca_porcentaje',
]

# Variables categóricas del requerimiento ("carrera, sede, ciclo, rendimiento,
# canal"): de baja cardinalidad, se codifican one-hot (codificar_categoricas).
FEATURE_COLUMNS_CATEGORICAS = ['sede_codigo', 'canal_codigo']

# Descripción en lenguaje natural de cada variable, para explicar a una
# autoridad no técnica por qué un alumno está en riesgo (factor_1..3).
DESCRIPCION_FEATURE = {
    'periodo': 'periodo académico en curso',
    'n_periodos_cursados': 'número de periodos cursados',
    'promedio_t': 'promedio del último periodo',
    'promedio_delta': 'cambio del promedio respecto al periodo anterior',
    'promedio_media_movil': 'promedio de los últimos periodos',
    'promedio_minimo_hist': 'peor promedio de su historial',
    'asistencia_t': 'asistencia del último periodo',
    'asistencia_delta': 'cambio de la asistencia respecto al periodo anterior',
    'asistencia_media_movil': 'asistencia de los últimos periodos',
    'asistencia_minima_hist': 'peor asistencia de su historial',
    'en_mora_t': 'mora en el último periodo',
    'saldo_pendiente_t': 'saldo pendiente actual',
    'pct_periodos_con_mora': 'proporción de periodos con mora',
    'beca_porcentaje': 'porcentaje de beca',
}

# Periodos que promedian las medias móviles (incluido el periodo t).
VENTANA_MOVIL = 3


def _query_historial(conn: pyodbc.Connection, empresa_codigo: str) -> pd.DataFrame:
    """Lee de CHAT el historial de matrículas de la institución.

    Ordena por alumno, carrera, fecha y fila, y convierte promedio,
    asistencia y saldo a float y es_ultimo_periodo a entero.
    """
    sql = """
        SELECT fm.fact_id, fm.alumno_id, fm.carrera_id, da.cedula, da.apellidos, da.nombres,
               dt.fecha, dt.anio, fm.semestre, fm.promedio, fm.asistencia_pct,
               fm.saldo_pendiente, fm.beca_porcentaje, fm.estado_codigo,
               fm.es_ultimo_periodo, df.facultad_codigo, df.facultad_nombre, dc.carrera,
               fm.sede_codigo, fm.canal_codigo
        FROM CHAT.dbo.fact_matriculas fm
        JOIN CHAT.dbo.dim_alumno da ON da.alumno_id = fm.alumno_id
        JOIN CHAT.dbo.dim_tiempo dt ON dt.tiempo_id = fm.tiempo_id
        JOIN CHAT.dbo.dim_facultad df ON df.facultad_codigo = fm.facultad_codigo
        JOIN CHAT.dbo.dim_carrera dc ON dc.carrera_id = fm.carrera_id
        WHERE fm.empresa_codigo = ?
        ORDER BY fm.alumno_id, fm.carrera_id, dt.fecha, fm.fact_id
    """
    df = pd.read_sql(sql, conn, params=[empresa_codigo])
    for c in ('promedio', 'asistencia_pct', 'saldo_pendiente'):
        df[c] = df[c].astype(float)
    df['es_ultimo_periodo'] = df['es_ultimo_periodo'].astype(int)
    return df


def construir_panel_desde_historial(hist: pd.DataFrame) -> pd.DataFrame:
    """Construye el panel alumno-periodo a partir del historial de matrículas.

    Es una transformación pura (sin base de datos), para poder probarla
    aislada. Las características se calculan dentro de cada trayectoria y
    solo con los periodos hasta t (diferencias, medias móviles, mínimos y
    proporciones acumuladas).

    Returns:
        Una fila por periodo con las columnas del historial más la
        trayectoria, las características, la etiqueta `y` (1 si el periodo
        siguiente de la trayectoria es RETIRADO, 0 si no, NaN si no hay
        periodo siguiente) y `para_calificar` (1 en el último periodo de una
        trayectoria que sigue ACTIVA).
    """
    if hist.empty:
        return pd.DataFrame(columns=['fact_id', 'alumno_id', 'y'] + FEATURE_COLUMNS_NUMERICAS)

    h = hist.sort_values(['alumno_id', 'carrera_id', 'fecha', 'fact_id']).reset_index(drop=True)
    por_carrera = h.groupby(['alumno_id', 'carrera_id'], sort=False)
    # Nueva trayectoria después de cada fila de cierre (es_ultimo_periodo = 1).
    h['trayectoria'] = por_carrera['es_ultimo_periodo'].transform(lambda s: s.shift(fill_value=0).cumsum())
    g = h.groupby(['alumno_id', 'carrera_id', 'trayectoria'], sort=False)

    h['periodo'] = h['semestre'].astype(int)
    h['n_periodos_cursados'] = g.cumcount() + 1
    h['promedio_t'] = h['promedio']
    h['promedio_delta'] = g['promedio'].diff().fillna(0.0)
    h['promedio_media_movil'] = g['promedio'].transform(lambda s: s.rolling(VENTANA_MOVIL, min_periods=1).mean())
    h['promedio_minimo_hist'] = g['promedio'].cummin()
    h['asistencia_t'] = h['asistencia_pct']
    h['asistencia_delta'] = g['asistencia_pct'].diff().fillna(0.0)
    h['asistencia_media_movil'] = g['asistencia_pct'].transform(lambda s: s.rolling(VENTANA_MOVIL, min_periods=1).mean())
    h['asistencia_minima_hist'] = g['asistencia_pct'].cummin()
    h['en_mora_t'] = (h['saldo_pendiente'] > 0).astype(int)
    h['saldo_pendiente_t'] = h['saldo_pendiente']
    h['pct_periodos_con_mora'] = g['en_mora_t'].transform(lambda s: s.expanding().mean())
    h['beca_porcentaje'] = h['beca_porcentaje'].astype(int)

    # Etiqueta: estado del periodo siguiente dentro de la misma trayectoria.
    siguiente = g['estado_codigo'].shift(-1)
    h['y'] = np.where(siguiente.isna(), np.nan, (siguiente == 'RETIRADO').astype(float))
    h['para_calificar'] = ((h['es_ultimo_periodo'] == 1) & (h['estado_codigo'] == 'ACTIVO')).astype(int)
    return h


def construir_panel(conn: pyodbc.Connection, empresa_codigo: str) -> pd.DataFrame:
    """Lee el historial de la institución y construye su panel alumno-periodo."""
    return construir_panel_desde_historial(_query_historial(conn, empresa_codigo))


def informe_atipicos(panel: pd.DataFrame) -> dict:
    """Cuenta los valores atípicos por rango intercuartílico (IQR).

    Forma parte de la preparación de datos (Alzabidi et al., 2026) y revisa
    promedio, asistencia y saldo pendiente. Solo INFORMA: no elimina filas,
    porque en abandono un valor extremo (asistencia muy baja) suele ser
    justamente la señal que se quiere aprender.

    Returns:
        Por columna: q1, q3, número y porcentaje de valores fuera de
        [q1 - 1,5·IQR, q3 + 1,5·IQR].
    """
    informe = {}
    for col in ('promedio_t', 'asistencia_t', 'saldo_pendiente_t'):
        s = panel[col].astype(float)
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        fuera = ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr))
        informe[col] = {
            'q1': round(float(q1), 2), 'q3': round(float(q3), 2),
            'atipicos': int(fuera.sum()), 'pct_atipicos': round(float(fuera.mean()) * 100, 2),
        }
    return informe


def codificar_categoricas(df: pd.DataFrame, columnas_dummy_esperadas: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Codifica en one-hot las columnas de FEATURE_COLUMNS_CATEGORICAS.

    Si `columnas_dummy_esperadas` viene dado (el caso de calificación: las
    columnas que el modelo vio al entrenar), reindexa a ESA lista exacta: si
    aparece una sede o canal nuevo que no existía al entrenar, se descarta;
    si falta uno que sí existía, se rellena con 0.

    Returns:
        (columnas dummy, lista de sus nombres).
    """
    dummies = pd.get_dummies(df[FEATURE_COLUMNS_CATEGORICAS], prefix=FEATURE_COLUMNS_CATEGORICAS).astype(int)
    if columnas_dummy_esperadas is not None:
        dummies = dummies.reindex(columns=columnas_dummy_esperadas, fill_value=0)
    return dummies, list(dummies.columns)


def matriz_X(df: pd.DataFrame, columnas_dummy: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Arma la matriz de entrada del modelo.

    Pone las columnas numéricas (como float) seguidas de las categóricas en
    one-hot. Al calificar se pasan las columnas dummy del entrenamiento para
    que la matriz tenga exactamente las mismas columnas.

    Returns:
        (X, nombres de las columnas dummy).
    """
    dummies, cols_dummy = codificar_categoricas(df, columnas_dummy)
    X = pd.concat([df[FEATURE_COLUMNS_NUMERICAS].reset_index(drop=True).astype(float),
                   dummies.reset_index(drop=True)], axis=1)
    return X, cols_dummy


def describir_feature(nombre: str) -> str:
    """Traduce el nombre de una variable a una frase para una autoridad no técnica.

    Las columnas dummy se describen como "sede <valor>" o "modalidad <valor>";
    un nombre desconocido se devuelve tal cual.
    """
    if nombre in DESCRIPCION_FEATURE:
        return DESCRIPCION_FEATURE[nombre]
    for pref in FEATURE_COLUMNS_CATEGORICAS:
        if nombre.startswith(pref + '_'):
            return f"{'sede' if pref == 'sede_codigo' else 'modalidad'} {nombre[len(pref) + 1:].lower()}"
    return nombre
