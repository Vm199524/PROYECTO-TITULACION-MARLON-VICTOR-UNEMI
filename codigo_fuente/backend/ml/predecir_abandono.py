# -*- coding: utf-8 -*-
"""
Calificación del riesgo de abandono de los alumnos activos.

Califica, con el modelo de SU institución (ml/models/<EMPRESA>/), el riesgo
de que cada alumno ACTIVO abandone en el PRÓXIMO periodo, usando sus datos
hasta el periodo más reciente (panel alumno-periodo, ver
ml/features_abandono.py). Guarda el resultado en
CHAT.dbo.fact_prediccion_abandono, que se lee por VIS_PREDICCION_ABANDONO
desde el panel (GET /api/ml/prediccion-abandono) y desde el chat NL2SQL.

Categorías de riesgo, derivadas del umbral operativo elegido en el
entrenamiento para el recall objetivo (no de cortes fijos arbitrarios):
    ALTO   probabilidad >= umbral
    MEDIO  probabilidad >= umbral / 2
    BAJO   el resto

Explicación por alumno (Khatun et al., 2025; Mustofa et al., 2025): para
los alumnos en riesgo ALTO o MEDIO se calculan los valores SHAP del Random
Forest y se guardan las tres variables que más empujan SU probabilidad hacia
el abandono, redactadas para una autoridad sin formación técnica.

Recarga completa por institución (DELETE + INSERT), mismo patrón que el ETL.

Uso:
    cd backend
    python -m ml.predecir_abandono --empresa UNEMI_PRUEBAS

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyodbc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402
from ml.features_abandono import construir_panel, describir_feature, matriz_X  # noqa: E402

MODELS_ROOT = Path(__file__).resolve().parent / 'models'


def categoria_riesgo(p: float, umbral: float) -> str:
    """Clasifica una probabilidad en ALTO (>= umbral), MEDIO (>= umbral / 2) o BAJO."""
    if p >= umbral:
        return 'ALTO'
    if p >= umbral / 2:
        return 'MEDIO'
    return 'BAJO'


def _formatear(nombre: str, valor: float) -> str:
    """Escribe el valor de una variable en unidades legibles (%, nota sobre 10, sí/no, dólares)."""
    if nombre.startswith(('asistencia',)):
        return f"{valor:+.1f} puntos" if nombre.endswith('delta') else f"{valor:.1f} %"
    if nombre.startswith('promedio'):
        return f"{valor:+.2f}" if nombre.endswith('delta') else f"{valor:.2f} / 10"
    if nombre == 'pct_periodos_con_mora':
        return f"{valor * 100:.0f} % de sus periodos"
    if nombre == 'en_mora_t':
        return 'sí' if valor >= 0.5 else 'no'
    if nombre == 'saldo_pendiente_t':
        return f"${valor:,.2f}"
    if nombre in ('periodo', 'n_periodos_cursados', 'beca_porcentaje'):
        return f"{valor:.0f}" + (' %' if nombre == 'beca_porcentaje' else '')
    return f"{valor:.0f}"


def factores_shap(modelo, X: pd.DataFrame, top: int = 3) -> list[list[str]]:
    """Devuelve, por fila, las `top` variables que más empujan hacia el abandono.

    Usa TreeExplainer sobre el Random Forest (el paso 'rf' si el modelo es el
    Pipeline con SMOTE) y toma solo contribuciones SHAP POSITIVAS, redactadas
    en lenguaje natural. Si una fila tiene menos de `top`, completa con None.
    """
    import shap

    rf = modelo.named_steps['rf'] if hasattr(modelo, 'named_steps') else modelo
    valores = np.asarray(shap.TreeExplainer(rf).shap_values(X))
    if valores.ndim == 3:  # (filas, variables, clases)
        valores = valores[:, :, 1]
    salida = []
    for i in range(len(X)):
        orden = np.argsort(-valores[i])
        frases = [
            f"{describir_feature(X.columns[j])}: {_formatear(X.columns[j], float(X.iat[i, j]))}"
            for j in orden[:top] if valores[i, j] > 0
        ]
        salida.append(frases + [None] * (top - len(frases)))
    return salida


def main() -> int:
    """Califica a los alumnos activos y recarga sus predicciones en fact_prediccion_abandono.

    Returns:
        0 si termina (también si no hay alumnos activos); 1 si la
        institución no tiene un modelo entrenado.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--empresa', default='UNEMI_PRUEBAS')
    args = parser.parse_args()
    empresa = args.empresa.strip().upper()

    ruta =MODELS_ROOT / empresa / 'abandono_model.joblib'
    if not ruta.exists():
        print(f"No existe {ruta}. Corre primero: python -m ml.entrenar_abandono --empresa {empresa}")
        return 1
    paquete = joblib.load(ruta)
    modelo, umbral, version = paquete['modelo'], float(paquete['umbral_operativo']), paquete['version']

    conn: pyodbc.Connection = conectar_admin('CHAT')
    print(f"Construyendo el panel de '{empresa}' ...")
    panel = construir_panel(conn, empresa)
    activos = panel[panel['para_calificar'] == 1].reset_index(drop=True)
    print(f"  {len(activos)} trayectorias ACTIVAS a calificar (riesgo en el próximo periodo).")
    if activos.empty:
        conn.close()
        return 0

    X, _ = matriz_X(activos, paquete['columnas_dummy'])
    X = X[paquete['feature_columns_final']]
    activos['probabilidad'] = modelo.predict_proba(X)[:, 1]
    activos['riesgo_categoria'] = [categoria_riesgo(p, umbral) for p in activos['probabilidad']]

    en_riesgo = activos.index[activos['riesgo_categoria'] != 'BAJO']
    factores = [[None, None, None]] * len(activos)
    if len(en_riesgo):
        print(f"  Explicando con SHAP a {len(en_riesgo)} alumnos en riesgo ALTO/MEDIO ...")
        explic = factores_shap(modelo, X.loc[en_riesgo])
        factores = list(factores)
        for idx, f in zip(en_riesgo, explic):
            factores[idx] = f

    cur = conn.cursor()
    cur.execute("DELETE FROM dbo.fact_prediccion_abandono WHERE empresa_codigo = ?", empresa)
    conn.commit()
    filas = [
        (empresa, int(r.alumno_id), int(r.fact_id), round(float(r.probabilidad), 4), round(umbral, 4),
         r.riesgo_categoria, f[0], f[1], f[2], version)
        for r, f in zip(activos.itertuples(), factores)
    ]
    cur.fast_executemany = True
    cur.executemany(
        """INSERT INTO dbo.fact_prediccion_abandono
               (empresa_codigo, alumno_id, fact_id_base, probabilidad, umbral_operativo,
                riesgo_categoria, factor_1, factor_2, factor_3, modelo_version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        filas,
    )
    conn.commit()
    conn.close()
    print(f"Guardadas {len(filas)} predicciones. Distribución: {activos['riesgo_categoria'].value_counts().to_dict()}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
