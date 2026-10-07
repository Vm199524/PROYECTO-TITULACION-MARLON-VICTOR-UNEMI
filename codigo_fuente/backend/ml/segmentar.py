# -*- coding: utf-8 -*-
"""
Segmentación de las carreras por perfil de riesgo.

Agrupa las carreras (o módulos) de una institución con K-Means según cuatro
indicadores estandarizados: tasa histórica de abandono, promedio y
asistencia históricos y riesgo medio actual de sus estudiantes activos. La
autoridad obtiene tres segmentos ordenados por riesgo (Atención prioritaria,
Estable, Bajo riesgo) para asignar recursos por programa y no solo por
estudiante.

Antes de guardarse, la partición se valida (Melchor et al., 2026; Valles-Coral
et al., 2022):
  1. Barrido de k = 2..6 con silhouette, Davies-Bouldin y Calinski-Harabasz.
  2. Estabilidad: índice de Rand ajustado medio frente a 100 remuestreos.
  3. Comparación con jerárquico (Ward) y HDBSCAN.
  4. Kruskal-Wallis: ¿la tasa de abandono difiere entre segmentos?
  5. Variante sin el riesgo del modelo, para descartar circularidad.

Uso:
    cd backend
    python -m ml.segmentar --institucion UNEMI_PRUEBAS

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kruskal
from sklearn.cluster import HDBSCAN, AgglomerativeClustering, KMeans
from sklearn.metrics import adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

VERSION = '3.0-kmeans'
SEMILLA = 20260909
RAIZ_MODELOS = Path(__file__).resolve().parent / 'modelos'
INDICADORES = ['tasa_abandono_hist', 'promedio_hist', 'asistencia_hist', 'riesgo_promedio']
SEGMENTOS = ['Atención prioritaria', 'Estable', 'Bajo riesgo']   # de mayor a menor riesgo

SQL_INDICADORES = """
SELECT fm.carrera_id, dc.carrera,
       COUNT(DISTINCT fm.alumno_id) AS estudiantes,
       AVG(CAST(fm.promedio AS FLOAT)) AS promedio_hist,
       AVG(CAST(fm.asistencia_pct AS FLOAT)) AS asistencia_hist,
       CAST(SUM(CASE WHEN fm.es_ultimo_periodo = 1 AND fm.estado_codigo = 'RETIRADO' THEN 1 ELSE 0 END) AS FLOAT)
         / NULLIF(SUM(CASE WHEN fm.es_ultimo_periodo = 1 AND fm.estado_codigo <> 'ACTIVO' THEN 1 ELSE 0 END), 0)
         AS tasa_abandono_hist
FROM dbo.fact_matriculas fm JOIN dbo.dim_carrera dc ON dc.carrera_id = fm.carrera_id
WHERE fm.institucion_codigo = ?
GROUP BY fm.carrera_id, dc.carrera
"""
SQL_RIESGO = """
SELECT fm.carrera_id, AVG(CAST(fp.probabilidad AS FLOAT)) AS riesgo_promedio,
       SUM(CASE WHEN fp.riesgo_categoria IN ('ALTO', 'MEDIO') THEN 1 ELSE 0 END) AS activos_en_riesgo
FROM dbo.fact_prediccion_abandono fp JOIN dbo.fact_matriculas fm ON fm.matricula_id = fp.matricula_id_base
WHERE fp.institucion_codigo = ?
GROUP BY fm.carrera_id
"""


def _escalar(df: pd.DataFrame, columnas: list[str]) -> np.ndarray:
    return StandardScaler().fit_transform(df[columnas].fillna(0.0))


def indice_riesgo(df: pd.DataFrame) -> pd.Series:
    """Índice para ordenar los segmentos con los dos resultados de riesgo (puntajes z):
    el abandono que ya ocurrió (tasa histórica) y el que el modelo anticipa (riesgo
    promedio de los activos). Promedio y asistencia agrupan, pero no ordenan: son causas
    posibles, no el resultado que la autoridad quiere vigilar."""
    z = lambda c: (df[c] - df[c].mean()) / (df[c].std(ddof=0) or 1.0)  # noqa: E731
    return z('tasa_abandono_hist') + z('riesgo_promedio')


def asignar(df: pd.DataFrame, k: int = 3, columnas: list[str] | None = None) -> pd.DataFrame:
    """K-Means con etiquetas ordenadas por el índice de riesgo compuesto del clúster
    (nunca por el número del clúster, que es arbitrario)."""
    columnas = columnas or INDICADORES
    k = min(k, len(df))
    df = df.copy()
    df['cluster'] = KMeans(n_clusters=k, random_state=SEMILLA, n_init=20).fit_predict(_escalar(df, columnas))
    df['_indice'] = indice_riesgo(df.fillna(0.0)) if 'riesgo_promedio' in df else df['tasa_abandono_hist']
    orden = df.groupby('cluster')['_indice'].mean().sort_values(ascending=False).index.tolist()
    df = df.drop(columns='_indice')
    etiquetas = SEGMENTOS if k == 3 else [f'Segmento {i + 1}' for i in range(k)]
    df['orden_segmento'] = df['cluster'].map({c: i + 1 for i, c in enumerate(orden)})
    df['segmento'] = df['orden_segmento'].map(lambda i: etiquetas[i - 1])
    return df


def validar(df: pd.DataFrame, k: int) -> dict:
    """Validación completa de la segmentación (ver docstring del módulo)."""
    X = _escalar(df, INDICADORES)
    barrido = []
    for kk in range(2, min(6, len(df) - 1) + 1):
        e = KMeans(n_clusters=kk, random_state=SEMILLA, n_init=20).fit_predict(X)
        barrido.append({'k': kk, 'silhouette': round(float(silhouette_score(X, e)), 4),
                        'davies_bouldin': round(float(davies_bouldin_score(X, e)), 4),
                        'calinski_harabasz': round(float(calinski_harabasz_score(X, e)), 2)})
    referencia = KMeans(n_clusters=k, random_state=SEMILLA, n_init=20).fit_predict(X)
    rng, aris = np.random.default_rng(SEMILLA), []
    for _ in range(100):
        idx = rng.choice(len(X), size=len(X), replace=True)
        if len(np.unique(X[idx], axis=0)) < k:
            continue
        aris.append(adjusted_rand_score(referencia, KMeans(n_clusters=k, random_state=SEMILLA, n_init=10)
                                        .fit(X[idx]).predict(X)))
    comparacion = {}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        for nombre, etiquetas in (('KMEANS', referencia),
                                  ('JERARQUICO_WARD', AgglomerativeClustering(n_clusters=k, linkage='ward').fit_predict(X)),
                                  ('HDBSCAN', HDBSCAN(min_cluster_size=2).fit_predict(X))):
            validos = etiquetas >= 0
            n = len(set(etiquetas[validos]))
            sil = silhouette_score(X[validos], etiquetas[validos]) if n >= 2 and validos.sum() > n else None
            comparacion[nombre] = {'clusteres': int(n), 'ruido': int((~validos).sum()),
                                   'silhouette': None if sil is None else round(float(sil), 4)}
    final = asignar(df, k)
    grupos = [g['tasa_abandono_hist'].to_numpy() for _, g in final.groupby('segmento')]
    kw = kruskal(*grupos) if len(grupos) >= 2 and sum(len(g) for g in grupos) > len(grupos) else None
    sin_riesgo = asignar(df, k, ['tasa_abandono_hist', 'promedio_hist', 'asistencia_hist'])
    return {
        'unidades': int(len(df)), 'k': k, 'barrido_k': barrido,
        'silhouette': next((b['silhouette'] for b in barrido if b['k'] == k), None),
        'estabilidad': {'remuestreos': len(aris), 'ari_medio': round(float(np.mean(aris)), 4) if aris else None,
                        'ari_desviacion': round(float(np.std(aris)), 4) if aris else None},
        'comparacion_algoritmos': comparacion,
        'kruskal_wallis': None if kw is None else {'H': round(float(kw.statistic), 4), 'p': round(float(kw.pvalue), 6)},
        'ari_sin_riesgo_del_modelo': round(float(adjusted_rand_score(final['cluster'], sin_riesgo['cluster'])), 4),
        'segmentos': {s: {'carreras': int((final.segmento == s).sum()),
                          'tasa_media': round(float(final.loc[final.segmento == s, 'tasa_abandono_hist'].mean()), 4)}
                      for s in final['segmento'].unique()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--institucion', required=True)
    parser.add_argument('--k', type=int, default=3)
    args = parser.parse_args()
    inst = args.institucion.strip().upper()

    from core.db import conectar_admin
    conn = conectar_admin()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        df = pd.read_sql(SQL_INDICADORES, conn, params=[inst]).merge(
            pd.read_sql(SQL_RIESGO, conn, params=[inst]), on='carrera_id', how='left')
    df['riesgo_promedio'] = df['riesgo_promedio'].fillna(0.0)
    df['activos_en_riesgo'] = df['activos_en_riesgo'].fillna(0).astype(int)
    df['tasa_abandono_hist'] = df['tasa_abandono_hist'].fillna(0.0)
    print(f'{len(df)} carreras o módulos con datos en {inst}.')
    if len(df) < 4:
        print('Se necesitan al menos 4 unidades para segmentar y validar.')
        return 0
    validacion = validar(df, args.k)
    final = asignar(df, args.k)
    print(final[['carrera', 'segmento', 'tasa_abandono_hist', 'riesgo_promedio']].to_string(index=False))

    cur = conn.cursor()
    cur.execute('DELETE FROM dbo.fact_segmento_carrera WHERE institucion_codigo = ?', inst)
    cur.executemany("""INSERT INTO dbo.fact_segmento_carrera (institucion_codigo, carrera_id, segmento, orden_segmento,
                       estudiantes, tasa_abandono_hist, promedio_hist, asistencia_hist, riesgo_promedio,
                       activos_en_riesgo, modelo_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [(inst, int(r.carrera_id), r.segmento, int(r.orden_segmento), int(r.estudiantes),
                      round(float(r.tasa_abandono_hist), 4), round(float(r.promedio_hist), 2),
                      round(float(r.asistencia_hist), 2), round(float(r.riesgo_promedio), 4),
                      int(r.activos_en_riesgo), VERSION) for r in final.itertuples()])
    metricas = [('SILHOUETTE', validacion['silhouette'], None),
                ('ESTABILIDAD_ARI', validacion['estabilidad']['ari_medio'], validacion['estabilidad']['ari_desviacion'])]
    if validacion['kruskal_wallis']:
        metricas.append(('KRUSKAL_WALLIS_P', validacion['kruskal_wallis']['p'], None))
    cur.execute("DELETE FROM dbo.fact_evaluacion_modelo WHERE institucion_codigo = ? AND componente = 'SEGMENTACION'", inst)
    cur.executemany("""INSERT INTO dbo.fact_evaluacion_modelo (institucion_codigo, componente, modelo, esquema_validacion,
                       metrica, valor, desviacion, es_modelo_final, modelo_version)
                       VALUES (?, 'SEGMENTACION', ?, 'VALIDACION_INTERNA', ?, ?, ?, 1, ?)""",
                    [(inst, f'KMEANS_K{args.k}', m, v, d, VERSION) for m, v, d in metricas if v is not None])
    conn.commit()
    conn.close()
    destino = RAIZ_MODELOS / inst
    destino.mkdir(parents=True, exist_ok=True)
    (destino / 'segmentacion.json').write_text(json.dumps(
        {'institucion': inst, 'version': VERSION, **validacion,
         'asignacion': final[['carrera', 'segmento'] + INDICADORES].round(4).to_dict('records')},
        indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    print(f"Silhouette {validacion['silhouette']}; ARI {validacion['estabilidad']['ari_medio']}; "
          f"Kruskal-Wallis {validacion['kruskal_wallis']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
