# -*- coding: utf-8 -*-
"""Capítulos 4 a 6 del Avance 2: conclusiones, referencias y anexos; resumen y abstract.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json

from _datos import BACKEND, C, C_ORIGEN, O, U, bonito, ent, f, pct

REPOSITORIO = 'https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI'

REFERENCIAS = [
    'Akiba, T., Sano, S., Yanase, T., Ohta, T., y Koyama, M. (2019). Optuna: A next-generation hyperparameter '
    'optimization framework. En *Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery '
    '& Data Mining* (pp. 2623-2631). Association for Computing Machinery. https://doi.org/10.1145/3292500.3330701',
    'Asamblea Nacional del Ecuador. (2021). *Ley Orgánica de Protección de Datos Personales*. Registro Oficial '
    'Quinto Suplemento n.º 459, 26 de mayo de 2021.',
    'Ascoli, B. G., y Choi, J. D. (2025). Advancing conversational text-to-SQL: Context strategies and model '
    'integration with large language models. *Future Internet, 17*(11), 527. https://doi.org/10.3390/fi17110527',
    'Bean, J. P., y Metzner, B. S. (1985). A conceptual model of nontraditional undergraduate student attrition. '
    '*Review of Educational Research, 55*(4), 485-540. https://doi.org/10.3102/00346543055004485',
    'Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5-32. https://doi.org/10.1023/A:1010933404324',
    'Carballo-Mendívil, B., Arellano-González, A., Ríos-Vázquez, N. J., y Lizardi-Duarte, M. del P. (2025). '
    'Predicting student dropout from day one: XGBoost-based early warning system using pre-enrollment data. '
    '*Applied Sciences, 15*(16), 9202. https://doi.org/10.3390/app15169202',
    'Chawla, N. V., Bowyer, K. W., Hall, L. O., y Kegelmeyer, W. P. (2002). SMOTE: Synthetic minority '
    'over-sampling technique. *Journal of Artificial Intelligence Research, 16*, 321-357. '
    'https://doi.org/10.1613/jair.953',
    'Duro, B., Gomes, A., Correia, F. B., Borges, A. R., y Bernardino, J. (2026). Machine learning and deep learning '
    'for dropout prediction in higher education: A review. *Computers, 15*(3), 164. '
    'https://doi.org/10.3390/computers15030164',
    'Gutierrez-Pachas, D. A., Garcia-Zanabria, G., Cuadros-Vargas, E., Camara-Chavez, G., y Gomez-Nieto, E. (2023). '
    'Supporting decision-making process on higher education dropout by analyzing academic, socioeconomic, and '
    'equity factors through machine learning and survival analysis methods in the Latin American context. '
    '*Education Sciences, 13*(2), 154. https://doi.org/10.3390/educsci13020154',
    'Hassan, H., Abdel-Fattah, M. A., y Mohamed, W. (2025). A pattern-based framework for automated migration of '
    'monolithic applications to microservices. *Big Data and Cognitive Computing, 9*(10), 253. '
    'https://doi.org/10.3390/bdcc9100253',
    'Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., y Liu, T.-Y. (2017). LightGBM: A highly '
    'efficient gradient boosting decision tree. En I. Guyon et al. (Eds.), *Advances in Neural Information '
    'Processing Systems 30* (pp. 3146-3154). Curran Associates.',
    'Kimball, R., y Ross, M. (2013). *The data warehouse toolkit: The definitive guide to dimensional modeling* '
    '(3.ª ed.). Wiley.',
    'Kok, C. L., Ho, C. K., Chen, L., Koh, Y. Y., y Tian, B. (2024). A novel predictive modeling for student '
    'attrition utilizing machine learning and sustainable big data analytics. *Applied Sciences, 14*(21), 9633. '
    'https://doi.org/10.3390/app14219633',
    'Komljenovic, J., Sellar, S., y Birch, K. (2025). Turning universities into data-driven organisations: Seven '
    'dimensions of change. *Higher Education, 89*(5), 1369-1386. https://doi.org/10.1007/s10734-024-01277-z',
    'Kuzilek, J., Hlosta, M., y Zdrahal, Z. (2017). Open University Learning Analytics dataset. *Scientific Data, '
    '4*, 170171. https://doi.org/10.1038/sdata.2017.171',
    'Lepori, B., y Bornmann, L. (2026). Comparing peers with peers in higher education institutions\' evaluations: '
    'Developing good practices to identify similar institutions by subject profile. *Research Evaluation, 35*. '
    'https://doi.org/10.1093/reseval/rvag012',
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
    'Orrego Granados, D., Ugalde, J., Salas, R., Torres, R., y López-Gonzales, J. L. (2022). Visual-predictive data '
    'analysis approach for the academic performance of students from a Peruvian university. *Applied Sciences, '
    '12*(21), 11251. https://doi.org/10.3390/app122111251',
    'Platt, J. C. (1999). Probabilistic outputs for support vector machines and comparisons to regularized '
    'likelihood methods. En A. J. Smola, P. Bartlett, B. Schölkopf y D. Schuurmans (Eds.), *Advances in large '
    'margin classifiers* (pp. 61-74). MIT Press.',
    'Rabelo, A. M., y Zárate, L. E. (2025). A model for predicting dropout of higher education students. *Data '
    'Science and Management, 8*(1), 72-85. https://doi.org/10.1016/j.dsm.2024.07.001',
    'Realinho, V., Machado, J., Baptista, L., y Martins, M. V. (2022). Predicting student dropout and academic '
    'success. *Data, 7*(11), 146. https://doi.org/10.3390/data7110146',
    'Sequeira, R., Reis, A., Alves, P., y Branco, F. (2024). Roadmap for implementing business intelligence systems '
    'in higher education institutions: Systematic literature review. *Information, 15*(4), 208. '
    'https://doi.org/10.3390/info15040208',
    'Tinto, V. (1975). Dropout from higher education: A theoretical synthesis of recent research. *Review of '
    'Educational Research, 45*(1), 89-125. https://doi.org/10.3102/00346543045001089',
    'Vaarma, M., y Li, H. (2024). Predicting student dropouts with machine learning: An empirical study in Finnish '
    'higher education. *Technology in Society, 76*, 102474. https://doi.org/10.1016/j.techsoc.2024.102474',
    'Wirth, R., y Hipp, J. (2000). CRISP-DM: Towards a standard process model for data mining. En *Proceedings of '
    'the 4th International Conference on the Practical Application of Knowledge Discovery and Data Mining* '
    '(pp. 29-39). Practical Application Company.',
]


def resumen_abstract() -> tuple[str, str, str, str]:
    um, om = U['m'], O['m']
    ut, ot = um['validacion_temporal'], om['validacion_temporal']
    pr = O['p']
    cert = C.get('por_origen', {}).get('CERTIFICADA', {}) if C else {}
    adv = C['resumen']['adversariales_contenidas'] if C else '8/8'
    total = (C['resumen']['preguntas_base'] + C['resumen']['preguntas_robustez']) if C else 0
    resumen = (
        'Se desarrolló un prototipo de sistema web que predice el abandono de estudiantes universitarios y permite '
        'consultar sus resultados en lenguaje natural, para que autoridades y personal de bienestar estudiantil '
        'identifiquen a tiempo a quienes están en riesgo. Siguiendo CRISP-DM, se construyó un almacén dimensional en '
        'SQL Server con aislamiento por institución y se modeló el abandono en el periodo siguiente sobre dos '
        f'fuentes: datos de prueba sintéticos con la estructura de la Universidad Estatal de Milagro '
        f'({ent(um["panel"]["estudiantes"])} estudiantes) y el conjunto real OULAD ({ent(om["panel"]["estudiantes"])} estudiantes). Se compararon '
        'regresión logística, Random Forest y LightGBM con validación cruzada agrupada por estudiante; LightGBM, '
        f'calibrado con Platt, alcanzó en la validación temporal un ROC-AUC de {f(ut["roc_auc"])} y {f(ot["roc_auc"])}, '
        f'con un recall de {f(ut["umbral_medio"]["recall"], 2)} y {f(ot["umbral_medio"]["recall"], 2)} en el umbral de '
        'riesgo medio' + (f', y de {f(pr["y_siguiente"]["roc_auc"])} en una evaluación prospectiva con datos reales'
                          if pr else '') + '. Cada alerta se explica con valores SHAP, las carreras se agrupan con '
        'K-means y la consulta conversacional responde primero con 40 métricas certificadas y solo después '
        'con SQL generado y validado sobre vistas gobernadas; '
        + (f'en una réplica del almacén, la ruta certificada respondió {cert.get("preguntas", 0)} de '
           f'{total} preguntas de prueba sin errores y se contuvieron las {adv.split("/")[1]} preguntas maliciosas, mientras que la '
           'exactitud con el modelo de lenguaje se medirá en la corrida final. ' if cert else '')
        + 'Se concluye que es viable integrar predicción, explicación, segmentación y consulta en lenguaje natural '
        'bajo una arquitectura que protege los datos estudiantiles conforme a la LOPDP.')
    claves = ('Abandono estudiantil, aprendizaje automático, alerta temprana, procesamiento del lenguaje natural, '
              'protección de datos personales')
    abstract = (
        'A web-based prototype was developed to predict university student dropout and to let academic authorities '
        'and student-support staff query the results in natural language, so that at-risk students can be '
        'identified early. Following CRISP-DM, a SQL Server dimensional warehouse with institution-level isolation '
        'was built, and next-term dropout was modelled on two sources: synthetic test data replicating the structure of the '
        f'State University of Milagro ({ent(um["panel"]["estudiantes"]).replace(".", ",")} students) and the real '
        f'OULAD dataset ({ent(om["panel"]["estudiantes"]).replace(".", ",")} students). Logistic regression, Random '
        'Forest and LightGBM were compared through student-grouped cross-validation; LightGBM with Platt '
        f'calibration reached a temporal-validation ROC-AUC of {ut["roc_auc"]:.3f} and {ot["roc_auc"]:.3f}, with a '
        f'recall of {ut["umbral_medio"]["recall"]:.2f} and {ot["umbral_medio"]["recall"]:.2f} at the medium-risk '
        'threshold' + (f', and {pr["y_siguiente"]["roc_auc"]:.3f} in a prospective evaluation on real data' if pr else '')
        + '. Each alert is explained with SHAP values, programs are grouped with K-means, and the '
        'conversational module answers first through 40 certified metrics and only then through generated SQL '
        'checked against governed views; '
        + (f'on a replica of the warehouse, the certified route answered {cert.get("preguntas", 0)} of {total} test '
           f'questions without errors and all {adv.split("/")[1]} malicious prompts were contained, while accuracy with the language '
           'model will be measured in the final run. ' if cert else '')
        + 'The results show that prediction, explanation, segmentation and natural-language querying can be '
        'integrated under an architecture that protects student data in line with Ecuadorian data-protection law.')
    keywords = 'Student dropout, machine learning, early warning, natural language processing, personal data protection'
    return resumen, claves, abstract, keywords


def bloques() -> list[tuple]:
    um, om = U['m'], O['m']
    ut, ot = um['validacion_temporal'], om['validacion_temporal']
    us = U['s']
    pr = O['p']
    b: list[tuple] = []
    a = b.append
    a(('h1', '4. Conclusiones y recomendaciones'))
    a(('h2', '4.1 Conclusiones preliminares'))
    a(('p', 'En relación con el primer objetivo, el análisis de la literatura y de la forma en que se organizan los '
            'sistemas académicos de las IES ecuatorianas permitió identificar las señales que anticipan el abandono '
            '(rendimiento y su tendencia, asistencia, mora, carga y repetición de matrícula, actividad en el aula '
            'virtual y entregas), y el análisis exploratorio confirmó su relación con el retiro tanto en los datos de '
            'prueba como en los datos reales de OULAD. De ese análisis se derivaron 18 requerimientos funcionales '
            'vinculados a las cuatro piezas de la solución, 10 no funcionales con métrica verificable y diez historias '
            'de usuario escritas para una autoridad sin perfil técnico. La validación de estos supuestos con los '
            'procesos reales de la UNEMI queda como condición del piloto.'))
    a(('p', 'En relación con el segundo objetivo, LightGBM calibrado fue el mejor modelo en las dos instituciones, y '
            'su desempeño se sostuvo en periodos que no vio durante el entrenamiento: ROC-AUC de '
            f'{f(ut["roc_auc"])} con los datos de prueba de UNEMI y {f(ot["roc_auc"])} con los datos reales de OULAD' + (
                f', y {f(pr["y_siguiente"]["roc_auc"])} en la evaluación prospectiva con datos reales' if pr else '')
            + '. Estos valores son más bajos que los del Avance 1, y esa diferencia es un hallazgo: con datos menos '
            'artificiales y una validación honesta, el modelo es útil para priorizar, no infalible. Con el umbral '
            f'medio, el sistema encuentra cerca de {pct(ot["umbral_medio"]["recall"], 0)} de los abandonos a cambio de '
            'alertar a una parte importante de los estudiantes, por lo que la lista debe leerse en orden y con el '
            'criterio de bienestar.'))
    a(('p', 'En relación con el tercer objetivo, el sistema web quedó implementado y funcionando de punta a punta: '
            'panel institucional, lista priorizada, ficha explicada con simulador, seguimiento, consulta '
            'conversacional, segmentación, referentes, calidad del modelo, reportes y administración, con tres roles '
            f'y 27 servicios REST. La segmentación agrupó las 18 carreras en {us.get("k", 3)} segmentos con '
            'diferencias significativas en su tasa histórica de abandono.'))
    a(('p', 'En relación con el cuarto objetivo, las métricas predictivas cumplen los criterios de aceptación y la '
            'calibración mejora la lectura de las probabilidades, aunque en OULAD su ganancia frente a la prevalencia '
            'es pequeña. En la réplica de validación, ninguna pregunta maliciosa modificó la base, ninguna respuesta '
            'mostró datos de otra institución y la ruta certificada respondió cerca de dos tercios de las preguntas '
            'sin errores. Quedan pendientes para la corrida final sobre SQL Server la exactitud global de la consulta '
            'conversacional, que incluye las preguntas resueltas por el modelo de lenguaje, y la prueba con usuarios '
            'no técnicos; ambas tienen ya su criterio y su protocolo.'))
    a(('p', 'Como conclusión general, es viable que una universidad ecuatoriana pase de medir el abandono a '
            'anticiparlo con los datos que ya tiene, siempre que la predicción llegue a las personas que deciden con '
            'una explicación comprensible, con cifras consistentes entre el panel y la consulta, y con controles de '
            'privacidad aplicados en la propia base de datos.'))

    a(('h2', '4.2 Análisis de innovación'))
    a(('p', 'La innovación del caso no reside en un algoritmo nuevo, sino en la integración y en el modo de entregar '
            'el resultado a quien decide. La {T:innovacion} compara la práctica habitual con lo que aporta VicMar en '
            'cinco dimensiones.'))
    a(('tab', 'innovacion', 'Análisis de Innovación del Prototipo', ['Dimensión', 'Práctica habitual', 'Aporte de VicMar',
                                                                     'Tipo de innovación'],
       [['Predicción', 'Modelo en un cuaderno, evaluado con partición aleatoria', 'Modelo calibrado, validado en el '
                                                                                'tiempo y prospectivamente, en '
                                                                                'producción por lotes', 'De proceso'],
        ['Explicación', 'Probabilidad sin contexto', 'Tres razones en español, percentil, simulador y acciones '
                                                     'sugeridas', 'De producto'],
        ['Consulta', 'Pedir un reporte a TI o usar un tablero fijo', 'Preguntas en español con métricas '
                                                                     'certificadas y SQL validado', 'De producto'],
        ['Gobierno de datos', 'Permisos en la aplicación', 'Aislamiento en el motor con SESSION_CONTEXT, cuentas de '
                                                           'mínimo privilegio y auditoría', 'Tecnológica'],
        ['Adaptabilidad', 'Rehacer el sistema para otra institución', 'Perfil de mapeo: OULAD se incorporó sin '
                                                                       'cambiar el modelo', 'Organizacional']],
       'Elaboración propia.', [2.8, 4.4, 6.2, 2.6]))
    a(('p', 'El grado de novedad es incremental en cada pieza; lo distintivo es su combinación para el contexto local: '
            'no se encontró en la literatura revisada un sistema que integre una predicción explicada, una consulta '
            'conversacional certificada y un aislamiento multiinstitución aplicado en la base de datos para la gestión '
            'de la permanencia en una universidad ecuatoriana.'))

    a(('h2', '4.3 Recomendaciones'))
    a(('ul', ['**A las autoridades de la UNEMI:** autorizar un piloto con datos reales anonimizados de una facultad, '
              'bajo un acuerdo de tratamiento conforme a la LOPDP, para medir el desempeño del modelo con la '
              'población propia antes de extenderlo.',
              '**Al área de bienestar estudiantil:** usar la lista priorizada como punto de partida y registrar cada '
              'intervención en el sistema, porque ese registro permitirá medir más adelante si el acompañamiento '
              'cambia el desenlace.',
              '**A la Dirección de Tecnologías de la Información:** mantener las cuentas de mínimo privilegio, '
              'programar el proceso por lotes al cierre de cada periodo y revisar el monitoreo de deriva antes de '
              'reentrenar.',
              '**A futuros trabajos de titulación:** evaluar el efecto causal de las intervenciones, incorporar '
              'variables socioeconómicas de la matrícula y ampliar el conjunto dorado de la consulta con preguntas '
              'reales de las autoridades.']))

    a(('h1', '5. Referencias'))
    for r in REFERENCIAS:
        a(('ref', r))

    a(('h1', '6. Anexos'))
    a(('h3', 'Anexo A. Guía de ejecución del prototipo'))
    a(('p', f'El código fuente, los scripts de instalación y esta documentación están en el repositorio del proyecto '
            f'({REPOSITORIO}). Para ejecutar la demostración en un equipo con Windows se siguen los pasos de la '
            '{T:guia}.'))
    a(('tab', 'guia', 'Pasos para Ejecutar la Demostración', ['Paso', 'Acción', 'Resultado esperado'],
       [['1', 'Instalar Docker Desktop, Python 3.13 y Node.js 20', 'Herramientas disponibles en la consola'],
        ['2', 'Clonar el repositorio y copiar codigo_fuente\\backend\\.env.example como .env, con las contraseñas '
              'y las claves de IA', 'Configuración local sin secretos en el repositorio'],
        ['3', 'Ejecutar codigo_fuente\\scripts\\reconstruir_sistema.bat --con-consulta', 'Contenedor de SQL '
                                                                                      'Server, almacén cargado, '
                                                                                      'modelos entrenados y conjunto '
                                                                                      'dorado evaluado'],
        ['4', 'Ejecutar codigo_fuente\\scripts\\levantar_sistema.bat', 'API en el puerto 8090 e interfaz en '
                                                                      'http://localhost:3000'],
        ['5', 'Ingresar con una cuenta de demostración (autoridad, bienestar o TI)', 'Panel institucional según el '
                                                                                   'rol'],
        ['6', 'Recorrer panel, ficha, consulta, carreras y calidad del modelo', 'Flujo completo de la alerta '
                                                                               'temprana']],
       'Elaboración propia.', [1.2, 8.6, 6.2]))
    a(('h3', 'Anexo B. Muestra del conjunto dorado de la consulta conversacional'))
    try:
        dorado = json.loads((BACKEND / 'eval' / 'conjunto_dorado.json').read_text(encoding='utf-8'))
        vistos, filas = set(), []
        for q in dorado['preguntas'] + dorado['robustez']:
            if q['categoria'] in vistos:
                continue
            vistos.add(q['categoria'])
            filas.append([q['id'], bonito(q['categoria'].capitalize()), q['historia'], q['pregunta']])
        for adv in dorado['adversariales'][:3]:
            filas.append([adv['id'], 'Maliciosa', 'No aplica', adv['pregunta']])
    except (OSError, KeyError):
        filas = []
    a(('p', 'La {T:dorado} muestra una pregunta por categoría del conjunto dorado y tres de las ocho preguntas '
            'maliciosas con que se probó la consulta conversacional.'))
    a(('tab', 'dorado', 'Muestra del Conjunto Dorado', ['ID', 'Categoría', 'Historia', 'Pregunta'], filas,
       'Elaboración propia a partir de codigo_fuente/backend/eval/conjunto_dorado.json.', [1.4, 2.8, 1.8, 10.0]))
    a(('h3', 'Anexo C. Enlaces de video del proyecto'))
    a(('videos',))
    return b
