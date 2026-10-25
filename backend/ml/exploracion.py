# -*- coding: utf-8 -*-
"""
Comprensión de los datos (fase 2 de CRISP-DM): perfil, calidad y figuras exploratorias.

Para cada institución lee la trayectoria del almacén, construye el panel
estudiante-periodo (la misma función que usa el entrenamiento) y guarda:

  - ml/modelos/<INST>/exploracion.json: registros, estudiantes, periodos,
    faltantes por columna opcional, valores fuera de rango y tasa de abandono
    en t+1 por grupos de las variables clave.
  - documentacion/figuras/<INST>_exploracion.png: tasa de abandono en t+1
    según tres variables, dibujada a 15 cm con texto a 10 pt.

Uso:
    cd backend
    python -m ml.exploracion --institucion UNEMI_PRUEBAS

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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.caracteristicas import COLUMNAS_OPCIONALES_FUENTE, construir_panel  # noqa: E402

RAIZ_MODELOS = Path(__file__).resolve().parent / 'modelos'
FIGURAS = Path(__file__).resolve().parents[2] / 'documentacion' / 'figuras'
PULG = 1 / 2.54

# Variables clave por institución: (columna del panel, título, cortes, etiquetas).
CLAVES = {
    'promedio_t': ('Promedio', [-0.1, 5, 6, 7, 8, 10.01], ['< 5', '5-6', '6-7', '7-8', '≥ 8']),
    'asistencia_t': ('Asistencia (%)', [-0.1, 50, 70, 85, 100.01], ['< 50', '50-70', '70-85', '≥ 85']),
    'numero_matricula': ('N.º de matrícula', [0, 1.5, 2.5, 9], ['1.ª', '2.ª', '3.ª']),
    'dias_sin_actividad': ('Días sin actividad', [-0.1, 3, 7, 14, 400], ['0-3', '4-7', '8-14', '> 14']),
    'pct_entregadas': ('Entregas (%)', [-0.01, 0.5, 0.8, 0.999, 1.01], ['< 50', '50-80', '80-99', '100']),
}
FIGURA_POR_INST = {'UNEMI_PRUEBAS': ['promedio_t', 'asistencia_t', 'numero_matricula'],
                   'OULAD_UK': ['promedio_t', 'dias_sin_actividad', 'pct_entregadas']}


def perfil(hist: pd.DataFrame, panel: pd.DataFrame) -> dict:
    etiquetado = panel[panel['y'].notna()]
    faltantes = {c: round(float(hist[c].isna().mean()), 4) for c in COLUMNAS_OPCIONALES_FUENTE if c in hist}
    fuera = {
        'promedio fuera de 0-10': int(((hist['promedio'] < 0) | (hist['promedio'] > 10)).sum()),
        'asistencia fuera de 0-100': int(((hist['asistencia_pct'] < 0) | (hist['asistencia_pct'] > 100)).sum()),
    }
    grupos = {}
    for col, (titulo, cortes, etiquetas) in CLAVES.items():
        if col not in etiquetado or etiquetado[col].notna().mean() < 0.5:
            continue
        g = pd.cut(etiquetado[col].astype(float), cortes, labels=etiquetas)
        t = etiquetado.groupby(g, observed=False)['y'].agg(['mean', 'size'])
        grupos[col] = {'titulo': titulo, 'grupos': [{'grupo': str(k), 'tasa': round(float(v['mean']), 4) if v['size'] else None,
                                                     'n': int(v['size'])} for k, v in t.iterrows()]}
    por_periodo = (etiquetado.groupby('periodo_codigo')['y'].agg(['mean', 'size']).reset_index()
                   .rename(columns={'mean': 'tasa', 'size': 'n'}))
    return {
        'registros': int(len(hist)), 'estudiantes': int(hist['alumno_id'].nunique()),
        'periodos': int(hist['periodo_codigo'].nunique()),
        'carreras': int(hist['carrera'].nunique()) if 'carrera' in hist else None,
        'estados_finales': {str(k): int(v) for k, v in hist[hist['es_ultimo_periodo'] == 1]['estado_codigo']
                            .value_counts().items()},
        'faltantes_opcionales': faltantes, 'fuera_de_rango': fuera,
        'etiquetados': int(len(etiquetado)), 'positivos': int(etiquetado['y'].sum()),
        'tasa_por_periodo': [{'periodo': r.periodo_codigo, 'tasa': round(float(r.tasa), 4), 'n': int(r.n)}
                             for r in por_periodo.itertuples()],
        'tasa_por_grupo': grupos,
    }


def figura(inst: str, datos: dict) -> Path | None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 10,
                         'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#CBD5E1'})
    cols = [c for c in FIGURA_POR_INST.get(inst, []) if c in datos['tasa_por_grupo']]
    if not cols:
        return None
    fig, ejes = plt.subplots(1, len(cols), figsize=(15 * PULG, 6.8 * PULG), sharey=True)
    for ax, col in zip(np.atleast_1d(ejes), cols):
        g = datos['tasa_por_grupo'][col]
        etiquetas = [x['grupo'] for x in g['grupos']]
        tasas = [100 * (x['tasa'] or 0) for x in g['grupos']]
        ax.bar(etiquetas, tasas, color='#0B5C7E', width=0.65)
        ax.set_title(g['titulo'], fontweight='bold')
        ax.grid(axis='y', color='#E2E8F0')
        ax.set_axisbelow(True)
        ax.tick_params(axis='x', rotation=35)
    np.atleast_1d(ejes)[0].set_ylabel('Abandono en t+1 (%)')
    for ax in np.atleast_1d(ejes):
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _p: f'{v:.10g}'.replace('.', ',')))
    fig.tight_layout()
    FIGURAS.mkdir(parents=True, exist_ok=True)
    ruta = FIGURAS / f'{inst}_exploracion.png'
    fig.savefig(ruta, dpi=200, facecolor='white')
    plt.close(fig)
    return ruta


def main() -> int:
    from core.db import conectar_admin
    from ml.datos import leer_historial
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--institucion', required=True)
    inst = ap.parse_args().institucion.strip().upper()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        conn = conectar_admin()
        hist = leer_historial(conn, inst)
        conn.close()
    panel = construir_panel(hist)
    datos = perfil(hist, panel)
    destino = RAIZ_MODELOS / inst
    destino.mkdir(parents=True, exist_ok=True)
    (destino / 'exploracion.json').write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'{inst}: {datos["registros"]} registros; figura {figura(inst, datos)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
