# -*- coding: utf-8 -*-
"""
Calificación del riesgo de abandono de los estudiantes activos.

Con el modelo de SU institución, estima para cada estudiante con matrícula
vigente la probabilidad (calibrada) de abandonar en el próximo periodo, la
clasifica en ALTO, MEDIO o BAJO según los umbrales del entrenamiento, calcula
su percentil dentro de la institución y explica las tres razones principales
(SHAP). Guarda todo en fact_prediccion_abandono, que el panel y la consulta
conversacional leen por la misma vista (VIS_PREDICCION_ABANDONO).

También vigila la deriva de los datos: compara la distribución actual de las
variables más importantes con la del entrenamiento (índice de estabilidad
poblacional, PSI) y lo publica en fact_evaluacion_modelo.

Uso:
    cd backend
    python -m ml.calificar --institucion UNEMI_PRUEBAS

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.caracteristicas import construir_panel, estado_simulacion, matriz  # noqa: E402
from ml.explicacion import contribuciones, detalle, factores  # noqa: E402

RAIZ_MODELOS = Path(__file__).resolve().parent / 'modelos'


def categoria(p: float, umbral_alto: float, umbral_medio: float) -> str:
    """ALTO si supera el umbral alto; MEDIO si supera el medio; BAJO en otro caso."""
    if p >= umbral_alto:
        return 'ALTO'
    if p >= umbral_medio:
        return 'MEDIO'
    return 'BAJO'


def psi(referencia: dict, actual: pd.Series) -> float | None:
    """Índice de estabilidad poblacional entre la distribución de referencia y la actual."""
    s = actual.dropna()
    if s.empty:
        return None
    cortes = np.asarray(referencia['cortes'], dtype=float)
    cortes[0], cortes[-1] = -np.inf, np.inf
    actual_p = np.histogram(s, bins=cortes)[0] / len(s)
    esperado = np.asarray(referencia['proporciones'])
    a, b = np.clip(actual_p, 1e-4, None), np.clip(esperado, 1e-4, None)
    return float(np.sum((a - b) * np.log(a / b)))


def cargar_paquete(institucion: str) -> dict:
    ruta = RAIZ_MODELOS / institucion / 'modelo_abandono.joblib'
    if not ruta.exists():
        raise FileNotFoundError(f'No existe {ruta}. Entrene primero: python -m ml.entrenar --institucion {institucion}')
    return joblib.load(ruta)


def calificar_panel(panel: pd.DataFrame, paquete: dict) -> pd.DataFrame:
    """Califica las filas `para_calificar` del panel. Función pura (sin base de datos)."""
    activos = panel[panel['para_calificar'] == 1].copy()
    if activos.empty:
        return activos
    X = matriz(activos, paquete['columnas'])
    crudo = paquete['modelo'].predict_proba(X)[:, 1]
    prob = paquete['calibrador'].predict(crudo)
    activos['probabilidad'] = np.round(prob, 4)
    activos['riesgo_categoria'] = [categoria(p, paquete['umbral_alto'], paquete['umbral_medio']) for p in prob]
    activos['percentil_riesgo'] = np.round(pd.Series(crudo).rank(pct=True).to_numpy() * 100, 2)
    contrib = contribuciones(paquete['modelo'], X)
    activos['factores'] = [factores(contrib[i], X.iloc[i]) for i in range(len(X))]
    activos['explicacion'] = [detalle(contrib[i], X.iloc[i]) for i in range(len(X))]
    estados = estado_simulacion(panel, activos)
    activos['caracteristicas'] = [
        {**{c: (None if pd.isna(X.iat[i, j]) else round(float(X.iat[i, j]), 6)) for j, c in enumerate(X.columns)},
         '_estado': estados[i]} for i in range(len(X))]
    return activos


def monitoreo(panel_activos: pd.DataFrame, paquete: dict, importancia: list[dict], top: int = 10) -> list[dict]:
    """PSI de las variables más importantes entre el entrenamiento y la población calificada."""
    X = matriz(panel_activos, paquete['columnas'])
    salida = []
    for item in importancia[:top]:
        v = item['variable']
        if v in paquete['referencia_psi'] and v in X:
            valor = psi(paquete['referencia_psi'][v], X[v])
            if valor is not None:
                estado = 'ESTABLE' if valor < 0.1 else 'MODERADO' if valor < 0.25 else 'DERIVA'
                salida.append({'variable': v, 'psi': round(valor, 4), 'estado': estado})
    return salida


def guardar(conn, institucion: str, activos: pd.DataFrame, paquete: dict, psi_vars: list[dict]) -> int:
    cur = conn.cursor()
    cur.execute('DELETE FROM dbo.fact_prediccion_abandono WHERE institucion_codigo = ?', institucion)
    conn.commit()
    filas = [(institucion, int(r.alumno_id), int(r.matricula_id), float(r.probabilidad), r.riesgo_categoria,
              round(float(paquete['umbral_alto']), 4), round(float(paquete['umbral_medio']), 4),
              float(r.percentil_riesgo), r.factores[0], r.factores[1], r.factores[2],
              json.dumps(r.explicacion, ensure_ascii=False), json.dumps(r.caracteristicas, ensure_ascii=False),
              f"{paquete['version']}-{paquete['nombre_modelo']}")
             for r in activos.itertuples()]
    cur.fast_executemany = False  # NVARCHAR(MAX) con fast_executemany consume mucha memoria
    cur.executemany("""INSERT INTO dbo.fact_prediccion_abandono
        (institucion_codigo, alumno_id, matricula_id_base, probabilidad, riesgo_categoria, umbral_alto, umbral_medio,
         percentil_riesgo, factor_1, factor_2, factor_3, explicacion_json, caracteristicas_json, modelo_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", filas)
    cur.execute("DELETE FROM dbo.fact_evaluacion_modelo WHERE institucion_codigo = ? AND esquema_validacion = 'MONITOREO'",
                institucion)
    for p in psi_vars:
        cur.execute("""INSERT INTO dbo.fact_evaluacion_modelo (institucion_codigo, componente, modelo, esquema_validacion,
                       metrica, valor, grupo, es_modelo_final, modelo_version)
                       VALUES (?, 'PREDICCION', ?, 'MONITOREO', 'PSI', ?, ?, 1, ?)""",
                    institucion, paquete['nombre_modelo'], p['psi'], p['variable'], paquete['version'])
    conn.commit()
    return len(filas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--institucion', required=True)
    args = parser.parse_args()
    institucion = args.institucion.strip().upper()

    from core.db import conectar_admin
    from ml.datos import leer_historial
    paquete = cargar_paquete(institucion)
    conn = conectar_admin()
    panel = construir_panel(leer_historial(conn, institucion))
    activos = calificar_panel(panel, paquete)
    if activos.empty:
        print('No hay estudiantes activos para calificar.')
        return 0
    metricas_path = RAIZ_MODELOS / institucion / 'metricas.json'
    importancia = json.loads(metricas_path.read_text(encoding='utf-8')).get('importancia_permutacion', [])
    psi_vars = monitoreo(activos, paquete, importancia)
    n = guardar(conn, institucion, activos, paquete, psi_vars)
    conn.close()
    resumen = activos['riesgo_categoria'].value_counts().to_dict()
    (RAIZ_MODELOS / institucion / 'monitoreo.json').write_text(
        json.dumps({'calificados': n, 'distribucion': resumen, 'psi': psi_vars}, indent=2, ensure_ascii=False),
        encoding='utf-8')
    print(f'{n} estudiantes calificados en {institucion}: {resumen}. PSI: {psi_vars[:3]} ...')
    return 0


if __name__ == '__main__':
    sys.exit(main())
