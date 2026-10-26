# -*- coding: utf-8 -*-
"""
Figura del desempeño por periodo con origen móvil (ROC-AUC y recall del umbral medio), a 16 cm de
ancho y texto de 10 pt, leída de ml/modelos/<institución>/metricas.json.

Uso:
    python documentacion/generador_documentos/figuras_periodo.py

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
MODELOS = RAIZ / 'backend' / 'ml' / 'modelos'
SALIDA = RAIZ / 'documentacion' / 'figuras' / 'tf_desempeno_periodo.png'
AZUL, NARANJA, GRIS = '#1F4E79', '#E07B24', '#6B7785'


def _coma(x: float, d: int = 2) -> str:
    return f'{x:.{d}f}'.replace('.', ',')


def main() -> int:
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 10,
                         'axes.labelsize': 10, 'xtick.labelsize': 10, 'ytick.labelsize': 10, 'legend.fontsize': 10})
    fig, ejes = plt.subplots(1, 2, figsize=(16 / 2.54, 7.2 / 2.54), sharey=True)
    for eje, (inst, titulo) in zip(ejes, (('UNEMI_PRUEBAS', 'UNEMI (datos de prueba)'), ('OULAD_UK', 'OULAD (datos reales)'))):
        m = json.loads((MODELOS / inst / 'metricas.json').read_text(encoding='utf-8'))
        filas = [f for f in (m.get('origen_movil') or {}).get('periodos', []) if f.get('roc_auc') is not None]
        x = list(range(len(filas)))
        auc = [f['roc_auc'] for f in filas]
        rec = [f['recall_medio'] for f in filas]
        eje.plot(x, auc, '-o', color=AZUL, label='ROC-AUC', lw=1.8, ms=5)
        eje.plot(x, rec, '-s', color=NARANJA, label='Recall (umbral medio)', lw=1.8, ms=5)
        eje.axhline(0.70, ls='--', color=GRIS, lw=1)
        for xi, (a, r) in enumerate(zip(auc, rec)):   # la etiqueta del valor mayor va arriba y la del menor abajo
            arriba_a = a >= r
            eje.annotate(_coma(a), (xi, a), textcoords='offset points', xytext=(0, 6 if arriba_a else -15),
                         ha='center', color=AZUL)
            eje.annotate(_coma(r), (xi, r), textcoords='offset points', xytext=(0, -15 if arriba_a else 6),
                         ha='center', color=NARANJA)
        eje.text(-0.35, 0.69, 'mínimo por periodo: 0,70', ha='left', va='top', color=GRIS, fontsize=8)
        eje.set_xticks(x, [f['periodo'] for f in filas])
        eje.set_title(titulo)
        eje.set_xlabel('Periodo predicho')
        eje.set_ylim(0.4, 1.0)
        eje.set_xlim(-0.4, len(filas) - 0.6)
        eje.grid(axis='y', alpha=0.3)
        for lado in ('top', 'right'):
            eje.spines[lado].set_visible(False)
    ejes[0].set_ylabel('Valor')
    ejes[0].yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: _coma(v, 1)))
    manijas, etiquetas = ejes[0].get_legend_handles_labels()
    fig.legend(manijas, etiquetas, loc='lower center', ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SALIDA, dpi=300)
    print(SALIDA)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
