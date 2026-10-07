# -*- coding: utf-8 -*-
"""
Configuración común de las pruebas.

Las pruebas unitarias no necesitan SQL Server ni proveedores de IA: usan un
lector falso en memoria y un almacén de cuentas temporal. Las de integración
(marca `integracion`) se omiten solas si no hay conexión con el almacén.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Antes de importar core.config: almacén de cuentas y auditoría temporales, y
# sin proveedores de IA (las pruebas nunca salen a internet).
_TMP = Path(tempfile.mkdtemp(prefix='pruebas_vicmar_'))
os.environ['RUTA_USUARIOS'] = str(_TMP / 'usuarios.json')
os.environ['RUTA_AUDITORIA'] = str(_TMP / 'auditoria.jsonl')
os.environ['JWT_SECRET_KEY'] = 'clave-de-pruebas-' + 'x' * 40
os.environ['ADMIN_INICIAL_USUARIO'] = ''
os.environ['ADMIN_INICIAL_CLAVE'] = ''
for _var in ('GEMINI_API_KEY', 'GROQ_API_KEY', 'NVIDIA_API_KEY', 'DEEPSEEK_API_KEY'):
    os.environ[_var] = ''

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CARRERAS = ['Ingeniería de Software', 'Enfermería', 'Psicología', 'Educación Básica']
FACULTADES = ['Facultad de Ciencias e Ingeniería', 'Facultad de Salud y Servicios Sociales']


class LectorFalso:
    """Imita core.db.leer: registra cada consulta y devuelve filas fijas.

    `respuestas` asocia un fragmento del SQL con (columnas, filas); la primera
    coincidencia gana. Así se comprueba qué SQL ejecutó el motor sin tocar
    SQL Server.
    """

    def __init__(self, respuestas: dict | None = None):
        self.respuestas = respuestas or {}
        self.llamadas: list[tuple[str, str, tuple]] = []

    def __call__(self, sql: str, institucion: str, parametros=()):
        self.llamadas.append((sql, institucion, tuple(parametros)))
        if 'SELECT DISTINCT carrera' in sql or ('carrera' in sql and 'facultad_nombre' in sql and 'DISTINCT' in sql):
            return ['carrera', 'facultad_nombre'], [[c, FACULTADES[i % 2]] for i, c in enumerate(CARRERAS)]
        for fragmento, (columnas, filas) in self.respuestas.items():
            if fragmento in sql:
                return columnas, filas
        return ['total'], [[42]]


@pytest.fixture
def lector():
    return LectorFalso()


def historial_sintetico(alumnos: int = 300, periodos: int = 6, semilla: int = 7) -> pd.DataFrame:
    """Trayectorias sintéticas con la forma que entrega ml.datos.leer_historial()."""
    rng = np.random.default_rng(semilla)
    filas, matricula = [], 0
    inicio = pd.Timestamp('2022-04-01')
    for a in range(alumnos):
        carrera = a % 4
        riesgo = rng.random()
        promedio, asistencia = 8.5 - 3 * riesgo, 92 - 30 * riesgo
        abandona_en = int(rng.integers(2, periodos + 1)) if riesgo > 0.6 else None
        for p in range(periodos):
            matricula += 1
            estado = 'ACTIVO'
            ultimo = p == periodos - 1
            if abandona_en is not None and p == abandona_en:
                estado, ultimo = 'RETIRADO', True
            promedio = float(np.clip(promedio + rng.normal(-0.2 * riesgo, 0.4), 0, 10))
            asistencia = float(np.clip(asistencia + rng.normal(-3 * riesgo, 4), 0, 100))
            filas.append({
                'matricula_id': matricula, 'alumno_id': a + 1, 'carrera_id': carrera + 1, 'periodo_id': p + 1,
                'periodo_codigo': f'{2022 + p // 2}-{p % 2 + 1}',
                'fecha_inicio': inicio + pd.DateOffset(months=6 * p),
                'fecha': inicio + pd.DateOffset(months=6 * p), 'nivel': p + 1, 'corte': 1,
                'estado_codigo': estado, 'es_ultimo_periodo': int(ultimo), 'promedio': round(promedio, 2),
                'asistencia_pct': round(asistencia, 1), 'saldo_pendiente': float(rng.choice([0, 0, 0, 150, 420]) if riesgo > 0.4 else 0),
                'beca_porcentaje': float(rng.choice([0, 0, 50])), 'cedula': f'09{a:08d}', 'genero': 'F' if a % 2 else 'M',
                'carrera': CARRERAS[carrera], 'sede_codigo': 'MIL', 'modalidad_codigo': 'PRESENCIAL',
            })
            if ultimo:
                break
    return pd.DataFrame(filas)


@pytest.fixture(scope='session')
def historial():
    return historial_sintetico()


def _hay_almacen() -> bool:
    try:
        from core.db import leer
        leer('SELECT TOP 1 institucion_codigo FROM VIS_INSTITUCION', 'UNEMI_PRUEBAS')
        return True
    except Exception:  # noqa: BLE001 — sin conexión, la prueba se omite
        return False


def pytest_collection_modifyitems(config, items):
    marcadas = [i for i in items if 'integracion' in i.keywords]
    if marcadas and not _hay_almacen():
        omitir = pytest.mark.skip(reason='Sin conexión con ALMACEN_ACADEMICO (prueba de integración)')
        for item in marcadas:
            item.add_marker(omitir)
