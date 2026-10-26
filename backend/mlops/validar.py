# -*- coding: utf-8 -*-
"""
Monitoreo de una institución: calidad de los datos (Great Expectations) y
deriva de las variables de entrada (Evidently), con registro en MLflow.

Se ejecuta después de calificar (paso «mlops» del pipeline) y cada vez que
se cargue un nuevo corte de datos:

    cd backend
    python -m mlops.validar --institucion UNEMI_PRUEBAS
    python -m mlops.validar --institucion OULAD_UK

Escribe en ml/modelos/<INSTITUCION>/:
    calidad_datos.json      expectativas evaluadas y si los datos son aptos para entrenar
    deriva.json             resumen de la deriva por variable
    deriva_evidently.html   informe interactivo de Evidently (no se versiona)

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.caracteristicas import construir_panel, matriz  # noqa: E402
from mlops.calidad_datos import validar as validar_calidad  # noqa: E402
from mlops.deriva import informe_deriva  # noqa: E402

RAIZ_MODELOS = Path(__file__).resolve().parent.parent / 'ml' / 'modelos'


def monitorear(hist: pd.DataFrame, institucion: str, registrar=print) -> tuple[dict, dict | None]:
    """Calidad de datos y deriva a partir de la trayectoria leída del almacén (sin escribir en la base)."""
    destino = RAIZ_MODELOS / institucion
    destino.mkdir(parents=True, exist_ok=True)
    calidad = validar_calidad(hist, institucion)
    (destino / 'calidad_datos.json').write_text(json.dumps(calidad, indent=2, ensure_ascii=False, default=str),
                                               encoding='utf-8')
    registrar(f"  Calidad de datos ({calidad['motor']}): {calidad['cumplidas']}/{calidad['evaluadas']} expectativas; "
              f"apto para entrenar: {'sí' if calidad['apto_para_entrenar'] else 'NO'}")
    for e in calidad['expectativas']:
        if not e['cumple']:
            registrar(f"    {'CRÍTICA' if e['critica'] else 'aviso'}: {e['descripcion']} ({e.get('porcentaje_no_cumple')} %)")

    ruta_modelo = destino / 'modelo_abandono.joblib'
    if not ruta_modelo.exists():
        registrar('  Sin modelo entrenado: se omite la deriva.')
        return calidad, None
    paquete = joblib.load(ruta_modelo)
    panel = construir_panel(hist)
    columnas = paquete['columnas']
    activos = panel[panel['para_calificar'] == 1]
    historicos = panel[panel['y'].notna()]
    # Comparación justa: la referencia se toma en los mismos cortes de evaluación en que están hoy
    # los estudiantes que se califican (al inicio del periodo hay menos actividad que al final).
    if 'corte' in panel and activos['corte'].notna().any():
        historicos = historicos[historicos['corte'].isin(activos['corte'].unique())]
    columnas_deriva = [c for c in columnas if c != 'corte']
    referencia = matriz(historicos, columnas_deriva)
    actual = matriz(activos, columnas_deriva)
    importancia = {}
    ruta_metricas = destino / 'metricas.json'
    if ruta_metricas.exists():
        m = json.loads(ruta_metricas.read_text(encoding='utf-8'))
        importancia = {i['variable']: i['media'] for i in m.get('importancia_permutacion', [])}
    deriva = informe_deriva(referencia, actual, institucion, destino / 'deriva_evidently.html', importancia)
    (destino / 'deriva.json').write_text(json.dumps(deriva, indent=2, ensure_ascii=False, default=str),
                                         encoding='utf-8')
    registrar(f"  Deriva ({deriva['motor']}): {deriva['variables_con_deriva']} de {len(deriva['variables'])} variables; "
              f"importantes con deriva: {deriva['importantes_con_deriva'] or 'ninguna'}")
    return calidad, deriva


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--institucion', required=True)
    args = parser.parse_args()
    institucion = args.institucion.strip().upper()
    from core.db import conectar_admin
    from ml.datos import leer_historial
    from mlops.registro_mlflow import registrar_monitoreo
    conn = conectar_admin()
    print(f"Monitoreo de '{institucion}' ...")
    hist = leer_historial(conn, institucion)
    conn.close()
    calidad, deriva = monitorear(hist, institucion)
    registrar_monitoreo(institucion, RAIZ_MODELOS / institucion, calidad, deriva)
    return 0 if calidad['apto_para_entrenar'] else 2


if __name__ == '__main__':
    sys.exit(main())
