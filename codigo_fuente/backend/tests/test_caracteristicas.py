# -*- coding: utf-8 -*-
"""Panel alumno-periodo: etiqueta correcta y variables sin fuga de información futura (CRISP-DM, preparación)."""
import numpy as np
import pandas as pd

from ml.caracteristicas import (VARIABLES_BASE, construir_panel, grupos_disponibles, matriz, variables_modelo)


def test_etiqueta_es_el_estado_del_periodo_siguiente(historial):
    panel = construir_panel(historial)
    for _, tray in panel.groupby('tray_id'):
        tray = tray.sort_values('fecha')
        estados = tray['estado_codigo'].tolist()
        for i, y in enumerate(tray['y'].tolist()):
            if i == len(estados) - 1:
                assert np.isnan(y)
            else:
                assert y == float(estados[i + 1] == 'RETIRADO')


def test_solo_se_califica_el_periodo_vigente_de_quien_sigue_activo(historial):
    panel = construir_panel(historial)
    calificables = panel[panel['para_calificar'] == 1]
    assert (calificables['estado_codigo'] == 'ACTIVO').all()
    assert (calificables['es_ultimo_periodo'] == 1).all()
    assert calificables['alumno_id'].is_unique


def test_variables_no_usan_periodos_futuros(historial):
    """Cortar la historia después de un periodo no cambia las variables de ese periodo."""
    completo = construir_panel(historial).set_index('matricula_id')
    corte = historial['fecha'].sort_values().unique()[2]
    truncado = construir_panel(historial[historial['fecha'] <= corte]).set_index('matricula_id')
    propias = [c for c in VARIABLES_BASE if 'cohorte' not in c and c != 'avance_relativo']
    comunes = truncado.index.intersection(completo.index)
    pd.testing.assert_frame_equal(truncado.loc[comunes, propias], completo.loc[comunes, propias], check_exact=False, atol=1e-9)


def test_grupos_opcionales_se_detectan_por_cobertura(historial):
    assert grupos_disponibles(historial) == ['financieras']
    sin_saldo = historial.drop(columns=['saldo_pendiente'])
    assert 'financieras' not in grupos_disponibles(sin_saldo)


def test_matriz_tiene_exactamente_las_columnas_del_modelo(historial):
    panel = construir_panel(historial)
    columnas = variables_modelo(['financieras'])
    X = matriz(panel, columnas)
    assert list(X.columns) == columnas and len(X) == len(panel)
    assert X[VARIABLES_BASE].notna().all().all()


def test_panel_vacio():
    assert construir_panel(pd.DataFrame()).empty
