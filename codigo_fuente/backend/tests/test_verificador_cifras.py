"""
Pruebas de core/verificador_cifras.py: la explicación que ve el usuario no
puede citar cifras que el resultado no respalda (casos reales detectados por
eval/evaluar_nl2sql.py el 25/09/2026).
"""

import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.verificador_cifras import cifras_no_respaldadas, resumen_determinista  # noqa: E402


def test_detecta_la_cifra_inventada_del_caso_real():
    # El modelo escribió "0.87" antes de ejecutar; el resultado real era 0,9971.
    texto = '✅ **ROC-AUC del modelo de predicción (validación temporal):** **0.87**.'
    assert cifras_no_respaldadas(texto, [(Decimal('0.9971'),)]) == ['0.87']


def test_detecta_marcadores_sin_rellenar():
    texto = 'La carrera con más riesgo es **[carrera]**, con **[alumnos_en_riesgo]** estudiantes; tasa {tasa_abandono}%.'
    assert len(cifras_no_respaldadas(texto, [('Derecho', 12)])) == 3


def test_acepta_cifras_respaldadas_con_formatos_distintos():
    filas = [(Decimal('10.02'), Decimal('44.9000'))]
    assert cifras_no_respaldadas('Nuestra tasa es 10,02 % frente a 44,9 % del referente.', filas) == []
    assert cifras_no_respaldadas('Hay **10.848** alumnos con matrícula vigente.', [(10848,)]) == []
    assert cifras_no_respaldadas('El modelo detecta el 77,71 % de los abandonos.', [(Decimal('0.7771'),)]) == []


def test_ignora_numeros_pequenos_anios_y_conteo_de_filas():
    filas = [('A', 1)] * 18
    assert cifras_no_respaldadas('Estas son las 18 carreras del periodo 2026, agrupadas en 3 niveles.', filas) == []


def test_resumen_determinista_solo_cita_el_resultado():
    r = resumen_determinista(['total'], [(1453,)])
    assert '1453' in r and cifras_no_respaldadas(r, [(1453,)]) == []
    assert '40 registros' in resumen_determinista(['a'], [(i,) for i in range(40)])
