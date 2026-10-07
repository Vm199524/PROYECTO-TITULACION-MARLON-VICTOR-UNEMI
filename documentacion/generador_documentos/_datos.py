# -*- coding: utf-8 -*-
"""
Cifras del Avance 2 leídas de los resultados reales del sistema.

El documento no copia números a mano: todo valor de desempeño sale de
ml/modelos/<institución>/*.json y de la evaluación de la consulta
conversacional, de modo que el texto y el software siempre coinciden.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / 'codigo_fuente' / 'backend'
MODELOS = BACKEND / 'ml' / 'modelos'
DIAGRAMAS = RAIZ / 'documentacion' / 'diagramas'
FIGURAS = RAIZ / 'documentacion' / 'figuras'
CAPTURAS = RAIZ / 'documentacion' / 'capturas'
NBSP = ' '


def _json(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else {}


def cargar(institucion: str) -> dict:
    base = MODELOS / institucion
    return {'m': _json(base / 'metricas.json'), 's': _json(base / 'segmentacion.json'),
            'mon': _json(base / 'monitoreo.json'), 'p': _json(base / 'prospectiva.json')}


def consulta() -> tuple[dict, str]:
    """Última evaluación de la consulta conversacional y su procedencia.

    Prioriza la corrida sobre SQL Server (backend/eval/resultados). Si aún no
    existe, usa la de la réplica de validación indicada en EVAL_CONSULTA.
    """
    reales = sorted(glob.glob(str(BACKEND / 'eval' / 'resultados' / 'consulta_UNEMI_PRUEBAS_*.json')))
    if reales:
        return _json(Path(reales[-1])), 'SQL_SERVER'
    alterna = os.environ.get('EVAL_CONSULTA')
    if alterna and Path(alterna).exists():
        return _json(Path(alterna)), 'REPLICA'
    return {}, 'PENDIENTE'


U = cargar('UNEMI_PRUEBAS')
O = cargar('OULAD_UK')
C, C_ORIGEN = consulta()


def f(x, d: int = 3) -> str:
    """Número con coma decimal (es-EC)."""
    if x is None:
        return 'n. d.'
    s = f'{float(x):,.{d}f}'
    return s.replace(',', '§').replace('.', ',').replace('§', '.')


def ent(n) -> str:
    return f'{int(n):,}'.replace(',', '.')


def pct(x, d: int = 1, escala: float = 100) -> str:
    return f'{f(float(x) * escala, d)}{NBSP}%'


def cv(m: dict, modelo: str, metrica: str = 'roc_auc') -> str:
    r = m['comparacion_cv'][modelo][metrica]
    return f"{f(r['media'])} ± {f(r['desviacion'])}"


NOMBRE_MODELO = {'RF_PONDERADO': 'Random Forest con pesos por clase', 'RF_SMOTE': 'Random Forest con SMOTE',
                 'LOGISTICA': 'Regresión logística', 'LIGHTGBM': 'LightGBM'}


_TILDES = {'Ingenieria': 'Ingeniería', 'Enfermeria': 'Enfermería', 'Comunicacion': 'Comunicación',
           'Educacion': 'Educación', 'Basica': 'Básica', 'Pedagogia': 'Pedagogía', 'Fisica': 'Física',
           'Contaduria': 'Contaduría', 'Publica': 'Pública', 'Auditoria': 'Auditoría', 'Agregacion': 'Agregación',
           'Evaluacion': 'Evaluación', 'Segmentacion': 'Segmentación', 'Clustering': 'Agrupamiento',
           'Benchmark': 'Referentes', 'Ranking': 'Clasificación'}


def bonito(texto: str) -> str:
    """Nombres de los datos de prueba (sin tildes) escritos con ortografía correcta para el documento."""
    import re as _re
    return _re.sub(r'\b(' + '|'.join(_TILDES) + r')\b', lambda m: _TILDES[m.group(1)], str(texto))


LAT = _json(RAIZ / 'documentacion' / 'evidencias' / 'latencia_replica.json')
EXP_U = _json(MODELOS / 'UNEMI_PRUEBAS' / 'exploracion.json')
EXP_O = _json(MODELOS / 'OULAD_UK' / 'exploracion.json')
