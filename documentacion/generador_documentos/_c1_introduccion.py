# -*- coding: utf-8 -*-
"""Capítulo 1 del Avance 2: descripción, propósito y base conceptual.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from _datos import NOMBRE_MODELO, O, U, ent, f, pct


def bloques() -> list[tuple]:
    um, om = U['m'], O['m']
    ut, ot = um['validacion_temporal'], om['validacion_temporal']
    b: list[tuple] = []
    a = b.append

    a(('h1', '1. Introducción'))
    # ── 1.1 ───────────────────────────────────────────────────────────────
    a(('h2', '1.1 Descripción'))
    a(('p', 'El abandono de los estudios universitarios es uno de los indicadores con que se mide la eficiencia de un '
            'sistema de educación superior y, al mismo tiempo, una pérdida personal para quien no concluye su carrera. '
            'En América Latina, la proporción de estudiantes que deja la universidad antes de titularse se mantiene en '
            'niveles altos y varía de forma marcada entre facultades, grupos socioeconómicos y cohortes de ingreso '
            '(Gutierrez-Pachas et al., 2023). En el Ecuador, un estudio sobre cinco cohortes de una universidad privada '
            'encontró que 484 de 1.078 estudiantes admitidos abandonaron sus estudios, con una probabilidad de abandono '
            'del 44,90 % asociada a factores personales, familiares, económicos, académicos e institucionales '
            '(Núñez-Naranjo, 2024). El problema, por tanto, no es hipotético en el país: está medido y tiene magnitud.'))
    a(('p', 'Las teorías clásicas explican el abandono como un proceso y no como un hecho aislado. Para Tinto (1975), '
            'el estudiante decide permanecer o retirarse según su grado de integración académica y social con la '
            'institución, mientras que Bean y Metzner (1985) muestran que, en estudiantes que trabajan o estudian a '
            'distancia, pesan más las variables externas (tiempo disponible, situación económica, carga familiar) que '
            'la vida en el campus. Ambos modelos coinciden en un punto útil para este trabajo: el abandono deja señales '
            'previas en el rendimiento, la asistencia, la carga matriculada o la deuda con la institución, señales que '
            'quedan registradas en los sistemas académicos periodo tras periodo.'))
    a(('p', 'Las instituciones de educación superior (IES) del país ya poseen esos registros, pero en la práctica los '
            'consultan para conocer el estado actual del estudiante y no para analizar su trayectoria. La información de '
            'matrícula, calificaciones, asistencia, aula virtual y cartera se guarda en sistemas separados, y obtener '
            'una cifra que combine varias de esas fuentes exige pedirla al área de tecnología. Komljenovic et al. (2025) '
            'describen esta fragmentación como uno de los obstáculos reales que enfrentan las universidades que quieren '
            'decidir con datos. La consecuencia es conocida por cualquier director de carrera: el retiro se detecta '
            'cuando el estudiante ya dejó de asistir y la oportunidad de acompañarlo pasó.'))
    a(('p', 'La {T:causas} resume las causas del problema según la literatura revisada y la forma en que suelen organizarse '
            'los sistemas académicos de las IES ecuatorianas, entre ellas la Universidad Estatal de Milagro (UNEMI), '
            'junto con los efectos que cada una produce en la gestión de la permanencia estudiantil. El levantamiento '
            'directo con las autoridades de la UNEMI forma parte del piloto propuesto en las recomendaciones.'))
    a(('tab', 'causas', 'Causas y Efectos del Problema de Detección Tardía del Abandono',
       ['Causa', 'Descripción', 'Efectos principales'],
       [['Trayectoria no explotada', 'Los sistemas guardan el estado vigente de la matrícula, no una serie histórica '
         'lista para analizar.', 'Las caídas de rendimiento o asistencia pasan inadvertidas; las decisiones son '
         'reactivas.'],
        ['Ausencia de modelos predictivos', 'No existe una herramienta de aprendizaje automático integrada al '
         'seguimiento académico (Duro et al., 2026).', 'Identificación tardía; tutorías y becas sin focalizar.'],
        ['Datos dispersos', 'Matrícula, calificaciones, aula virtual y cartera operan por separado '
         '(Komljenovic et al., 2025).', 'No se cruzan variables; reportes inconsistentes entre áreas.'],
        ['Dependencia técnica para consultar', 'La reportería exige SQL o herramientas especializadas '
         '(Sequeira et al., 2024).', 'Demoras en las respuestas y baja adopción por las autoridades.'],
        ['Sin referentes externos', 'La tasa propia no se contrasta con instituciones comparables '
         '(Lepori y Bornmann, 2026).', 'Es difícil dimensionar la gravedad del problema y justificar inversión.'],
        ['Protección de datos poco operativa', 'La Ley Orgánica de Protección de Datos Personales (LOPDP) exige '
         'finalidad, minimización y trazabilidad (Asamblea Nacional del Ecuador, 2021).', 'Temor a usar los datos o uso sin '
         'controles de acceso ni registro.']],
       'Elaboración propia a partir del diagnóstico del caso y de la literatura citada.', [3.6, 6.4, 6.0]))
    a(('p', 'Frente a este escenario, la literatura reciente muestra que el aprendizaje automático permite anticipar el '
            'abandono con datos que las IES ya tienen. Los modelos de ensamble basados en árboles dominan el campo por '
            'su equilibrio entre desempeño e interpretabilidad (Duro et al., 2026); XGBoost logra alertas desde el '
            'primer día con datos previos a la matrícula (Carballo-Mendívil et al., 2025), y los registros de actividad '
            'en Moodle aportan señales de deterioro que preceden al retiro (Marcolino et al., 2025; Vaarma y Li, 2024). '
            'Sin embargo, esos estudios entregan un modelo evaluado en un cuaderno de investigación; ninguno resuelve '
            'cómo una autoridad sin formación técnica consulta la predicción, la entiende y la usa con controles de '
            'privacidad, que es el vacío práctico que motiva este proyecto.'))
    a(('p', 'Durante el Avance 1 se construyó una primera versión del prototipo sobre datos sintéticos generados con '
            'reglas deterministas. Su validación temporal arrojó un ROC-AUC de 0,9999, un valor que, lejos de ser un '
            'logro, indicaba que los datos eran demasiado fáciles de separar y que el resultado no sería creíble ante '
            'un caso real. En este Avance 2 se rehízo el simulador con factores latentes inspirados en Tinto (1975) y '
            'en Bean y Metzner (1985), se incorporó un conjunto real y público (Open University Learning Analytics '
            f'Dataset, OULAD; Kuzilek et al., 2017) y se repitió todo el proceso. Los valores actuales, entre '
            f'{f(ot["roc_auc"])} y {f(ut["roc_auc"])} de ROC-AUC en la validación temporal, se acercan a los que '
            'informan los estudios que evalúan con cohortes posteriores al entrenamiento, como el ROC-AUC de 0,69 de '
            'Carballo-Mendívil et al. (2025).'))
    a(('p', '**Conveniencia y utilidad.** El proyecto es conveniente porque traslada la gestión de la permanencia de la '
            'medición posterior a la anticipación. Sirve para que el decanato, la dirección de carrera y el área de '
            'bienestar estudiantil sepan cada periodo qué estudiantes tienen mayor probabilidad de no matricularse en el '
            'siguiente, por qué el sistema los señala y qué carreras concentran el riesgo; además, les permite '
            'preguntar en español, sin escribir SQL, por cualquier cifra certificada del almacén de datos. Ayuda a '
            'resolver un problema real: la detección tardía, que hoy depende de que un docente note la ausencia del '
            'estudiante.'))
    a(('p', '**Beneficiarios.** Los beneficiarios directos son las autoridades académicas y el personal de bienestar '
            'estudiantil, que podrán priorizar tutorías, consejería y apoyos económicos con un criterio objetivo; los '
            'estudiantes en riesgo, que recibirán acompañamiento antes de retirarse; y el área de tecnologías de la '
            'información, que contará con una arquitectura documentada, con cuentas de mínimo privilegio y auditoría. '
            'De forma indirecta se beneficia el Estado, porque la educación superior pública se financia con recursos '
            'fiscales cuya pérdida por deserción es evitable.'))

    # ── 1.2 ───────────────────────────────────────────────────────────────
    a(('h2', '1.2 Propósito del caso'))
    a(('p', 'El propósito del caso es demostrar que un sistema web puede convertir la trayectoria académica que una '
            'universidad ya registra en alertas tempranas de abandono confiables, explicables y consultables por '
            'personas sin perfil técnico, respetando la protección de los datos estudiantiles. Los aprendizajes que se '
            'buscan extraer son tres: qué variables anticipan el abandono con datos disponibles al cierre de cada '
            'periodo, qué tan bien se sostiene esa anticipación cuando se evalúa con periodos que el modelo nunca vio, '
            'y qué condiciones técnicas y de gobierno de datos hacen falta para que una autoridad confíe en la cifra y '
            'actúe sobre ella. Los destinatarios de esos aprendizajes son la UNEMI y cualquier IES ecuatoriana que '
            'quiera replicar la solución con su propio perfil de datos.'))
    a(('h3', '1.2.1 Objetivo general'))
    a(('p', 'Desarrollar un prototipo de sistema web que prediga el abandono de estudiantes universitarios mediante '
            'aprendizaje automático y permita consultar sus resultados en lenguaje natural, para que las autoridades '
            'académicas y el personal de bienestar estudiantil identifiquen tempranamente a quienes están en riesgo y '
            'prioricen su acompañamiento.'))
    a(('h3', '1.2.2 Objetivos específicos'))
    a(('ul', ['Analizar los procesos de seguimiento académico y las variables de trayectoria, matrícula, aula virtual, '
              'evaluaciones y cartera asociadas al abandono, para derivar los requerimientos del sistema.',
              'Construir y validar un modelo de predicción calibrado y explicable, mediante validación cruzada agrupada '
              'por estudiante, validación temporal y evaluación prospectiva, sobre datos de prueba de la UNEMI y sobre '
              'el conjunto real OULAD.',
              'Implementar el sistema web por roles, con panel institucional, ficha explicada del estudiante, '
              'segmentación de carreras y consulta conversacional sobre vistas gobernadas del almacén de datos.',
              'Evaluar el prototipo con métricas predictivas (ROC-AUC, PR-AUC, recall, calibración), de exactitud de '
              'la consulta conversacional y de protección de datos, contrastándolas con los criterios de aceptación.']))
    a(('h3', '1.2.3 Delimitación del estudio de caso'))
    a(('p', 'La {T:delim} delimita el estudio respondiendo a las preguntas qué, cómo y para qué, tal como lo solicita la '
            'guía del estudio de caso.'))
    a(('tab', 'delim', 'Delimitación del Estudio de Caso',
       ['Pregunta', 'Respuesta'],
       [['¿Qué?', 'Desarrollar un prototipo de sistema web de alerta temprana del abandono estudiantil.'],
        ['¿Cómo?', 'Con la metodología CRISP-DM: un almacén dimensional en SQL Server, modelos de aprendizaje '
                   'automático (Random Forest, regresión logística y LightGBM) validados en el tiempo, segmentación '
                   'K-means de carreras y un motor de lenguaje natural a SQL (NL2SQL) con métricas certificadas, '
                   'expuestos por una API FastAPI y una interfaz React.'],
        ['¿Para qué?', 'Para que autoridades y bienestar estudiantil identifiquen a tiempo a los estudiantes en '
                       'riesgo, entiendan los motivos y prioricen tutorías, consejería o apoyo económico.'],
        ['¿Dónde?', 'UNEMI, con datos de prueba que reproducen su estructura (dos sedes, 18 carreras, 2019-2026), y '
                    'Open University (Reino Unido) con datos reales anonimizados.'],
        ['¿Para quién?', 'Decanato, dirección de carrera, bienestar estudiantil y administración de TI.']],
       'Elaboración propia.', [3.0, 13.0]))
    a(('p', '**Alcance.** El trabajo corresponde a un alcance explicativo-experimental: no se limita a describir el '
            'abandono, sino que construye una intervención tecnológica y mide su desempeño. Incluye la carga y '
            'transformación de datos por perfil institucional, el entrenamiento y la calificación por lotes, la '
            'explicación de cada predicción, el registro del seguimiento, la consulta conversacional, la segmentación, '
            'los referentes externos y los reportes ejecutivos. Queda fuera el despliegue productivo con datos reales '
            'de estudiantes de la UNEMI, que requiere autorización institucional y un acuerdo de tratamiento de datos, '
            'así como el envío automático de notificaciones a estudiantes.'))
    a(('p', '**Criterios de éxito revisados.** El criterio del Avance 1 (ROC-AUC de al menos 0,90) se reformula porque '
            'se apoyaba en datos deterministas, y se fija antes de observar los resultados de este avance a partir de '
            'dos referencias externas: los estudios que validan con cohortes posteriores al entrenamiento informan '
            'valores cercanos a 0,70 (Carballo-Mendívil et al., 2025), mientras que los que superan 0,90 suelen usar '
            'particiones aleatorias o variables del mismo periodo del retiro, como ocurrió en el Avance 1. Con '
            f'prevalencias entre {pct(om["panel"]["prevalencia"])} y {pct(um["panel"]["prevalencia"])}, se adopta '
            '0,75 como mínimo exigible. Atendiendo las observaciones de la tutoría, los objetivos específicos pasaron '
            'de tres a cuatro para incluir de forma explícita la evaluación con métricas de calidad y de protección de '
            'datos. Los criterios quedan así: '
            '(a) ROC-AUC de al menos 0,75 en la validación temporal de ambas instituciones; (b) recall de al menos '
            '0,75 en el umbral de riesgo medio, fijado con datos de entrenamiento para un objetivo de 0,80; (c) '
            'calibración que reduzca el puntaje de Brier; (d) al menos tres segmentos de carreras con diferencias '
            'significativas; (e) exactitud por ejecución de la consulta conversacional de al menos 85 %, con el '
            '100 % de las preguntas maliciosas contenidas; y (f) ninguna fuga de datos entre instituciones.'))

    # ── 1.3 ───────────────────────────────────────────────────────────────
    a(('h2', '1.3 Base conceptual'))
    a(('h3', '1.3.1 Supuestos epistemológicos y unidad de análisis'))
    a(('p', 'El trabajo adopta un enfoque pragmático-tecnológico: el conocimiento se valida por su capacidad de '
            'mejorar una práctica institucional concreta, no solo por describirla. Desde esta posición, el abandono se '
            'trata como un fenómeno observable en datos administrativos, cuya probabilidad puede estimarse y cuya '
            'estimación debe ser útil para decidir. Se aceptan dos limitaciones explícitas: un modelo predictivo '
            'identifica asociaciones y no causas, y su utilidad depende de que las personas lo entiendan; por eso el '
            'diseño incluye explicaciones por estudiante y un lenguaje sin tecnicismos.'))
    a(('p', 'La unidad de análisis es el **estudiante en un periodo académico**: cada fila del panel describe lo que se '
            'sabía de un estudiante al cierre de un periodo (o de un corte, en OULAD) y la etiqueta indica si abandonó '
            'en el periodo siguiente. Con esta definición, un mismo estudiante aporta tantas observaciones como '
            'periodos cursó, el modelo aprende tendencias de deterioro y la validación puede respetar el orden del '
            'tiempo, condición que Duro et al. (2026) señalan como necesaria para que el desempeño informado sea '
            'realista.'))
    a(('h3', '1.3.2 Teorías del abandono y variables del modelo'))
    a(('p', 'El modelo de integración de Tinto (1975) orienta las variables académicas: promedio del periodo, su '
            'tendencia, el peor promedio histórico, la asistencia y su racha a la baja. El modelo de Bean y Metzner '
            '(1985) justifica las variables externas: saldo pendiente y periodos en mora, porcentaje de beca, créditos '
            'matriculados y anticipación con que se matricula el estudiante. A ello se suman dos fuentes que los '
            'estudios recientes destacan: la actividad en el aula virtual y el cumplimiento de evaluaciones, cuyo '
            'aporte predictivo se documenta en universidades europeas (Vaarma y Li, 2024) y latinoamericanas '
            '(Marcolino et al., 2025). Las variables se comparan además con la cohorte, porque un promedio de siete '
            'significa algo distinto en una carrera exigente que en una que no lo es.'))
    a(('h3', '1.3.3 Aprendizaje automático para la predicción del abandono'))
    a(('p', 'Se comparan cuatro configuraciones de tres algoritmos. La **regresión logística** sirve de línea base interpretable. **Random Forest** '
            '(Breiman, 2001) combina árboles entrenados sobre muestras distintas y tolera relaciones no lineales; se '
            'prueba con pesos por clase y con sobremuestreo SMOTE (Chawla et al., 2002), dos formas de tratar el '
            'desbalance entre quienes abandonan y quienes no. **LightGBM** (Ke et al., 2017) construye árboles de '
            'manera secuencial con histogramas y es eficiente con tablas grandes; sus hiperparámetros se ajustan con '
            'Optuna (Akiba et al., 2019). Como la salida de estos modelos no es una probabilidad bien calibrada, se '
            'aplica la calibración de Platt (1999), y la explicación de cada predicción se obtiene con valores SHAP '
            '(Lundberg y Lee, 2017), que reparten la diferencia entre la probabilidad del estudiante y la media '
            'institucional entre sus variables.'))
    a(('p', 'Con clases desbalanceadas, la exactitud global engaña: un modelo que nunca alerta acertaría en más del '
            '90 % de los casos. Por eso se informan el ROC-AUC (capacidad de ordenar), el PR-AUC (precisión '
            'promedio sobre los positivos), el recall en los umbrales de alerta y el puntaje de Brier (calibración). '
            'Los umbrales no se fijan en 0,5, sino en el valor que alcanza un recall objetivo con datos de '
            'entrenamiento: 0,80 para el riesgo medio y 0,50 para el riesgo alto.'))
    a(('h3', '1.3.4 Segmentación de carreras'))
    a(('p', 'K-means agrupa observaciones minimizando la distancia a los centroides y ha servido para identificar '
            'patrones de comportamiento estudiantil en educación superior (Mohd Talib et al., 2023). En este trabajo '
            'la unidad no es el estudiante sino la carrera, descrita por su tasa histórica de abandono, promedio, '
            'asistencia y riesgo medio estimado por el modelo. La cantidad de grupos se elige con el coeficiente de '
            'silueta y se valida con remuestreo, con la comparación frente a un método jerárquico y a HDBSCAN, y con '
            'la prueba de Kruskal-Wallis sobre la tasa de abandono entre segmentos.'))
    a(('h3', '1.3.5 Consulta conversacional y gobierno de datos'))
    a(('p', 'Los sistemas NL2SQL traducen una pregunta en lenguaje natural a una consulta SQL. Los modelos de lenguaje '
            'de gran escala mejoraron esa traducción, sobre todo cuando reciben el esquema y ejemplos de contexto '
            '(Ascoli y Choi, 2025), pero también introducen riesgos: pueden inventar columnas, devolver cifras '
            'incorrectas o ser manipulados para leer datos que no corresponden. Por eso el motor de este trabajo '
            'responde primero con **métricas certificadas** (40 consultas fijas y verificadas) y solo recurre al modelo '
            'de lenguaje cuando la pregunta no coincide con ninguna; en ese caso, el SQL generado pasa por un '
            'validador de árbol sintáctico antes de ejecutarse con una cuenta que únicamente puede leer vistas.'))
    a(('p', 'El almacén sigue el modelo dimensional de Kimball y Ross (2013): una tabla de hechos por proceso y '
            'dimensiones compartidas. Sobre él, el aislamiento entre instituciones se resuelve en el motor de base de '
            'datos mediante vistas filtradas por el contexto de sesión, y no en la aplicación. Esta decisión responde a '
            'los principios de finalidad, minimización, seguridad y responsabilidad proactiva de la LOPDP (Asamblea '
            'Nacional del Ecuador, 2021).'))

    # ── 1.3.6 tabla comparativa ───────────────────────────────────────────
    a(('h3', '1.3.6 Comparación con trabajos previos'))
    a(('p', 'La {T:comparacion} contrasta catorce estudios con el caso práctico. Para cada uno se registra el contexto, la '
            'técnica, el resultado principal y si el trabajo integra la predicción en un sistema usable, con consulta '
            'en lenguaje natural y con control de acceso a los datos; la última columna indica qué toma o en qué se '
            'diferencia este proyecto.'))
    filas = [
        ['Gutierrez-Pachas et al. (2023)', 'Universidad peruana, 13 años, 6 departamentos', 'Aprendizaje automático y '
         'análisis de supervivencia', 'El riesgo varía por facultad, género y nivel socioeconómico', 'No / No / No',
         'Se adopta el análisis por unidad académica (segmentación)'],
        ['Núñez-Naranjo (2024)', 'Universidad privada ecuatoriana, 1.078 estudiantes', 'Regresión logística '
         'multinivel', 'Abandono de 44,90 %; 76,44 % de precisión', 'No / No / No', 'Evidencia local; aquí '
         'se predice por periodo y se integra en un sistema'],
        ['Carballo-Mendívil et al. (2025)', 'Universidad pública mexicana, cerca de 40.000 estudiantes de primer '
         'año', 'XGBoost con datos previos a la matrícula', 'ROC-AUC de 0,69 y recall de 0,88 en las cohortes '
         '2023 y 2024', 'Parcial / No / No', 'Valida el uso de prueba prospectiva; aquí se suma la trayectoria'],
        ['Kok et al. (2024)', 'Gran volumen de datos institucionales', 'Ensambles y analítica de big data',
         'Precisión cercana al 100 %; el rendimiento es el mayor predictor', 'No / No / No', 'Se evita la '
         'exactitud como métrica principal por el desbalance'],
        ['Rabelo y Zárate (2025)', 'Educación superior en Brasil', 'Ensamble de logística, redes y árbol', 'Detecta '
         '98,1 % de los abandonos', 'No / No / No', 'Se reporta además precisión y calibración'],
        ['Marcolino et al. (2025)', 'Registros de Moodle', 'Optimización de hiperparámetros', 'La actividad en el '
         'aula virtual anticipa el abandono', 'No / No / No', 'Se incorpora la actividad del aula virtual'],
        ['Vaarma y Li (2024)', 'Universidad finlandesa, Moodle y expediente', 'Tres modelos de aprendizaje '
         'automático, predicción mensual', 'Créditos acumulados, asignaturas reprobadas y actividad en Moodle son '
         'clave', 'No / No / No', 'Se adoptan cortes de seguimiento dentro del periodo'],
        ['Realinho et al. (2022)', 'Politécnico portugués, 4.424 estudiantes', 'Conjunto de datos para '
         'clasificación', 'Variables académicas y socioeconómicas al cierre de cada semestre', 'Parcial / No / No',
         'Se toma como referencia para el diseño de variables'],
        ['Kuzilek et al. (2017)', 'Open University, 32.593 matrículas en módulos (28.785 estudiantes)', 'Conjunto público de analítica del '
         'aprendizaje', 'Datos demográficos, evaluaciones y clics anonimizados', 'No aplica', 'Segunda institución '
         'real del prototipo (OULAD)'],
        ['Duro et al. (2026)', 'Revisión de la literatura', 'Aprendizaje automático y profundo', 'Los árboles '
         'compiten con redes profundas con datos moderados', 'No aplica', 'Justifica comparar ensambles de árboles '
         'y validar en el tiempo'],
        ['Mohd Talib et al. (2023)', 'Educación superior, Malasia', 'K-means y SVM', 'Patrones de comportamiento '
         'estudiantil', 'No / No / No', 'Se aplica K-means a carreras, con validación de estabilidad'],
        ['Orrego Granados et al. (2022)', 'Universidad peruana', 'Análisis visual y predictivo', 'La visualización '
         'complementa al modelo', 'Parcial / No / No', 'El panel y la ficha leen la misma fuente gobernada'],
        ['Ascoli y Choi (2025)', 'Bases de datos genéricas', 'NL2SQL conversacional con LLM', 'Las estrategias de '
         'contexto mejoran la exactitud', 'No aplica / Sí / No', 'Se añaden métricas certificadas, validador y '
         'aislamiento'],
        ['Sequeira et al. (2024)', 'IES, revisión sistemática', 'Hoja de ruta de inteligencia de negocios', 'La '
         'brecha de habilidades frena la adopción', 'No aplica', 'Motiva la consulta en lenguaje natural'],
    ]
    a(('tab', 'comparacion', 'Comparación de Trabajos Previos frente al Caso Práctico',
       ['Estudio', 'Contexto y datos', 'Técnica', 'Resultado principal', 'Sistema / NL / Gobierno', 'Aporte al caso'],
       filas, 'Sistema: la predicción se integra en una aplicación usable; NL: consulta en lenguaje natural; '
       'Gobierno: control de acceso y aislamiento de datos. Elaboración propia a partir de los estudios citados.',
       [2.6, 2.7, 2.5, 3.1, 1.9, 3.2]))
    a(('p', 'La comparación deja ver tres patrones. Primero, los estudios predictivos informan desempeños muy '
            'distintos (de 76 % a casi 100 %) porque usan métricas, horizontes y esquemas de validación '
            'diferentes; los valores más altos suelen provenir de particiones aleatorias que mezclan periodos, lo que '
            'sobrestima lo que ocurrirá con una cohorte futura. Este trabajo reserva los periodos más recientes como '
            'prueba y añade una evaluación prospectiva, con resultados más modestos pero comparables con un uso real. '
            'Segundo, ningún estudio predictivo revisado entrega la predicción dentro de un sistema con roles, '
            'explicación por estudiante y registro del acompañamiento. Tercero, los trabajos de NL2SQL y de '
            'inteligencia de negocios no tratan el aislamiento entre instituciones ni la protección de datos '
            'estudiantiles.'))
    a(('h3', '1.3.7 Aporte, beneficios y utilidad del trabajo'))
    a(('p', 'El aporte del caso es la integración, bajo una sola arquitectura gobernada, de cuatro piezas que la '
            'literatura resuelve por separado: un modelo de abandono calibrado y explicable, una segmentación de '
            'carreras, una consulta conversacional con respuestas certificadas y un panel por roles. Las cuatro leen '
            'las mismas vistas del almacén, de modo que la cifra del panel y la del chat provienen de la misma fuente. '
            'El sistema se '
            'adapta a otra institución agregando un perfil de mapeo, como se comprobó con OULAD, sin reescribir el '
            f'motor; con ese perfil, el mismo código construyó un panel de {ent(om["panel"]["filas"])} registros '
            f'reales ({ent(om["panel"]["etiquetadas"])} etiquetados) y entrenó un modelo de {om["n_variables"]} '
            'variables. Su utilidad práctica es servir de herramienta de apoyo a '
            'la decisión y de arquitectura de referencia para las IES ecuatorianas que quieran pasar de medir el '
            'abandono a anticiparlo.'))
    return b
