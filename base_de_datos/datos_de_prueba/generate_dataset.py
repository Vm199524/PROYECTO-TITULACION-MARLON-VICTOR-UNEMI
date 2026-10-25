# -*- coding: utf-8 -*-
"""
Generación del dataset de prueba alumnos_prueba.csv.

Parte del padrón extraído del PDF de UNEMI (raw_records.json): conserva número,
apellidos y nombres (de NOMINA), cédula y facultad; descarta SEDE, LUGAR DE
VOTACION, N DE MESA y FIRMA, y agrega columnas SINTÉTICAS con semilla fija para
pruebas de BI (carrera, semestre, estado, promedio, fechas, montos, beca, saldo,
género, ciudad), que no son datos académicos reales de UNEMI. No escribe el
padrón crudo y al terminar ejecuta anonimizar_padron.py (LOPDP). raw_records.json
contiene datos personales y se conserva FUERA del repositorio, por lo que este
script no se puede volver a correr sin él: el artefacto del proyecto es el CSV
anonimizado. Se ejecuta desde la raíz del repositorio.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import json
import random
import csv
from datetime import date, timedelta

random.seed(20260909)  # reproducible

with open('base_de_datos/datos_de_prueba/raw_records.json', encoding='utf-8') as f:
    raw = json.load(f)

FACULTADES = {
    'FACSECYD': {
        'nombre': 'Facultad de Ciencias Sociales, Educacion Comercial y Derecho',
        'carreras': ['Ingenieria Comercial', 'Contaduria Publica y Auditoria', 'Derecho', 'Turismo', 'Comunicacion Social', 'Trabajo Social'],
    },
    'FACE': {
        'nombre': 'Facultad de Educacion Semipresencial y a Distancia',
        'carreras': ['Educacion Basica', 'Educacion Inicial', 'Pedagogia de la Actividad Fisica y Deporte', 'Pedagogia de los Idiomas Nacionales y Extranjeros'],
    },
    'FACI': {
        'nombre': 'Facultad de Ciencias e Ingenieria',
        'carreras': ['Ingenieria en Sistemas Computacionales', 'Ingenieria Industrial', 'Ingenieria Civil', 'Ingenieria en Alimentos', 'Ingenieria Agropecuaria'],
    },
    'FACS': {
        'nombre': 'Facultad de Ciencias de la Salud',
        'carreras': ['Enfermeria', 'Terapia Respiratoria', 'Medicina'],
    },
}

ESTADOS = ['ACTIVO'] * 75 + ['GRADUADO'] * 10 + ['RETIRADO'] * 10 + ['EGRESADO'] * 5
CIUDADES = (['MILAGRO'] * 40 + ['GUAYAQUIL'] * 25 + ['NARANJITO'] * 8 + ['YAGUACHI'] * 8 +
            ['SIMON BOLIVAR'] * 6 + ['EL TRIUNFO'] * 5 + ['DURAN'] * 4 + ['BUCAY'] * 2 + ['BABAHOYO'] * 2)
BECAS = [0] * 60 + [25] * 15 + [50] * 15 + [75] * 5 + [100] * 5

# Diccionario de excepciones construido sobre los ~150 nombres más
# frecuentes del propio dataset que NO terminan en "A", donde la heurística
# simple por terminación puede fallar (p. ej., GENESIS o EVELYN son
# femeninos); los masculinos frecuentes se fijan también de forma explícita.
GENERO_EXCEPCIONES = {
    'F': {
        'GENESIS', 'ANGIE', 'KAREN', 'EVELYN', 'JOSELYN', 'LADY', 'KATHERINE', 'MELANIE',
        'JENNIFER', 'MELANY', 'KERLY', 'NICOLE', 'JENNIFFER', 'EMILY', 'LISSETTE', 'CARMEN',
        'ALLISSON', 'SHIRLEY', 'GINGER', 'ALLISON', 'NATHALY', 'LISBETH', 'AMBAR', 'WENDY',
        'DAMARIS', 'NAYELI', 'JENIFFER', 'MICHELLE', 'RUTH', 'CINDY', 'DENISSE', 'SOLANGE',
        'KELLY', 'MARJORIE', 'HELEN', 'ELIZABETH', 'INGRID', 'ODALYS', 'ASHLEY', 'JAZMIN',
        'MARIUXI', 'JOSSELYN', 'BRIGGITTE', 'JOSELYNE', 'SANDY', 'GRACE', 'LILIBETH', 'ESTHER',
        'MERCEDES', 'MELANNY', 'LOURDES', 'GLADYS', 'ODALIS', 'JENNY', 'NAGELY', 'JOYCE',
        'MIRIAM', 'NELLY', 'EVELIN', 'NAYELY', 'LESLIE', 'KIMBERLY', 'MARILYN', 'MILDRED',
        'BETSY', 'KATTY', 'EMELY', 'NALLELY', 'JOSELINE', 'ITZEL', 'NAOMI', 'MAYTE', 'ANAIS',
        'DEBORA', 'TAHIS', 'BRITHANY', 'ABIGAIL', 'ROCIO', 'LUZ', 'DOLORES', 'BELEN', 'PAZ',
    },
    'M': {
        'LUIS', 'JOSE', 'CARLOS', 'KEVIN', 'BRYAN', 'JORGE', 'JUAN', 'VICTOR', 'JONATHAN',
        'ANTHONY', 'ANGEL', 'ALEX', 'CHRISTIAN', 'STEVEN', 'ERICK', 'JOEL', 'MICHAEL', 'ANDRES',
        'JEAN', 'DANIEL', 'JEFFERSON', 'JOSUE', 'JESUS', 'DAVID', 'OSCAR', 'CRISTHIAN', 'MARIO',
        'EDISON', 'FERNANDO', 'MIGUEL', 'DIEGO', 'FREDDY', 'PEDRO', 'RICARDO', 'MANUEL', 'WILSON',
        'JOHN', 'JULIO', 'CESAR', 'BYRON', 'RONALD', 'ADRIAN', 'EDUARDO', 'ARIEL', 'FRANCISCO',
        'DANNY', 'RONNY', 'JAVIER', 'EDWIN', 'MARCOS', 'JORDAN', 'WILLIAM', 'HECTOR', 'PABLO',
        'DARWIN', 'MARCO', 'JHON', 'ROBERTO', 'WALTER', 'ANGELO', 'MARLON', 'JORDY', 'ALEXIS',
        'IVAN', 'EDGAR', 'RICHARD', 'HENRY', 'ANDY', 'FRANKLIN', 'CRISTOPHER', 'JIMMY', 'GABRIEL',
        'ISAAC', 'LEONARDO', 'OMAR', 'ANTONIO', 'SAMUEL', 'STALIN', 'JOHNNY',
    },
}

def split_nombre(nomina: str):
    """Separa la NOMINA del padrón en (apellidos, nombres).

    Con tres o más palabras, las dos primeras son los apellidos; con dos, una
    y una; con una sola, se toma como apellido y el nombre queda vacío.
    """
    partes = nomina.split()
    if len(partes) >= 3:
        apellidos = ' '.join(partes[:2])
        nombres = ' '.join(partes[2:])
    elif len(partes) == 2:
        apellidos, nombres = partes[0], partes[1]
    else:
        apellidos, nombres = partes[0], ''
    return apellidos, nombres

def inferir_genero(primer_nombre: str) -> str:
    """Infiere el género ('F' o 'M') a partir del primer nombre.

    Consulta primero GENERO_EXCEPCIONES; si el nombre no está, aplica la
    heurística de terminación: 'F' si termina en "A", 'M' en otro caso.
    """
    nombre = primer_nombre.upper()
    if nombre in GENERO_EXCEPCIONES['F']:
        return 'F'
    if nombre in GENERO_EXCEPCIONES['M']:
        return 'M'
    return 'F' if nombre.endswith('A') else 'M'

def fecha_matricula_random() -> date:
    """Devuelve una fecha de matrícula aleatoria entre el 1/4/2022 y el 1/4/2026."""
    inicio = date(2022, 4, 1)
    fin = date(2026, 4, 1)
    dias = (fin - inicio).days
    return inicio + timedelta(days=random.randint(0, dias))

rows = []
for r in raw:
    apellidos, nombres = split_nombre(r['nomina'])
    facultad_codigo = r['facultad']
    fac = FACULTADES.get(facultad_codigo, FACULTADES['FACSECYD'])
    carrera = random.choice(fac['carreras'])
    estado = random.choice(ESTADOS)
    semestre = 10 if estado in ('GRADUADO', 'EGRESADO') else random.randint(1, 9)
    promedio_base = random.gauss(7.6, 1.0)
    if estado == 'RETIRADO':
        promedio_base -= 1.2
    promedio = max(0.0, min(10.0, round(promedio_base, 2)))
    monto_matricula = round(random.uniform(80, 300), 2)
    beca_porcentaje = random.choice(BECAS)
    monto_neto = round(monto_matricula * (1 - beca_porcentaje / 100), 2)
    en_mora = random.random() < 0.18 and estado == 'ACTIVO'
    saldo_pendiente = round(monto_neto * random.uniform(0.3, 1.0), 2) if en_mora else 0.0
    primer_nombre = nombres.split()[0] if nombres else apellidos.split()[0]
    genero = inferir_genero(primer_nombre)
    ciudad = random.choice(CIUDADES)

    rows.append({
        'no': r['no'],
        'apellidos': apellidos,
        'nombres': nombres,
        'cedula': r['cedula'],
        'facultad_codigo': facultad_codigo,
        'facultad_nombre': fac['nombre'],
        'carrera': carrera,
        'semestre': semestre,
        'estado_matricula': estado,
        'promedio': promedio,
        'fecha_matricula': fecha_matricula_random().isoformat(),
        'monto_matricula': monto_matricula,
        'beca_porcentaje': beca_porcentaje,
        'saldo_pendiente': saldo_pendiente,
        'genero': genero,
        'ciudad_residencia': ciudad,
    })

out_path = 'base_de_datos/datos_de_prueba/alumnos_prueba.csv'
fieldnames = list(rows[0].keys())
with open(out_path, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print('CSV final generado:', out_path, '-', len(rows), 'filas')

# Anonimizar de inmediato: el CSV con cédulas/nombres reales no debe
# quedar en disco ni un paso más de lo necesario.
import runpy
runpy.run_path('base_de_datos/datos_de_prueba/anonimizar_padron.py', run_name='__main__')
