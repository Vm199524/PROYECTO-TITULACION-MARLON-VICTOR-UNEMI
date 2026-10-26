# -*- coding: utf-8 -*-
"""Capítulos 4 a 6 del trabajo final: conclusiones, referencias y anexos; resumen y abstract.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json

from _datos import BACKEND, C, C_ORIGEN, O, U, bonito, ent, f, pct  # noqa: F401

REPOSITORIO = 'https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI'
DRIVE_GRUPO = 'https://drive.google.com/drive/folders/1ZOVwEslSaSjJbUeS1RCL1q3BDyVea9tT'

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
    'Brooke, J. (1996). SUS: A "quick and dirty" usability scale. En P. W. Jordan, B. Thomas, B. A. '
    'Weerdmeester y I. L. McClelland (Eds.), *Usability evaluation in industry* (pp. 189-194). Taylor & Francis.',
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
    'Gama, J., Žliobaitė, I., Bifet, A., Pechenizkiy, M., y Bouchachia, A. (2014). A survey on concept drift '
    'adaptation. *ACM Computing Surveys, 46*(4), 44. https://doi.org/10.1145/2523813',
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
    'Superintendencia de Protección de Datos Personales. (2025). *Guía de gestión de riesgos y evaluación de '
    'impacto del tratamiento de datos personales* (Resolución SPDP-SPD-2025-0003-R).',
    'Superintendencia de Protección de Datos Personales. (2026). *Norma general para la garantía del derecho de '
    'protección de datos personales en el uso de sistemas de inteligencia artificial* (Resolución '
    'SPDP-SPD-2026-0009-R).',
    'Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis and review. *International '
    'Journal of Forecasting, 16*(4), 437-450. https://doi.org/10.1016/S0169-2070(00)00065-0',
    'Tinto, V. (1975). Dropout from higher education: A theoretical synthesis of recent research. *Review of '
    'Educational Research, 45*(1), 89-125. https://doi.org/10.3102/00346543045001089',
    'Vaarma, M., y Li, H. (2024). Predicting student dropouts with machine learning: An empirical study in Finnish '
    'higher education. *Technology in Society, 76*, 102474. https://doi.org/10.1016/j.techsoc.2024.102474',
    'Wirth, R., y Hipp, J. (2000). CRISP-DM: Towards a standard process model for data mining. En *Proceedings of '
    'the 4th International Conference on the Practical Application of Knowledge Discovery and Data Mining* '
    '(pp. 29-39). Practical Application Company.',
    'Zaharia, M., Chen, A., Davidson, A., Ghodsi, A., Hong, S. A., Konwinski, A., Murching, S., Nykodym, T., '
    'Ogilvie, P., Parkhe, M., Xie, F., y Zumar, C. (2018). Accelerating the machine learning lifecycle with MLflow. '
    '*IEEE Data Engineering Bulletin, 41*(4), 39-45.',
]


def _om_resumen(m: dict) -> dict:
    return (m.get('origen_movil') or {}).get('resumen') or {}


def resumen_abstract() -> tuple[str, str, str, str]:
    """Resumen de máximo 150 palabras (formato oficial) y su abstract."""
    um, om = U['m'], O['m']
    ut, ot = um['validacion_temporal'], om['validacion_temporal']
    ro = _om_resumen(om)
    exact = C['resumen']['exactitud_relajada_total'] if C else None
    resumen = (
        'Se desarrolló un prototipo de sistema web que predice el abandono de estudiantes universitarios y permite '
        'consultar sus resultados en lenguaje natural. Con la metodología CRISP-DM se construyó un almacén '
        'dimensional en SQL Server y se compararon regresión logística, Random Forest y LightGBM con datos de prueba '
        'de la Universidad Estatal de Milagro y con el conjunto real OULAD. LightGBM calibrado alcanzó un ROC-AUC '
        f'temporal de {f(ut["roc_auc"])} y {f(ot["roc_auc"])}, con recall de {f(ut["umbral_medio"]["recall"], 2)} y '
        f'{f(ot["umbral_medio"]["recall"], 2)} en el umbral de riesgo medio'
        + (f', y se mantuvo entre {f(ro["roc_auc_min"])} y {f(ro["roc_auc_max"])} al predecir cada periodo real solo '
           'con el pasado' if ro else '') + '. Cada alerta se explica con SHAP; la consulta conversacional '
        + (f'acertó en {pct(exact, 0)} de las preguntas de prueba y ' if exact is not None else '')
        + 'contuvo los ataques, y el monitoreo verifica la calidad y la deriva de los datos. Se concluye que es '
        'viable anticipar el abandono con datos institucionales, protegiendo la información conforme a la LOPDP.')
    claves = 'Abandono estudiantil, aprendizaje automático, alerta temprana, consulta conversacional, protección de datos'
    abstract = (
        'A web-based prototype was developed to predict university student dropout and to query its results in '
        'natural language. Following CRISP-DM, a dimensional warehouse was built on SQL Server, and logistic '
        'regression, Random Forest and LightGBM were compared on test data from the State University of Milagro and '
        f'on the real OULAD dataset. Calibrated LightGBM reached a temporal ROC-AUC of {ut["roc_auc"]:.3f} and '
        f'{ot["roc_auc"]:.3f}, with a recall of {ut["umbral_medio"]["recall"]:.2f} and '
        f'{ot["umbral_medio"]["recall"]:.2f} at the medium-risk threshold'
        + (f', and stayed between {ro["roc_auc_min"]:.3f} and {ro["roc_auc_max"]:.3f} when each real term was '
           'predicted from past terms only' if ro else '') + '. Each alert is explained with SHAP; the '
        'conversational module ' + (f'answered {exact:.0%} of the test questions correctly and ' if exact is not None
                                    else '')
        + 'blocked every malicious prompt, while monitoring checks data quality and drift. Anticipating dropout '
        'with institutional data is feasible while protecting student information under Ecuadorian data-protection '
        'law.')
    keywords = 'Student dropout, machine learning, early warning, conversational query, data protection'
    return resumen, claves, abstract, keywords


def bloques() -> list[tuple]:
    um, om = U['m'], O['m']
    ut, ot = um['validacion_temporal'], om['validacion_temporal']
    us = U['s']
    pr = O['p']
    b: list[tuple] = []
    a = b.append
    a(('h1', '4. Conclusiones y recomendaciones'))
    a(('h2', '4.1 Conclusiones'))
    ro, ru = _om_resumen(om), _om_resumen(um)
    car_o = [c for c in om.get('por_carrera', []) if c.get('evaluable')]
    a(('p', 'En relación con el primer objetivo, el análisis de la literatura y de la forma en que se organizan los '
            'sistemas académicos de las IES ecuatorianas permitió identificar las señales que anticipan el abandono '
            '(rendimiento y su tendencia, asistencia, mora, carga y repetición de matrícula, actividad en el aula '
            'virtual y entregas), y el análisis exploratorio confirmó su relación con el retiro tanto en los datos de '
            'prueba como en los datos reales de OULAD. De ese análisis se derivaron 18 requerimientos funcionales '
            'vinculados a las cuatro piezas de la solución, 10 no funcionales con métrica verificable y diez historias '
            'de usuario escritas para una autoridad sin perfil técnico; en la etapa final se sumaron cinco '
            'requerimientos funcionales de operación del modelo (calidad de datos, deriva, registro de experimentos '
            'y consulta alternativa), uno no funcional de estabilidad por periodo (23 y 11 en total) y un '
            'documento de gobierno de datos alineado con la LOPDP. La validación de estos supuestos con los procesos '
            'reales de la UNEMI queda como condición del piloto.'))
    a(('p', 'En relación con el segundo objetivo, LightGBM calibrado fue el mejor modelo en las dos instituciones, y '
            'su desempeño se sostuvo en periodos que no vio durante el entrenamiento: ROC-AUC de '
            f'{f(ut["roc_auc"])} con los datos de prueba de UNEMI y {f(ot["roc_auc"])} con los datos reales de OULAD' + (
                f', y {f(pr["y_siguiente"]["roc_auc"])} en la evaluación prospectiva con datos reales' if pr else '')
            + (f'. Al predecir cada periodo solo con los anteriores, el ROC-AUC se mantuvo entre {f(ro["roc_auc_min"])} '
               f'y {f(ro["roc_auc_max"])} en OULAD y entre {f(ru["roc_auc_min"])} y {f(ru["roc_auc_max"])} en UNEMI'
               if ro and ru else '')
            + (f', y entre {f(min(c["roc_auc"] for c in car_o))} y {f(max(c["roc_auc"] for c in car_o))} en los '
               'módulos de OULAD' + (f', donde {sum(1 for c in car_o if c["roc_auc"] < 0.70)} módulos con pocos '
                                    'abandonos quedaron por debajo de 0,70 y piden umbrales propios'
                                    if any(c['roc_auc'] < 0.70 for c in car_o) else '') if car_o else '')
            + '. Estos valores son más bajos que los del Avance 1, y esa diferencia es un hallazgo: con datos menos '
            'artificiales y una validación honesta, el modelo es útil para priorizar, no infalible. Con el umbral '
            f'medio, el sistema encuentra cerca de {pct(ot["umbral_medio"]["recall"], 0)} de los abandonos a cambio de '
            'alertar a una parte importante de los estudiantes, por lo que la lista debe leerse en orden y con el '
            'criterio de bienestar.'))
    a(('p', 'En relación con el tercer objetivo, el sistema web quedó implementado y funcionando de punta a punta: '
            'panel institucional, lista priorizada, ficha explicada con simulador, seguimiento, consulta '
            'conversacional, segmentación, referentes, calidad del modelo, reportes y administración, con tres roles '
            f'y 27 servicios REST. La segmentación agrupó las 18 carreras en {us.get("k", 3)} segmentos con '
            'diferencias significativas en su tasa histórica de abandono. La operación quedó automatizada: cada '
            'corrida valida la calidad de los datos con Great Expectations, mide la deriva con Evidently y registra '
            'el modelo en MLflow, y Metabase ofrece una vía de consulta agregada para analistas.'))
    a(('p', 'En relación con el cuarto objetivo, las métricas predictivas cumplen los criterios de aceptación y la '
            'calibración mejora la lectura de las probabilidades, aunque en OULAD su ganancia frente a la prevalencia '
            'es pequeña. ' + (
                f'En la corrida sobre SQL Server, la consulta conversacional acertó por ejecución en '
                f'{pct(C["resumen"]["exactitud_relajada_total"], 0)} de las preguntas del conjunto dorado, por encima '
                'del 85\u00a0% exigido; la coincidencia exacta de columnas fue menor '
                f'({pct(C["resumen"]["exactitud_estricta_base"], 0)}), porque varias respuestas agregan columnas de '
                'contexto. Ninguna pregunta maliciosa modificó la base ni hubo lecturas de otra institución. La prueba '
                'de usabilidad con autoridades y personal de bienestar tiene su protocolo y su instrumento (Anexo D); '
                'su ejecución con usuarios de la universidad es la siguiente verificación del prototipo.'
                if C_ORIGEN == 'SQL_SERVER' else
                'En la réplica de validación, ninguna pregunta maliciosa modificó la base, ninguna respuesta '
                'mostró datos de otra institución y la ruta certificada respondió cerca de dos tercios de las preguntas '
                'sin errores. Quedan pendientes para la corrida final sobre SQL Server la exactitud global de la consulta '
                'conversacional, que incluye las preguntas resueltas por el modelo de lenguaje, y la prueba con usuarios '
                'no técnicos; ambas tienen ya su criterio y su protocolo.')))
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
    a(('ul', ['**A las autoridades de la UNEMI:** autorizar la validación con datos reales anonimizados de una '
              'carrera siguiendo el documento de gobierno de datos (Anexo C): evaluación de impacto, acuerdo de '
              'confidencialidad, extracción y seudonimización a cargo de TI con anonimizar_carrera.py y reporte del '
              'AUC y del recall por periodo y por cohorte antes de extender el uso.',
              '**Al área de bienestar estudiantil:** usar la lista priorizada como punto de partida y registrar cada '
              'intervención en el sistema, porque ese registro permitirá medir más adelante si el acompañamiento '
              'cambia el desenlace.',
              '**A la Dirección de Tecnologías de la Información:** mantener las cuentas de mínimo privilegio, '
              'programar el pipeline al cierre de cada periodo, revisar en MLflow y en el informe de Evidently cada '
              'reentrenamiento antes de publicarlo, y deshabilitar la interpretación con IA (CONSULTA_INTERPRETAR=0) '
              'mientras no exista un proveedor con garantías contractuales o un modelo alojado en la institución.',
              '**A futuros trabajos de titulación:** calibrar umbrales por carrera cuando una unidad tenga pocos '
              'abandonos (en OULAD, dos módulos quedaron por debajo de 0,70), evaluar el efecto causal de las '
              'intervenciones, incorporar '
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
       [['1', 'Instalar Docker Desktop, Python 3.13 o 3.14 y Node.js 20 o superior', 'Herramientas disponibles en la '
                                                                                    'consola'],
        ['2', 'Clonar el repositorio y copiar backend\\.env.example como .env, con las contraseñas y las claves de IA',
         'Configuración local sin secretos en el repositorio'],
        ['3', 'Ejecutar scripts\\reconstruir_sistema.bat (con --con-consulta para evaluar la consulta)',
         'SQL Server en Docker, almacén cargado, calidad de datos validada, modelos entrenados y registrados en MLflow'],
        ['4', 'Ejecutar iniciar.bat (o npm start en la raíz)', 'API en el puerto 8090 e interfaz en '
                                                              'http://localhost:3000'],
        ['5', 'Ingresar con una cuenta de demostración (autoridad, bienestar o TI)', 'Panel institucional según el rol'],
        ['6', 'Recorrer panel, ficha, consulta, carreras y calidad del modelo (pestañas «Por periodo y carrera» y '
              '«Datos y deriva»)', 'Flujo completo de la alerta temprana'],
        ['7', 'Opcional: pip install mlflow y mlflow ui (en backend); docker compose -f '
              'despliegue\\metabase\\docker-compose.yml up -d',
         'Experimentos en http://localhost:5000 y Metabase en http://localhost:3001']],
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
       'Elaboración propia a partir de backend/eval/conjunto_dorado.json.', [1.4, 2.8, 1.8, 10.0]))
    a(('h3', 'Anexo C. Gobierno de datos del prototipo'))
    a(('p', 'El documento completo de gobierno de datos está en documentacion/gobierno_datos/GOBIERNO_DE_DATOS.md del '
            'repositorio. La {T:gobierno} resume sus reglas y el control técnico que hace cumplir cada una, conforme a '
            'la LOPDP (Asamblea Nacional del Ecuador, 2021) y a las normas de la Superintendencia de Protección de '
            'Datos Personales sobre evaluación de impacto (2025) y sobre el uso de inteligencia artificial (2026).'))
    a(('tab', 'gobierno', 'Reglas del Gobierno de Datos y Control que las Hace Cumplir',
       ['Etapa', 'Regla', 'Control técnico'],
       [['Solicitud', 'Finalidad única: priorizar el acompañamiento; nunca sancionar ni negar beneficios',
         'Ficha del modelo'],
        ['Extracción', 'Solo las columnas del contrato del almacén; sin datos sensibles', 'etl/perfiles.py'],
        ['Anonimización', 'Seudónimo HMAC-SHA256 con clave de TI, sin nombres, ciudades poco frecuentes agrupadas y '
                          'k-anonimato con k = 5', 'scripts/anonimizar_carrera.py'],
        ['Calidad', 'Ninguna falla crítica antes de entrenar', 'Great Expectations (23 expectativas)'],
        ['Acceso', 'Mínimo privilegio y aislamiento por institución', 'SESSION_CONTEXT, vistas VIS_* y cuentas '
                                                                      'separadas'],
        ['Uso', 'La alerta es una sugerencia; una persona decide (art. 20 de la LOPDP)', 'Registro de la '
                                                                                         'intervención'],
        ['Transferencia', 'La IA externa no recibe cédulas ni nombres; la interpretación se puede deshabilitar',
         'core/privacidad.py y CONSULTA_INTERPRETAR'],
        ['Monitoreo', 'Reentrenar si deriva la mayoría de variables; retirar el modelo si el ROC-AUC del último '
                      'periodo baja de 0,70', 'Evidently, PSI y MLflow'],
        ['Incidentes', 'Notificación a la autoridad en el término de cinco días', 'Bitácora de auditoría']],
       'Elaboración propia a partir de documentacion/gobierno_datos/GOBIERNO_DE_DATOS.md.', [2.6, 7.6, 5.8]))
    a(('h3', 'Anexo D. Instrumento de la prueba de usabilidad'))
    a(('p', 'La prueba de usabilidad se aplica a 2 autoridades y 3 profesionales de bienestar estudiantil, con la '
            'institución de prueba. Cada participante resuelve sin ayuda las tareas de la {T:tareas_sus}, mientras se '
            'registra si la completa y en cuánto tiempo; al final responde la escala de usabilidad del sistema (SUS), '
            'de diez afirmaciones con respuesta de 1 a 5 (Brooke, 1996). La meta es una tasa de éxito de al menos '
            '80 % y un puntaje SUS de al menos 68.'))
    a(('tab', 'tareas_sus', 'Tareas de la Prueba de Usabilidad', ['N.º', 'Tarea', 'Historia'],
       [['1', 'Indique cuántos estudiantes están en riesgo alto este periodo y si aumentaron.', 'HU-01'],
        ['2', 'Encuentre a los cinco estudiantes de mayor riesgo de una carrera.', 'HU-02'],
        ['3', 'Abra la ficha de uno de ellos y explique con sus palabras por qué está en riesgo.', 'HU-03'],
        ['4', 'Simule qué pasaría si mejora su asistencia en 15 puntos.', 'HU-04'],
        ['5', 'Registre una tutoría para ese estudiante.', 'HU-05'],
        ['6', 'Pregunte al sistema qué carrera tiene más estudiantes en riesgo alto.', 'HU-06'],
        ['7', 'Diga qué carreras requieren atención prioritaria.', 'HU-07']],
       'Elaboración propia.', [1.2, 12.2, 2.6]))
    a(('h3', 'Anexo E. Enlaces del proyecto'))
    a(('p', f'Repositorio del código fuente: {REPOSITORIO}. Carpeta digital del grupo con el trabajo final, el '
            f'trabajo práctico, la presentación, el video y las evidencias: {DRIVE_GRUPO}.'))
    a(('videos',))
    return b
