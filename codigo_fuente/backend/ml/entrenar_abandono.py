# -*- coding: utf-8 -*-
"""
Entrenamiento del modelo de predicción de abandono de una institución.

Entrena el modelo de UNA institución sobre el panel alumno-periodo (ver
ml/features_abandono.py): "con lo que se sabe del alumno hasta el periodo t,
¿abandonará en t+1?".

Un modelo por institución (--empresa), guardado en ml/models/<EMPRESA>/: los
datos de dos instituciones nunca se mezclan en un mismo entrenamiento
(coherente con el aislamiento del sistema y con Kovor et al., 2026).

Validación (Objetivo específico 3), en este orden y sin reutilizar datos de
prueba para decidir nada:

  1. Corte TEMPORAL: las filas del panel se ordenan por fecha del periodo t;
     el 25 % más reciente queda reservado como prueba final. Todo lo que
     sigue (ajuste, comparación, umbral) usa solo el 75 % anterior.
  2. Ajuste de hiperparámetros del Random Forest con RandomizedSearchCV y
     validación cruzada StratifiedGroupKFold (5 pliegues) agrupada por
     ALUMNO: un mismo estudiante nunca queda a la vez en entrenamiento y en
     prueba (en un panel, esa fuga inflaría las métricas).
  3. Comparación, con los MISMOS pliegues, de:
       - RF_CLASS_WEIGHT  Random Forest con ponderación de clases.
       - RF_SMOTE         Random Forest con SMOTE aplicado SOLO a los
                          pliegues de entrenamiento (imblearn.Pipeline),
                          como en Villar & Andrade (2024).
       - LOGISTICA        regresión logística (la técnica de Núñez-Naranjo,
                          2024), línea base interpretable.
       - GRADIENT_BOOST   HistGradientBoosting, representante del boosting
                          (XGBoost en Carballo-Mendívil et al., 2025).
     El modelo final es la variante de Random Forest con mayor ROC-AUC
     medio (desempate por PR-AUC): es la técnica que declara el documento,
     por su balance entre desempeño e interpretabilidad (Duro et al., 2026).
     LOGISTICA y GRADIENT_BOOST son líneas base: si alguna supera al RF
     elegido en más de 0,01 de ROC-AUC medio, queda registrado como
     advertencia.
  4. Umbral operativo: sobre las predicciones fuera de pliegue, el mayor
     umbral que alcanza el recall objetivo (por defecto 0,80). La
     metodología prioriza no dejar pasar abandonos (recall).
  5. Prueba temporal: el modelo elegido, entrenado con el 75 % anterior, se
     evalúa UNA vez sobre el 25 % reservado. Importancia por permutación
     sobre ese mismo conjunto (Dube & Verster, 2024: la importancia por
     impureza se sesga con clases desbalanceadas).
  6. Modelo final: se reentrena con todas las filas etiquetadas y se guarda
     junto con su umbral. Las métricas se escriben en metrics.json y en
     CHAT.dbo.fact_evaluacion_modelo (consultables por el panel y el chat);
     las probabilidades de CV y de la prueba temporal quedan en CSV para
     ml/reporte_validacion.py.

Uso:
    cd backend
    python -m ml.entrenar_abandono --empresa UNEMI_PRUEBAS
    python -m ml.entrenar_abandono --empresa OULAD_UK

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyodbc
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as PipelineImb
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, confusion_matrix, f1_score, precision_recall_curve,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402
from ml.features_abandono import (  # noqa: E402
    construir_panel, informe_atipicos, matriz_X,
)

MODELS_ROOT = Path(__file__).resolve().parent / 'models'
MODEL_VERSION = '2026.09.25-panel-t1'
SEMILLA = 20260909
N_JOBS = -1  # todos los núcleos

# El espacio de búsqueda incluye árboles sin límite de profundidad
# (max_depth=None): la búsqueda decide, no se fija a mano.
ESPACIO_HIPERPARAMETROS = {
    'n_estimators': [150, 250, 300, 400, 500],
    'max_depth': [4, 6, 8, 10, 12, None],
    'min_samples_leaf': [1, 2, 5, 10, 20],
    'min_samples_split': [2, 5, 10, 20],
    'max_features': ['sqrt', 'log2', None],
}


def conectar() -> pyodbc.Connection:
    """Abre la conexión administrativa a la base CHAT."""
    return conectar_admin('CHAT')


def _r(x) -> float | None:
    """Redondea a 4 decimales; devuelve None si el valor falta o es NaN (JSON válido)."""
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


def metricas(y_true, proba, umbral: float) -> dict:
    """Calcula las métricas de clasificación de unas probabilidades con un umbral dado.

    Returns:
        n, positivos, prevalencia, umbral, ROC-AUC y PR-AUC (None si y_true
        tiene una sola clase), recall, precisión, F1 y matriz de confusión
        [[VN, FP], [FN, VP]].
    """
    y_true = np.asarray(y_true).astype(int)
    pred = (np.asarray(proba) >= umbral).astype(int)
    dos_clases = len(set(y_true)) > 1
    return {
        'n': int(len(y_true)),
        'positivos': int(y_true.sum()),
        'prevalencia': _r(y_true.mean()),
        'umbral': _r(umbral),
        'roc_auc': _r(roc_auc_score(y_true, proba)) if dos_clases else None,
        'pr_auc': _r(average_precision_score(y_true, proba)) if dos_clases else None,
        'recall': _r(recall_score(y_true, pred, zero_division=0)),
        'precision': _r(precision_score(y_true, pred, zero_division=0)),
        'f1': _r(f1_score(y_true, pred, zero_division=0)),
        'matriz_confusion': confusion_matrix(y_true, pred, labels=[0, 1]).tolist(),
    }


def umbral_para_recall(y_true, proba, recall_objetivo: float) -> float:
    """Devuelve el MAYOR umbral cuyo recall sigue siendo >= recall_objetivo.

    Subir el umbral reduce falsos positivos, así que se busca la mejor
    precisión posible sin bajar del recall exigido. Si ningún umbral lo
    alcanza, devuelve el menor umbral de la curva precisión-recall.
    """
    precision, recall, umbrales = precision_recall_curve(y_true, proba)
    validos = [u for u, r in zip(umbrales, recall[:-1]) if r >= recall_objetivo]
    return float(max(validos)) if validos else float(umbrales.min())


def candidatos(params_rf: dict) -> dict:
    """Construye, sin entrenar, los cuatro modelos que se comparan.

    Las dos variantes de Random Forest usan los hiperparámetros elegidos por
    la búsqueda. RF_SMOTE va dentro de un Pipeline de imblearn para que SMOTE
    se aplique solo al ajustar, es decir, solo a los datos de entrenamiento
    de cada pliegue y nunca a los de prueba.
    """
    return {
        'RF_CLASS_WEIGHT': RandomForestClassifier(class_weight='balanced', random_state=SEMILLA,
                                                  n_jobs=N_JOBS, **params_rf),
        'RF_SMOTE': PipelineImb([
            ('smote', SMOTE(random_state=SEMILLA)),
            ('rf', RandomForestClassifier(random_state=SEMILLA, n_jobs=N_JOBS, **params_rf)),
        ]),
        'LOGISTICA': make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', max_iter=2000)),
        'GRADIENT_BOOST': HistGradientBoostingClassifier(class_weight='balanced', random_state=SEMILLA),
    }


def evaluar_cv(nombre, modelo, X, y, grupos, cv) -> tuple[dict, np.ndarray]:
    """Evalúa un modelo con validación cruzada agrupada por alumno.

    Con los mismos pliegues para todos los modelos, calcula por pliegue
    ROC-AUC, PR-AUC, y recall y precisión con umbral 0,5.

    Returns:
        (resumen con la lista por pliegue, la media y la desviación de cada
        métrica; probabilidades fuera de pliegue, que sirven para elegir el
        umbral operativo sin tocar la prueba temporal).
    """
    por_pliegue = {'roc_auc': [], 'pr_auc': [], 'recall_05': [], 'precision_05': []}
    oof = np.zeros(len(y))
    for tr, te in cv.split(X, y, grupos):
        m = clone(modelo)
        m.fit(X.iloc[tr], y.iloc[tr])
        p = m.predict_proba(X.iloc[te])[:, 1]
        oof[te] = p
        por_pliegue['roc_auc'].append(roc_auc_score(y.iloc[te], p))
        por_pliegue['pr_auc'].append(average_precision_score(y.iloc[te], p))
        por_pliegue['recall_05'].append(recall_score(y.iloc[te], p >= 0.5, zero_division=0))
        por_pliegue['precision_05'].append(precision_score(y.iloc[te], p >= 0.5, zero_division=0))
    resumen = {k: {'pliegues': [round(float(v), 4) for v in vs],
                   'media': round(float(np.mean(vs)), 4), 'desviacion': round(float(np.std(vs)), 4)}
               for k, vs in por_pliegue.items()}
    print(f"    {nombre:16s} ROC-AUC {resumen['roc_auc']['media']:.4f} ± {resumen['roc_auc']['desviacion']:.4f} | "
          f"PR-AUC {resumen['pr_auc']['media']:.4f} ± {resumen['pr_auc']['desviacion']:.4f}")
    return resumen, oof


def guardar_en_warehouse(conn, empresa: str, metrics: dict) -> int:
    """Reemplaza en fact_evaluacion_modelo las métricas de predicción de la institución.

    Guarda el ROC-AUC y el PR-AUC medios de CV de cada modelo comparado
    (CV_GRUPOS_5), las métricas de la prueba temporal en el umbral operativo
    y el propio umbral (TEMPORAL). No toca las métricas de otros esquemas,
    como la evaluación prospectiva.

    Returns:
        Número de filas insertadas.
    """
    filas = []
    for nombre, res in metrics['comparacion_cv'].items():
        final = int(nombre == metrics['modelo_final'])
        for met, clave in (('ROC_AUC', 'roc_auc'), ('PR_AUC', 'pr_auc')):
            filas.append((empresa, 'PREDICCION', nombre, 'CV_GRUPOS_5', met,
                          res[clave]['media'], res[clave]['desviacion'], final, MODEL_VERSION))
    t = metrics['validacion_temporal']['umbral_operativo']
    for met in ('roc_auc', 'pr_auc', 'recall', 'precision', 'f1'):
        if t.get(met) is not None:
            filas.append((empresa, 'PREDICCION', metrics['modelo_final'], 'TEMPORAL', met.upper(),
                          t[met], None, 1, MODEL_VERSION))
    filas.append((empresa, 'PREDICCION', metrics['modelo_final'], 'TEMPORAL', 'UMBRAL_OPERATIVO',
                  metrics['umbral_operativo'], None, 1, MODEL_VERSION))
    cur = conn.cursor()
    cur.execute("DELETE FROM dbo.fact_evaluacion_modelo WHERE empresa_codigo = ? AND componente = 'PREDICCION'"
                " AND esquema_validacion IN ('CV_GRUPOS_5', 'TEMPORAL')", empresa)
    cur.executemany("""INSERT INTO dbo.fact_evaluacion_modelo
        (empresa_codigo, componente, modelo, esquema_validacion, metrica, valor, desviacion, es_modelo_final, modelo_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", filas)
    conn.commit()
    return len(filas)


def main() -> int:
    """Ejecuta el entrenamiento y la validación completos de la institución.

    Returns:
        0 si termina; 1 si el panel tiene menos de 20 abandonos etiquetados.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--empresa', default='UNEMI_PRUEBAS')
    parser.add_argument('--recall-objetivo', type=float, default=0.80)
    parser.add_argument('--n-iter', type=int, default=25, help='Combinaciones de RandomizedSearchCV')
    args = parser.parse_args()
    empresa = args.empresa.strip().upper()
    inicio = time.time()

    conn = conectar()
    print(f"Construyendo el panel alumno-periodo de '{empresa}' ...")
    panel = construir_panel(conn, empresa)
    etiquetado = panel[panel['y'].notna()].reset_index(drop=True)
    etiquetado['y'] = etiquetado['y'].astype(int)
    print(f"  {len(panel)} filas alumno-periodo; {len(etiquetado)} con periodo siguiente conocido; "
          f"{int(etiquetado['y'].sum())} abandonos al periodo siguiente ({etiquetado['y'].mean():.2%}).")
    if etiquetado['y'].sum() < 20:
        print("Muy pocos casos positivos para entrenar de forma confiable. Abortando.")
        return 1

    atipicos = informe_atipicos(etiquetado)

    # ── 1. Corte temporal: el 25 % más reciente queda reservado ───────────
    fechas = pd.to_datetime(etiquetado['fecha'])
    corte = fechas.sort_values().iloc[int(len(fechas) * 0.75)]
    es_prueba = fechas >= corte
    train, test = etiquetado[~es_prueba].reset_index(drop=True), etiquetado[es_prueba].reset_index(drop=True)
    X_train, columnas_dummy = matriz_X(train)
    X_test, _ = matriz_X(test, columnas_dummy)
    y_train, y_test = train['y'], test['y']
    grupos = train['alumno_id']
    print(f"  Corte temporal en {corte.date()}: entrenamiento {len(train)} filas, prueba {len(test)} filas.")

    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEMILLA)

    # ── 2. Ajuste de hiperparámetros (solo con el 75 % anterior) ──────────
    print(f"  RandomizedSearchCV ({args.n_iter} combinaciones, 5 pliegues agrupados por alumno) ...")
    busqueda = RandomizedSearchCV(
        RandomForestClassifier(class_weight='balanced', random_state=SEMILLA, n_jobs=N_JOBS),
        ESPACIO_HIPERPARAMETROS, n_iter=args.n_iter, scoring='roc_auc', cv=cv,
        random_state=SEMILLA, n_jobs=1,
    )
    busqueda.fit(X_train, y_train, groups=grupos)
    params_rf = busqueda.best_params_
    print(f"    Mejores hiperparámetros: {params_rf}")

    # ── 3. Comparación con los mismos pliegues ───────────────────────────
    print("  Comparación de modelos (mismos 5 pliegues):")
    MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    comparacion, oofs = {}, {}
    for nombre, modelo in candidatos(params_rf).items():
        comparacion[nombre], oofs[nombre] = evaluar_cv(nombre, modelo, X_train, y_train, grupos, cv)

    rf_variantes = ['RF_CLASS_WEIGHT', 'RF_SMOTE']
    final = max(rf_variantes, key=lambda n: (comparacion[n]['roc_auc']['media'], comparacion[n]['pr_auc']['media']))
    mejor_rf = comparacion[final]['roc_auc']['media']
    advertencias = [
        f"{n} supera al Random Forest elegido en ROC-AUC medio de CV "
        f"({comparacion[n]['roc_auc']['media']:.4f} vs {mejor_rf:.4f})."
        for n in ('LOGISTICA', 'GRADIENT_BOOST') if comparacion[n]['roc_auc']['media'] > mejor_rf + 0.01
    ]
    print(f"  Modelo final: {final}" + (f"  ADVERTENCIA: {advertencias}" if advertencias else ''))

    # ── 4. Umbral operativo por recall objetivo (fuera de pliegue) ───────
    umbral = umbral_para_recall(y_train, oofs[final], args.recall_objetivo)
    print(f"  Umbral operativo para recall >= {args.recall_objetivo:.2f}: {umbral:.4f}")

    # ── 5. Prueba temporal (una sola vez) ────────────────────────────────
    modelo_temporal = candidatos(params_rf)[final]
    modelo_temporal.fit(X_train, y_train)
    proba_test = modelo_temporal.predict_proba(X_test)[:, 1]
    temporal = {
        'corte': str(corte.date()),
        'umbral_operativo': metricas(y_test, proba_test, umbral),
        'umbral_0_5': metricas(y_test, proba_test, 0.5),
    }
    print(f"  Prueba temporal: {temporal['umbral_operativo']}")
    perm = permutation_importance(modelo_temporal, X_test, y_test, scoring='average_precision',
                                  n_repeats=5, random_state=SEMILLA, n_jobs=1)
    importancia = sorted(
        ({'variable': c, 'media': round(float(m), 4), 'desviacion': round(float(s), 4)}
         for c, m, s in zip(X_test.columns, perm.importances_mean, perm.importances_std)),
        key=lambda d: -d['media'],
    )

    # ── 6. Modelo final con todas las filas etiquetadas ──────────────────
    X_todo, _ = matriz_X(etiquetado, columnas_dummy)
    modelo_final = candidatos(params_rf)[final]
    modelo_final.fit(X_todo, etiquetado['y'])

    destino = MODELS_ROOT / empresa
    destino.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        'modelo': modelo_final,
        'nombre_modelo': final,
        'columnas_dummy': columnas_dummy,
        'feature_columns_final': list(X_todo.columns),
        'umbral_operativo': umbral,
        'version': MODEL_VERSION,
        'empresa': empresa,
    }, destino / 'abandono_model.joblib')
    pd.DataFrame({'y': y_train, 'proba_oof': oofs[final]}).to_csv(destino / 'predicciones_cv.csv', index=False)
    pd.DataFrame({'y': y_test, 'proba': proba_test, 'fecha': test['fecha'].astype(str)}).to_csv(
        destino / 'predicciones_temporal.csv', index=False)

    metrics = {
        'empresa': empresa,
        'modelo_version': MODEL_VERSION,
        'unidad_de_analisis': 'alumno-periodo (predicción del periodo siguiente)',
        'panel': {'filas': int(len(panel)), 'etiquetadas': int(len(etiquetado)),
                  'positivos': int(etiquetado['y'].sum()), 'prevalencia': _r(etiquetado['y'].mean()),
                  'para_calificar': int(panel['para_calificar'].sum())},
        'atipicos_iqr': atipicos,
        'hiperparametros_rf': params_rf,
        'comparacion_cv': comparacion,
        'modelo_final': final,
        'advertencias': advertencias,
        'recall_objetivo': args.recall_objetivo,
        'umbral_operativo': round(umbral, 4),
        'validacion_temporal': temporal,
        'importancia_permutacion': importancia,
        'segundos': round(time.time() - inicio, 1),
    }
    (destino / 'metrics.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8')
    n = guardar_en_warehouse(conn, empresa, metrics)
    conn.close()
    print(f"Modelo y métricas guardados en {destino} ({n} métricas en fact_evaluacion_modelo). "
          f"Tiempo: {metrics['segundos']} s")
    return 0


if __name__ == '__main__':
    sys.exit(main())
