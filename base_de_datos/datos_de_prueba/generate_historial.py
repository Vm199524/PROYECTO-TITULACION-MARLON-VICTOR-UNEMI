# -*- coding: utf-8 -*-
"""
Simulación de la trayectoria académica longitudinal de la base de pruebas UNEMI.

Genera historial_matriculas.csv (una fila por estudiante y periodo) y actualiza
en alumnos_prueba.csv las columnas que dependen de la trayectoria (nivel,
estado, promedio, fecha y saldo finales). Conserva la identidad ficticia de
cada estudiante (cédula, nombres, género, ciudad), su carrera, el valor de la
matrícula y la beca.

Por qué una simulación y no reglas fijas
-----------------------------------------
Una versión anterior insertaba el deterioro solo en el periodo previo al
retiro. Así el modelo separaba casi perfectamente (ROC-AUC ≈ 0,99), algo que no
ocurre con datos reales. Además, los estudiantes «activos» quedaban detenidos
en periodos antiguos. Esta versión simula el proceso que la literatura
describe (Tinto, 1975; Bean y Metzner, 1985):

  * Cada estudiante tiene factores latentes: capacidad académica, compromiso
    (que cambia de un periodo a otro con choques aleatorios) y situación
    económica (que entra y sale de la mora).
  * Lo observable se deriva de esos factores con ruido: promedio, asistencia,
    actividad en el aula virtual, entregas, anticipación de la matrícula,
    créditos, repetición de nivel y saldo pendiente.
  * Al cerrar cada periodo, el riesgo de abandonar en el siguiente es una
    función logística no lineal de lo observado. A eso se suman la dificultad
    de la carrera, el primer año y un componente que el sistema NO observa
    (motivación, familia, trabajo). Por eso ningún modelo puede predecir con
    certeza y las métricas resultan realistas.
  * Si se reprueba un nivel por tercera vez, se pierde la carrera (tercera
    matrícula, LOES art. 84).
  * Gradúa (o egresa sin titularse) quien aprueba el último nivel.

Calendario: semestres 2019-1 a 2026-1 (1S con clases desde mayo; 2S desde
octubre). Quien sigue ACTIVO en 2026-1, el último periodo cerrado, es el
estudiante que el sistema califica para el periodo siguiente (2026-2).

Todos los valores son SINTÉTICOS (semilla fija): sirven para probar la
arquitectura de punta a punta. La validación del modelo con datos reales se
hace con OULAD (Kuzilek et al., 2017).

Uso (desde la raíz del repositorio):
    python base_de_datos/datos_de_prueba/generate_historial.py

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 20260909
DIR = Path(__file__).resolve().parent
ALUMNOS = DIR / 'alumnos_prueba.csv'
HISTORIAL = DIR / 'historial_matriculas.csv'

# Calendario académico: (código, inicio de clases).
PERIODOS = []
for _anio in range(2019, 2027):
    PERIODOS.append((f'{_anio}-1', date(_anio, 5, 6)))
    if _anio < 2026:
        PERIODOS.append((f'{_anio}-2', date(_anio, 10, 7)))
ULTIMO = len(PERIODOS) - 1          # 2026-1: último periodo cerrado

# Duración del plan de estudios (niveles) y dificultad relativa de la carrera
# (desplazamiento del riesgo en escala logit; positivo = más abandono).
DURACION = {'Medicina': 10}
DIFICULTAD = {
    'Ingenieria Civil': 0.45, 'Ingenieria Industrial': 0.40, 'Ingenieria en Sistemas Computacionales': 0.35,
    'Ingenieria en Alimentos': 0.30, 'Ingenieria Agropecuaria': 0.30, 'Medicina': 0.10, 'Enfermeria': -0.10,
    'Terapia Respiratoria': 0.05, 'Derecho': 0.05, 'Contaduria Publica y Auditoria': 0.10,
    'Ingenieria Comercial': 0.05, 'Turismo': 0.15, 'Comunicacion Social': 0.0, 'Trabajo Social': -0.10,
    'Educacion Basica': -0.15, 'Educacion Inicial': -0.20, 'Pedagogia de la Actividad Fisica y Deporte': 0.0,
    'Pedagogia de los Idiomas Nacionales y Extranjeros': 0.10,
}
# Exigencia académica: cuánto baja el promedio esperado en la carrera.
EXIGENCIA = {'Medicina': 0.45, 'Ingenieria Civil': 0.40, 'Ingenieria Industrial': 0.30,
             'Ingenieria en Sistemas Computacionales': 0.30, 'Terapia Respiratoria': 0.20, 'Enfermeria': 0.20}

SEDES = [('MILAGRO', 'Sede Milagro')] * 80 + [('DURAN', 'Extension Duran')] * 20
CANALES = ['PRESENCIAL'] * 70 + ['HIBRIDA'] * 15 + ['EN LINEA'] * 15
# Evaluaciones con fecha de entrega vencida al cierre del periodo (todas las del
# periodo); las entregadas son un subconjunto. Mismo significado que en OULAD.
EVALUACIONES_POR_PERIODO = 12
INTERCEPTO = -4.75                  # calibrado: ~10 % de abandono por periodo en primer año y ~3 % al final


def _sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _poisson(rng: random.Random, media: float) -> int:
    """Poisson por aproximación normal (medias grandes) o por Knuth (pequeñas)."""
    if media > 30:
        return max(0, int(round(rng.gauss(media, math.sqrt(media)))))
    limite, k, p = math.exp(-media), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limite:
            return k
        k += 1


def _binomial(rng: random.Random, n: int, p: float) -> int:
    return sum(1 for _ in range(n) if rng.random() < p)


def riesgo_logit(obs: dict, carrera: str, latente: float) -> float:
    """Riesgo de abandonar en el periodo siguiente, en escala logit (no lineal)."""
    z = INTERCEPTO + DIFICULTAD.get(carrera, 0.0) + latente
    z += 0.75 if obs['nivel'] <= 2 else (0.25 if obs['nivel'] <= 4 else -0.20)
    z += 0.85 * max(0.0, 7.0 - obs['promedio'])                 # por debajo de la nota de aprobación
    z += 0.45 * max(0.0, obs['caida_promedio'])                  # deterioro respecto del periodo anterior
    z += 0.045 * max(0.0, 82.0 - obs['asistencia_pct'])
    z += 0.70 if obs['saldo_pendiente'] > 0 else 0.0
    z += 0.35 if obs['saldo_pendiente'] > 0 and obs['beca_porcentaje'] == 0 else 0.0
    z -= 0.35 if obs['beca_porcentaje'] >= 50 else 0.0
    z += 0.55 * (obs['numero_matricula'] - 1)
    z += 0.035 * max(0, obs['dias_sin_actividad'] - 9)
    z += 0.16 * obs['no_entregadas']
    z += 0.30 if obs['dias_anticipacion_matricula'] < 0 else 0.0  # matrícula tardía
    z += 0.25 if obs['creditos_matriculados'] < 18 else 0.0
    return z


def simular_estudiante(alumno: dict, cohorte: int, rng: random.Random) -> list[dict]:
    """Trayectoria de un estudiante desde su periodo de ingreso hasta su desenlace o 2026-1."""
    carrera = alumno['carrera']
    duracion = DURACION.get(carrera, 9)
    beca = int(alumno['beca_porcentaje'])
    monto = float(alumno['monto_matricula'])
    monto_neto = round(monto * (1 - beca / 100), 2)
    sede_codigo, sede_nombre = rng.choice(SEDES)
    canal = rng.choice(CANALES)

    capacidad = rng.gauss(0, 1)
    compromiso = rng.gauss(0, 1)
    # Vulnerabilidad económica: más alta sin beca y con matrícula cara.
    vulnerable = _sig(-1.2 + 0.9 * (beca == 0) + 0.006 * (monto - 190) + rng.gauss(0, 0.6))
    en_mora = rng.random() < 0.6 * vulnerable * 0.25
    latente_fijo = rng.gauss(0, 0.55)       # lo que el sistema nunca observa (familia, trabajo, motivación)

    filas: list[dict] = []
    nivel, intento, promedio_prev = 1, 1, None
    for k in range(cohorte, ULTIMO + 1):
        codigo, inicio = PERIODOS[k]
        # Dinámica de los factores latentes entre periodos.
        compromiso = 0.82 * compromiso + rng.gauss(0, 0.55)
        if en_mora:
            en_mora = rng.random() > 0.40
        else:
            en_mora = rng.random() < 0.20 * vulnerable

        exig = EXIGENCIA.get(carrera, 0.0)
        promedio = _clamp(rng.gauss(8.05 + 0.8 * capacidad + 0.45 * compromiso - exig - 0.25 * en_mora, 0.65), 0, 10)
        asistencia = _clamp(rng.gauss(87 + 6.5 * compromiso - 7 * en_mora - (4 if canal == 'EN LINEA' else 0), 6.5), 15, 100)
        actividad = _poisson(rng, math.exp(4.25 + 0.38 * compromiso + 0.10 * capacidad + (0.35 if canal != 'PRESENCIAL' else 0)))
        sin_actividad = int(_clamp(round(rng.gauss(6 - 4.5 * compromiso, 4.5)), 0, 60))
        p_entrega = _sig(2.1 + 1.25 * compromiso + 0.45 * capacidad - 0.4 * en_mora)
        entregadas = _binomial(rng, EVALUACIONES_POR_PERIODO, p_entrega)
        tardias = _binomial(rng, entregadas, _sig(-1.7 - 0.9 * compromiso + 0.5 * en_mora))
        nota_eval = _clamp(promedio + rng.gauss(0.2, 0.55), 0, 10) if entregadas else None
        anticipacion = int(round(rng.gauss(14 + 5 * compromiso - 9 * en_mora, 7)))
        creditos = int(_clamp(round(rng.gauss(26 - 6 * (intento > 1) - 4 * en_mora, 3)), 8, 32))
        saldo = round(monto_neto * rng.uniform(0.3, 1.0), 2) if en_mora and monto_neto > 0 else 0.0
        fecha = min(inicio - timedelta(days=anticipacion), date(2026, 10, 6))

        obs = {
            'nivel': nivel, 'promedio': round(promedio, 2), 'asistencia_pct': round(asistencia, 2),
            'caida_promedio': (promedio_prev - promedio) if promedio_prev is not None else 0.0,
            'saldo_pendiente': saldo, 'beca_porcentaje': beca, 'numero_matricula': intento,
            'dias_sin_actividad': sin_actividad, 'no_entregadas': EVALUACIONES_POR_PERIODO - entregadas,
            'dias_anticipacion_matricula': anticipacion, 'creditos_matriculados': creditos,
        }
        fila = {
            'cedula': alumno['cedula'], 'periodo_num': k - cohorte + 1, 'es_ultimo_periodo': 0,
            'facultad_codigo': alumno['facultad_codigo'], 'facultad_nombre': alumno['facultad_nombre'],
            'carrera': carrera, 'sede_codigo': sede_codigo, 'sede_nombre': sede_nombre, 'canal_codigo': canal,
            'semestre': nivel, 'estado_matricula': 'ACTIVO', 'promedio': obs['promedio'],
            'asistencia_pct': obs['asistencia_pct'], 'fecha_matricula': fecha.isoformat(),
            'inicio_clases': inicio.isoformat(), 'monto_matricula': monto, 'beca_porcentaje': beca,
            'saldo_pendiente': saldo, 'creditos_matriculados': creditos, 'numero_matricula': intento,
            'dias_anticipacion_matricula': anticipacion, 'actividad_lms': actividad,
            'dias_sin_actividad': sin_actividad, 'evaluaciones_vencidas': EVALUACIONES_POR_PERIODO,
            'evaluaciones_entregadas': entregadas, 'evaluaciones_tardias': tardias,
            'nota_evaluaciones': round(nota_eval, 2) if nota_eval is not None else '',
        }
        filas.append(fila)

        aprobado = promedio >= 7.0
        if aprobado and nivel == duracion:
            fila['estado_matricula'] = 'GRADUADO' if rng.random() < 0.72 else 'EGRESADO'
            break
        if not aprobado and intento == 3:
            fila['estado_matricula'] = 'RETIRADO'     # tercera matrícula reprobada: pierde la carrera
            break
        if k == ULTIMO:
            break
        # ¿Abandona en el periodo siguiente? Choque transitorio + latente fijo.
        if rng.random() < _sig(riesgo_logit(obs, carrera, latente_fijo + rng.gauss(0, 0.45))):
            codigo_sig, inicio_sig = PERIODOS[k + 1]
            # Se matricula, deja de asistir y se retira a mitad del periodo.
            filas.append(dict(
                fila, periodo_num=fila['periodo_num'] + 1, estado_matricula='RETIRADO',
                semestre=nivel + 1 if aprobado else nivel, numero_matricula=1 if aprobado else intento + 1,
                promedio=round(_clamp(promedio - rng.uniform(1.0, 3.0), 0, 10), 2),
                asistencia_pct=round(_clamp(rng.gauss(45, 15), 5, 100), 2),
                actividad_lms=_poisson(rng, max(2.0, actividad * 0.25)),
                dias_sin_actividad=int(_clamp(rng.gauss(35, 10), 10, 90)),
                evaluaciones_entregadas=_binomial(rng, EVALUACIONES_POR_PERIODO, 0.25),
                fecha_matricula=min(inicio_sig - timedelta(days=int(rng.gauss(4, 6))), date(2026, 10, 6)).isoformat(),
                inicio_clases=inicio_sig.isoformat(),
            ))
            ult = filas[-1]
            ult['evaluaciones_tardias'] = min(ult['evaluaciones_tardias'], ult['evaluaciones_entregadas'])
            ult['nota_evaluaciones'] = (round(_clamp(ult['promedio'] + rng.gauss(0, 0.6), 0, 10), 2)
                                        if ult['evaluaciones_entregadas'] else '')
            break
        if aprobado:
            nivel, intento = nivel + 1, 1
        else:
            intento += 1
        promedio_prev = promedio
    filas[-1]['es_ultimo_periodo'] = 1
    return filas


def main() -> None:
    rng = random.Random(SEMILLA)
    with open(ALUMNOS, encoding='utf-8-sig', newline='') as f:
        lector = csv.DictReader(f)
        campos_alumnos = lector.fieldnames
        alumnos = list(lector)

    # Cohortes de ingreso: más estudiantes en los periodos recientes (crecimiento de la oferta).
    pesos = [1.0 + 0.04 * k for k in range(ULTIMO + 1)]
    historial: list[dict] = []
    for alumno in alumnos:
        cohorte = rng.choices(range(ULTIMO + 1), weights=pesos)[0]
        filas = simular_estudiante(alumno, cohorte, rng)
        historial.extend(filas)
        final = filas[-1]
        alumno.update(semestre=final['semestre'], estado_matricula=final['estado_matricula'],
                      promedio=final['promedio'], fecha_matricula=final['fecha_matricula'],
                      saldo_pendiente=final['saldo_pendiente'])

    with open(HISTORIAL, 'w', newline='', encoding='utf-8-sig') as f:
        escritor = csv.DictWriter(f, fieldnames=list(historial[0].keys()))
        escritor.writeheader()
        escritor.writerows(historial)
    with open(ALUMNOS, 'w', newline='', encoding='utf-8-sig') as f:
        escritor = csv.DictWriter(f, fieldnames=campos_alumnos)
        escritor.writeheader()
        escritor.writerows(alumnos)

    estados: dict[str, int] = {}
    for a in alumnos:
        estados[a['estado_matricula']] = estados.get(a['estado_matricula'], 0) + 1
    no_ultimas = [h for h in historial if not h['es_ultimo_periodo'] or h['estado_matricula'] != 'ACTIVO']
    print(f'Historial: {len(historial)} filas de {len(alumnos)} estudiantes ({len(historial) / len(alumnos):.2f} periodos c/u).')
    print(f'Estado final: {estados}')
    print(f'Activos en 2026-1 (se califican para 2026-2): {estados.get("ACTIVO", 0)}')
    retiros = sum(1 for h in historial if h['estado_matricula'] == 'RETIRADO')
    print(f'Retiros por transición observada: {100 * retiros / max(1, len(no_ultimas)):.2f} %')


if __name__ == '__main__':
    main()
