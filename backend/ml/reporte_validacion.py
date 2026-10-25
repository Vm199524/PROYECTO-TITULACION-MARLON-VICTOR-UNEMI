# -*- coding: utf-8 -*-
"""
Figuras de validación y evaluación prospectiva de una institución.

Genera, en documentacion/figuras/, las gráficas que usan el documento de
titulación y el README a partir de los archivos que dejó el entrenamiento:

  - curvas ROC y precisión-recall (validación cruzada y prueba temporal);
  - curva de ganancia acumulada: qué proporción de los abandonos se detecta
    contactando al 10 %, 20 %... de mayor riesgo (lo que necesita bienestar);
  - diagrama de calibración (probabilidad predicha frente a observada);
  - comparación de algoritmos por pliegue, importancia por permutación,
    matriz de confusión, equidad por subgrupo y selección de k.

Para OULAD_UK agrega la evaluación PROSPECTIVA: compara las predicciones
hechas sobre la presentación «en curso» (2014J, corte 3) con lo que de verdad
ocurrió después (dbo.verdad_futura), que el modelo nunca vio.

Uso:
    cd backend
    python -m ml.reporte_validacion --institucion OULAD_UK

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (average_precision_score, confusion_matrix, precision_recall_curve,  # noqa: E402
                             precision_score, recall_score, roc_auc_score, roc_curve)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.caracteristicas import describir  # noqa: E402

RAIZ_MODELOS = Path(__file__).resolve().parent / 'modelos'
FIGURAS = Path(__file__).resolve().parents[2] / 'documentacion' / 'figuras'
AZUL, NARANJA, GRIS, ROJO, AMBAR, VERDE = '#002E45', '#FF6900', '#94A3B8', '#DC2626', '#D97706', '#059669'
NOMBRES = {'RF_PONDERADO': 'RF ponderado', 'RF_SMOTE': 'RF + SMOTE', 'LOGISTICA': 'Reg. logística', 'LIGHTGBM': 'LightGBM'}
# Cada figura se dibuja al ancho con que se inserta en el documento (ANCHO_CM), de modo
# que todo su texto mida 10 pt reales impreso.
ANCHO_CM = {'roc_pr': 15, 'ganancia': 14, 'calibracion': 12.5, 'comparacion_cv': 15, 'importancia': 15,
            'matriz_confusion': 10.5, 'equidad': 15, 'segmentacion_k': 14}
PULG = 1 / 2.54
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 10, 'axes.titleweight': 'bold',
                     'legend.fontsize': 10, 'xtick.labelsize': 10, 'ytick.labelsize': 10, 'axes.labelsize': 10,
                     'axes.edgecolor': '#CBD5E1', 'axes.labelcolor': '#334155', 'xtick.color': '#475569',
                     'ytick.color': '#475569', 'axes.spines.top': False, 'axes.spines.right': False})


def _coma_decimal(fig) -> None:
    """Marcas numéricas con coma decimal, como en el resto del documento."""
    from matplotlib.ticker import FuncFormatter, ScalarFormatter
    for ax in fig.axes:
        for eje in (ax.xaxis, ax.yaxis):
            if isinstance(eje.get_major_formatter(), ScalarFormatter):
                eje.set_major_formatter(FuncFormatter(lambda v, _p: f'{v:.10g}'.replace('.', ',')))


def _guardar(fig, nombre: str) -> None:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    _coma_decimal(fig)
    fig.tight_layout()
    fig.savefig(FIGURAS / nombre, dpi=200, facecolor='white')
    plt.close(fig)


def _rejilla(ax) -> None:
    ax.grid(axis='y', color='#E2E8F0', linewidth=0.8)
    ax.set_axisbelow(True)


def figura_roc_pr(inst: str, cv: pd.DataFrame, te: pd.DataFrame) -> None:
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(15 * PULG, 13 * PULG))
    series = [('Prueba temporal', te['y'], te['probabilidad'], NARANJA)]
    if cv is not None:
        series.insert(0, ('Validación cruzada', cv['y'], cv['probabilidad'], AZUL))
    for nombre, y, p, color in series:
        fpr, tpr, _ = roc_curve(y, p)
        a1.plot(fpr, tpr, color=color, lw=2, label=f'{nombre} (AUC {roc_auc_score(y, p):.3f})'.replace('.', ','))
        pr, rc, _ = precision_recall_curve(y, p)
        a2.plot(rc, pr, color=color, lw=2, label=f'{nombre} (AP {average_precision_score(y, p):.3f})'.replace('.', ','))
    a1.plot([0, 1], [0, 1], ls='--', color=GRIS, lw=1)
    a2.axhline(te['y'].mean(), ls='--', color=GRIS, lw=1, label=f"Azar (prevalencia {te['y'].mean():.3f})".replace('.', ','))
    a1.set(xlabel='Tasa de falsos positivos', ylabel='Recall (abandonos detectados)', title='Curva ROC')
    a2.set(xlabel='Recall (abandonos detectados)', ylabel='Precisión', title='Curva precisión-recall')
    for a in (a1, a2):
        _rejilla(a)
        a.legend(frameon=False)
    _guardar(fig, f'{inst}_roc_pr.png')


def figura_ganancia(inst: str, te: pd.DataFrame) -> None:
    orden = te.sort_values('probabilidad', ascending=False)['y'].to_numpy()
    x = np.arange(1, len(orden) + 1) / len(orden) * 100
    y = np.cumsum(orden) / max(orden.sum(), 1) * 100
    fig, ax = plt.subplots(figsize=(14 * PULG, 9.5 * PULG))
    ax.plot(x, y, color=NARANJA, lw=2.2, label='Modelo')
    ax.plot([0, 100], [0, 100], ls='--', color=GRIS, label='Sin modelo (al azar)')
    for corte in (10, 20, 30):
        i = int(len(x) * corte / 100) - 1
        ax.scatter([x[i]], [y[i]], color=AZUL, zorder=3, s=18)
        ax.annotate(f'{y[i]:.0f} %', (x[i], y[i]), textcoords='offset points', xytext=(6, -13), color=AZUL)
    ax.set(xlabel='Estudiantes contactados, de mayor a menor riesgo (%)', ylabel='Abandonos detectados (%)',
           title='Ganancia acumulada en la prueba temporal', xlim=(0, 100), ylim=(0, 102))
    _rejilla(ax)
    ax.legend(frameon=False, loc='lower right')
    _guardar(fig, f'{inst}_ganancia.png')


def figura_calibracion(inst: str, metricas: dict, te: pd.DataFrame) -> None:
    curva = metricas['validacion_temporal']['curva_calibracion']
    fig, ax = plt.subplots(figsize=(12.5 * PULG, 10 * PULG))
    lim = max(max(c['predicha'] for c in curva), max(c['observada'] for c in curva)) * 1.08
    ax.plot([0, lim], [0, lim], ls='--', color=GRIS, label='Calibración perfecta')
    ax.plot([c['predicha'] for c in curva], [c['observada'] for c in curva], marker='o', color=AZUL, lw=2,
            label='Modelo calibrado (Platt)')
    ax.set(xlabel='Probabilidad predicha (media del decil)', ylabel='Abandono observado',
           title='Calibración en la prueba temporal', xlim=(0, lim), ylim=(0, lim))
    _rejilla(ax)
    ax.legend(frameon=False)
    _guardar(fig, f'{inst}_calibracion.png')


def figura_comparacion(inst: str, metricas: dict) -> None:
    comp = metricas['comparacion_cv']
    fig, axes = plt.subplots(1, 2, figsize=(15 * PULG, 8 * PULG))
    for ax, clave, titulo in zip(axes, ('roc_auc', 'pr_auc'), ('ROC-AUC por pliegue', 'PR-AUC por pliegue')):
        datos = [comp[n][clave]['pliegues'] for n in comp]
        caja = ax.boxplot(datos, tick_labels=[NOMBRES.get(n, n) for n in comp], patch_artist=True, widths=0.55)
        for parche, nombre in zip(caja['boxes'], comp):
            parche.set(facecolor=NARANJA if nombre == metricas['modelo_final'] else '#E2E8F0', edgecolor=AZUL)
        ax.set_title(titulo)
        ax.tick_params(axis='x', rotation=30)
        for t in ax.get_xticklabels():
            t.set_ha('right')
        _rejilla(ax)
    _guardar(fig, f'{inst}_comparacion_cv.png')


def figura_importancia(inst: str, metricas: dict) -> None:
    imp = [d for d in metricas['importancia_permutacion'] if (d['media'] or 0) > 0][:12][::-1]
    if not imp:
        return
    fig, ax = plt.subplots(figsize=(15 * PULG, (0.62 * len(imp) + 2.2) * PULG))
    ax.barh([describir(d['variable']) for d in imp], [d['media'] for d in imp], xerr=[d['desviacion'] for d in imp],
            color=AZUL, ecolor=GRIS, height=0.6)
    ax.set(xlabel='Caída del PR-AUC al permutarla')
    ax.grid(axis='x', color='#E2E8F0')
    _guardar(fig, f'{inst}_importancia.png')


def figura_confusion(inst: str, metricas: dict) -> None:
    t = metricas['validacion_temporal']['umbral_medio']
    m = np.array(t['matriz_confusion'])
    fig, ax = plt.subplots(figsize=(10.5 * PULG, 9 * PULG))
    ax.imshow(m, cmap='Blues')
    for (i, j), v in np.ndenumerate(m):
        ax.text(j, i, f'{v:,}'.replace(',', '.'), ha='center', va='center', fontsize=11,
                color='white' if v > m.max() / 2 else '#0F172A')
    ax.set_xticks([0, 1], ['Continúa', 'Abandona'])
    ax.set_yticks([0, 1], ['Continúa', 'Abandona'])
    ax.set(xlabel='Alerta del modelo (ALTO o MEDIO)', ylabel='Desenlace real')
    ax.spines[:].set_visible(False)
    _guardar(fig, f'{inst}_matriz_confusion.png')


def figura_equidad(inst: str, metricas: dict) -> None:
    eq = metricas.get('equidad') or []
    if not eq:
        return
    grupos = {'F': 'mujeres', 'M': 'hombres'}
    etiquetas = [f"{'Género' if e['variable'] == 'genero' else e['variable'].split('_')[0].capitalize()}: "
                 f"{grupos.get(e['grupo'], str(e['grupo']).lower())}" for e in eq]
    x = np.arange(len(eq))
    fig, ax = plt.subplots(figsize=(15 * PULG, 8.5 * PULG))
    ax.bar(x - 0.2, [e['recall'] for e in eq], width=0.4, color=AZUL, label='Recall (abandonos detectados)')
    ax.bar(x + 0.2, [e['roc_auc'] for e in eq], width=0.4, color=NARANJA, label='ROC-AUC')
    ax.set_xticks(x, [e.replace(': ', ':\n') for e in etiquetas])
    ax.set(ylim=(0, 1.25))
    _rejilla(ax)
    ax.legend(frameon=False, loc='upper center', ncol=2)
    _guardar(fig, f'{inst}_equidad.png')


def figura_segmentacion(inst: str, seg: dict | None) -> None:
    if not seg or not seg.get('barrido_k'):
        return
    b = seg['barrido_k']
    fig, ax = plt.subplots(figsize=(14 * PULG, 9.5 * PULG))
    ax.plot([x['k'] for x in b], [x['silhouette'] for x in b], marker='o', color=AZUL, label='Silhouette (mayor, mejor)')
    ax2 = ax.twinx()
    ax2.plot([x['k'] for x in b], [x['davies_bouldin'] for x in b], marker='s', color=NARANJA,
             label='Davies-Bouldin (menor, mejor)')
    ax.axvline(seg.get('k', 3), color=GRIS, ls=':', lw=1)
    ax.set(xlabel='Número de segmentos (k)', ylabel='Silhouette')
    ax2.set_ylabel('Davies-Bouldin')
    ax2.spines['right'].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper center', bbox_to_anchor=(0.5, -0.28), ncol=2, frameon=False)
    ax.set_xticks([x['k'] for x in b])
    _rejilla(ax)
    _guardar(fig, f'{inst}_segmentacion_k.png')


def prospectiva_oulad(inst: str, paquete: dict) -> dict | None:
    """Compara las predicciones vigentes de OULAD con su desenlace real posterior."""
    from core.db import conectar_admin
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        conn = conectar_admin()
        pred = pd.read_sql("""SELECT da.cedula, RIGHT(dc.carrera, 3) AS code_module, fm.corte,
                                     CAST(fp.probabilidad AS FLOAT) AS probabilidad
                              FROM dbo.fact_prediccion_abandono fp
                              JOIN dbo.dim_alumno da ON da.alumno_id = fp.alumno_id
                              JOIN dbo.fact_matriculas fm ON fm.matricula_id = fp.matricula_id_base
                              JOIN dbo.dim_carrera dc ON dc.carrera_id = fm.carrera_id
                              WHERE fp.institucion_codigo = ?""", conn, params=[inst])
        conn.close()
        if pred.empty:
            return None
        conn = conectar_admin('OULAD_PRUEBAS')
        verdad = pd.read_sql('SELECT code_module, cedula, corte_final_real, estado_final_real FROM dbo.verdad_futura', conn)
        conn.close()
    m = pred.merge(verdad, on=['cedula', 'code_module'], how='inner')
    retiro = m['estado_final_real'] == 'RETIRADO'
    m['y_siguiente'] = (retiro & (m['corte_final_real'] == m['corte'] + 1)).astype(int)
    m['y_resto'] = (retiro & (m['corte_final_real'] > m['corte'])).astype(int)
    salida = {'calificados': int(len(m)), 'presentacion': '2014J', 'umbral_medio': round(paquete['umbral_medio'], 4)}
    for clave in ('y_siguiente', 'y_resto'):
        y, p = m[clave], m['probabilidad']
        alerta = p >= paquete['umbral_medio']
        salida[clave] = {'positivos': int(y.sum()), 'roc_auc': round(float(roc_auc_score(y, p)), 4),
                         'pr_auc': round(float(average_precision_score(y, p)), 4),
                         'recall': round(float(recall_score(y, alerta, zero_division=0)), 4),
                         'precision': round(float(precision_score(y, alerta, zero_division=0)), 4),
                         'matriz_confusion': confusion_matrix(y, alerta, labels=[0, 1]).tolist()}
    conn = conectar_admin()
    cur = conn.cursor()
    cur.execute("DELETE FROM dbo.fact_evaluacion_modelo WHERE institucion_codigo = ? AND esquema_validacion = 'PROSPECTIVA'", inst)
    cur.executemany("""INSERT INTO dbo.fact_evaluacion_modelo (institucion_codigo, componente, modelo, esquema_validacion,
                       metrica, valor, es_modelo_final, modelo_version) VALUES (?, 'PREDICCION', ?, 'PROSPECTIVA', ?, ?, 1, ?)""",
                    [(inst, paquete['nombre_modelo'], k.upper(), v, paquete['version'])
                     for k, v in salida['y_siguiente'].items() if k in ('roc_auc', 'pr_auc', 'recall', 'precision')])
    conn.commit()
    conn.close()
    return salida


def generar_figuras(inst: str) -> list[str]:
    carpeta = RAIZ_MODELOS / inst
    metricas = json.loads((carpeta / 'metricas.json').read_text(encoding='utf-8'))
    te = pd.read_csv(carpeta / 'predicciones_prueba_temporal.csv')
    cv_ruta = carpeta / 'predicciones_validacion_cruzada.csv'
    figura_roc_pr(inst, pd.read_csv(cv_ruta) if cv_ruta.exists() else None, te)
    figura_ganancia(inst, te)
    figura_calibracion(inst, metricas, te)
    figura_comparacion(inst, metricas)
    figura_importancia(inst, metricas)
    figura_confusion(inst, metricas)
    figura_equidad(inst, metricas)
    seg = carpeta / 'segmentacion.json'
    figura_segmentacion(inst, json.loads(seg.read_text(encoding='utf-8')) if seg.exists() else None)
    return sorted(p.name for p in FIGURAS.glob(f'{inst}_*.png'))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--institucion', required=True)
    args = parser.parse_args()
    inst = args.institucion.strip().upper()
    figuras = generar_figuras(inst)
    print(f'Figuras en {FIGURAS}: {figuras}')
    if inst == 'OULAD_UK':
        from ml.calificar import cargar_paquete
        resultado = prospectiva_oulad(inst, cargar_paquete(inst))
        if resultado:
            (RAIZ_MODELOS / inst / 'prospectiva.json').write_text(json.dumps(resultado, indent=2, ensure_ascii=False),
                                                                  encoding='utf-8')
            print('Evaluación prospectiva (2014J):', {k: resultado[k] for k in ('calificados', 'y_siguiente')})
    return 0


if __name__ == '__main__':
    sys.exit(main())
