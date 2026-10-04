# -*- coding: utf-8 -*-
"""
Genera la trayectoria academica longitudinal (1 fila por alumno-periodo) a
partir de alumnos_prueba.csv, que hoy solo tiene el estado FINAL de cada
alumno (1 fila = 1 alumno). Sin historia no hay como entrenar un modelo de
prediccion de abandono real: hace falta ver la EVOLUCION de cada estudiante
(promedio, mora, asistencia) periodo a periodo, no solo su foto actual.

Regla de generacion: el estado final de cada alumno (columna 'semestre' =
en que periodo esta / se retiro, 'estado_matricula' = como termino) definido
en alumnos_prueba.csv se respeta tal cual (no se toca ese archivo, sigue
siendo la fuente del padron real). Este script solo rellena los periodos
ANTERIORES 1..semestre-1 con una trayectoria sintetica coherente:

  - RETIRADO: rendimiento estable, luego caida de promedio + aumento de mora
    + caida de asistencia en los 1-2 periodos previos al abandono (senal que
    un modelo de churn deberia poder aprender).
  - ACTIVO / GRADUADO / EGRESADO: trayectoria estable con ruido normal.

Todos los valores son SINTETICOS (semilla fija), igual que en
generate_dataset.py.
"""
import csv
import random
from datetime import date, timedelta

random.seed(20260909)

SRC = 'codigo_fuente/base_de_datos/datos_de_prueba/alumnos_prueba.csv'
OUT = 'codigo_fuente/base_de_datos/datos_de_prueba/historial_matriculas.csv'

DIAS_POR_PERIODO = 152  # ~5 meses entre matriculas (2 periodos/anio)

# Variables nuevas pedidas para el modelo predictivo (sede, canal — ver
# documentacion/tecnica/PREDICCION_ABANDONO.md #8). UNEMI real es de un solo campus (Milagro),
# pero para probar de verdad que el pipeline soporta una IES multi-sede/
# multi-canal (como Universidad Politecnica Salesiana, con sedes en
# Cuenca/Quito/Guayaquil) se sintetiza una segunda sede y un canal a
# distancia, constantes por alumno igual que carrera/facultad.
SEDES = [('MILAGRO', 'Sede Milagro')] * 80 + [('DURAN', 'Extension Duran')] * 20
CANALES = ['PRESENCIAL'] * 85 + ['EN LINEA'] * 15


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def generar_trayectoria(alumno: dict) -> list[dict]:
    semestre_final = int(alumno['semestre'])
    estado_final = alumno['estado_matricula']
    fecha_final = date.fromisoformat(alumno['fecha_matricula'])
    promedio_final = float(alumno['promedio'])
    monto = float(alumno['monto_matricula'])
    beca = int(alumno['beca_porcentaje'])
    monto_neto = round(monto * (1 - beca / 100), 2)

    # Linea base de la carrera del alumno (antes del posible deterioro final).
    if estado_final == 'RETIRADO':
        promedio_base = clamp(promedio_final + random.uniform(1.0, 2.3), 4.0, 9.5)
    else:
        promedio_base = promedio_final

    sede_codigo, sede_nombre = random.choice(SEDES)
    canal_codigo = random.choice(CANALES)

    filas = []
    for p in range(1, semestre_final + 1):
        es_ultimo = (p == semestre_final)
        fecha_p = fecha_final - timedelta(days=(semestre_final - p) * DIAS_POR_PERIODO)

        if estado_final == 'RETIRADO' and p >= semestre_final - 1:
            # 1-2 periodos previos al abandono: deterioro visible.
            factor = 1.0 if es_ultimo else 0.5
            promedio_p = clamp(promedio_base - random.uniform(0.8, 1.8) * factor, 0.0, 10.0)
            asistencia_p = clamp(random.gauss(62, 12) - 15 * factor, 20.0, 100.0)
            en_mora = random.random() < (0.55 if es_ultimo else 0.35)
            saldo_p = round(monto_neto * random.uniform(0.4, 1.0), 2) if en_mora else 0.0
            estado_p = estado_final if es_ultimo else 'ACTIVO'
        else:
            promedio_p = clamp(random.gauss(promedio_base, 0.5), 0.0, 10.0)
            asistencia_p = clamp(random.gauss(89, 6), 40.0, 100.0)
            en_mora = random.random() < 0.10
            saldo_p = round(monto_neto * random.uniform(0.2, 0.7), 2) if en_mora else 0.0
            estado_p = estado_final if es_ultimo else 'ACTIVO'

        filas.append({
            'cedula': alumno['cedula'],
            'periodo_num': p,
            'es_ultimo_periodo': 1 if es_ultimo else 0,
            'facultad_codigo': alumno['facultad_codigo'],
            'facultad_nombre': alumno['facultad_nombre'],
            'carrera': alumno['carrera'],
            'sede_codigo': sede_codigo,
            'sede_nombre': sede_nombre,
            'canal_codigo': canal_codigo,
            'semestre': p,
            'estado_matricula': estado_p,
            'promedio': round(promedio_p, 2),
            'asistencia_pct': round(asistencia_p, 2),
            'fecha_matricula': fecha_p.isoformat(),
            'monto_matricula': monto,
            'beca_porcentaje': beca,
            'saldo_pendiente': saldo_p,
        })
    return filas


def main():
    with open(SRC, encoding='utf-8-sig', newline='') as f:
        alumnos = list(csv.DictReader(f))

    filas_out = []
    for alumno in alumnos:
        filas_out.extend(generar_trayectoria(alumno))

    fieldnames = list(filas_out[0].keys())
    with open(OUT, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filas_out)

    retirados = sum(1 for a in alumnos if a['estado_matricula'] == 'RETIRADO')
    print(f'Historial generado: {OUT}')
    print(f'  {len(alumnos)} alumnos -> {len(filas_out)} filas alumno-periodo')
    print(f'  promedio de periodos por alumno: {len(filas_out) / len(alumnos):.2f}')
    print(f'  alumnos con abandono (RETIRADO) en el estado final: {retirados}')


if __name__ == '__main__':
    main()
