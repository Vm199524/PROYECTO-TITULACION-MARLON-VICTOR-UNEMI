# -*- coding: utf-8 -*-
"""
Anonimización del dataset de prueba (RNF de privacidad, LOPDP).

alumnos_prueba.csv parte del padrón electoral público de UNEMI: sus cédulas y
nombres corresponden a personas reales, mientras que el resto de columnas
(carrera, promedio, mora, estado RETIRADO...) es sintético, lo que atribuiría
abandono y mora inventados a personas identificables. El script reemplaza
cédula, apellidos y nombres por valores ficticios en alumnos_prueba.csv y en
historial_matriculas.csv con la misma correspondencia, y conserva EXACTAMENTE el
resto de columnas, así ninguna métrica del modelo cambia. Es idempotente.

Uso (desde la raíz del proyecto):
    python "base_de_datos/datos_de_prueba/anonimizar_padron.py"

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
ALUMNOS = DIR / 'alumnos_prueba.csv'
HISTORIAL = DIR / 'historial_matriculas.csv'
# Semilla fija, la misma del resto del dataset: la anonimización es reproducible.
SEMILLA = 20260909

# Nombres ficticios: combinaciones de listas genéricas, elegidas según la
# columna `genero` existente para que el nombre sea coherente con ella.
NOMBRES_F = ['Ana', 'María', 'Lucía', 'Valeria', 'Camila', 'Daniela', 'Gabriela', 'Andrea', 'Paula',
             'Sofía', 'Isabel', 'Carolina', 'Fernanda', 'Natalia', 'Mónica', 'Patricia', 'Rosa', 'Elena',
             'Julia', 'Carla', 'Diana', 'Laura', 'Sara', 'Tatiana', 'Verónica', 'Ximena', 'Silvia', 'Noemí']
NOMBRES_M = ['Juan', 'Carlos', 'Luis', 'José', 'Andrés', 'Diego', 'Mateo', 'Santiago', 'Pablo', 'Javier',
             'Miguel', 'Daniel', 'Fernando', 'Ricardo', 'Sebastián', 'Tomás', 'Nicolás', 'Gustavo', 'Hugo',
             'Iván', 'Rafael', 'Samuel', 'Esteban', 'Manuel', 'Óscar', 'Raúl', 'Víctor', 'Alberto']
APELLIDOS = ['Aguirre', 'Alvarado', 'Andrade', 'Bravo', 'Cabrera', 'Castillo', 'Cedeño', 'Cevallos', 'Chávez',
             'Delgado', 'Espinoza', 'Flores', 'Guerrero', 'Herrera', 'Jiménez', 'León', 'Macías', 'Mendoza',
             'Mora', 'Moreira', 'Navarrete', 'Ortiz', 'Paredes', 'Quintero', 'Ramírez', 'Reyes', 'Rivera',
             'Salazar', 'Sánchez', 'Suárez', 'Torres', 'Valencia', 'Vargas', 'Vera', 'Villacís', 'Zambrano']


def digito_verificador(nueve: str) -> int:
    """Algoritmo módulo 10 de la cédula ecuatoriana sobre los 9 primeros dígitos."""
    total = 0
    for i, d in enumerate(nueve):
        v = int(d) * (2 if i % 2 == 0 else 1)
        total += v - 9 if v > 9 else v
    return (10 - total % 10) % 10


def cedula_ficticia(rng: random.Random, usadas: set[str]) -> str:
    """Genera una cédula ficticia única de 10 dígitos y la registra en `usadas`.

    Lleva dígito verificador válido (módulo 10), pero código de provincia
    "00", que el Registro Civil no asigna: así nunca coincide con la cédula de
    una persona real.
    """
    while True:
        nueve = '00' + str(rng.randint(0, 5)) + f'{rng.randint(0, 999999):06d}'
        ced = nueve + str(digito_verificador(nueve))
        if ced not in usadas:
            usadas.add(ced)
            return ced


def leer(path: Path) -> tuple[list[str], list[dict]]:
    """Lee un CSV en UTF-8 con BOM y devuelve sus columnas y sus filas como diccionarios."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        return list(lector.fieldnames or []), list(lector)


def escribir(path: Path, columnas: list[str], filas: list[dict]) -> None:
    """Sobrescribe un CSV en UTF-8 con BOM con las columnas y filas dadas, en ese orden."""
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)


def main() -> int:
    """Anonimiza alumnos_prueba.csv y el historial; devuelve el código de salida.

    Devuelve 0 si anonimiza o si el archivo ya estaba anonimizado (todas las
    cédulas con provincia 00), y 1 si falta alumnos_prueba.csv o si el
    historial tiene cédulas ausentes de él; en ese caso no escribe nada.
    """
    if not ALUMNOS.exists():
        print(f'No existe {ALUMNOS}')
        return 1

    rng = random.Random(SEMILLA)
    cols_a, alumnos = leer(ALUMNOS)
    if all(r['cedula'].startswith('00') for r in alumnos):
        print('alumnos_prueba.csv ya está anonimizado (todas las cédulas con provincia 00). Nada que hacer.')
        return 0

    usadas: set[str] = set()
    # La correspondencia cédula real -> ficticia vive solo en memoria y nunca
    # se guarda: esa tabla permitiría revertir la anonimización (sería, en sí
    # misma, un dato personal).
    mapa: dict[str, str] = {}
    for r in sorted(alumnos, key=lambda r: int(r['no'])):
        real = r['cedula']
        if real not in mapa:
            mapa[real] = cedula_ficticia(rng, usadas)
        nombres = NOMBRES_F if r['genero'] == 'F' else NOMBRES_M
        r['cedula'] = mapa[real]
        r['apellidos'] = f'{rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}'
        r['nombres'] = f'{rng.choice(nombres)} {rng.choice(nombres)}'

    n_hist = 0
    if HISTORIAL.exists():
        cols_h, historial = leer(HISTORIAL)
        faltantes = {h['cedula'] for h in historial} - set(mapa)
        if faltantes:
            print(f'ERROR: {len(faltantes)} cédulas del historial no están en alumnos_prueba.csv; no se escribe nada.')
            return 1
        for h in historial:
            h['cedula'] = mapa[h['cedula']]
        escribir(HISTORIAL, cols_h, historial)
        n_hist = len(historial)

    escribir(ALUMNOS, cols_a, alumnos)
    print(f'Anonimizados {len(alumnos)} alumnos y {n_hist} filas de historial '
          f'(cédulas con provincia 00; el resto de columnas sin cambios).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
