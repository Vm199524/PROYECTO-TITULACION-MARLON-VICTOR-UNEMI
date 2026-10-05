# -*- coding: utf-8 -*-
"""
Figuras de validación y evaluación prospectiva de los modelos.

Genera las figuras y la evaluación prospectiva a partir de los artefactos que
dejan entrenar_abandono.py, predecir_abandono.py y
clustering_institucional.py (NO reentrena nada: solo lee resultados).

Figuras (PNG en documentacion/figuras/, para el documento de titulación):
  <EMPRESA>_roc_pr.png           curvas ROC y precisión-recall (CV y temporal)
  <EMPRESA>_matriz_confusion.png matriz de confusión en el umbral operativo
  <EMPRESA>_importancia.png      importancia por permutación (prueba temporal)
  <EMPRESA>_comparacion_cv.png   ROC-AUC y PR-AUC por pliegue de cada modelo
  <EMPRESA>_clustering_k.png     silhouette y Davies-Bouldin según k

Evaluación PROSPECTIVA (solo OULAD_UK): la presentación 2014J se cargó
truncada "en curso" (scripts/seed_oulad.py). El modelo calificó a quienes
seguían activos al corte; aquí se compara esa calificación con lo que
REALMENTE ocurrió después (OULAD_PRUEBAS.dbo.verdad_futura, que nunca pasó
por el warehouse ni por el entrenamiento). Es la prueba más honesta posible:
predicción hecha antes, desenlace conocido después.

Uso:
    cd backend
    python -m ml.reporte_validacion --empresa OULAD_UK

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score, confusion_matrix, precision_recall_curve, precision_score,
    recall_score, roc_auc_score, roc_curve,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402

MODELS_ROOT = Path(__file__).resolve().parent / 'models'
FIGURAS = Path(__file__).resolve().parents[3] / 'documentacion' / 'figuras'
FIGURAS.mkdir(parents=True, exist_ok=True)
COLOR = {'cv': '#2563eb', 'temporal': '#dc2626', 'base': '#9ca3af'}
NOMBRE_MODELO = {'RF_CLASS_WEIGHT': 'RF + ponderación', 'RF_SMOTE': 'RF + SMOTE',
                 'LOGISTICA': 'Regresión logística', 'GRADIENT_BOOST': 'Gradient boosting'}


def _estilo(ax, titulo):
    ax.set_title(titulo, fontsize=11)
    ax.grid(alpha=0.25)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)


def figura_roc_pr(empresa: str, carpeta: Path) -> None:
    """Dibuja las curvas ROC y precisión-recall de la CV (fuera de pliegue) y de la prueba temporal."""
    cv =pd.read_csv(carpeta / 'predicciones_cv.csv')
    te = pd.read_csv(carpeta / 'predicciones_temporal.csv')
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    for nombre, y, p, c in (('Validación cruzada (fuera de pliegue)', cv['y'], cv['proba_oof'], COLOR['cv']),
                            ('Prueba temporal', te['y'], te['proba'], COLOR['temporal'])):
        fpr, tpr, _ = roc_curve(y, p)
        a1.plot(fpr, tpr, color=c, label=f"{nombre} (AUC {roc_auc_score(y, p):.3f})")
        pr, rc, _ = precision_recall_curve(y, p)
        a2.plot(rc, pr, color=c, label=f"{nombre} (AP {average_precision_score(y, p):.3f})")
    a1.plot([0, 1], [0, 1], ls='--', color=COLOR['base'])
    a2.axhline(te['y'].mean(), ls='--', color=COLOR['base'], label=f"Prevalencia {te['y'].mean():.3f}")
    a1.set_xlabel('Tasa de falsos positivos'); a1.set_ylabel('Tasa de verdaderos positivos (recall)')
    a2.set_xlabel('Recall'); a2.set_ylabel('Precisión')
    _estilo(a1, 'Curva ROC'); _estilo(a2, 'Curva precisión-recall')
    a1.legend(fontsize=8, loc='lower right'); a2.legend(fontsize=8, loc='lower left')
    fig.suptitle(f'{empresa}: abandono en el próximo periodo', fontsize=12)
    fig.tight_layout()
    fig.savefig(FIGURAS / f'{empresa}_roc_pr.png', dpi=160)
    plt.close(fig)


def figura_confusion(empresa: str, metrics: dict) -> None:
    """Dibuja la matriz de confusión de la prueba temporal en el umbral operativo."""
    m =np.array(metrics['validacion_temporal']['umbral_operativo']['matriz_confusion'])
    fig, ax = plt.subplots(figsize=(4.4, 3.8))
    ax.imshow(m, cmap='Blues')
    for (i, j), v in np.ndenumerate(m):
        ax.text(j, i, f'{v:,}'.replace(',', '.'), ha='center', va='center',
                color='white' if v > m.max() / 2 else 'black', fontsize=12)
    ax.set_xticks([0, 1], ['Continúa', 'Abandona']); ax.set_yticks([0, 1], ['Continúa', 'Abandona'])
    ax.set_xlabel('Predicción'); ax.set_ylabel('Real')
    ax.set_title(f"Prueba temporal (umbral {metrics['umbral_operativo']:.3f})", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGURAS / f'{empresa}_matriz_confusion.png', dpi=160)
    plt.close(fig)


def figura_importancia(empresa: str, metrics: dict) -> None:
    """Dibuja las 10 variables con mayor importancia por permutación positiva.

    No genera la figura si ninguna variable tiene importancia positiva.
    """
    imp =[d for d in metrics['importancia_permutacion'] if d['media'] > 0][:10][::-1]
    if not imp:
        return
    fig, ax = plt.subplots(figsize=(6.5, 0.4 * len(imp) + 1.2))
    ax.barh([d['variable'] for d in imp], [d['media'] for d in imp],
            xerr=[d['desviacion'] for d in imp], color=COLOR['cv'])
    ax.set_xlabel('Caída de la precisión promedio (PR-AUC) al permutar la variable')
    _estilo(ax, f'{empresa}: importancia por permutación')
    fig.tight_layout()
    fig.savefig(FIGURAS / f'{empresa}_importancia.png', dpi=160)
    plt.close(fig)


def figura_comparacion(empresa: str, metrics: dict) -> None:
    """Dibuja diagramas de caja del ROC-AUC y del PR-AUC por pliegue de cada modelo comparado."""
    comp =metrics['comparacion_cv']
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    for ax, clave, titulo in zip(axes, ('roc_auc', 'pr_auc'), ('ROC-AUC por pliegue', 'PR-AUC por pliegue')):
        datos = [comp[n][clave]['pliegues'] for n in comp]
        ax.boxplot(datos, tick_labels=[NOMBRE_MODELO.get(n, n) for n in comp])
        ax.tick_params(axis='x', labelsize=8)
        _estilo(ax, titulo)
    fig.suptitle(f'{empresa}: comparación de modelos (5 pliegues agrupados por alumno)', fontsize=11)
    fig.tight_layout()
    fig.savefig(FIGURAS / f'{empresa}_comparacion_cv.png', dpi=160)
    plt.close(fig)


def figura_clustering(empresa: str, carpeta: Path) -> None:
    """Dibuja silhouette y Davies-Bouldin según k; no hace nada si no existe metricas_clustering.json."""
    ruta =carpeta / 'metricas_clustering.json'
    if not ruta.exists():
        return
    b = json.loads(ruta.read_text(encoding='utf-8'))['barrido_k']
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.plot([x['k'] for x in b], [x['silhouette'] for x in b], marker='o', color=COLOR['cv'], label='Silhouette (↑)')
    ax2 = ax.twinx()
    ax2.plot([x['k'] for x in b], [x['davies_bouldin'] for x in b], marker='s', color=COLOR['temporal'],
             label='Davies-Bouldin (↓)')
    ax.set_xlabel('Número de clústeres k')
    _estilo(ax, f'{empresa}: calidad de la segmentación según k')
    fig.legend(loc='upper right', fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURAS / f'{empresa}_clustering_k.png', dpi=160)
    plt.close(fig)


def evaluacion_prospectiva_oulad(empresa: str) -> dict | None:
    """Compara las predicciones guardadas con lo que ocurrió después en OULAD.

    Cruza fact_prediccion_abandono con OULAD_PRUEBAS.dbo.verdad_futura y
    evalúa dos desenlaces: y_proximo (retiro en el bloque siguiente al
    calificado, que es el horizonte del modelo) e y_cualquier_momento
    (retiro en cualquier bloque posterior). Guarda las métricas de
    y_proximo en fact_evaluacion_modelo con el esquema PROSPECTIVA.

    Returns:
        Métricas de ambos desenlaces, o None si no hay predicciones.
    """
    conn = conectar_admin('CHAT')
    pred = pd.read_sql("""
        SELECT da.cedula, RIGHT(dc.carrera, 3) AS code_module, fm.semestre AS bloque_actual,
               CAST(fp.probabilidad AS FLOAT) AS probabilidad, CAST(fp.umbral_operativo AS FLOAT) AS umbral
        FROM dbo.fact_prediccion_abandono fp
        JOIN dbo.dim_alumno da ON da.alumno_id = fp.alumno_id
        JOIN dbo.fact_matriculas fm ON fm.fact_id = fp.fact_id_base
        JOIN dbo.dim_carrera dc ON dc.carrera_id = fm.carrera_id
        WHERE fp.empresa_codigo = ?
    """, conn, params=[empresa])
    conn.close()
    if pred.empty:
        return None
    conn = conectar_admin('OULAD_PRUEBAS')
    verdad = pd.read_sql("SELECT code_module, cedula, bloque_final_real, estado_final_real FROM dbo.verdad_futura", conn)
    conn.close()
    m = pred.merge(verdad, on=['cedula', 'code_module'], how='inner')
    retiro = m['estado_final_real'] == 'RETIRADO'
    m['y_proximo'] = (retiro & (m['bloque_final_real'] == m['bloque_actual'] + 1)).astype(int)
    m['y_cualquier_momento'] = (retiro & (m['bloque_final_real'] > m['bloque_actual'])).astype(int)
    umbral = float(m['umbral'].iloc[0])
    salida = {'calificados': int(len(m)), 'umbral': round(umbral, 4)}
    for clave in ('y_proximo', 'y_cualquier_momento'):
        y, p = m[clave], m['probabilidad']
        salida[clave] = {
            'positivos': int(y.sum()),
            'roc_auc': round(float(roc_auc_score(y, p)), 4),
            'pr_auc': round(float(average_precision_score(y, p)), 4),
            'recall': round(float(recall_score(y, p >= umbral, zero_division=0)), 4),
            'precision': round(float(precision_score(y, p >= umbral, zero_division=0)), 4),
            'matriz_confusion': confusion_matrix(y, p >= umbral, labels=[0, 1]).tolist(),
        }
    conn = conectar_admin('CHAT')
    cur = conn.cursor()
    cur.execute("DELETE FROM dbo.fact_evaluacion_modelo WHERE empresa_codigo = ? AND esquema_validacion = 'PROSPECTIVA'", empresa)
    cur.executemany("""INSERT INTO dbo.fact_evaluacion_modelo
        (empresa_codigo, componente, modelo, esquema_validacion, metrica, valor, desviacion, es_modelo_final, modelo_version)
        VALUES (?, 'PREDICCION', 'MODELO_FINAL', 'PROSPECTIVA', ?, ?, NULL, 1, 'prospectiva-2014J')""",
        [(empresa, k.upper(), v) for k, v in salida['y_proximo'].items() if k in ('roc_auc', 'pr_auc', 'recall', 'precision')])
    conn.commit()
    conn.close()
    return salida


def main() -> int:
    """Genera las figuras de la institución y, para OULAD_UK, agrega la evaluación prospectiva a metrics.json."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--empresa', default='UNEMI_PRUEBAS')
    args = parser.parse_args()
    empresa = args.empresa.strip().upper()
    carpeta =MODELS_ROOT / empresa
    metrics = json.loads((carpeta / 'metrics.json').read_text(encoding='utf-8'))
    FIGURAS.mkdir(parents=True, exist_ok=True)

    figura_roc_pr(empresa, carpeta)
    figura_confusion(empresa, metrics)
    figura_importancia(empresa, metrics)
    figura_comparacion(empresa, metrics)
    figura_clustering(empresa, carpeta)
    print(f"Figuras de {empresa} en {FIGURAS}")

    if empresa == 'OULAD_UK':
        prosp = evaluacion_prospectiva_oulad(empresa)
        if prosp:
            metrics['evaluacion_prospectiva'] = prosp
            (carpeta / 'metrics.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"Evaluación prospectiva: {json.dumps(prosp, ensure_ascii=False)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
