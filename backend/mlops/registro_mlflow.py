# -*- coding: utf-8 -*-
"""
Registro de cada entrenamiento en MLflow (trazabilidad de experimentos).

Cada vez que se entrena el modelo de una institución queda una ejecución
(«run») en el experimento «abandono-<INSTITUCION>» con:

  - parámetros: algoritmo elegido, hiperparámetros, umbrales, recall objetivo,
    grupos de variables y tamaño del panel;
  - métricas: ROC-AUC y PR-AUC de la validación cruzada de los cuatro
    candidatos, métricas de la prueba temporal, ROC-AUC y recall por periodo y
    resumen de la validación con origen móvil;
  - artefactos: metricas.json, monitoreo, deriva, calidad de datos y el
    paquete del modelo (joblib).

Así se puede responder, para cualquier modelo en producción, con qué datos,
qué parámetros y qué resultados se entrenó, y comparar reentrenamientos.

Almacén: SQLite local en backend/datos_locales/mlflow/ (no se versiona). Se
cambia con la variable MLFLOW_TRACKING_URI (por ejemplo, un servidor MLflow de
la institución). requirements.txt instala mlflow-skinny, que registra pero no trae
la interfaz web; para verla se instala el paquete completo y se abre con:

    cd backend
    pip install mlflow
    mlflow ui --backend-store-uri sqlite:///datos_locales/mlflow/mlflow.db

Si MLflow no está instalado, el registro se omite con un aviso.

Requerimientos que implementa: RF-13 (calidad del modelo), RNF-03 (trazabilidad).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
import os
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
DIR_MLFLOW = RAIZ_BACKEND / 'datos_locales' / 'mlflow'


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def parametros_y_metricas(metricas: dict) -> tuple[dict, dict]:
    """Aplana metricas.json en parámetros y métricas para MLflow (función pura, se prueba sin MLflow)."""
    final = metricas.get('modelo_final')
    params = {
        'institucion': metricas.get('institucion'), 'version': metricas.get('version'),
        'modelo_final': final, 'horizonte': metricas.get('horizonte'),
        'grupos_de_variables': ','.join(metricas.get('grupos_de_variables', [])),
        'n_variables': metricas.get('n_variables'),
        'umbral_medio': metricas.get('umbrales', {}).get('medio'),
        'umbral_alto': metricas.get('umbrales', {}).get('alto'),
        'recall_objetivo_medio': metricas.get('umbrales', {}).get('recall_objetivo_medio'),
        'recall_objetivo_alto': metricas.get('umbrales', {}).get('recall_objetivo_alto'),
        'periodos_prueba': ','.join(metricas.get('validacion_temporal', {}).get('periodos', [])),
    }
    for k, v in (metricas.get('panel') or {}).items():
        params[f'panel_{k}'] = v
    for k, v in (metricas.get('hiperparametros', {}).get(final, {}) or {}).items():
        params[f'hp_{k}'] = v
    params = {k: str(v)[:500] for k, v in params.items() if v is not None}

    met = {}
    for nombre, res in (metricas.get('comparacion_cv') or {}).items():
        for clave in ('roc_auc', 'pr_auc'):
            met[f'cv_{nombre.lower()}_{clave}'] = _num(res.get(clave, {}).get('media'))
    t = metricas.get('validacion_temporal') or {}
    for clave in ('roc_auc', 'pr_auc', 'brier_calibrado', 'captura_top_10', 'captura_top_20', 'prevalencia'):
        met[f'temporal_{clave}'] = _num(t.get(clave))
    for nivel in ('medio', 'alto'):
        for clave in ('recall', 'precision', 'tasa_alerta'):
            met[f'temporal_{clave}_{nivel}'] = _num((t.get(f'umbral_{nivel}') or {}).get(clave))
    for g in metricas.get('por_periodo', []):
        for clave in ('roc_auc', 'recall_medio'):
            met[f'periodo_{g["grupo"]}_{clave}'] = _num(g.get(clave))
    for clave, valor in ((metricas.get('origen_movil') or {}).get('resumen') or {}).items():
        met[f'origen_movil_{clave}'] = _num(valor)
    met['segundos_entrenamiento'] = _num(metricas.get('segundos'))
    limpio = {}
    for k, v in met.items():
        if v is None:
            continue
        # MLflow admite letras, números, guion bajo, guion, punto, espacio y barra en los nombres.
        limpio[''.join(c if c.isalnum() or c in '_-./ ' else '_' for c in k)] = v
    return params, limpio


def registrar_entrenamiento(institucion: str, destino: Path, metricas: dict, registrar=print) -> dict | None:
    """Crea la ejecución de MLflow del entrenamiento y deja un resumen en mlflow_registro.json."""
    try:
        os.environ.setdefault('MLFLOW_DISABLE_AGENT_HINT', '1')
        import mlflow
    except ImportError:
        registrar('  MLflow no está instalado: se omite el registro del experimento (pip install mlflow-skinny).')
        return None
    try:
        DIR_MLFLOW.mkdir(parents=True, exist_ok=True)
        uri = os.environ.get('MLFLOW_TRACKING_URI') or f'sqlite:///{(DIR_MLFLOW / "mlflow.db").as_posix()}'
        mlflow.set_tracking_uri(uri)
        nombre = f'abandono-{institucion}'
        experimento = mlflow.get_experiment_by_name(nombre)
        if experimento is None:
            id_exp = mlflow.create_experiment(nombre, artifact_location=(DIR_MLFLOW / 'artefactos' / institucion).as_uri())
        else:
            id_exp = experimento.experiment_id
        params, met = parametros_y_metricas(metricas)
        with mlflow.start_run(experiment_id=id_exp, run_name=f"{metricas.get('modelo_final')} v{metricas.get('version')}") as run:
            mlflow.set_tags({'institucion': institucion, 'modelo_final': metricas.get('modelo_final'),
                             'autores': 'Marlon David Pérez Almachi; Víctor Manuel Lluilema Pisco',
                             'proyecto': 'Prototipo de alerta temprana del abandono estudiantil (UNEMI)'})
            mlflow.log_params(params)
            mlflow.log_metrics(met)
            for archivo in ('metricas.json', 'monitoreo.json', 'deriva.json', 'calidad_datos.json',
                            'prospectiva.json', 'modelo_abandono.joblib'):
                ruta = Path(destino) / archivo
                if ruta.exists():
                    mlflow.log_artifact(str(ruta))
            resumen = {'experimento': nombre, 'experiment_id': id_exp, 'run_id': run.info.run_id,
                       'tracking_uri': 'sqlite:///datos_locales/mlflow/mlflow.db'
                       if 'MLFLOW_TRACKING_URI' not in os.environ else uri,
                       'parametros': len(params), 'metricas': len(met), 'fecha': metricas.get('fecha')}
        (Path(destino) / 'mlflow_registro.json').write_text(json.dumps(resumen, indent=2, ensure_ascii=False),
                                                            encoding='utf-8')
        registrar(f"  MLflow: ejecución {resumen['run_id'][:8]} en el experimento {nombre} "
                  f"({len(params)} parámetros, {len(met)} métricas).")
        return resumen
    except Exception as exc:  # noqa: BLE001 - el registro nunca debe impedir guardar el modelo
        registrar(f'  Aviso: no se pudo registrar el entrenamiento en MLflow ({exc}).')
        return None


def registrar_monitoreo(institucion: str, destino: Path, calidad: dict | None, deriva: dict | None,
                        registrar=print) -> str | None:
    """Registra en el mismo experimento una ejecución de monitoreo (calidad de datos y deriva)."""
    try:
        os.environ.setdefault('MLFLOW_DISABLE_AGENT_HINT', '1')
        import mlflow
    except ImportError:
        return None
    try:
        DIR_MLFLOW.mkdir(parents=True, exist_ok=True)
        mlflow.set_tracking_uri(os.environ.get('MLFLOW_TRACKING_URI') or f'sqlite:///{(DIR_MLFLOW / "mlflow.db").as_posix()}')
        nombre = f'abandono-{institucion}'
        experimento = mlflow.get_experiment_by_name(nombre)
        id_exp = (experimento.experiment_id if experimento else
                  mlflow.create_experiment(nombre, artifact_location=(DIR_MLFLOW / 'artefactos' / institucion).as_uri()))
        with mlflow.start_run(experiment_id=id_exp, run_name='monitoreo') as run:
            mlflow.set_tag('tipo', 'monitoreo')
            if calidad:
                mlflow.log_metrics({'calidad_porcentaje_cumplimiento': calidad['porcentaje_cumplimiento'],
                                    'calidad_apto_para_entrenar': float(calidad['apto_para_entrenar'])})
            if deriva:
                mlflow.log_metrics({'deriva_proporcion_variables': deriva['proporcion_con_deriva'],
                                    'deriva_variables': float(deriva['variables_con_deriva'])})
            for archivo in ('calidad_datos.json', 'deriva.json', 'deriva_evidently.html'):
                if (Path(destino) / archivo).exists():
                    mlflow.log_artifact(str(Path(destino) / archivo))
            return run.info.run_id
    except Exception as exc:  # noqa: BLE001
        registrar(f'  Aviso: no se pudo registrar el monitoreo en MLflow ({exc}).')
        return None
