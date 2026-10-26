# -*- coding: utf-8 -*-
"""
Anonimización de la trayectoria real de una carrera antes de cargarla al almacén.

Prepara el extracto que una institución entregue (con autorización y bajo
acuerdo de confidencialidad, ver documentacion/gobierno_datos/) para validar el
modelo con datos reales sin que la información identifique a ninguna persona.
Aplica, en este orden, las medidas de la LOPDP (minimización y
seudonimización) y de la política de gobierno de datos del proyecto:

  1. Minimización: se conservan solo las columnas del contrato del almacén
     (etl/perfiles.py). Cualquier otra (dirección, teléfono, correo, fecha de
     nacimiento, etnia, discapacidad...) se descarta sin leerse más.
  2. Seudonimización de la cédula con HMAC-SHA256 y una clave secreta que
     custodia la institución (variable ANONIMIZACION_CLAVE). El resultado es un
     identificador estable de 10 dígitos que permite unir los periodos de un
     mismo estudiante, pero que sin la clave no se puede revertir ni recalcular
     con un diccionario de cédulas.
  3. Supresión de nombres y apellidos (se reemplazan por «Estudiante» y el
     seudónimo) y generalización de la ciudad de residencia: las ciudades con
     menos de K estudiantes pasan a «OTRA».
  4. Control de k-anonimato sobre los cuasi-identificadores (género, ciudad,
     carrera, sede, modalidad, periodo de ingreso): los estudiantes cuya
     combinación aparece menos de K veces se informan y, con --suprimir, se
     excluyen del extracto.
  5. Informe JSON con lo que se hizo (columnas descartadas, k alcanzado,
     filas suprimidas) para el registro de tratamiento de datos. El informe no
     contiene ningún dato personal.

Uso:
    set ANONIMIZACION_CLAVE=<clave larga que guarda la institución>
    python -m scripts.anonimizar_carrera entrada.csv salida.csv --k 5 --suprimir

El CSV de entrada debe traer, con esos nombres o con un mapeo en --columnas,
las columnas del contrato. El de salida se carga con un perfil
REAL_ANONIMIZADO (por ejemplo UNEMI_CARRERA en etl/perfiles.py).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.perfiles import COLUMNAS_OBLIGATORIAS, COLUMNAS_OPCIONALES  # noqa: E402

CUASI_IDENTIFICADORES = ['genero', 'ciudad_residencia', 'carrera', 'sede_codigo', 'modalidad', 'cohorte']


def seudonimo(cedula: str, clave: bytes) -> str:
    """Identificador de 10 dígitos derivado con HMAC-SHA256 (irreversible sin la clave)."""
    digest = hmac.new(clave, str(cedula).strip().encode('utf-8'), hashlib.sha256).hexdigest()
    return str(int(digest[:15], 16) % 10**10).zfill(10)


def anonimizar(df: pd.DataFrame, clave: bytes, k: int = 5, suprimir: bool = False) -> tuple[pd.DataFrame, dict]:
    """Aplica minimización, seudonimización, generalización y control de k-anonimato.

    Returns:
        (extracto anonimizado, informe sin datos personales).
    """
    if len(clave) < 16:
        raise ValueError('La clave de anonimización debe tener al menos 16 caracteres.')
    faltan = [c for c in COLUMNAS_OBLIGATORIAS if c not in df.columns]
    if faltan:
        raise ValueError(f'Faltan columnas obligatorias del contrato: {faltan}')
    permitidas = COLUMNAS_OBLIGATORIAS + [c for c in COLUMNAS_OPCIONALES if c in df.columns]
    descartadas = [c for c in df.columns if c not in permitidas]
    out = df[permitidas].copy()

    mapa = {c: seudonimo(c, clave) for c in out['cedula'].astype(str).unique()}
    if len(set(mapa.values())) != len(mapa):
        raise RuntimeError('Colisión de seudónimos: use una clave distinta.')
    out['cedula'] = out['cedula'].astype(str).map(mapa)
    out['apellidos'] = 'Estudiante'
    out['nombres'] = out['cedula']

    por_ciudad = out.groupby('ciudad_residencia')['cedula'].nunique()
    raras = set(por_ciudad[por_ciudad < k].index)
    out['ciudad_residencia'] = out['ciudad_residencia'].where(~out['ciudad_residencia'].isin(raras), 'OTRA')

    primer = out.groupby('cedula')['periodo_academico'].transform('min')
    estudiantes = out.assign(cohorte=primer).drop_duplicates('cedula')[['cedula'] + CUASI_IDENTIFICADORES]
    tamanos = estudiantes.groupby(CUASI_IDENTIFICADORES, dropna=False)['cedula'].transform('size')
    en_riesgo = set(estudiantes.loc[tamanos < k, 'cedula'])
    k_alcanzado = int(tamanos.min()) if len(tamanos) else 0
    if suprimir and en_riesgo:
        out = out[~out['cedula'].isin(en_riesgo)]
        restantes = estudiantes[~estudiantes['cedula'].isin(en_riesgo)]
        k_alcanzado = int(restantes.groupby(CUASI_IDENTIFICADORES, dropna=False).size().min()) if len(restantes) else 0

    informe = {
        'filas_entrada': int(len(df)), 'filas_salida': int(len(out)),
        'estudiantes_entrada': int(df['cedula'].nunique()), 'estudiantes_salida': int(out['cedula'].nunique()),
        'columnas_descartadas': descartadas, 'ciudades_generalizadas': len(raras),
        'k_objetivo': k, 'k_alcanzado': k_alcanzado,
        'estudiantes_bajo_k': len(en_riesgo), 'suprimidos': bool(suprimir and en_riesgo),
        'cuasi_identificadores': CUASI_IDENTIFICADORES,
        'tecnica_seudonimo': 'HMAC-SHA256 con clave custodiada por la institución (10 dígitos)',
    }
    return out.reset_index(drop=True), informe


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('entrada')
    parser.add_argument('salida')
    parser.add_argument('--k', type=int, default=5, help='Tamaño mínimo de cada grupo de cuasi-identificadores')
    parser.add_argument('--suprimir', action='store_true', help='Excluir a quienes no alcanzan k')
    parser.add_argument('--columnas', help='JSON con el mapeo {"columna_origen": "columna_contrato"}')
    args = parser.parse_args()
    clave = os.environ.get('ANONIMIZACION_CLAVE', '').encode('utf-8')
    df = pd.read_csv(args.entrada, dtype={'cedula': str}, encoding='utf-8-sig')
    if args.columnas:
        df = df.rename(columns=json.loads(Path(args.columnas).read_text(encoding='utf-8')))
    salida, informe = anonimizar(df, clave, args.k, args.suprimir)
    salida.to_csv(args.salida, index=False, encoding='utf-8')
    Path(args.salida).with_suffix('.informe.json').write_text(json.dumps(informe, indent=2, ensure_ascii=False),
                                                              encoding='utf-8')
    print(json.dumps(informe, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
