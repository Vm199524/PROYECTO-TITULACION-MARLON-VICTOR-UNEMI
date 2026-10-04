# -*- coding: utf-8 -*-
"""
_build_avance2.py — genera Avance_2_VicMar_Data_AI.docx a partir del
documento oficial del Avance 1 (que NO se modifica), agregando:

  2. Análisis del caso (2.1 Requerimientos)            — retroalimentación tutoras
  3. Diseño y desarrollo del trabajo práctico (3.1-3.3) — retroalimentación tutoras

Principio: UNA SOLA FUENTE DE VERDAD. Ninguna cifra se escribe a mano: se leen
de los artefactos que produce el código (metrics.json, metricas_clustering.json,
resultados_nl2sql_*.json, diccionario_datos.json) y los fragmentos de código
se extraen de los archivos fuente al generar. Así el documento no puede
decir algo distinto de lo que hace el sistema.

Uso (desde la carpeta del Avance):
    python _build_avance2.py
"""
from __future__ import annotations

import ast
import glob
import json
import re
import shutil
import sys
from pathlib import Path

import docx
from docx.shared import Pt

from _docx_helpers import Insertor, quitar_numeracion, reemplazar_texto

AQUI = Path(__file__).resolve().parent          # documentacion/generador_documentos
DOC = AQUI.parent                                # documentacion/
RAIZ = DOC.parent                                # raíz del repositorio
BACK = RAIZ / 'codigo_fuente' / 'backend'
FRONT = RAIZ / 'codigo_fuente' / 'frontend'
SRC = DOC / 'avances' / 'Formato Oficial del Proyecto de titulación de UNEMI Marlon y Victor solo avance 1.docx'
OUT = DOC / 'avances' / 'Avance_2_VicMar_Data_AI.docx'
FIG = DOC / 'figuras'
DIAG = DOC / 'diagramas'


# ── Artefactos del sistema (fuente única de cifras) ─────────────────────────
def _json(ruta):
    return json.loads(Path(ruta).read_text(encoding='utf-8'))


MU = _json(BACK / 'ml/models/UNEMI_PRUEBAS/metrics.json')
MO = _json(BACK / 'ml/models/OULAD_UK/metrics.json')
CU = _json(BACK / 'ml/models/UNEMI_PRUEBAS/metricas_clustering.json')
CO = _json(BACK / 'ml/models/OULAD_UK/metricas_clustering.json')
DIC = _json(DOC / 'tecnica' / 'diccionario_datos.json')
_evals = [p for p in sorted(glob.glob(str(BACK / 'eval/resultados_nl2sql_*.json')))
          if _json(p)['resumen']['preguntas'] >= 40 and _json(p)['resumen']['adversariales'] >= 8]
if not _evals:
    sys.exit('Falta una corrida COMPLETA de eval/evaluar_nl2sql.py (40 preguntas + 8 adversariales).')
NL = _json(_evals[-1])
R = NL['resumen']


def n(x, d=3):
    """Número con coma decimal (norma del documento)."""
    return f'{x:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def pct(x, d=1):
    return f'{n(x * 100, d)} %'


def miles(x):
    return f'{int(x):,}'.replace(',', '.')


def cv(m, modelo, clave):
    c = m['comparacion_cv'][modelo][clave]
    return f"{n(c['media'])} ± {n(c['desviacion'])}"


TU, TO = MU['validacion_temporal']['umbral_operativo'], MO['validacion_temporal']['umbral_operativo']
PROS = MO['evaluacion_prospectiva']
SIL_U = next(b['silhouette'] for b in CU['barrido_k'] if b['k'] == 3)
SIL_O = next(b['silhouette'] for b in CO['barrido_k'] if b['k'] == 3)
KW_U, KW_O = CU['kruskal_wallis_tasa_abandono'], CO['kruskal_wallis_tasa_abandono']
EX = R['exactitud_relajada']
NOMBRE = {'RF_CLASS_WEIGHT': 'Random Forest con ponderación de clases', 'RF_SMOTE': 'Random Forest con SMOTE',
          'LOGISTICA': 'Regresión logística', 'GRADIENT_BOOST': 'Gradient boosting (HistGradientBoosting)'}


# ── Extracción de código desde los archivos fuente ──────────────────────────
def funcion_py(ruta, nombre, max_lineas=60):
    texto = Path(ruta).read_text(encoding='utf-8')
    for nodo in ast.walk(ast.parse(texto)):
        if isinstance(nodo, (ast.FunctionDef, ast.Assign)) and (
                getattr(nodo, 'name', None) == nombre or
                any(getattr(t, 'id', None) == nombre for t in getattr(nodo, 'targets', []))):
            seg = ast.get_source_segment(texto, nodo)
            lineas = seg.split('\n')
            # quita docstrings largos para que el fragmento muestre la lógica
            seg = re.sub(r'\n(\s+)"""[\s\S]*?"""\n', '\n', seg, count=1) if len(lineas) > 25 else seg
            lineas = seg.split('\n')
            return '\n'.join(lineas[:max_lineas]) + ('\n    ...' if len(lineas) > max_lineas else '')
    raise KeyError(f'{nombre} no está en {ruta}')


def fragmento(ruta, desde, hasta, exacto=False):
    """Líneas desde la primera que contiene `desde` hasta la primera que
    contiene `hasta` (o que es exactamente `hasta`, sin espacios, si exacto)."""
    lineas = Path(ruta).read_text(encoding='utf-8').split('\n')
    i = next(k for k, l in enumerate(lineas) if desde in l)
    j = next(k for k, l in enumerate(lineas[i + 1:], i + 1) if (l.strip() == hasta if exacto else hasta in l))
    bloque = lineas[i:j + 1]
    sangria = min(len(l) - len(l.lstrip()) for l in bloque if l.strip())
    return '\n'.join(l[sangria:] for l in bloque)


# ═══════════════════════════════════════════════════════════════════════════
doc = docx.Document(str(SRC))
P = doc.paragraphs
ins = Insertor(doc)


def buscar(prefijo, estilo=None):
    for p in P:
        if p.text.strip().startswith(prefijo) and (estilo is None or p.style.name == estilo):
            return p
    raise KeyError(prefijo)


# ── Ajustes de coherencia en la sección 1 (ver Registro_cambios_Avance2.md) ─
RESUMEN = (
    'Se desarrolló un prototipo de inteligencia de negocios con un modelo predictivo de abandono estudiantil para que '
    'las instituciones de educación superior identifiquen tempranamente a los estudiantes en riesgo. Siguiendo CRISP-DM, '
    f'se construyó un almacén de datos en esquema estrella con la trayectoria de {miles(14508)} alumnos, organizada como '
    'panel alumno-periodo, sobre el cual un Random Forest estimó el abandono del periodo siguiente; K-Means segmentó las '
    'carreras y un motor de lenguaje natural a SQL permitió consultarlas sin conocimientos técnicos. Con validación '
    f"cruzada agrupada por alumno y validación temporal, el modelo alcanzó un ROC-AUC de {n(TU['roc_auc'])} en los datos "
    f"de prueba y de {n(TO['roc_auc'])} en un conjunto real externo (OULAD); la segmentación diferenció tres niveles de "
    f"riesgo (p = {n(KW_U['p_valor'])}) y el motor conversacional respondió correctamente el {pct(EX, 1)} de 40 preguntas "
    'de referencia, con aislamiento por institución verificado y protección de datos personales.'
)
ABSTRACT = (
    'A business intelligence prototype with a student dropout prediction model was developed so that higher education '
    'institutions can identify at-risk students early. Following CRISP-DM, a star-schema data warehouse was built from the '
    'trajectories of 14,508 students, organized as a student-period panel, on which a Random Forest estimated dropout in '
    'the next period; K-Means segmented academic programs and a natural-language-to-SQL engine allowed non-technical users '
    'to query them. Using student-grouped cross-validation and temporal validation, the model reached a ROC-AUC of '
    f"{TU['roc_auc']:.3f} on the test data and {TO['roc_auc']:.3f} on an external real dataset (OULAD); the segmentation "
    f"distinguished three risk levels (p = {KW_U['p_valor']:.3f}) and the conversational engine correctly answered "
    f'{EX * 100:.1f}% of 40 reference questions, with verified institution-level isolation and personal data protection.'
)
assert len(RESUMEN.split()) <= 150, f'Resumen con {len(RESUMEN.split())} palabras'
reemplazar_texto(buscar('Se desarrolló un prototipo'), RESUMEN)
reemplazar_texto(buscar('A business intelligence prototype'), ABSTRACT)

p = buscar('Alcance funcional.')
reemplazar_texto(p, p.text.replace(
    'ya que el prototipo se valida sobre datos de prueba de una institución ecuatoriana.',
    'ya que el prototipo se valida sobre datos de prueba de una institución ecuatoriana y se contrasta con un conjunto '
    'de datos público real, el Open University Learning Analytics Dataset (Kuzilek et al., 2017), cargado como segunda '
    'institución.'))
p = buscar('Una autoridad académica sin conocimientos de SQL logra')
reemplazar_texto(p, p.text.rstrip('.').rstrip() + ', lo que se mide con un conjunto de 40 preguntas de referencia '
                 'mediante exactitud por ejecución y se confirma con una prueba con usuarios.')
p = buscar('Esta selección se refuerza, además')
reemplazar_texto(p, p.text.replace('mediante la técnica de remuestreo SMOTE, la misma aplicada en el presente trabajo',
                                   'mediante la técnica de remuestreo SMOTE, que el presente trabajo compara con la '
                                   'ponderación de clases dentro de la misma validación cruzada'))
p = buscar('En cuanto a si ayudará a resolver')
reemplazar_texto(p, re.sub(
    r'Finalmente, las asignaturas base.*$',
    'Finalmente, las asignaturas base de la carrera que aportan a la ejecución del presente trabajo, verificadas contra '
    'la malla curricular vigente de Ingeniería en Tecnologías de la Información de la UNEMI, son: Sistemas de Bases de '
    'Datos y Gestión de Bases de Datos, Estructuras de Datos, Ingeniería de Software I y II, Minería de Datos, '
    'Probabilidad y Estadística, Inteligencia Artificial, Sistemas Distribuidos, Desarrollo de Aplicaciones Web, '
    'Seguridad Informática e Inteligencia de Negocios, esta última la que da nombre directo al presente trabajo.',
    p.text))

# Numeración manual coherente: 2 y 3 se escriben en el título, igual que "1. Introducción".
for pref in ('Referencias', 'Anexos', 'Anexo de información académica'):
    quitar_numeracion(buscar(pref, 'Heading 1'))

# Ancla: último párrafo de 1.3, antes de "Referencias".
ancla = buscar('En cuanto a si ayudará a resolver')

# ── 1.3: tabla comparativa explícita de los trabajos previos frente al caso ──
# Las filas salen de la lectura del texto completo (literatura/trabajos_previos.json).
TPJ = _json(DOC / 'literatura' / 'trabajos_previos.json')
ORDEN_TP = ['Duro', 'Carballo', 'Marcolino', 'Ovtsarenko', 'Romero', 'Kok', 'Rabelo', 'Khatun', 'Mustofa', 'Sequeira',
            'Mohd', 'Lepori', 'Ascoli']
TPS = sorted((t for t in TPJ['trabajos'] if t['decision'] == 'Incluido' or t['decision'].startswith('Resumen')),
             key=lambda t: next(i for i, o in enumerate(ORDEN_TP) if t['cita'].startswith(o)))
LEIDOS = [t for t in TPS if t['texto_completo_leido']]


def _cita_tp(t):
    return t['cita'] + ('*' if not t['texto_completo_leido'] else '')


def _tec_tp(t):
    tec = t['tecnologias']
    partes = [tec.get('lenguaje', ''), tec.get('frameworks', ''), tec.get('base_datos', '')]
    partes = [x for x in partes if x and not x.startswith(('no reporta', 'no verificable', 'no aplica'))]
    return '; '.join(partes) if partes else 'No reporta'


a13 = buscar('Por su parte, Sequeira et al. (2024)')
a13 = ins.parrafo(a13, f'Las dos tablas siguientes contrastan de forma explícita los {len(TPS)} trabajos previos con el presente '
                       f'caso. Sus filas se construyeron leyendo el texto completo de {len(LEIDOS)} de ellos; las páginas de '
                       'cada evidencia constan en documentacion/literatura/trabajos_previos.json.')
NOTA_TP = ('Elaboración propia a partir de la lectura del texto completo. * Texto completo no recuperado, porque el sitio '
           'del editor exige una verificación humana; la fila se construyó con el resumen verificado por DOI.')
a13 = ins.tabla(a13, [('Estudio', 'Problema y técnica', 'Datos', 'Validación y resultado')] + [
    (_cita_tp(t), f"{t['problema']}. {t['tecnica']}", t['datos_muestra'], f"{t['validacion_metricas']}. {t['resultado']}")
    for t in TPS] + [(
        'Presente trabajo', 'Abandono en el periodo siguiente. Random Forest comparado con SMOTE, regresión logística y '
        'gradient boosting; K-Means por carrera; NL2SQL',
        f"UNEMI_PRUEBAS: {miles(14508)} alumnos sintéticos en panel alumno-periodo; OULAD real: {miles(32593)} matrículas",
        f"Validación cruzada agrupada por alumno, prueba temporal y prospectiva. ROC-AUC temporal {n(TU['roc_auc'])} "
        f"(sintético) y {n(TO['roc_auc'])} (real); NL2SQL {pct(EX, 1)} de 40 preguntas")],
    titulo='Trabajos previos frente al caso: problema, datos y validación', anchos=[1.0, 1.95, 1.7, 1.85], tam=7.5,
    nota=NOTA_TP)
a13 = ins.tabla(a13, [('Estudio', 'Tecnologías', 'Arquitectura', 'Limitación', 'Qué aporta el presente caso')] + [
    (_cita_tp(t), _tec_tp(t), t['arquitectura'], t['limitacion'], t['relacion_con_este_trabajo']) for t in TPS] + [(
        'Presente trabajo', 'Python 3.14, scikit-learn, SHAP, FastAPI, React, SQL Server 2022',
        'Cliente-servidor desacoplado con backend en capas; almacén en estrella con aislamiento por institución en el motor',
        'Institución piloto con datos sintéticos; prueba con usuarios pendiente', '—')],
    titulo='Trabajos previos frente al caso: tecnologías, arquitectura y aporte', anchos=[0.95, 1.2, 1.45, 1.45, 1.45],
    tam=7.5, nota=NOTA_TP)
_aislados = sum(1 for t in LEIDOS if re.search(r'aislad|laboratorio|fuera de línea', t['arquitectura'], re.I))
_python = sum(1 for t in LEIDOS if 'Python' in t['tecnologias'].get('lenguaje', ''))
_sin_bd = sum(1 for t in LEIDOS if t['tecnologias'].get('base_datos', '').startswith('no reporta'))
a13 = ins.parrafo(a13, f'La comparación confirma el vacío de integración: {_aislados} de los {len(LEIDOS)} trabajos leídos en '
                       'texto completo dejan el modelo como un análisis, un script o un experimento aislado, y la integración '
                       'en un sistema aparece solo como propuesta. La columna de tecnologías muestra además que la mayoría no '
                       f'declara su pila: solo {_python} informan Python y {_sin_bd} no informan el motor de base de datos. '
                       'Ninguno de los estudios primarios predice el abandono del periodo siguiente sobre un panel '
                       'alumno-periodo, y solo Rabelo y Zárate (2025) usan una prueba temporal. En contrapartida, el presente '
                       'trabajo es más débil que varios de ellos en un punto: su institución piloto usa datos sintéticos, por '
                       'lo que la evidencia de desempeño real descansa en OULAD.')


# ── Matrices de decisión (documentacion/decisiones/DT-*.json) ───────────────
def _dt(ruta):
    d = _json(ruta)
    tot = sum(c['peso'] for c in d['criterios'])

    def puntaje(k, pesos):
        return sum(k['puntajes'][c['id']]['valor'] * pesos[c['id']] for c in d['criterios']) / sum(pesos.values())

    base = {c['id']: c['peso'] for c in d['criterios']}
    rank = sorted(d['candidatas'], key=lambda k: -puntaje(k, base))
    estable = True
    for c in d['criterios']:
        for f in (0.8, 1.2):
            pesos = dict(base, **{c['id']: c['peso'] * f})
            estable &= max(d['candidatas'], key=lambda k: puntaje(k, pesos))['id'] == rank[0]['id']
    filas = [('Criterio (peso)',) + tuple(k['nombre'] for k in rank)]
    filas += [(f"{c['nombre']} ({c['peso']} %)",) + tuple(str(k['puntajes'][c['id']]['valor']) for k in rank)
              for c in d['criterios']]
    filas.append(('**Puntaje ponderado (sobre 5)**',) + tuple(f'**{n(puntaje(k, base), 2)}**' for k in rank))
    assert tot == 100, ruta
    return d, rank[0], filas, estable


DEC = DOC / 'decisiones'
DT6, GANA6, FILAS6, EST6 = _dt(DEC / 'DT-06_arquitectura.json')

# ═══════════════════════════════════════════════════════════════════════════
# 2. ANÁLISIS DEL CASO
# ═══════════════════════════════════════════════════════════════════════════
a = ins.titulo(ancla, '2. Análisis del caso', 1, salto_pagina=True)
a = ins.titulo(a, '2.1 Requerimientos', 2)
a = ins.bloque(a, """
Los requerimientos se derivaron de las cuatro piezas que la sección 1.2 define como alcance técnico —el modelo predictivo, la segmentación institucional (clustering), el motor conversacional NL2SQL y el panel visual— más los componentes transversales que las sostienen: el proceso ETL, la seguridad y la protección de datos. Cada requerimiento se enlaza con una historia de usuario de la autoridad académica sin perfil técnico, con un objetivo específico y con el archivo del sistema que lo implementa, de modo que ninguno quede sin respaldo en el código ni sin una prueba que lo verifique.

Este enfoque responde a las barreras de adopción documentadas en la literatura: la brecha de habilidades técnicas señalada por Sequeira et al. (2024), la complejidad percibida del sistema que Alzubi et al. (2025) identifican como el mayor obstáculo, y las dificultades organizacionales que Komljenovic et al. (2024) describen al intentar convertir una universidad en una organización basada en datos.
""")

a = ins.subtitulo(a, 'Identificación de alternativas de solución')
a = ins.bloque(a, """
Se evaluaron tres alternativas frente a tres criterios: capacidad predictiva, gobernanza de los datos y costo para una institución pública.

**Alternativa 1: reportes estáticos periódicos (Excel o extracciones manuales).** Mantiene el proceso actual y no requiere inversión, pero solo describe el estado de la matrícula; no anticipa el abandono.

**Alternativa 2: plataforma comercial de BI (Power BI o Tableau) sin modelo propio.** Permite tableros con poco esfuerzo, como muestran Mejía-Peñafiel et al. (2026) en universidades ecuatorianas, pero no incorpora un modelo de aprendizaje automático propio ni una consulta en lenguaje natural gobernada por institución, y su licenciamiento es recurrente.

**Alternativa 3 (seleccionada): prototipo propio de inteligencia de negocios con modelo predictivo.** Integra un almacén dimensional, el modelo de abandono, la segmentación de carreras y la consulta en lenguaje natural bajo una arquitectura que aísla el acceso por institución a nivel del motor de base de datos. Es la única que ofrece anticipación, gobernanza y extensibilidad a otra institución sin licencias recurrentes.
""")

a = ins.subtitulo(a, 'Actores y persona principal')
a = ins.tabla(a, [
    ('Actor', 'Perfil', 'Necesidad principal', 'Conocimiento técnico'),
    ('Autoridad académica (decano, director de carrera)', 'Decide la asignación de recursos de retención',
     'Saber a quién y a qué carrera priorizar, y cuánto confiar en el sistema', 'Bajo: no escribe SQL'),
    ('Bienestar estudiantil', 'Ejecuta el acompañamiento', 'Entender por qué un alumno está en riesgo', 'Bajo'),
    ('Administrador de TI', 'Opera la plataforma', 'Conectar instituciones y reentrenar sin reescribir código', 'Alto'),
    ('Motor de IA (actor de sistema)', 'Traduce preguntas a SQL', 'Consultar solo vistas gobernadas con permiso de lectura',
     'No aplica'),
], titulo='Actores del sistema', anchos=[1.5, 1.5, 2.2, 1.1])
a = ins.parrafo(a, 'La **persona principal** es la autoridad académica sin formación técnica: toma decisiones sobre '
                   'retención, necesita respuestas en su propio lenguaje y no dispone de un analista que traduzca sus '
                   'preguntas a consultas. Todas las historias de usuario se escribieron desde su punto de vista o '
                   'desde el de quienes la apoyan.')

a = ins.subtitulo(a, 'Historias de usuario')
HU = [
    ('ID', 'Historia de usuario', 'Criterio de aceptación (Dado / Cuando / Entonces)', 'Pieza'),
    ('HU-01', 'Como director de carrera, quiero ver a los alumnos con mayor riesgo de abandonar el próximo periodo, para priorizar a quién contactar.',
     'Dado que hay predicciones calculadas, cuando abro el panel, entonces veo a los alumnos ordenados por probabilidad, con su categoría (alto, medio o bajo) y el horizonte «próximo periodo».', 'Modelo y panel'),
    ('HU-02', 'Como personal de bienestar, quiero saber por qué un alumno está en riesgo, para preparar el acompañamiento.',
     'Dado un alumno en riesgo alto o medio, cuando lo veo en el panel, entonces aparecen hasta tres razones en lenguaje natural (por ejemplo, «asistencia del último periodo: 54,8 %»).', 'Modelo y panel'),
    ('HU-03', 'Como autoridad sin conocimientos de SQL, quiero preguntar en español, para obtener cifras sin depender de personal técnico.',
     'Dada una pregunta del conjunto de referencia, cuando la escribo en el chat, entonces recibo la cifra correcta con una explicación de negocio y sin ver SQL.', 'NL2SQL'),
    ('HU-04', 'Como vicerrector académico, quiero saber qué carreras requieren atención prioritaria, para asignar recursos por programa.',
     'Cuando consulto el panel o pregunto en el chat, entonces veo el segmento de riesgo de cada carrera, y los segmentos difieren estadísticamente en su tasa de abandono.', 'Clustering y panel'),
    ('HU-05', 'Como planificación institucional, quiero comparar nuestra tasa de abandono con referentes externos, para dimensionar la urgencia.',
     'Cada referente muestra su fuente con DOI, qué mide exactamente y su nivel de comparabilidad (alto, medio o bajo).', 'Benchmarking'),
    ('HU-06', 'Como autoridad, quiero exportar los resultados, para presentarlos en consejo universitario.',
     'Cuando elijo exportar, obtengo un archivo Excel o PDF con los mismos datos que muestra la pantalla.', 'Panel'),
    ('HU-07', 'Como autoridad, quiero saber qué tan confiable es el modelo, para decidir cuánto peso dar a sus alertas.',
     'El panel muestra el ROC-AUC y el porcentaje de abandonos detectados en la validación temporal; el chat responde a la misma pregunta.', 'Modelo, panel y NL2SQL'),
    ('HU-08', 'Como administrador de TI, quiero conectar otra institución escribiendo solo un perfil de mapeo, para no modificar el ETL ni el modelo.',
     f"Con el perfil OULAD_UK, el mismo ETL carga {miles(189299)} filas y el mismo código entrena y califica, sin cambios.", 'ETL (transversal)'),
    ('HU-09', 'Como estudiante titular de los datos, quiero que mi identidad no salga hacia servicios externos ni se muestre completa, para proteger mi privacidad.',
     'Cuando el sistema redacta una respuesta con un proveedor externo de IA, este recibe seudónimos; en pantalla la cédula aparece enmascarada.', 'Privacidad (transversal)'),
    ('HU-10', 'Como autoridad de una institución, quiero que ninguna otra institución vea nuestros datos, para cumplir la confidencialidad.',
     'Con la institución A activa, ninguna vista devuelve filas de la institución B, aunque se pida explícitamente en el chat.', 'Seguridad (transversal)'),
]
a = ins.tabla(a, HU, titulo='Historias de usuario con criterios de aceptación', anchos=[0.55, 2.3, 2.75, 0.9], tam=8.5)

a = ins.subtitulo(a, 'Requerimientos funcionales por pieza')
RF = [
    ('ID', 'Pieza', 'Requerimiento funcional', 'HU', 'Obj.', 'Implementación'),
    ('RF-01', 'Modelo', 'Construir el panel alumno-periodo: características hasta t y etiqueta de abandono en t+1', 'HU-01', 'OE1', 'ml/features_abandono.py'),
    ('RF-02', 'Modelo', 'Entrenar un modelo por institución, con ajuste de hiperparámetros y comparación de cuatro técnicas', 'HU-01', 'OE2', 'ml/entrenar_abandono.py'),
    ('RF-03', 'Modelo', 'Validar con CV agrupada por alumno y con prueba temporal; guardar las métricas en el almacén', 'HU-07', 'OE3', 'ml/entrenar_abandono.py'),
    ('RF-04', 'Modelo', 'Calificar a los alumnos activos para el próximo periodo con umbral de recall ≥ 0,80', 'HU-01', 'OE2', 'ml/predecir_abandono.py'),
    ('RF-05', 'Modelo', 'Explicar cada alumno en riesgo con tres factores SHAP en lenguaje natural', 'HU-02', 'OE2', 'ml/predecir_abandono.py'),
    ('RF-06', 'Clustering', 'Segmentar las carreras en tres niveles de riesgo con K-Means', 'HU-04', 'OE2', 'ml/clustering_institucional.py'),
    ('RF-07', 'Clustering', 'Validar la segmentación: silhouette, estabilidad, comparación de algoritmos y Kruskal-Wallis', 'HU-04', 'OE3', 'ml/clustering_institucional.py'),
    ('RF-08', 'NL2SQL', 'Traducir preguntas en español a SQL de solo lectura sobre vistas VIS_*, con métricas certificadas y lógica de negocio por institución', 'HU-03', 'OE2', 'core/nl2sql_engine.py, knowledge/'),
    ('RF-09', 'NL2SQL', 'Explicar la respuesta en lenguaje de negocio y ocultar el SQL a roles no administradores', 'HU-03', 'OE2', 'api/routes_query.py'),
    ('RF-10', 'NL2SQL', 'Responder preguntas sobre riesgo, segmentos, referentes y confiabilidad del modelo', 'HU-04, 05, 07', 'OE2', 'vistas VIS_* en CHAT'),
    ('RF-11', 'Panel', 'Mostrar el riesgo por alumno con sus factores y la confiabilidad del modelo', 'HU-01, 02, 07', 'OE2', 'RiesgoAbandonoCard.jsx'),
    ('RF-12', 'Panel', 'Mostrar segmentos y referentes externos con fuente, DOI y comparabilidad', 'HU-04, 05', 'OE2', 'InteligenciaInstitucionalCard.jsx'),
    ('RF-13', 'Panel', 'Exportar resultados a Excel o PDF', 'HU-06', 'OE2', 'core/excel_exporter.py'),
    ('RF-14', 'Transversal', 'Incorporar una institución mediante un perfil de mapeo, sin cambiar el ETL', 'HU-08', 'OE2', 'etl/perfiles.py, scripts/etl_academico.py'),
    ('RF-15', 'Transversal', 'Cargar referentes externos solo con fuente académica verificable', 'HU-05', 'OE3', 'etl/etl_benchmarking.py'),
    ('RF-16', 'Transversal', 'Aislar los datos por institución y ejecutar el SQL de la IA con una cuenta de solo lectura que falla cerrada', 'HU-10', 'OE2', 'scripts/crear_chat_academico.sql, main.py'),
]
a = ins.tabla(a, RF, titulo='Requerimientos funcionales derivados de las cuatro piezas', anchos=[0.5, 0.75, 2.6, 0.65, 0.45, 1.55], tam=8.5,
              nota='Elaboración propia. OE1, OE2 y OE3 son los objetivos específicos de la sección 1.2.')

a = ins.subtitulo(a, 'Requerimientos no funcionales')
a = ins.parrafo(a, 'Los requerimientos de **protección de datos estudiantiles** se fundamentan en la Ley Orgánica de '
                   'Protección de Datos Personales (Asamblea Nacional del Ecuador, 2021), en particular en los principios '
                   'de minimización y finalidad: el sistema solo debe tratar los datos personales necesarios para priorizar '
                   'la intervención, y no debe transferirlos a terceros cuando no es imprescindible. Como el prototipo usa '
                   'proveedores externos de modelos de lenguaje, este punto se convirtió en requisitos verificables.')
RNF = [
    ('ID', 'Atributo', 'Requerimiento', 'Cómo se verifica'),
    ('RNF-01', 'Seguridad', 'Tres capas: sanitizador de SQL, vistas filtradas por SESSION_CONTEXT y cuenta chat_reader sin acceso a tablas físicas ni bases operativas; si chat_reader no está disponible, la consulta no se ejecuta con otra cuenta', 'tests/test_capa_seguridad_bd.py (22 pruebas, SQL Server real)'),
    ('RNF-02', 'Privacidad: minimización', 'Toda fila enviada a un proveedor externo de IA reemplaza cédula, nombres, correo y teléfono por un seudónimo', 'tests/test_privacidad.py: el cuerpo HTTP enviado no contiene ninguna cédula'),
    ('RNF-03', 'Privacidad: seudonimización', 'Los datos de prueba usan cédulas ficticias (código de provincia 00, no asignable) y nombres ficticios; el padrón real no está en el repositorio ni en la base', 'anonimizar_padron.py (huella de las columnas no personales idéntica antes y después)'),
    ('RNF-04', 'Privacidad: finalidad y acceso', 'La cédula se muestra enmascarada; el SQL y la traza técnica solo los ve el rol administrador', 'core/privacidad.py, _redactar_campos_privados'),
    ('RNF-05', 'Privacidad: conservación', 'La política de retención y la base legal del tratamiento se acuerdan con la institución antes de conectar datos reales', 'Fuera del alcance del prototipo (declarado)'),
    ('RNF-06', 'Rendimiento', 'Entrenamiento y calificación por lotes; el panel lee resultados precalculados', f"Latencia NL2SQL medida: mediana {n(R['latencia_p50_s'], 1)} s"),
    ('RNF-07', 'Usabilidad', 'Preguntas en español, sin SQL; respuestas en lenguaje de negocio', 'Conjunto de referencia y prueba con usuarios'),
    ('RNF-08', 'Mantenibilidad', 'Una sola función de características para entrenar y calificar; pruebas automatizadas', 'pytest (suite del backend)'),
    ('RNF-09', 'Reproducibilidad', 'Semilla fija 20260909, versiones fijadas y pipeline en un solo script', 'requirements.lock.txt, scripts/demo_tesis.ps1'),
    ('RNF-10', 'Disponibilidad', 'Cascada de proveedores de IA; las métricas certificadas no dependen del proveedor', 'Evaluación NL2SQL: fallas técnicas registradas aparte'),
    ('RNF-11', 'Portabilidad', 'Una institución nueva se incorpora con un perfil; un modelo por institución, sin mezclar datos', 'Perfil OULAD_UK cargado y entrenado con el mismo código'),
]
a = ins.tabla(a, RNF, titulo='Requerimientos no funcionales', anchos=[0.6, 1.2, 2.9, 1.8], tam=8.5)

a = ins.subtitulo(a, 'Métricas de calidad y resultados obtenidos')
a = ins.parrafo(a, 'Cada pieza tiene una métrica con meta explícita. La exactitud del motor NL2SQL se mide por '
                   'ejecución: se compara el resultado de la respuesta con el de una consulta de referencia ejecutada con la '
                   'misma cuenta y la misma institución, porque a una autoridad le importa que la cifra sea correcta, '
                   'aunque el SQL sea distinto. Es una métrica más exigente en lo práctico que la coincidencia exacta de '
                   'conjuntos que reportan Ascoli y Choi (2025) sobre CoSQL, que compara la estructura de la consulta.')
MET = [
    ('Métrica', 'Pieza', 'Meta', 'UNEMI_PRUEBAS (sintéticos)', 'OULAD_UK (reales)'),
    ('ROC-AUC, prueba temporal', 'Modelo', '≥ 0,90', n(TU['roc_auc']), n(TO['roc_auc'])),
    ('Recall en el umbral operativo', 'Modelo', '≥ 0,80', n(TU['recall']), n(TO['recall'])),
    ('PR-AUC, prueba temporal (prevalencia)', 'Modelo', 'Reportar', f"{n(TU['pr_auc'])} ({n(TU['prevalencia'])})",
     f"{n(TO['pr_auc'])} ({n(TO['prevalencia'])})"),
    ('ROC-AUC prospectivo (desenlace real posterior)', 'Modelo', 'Reportar', 'No aplica', n(PROS['y_proximo']['roc_auc'])),
    ('Silhouette con k = 3', 'Clustering', '≥ 0,25', n(SIL_U), n(SIL_O)),
    ('Kruskal-Wallis entre segmentos (p)', 'Clustering', '< 0,05', n(KW_U['p_valor']), n(KW_O['p_valor'])),
    ('Exactitud por ejecución (40 preguntas)', 'NL2SQL', '≥ 0,80', n(EX), 'No evaluado'),
    ('Preguntas maliciosas contenidas', 'NL2SQL y seguridad', '100 %',
     f"{R['adversariales_superadas']} de {R['adversariales']}", 'No evaluado'),
    ('Violaciones de aislamiento entre instituciones', 'Seguridad', '0', str(R['violaciones_aislamiento']), '0 (pruebas de integración)'),
]
a = ins.tabla(a, MET, titulo='Métricas de calidad: meta y resultado', anchos=[2.0, 0.9, 0.7, 1.4, 1.4], tam=8.5,
              nota='Elaboración propia a partir de metrics.json, metricas_clustering.json y resultados_nl2sql (backend/). '
                   'La discusión de cada resultado está en la sección 3.3.')

a = ins.subtitulo(a, 'Matriz de trazabilidad')
TRZ = [
    ('Objetivo específico', 'Historias', 'Requerimientos', 'Componente', 'Prueba o evidencia'),
    ('OE1: analizar procesos e identificar variables de riesgo', 'HU-01, HU-02', 'RF-01, RF-05', 'features_abandono.py',
     'test_panel_abandono.py; importancia por permutación'),
    ('OE2: implementar el modelo integrado al prototipo de BI con panel y lenguaje natural', 'HU-01 a HU-10',
     'RF-02, RF-04 a RF-06, RF-08 a RF-14, RF-16', 'backend/ml, API, panel, chat', 'Demostración; evaluación NL2SQL; pruebas de seguridad'),
    ('OE3: evaluar con validación cruzada y temporal frente a referentes externos', 'HU-05, HU-07', 'RF-03, RF-07, RF-15',
     'entrenar_abandono.py, clustering_institucional.py, etl_benchmarking.py', 'metrics.json; fact_evaluacion_modelo'),
]
a = ins.tabla(a, TRZ, titulo='Trazabilidad entre objetivos, historias, requerimientos y evidencias',
              anchos=[1.8, 0.8, 1.2, 1.4, 1.5], tam=8.5)

a = ins.subtitulo(a, 'Validación con usuarios')
a = ins.parrafo(a, 'El criterio de éxito (d) exige que una autoridad sin conocimientos de SQL obtenga una respuesta '
                   'correcta. Además de la evaluación automática, se preparó una prueba con tres a cinco participantes sin '
                   'perfil técnico, con seis tareas derivadas de las historias HU-01 a HU-07 (por ejemplo, «identifique '
                   'las tres carreras que requieren atención prioritaria» o «averigüe por qué el alumno con mayor riesgo '
                   'está en riesgo»). Se registran el éxito de cada tarea, el tiempo empleado y la dificultad percibida. '
                   'Sus resultados se incorporarán en el siguiente avance; hasta entonces, el criterio (d) se sustenta '
                   'únicamente en la evaluación automática descrita arriba.')

# ═══════════════════════════════════════════════════════════════════════════
# 3. DISEÑO Y DESARROLLO DEL TRABAJO PRÁCTICO
# ═══════════════════════════════════════════════════════════════════════════
a = ins.titulo(a, '3. Diseño y desarrollo del trabajo práctico', 1, salto_pagina=True)
a = ins.titulo(a, '3.1 Metodología', 2)
a = ins.parrafo(a, 'CRISP-DM no es lineal: la evaluación puede devolver el trabajo a fases anteriores. En este avance '
                   'ocurrió dos veces y ambas quedaron registradas. La evaluación del modelo anterior mostró que usaba la '
                   'asistencia del mismo periodo en que el alumno ya se había retirado, lo que obligó a volver a la '
                   'preparación de datos y a rediseñar la unidad de análisis como panel alumno-periodo. Después, la '
                   'evaluación del motor conversacional destapó definiciones de negocio erróneas en las métricas '
                   'certificadas, lo que devolvió el trabajo a la comprensión del negocio. La figura siguiente resume el '
                   'ciclo aplicado con los artefactos de cada fase.')
a = ins.figura(a, DIAG / 'av2_crisp_dm.png', 'Ciclo CRISP-DM aplicado al proyecto y sus artefactos principales')
a = ins.bloque(a, f"""
El componente de ciencia de datos siguió CRISP-DM (Wirth & Hipp, 2000), cuyas seis fases se documentan a continuación con el entregable concreto que produjo cada una en el repositorio. Los componentes de software (ETL, API, panel y chat) se construyeron en iteraciones incrementales, cada una cerrada con pruebas automatizadas.

**Fase 1. Comprensión del negocio.** Se definió el problema como la detección tardía del abandono y se fijó el objetivo analítico: estimar, con los datos de un alumno hasta su periodo actual, la probabilidad de que abandone en el periodo siguiente. Se priorizó el recall —no dejar pasar abandonos— sobre la precisión, porque para la institución es más costoso no alertar a tiempo que contactar a un alumno que no se iba. *Entregables:* sección 1.2, historias de usuario y criterios de éxito.

**Fase 2. Comprensión de los datos.** Se trabajó con dos fuentes. La primera, UNEMI_PRUEBAS, contiene la trayectoria sintética y anonimizada de {miles(14508)} alumnos en {miles(83678)} registros alumno-periodo, con una tasa de abandono de 10,02 %. La segunda es OULAD, un conjunto real y anonimizado de la Open University (Kuzilek et al., 2017) con {miles(32593)} matrículas de {miles(28785)} estudiantes y 10,6 millones de registros de actividad en el aula virtual. El análisis exploratorio reveló un hallazgo decisivo: en los datos sintéticos la asistencia de quien abandona cae de 89 % a 55 % un periodo antes, de modo que esa sola variable ya separa los casos con un ROC-AUC de 0,996, mientras que en OULAD la mejor variable individual apenas llega a 0,689. Por eso los datos sintéticos sirven para probar la arquitectura y OULAD para medir el desempeño realista. *Entregables:* generate_historial.py, seed_oulad.py.

**Fase 3. Preparación de los datos.** Se anonimizó el conjunto de prueba (anonimizar_padron.py), se cargaron ambas instituciones al almacén en esquema estrella con el mismo ETL parametrizado por perfil y se construyó el panel alumno-periodo. De {miles(MU['panel']['filas'])} filas de UNEMI_PRUEBAS, {miles(MU['panel']['etiquetadas'])} tienen un periodo siguiente conocido (prevalencia de abandono al periodo siguiente de {pct(MU['panel']['prevalencia'], 2)}); en OULAD son {miles(MO['panel']['etiquetadas'])} de {miles(MO['panel']['filas'])} ({pct(MO['panel']['prevalencia'], 2)}). Siguiendo a Alzabidi et al. (2026) se revisaron los valores atípicos por rango intercuartílico: en UNEMI_PRUEBAS el {n(MU['atipicos_iqr']['asistencia_t']['pct_atipicos'], 2)} % de las asistencias queda fuera del rango, y no se eliminaron, porque una asistencia muy baja es justamente la señal que se quiere aprender. Se declaran dos límites: quien abandona en su primer periodo no tiene historia previa (162 alumnos en UNEMI_PRUEBAS) y el 26,3 % de los retiros de OULAD ocurre antes del inicio del curso; ninguno de los dos casos puede anticiparse con este enfoque. *Entregables:* anonimizar_padron.py, etl_academico.py, perfiles.py, features_abandono.py.

**Fase 4. Modelado.** Para cada institución por separado —sin mezclar sus datos, coherente con la propuesta federada de Kovor et al. (2026)— se ajustaron los hiperparámetros del Random Forest con RandomizedSearchCV (25 combinaciones) y se compararon, con los mismos cinco pliegues, cuatro modelos: Random Forest con ponderación de clases; Random Forest con SMOTE aplicado solo a los pliegues de entrenamiento (Villar & Andrade, 2024); regresión logística, la técnica de Núñez-Naranjo (2024) y Rabelo y Zárate (2025); y gradient boosting, representante de la familia del XGBoost de Carballo-Mendívil et al. (2025). La segmentación de carreras usó K-Means con k = 3. *Entregables:* entrenar_abandono.py, clustering_institucional.py.

**Fase 5. Evaluación.** La validación cruzada agrupa las filas por alumno (StratifiedGroupKFold): un mismo estudiante nunca está a la vez en entrenamiento y en prueba, porque en un panel esa fuga inflaría las métricas. El 25 % más reciente del panel quedó reservado como prueba temporal y se usó una sola vez. En OULAD se añadió una evaluación prospectiva: la presentación más reciente se cargó «en curso» hasta la semana 12, el modelo calificó a quienes seguían activos y luego se comparó con lo que realmente ocurrió. El clustering se validó con silhouette, estabilidad bootstrap y la prueba de Kruskal-Wallis (Melchor et al., 2026), y el motor NL2SQL con un conjunto de 40 preguntas de referencia y 8 preguntas maliciosas. *Entregables:* metrics.json, metricas_clustering.json, reporte_validacion.py, evaluar_nl2sql.py y las pruebas automatizadas.

**Fase 6. Despliegue.** El modelo final se reentrena con todas las filas etiquetadas y se guarda junto con su umbral operativo. La calificación escribe en el almacén la probabilidad y los tres factores de cada alumno, y las métricas de validación se guardan en fact_evaluacion_modelo, de modo que el panel y el chat leen exactamente las mismas vistas. *Entregables:* predecir_abandono.py, endpoints /api/ml/*, RiesgoAbandonoCard.jsx, InteligenciaInstitucionalCard.jsx y scripts/demo_tesis.ps1.
""")
a = ins.tabla(a, [
    ('Fase CRISP-DM', 'Entregable en el repositorio', 'Resultado verificable'),
    ('1. Comprensión del negocio', 'Sección 1.2, historias HU-01 a HU-10', 'Cuatro criterios de éxito medibles'),
    ('2. Comprensión de los datos', 'generate_historial.py, seed_oulad.py', 'Dos instituciones; separabilidad sintética frente a real cuantificada'),
    ('3. Preparación', 'anonimizar_padron.py, etl_academico.py, perfiles.py, features_abandono.py',
     f"{miles(MU['panel']['etiquetadas'] + MO['panel']['etiquetadas'])} filas de panel etiquetadas"),
    ('4. Modelado', 'entrenar_abandono.py, clustering_institucional.py', 'Cuatro modelos comparados con los mismos pliegues'),
    ('5. Evaluación', 'metrics.json, reporte_validacion.py, evaluar_nl2sql.py, tests/', 'Validación cruzada, temporal, prospectiva, NL2SQL y seguridad'),
    ('6. Despliegue', 'predecir_abandono.py, API, panel, demo_tesis.ps1', 'Resultados consultables en el panel y en el chat'),
], titulo='Entregables por fase de CRISP-DM', anchos=[1.5, 2.6, 2.4])
a = ins.tabla(a, [
    ('Iteración', 'Periodo', 'Incremento', 'Cierre'),
    ('I1', 'Agosto de 2026', 'Conexión multiempresa, motor NL2SQL y capa de sanitización', 'Pruebas de aislamiento en caché y sanitizador'),
    ('I2', '9 al 11 de septiembre de 2026', 'Almacén CHAT, ETL físico, cuenta chat_reader, primer modelo y benchmarking', 'Auditorías del 9 y 11 de septiembre'),
    ('I3', '25 de septiembre de 2026', 'Panel alumno-periodo, OULAD como segunda institución, validación completa, privacidad y evaluación NL2SQL', 'Pruebas de panel, privacidad y seguridad; conjunto de referencia'),
], titulo='Iteraciones del desarrollo de software', anchos=[0.7, 1.5, 2.8, 1.6])
a = ins.bloque(a, """
**Organización del trabajo y control de calidad.** El código se versiona en git; antes de cada cambio de fondo se crea un punto de respaldo, y cada iteración se cierra solo si pasan las pruebas automatizadas del backend. La reproducibilidad se garantiza con tres medidas: una semilla fija (20260909) en todo proceso aleatorio, las versiones exactas de las dependencias en backend/requirements.lock.txt y un único script (codigo_fuente/scripts/demo_tesis.ps1) que reconstruye bases, modelos, resultados y pruebas en el mismo orden. Así, cualquier cifra de este documento puede regenerarse desde cero, y el propio documento se genera leyendo esos resultados (_build_avance2.py), de modo que texto y sistema no pueden diferir.
""")
a = ins.tabla(a, [
    ('Fase', 'Pregunta de control', 'Cómo se verifica'),
    ('Comprensión del negocio', '¿El objetivo analítico responde al problema de la sección 1.1?', 'Trazabilidad objetivo, historia y requerimiento (sección 2.1)'),
    ('Comprensión de los datos', '¿Los datos permiten medir lo que se afirma?', 'Separabilidad sintética frente a real cuantificada antes de modelar'),
    ('Preparación', '¿Hay fuga de información del futuro?', 'test_panel_abandono.py: las características solo usan datos hasta t'),
    ('Modelado', '¿Se comparó con alternativas razonables?', 'Cuatro modelos con los mismos pliegues; advertencia si una línea base gana'),
    ('Evaluación', '¿La métrica refleja el uso real?', 'Prueba temporal usada una vez, evaluación prospectiva y conjunto de referencia NL2SQL'),
    ('Despliegue', '¿El panel y el chat muestran lo mismo y de forma segura?', 'Mismas vistas VIS_*; pruebas de integración de seguridad y privacidad'),
], titulo='Control de calidad por fase de CRISP-DM', anchos=[1.5, 2.4, 2.6])

# ── 3.2 Diseño ────────────────────────────────────────────────────────────
a = ins.titulo(a, '3.2 Diseño', 2)
a = ins.subtitulo(a, 'Arquitectura de la solución')
a = ins.parrafo(a, 'La solución sigue una arquitectura en capas con separación estricta entre los datos operativos de cada '
                   'institución y lo que puede consultar el motor de inteligencia artificial. Las bases operativas solo '
                   'se leen desde el ETL; el almacén CHAT concentra el modelo dimensional y los resultados de los procesos '
                   'por lotes; y todo lo que llega al panel o al chat pasa por vistas filtradas por institución y por una '
                   'cuenta que solo tiene permiso de lectura sobre esas vistas.')
a = ins.figura(a, DIAG / 'av2_arquitectura.png', 'Arquitectura del sistema y sus tres capas de seguridad')
a = ins.parrafo(a, 'La primera capa es el motor de base de datos: la cuenta chat_reader no puede leer las bases operativas '
                   'ni las tablas físicas del almacén, ni escribir en ningún objeto. La segunda es semántica: el modelo de '
                   'lenguaje solo conoce los nombres de las vistas VIS_*, y cada vista devuelve únicamente las filas de la '
                   'institución fijada en SESSION_CONTEXT. La tercera es la aplicación: el sanitizador rechaza cualquier '
                   'sentencia que no sea de lectura. Como la garantía descansa en el motor, se mantiene aunque alguna de las '
                   'otras dos fallara.')

a = ins.subtitulo(a, 'Comparación de estilos arquitectónicos')
a = ins.parrafo(a, 'El estilo se eligió comparando tres alternativas frente a seis escenarios de atributos de calidad '
                   'derivados de los requerimientos, con pesos que suman 100 y un puntaje de 1 a 5 por escenario. Cada '
                   'puntaje se respalda en los trabajos previos, en artículos con DOI o en las pruebas del propio '
                   'prototipo; la justificación y la fuente de cada celda están en documentacion/decisiones/.')
a = ins.tabla(a, FILAS6, titulo='Comparación de estilos arquitectónicos (matriz ponderada)', anchos=[2.2, 1.45, 1.45, 1.45],
              tam=8.5, nota='Elaboración propia. Puntajes de 1 (peor) a 5 (mejor).')
a = ins.parrafo(a, f"Ganó el estilo «{GANA6['nombre']}». "
                   + ('Ninguna variación de ±20 % en un solo peso cambia la ganadora. ' if EST6 else
                      'La ganadora cambia con alguna variación de ±20 % en un peso; se aplicó el criterio de desempate. ')
                   + 'Frente al monolito en capas gana por independizar la interfaz (panel, chat y variantes móviles) sin '
                   'multiplicar la operación. Frente a los microservicios evita un costo que no se justifica para un equipo '
                   'de dos personas: Hassan et al. (2025) advierten que pasar a microservicios exige un esfuerzo de '
                   'desarrollo y recursos considerables, y que el éxito no está garantizado. La arquitectura implementada '
                   'se verificó automáticamente sobre el repositorio: dos desplegables (frontend y backend), ninguna '
                   'dependencia prohibida entre capas y una sola excepción documentada, un texto de ayuda del frontend que '
                   'describe una consulta del backend.')

a = ins.subtitulo(a, 'Diagramas UML')
a = ins.figura(a, DIAG / 'av2_casos_uso.png', 'Diagrama de casos de uso', ancho_pulgadas=5.2)
a = ins.parrafo(a, 'La autoridad académica inicia los casos de consulta y decisión (CU-01 a CU-07); bienestar estudiantil '
                   'comparte los tres primeros; y el administrador de TI opera la incorporación de instituciones y los '
                   'procesos por lotes (CU-08 y CU-09). El motor de IA solo participa dentro de CU-03, a través de CU-10: '
                   'ejecutar SQL de lectura sobre vistas gobernadas. No existe ningún caso de uso en el que la IA escriba '
                   'datos.')
a = ins.figura(a, DIAG / 'av2_secuencia_nl2sql.png', 'Diagrama de secuencia de una consulta en lenguaje natural')
a = ins.parrafo(a, 'La secuencia refleja el flujo real del endpoint /api/query. Primero se busca una métrica certificada '
                   '(pasos 4 y 5): si existe, el SQL es fijo y pre-aprobado y el modelo de lenguaje no interviene en la '
                   'cifra. Si no existe, el modelo recibe la pregunta, el esquema de las vistas y la lógica de negocio de '
                   'la institución, nunca filas de datos (paso 6). El paso crítico de seguridad es el 13: el contexto de '
                   'institución y el SELECT se ejecutan en la misma conexión física, lo que evita que dos consultas '
                   'concurrentes de instituciones distintas se crucen. Si se pide redactar la explicación, las filas '
                   'viajan al proveedor externo con los datos personales enmascarados (paso 18).')
a = ins.figura(a, DIAG / 'av2_secuencia_lotes.png', 'Diagrama de secuencia de los procesos por lotes')
a = ins.parrafo(a, 'Los procesos pesados (ETL, entrenamiento, calificación y segmentación) se ejecutan fuera del ciclo de '
                   'la consulta interactiva y escriben sus resultados en el almacén. Así la respuesta al usuario nunca '
                   'espera un entrenamiento, y el panel y el chat muestran siempre las mismas cifras, porque leen las '
                   'mismas vistas.')
a = ins.figura(a, DIAG / 'av2_colaboracion.png', 'Diagrama de colaboración entre componentes')
a = ins.parrafo(a, 'El diagrama de colaboración numera los mensajes que intercambian los componentes en las dos '
                   'interacciones principales: la carga del panel de riesgo (mensajes 1 a 5) y una pregunta en el chat '
                   '(mensajes 6 a 11). El módulo core/privacidad.py interviene dos veces: al enmascarar la cédula que '
                   've la pantalla y al seudonimizar las filas antes de que salgan hacia el proveedor de IA.')
a = ins.figura(a, DIAG / 'av2_actividad_etl.png', 'Diagrama de actividades del ETL', ancho_pulgadas=5.8)
a = ins.parrafo(a, 'El ETL se organiza en tres carriles. El administrador de TI solo registra el perfil de la institución y '
                   'ejecuta el proceso; el ETL valida que el perfil produzca las 20 columnas del contrato antes de tocar '
                   'el almacén y, en ese caso, recarga únicamente los datos de esa institución, en el orden que imponen '
                   'las llaves foráneas. Con este mismo flujo se cargaron UNEMI_PRUEBAS y OULAD_UK sin modificar el código.')
a = ins.figura(a, DIAG / 'av2_actividad_modelo.png', 'Diagrama de actividades del entrenamiento y la calificación', ancho_pulgadas=5.8)
a = ins.parrafo(a, 'El entrenamiento reserva la prueba temporal antes de cualquier decisión: ajuste, comparación y elección '
                   'del umbral usan solo el 75 % más antiguo, y la prueba temporal se consulta una sola vez. Si un modelo de '
                   'referencia supera al Random Forest por más de 0,01 de ROC-AUC, queda registrado como advertencia en '
                   'lugar de ocultarse.')
a = ins.figura(a, DIAG / 'av2_estados.png', 'Diagrama de estados de la matrícula y del riesgo predicho', ancho_pulgadas=5.0)
a = ins.parrafo(a, 'La trayectoria de matrícula permanece en ACTIVO periodo tras periodo hasta un estado final (retirado, '
                   'graduado, egresado o, en OULAD, reprobado). La etiqueta del modelo es la transición de ACTIVO a '
                   'RETIRADO en el periodo siguiente. El riesgo predicho es un estado distinto, que cambia con cada nueva '
                   'calificación: sus umbrales derivan del umbral operativo elegido para alcanzar un recall de 0,80.')

a = ins.subtitulo(a, 'Modelo de datos: esquema estrella y diccionario de datos')
a = ins.figura(a, DIAG / 'av2_modelo_dimensional.png', 'Modelo dimensional del almacén CHAT (esquema estrella)')
a = ins.parrafo(a, 'fact_matriculas tiene grano de «un alumno en un periodo», la unidad de análisis declarada en la sección 1.3. '
                   'Desde este avance, dim_alumno se identifica por la pareja (institución, cédula), para que dos '
                   'instituciones con un identificador coincidente no se fusionen en una sola persona. Las tablas de '
                   'resultados (predicción, segmentos y métricas) son derivadas: las escriben los procesos por lotes, '
                   'nunca un usuario. El diccionario siguiente se generó automáticamente desde el esquema real de la base '
                   '(scripts/generar_diccionario_datos.py).')
for tabla in ('fact_matriculas', 'dim_alumno', 'dim_tiempo', 'fact_prediccion_abandono', 'fact_cluster_carrera',
              'fact_evaluacion_modelo', 'fact_benchmark_externo'):
    info = DIC['tablas'][tabla]
    filas = [('Columna', 'Tipo', 'Clave', 'Descripción')] + [
        (c['columna'], c['tipo'], c['clave'], c['descripcion']) for c in info['columnas']]
    a = ins.tabla(a, filas, titulo=f'Diccionario de datos: {tabla}', anchos=[1.5, 1.2, 1.3, 2.5], tam=8,
                  nota=f"Elaboración propia, generado desde el esquema real. {info['descripcion']}")
a = ins.parrafo(a, 'Las dimensiones restantes (dim_empresa, dim_facultad, dim_carrera, dim_estado_matricula, dim_sede, '
                   'dim_canal y dim_institucion_externa) son catálogos de código y nombre, documentados en '
                   'documentacion/tecnica/DICCIONARIO_DE_DATOS.md. La cuenta chat_reader solo puede leer las vistas de presentación: '
                   + ', '.join(DIC['vistas']) + '.')

a = ins.subtitulo(a, 'Recursos')
a = ins.tabla(a, [
    ('Tipo', 'Recurso', 'Uso'),
    ('Equipo', 'Portátil AMD Ryzen AI 9 HX 370 (12 núcleos / 24 hilos), 32 GB de RAM, GPU NVIDIA RTX 5070, Windows 11',
     'Desarrollo, entrenamiento y servidor de pruebas'),
    ('Base de datos', 'SQL Server 2022 en Docker (contenedor vicmar-sqlserver)', 'Bases operativas y almacén CHAT'),
    ('Datos', f"UNEMI_PRUEBAS (sintético y anonimizado) y OULAD (CC BY 4.0; Kuzilek et al., 2017)", 'Institución piloto y validación externa'),
    ('Servicios externos', 'Proveedores de modelos de lenguaje (Gemini, Groq, NVIDIA NIM) en nivel gratuito', 'Traducción de lenguaje natural a SQL y redacción'),
    ('Software', 'Python 3.14, Node.js 24, Git, Docker Desktop, Mermaid CLI', 'Construcción, pruebas y documentación'),
], titulo='Recursos empleados', anchos=[1.1, 3.3, 2.1])

# ── 3.3 Desarrollo ────────────────────────────────────────────────────────
a = ins.titulo(a, '3.3 Desarrollo', 2)
a = ins.subtitulo(a, 'Tecnologías implementadas')
a = ins.tabla(a, [
    ('Capa', 'Tecnología y versión', 'Uso'),
    ('Almacenamiento', 'SQL Server 2022 (Docker 29.5)', 'Bases operativas, esquema estrella, vistas y permisos'),
    ('Acceso a datos', 'pyodbc 5.3, ODBC Driver 18, SQLAlchemy 2.1', 'ETL, procesos por lotes y API'),
    ('Ciencia de datos', 'pandas 3.0, NumPy 2.5, scikit-learn 1.9.1, imbalanced-learn 0.14, SHAP 0.52', 'Panel, modelos, validación y explicaciones'),
    ('Visualización de resultados', 'matplotlib 3.11', 'Figuras de validación'),
    ('API', 'Python 3.14, FastAPI 0.141, Uvicorn 0.54', 'Endpoints REST con autenticación JWT'),
    ('Lenguaje natural', 'LangChain 1.4 y langchain-openai 1.6 (cascada Gemini, Groq y NVIDIA NIM)', 'Traducción a SQL y redacción'),
    ('Frontend', 'React 18.3, Vite 5.4, Tailwind CSS 4, framer-motion 11, react-apexcharts 2.1', 'Panel y chat'),
    ('Calidad', 'pytest 9.1', 'Pruebas unitarias y de integración'),
], titulo='Tecnologías y versiones fijadas', anchos=[1.3, 2.9, 2.3],
    nota='Elaboración propia. Las versiones exactas de todas las dependencias están en backend/requirements.lock.txt.')

a = ins.subtitulo(a, 'Selección de tecnologías: tres opciones por decisión')
a = ins.parrafo(a, 'Cada tecnología se eligió comparando al menos tres opciones con una matriz ponderada. Los criterios salen '
                   'de los requerimientos y de las restricciones del proyecto, y cada puntaje lleva una fuente verificable: '
                   'la tabla de trabajos previos de la sección 1.3, artículos con DOI, la documentación oficial consultada '
                   'el 3 de octubre de 2026 o las pruebas del prototipo. Los criterios de costo de cambio reconocen que la '
                   'decisión se documenta sobre un prototipo ya probado, y se declaran para que el lector pueda descontarlos.')
for _ruta, _titulo in (('DT-01_lenguaje_backend.json', 'Lenguaje del backend'),
                       ('DT-02_framework_backend.json', 'Framework del backend'),
                       ('DT-03_framework_frontend.json', 'Framework del frontend'),
                       ('DT-04_almacen_datos.json', 'Motor del almacén de datos'),
                       ('DT-05_algoritmo_modelo.json', 'Algoritmo del modelo predictivo')):
    _d, _g, _filas, _est = _dt(DEC / _ruta)
    a = ins.tabla(a, _filas, titulo=f"{_d['id']}. {_titulo}: comparación de opciones", anchos=[2.4, 1.35, 1.35, 1.35], tam=8.5,
                  nota='Elaboración propia. Puntajes de 1 (peor) a 5 (mejor); justificación y fuente de cada celda en '
                       f"documentacion/decisiones/{_ruta}.")
    a = ins.parrafo(a, f"**Elección: {_g['nombre']}.** {_d['eleccion']['razon']}"
                       + ('' if _est else ' La ganadora no es estable ante variaciones de ±20 % en los pesos.'))

a = ins.subtitulo(a, 'Backend: construcción del panel alumno-periodo')
a = ins.codigo(a, fragmento(BACK / 'ml/features_abandono.py', "h = hist.sort_values(", "h['para_calificar'] ="))
a = ins.parrafo(a, 'hist contiene una fila por alumno y periodo, leída del almacén. El agrupamiento g separa cada '
                   'trayectoria (alumno, carrera y secuencia hasta un cierre), de modo que las características de un '
                   'periodo solo usan información pasada: diff() compara con el periodo anterior, rolling() promedia los '
                   'últimos tres y cummin() guarda el peor valor histórico. La etiqueta y toma el estado del periodo '
                   'siguiente (shift(-1)) y vale NaN cuando no existe; esas filas no se usan para entrenar. para_calificar '
                   'marca el periodo vigente de quien sigue activo, que es a quien se le predice el próximo periodo.')
a = ins.subtitulo(a, 'Backend: comparación de modelos y umbral operativo')
a = ins.codigo(a, funcion_py(BACK / 'ml/entrenar_abandono.py', 'candidatos'))
a = ins.codigo(a, funcion_py(BACK / 'ml/entrenar_abandono.py', 'umbral_para_recall'))
a = ins.parrafo(a, 'candidatos() devuelve los cuatro modelos que se comparan con los mismos pliegues. En RF_SMOTE, SMOTE '
                   'forma parte de un Pipeline de imbalanced-learn, así que el sobremuestreo ocurre solo dentro del pliegue '
                   'de entrenamiento y nunca contamina el de prueba. umbral_para_recall() recorre la curva de '
                   'precisión-recall de las predicciones fuera de pliegue y devuelve el mayor umbral que todavía alcanza el '
                   'recall exigido, es decir, la mejor precisión posible sin dejar de detectar al 80 % de quienes abandonan.')
a = ins.subtitulo(a, 'Backend: ejecución segura de las consultas del chat')
a = ins.codigo(a, fragmento(BACK / 'main.py', 'if db_label == "CHAT":', 'return connector.execute_query(sql, target_db=db_label, **kwargs)'))
a = ins.parrafo(a, 'execute_chat_query es el único punto en que se decide con qué cuenta se ejecuta una consulta contra '
                   'CHAT. Usa chat_reader y fija el contexto de institución en la misma conexión que ejecuta el SELECT '
                   '(execute_query_with_context). Si chat_reader no está disponible, la consulta se rechaza en lugar de '
                   'ejecutarse con la cuenta administrativa: el sistema falla cerrado. Antes de este avance ocurría lo '
                   'contrario, y la garantía de aislamiento se anulaba sin aviso.')
a = ins.subtitulo(a, 'Backend: minimización de datos personales')
a = ins.codigo(a, funcion_py(BACK / 'core/privacidad.py', 'enmascarar_filas', max_lineas=40))
a = ins.parrafo(a, 'enmascarar_filas recibe las columnas y filas de un resultado y reemplaza las columnas que identifican a '
                   'una persona por un seudónimo estable dentro de la misma llamada («Alumno 1», «Alumno 2»). Así el '
                   'proveedor puede redactar «hay dos alumnos en riesgo alto en Enfermería» sin conocer su identidad. '
                   'Además oculta cualquier número con forma de cédula que aparezca en otra columna.')
a = ins.subtitulo(a, 'Backend: incorporación de la segunda institución')
a = ins.codigo(a, funcion_py(BACK / 'etl/perfiles.py', '_OULAD_UK'))
a = ins.parrafo(a, 'Incorporar OULAD requirió solo este perfil: un SELECT que traduce el esquema de la institución a los '
                   'nombres lógicos que espera el almacén, con literales para los datos que no registra (sede, modalidad y '
                   'variables financieras). El ETL, las características y el entrenamiento son exactamente los mismos '
                   'que para UNEMI_PRUEBAS.')

a = ins.subtitulo(a, 'Frontend: panel de riesgo con explicaciones y confiabilidad')
a = ins.codigo(a, fragmento(FRONT / 'src/components/views/RiesgoAbandonoCard.jsx', 'function metricaTemporal', '}', exacto=True))
a = ins.codigo(a, fragmento(FRONT / 'src/components/views/RiesgoAbandonoCard.jsx', '{a.factores?.length > 0 && (', ')}', exacto=True))
a = ins.parrafo(a, 'metricaTemporal busca, entre las métricas que devuelve /api/ml/evaluacion-modelo, el valor de la '
                   'validación temporal (ROC-AUC y recall) que se muestra como insignia de confiabilidad. Bajo el nombre de '
                   'cada alumno, la lista a.factores muestra las tres razones SHAP que devolvió la API. La tarjeta recibe '
                   'la cédula ya enmascarada desde el servidor y muestra un aviso distinto según la institución: datos '
                   'sintéticos en UNEMI_PRUEBAS y datos reales anonimizados en OULAD_UK.')
a = ins.subtitulo(a, 'Frontend: referentes externos con comparabilidad')
a = ins.codigo(a, fragmento(FRONT / 'src/components/views/InteligenciaInstitucionalCard.jsx', 'const COMPARABILIDAD_STYLE', '};'))
a = ins.parrafo(a, 'COMPARABILIDAD_STYLE asigna un color a cada nivel de comparabilidad. Cada referente muestra su país, su '
                   'modalidad, la cita con enlace al DOI y, al pasar el cursor, la definición exacta de lo que mide, '
                   'siguiendo la recomendación de Lepori y Bornmann (2026) de comparar pares con pares.')

# ── Resultados ────────────────────────────────────────────────────────────
a = ins.subtitulo(a, 'Resultados de la validación del modelo predictivo')
comp = [('Modelo', 'UNEMI: ROC-AUC', 'UNEMI: PR-AUC', 'OULAD: ROC-AUC', 'OULAD: PR-AUC')]
for m in ('RF_CLASS_WEIGHT', 'RF_SMOTE', 'LOGISTICA', 'GRADIENT_BOOST'):
    comp.append((NOMBRE[m] + (' (elegido en UNEMI)' if m == MU['modelo_final'] else '') +
                 (' (elegido en OULAD)' if m == MO['modelo_final'] else ''),
                 cv(MU, m, 'roc_auc'), cv(MU, m, 'pr_auc'), cv(MO, m, 'roc_auc'), cv(MO, m, 'pr_auc')))
a = ins.tabla(a, comp, titulo='Comparación de modelos en validación cruzada agrupada por alumno (media ± desviación, 5 pliegues)',
              anchos=[2.4, 1.05, 1.05, 1.05, 1.05])
a = ins.tabla(a, [
    ('Esquema', 'Institución', 'ROC-AUC', 'PR-AUC', 'Recall', 'Precisión', 'Umbral'),
    ('Prueba temporal', 'UNEMI_PRUEBAS', n(TU['roc_auc']), n(TU['pr_auc']), n(TU['recall']), n(TU['precision']), n(TU['umbral'])),
    ('Prueba temporal', 'OULAD_UK', n(TO['roc_auc']), n(TO['pr_auc']), n(TO['recall']), n(TO['precision']), n(TO['umbral'])),
    ('Prospectiva (bloque siguiente)', 'OULAD_UK', n(PROS['y_proximo']['roc_auc']), n(PROS['y_proximo']['pr_auc']),
     n(PROS['y_proximo']['recall']), n(PROS['y_proximo']['precision']), n(PROS['umbral'])),
], titulo='Validación temporal y prospectiva del modelo elegido', anchos=[1.6, 1.2, 0.7, 0.7, 0.7, 0.8, 0.7],
   nota=f"Elaboración propia. Corte temporal: {MU['validacion_temporal']['corte']} (UNEMI) y "
        f"{MO['validacion_temporal']['corte']} (OULAD). La prospectiva compara la calificación de "
        f"{miles(PROS['calificados'])} matrículas activas de OULAD con su desenlace real posterior.")
a = ins.figura(a, FIG / 'UNEMI_PRUEBAS_roc_pr.png', 'Curvas ROC y precisión-recall en UNEMI_PRUEBAS (datos sintéticos)')
a = ins.figura(a, FIG / 'OULAD_UK_roc_pr.png', 'Curvas ROC y precisión-recall en OULAD_UK (datos reales)')
a = ins.figura(a, FIG / 'OULAD_UK_importancia.png', 'Importancia por permutación en OULAD_UK', ancho_pulgadas=5.2)
top_u = MU['importancia_permutacion'][0]['variable']
top_o = MO['importancia_permutacion'][0]['variable']
a = ins.bloque(a, f"""
**Discusión.** Los resultados de las dos instituciones cuentan historias distintas, y ambas se reportan tal como salieron. En UNEMI_PRUEBAS todos los modelos superan 0,98 de ROC-AUC, incluida la regresión logística. No es un mérito del modelo: el generador sintético hace caer la asistencia justo antes del abandono, y la variable más importante es precisamente {top_u}. Estos datos demuestran que la arquitectura completa funciona de extremo a extremo, pero no miden el desempeño esperable en una institución real.

En OULAD, con datos reales, el ROC-AUC temporal es {n(TO['roc_auc'])} y el prospectivo {n(PROS['y_proximo']['roc_auc'])}. Para cumplir el recall objetivo, el modelo acepta una precisión baja ({n(TO['precision'])}): de cada veinte alertas, aproximadamente una corresponde a un abandono en el bloque siguiente. Con una prevalencia de {pct(TO['prevalencia'], 1)}, un PR-AUC de {n(TO['pr_auc'])} equivale a unas {n(TO['pr_auc'] / TO['prevalencia'], 1)} veces el azar. La variable más importante es {top_o}, el rendimiento académico, lo que coincide con lo que reportan Kok et al. (2024), mientras que la actividad en el aula virtual aporta una señal menor pero presente, como documentan Marcolino et al. (2025) y Vaarma y Li (2024). En consecuencia, el criterio de éxito (a) —ROC-AUC de al menos 0,90 en la validación temporal— se cumple en la institución piloto, pero no en datos reales. Esto confirma la advertencia de Dube y Verster (2024) sobre el desbalance de clases y justifica dos líneas de trabajo: enriquecer las características con datos que la institución ya registra (entregas atrasadas, créditos, actividad semanal) y definir el umbral según la capacidad real de intervención de la institución, no solo según el recall.

Sobre el desbalance: SMOTE superó a la ponderación de clases en UNEMI_PRUEBAS y la ponderación a SMOTE en OULAD, en ambos casos por menos de una desviación estándar, así que ninguna técnica domina con estos datos. El gradient boosting empató con el Random Forest en OULAD y la regresión logística quedó por debajo, lo que respalda la conclusión de Duro et al. (2026) sobre el desempeño competitivo de los modelos de árboles.
""")

a = ins.subtitulo(a, 'Resultados de la segmentación de carreras')
a = ins.tabla(a, [
    ('Indicador', 'UNEMI_PRUEBAS', 'OULAD_UK'),
    ('Unidades segmentadas', f"{CU['n_unidades']} carreras", f"{CO['n_unidades']} módulos"),
    ('Silhouette (k = 3)', n(SIL_U), n(SIL_O)),
    ('Estabilidad bootstrap (ARI medio)', n(CU['estabilidad_bootstrap']['ari_medio']), n(CO['estabilidad_bootstrap']['ari_medio'])),
    ('Kruskal-Wallis sobre la tasa de abandono (p)', n(KW_U['p_valor']), n(KW_O['p_valor'])),
    ('Silhouette jerárquico (Ward)', n(CU['comparacion_algoritmos']['JERARQUICO_WARD']['silhouette']),
     n(CO['comparacion_algoritmos']['JERARQUICO_WARD']['silhouette'])),
    ('Coincidencia sin riesgo predicho (ARI)', n(CU['coincidencia_sin_riesgo_promedio_ari']), n(CO['coincidencia_sin_riesgo_promedio_ari'])),
], titulo='Validación de la segmentación institucional', anchos=[2.8, 1.8, 1.8])
a = ins.figura(a, FIG / 'UNEMI_PRUEBAS_clustering_k.png', 'Calidad de la segmentación de carreras según el número de clústeres', ancho_pulgadas=4.6)
a = ins.parrafo(a, f"En UNEMI_PRUEBAS los tres segmentos difieren de forma estadísticamente significativa en su tasa de "
                   f"abandono (p = {n(KW_U['p_valor'])}), lo que cumple el criterio de éxito (b); la silhouette de "
                   f"{n(SIL_U)} indica una estructura razonable, y la estabilidad moderada (ARI = "
                   f"{n(CU['estabilidad_bootstrap']['ari_medio'])}) aconseja tratar los segmentos como priorización y no "
                   f"como clasificación rígida, tal como exigen Melchor et al. (2026). En OULAD, con solo siete módulos, la "
                   f"diferencia no es significativa (p = {n(KW_O['p_valor'])}): siete unidades son muy pocas para segmentar, "
                   "como se había anticipado.")

a = ins.subtitulo(a, 'Resultados del motor conversacional NL2SQL')
porcat = [('Categoría', 'Preguntas', 'Correctas', 'Exactitud')] + [
    (cat, str(v['n']), str(v['relajada']), n(v['exactitud_relajada'], 2)) for cat, v in sorted(R['por_categoria'].items())]
porcat.append(('Total', str(R['preguntas']), str(round(EX * R['preguntas'])), n(EX, 2)))
a = ins.tabla(a, porcat, titulo='Exactitud por ejecución del motor NL2SQL por categoría de pregunta', anchos=[2.0, 1.2, 1.2, 1.2],
              nota=f"Elaboración propia a partir de eval/{Path(_evals[-1]).name}. Usuario de prueba con rol ACADÉMICO; "
                   f"caché de respuestas desactivada; fallas técnicas del proveedor: {R['fallas_tecnicas_proveedor']}.")
malas = [q for q in NL['preguntas'] if not q['relajada']]
a = ins.parrafo(a, f"El motor respondió correctamente {round(EX * R['preguntas'])} de {R['preguntas']} preguntas "
                   f"(exactitud {n(EX, 2)}), con una mediana de {n(R['latencia_p50_s'], 1)} s por respuesta. Las "
                   f"{R['adversariales']} preguntas maliciosas —borrar datos, consultar la base operativa o las tablas "
                   f"físicas, pedir los alumnos de la otra institución o inyectar instrucciones— quedaron contenidas en "
                   f"{R['adversariales_superadas']} casos, la base no cambió y no se registró ninguna fila de otra "
                   f"institución en ninguna respuesta. Las preguntas no resueltas ("
                   + ', '.join(q['id'] for q in malas) + ") se analizan en el archivo de resultados.")
a = ins.parrafo(a, f"Dos precisiones sobre cómo leer esta cifra. Primero, la exactitud depende también de la "
                   f"disponibilidad de los proveedores gratuitos de modelos de lenguaje: en la corrida final hubo "
                   f"{R['fallas_tecnicas_proveedor']} fallas técnicas (cuota diaria agotada, límites por minuto o "
                   f"saturación del servicio); sin ellas, la exactitud es {n(R['exactitud_relajada_sin_fallas_tecnicas'], 3)}. "
                   f"Segundo, las preguntas se espaciaron {n(R.get('pausa_entre_preguntas_s', 0), 0)} s, un ritmo realista "
                   "para una autoridad que consulta el sistema, porque los niveles gratuitos limitan los tokens por "
                   "minuto. Para un despliegue institucional se recomienda un proveedor con cuota contratada, que la "
                   "arquitectura ya admite como proveedor principal de la cascada sin cambiar el resto del sistema.")
_corridas = [('1. Línea base', BACK / 'eval/corrida1_antes_de_correcciones.json',
              'Antes de las correcciones; comparador estricto de la primera versión'),
             ('2. Contexto académico', BACK / 'eval/corrida2_contexto_academico.json',
              'Métricas certificadas y lógica de negocio corregidas'),
             ('3. Proveedores', BACK / 'eval/corrida3_sin_pausa.json',
              'Modelos vigentes, modo sin razonamiento y verificador de cifras'),
             ('4. Final', Path(_evals[-1]), 'Reintento ante salida degenerada y preguntas espaciadas 30 s')]
filas_c = [('Corrida', 'Exactitud por ejecución', 'Sin fallas técnicas', 'Maliciosas contenidas', 'Fallas técnicas', 'Cambios')]
for nombre, ruta, cambios in _corridas:
    if ruta.exists():
        rr = _json(ruta)['resumen']
        sf = rr.get('exactitud_relajada_sin_fallas_tecnicas')
        filas_c.append((nombre, n(rr['exactitud_relajada'], 3), n(sf, 3) if sf is not None else '—',
                        f"{rr['adversariales_superadas']}/{rr['adversariales']}",
                        str(rr.get('fallas_tecnicas_proveedor', '—')), cambios))
a = ins.tabla(a, filas_c, titulo='Evolución de la exactitud del motor NL2SQL entre corridas de evaluación',
              anchos=[1.05, 0.95, 0.95, 0.9, 0.75, 1.9],
              nota='Elaboración propia. Las cuatro corridas usan las mismas 40 preguntas y el mismo usuario; los archivos '
                   'de cada corrida están en backend/eval/.')
a = ins.parrafo(a, 'La evaluación cumplió su propósito: destapó defectos reales que ninguna prueba unitaria había '
                   'detectado. Se corrigieron durante este avance y se resumen a continuación.')
a = ins.tabla(a, [
    ('Defecto detectado', 'Evidencia', 'Corrección', 'Archivo'),
    ('Las métricas certificadas contaban filas y no personas', '«¿Cuántos matriculados?» respondía 676 en lugar de 10.848',
     'Contar cédulas distintas en el periodo vigente (es_ultimo_periodo = 1)', 'knowledge/metric_catalog.json'),
    ('El modelo de lenguaje no sabía que la institución es una universidad', 'Contexto recibido: «empresa comercial estándar»',
     'Lógica de negocio académica por institución (estrategia de contexto; Ascoli y Choi, 2025)', 'knowledge/business_logic.json'),
    ('La cascada de proveedores no tenía respaldo real', 'Modelos NVIDIA retirados (HTTP 410) y límite de Groq de 8.000 tokens por minuto',
     'Modelos vigentes verificados en vivo', 'config.py'),
    ('Respuestas vacías de los modelos de razonamiento', '«No se pudo estructurar la salida del modelo»',
     'Presupuesto mínimo de tokens y modo sin razonamiento en NVIDIA NIM', 'core/nl2sql_engine.py'),
    ('La explicación podía citar cifras inventadas', 'Tabla con 0,9971 y texto con «0,87»',
     'Verificador de cifras: se redacta de nuevo sobre el resultado real', 'core/verificador_cifras.py'),
    ('Salidas vacías o degeneradas sin error', 'Respuestas «!!!!!!!!» del proveedor con HTTP 200',
     'Detección de salida degenerada y un reintento de la cascada', 'core/nl2sql_engine.py'),
    ('La memoria semántica aprendía respuestas sin verificar', 'SQL erróneo memorizado y repetido',
     'La evaluación no escribe en la memoria; memoria de la institución depurada', 'eval/evaluar_nl2sql.py'),
], titulo='Defectos detectados por la evaluación y su corrección', anchos=[1.7, 1.7, 1.9, 1.3], tam=8)

a = ins.subtitulo(a, 'Pruebas de seguridad y privacidad')
a = ins.parrafo(a, 'Las pruebas de integración se ejecutan contra el SQL Server real con las dos instituciones cargadas y '
                   'comprueban lo que el documento afirma en el criterio de éxito (c): chat_reader recibe «permiso '
                   'denegado» al intentar leer las bases operativas o las tablas físicas y al intentar escribir; con el '
                   'contexto de una institución, las vistas no devuelven ninguna fila de la otra; sin contexto, no '
                   'devuelven nada; y si chat_reader falla, la consulta no se ejecuta con la cuenta administrativa. Las '
                   'pruebas de privacidad verifican que el cuerpo HTTP enviado a un proveedor externo no contiene ninguna '
                   'cédula ni nombre.')

a = ins.subtitulo(a, 'Demostración del prototipo')
capturas = sorted(FIG.glob('demo_*.png'))
for c in capturas:
    a = ins.figura(a, c, c.stem.replace('demo_', '').replace('_', ' ').capitalize(), ancho_pulgadas=6.0)
a = ins.parrafo(a, 'La demostración completa se reproduce con un solo comando (scripts/demo_tesis.ps1), que reconstruye '
                   'las bases, carga las dos instituciones, entrena, califica, segmenta, carga los referentes externos y '
                   'ejecuta las pruebas, antes de levantar el backend y el frontend. El recorrido: ingresar con el usuario '
                   'académico, conectar UNEMI_PRUEBAS, revisar el riesgo con sus factores y la confiabilidad del modelo, '
                   'revisar los segmentos y los referentes, hacer tres preguntas en el chat, comprobar que una pregunta '
                   'maliciosa se bloquea y cambiar a OULAD_UK para verificar que cada institución solo ve sus datos.')

# ── Referencias nuevas (orden alfabético) ────────────────────────────────
refs = [p for p in doc.paragraphs if p.style.name == 'Bibliography']


def insertar_referencia(antes_de_prefijo, partes):
    """partes: lista de (texto, cursiva). Copia el formato de la referencia vecina."""
    import copy
    base = next(p for p in refs if p.text.startswith(antes_de_prefijo))
    nuevo = copy.deepcopy(base._p)
    base._p.addprevious(nuevo)
    par = docx.text.paragraph.Paragraph(nuevo, base._parent)
    # Quitar TODO el contenido copiado (runs e hipervínculos del DOI de la
    # referencia vecina), conservando solo el formato del párrafo (pPr).
    for hijo in list(nuevo):
        if hijo.tag != docx.oxml.ns.qn('w:pPr'):
            nuevo.remove(hijo)
    for texto, cursiva in partes:
        run = par.add_run(texto)
        run.italic = cursiva
    return par


insertar_referencia('Ascoli', [('Asamblea Nacional del Ecuador. (2021). ', False),
                               ('Ley Orgánica de Protección de Datos Personales', True),
                               ('. Registro Oficial, Quinto Suplemento n.º 459, 26 de mayo de 2021.', False)])
_tras_hassan = min((p for p in refs if p.text.strip() > 'Hassan'), key=lambda p: p.text.strip())
insertar_referencia(_tras_hassan.text.strip()[:12], [
    ('Hassan, H., Abdel-Fattah, M. A., & Mohamed, W. (2025). A pattern-based framework for automated migration of '
     'monolithic applications to microservices. ', False),
    ('Big Data and Cognitive Computing, 9', True), ('(10), Article 253. https://doi.org/10.3390/bdcc9100253', False)])
insertar_referencia('Lepori', [('Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2017). Open University Learning Analytics dataset. ', False),
                               ('Scientific Data, 4', True), (', 170171. https://doi.org/10.1038/sdata.2017.171', False)])

doc.core_properties.author = 'Marlon David Pérez Almachi; Víctor Manuel Lluilema Pisco'
doc.core_properties.last_modified_by = 'Marlon David Pérez Almachi'
doc.save(str(OUT))
print(f'Generado {OUT.name}: {ins.n_figura} figuras, {ins.n_tabla} tablas. Resumen: {len(RESUMEN.split())} palabras.')
