# -*- coding: utf-8 -*-
"""
Segmentación de las carreras de una institución por perfil de riesgo.

Agrupa con K-Means las CARRERAS (o módulos, en OULAD) de una institución
según su perfil de riesgo y VALIDA la partición antes de guardarla en
CHAT.dbo.fact_cluster_carrera, que consultan el panel y el chat.

Por qué carreras y no universidades: con pocos referentes externos, agrupar
instituciones completas no es estadísticamente defendible; segmentar las
unidades académicas propias sí tiene volumen y es accionable ("qué
programas necesitan atención prioritaria"). Ver documentacion/tecnica/BENCHMARKING_INSTITUCIONAL.md.

Indicadores por carrera (se estandarizan con StandardScaler porque tienen
escalas distintas):
  - tasa_abandono_hist: proporción de trayectorias cuyo último periodo
    cierra como RETIRADO
  - promedio_hist: rendimiento académico histórico promedio
  - riesgo_promedio: probabilidad media de abandono de los alumnos ACTIVOS
    (salida de ml/predecir_abandono.py)

Validación (Melchor et al., 2026: los clústeres deben someterse a una
validación rigurosa antes de usarse para decidir; Valles-Coral et al.,
2022: comparar algoritmos):
  1. Barrido de k = 2..6: silhouette, Davies-Bouldin, Calinski-Harabasz.
  2. Estabilidad: ARI medio entre la partición de referencia y 100
     particiones obtenidas sobre remuestreos bootstrap.
  3. Comparación, con el k elegido (3 por defecto), de K-Means, jerárquico
     (Ward) y HDBSCAN.
  4. Kruskal-Wallis: ¿la tasa de abandono difiere entre los clústeres? Es lo
     que respalda que los "tres niveles" sean diferenciables (criterio b).
  5. Variante SIN riesgo_promedio: comprueba que la segmentación no sea
     circular respecto del propio modelo predictivo.

Las etiquetas se asignan por la tasa media de abandono de cada clúster
(ascendente), nunca por el número arbitrario que devuelve K-Means.

Uso:
    cd backend
    python -m ml.clustering_institucional --empresa UNEMI_PRUEBAS

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyodbc
from scipy.stats import kruskal
from sklearn.cluster import HDBSCAN, AgglomerativeClustering, KMeans
from sklearn.metrics import (
    adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score, silhouette_score,
)
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402

MODEL_VERSION = '2026.09.25-kmeans-validado'
SEMILLA = 20260909
MODELS_ROOT = Path(__file__).resolve().parent / 'models'
COLUMNAS = ['tasa_abandono_hist', 'promedio_hist', 'riesgo_promedio']

ETIQUETAS_POR_RIESGO_ASC = [
    'Bajo riesgo / alto rendimiento',
    'Estable',
    'Atencion prioritaria',
]


def conectar() -> pyodbc.Connection:
    """Abre la conexión administrativa a la base CHAT."""
    return conectar_admin('CHAT')


def construir_indicadores_por_carrera(conn: pyodbc.Connection, empresa: str) -> pd.DataFrame:
    """Calcula los indicadores de cada carrera de la institución.

    Por carrera: alumnos distintos (matricula_total), promedio histórico,
    tasa de abandono histórica y probabilidad media de abandono de sus
    alumnos calificados en fact_prediccion_abandono. Una carrera sin
    predicciones queda con riesgo_promedio = 0.
    """
    sql = """
        SELECT
            fm.carrera_id,
            dc.carrera,
            COUNT(DISTINCT fm.alumno_id) AS matricula_total,
            AVG(CAST(fm.promedio AS FLOAT)) AS promedio_hist,
            CAST(SUM(CASE WHEN fm.es_ultimo_periodo = 1 AND fm.estado_codigo = 'RETIRADO' THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(SUM(CASE WHEN fm.es_ultimo_periodo = 1 THEN 1 ELSE 0 END), 0) AS tasa_abandono_hist
        FROM dbo.fact_matriculas fm
        JOIN dbo.dim_carrera dc ON dc.carrera_id = fm.carrera_id
        WHERE fm.empresa_codigo = ?
        GROUP BY fm.carrera_id, dc.carrera
    """
    indicadores = pd.read_sql(sql, conn, params=[empresa])
    sql_riesgo = """
        SELECT fm.carrera_id, AVG(CAST(fp.probabilidad AS FLOAT)) AS riesgo_promedio
        FROM dbo.fact_prediccion_abandono fp
        JOIN dbo.fact_matriculas fm ON fm.fact_id = fp.fact_id_base
        WHERE fp.empresa_codigo = ?
        GROUP BY fm.carrera_id
    """
    riesgo = pd.read_sql(sql_riesgo, conn, params=[empresa])
    df = indicadores.merge(riesgo, on='carrera_id', how='left')
    df['riesgo_promedio'] = df['riesgo_promedio'].fillna(0.0)
    return df


def _escalar(df: pd.DataFrame, columnas: list[str]) -> np.ndarray:
    return StandardScaler().fit_transform(df[columnas])


def barrido_k(X: np.ndarray, k_max: int = 6) -> list[dict]:
    """Evalúa K-Means para k = 2..k_max (sin pasar de n - 1 unidades).

    Returns:
        Una entrada por k con silhouette, Davies-Bouldin y Calinski-Harabasz.
    """
    salida = []
    for k in range(2, min(k_max, len(X) - 1) + 1):
        etiquetas = KMeans(n_clusters=k, random_state=SEMILLA, n_init=10).fit_predict(X)
        salida.append({
            'k': k,
            'silhouette': round(float(silhouette_score(X, etiquetas)), 4),
            'davies_bouldin': round(float(davies_bouldin_score(X, etiquetas)), 4),
            'calinski_harabasz': round(float(calinski_harabasz_score(X, etiquetas)), 2),
        })
    return salida


def estabilidad_bootstrap(X: np.ndarray, k: int, n: int = 100) -> dict:
    """Mide la estabilidad de la partición con k clústeres por bootstrap.

    Ajusta K-Means sobre n remuestreos con reemplazo, asigna con cada modelo
    TODAS las unidades y compara esa asignación con la partición de
    referencia mediante el índice de Rand ajustado (ARI). Se omiten los
    remuestreos con menos puntos distintos que k.
    """
    referencia =KMeans(n_clusters=k, random_state=SEMILLA, n_init=10).fit_predict(X)
    rng = np.random.default_rng(SEMILLA)
    aris = []
    for _ in range(n):
        idx = rng.choice(len(X), size=len(X), replace=True)
        if len(np.unique(X[idx], axis=0)) < k:
            continue
        m = KMeans(n_clusters=k, random_state=SEMILLA, n_init=10).fit(X[idx])
        aris.append(adjusted_rand_score(referencia, m.predict(X)))
    return {'remuestreos': len(aris), 'ari_medio': round(float(np.mean(aris)), 4),
            'ari_desviacion': round(float(np.std(aris)), 4)}


def comparar_algoritmos(X: np.ndarray, k: int) -> dict:
    """Compara K-Means y jerárquico Ward (ambos con k clústeres) con HDBSCAN.

    HDBSCAN decide su propio número de clústeres y puede marcar puntos como
    ruido (etiqueta -1). La silhouette se calcula sin el ruido y queda en
    None si no hay al menos dos clústeres.
    """
    resultados = {}
    for nombre, etiquetas in (
        ('KMEANS', KMeans(n_clusters=k, random_state=SEMILLA, n_init=10).fit_predict(X)),
        ('JERARQUICO_WARD', AgglomerativeClustering(n_clusters=k, linkage='ward').fit_predict(X)),
        ('HDBSCAN', HDBSCAN(min_cluster_size=2).fit_predict(X)),
    ):
        validos = etiquetas >= 0
        n_clusters = len(set(etiquetas[validos]))
        sil = (silhouette_score(X[validos], etiquetas[validos])
               if n_clusters >= 2 and validos.sum() > n_clusters else None)
        resultados[nombre] = {'n_clusters': int(n_clusters), 'ruido': int((~validos).sum()),
                              'silhouette': None if sil is None else round(float(sil), 4)}
    return resultados


def clusterizar(df: pd.DataFrame, k: int = 3, columnas: list[str] | None = None) -> pd.DataFrame:
    """Asigna cada carrera a un clúster K-Means y le pone su etiqueta de riesgo.

    Las columnas se estandarizan antes del ajuste y k se recorta al número de
    carreras. Los clústeres se ordenan por su tasa media de abandono y
    reciben, en ese orden, las etiquetas de ETIQUETAS_POR_RIESGO_ASC.

    Returns:
        Copia de df con las columnas cluster_id y cluster_label.
    """
    columnas = columnas or COLUMNAS
    X = _escalar(df, columnas)
    k_efectivo = min(k, len(df))
    df = df.copy()
    df['cluster_id'] = KMeans(n_clusters=k_efectivo, random_state=SEMILLA, n_init=10).fit_predict(X)
    orden = df.groupby('cluster_id')['tasa_abandono_hist'].mean().sort_values().index.tolist()
    df['cluster_label'] = df['cluster_id'].map(dict(zip(orden, ETIQUETAS_POR_RIESGO_ASC[:len(orden)])))
    return df


def validar(df: pd.DataFrame, k: int) -> dict:
    """Reúne la validación completa de la segmentación con k clústeres.

    Incluye el barrido de k, la estabilidad bootstrap, la comparación de
    algoritmos, la prueba de Kruskal-Wallis de la tasa de abandono entre
    clústeres, el ARI frente a la variante sin riesgo_promedio y el tamaño y
    la tasa media de abandono de cada clúster.
    """
    X = _escalar(df, COLUMNAS)
    final = clusterizar(df, k)
    grupos = [g['tasa_abandono_hist'].values for _, g in final.groupby('cluster_id')]
    kw = kruskal(*grupos) if len(grupos) >= 2 and all(len(g) >= 1 for g in grupos) else None
    sin_riesgo = clusterizar(df, k, ['tasa_abandono_hist', 'promedio_hist'])
    return {
        'n_unidades': int(len(df)),
        'k': k,
        'barrido_k': barrido_k(X),
        'estabilidad_bootstrap': estabilidad_bootstrap(X, k),
        'comparacion_algoritmos': comparar_algoritmos(X, k),
        'kruskal_wallis_tasa_abandono': None if kw is None else {
            'estadistico_H': round(float(kw.statistic), 4), 'p_valor': round(float(kw.pvalue), 6)},
        'coincidencia_sin_riesgo_promedio_ari': round(float(adjusted_rand_score(final['cluster_id'], sin_riesgo['cluster_id'])), 4),
        'tamano_clusters': final['cluster_label'].value_counts().to_dict(),
        'tasa_media_por_cluster': {k2: round(float(v), 4) for k2, v in
                                   final.groupby('cluster_label')['tasa_abandono_hist'].mean().items()},
    }


def main() -> int:
    """Segmenta las carreras de la institución y guarda el resultado.

    Recarga la asignación en fact_cluster_carrera y las métricas de
    validación (silhouette, ARI, p de Kruskal-Wallis) en
    fact_evaluacion_modelo, y escribe metricas_clustering.json en
    ml/models/<EMPRESA>/. Con menos de 3 carreras no segmenta.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--empresa', default='UNEMI_PRUEBAS')
    parser.add_argument('--k', type=int, default=3)
    args = parser.parse_args()
    empresa = args.empresa.strip().upper()

    conn = conectar()
    print(f"Construyendo indicadores por carrera para '{empresa}' ...")
    df = construir_indicadores_por_carrera(conn, empresa)
    print(f"  {len(df)} carreras/módulos con datos.")
    if len(df) < 3:
        print("Se necesitan al menos 3 unidades académicas para segmentar.")
        conn.close()
        return 0

    validacion = validar(df, args.k)
    final = clusterizar(df, k=args.k)
    print(final[['carrera', 'matricula_total', 'tasa_abandono_hist', 'promedio_hist', 'riesgo_promedio', 'cluster_label']]
          .to_string(index=False))
    sil_k = next((b['silhouette'] for b in validacion['barrido_k'] if b['k'] == args.k), None)
    print(f"  silhouette(k={args.k}) = {sil_k}; estabilidad ARI = {validacion['estabilidad_bootstrap']['ari_medio']}; "
          f"Kruskal-Wallis = {validacion['kruskal_wallis_tasa_abandono']}")

    cur = conn.cursor()
    cur.execute("DELETE FROM dbo.fact_cluster_carrera WHERE empresa_codigo = ?", empresa)
    cur.executemany("""
        INSERT INTO dbo.fact_cluster_carrera
            (empresa_codigo, carrera_id, cluster_id, cluster_label, matricula_total,
             tasa_abandono_hist, promedio_hist, riesgo_promedio, modelo_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(empresa, int(r.carrera_id), int(r.cluster_id), r.cluster_label, int(r.matricula_total),
           round(float(r.tasa_abandono_hist), 4), round(float(r.promedio_hist), 2),
           round(float(r.riesgo_promedio), 4), MODEL_VERSION) for r in final.itertuples()])

    metricas = [('SILHOUETTE', sil_k, None),
                ('ESTABILIDAD_ARI', validacion['estabilidad_bootstrap']['ari_medio'],
                 validacion['estabilidad_bootstrap']['ari_desviacion'])]
    if validacion['kruskal_wallis_tasa_abandono']:
        metricas.append(('KRUSKAL_WALLIS_P', validacion['kruskal_wallis_tasa_abandono']['p_valor'], None))
    cur.execute("DELETE FROM dbo.fact_evaluacion_modelo WHERE empresa_codigo = ? AND componente = 'CLUSTERING'", empresa)
    cur.executemany("""INSERT INTO dbo.fact_evaluacion_modelo
        (empresa_codigo, componente, modelo, esquema_validacion, metrica, valor, desviacion, es_modelo_final, modelo_version)
        VALUES (?, 'CLUSTERING', ?, 'VALIDACION_INTERNA', ?, ?, ?, 1, ?)""",
        [(empresa, f'KMEANS_K{args.k}', m, v, d, MODEL_VERSION) for m, v, d in metricas if v is not None])
    conn.commit()
    conn.close()

    destino = MODELS_ROOT / empresa
    destino.mkdir(parents=True, exist_ok=True)
    (destino / 'metricas_clustering.json').write_text(
        json.dumps({'empresa': empresa, 'modelo_version': MODEL_VERSION, **validacion,
                    'asignacion': final[['carrera', 'cluster_label', 'tasa_abandono_hist', 'promedio_hist',
                                         'riesgo_promedio']].round(4).to_dict('records')},
                   indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    print(f"Guardados {len(final)} clústeres y la validación en {destino / 'metricas_clustering.json'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
