# -*- coding: utf-8 -*-
"""
Generación de la trayectoria académica longitudinal historial_matriculas.csv.

alumnos_prueba.csv solo tiene el estado FINAL de cada alumno, y predecir el
abandono exige ver la EVOLUCIÓN (promedio, mora, asistencia) periodo a periodo.
Este script genera una fila por alumno-periodo: respeta el estado final
('semestre' = periodo en que está o se retiró; 'estado_matricula' = cómo
terminó), sin modificar alumnos_prueba.csv, y rellena los periodos anteriores.
RETIRADO: rendimiento estable y, en los 1-2 periodos previos al abandono, caída
de promedio y asistencia y más mora (la señal que el modelo debe aprender);
ACTIVO, GRADUADO y EGRESADO: trayectoria estable con ruido normal. Todos los
valores son SINTÉTICOS (semilla fija). Se ejecuta desde la raíz del repositorio.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import csv
import random
from datetime import date, timedelta

random.seed(20260909)

SRC = 'codigo_fuente/base_de_datos/datos_de_prueba/alumnos_prueba.csv'
OUT = 'codigo_fuente/base_de_datos/datos_de_prueba/historial_matriculas.csv'

DIAS_POR_PERIODO = 152  # ~5 meses entre matrículas (2 periodos por año)

# Variables sede y canal del modelo predictivo (ver
# documentacion/tecnica/PREDICCION_ABANDONO.md, sección 3). UNEMI tiene un
# solo campus (Milagro), pero para probar que el pipeline soporta una IES
# multisede y multicanal se sintetizan una segunda sede y un canal EN LINEA,
# constantes por alumno igual que la carrera y la facultad.
SEDES = [('MILAGRO', 'Sede Milagro')] * 80 + [('DURAN', 'Extension Duran')] * 20
CANALES = ['PRESENCIAL'] * 85 + ['EN LINEA'] * 15


def clamp(v, lo, hi):
    """Limita `v` al intervalo cerrado [lo, hi]."""
    return max(lo, min(hi, v))


def generar_trayectoria(alumno: dict) -> list[dict]:
    """Genera las filas alumno-periodo 1..semestre de un alumno de alumnos_prueba.csv.

    Las fechas retroceden DIAS_POR_PERIODO desde la fecha de matrícula final;
    sede y canal se sortean una vez y quedan fijos para todo el alumno. Solo
    el último periodo lleva el estado final; los anteriores quedan ACTIVO.
    """
    semestre_final = int(alumno['semestre'])
    estado_final = alumno['estado_matricula']
    fecha_final = date.fromisoformat(alumno['fecha_matricula'])
    promedio_final = float(alumno['promedio'])
    monto = float(alumno['monto_matricula'])
    beca = int(alumno['beca_porcentaje'])
    monto_neto = round(monto * (1 - beca / 100), 2)

    # Línea base del promedio del alumno (antes del posible deterioro final).
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
    """Lee alumnos_prueba.csv, escribe historial_matriculas.csv e imprime un resumen."""
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
