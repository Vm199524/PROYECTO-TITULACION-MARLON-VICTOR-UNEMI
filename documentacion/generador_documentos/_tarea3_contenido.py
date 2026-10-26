# -*- coding: utf-8 -*-
"""
Contenido de la Tarea 3 de Redacción de Investigación de Textos Académicos: estado del arte del trabajo
de titulación (planteamiento corregido, matriz de congruencia, antecedentes internacionales, nacionales
y locales, estado del arte por ejes, contexto, bases teóricas, términos, comparación crítica, vacío,
metodología y gestión bibliográfica).

Las cifras del prototipo se leen de los resultados del sistema (_datos.py); las de los antecedentes, de
la matriz de extracción verificada (documentacion/literatura/trabajos_previos.json) y de las fuentes.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from pathlib import Path

from _datos import O, RAIZ, U, ent, f, pct

TITULO = ('Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje '
          'automático y consulta conversacional')
DRIVE = 'https://drive.google.com/drive/folders/1ZOVwEslSaSjJbUeS1RCL1q3BDyVea9tT'
REPOSITORIO = 'https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI'
CAPTURA_ZOTERO = RAIZ / 'documentacion' / 'evidencias' / 'zotero_coleccion.png'

REFERENCIAS = [
    'Asamblea Nacional del Ecuador. (2021). *Ley Orgánica de Protección de Datos Personales*. Registro Oficial, '
    'Quinto Suplemento 459, 26 de mayo de 2021.',
    'Ascoli, B. G., y Choi, J. D. (2025). Advancing conversational text-to-SQL: Context strategies and model '
    'integration with large language models. *Future Internet, 17*(11), 527. https://doi.org/10.3390/fi17110527',
    'Bean, J. P., y Metzner, B. S. (1985). A conceptual model of nontraditional undergraduate student attrition. '
    '*Review of Educational Research, 55*(4), 485-540. https://doi.org/10.3102/00346543055004485',
    'Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5-32. https://doi.org/10.1023/A:1010933404324',
    'Brooke, J. (1996). SUS: A "quick and dirty" usability scale. En P. W. Jordan, B. Thomas, B. A. Weerdmeester y '
    'I. L. McClelland (Eds.), *Usability evaluation in industry* (pp. 189-194). Taylor & Francis.',
    'Carballo-Mendívil, B., Arellano-González, A., Ríos-Vázquez, N. J., y Lizardi-Duarte, M. del P. (2025). '
    'Predicting student dropout from day one: XGBoost-based early warning system using pre-enrollment data. '
    '*Applied Sciences, 15*(16), 9202. https://doi.org/10.3390/app15169202',
    'Dávila, G., Haro, J., González-Eras, A., Ruiz Vivanco, O., y Guamán Coronel, D. (2023). Student dropout '
    'prediction in high education, using machine learning and deep learning models: Case of Ecuadorian university. '
    'En *2023 International Conference on Computational Science and Computational Intelligence (CSCI)* '
    '(pp. 1677-1684). IEEE. https://doi.org/10.1109/CSCI62032.2023.00277',
    'Duro, B., Gomes, A., Correia, F. B., Borges, A. R., y Bernardino, J. (2026). Machine learning and deep learning '
    'for dropout prediction in higher education: A review. *Computers, 15*(3), 164. '
    'https://doi.org/10.3390/computers15030164',
    'Gama, J., Žliobaitė, I., Bifet, A., Pechenizkiy, M., y Bouchachia, A. (2014). A survey on concept drift '
    'adaptation. *ACM Computing Surveys, 46*(4), 44. https://doi.org/10.1145/2523813',
    'Gutierrez-Pachas, D. A., Garcia-Zanabria, G., Cuadros-Vargas, E., Camara-Chavez, G., y Gomez-Nieto, E. (2023). '
    'Supporting decision-making process on higher education dropout by analyzing academic, socioeconomic, and '
    'equity factors through machine learning and survival analysis methods in the Latin American context. '
    '*Education Sciences, 13*(2), 154. https://doi.org/10.3390/educsci13020154',
    'Heredia-Jimenez, V., Jiménez Macías, A. A., Ortiz Rojas, M., Imaz Marín, J., Moreno-Marcos, P. M., Muñoz '
    'Merino, P. J., y Delgado Kloos, C. (2020). An early warning dropout model in higher education degree programs: '
    'A case study in Ecuador. En *Proceedings of the Workshop on Adoption, Adaptation and Pilots of Learning '
    'Analytics in Under-represented Regions (LAUR 2020)* (CEUR Workshop Proceedings, Vol. 2704, pp. 58-67). '
    'CEUR-WS.org. https://ceur-ws.org/Vol-2704/paper5.pdf',
    'Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., y Liu, T.-Y. (2017). LightGBM: A highly '
    'efficient gradient boosting decision tree. En I. Guyon et al. (Eds.), *Advances in Neural Information '
    'Processing Systems 30* (pp. 3146-3154). Curran Associates.',
    'Kimball, R., y Ross, M. (2013). *The data warehouse toolkit: The definitive guide to dimensional modeling* '
    '(3.ª ed.). Wiley.',
    'Komljenovic, J., Sellar, S., y Birch, K. (2025). Turning universities into data-driven organisations: Seven '
    'dimensions of change. *Higher Education, 89*(5), 1369-1386. https://doi.org/10.1007/s10734-024-01277-z',
    'Kuzilek, J., Hlosta, M., y Zdrahal, Z. (2017). Open University Learning Analytics dataset. *Scientific Data, '
    '4*, 170171. https://doi.org/10.1038/sdata.2017.171',
    'Llerena Nieto, E. M., y Mayorga Villegas, V. H. (2026). Modelo conceptual de la deserción estudiantil en '
    'educación superior técnica basado en factores académicos, socioeconómicos e institucionales. *LATAM Revista '
    'Latinoamericana de Ciencias Sociales y Humanidades, 7*(2), 1728-1742. https://doi.org/10.56712/latam.v7i2.5757',
    'Lundberg, S. M., y Lee, S.-I. (2017). A unified approach to interpreting model predictions. En I. Guyon et al. '
    '(Eds.), *Advances in Neural Information Processing Systems 30* (pp. 4765-4774). Curran Associates.',
    'Marcolino, M. R., Porto, T. R., Primo, T. T., Targino, R., Ramos, V., Queiroga, E. M., Munoz, R., y Cechinel, '
    'C. (2025). Student dropout prediction through machine learning optimization: Insights from Moodle log data. '
    '*Scientific Reports, 15*(1), 9840. https://doi.org/10.1038/s41598-025-93918-1',
    'Mohd Talib, N. I., Abd Majid, N. A., y Sahran, S. (2023). Identification of student behavioral patterns in '
    'higher education using K-means clustering and support vector machine. *Applied Sciences, 13*(5), 3267. '
    'https://doi.org/10.3390/app13053267',
    'Núñez-Naranjo, A. F. (2024). Analysis of the determinant factors in university dropout: A case study of '
    'Ecuador. *Frontiers in Education, 9*, 1444534. https://doi.org/10.3389/feduc.2024.1444534',
    'Pilco-Salazar, A. M., y Bonilla-Novillo, S. M. (2026). Modelado predictivo de la deserción estudiantil en el '
    'Instituto Superior Tecnológico General Eloy Alfaro, Ecuador. *Ingenium et Potentia, 8*(14), 235-265. '
    'https://doi.org/10.35381/i.p.v8i14.5061',
    'Platt, J. C. (1999). Probabilistic outputs for support vector machines and comparisons to regularized '
    'likelihood methods. En A. J. Smola, P. Bartlett, B. Schölkopf y D. Schuurmans (Eds.), *Advances in large '
    'margin classifiers* (pp. 61-74). MIT Press.',
    'Rabelo, A. M., y Zárate, L. E. (2025). A model for predicting dropout of higher education students. *Data '
    'Science and Management, 8*(1), 72-85. https://doi.org/10.1016/j.dsm.2024.07.001',
    'Realinho, V., Machado, J., Baptista, L., y Martins, M. V. (2022). Predicting student dropout and academic '
    'success. *Data, 7*(11), 146. https://doi.org/10.3390/data7110146',
    'Santillán Tasigchana, M. A., y Meneses Freire, M. A. (2026). Análisis de los factores asociados a la deserción '
    'estudiantil en la Facultad de Administración de Empresas en una universidad pública del Ecuador. *Technology '
    'Rain Journal, 5*(2), e139. https://doi.org/10.55204/trj.v5i2.e139',
    'Sequeira, R., Reis, A., Alves, P., y Branco, F. (2024). Roadmap for implementing business intelligence systems '
    'in higher education institutions: Systematic literature review. *Information, 15*(4), 208. '
    'https://doi.org/10.3390/info15040208',
    'Superintendencia de Protección de Datos Personales. (2025). *Guía de gestión de riesgos y evaluación de '
    'impacto del tratamiento de datos personales* (Resolución SPDP-SPD-2025-0003-R).',
    'Superintendencia de Protección de Datos Personales. (2026). *Norma general para la garantía del derecho de '
    'protección de datos personales en el uso de sistemas de inteligencia artificial* (Resolución '
    'SPDP-SPD-2026-0009-R).',
    'Tinto, V. (1975). Dropout from higher education: A theoretical synthesis of recent research. *Review of '
    'Educational Research, 45*(1), 89-125. https://doi.org/10.3102/00346543045001089',
    'Vaarma, M., y Li, H. (2024). Predicting student dropouts with machine learning: An empirical study in Finnish '
    'higher education. *Technology in Society, 76*, 102474. https://doi.org/10.1016/j.techsoc.2024.102474',
    'Villar, A., y Robledo Velini de Andrade, C. (2024). Supervised machine learning algorithms for predicting '
    'student dropout and academic success: A comparative study. *Discover Artificial Intelligence, 4*(1), 2. '
    'https://doi.org/10.1007/s44163-023-00079-z',
    'Wirth, R., y Hipp, J. (2000). CRISP-DM: Towards a standard process model for data mining. En *Proceedings of '
    'the 4th International Conference on the Practical Application of Knowledge Discovery and Data Mining* '
    '(pp. 29-39). Practical Application Company.',
    'Zaharia, M., Chen, A., Davidson, A., Ghodsi, A., Hong, S. A., Konwinski, A., Murching, S., Nykodym, T., '
    'Ogilvie, P., Parkhe, M., Xie, F., y Zumar, C. (2018). Accelerating the machine learning lifecycle with MLflow. '
    '*IEEE Data Engineering Bulletin, 41*(4), 39-45.',
]


def bloques() -> list[tuple]:
    um, om = U['m'], O['m']
    ut, ot = um['validacion_temporal'], om['validacion_temporal']
    ro = (om.get('origen_movil') or {}).get('resumen') or {}
    ru = (um.get('origen_movil') or {}).get('resumen') or {}
    b: list[tuple] = []
    a = b.append

    # ── 1 ─────────────────────────────────────────────────────────────────
    a(('h1', '1. Título aprobado'))
    a(('p', f'**{TITULO}.**'))
    a(('p', 'El título fue aprobado en la asignatura de Desarrollo del Trabajo de Titulación y no cambia en este '
            'avance. Delimita el objeto (un prototipo de sistema web), el fenómeno (el abandono de estudiantes '
            'universitarios) y las dos técnicas que lo distinguen: el aprendizaje automático para anticipar el riesgo '
            'y la consulta conversacional para que una autoridad sin perfil técnico pregunte por los resultados en '
            'español.'))

    # ── 2 ─────────────────────────────────────────────────────────────────
    a(('h1', '2. Planteamiento del problema'))
    a(('h2', '2.1 Problema'))
    a(('p', 'El abandono de los estudios universitarios mide la eficiencia de un sistema de educación superior y, al '
            'mismo tiempo, es una pérdida personal para quien no concluye su carrera. En el Ecuador el problema está '
            'cuantificado: en cinco cohortes de una universidad privada, 484 de 1.078 estudiantes admitidos '
            'abandonaron, con una probabilidad estimada de abandono del 44,90 % asociada a factores personales, '
            'familiares, económicos, académicos e institucionales (Núñez-Naranjo, 2024). Una síntesis reciente '
            'elaborada en la Universidad Estatal de Milagro (UNEMI) ubica las condiciones socioeconómicas como el '
            'principal detonante del retiro y recomienda sistemas de alerta temprana (Llerena Nieto y Mayorga '
            'Villegas, 2026).'))
    a(('p', 'Las universidades ya registran las señales que anteceden al abandono: caídas de rendimiento, inasistencias, '
            'deudas, menor carga matriculada o desconexión del aula virtual. Sin embargo, esos registros están '
            'repartidos en sistemas que no se comunican y se consultan para conocer el estado actual del estudiante, '
            'no su trayectoria (Komljenovic et al., 2025). Obtener una cifra que combine varias fuentes exige pedirla '
            'al área de tecnología, porque la reportería tradicional requiere SQL o herramientas especializadas '
            '(Sequeira et al., 2024). El resultado es que el retiro se detecta cuando el estudiante ya dejó de '
            'asistir y la oportunidad de acompañarlo pasó.'))
    a(('p', 'La literatura muestra que el aprendizaje automático anticipa el abandono con datos institucionales '
            '(Duro et al., 2026), pero entrega modelos evaluados en un cuaderno de investigación, casi siempre con '
            'particiones aleatorias y sin un medio para que la autoridad los consulte, los entienda y los use con '
            'controles de privacidad. El problema de este trabajo se formula así: **la detección del riesgo de '
            'abandono en las universidades ecuatorianas es tardía porque la trayectoria académica que ya registran no '
            'se convierte en alertas tempranas confiables, explicables y consultables por quienes deciden, con la '
            'protección que exige la Ley Orgánica de Protección de Datos Personales (LOPDP).**'))
    a(('h2', '2.2 Preguntas de investigación'))
    a(('p', '**Pregunta general.** ¿De qué manera un prototipo de sistema web basado en aprendizaje automático y '
            'consulta conversacional permite identificar tempranamente a los estudiantes universitarios en riesgo de '
            'abandono y apoyar las decisiones de las autoridades académicas?'))
    a(('p', '**Preguntas específicas.**'))
    a(('ul', ['¿Qué variables de trayectoria, matrícula, aula virtual, evaluaciones y cartera se asocian al abandono, y '
              'qué requerimientos debe cumplir un sistema que las use?',
              '¿Qué desempeño alcanza un modelo calibrado y explicable cuando se valida en periodos que no vio durante '
              'el entrenamiento, con datos de prueba de la UNEMI y con datos reales?',
              '¿Cómo se integran la predicción, la segmentación de carreras y la consulta conversacional en un sistema '
              'web por roles que proteja los datos estudiantiles?',
              '¿En qué medida el prototipo cumple los criterios de calidad predictiva, de exactitud de la consulta y de '
              'protección de datos fijados antes de evaluarlo?']))
    a(('h2', '2.3 Objetivos'))
    a(('p', '**Objetivo general.** Desarrollar un prototipo de sistema web que prediga el abandono de estudiantes '
            'universitarios mediante aprendizaje automático y permita consultar sus resultados en lenguaje natural, '
            'para que las autoridades académicas y el personal de bienestar estudiantil identifiquen tempranamente a '
            'quienes están en riesgo y prioricen su acompañamiento.'))
    a(('p', '**Objetivos específicos.**'))
    a(('ul', ['Analizar los procesos de seguimiento académico y las variables de trayectoria, matrícula, aula virtual, '
              'evaluaciones y cartera asociadas al abandono, para derivar los requerimientos del sistema.',
              'Construir y validar un modelo de predicción calibrado y explicable, mediante validación cruzada agrupada '
              'por estudiante, validación temporal por periodo y evaluación prospectiva, sobre datos de prueba de la '
              'UNEMI y sobre el conjunto real OULAD.',
              'Implementar el sistema web por roles, con panel institucional, ficha explicada del estudiante, '
              'segmentación de carreras y consulta conversacional sobre vistas gobernadas del almacén de datos.',
              'Evaluar el prototipo con métricas predictivas (ROC-AUC, PR-AUC, recall y calibración), de exactitud de '
              'la consulta conversacional y de protección de datos, contrastándolas con los criterios de aceptación.']))
    a(('p', 'Las correcciones de este avance consisten en alinear cada pregunta específica con un objetivo, usar verbos '
            'de la taxonomía de Bloom que crecen en complejidad (analizar, construir, implementar, evaluar) y explicitar '
            'en el segundo objetivo la validación por periodo que recomendó la tutoría.'))
    a(('h2', '2.4 Justificación'))
    a(('p', 'El proyecto es **conveniente** porque traslada la gestión de la permanencia de la medición posterior a la '
            'anticipación: cada periodo, el decanato, la dirección de carrera y bienestar estudiantil sabrían qué '
            'estudiantes tienen mayor probabilidad de no continuar, por qué y en qué carreras se concentra el riesgo. '
            'Tiene **relevancia social** porque el acompañamiento oportuno beneficia a estudiantes que hoy se retiran '
            'sin haber recibido apoyo y porque la educación superior pública se financia con recursos del Estado. '
            'Tiene **valor teórico y metodológico** porque contrasta con datos las teorías de Tinto (1975) y de Bean '
            'y Metzner (1985) y porque adopta prácticas de validación que la literatura reclama y pocas veces aplica: '
            'evaluación temporal, calibración y reporte del recall (Duro et al., 2026). Tiene **utilidad práctica** '
            'porque el producto es un sistema funcionando, con código abierto para la institución, y es **viable** '
            'porque usa datos que las universidades ya registran, herramientas libres y una arquitectura que cumple '
            'la LOPDP desde el diseño.'))

    # ── 3 ─────────────────────────────────────────────────────────────────
    a(('h1', '3. Matriz de congruencia'))
    a(('p', 'La {T:congruencia} verifica que el problema, las preguntas, los objetivos, las variables, los indicadores y '
            'los instrumentos guarden coherencia entre sí. Cada fila corresponde a una pregunta y a su objetivo.'))
    a(('tab', 'congruencia', 'Matriz de Congruencia Actualizada',
       ['Pregunta', 'Objetivo', 'Variable o categoría', 'Indicadores', 'Técnica e instrumento'],
       [['General: ¿cómo un prototipo web con aprendizaje automático y consulta conversacional permite identificar '
         'tempranamente el riesgo de abandono?', 'Desarrollar el prototipo (Crear)', 'Alerta temprana del abandono '
                                                                                      'estudiantil',
         'Cumplimiento de los criterios de aceptación', 'CRISP-DM; pipeline y pruebas automatizadas'],
        ['PE1: variables asociadas y requerimientos', 'OE1: Analizar', 'Factores del abandono; requerimientos',
         'Tasa de abandono por variable; RF y RNF verificables', 'Análisis documental y exploratorio; historias de '
                                                                 'usuario'],
        ['PE2: desempeño en periodos no vistos', 'OE2: Construir y validar', 'Predicción del riesgo',
         'ROC-AUC, PR-AUC, recall, Brier, ROC-AUC por periodo y por carrera', 'Validación cruzada agrupada, temporal, '
                                                                            'origen móvil y prospectiva'],
        ['PE3: integración en un sistema por roles', 'OE3: Implementar', 'Sistema web y consulta conversacional',
         'Servicios operativos; roles; aislamiento por institución', 'Desarrollo incremental; pruebas de integración'],
        ['PE4: cumplimiento de criterios', 'OE4: Evaluar', 'Calidad predictiva, exactitud de la consulta, protección '
                                                           'de datos y usabilidad',
         'ROC-AUC ≥ 0,75; recall ≥ 0,75; exactitud ≥ 85 %; 0 fugas; SUS ≥ 68', 'Conjunto dorado de preguntas; '
                                                                                'pruebas de ataque; escala SUS']],
       'Elaboración propia.', [3.6, 2.6, 3.0, 3.6, 3.2]))

    # ── 4 ─────────────────────────────────────────────────────────────────
    a(('h1', '4. Antecedentes'))
    a(('p', 'Los antecedentes se seleccionaron con cinco búsquedas sistemáticas en Scopus y búsquedas dirigidas en '
            'Crossref y en repositorios latinoamericanos, con estudios de 2020 a 2026 y algunas fuentes clásicas que '
            'sustentan la teoría. Cada estudio se leyó completo y se registró en una matriz de extracción con siete '
            'preguntas: problema y técnica, datos, validación, tecnologías, arquitectura, limitaciones y aporte al '
            'presente trabajo. Se organizan por su ámbito geográfico.'))
    a(('h2', '4.1 Antecedentes internacionales'))
    a(('p', 'La revisión de Duro et al. (2026), sobre 61 estudios publicados entre 2018 y 2025, ofrece el mejor '
            'panorama del campo. Encontró que domina el aprendizaje automático tradicional (Random Forest en 33 '
            'estudios, regresión logística en 27 y XGBoost en 12), que la mayoría usa datos de una sola institución '
            'con clasificación estática y que 48 estudios informan la exactitud, mientras solo uno informa el PR-AUC. '
            'Su conclusión es metodológica: pesa más el tipo de dato que el algoritmo, y hacen falta validación '
            'temporal y umbrales justificados. Este diagnóstico orientó el diseño de la validación del presente '
            'trabajo.'))
    a(('p', 'En México, Carballo-Mendívil et al. (2025) construyeron una alerta temprana con datos previos a la '
            'matrícula de 38.932 estudiantes de primer año (cohortes 2014 a 2024). Compararon regresión logística, '
            'Random Forest, LightGBM y XGBoost, y eligieron XGBoost por su recall (0,88 con un umbral de 0,338), '
            'aunque su ROC-AUC fue de 0,69. El estudio prueba que se puede alertar desde el primer día, pero con una '
            'sola fotografía al ingreso: no sigue la trayectoria. En Brasil, Marcolino et al. (2025) usaron los '
            'registros semanales de Moodle de 567 casos de 23 cursos; con CatBoost alcanzaron un F1 de 0,86 en una '
            'partición aleatoria, pero el F1 no superó 0,50 en cursos que el modelo no había visto. Esa caída es la '
            'evidencia más clara de que las particiones aleatorias sobrestiman el desempeño futuro.'))
    a(('p', 'Rabelo y Zárate (2025) son de los pocos que validan en el tiempo: con una universidad privada brasileña '
            'entrenaron con 2018 y probaron con 2019; un ensamble de árbol de decisión, regresión logística y red '
            'neuronal detectó el 92,6 % de los desertores, frente al 91,8 % de Random Forest. Realinho et al. (2022) '
            'publicaron un conjunto de 4.424 estudiantes del Instituto Politécnico de Portalegre, con variables '
            'demográficas, socioeconómicas y académicas, que hoy es referencia del campo, y Villar y Robledo Velini de '
            'Andrade (2024), con datos de ese tipo, mostraron que LightGBM y CatBoost ajustados con Optuna superan a '
            'los clasificadores tradicionales. En Finlandia, Vaarma y Li (2024) encontraron que la actividad en el '
            'sistema de gestión del aprendizaje está entre los predictores más importantes del abandono.'))
    a(('p', 'En América Latina, Gutierrez-Pachas et al. (2023) combinaron aprendizaje automático y análisis de '
            'supervivencia en una universidad peruana para estimar no solo quién abandona sino cuándo, y mostraron que '
            'el riesgo cambia entre facultades. En segmentación, Mohd Talib et al. (2023) agruparon a 140 estudiantes '
            'con K-means, aunque sus grupos no difirieron de forma significativa en rendimiento (p = 0,454), lo que '
            'advierte sobre la necesidad de validar los segmentos. En la consulta conversacional, Ascoli y Choi '
            '(2025) lograron una exactitud por ejecución de 70,2 % en el banco CoSQL al traducir preguntas de varios '
            'turnos a SQL; el resultado confirma que los modelos de lenguaje mejoran con contexto, pero también que '
            'tres de cada diez respuestas pueden ser incorrectas. Por último, Sequeira et al. (2024) revisaron la '
            'implantación de inteligencia de negocios en universidades y encontraron que solo 4 de 10 estudios la '
            'implementan y que ninguno propone una hoja de ruta, mientras Komljenovic et al. (2025) describen los '
            'obstáculos organizacionales y legales de volverse una universidad basada en datos.'))
    a(('h2', '4.2 Antecedentes nacionales'))
    a(('p', 'En el Ecuador, el estudio de mayor alcance sobre los determinantes del abandono es el de Núñez-Naranjo '
            '(2024), que aplicó regresión logística multinivel a 1.078 estudiantes admitidos en cinco cohortes de una '
            'universidad privada; 484 abandonaron y la probabilidad estimada de abandono fue del 44,90 %. Su aporte es '
            'cuantificar el problema y su multicausalidad; su límite, para fines de alerta, es que explica el pasado '
            'sin entregar una predicción por estudiante y por periodo.'))
    a(('p', 'Heredia-Jimenez et al. (2020) diseñaron un modelo de alerta temprana con los registros de todas las '
            'carreras de una universidad pública ecuatoriana entre 2000 y 2019. Su hallazgo es relevante para este '
            'trabajo: los datos académicos por sí solos, sin variables sociodemográficas ni de ingreso, produjeron '
            'predicciones más confiables, incluso con un solo semestre cursado. Dávila et al. (2023), de la '
            'Universidad Técnica Particular de Loja, compararon modelos de aprendizaje automático y de aprendizaje '
            'profundo para predecir la deserción en una universidad ecuatoriana, lo que confirma el interés local en '
            'la técnica.'))
    a(('p', 'Los estudios más recientes muestran resultados modestos cuando la información es limitada. Pilco-Salazar '
            'y Bonilla-Novillo (2026) aplicaron regresión logística binaria a 684 estudiantes del Instituto Superior '
            'Tecnológico General Eloy Alfaro, entre los periodos 2021-I y 2025-I, y obtuvieron una exactitud de 0,665 '
            'y un ROC-AUC de 0,6623 con un modelo final de tres variables (género, ocupación y estado civil). '
            'Santillán Tasigchana y Meneses Freire (2026) encuestaron a 300 estudiantes de una facultad de '
            'administración de una universidad pública, validaron el cuestionario con la V de Aiken y el alfa de '
            'Cronbach, y con análisis factorial, regresión logística multinomial y Random Forest identificaron las '
            'condiciones académico-económicas como el factor principal. Ninguno de los estudios nacionales revisados '
            'integra el modelo en un sistema de información ni lo pone a disposición de las autoridades.'))
    a(('h2', '4.3 Antecedentes locales'))
    a(('p', 'En el ámbito local, Llerena Nieto y Mayorga Villegas (2026), de la Facultad de Posgrado de la UNEMI, '
            'construyeron un modelo conceptual de la deserción en la educación superior técnica a partir de una '
            'revisión sistemática con el método PRISMA (26 publicaciones incluidas de 56 registros). Concluyen que las '
            'condiciones socioeconómicas son el principal detonante, que el estrés académico y las brechas de '
            'conocimientos previos se asocian a la intención de abandonar, y recomiendan sistemas de alerta temprana '
            'combinados con apoyo financiero y acompañamiento psicopedagógico. Es un antecedente conceptual, sin '
            'datos de la UNEMI.'))
    a(('p', 'La búsqueda no encontró estudios empíricos publicados que predigan el abandono con datos de estudiantes '
            'de la UNEMI o de la ciudad de Milagro. Esa ausencia es parte del vacío que atiende este trabajo: el '
            'prototipo se construyó con datos de prueba que reproducen la estructura de la universidad y quedó listo '
            'para validarse con una carrera real, cuando la institución lo autorice, bajo el procedimiento de '
            'anonimización de su documento de gobierno de datos.'))

    # ── 5 ─────────────────────────────────────────────────────────────────
    a(('h1', '5. Estado del arte'))
    a(('p', 'El estado del arte se organiza en seis ejes temáticos que corresponden a las piezas del prototipo. En '
            'cada eje se sintetiza lo que la literatura ya resolvió, en qué coincide, en qué discrepa y qué deja '
            'abierto.'))
    a(('h2', '5.1 Eje 1: modelos para predecir el abandono'))
    a(('p', 'Hay consenso en que los ensambles basados en árboles (Random Forest y *gradient boosting*) ofrecen el mejor '
            'equilibrio entre desempeño e interpretabilidad para datos tabulares (Duro et al., 2026; Villar y Robledo '
            'Velini de Andrade, 2024). Random Forest promedia muchos árboles entrenados con muestras distintas '
            '(Breiman, 2001), mientras que LightGBM construye árboles en secuencia, cada uno corrigiendo el error de '
            'los anteriores, con una implementación eficiente en memoria y tiempo (Ke et al., 2017). La regresión '
            'logística sigue siendo la línea base de referencia y, en algunos estudios, compite de cerca con los '
            'ensambles (Rabelo y Zárate, 2025; Núñez-Naranjo, 2024).'))
    a(('p', 'La discrepancia está en las cifras, no en los algoritmos. Los estudios que informan exactitudes '
            'superiores a 0,90 suelen evaluar con particiones aleatorias o con variables del mismo periodo del '
            'retiro, mientras que los que validan con cohortes posteriores informan valores cercanos a 0,70 '
            '(Carballo-Mendívil et al., 2025; Pilco-Salazar y Bonilla-Novillo, 2026). La diferencia no indica que un '
            'algoritmo sea mejor, sino que la forma de validar cambia la conclusión.'))
    a(('h2', '5.2 Eje 2: variables que anticipan el abandono'))
    a(('p', 'Los estudios coinciden en tres familias de variables. Las académicas (promedio, su tendencia, '
            'reprobación y asistencia) son las más estables entre contextos (Heredia-Jimenez et al., 2020; Rabelo '
            'y Zárate, 2025). Las de actividad en el aula virtual anticipan el retiro antes '
            'de que se refleje en las notas (Marcolino et al., 2025; Vaarma y Li, 2024). Las socioeconómicas tienen '
            'peso explicativo en los estudios basados en encuestas (Santillán Tasigchana y Meneses Freire, 2026; '
            'Llerena Nieto y Mayorga Villegas, 2026), pero no siempre están disponibles en los registros '
            'institucionales. Este trabajo usa las tres familias cuando existen y declara su ausencia cuando no.'))
    a(('h2', '5.3 Eje 3: validación, calibración, explicación y equidad'))
    a(('p', 'La revisión de Duro et al. (2026) identifica la validación temporal como la práctica más necesaria y menos '
            'aplicada. Rabelo y Zárate (2025) y Carballo-Mendívil et al. (2025) son excepciones que muestran el costo '
            'de validar con el futuro: cifras más bajas pero más creíbles. La calibración, que convierte un puntaje en '
            'una probabilidad interpretable, casi no se informa, aunque el escalado de Platt (1999) es un método '
            'establecido. La explicación local con valores SHAP (Lundberg y Lee, 2017) se ha vuelto habitual para que '
            'un usuario no técnico entienda cada predicción, y Gutierrez-Pachas et al. (2023) muestran que el riesgo '
            'difiere entre grupos, lo que obliga a revisar el desempeño por subgrupo.'))
    a(('h2', '5.4 Eje 4: segmentación de carreras'))
    a(('p', 'La segmentación con K-means es frecuente para describir perfiles, pero su validación es débil: en Mohd '
            'Talib et al. (2023) los grupos no difirieron de forma significativa. La lección para este trabajo es que '
            'un segmento solo es útil si se valida con índices de calidad, con estabilidad al remuestrear y con una '
            'prueba de diferencias, y si se declara cuando la prueba depende de las mismas variables que formaron '
            'los grupos.'))
    a(('h2', '5.5 Eje 5: consulta en lenguaje natural e inteligencia de negocios'))
    a(('p', 'La inteligencia de negocios en las universidades enfrenta una brecha de adopción: exige personal técnico '
            'y herramientas que las autoridades no dominan (Sequeira et al., 2024; Komljenovic et al., 2025). Los '
            'modelos de lenguaje que traducen preguntas a SQL prometen cerrar esa brecha, pero su exactitud en '
            'bancos de prueba ronda el 70 % (Ascoli y Choi, 2025), insuficiente para cifras que sustentan decisiones. '
            'La literatura revisada no reporta sistemas que combinen métricas certificadas, validación del SQL '
            'generado y aislamiento por institución en el contexto universitario.'))
    a(('h2', '5.6 Eje 6: gobierno de datos y operación del modelo'))
    a(('p', 'El tratamiento de datos estudiantiles en el Ecuador debe cumplir la LOPDP (Asamblea Nacional del Ecuador, '
            '2021), que reconoce el derecho a no ser objeto de decisiones basadas únicamente en valoraciones '
            'automatizadas, y las normas de la Superintendencia de Protección de Datos Personales sobre evaluación de '
            'impacto (2025) y sobre sistemas de inteligencia artificial (2026). En el plano técnico, un modelo en uso '
            'se degrada si cambia la distribución de sus datos de entrada (Gama et al., 2014), por lo que se recomienda '
            'registrar cada entrenamiento (Zaharia et al., 2018) y vigilar la deriva. Ninguno de los antecedentes de '
            'predicción del abandono revisados documenta un esquema de gobierno de datos ni de monitoreo del modelo.'))

    # ── 6 ─────────────────────────────────────────────────────────────────
    a(('h1', '6. Contexto tecnológico, institucional y territorial'))
    a(('p', '**Territorial e institucional.** La UNEMI es una universidad pública ubicada en el cantón Milagro, '
            'provincia del Guayas, que ofrece carreras en modalidades presencial, híbrida y en línea. La oferta en '
            'línea incorpora a estudiantes que estudian a distancia, el perfil que Bean y Metzner (1985) describen '
            'como más expuesto a factores externos al campus. Como toda '
            'institución pública, responde por el uso eficiente de recursos fiscales, de modo que cada retiro evitable '
            'tiene también un costo para el Estado.'))
    a(('p', '**Normativo.** La LOPDP rige desde 2021 y la Superintendencia de Protección de Datos Personales emitió '
            'en 2025 una guía obligatoria de gestión de riesgos y evaluación de impacto, y en 2026 una norma general '
            'para el uso de sistemas de inteligencia artificial que exige transparencia, evaluación de impacto, '
            'medidas de seguridad, registro de actividades de tratamiento y auditoría según el nivel de riesgo. Un '
            'sistema de alerta de abandono perfila a estudiantes de forma automatizada, por lo que este marco es '
            'parte de los requisitos y no un complemento.'))
    a(('p', '**Tecnológico.** Las universidades ecuatorianas disponen de sistemas de matrícula, calificaciones, aula '
            'virtual y cartera que operan por separado. Las tecnologías para integrarlos son hoy accesibles y, en '
            'gran parte, libres: almacenes dimensionales (Kimball y Ross, 2013), bibliotecas de aprendizaje '
            'automático en Python, marcos web modernos y modelos de lenguaje disponibles por API. El prototipo de '
            'este trabajo se construyó con SQL Server, Python, FastAPI y React, con dos fuentes de datos: datos de '
            f'prueba con la estructura de la UNEMI ({ent(um["panel"]["estudiantes"])} estudiantes y 18 carreras) y '
            f'el conjunto real y anonimizado OULAD de la Open University ({ent(om["panel"]["estudiantes"])} '
            'estudiantes; Kuzilek et al., 2017).'))

    # ── 7 ─────────────────────────────────────────────────────────────────
    a(('h1', '7. Bases teóricas'))
    a(('p', '**Teoría de la integración de Tinto.** El estudiante permanece o se retira según su integración '
            'académica (rendimiento y relación con los docentes) y social (vínculos con la comunidad universitaria) '
            '(Tinto, 1975). La teoría justifica usar el rendimiento y su tendencia como señales y entender el abandono '
            'como un proceso que se acumula, no como un hecho súbito.'))
    a(('p', '**Modelo de Bean y Metzner.** En estudiantes que trabajan, estudian a distancia o tienen cargas '
            'familiares, pesan más las variables externas (tiempo, finanzas, familia) que la vida en el campus (Bean '
            'y Metzner, 1985). Sustenta el uso de la mora, la carga matriculada y la actividad en el aula virtual, y '
            'es especialmente pertinente para la modalidad en línea.'))
    a(('p', '**Aprendizaje supervisado y ensambles.** Un clasificador aprende de casos con desenlace conocido para '
            'estimar el desenlace de casos nuevos. Random Forest (Breiman, 2001) y LightGBM (Ke et al., 2017) combinan '
            'muchos árboles de decisión y capturan relaciones no lineales sin requerir que el analista las '
            'especifique. La calibración de Platt (1999) ajusta una regresión logística sobre el puntaje para que la '
            'probabilidad se parezca a una frecuencia observada, y SHAP (Lundberg y Lee, 2017) reparte la predicción '
            'entre las variables con base en la teoría de juegos cooperativos.'))
    a(('p', '**Proceso CRISP-DM y modelo dimensional.** CRISP-DM organiza un proyecto de minería de datos en seis '
            'fases: comprensión del negocio, comprensión de los datos, preparación, modelado, evaluación y despliegue '
            '(Wirth y Hipp, 2000). El modelo dimensional de Kimball y Ross (2013) organiza los datos en hechos '
            'medibles rodeados de dimensiones, lo que permite responder preguntas de gestión con consultas simples y '
            'consistentes.'))
    a(('p', '**Traducción de lenguaje natural a SQL.** Un modelo de lenguaje recibe la pregunta y el esquema de la base '
            'y genera la consulta SQL que la responde. Como la consulta puede ser incorrecta o maliciosa, la teoría de '
            'sistemas seguros aconseja tratarla como entrada no confiable: validarla antes de ejecutarla y ejecutarla '
            'con el mínimo privilegio (Ascoli y Choi, 2025).'))

    # ── 8 ─────────────────────────────────────────────────────────────────
    a(('h1', '8. Definición de términos'))
    a(('tab', 'terminos', 'Términos Relevantes del Trabajo', ['Término', 'Definición en este trabajo'],
       [['Abandono (en el periodo siguiente)', 'El estudiante activo en un periodo no continúa en el siguiente '
                                               '(UNEMI: no se matricula; OULAD: se retira del módulo).'],
        ['Alerta temprana', 'Señal que identifica a un estudiante en riesgo antes de que abandone, para ofrecerle '
                            'acompañamiento.'],
        ['ROC-AUC', 'Probabilidad de que el modelo asigne más riesgo a un estudiante que abandona que a uno que no; '
                    '0,5 equivale al azar y 1 a la perfección.'],
        ['PR-AUC', 'Área bajo la curva de precisión y recall; se compara con la prevalencia del abandono.'],
        ['Recall (sensibilidad)', 'Proporción de los estudiantes que abandonaron que el sistema había alertado.'],
        ['Calibración', 'Ajuste para que una probabilidad de 0,30 signifique que abandonan cerca de 3 de cada 10.'],
        ['Validación temporal', 'Entrenar con periodos pasados y evaluar con periodos posteriores no vistos.'],
        ['Origen móvil', 'Validación temporal repetida: cada periodo se predice entrenando solo con los anteriores.'],
        ['SHAP', 'Método que reparte una predicción entre las variables que la explican.'],
        ['Segmentación (K-means)', 'Agrupación de carreras con indicadores parecidos en un número k de grupos.'],
        ['NL2SQL', 'Traducción de una pregunta en lenguaje natural a una consulta SQL.'],
        ['Métrica certificada', 'Consulta SQL fija y verificada que responde un tipo de pregunta frecuente.'],
        ['Almacén de datos (esquema estrella)', 'Base de datos analítica con tablas de hechos y dimensiones.'],
        ['Deriva de los datos', 'Cambio en la distribución de las variables de entrada respecto del entrenamiento.'],
        ['Gobierno de datos', 'Reglas, roles y controles sobre cómo se obtienen, usan, protegen y eliminan los datos.'],
        ['Seudonimización', 'Sustitución de los identificadores por códigos que no permiten identificar a la persona '
                            'sin una clave adicional.']],
       'Elaboración propia.', [4.4, 11.6]))

    # ── 9 ─────────────────────────────────────────────────────────────────
    a(('h1', '9. Comparación crítica de autores, métodos y resultados'))
    a(('p', 'La {T:critica} compara los antecedentes más cercanos con el presente trabajo según su método, sus datos, '
            'su validación y su resultado. La última fila ubica el aporte propio en el mismo formato.'))
    filas = [
        ['Carballo-Mendívil et al. (2025)', 'XGBoost vs. RL, RF y LightGBM', '38.932 estudiantes; corte único al '
                                                                            'ingreso', 'Partición 80/20', 'ROC-AUC 0,69; '
                                                                                                          'recall 0,88'],
        ['Marcolino et al. (2025)', 'CatBoost elegido por optimización', '567 casos de Moodle', 'Aleatoria y cursos '
                                                                                                 'nuevos',
         'F1 0,86 aleatoria; ≤ 0,50 en cursos nuevos'],
        ['Rabelo y Zárate (2025)', 'Ensamble AD + RL + red neuronal', 'Universidad privada, 2018-2019',
         'Prueba temporal (2019)', '92,6 % de desertores detectados'],
        ['Núñez-Naranjo (2024)', 'Regresión logística multinivel', '1.078 estudiantes, Ecuador', 'Ajuste del modelo',
         'Probabilidad de abandono 44,90 %'],
        ['Heredia-Jimenez et al. (2020)', 'Alerta temprana con datos académicos', 'Universidad pública del Ecuador, '
                                                                                  '2000-2019', 'Por semestre',
         'Datos académicos más confiables que los sociodemográficos'],
        ['Pilco-Salazar y Bonilla-Novillo (2026)', 'Regresión logística binaria', '684 estudiantes, Ecuador',
         'Ajuste del modelo', 'ROC-AUC 0,66; exactitud 0,665'],
        ['Ascoli y Choi (2025)', 'Text-to-SQL con modelo ajustado', 'CoSQL y SParC', 'Conjunto de desarrollo',
         'Exactitud de ejecución 70,2 %'],
        ['Presente trabajo', 'LightGBM calibrado + SHAP; NL2SQL con métricas certificadas',
         f'{ent(um["panel"]["estudiantes"])} (prueba UNEMI) y {ent(om["panel"]["estudiantes"])} (OULAD real)',
         'Cruzada por estudiante, temporal, origen móvil y prospectiva',
         f'ROC-AUC {f(ut["roc_auc"])} y {f(ot["roc_auc"])}; recall {f(ut["umbral_medio"]["recall"], 2)} y '
         f'{f(ot["umbral_medio"]["recall"], 2)}'],
    ]
    a(('tab', 'critica', 'Comparación Crítica de los Antecedentes más Cercanos con el Presente Trabajo',
       ['Estudio', 'Método', 'Datos', 'Validación', 'Resultado'], filas,
       'AD: árbol de decisión; RL: regresión logística; RF: Random Forest. Elaboración propia a partir de los estudios '
       'citados y de los resultados del prototipo.', [3.4, 3.4, 3.2, 3.0, 3.0]))
    a(('p', '**Consensos.** Los antecedentes coinciden en que la trayectoria académica anticipa el abandono, en que los '
            'ensambles de árboles son una elección sólida para datos tabulares y en que el problema exige actuar '
            'antes del retiro. **Discrepancias.** Las cifras varían de 0,66 a casi 1 de ROC-AUC o de exactitud, pero la '
            'variación se explica sobre todo por la forma de validar: los resultados más altos provienen de '
            'particiones aleatorias o de datos de un solo corte, y los más bajos, de validaciones con periodos o '
            'cursos nuevos (Marcolino et al., 2025; Carballo-Mendívil et al., 2025). **Posición crítica.** Por esa '
            'razón, este trabajo no compite por la cifra más alta, sino por la más honesta: valida con periodos no '
            'vistos, repite la validación por periodo con origen móvil'
            + (f' (ROC-AUC de {f(ro["roc_auc_min"])} a {f(ro["roc_auc_max"])} en OULAD y de {f(ru["roc_auc_min"])} '
               f'a {f(ru["roc_auc_max"])} en UNEMI)' if ro and ru else '')
            + ', informa el PR-AUC y el recall con umbrales fijados antes de la prueba y declara que una de sus dos '
            'fuentes es sintética. Su debilidad frente a los antecedentes nacionales es que aún no usa datos reales '
            'de una universidad ecuatoriana; su fortaleza es que entrega el modelo dentro de un sistema que la '
            'autoridad puede usar.'))

    # ── 10 ────────────────────────────────────────────────────────────────
    a(('h1', '10. Vacío de investigación'))
    a(('p', 'Del estado del arte se desprenden cuatro vacíos. El primero es **metodológico**: la mayoría de los '
            'modelos de abandono se evalúa con particiones aleatorias y métricas de exactitud, sin validación temporal, '
            'sin calibración y sin reporte por periodo o por unidad académica (Duro et al., 2026). El segundo es de '
            '**uso**: ningún antecedente nacional o local revisado integra la predicción en un sistema que la '
            'autoridad pueda consultar y entender. El tercero es de **acceso**: la consulta en lenguaje natural '
            'sobre datos institucionales se ha estudiado en bancos de prueba genéricos, sin las garantías de exactitud '
            'y de aislamiento que requieren las cifras de una universidad. El cuarto es **normativo**: no se encontraron '
            'trabajos que operen el modelo con un gobierno de datos alineado con la LOPDP y con las normas de 2025 y '
            '2026 de la Superintendencia de Protección de Datos Personales.'))
    a(('p', 'El presente trabajo atiende esos vacíos con un prototipo que valida el modelo en el tiempo y por periodo, '
            'lo explica estudiante por estudiante, lo entrega en un sistema web por roles con consulta en español '
            'sobre métricas certificadas y lo opera con calidad de datos, monitoreo de deriva y gobierno de datos. '
            'La validación con datos reales de una carrera de la UNEMI queda como la siguiente etapa, sujeta a la '
            'autorización institucional.'))

    # ── 11 ────────────────────────────────────────────────────────────────
    a(('h1', '11. Metodología actualizada'))
    a(('p', '**Enfoque y tipo de investigación.** El estudio tiene enfoque cuantitativo y es una investigación aplicada '
            'de desarrollo tecnológico: construye un artefacto (el prototipo) y mide su desempeño con datos. El diseño '
            'es no experimental, longitudinal y retrospectivo para la evaluación del modelo, porque usa trayectorias de '
            'cohortes pasadas sin manipular variables. El desarrollo sigue las seis fases de CRISP-DM (Wirth y Hipp, '
            '2000), con entregables verificables en cada una.'))
    a(('p', '**Población y unidades de análisis.** La unidad de análisis es el registro estudiante-periodo. Se trabaja '
            'con dos poblaciones completas, sin muestreo: los datos de prueba con la estructura de la UNEMI '
            f'({ent(um["panel"]["filas"])} registros de {ent(um["panel"]["estudiantes"])} estudiantes, 2019 a 2026) y '
            f'el conjunto OULAD ({ent(om["panel"]["filas"])} registros de {ent(om["panel"]["estudiantes"])} '
            'estudiantes, 2013 y 2014). Para la consulta conversacional, la unidad es la pregunta: 52 preguntas del '
            'conjunto dorado y 8 preguntas maliciosas. La prueba de usabilidad prevé 5 participantes: 2 autoridades y '
            '3 profesionales de bienestar estudiantil.'))
    a(('tab', 'tecnicas', 'Técnicas e Instrumentos por Objetivo', ['Objetivo', 'Técnica', 'Instrumento'],
       [['OE1', 'Análisis documental y análisis exploratorio de datos', 'Matriz de extracción bibliográfica; perfiles '
                                                                        'de datos; historias de usuario'],
        ['OE2', 'Minería de datos: validación cruzada agrupada, temporal, de origen móvil y prospectiva',
         'Pipeline reproducible en Python; registro de experimentos en MLflow'],
        ['OE3', 'Desarrollo incremental y pruebas de software', 'Repositorio con integración continua; pruebas '
                                                                'unitarias y de integración'],
        ['OE4', 'Evaluación con criterios fijados de antemano; prueba de usabilidad', 'Conjunto dorado; pruebas de '
                                                                                       'ataque; escala SUS '
                                                                                       '(Brooke, 1996)']],
       'Elaboración propia.', [1.6, 7.4, 7.0]))
    a(('p', '**Plan de análisis.** El desempeño predictivo se resume con ROC-AUC, PR-AUC, recall, precisión y puntaje '
            'de Brier en la prueba temporal, desagregados por periodo y por carrera; la consulta, con la exactitud por '
            'ejecución frente a un SQL de referencia; la protección de datos, con el número de lecturas de otra '
            'institución y de ataques no contenidos; y la usabilidad, con la tasa de éxito por tarea y el puntaje SUS. '
            'Los criterios de aceptación se fijaron antes de observar los resultados.'))
    a(('p', '**Consideraciones éticas.** No se usan datos personales reales de la UNEMI: los datos de prueba son '
            'sintéticos y OULAD es un conjunto público y anonimizado. La validación con una carrera real requiere '
            'autorización, evaluación de impacto y la anonimización descrita en el documento de gobierno de datos del '
            'proyecto. Los participantes de la prueba de usabilidad firmarán un consentimiento informado. La '
            'inteligencia artificial se usó como herramienta de apoyo bajo supervisión de los autores, que son los '
            'responsables del contenido.'))

    # ── 12 ────────────────────────────────────────────────────────────────
    a(('h1', '12. Gestión bibliográfica'))
    a(('p', 'Las referencias se gestionaron con Zotero. Las exportaciones de Scopus y de Crossref se importaron en '
            'formato RIS a la colección del proyecto, donde se depuraron los duplicados, se completaron los DOI y se '
            'verificó cada registro antes de citarlo. Las citas y la lista de referencias siguen la norma APA 7.ª '
            'edición en español. El archivo RIS de este documento acompaña la entrega en la carpeta digital del '
            'grupo.'))
    if CAPTURA_ZOTERO.exists():
        a(('p', 'La {F:zotero} muestra la colección del proyecto en Zotero.'))
        a(('fig', 'zotero', 'Colección del Proyecto en el Gestor Bibliográfico Zotero', CAPTURA_ZOTERO, 16.0,
           'Captura de pantalla de Zotero con la colección de referencias del proyecto', 'Captura de los autores.'))

    a(('h1', '13. Referencias'))
    for r in REFERENCIAS:
        a(('ref', r))
    a(('h1', '14. Enlace de la carpeta digital'))
    a(('p', f'Carpeta digital del grupo: {DRIVE}'))
    a(('p', f'Repositorio del proyecto: {REPOSITORIO}'))
    return b
