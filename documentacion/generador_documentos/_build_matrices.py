# -*- coding: utf-8 -*-
"""
Construye Matrices_Metodologicas_Avance1.xlsx con las 3 matrices de
investigación:
  1. Matriz de extracción de datos bibliográficos (25 referencias reales)
  2. Matriz PRISMA (identificación -> cribado -> elegibilidad -> inclusión)
  3. Matriz de consistencia / congruencia (coherencia interna del trabajo)
"""
import glob
import json
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = str(Path(__file__).resolve().parents[1] / "matrices" / "Matrices_Metodologicas_Avance1.xlsx")

# Avance 2: las cifras de resultados se leen de los artefactos del sistema
# (misma fuente que _build_avance2.py), nunca se escriben a mano.
_BACK = Path(__file__).resolve().parents[2] / "codigo_fuente" / "backend"
_MU = json.loads((_BACK / "ml/models/UNEMI_PRUEBAS/metrics.json").read_text(encoding="utf-8"))
_MO = json.loads((_BACK / "ml/models/OULAD_UK/metrics.json").read_text(encoding="utf-8"))
_CU = json.loads((_BACK / "ml/models/UNEMI_PRUEBAS/metricas_clustering.json").read_text(encoding="utf-8"))
_NL = [json.loads(Path(p).read_text(encoding="utf-8"))["resumen"]
       for p in sorted(glob.glob(str(_BACK / "eval/resultados_nl2sql_*.json")))]
_NL = [r for r in _NL if r["preguntas"] >= 40 and r["adversariales"] >= 8][-1]


def _n(x, d=3):
    return f"{x:.{d}f}".replace(".", ",")

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=10)
TITLE_FONT = Font(bold=True, size=14, color="1F4E78")
SUB_FONT = Font(italic=True, size=9, color="595959")
WRAP = Alignment(wrap_text=True, vertical="top", horizontal="left")
CENTER = Alignment(wrap_text=True, vertical="center", horizontal="center")
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
ROW_FILL_A = PatternFill(start_color="F2F6FA", end_color="F2F6FA", fill_type="solid")
ROW_FILL_B = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")


def style_header_row(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER


def write_table(ws, start_row, headers, rows, col_widths):
    style_header_row(ws, start_row, len(headers))
    for c, h in enumerate(headers, start=1):
        ws.cell(row=start_row, column=c, value=h)
    for i, row_data in enumerate(rows):
        r = start_row + 1 + i
        fill = ROW_FILL_A if i % 2 == 0 else ROW_FILL_B
        for c, val in enumerate(row_data, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.alignment = WRAP
            cell.border = BORDER
            cell.fill = fill
    for c, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1).coordinate


wb = openpyxl.Workbook()

# ══════════════════════════════════════════════════════════════════════════
# HOJA 1 — Matriz de extracción de datos bibliográficos
# ══════════════════════════════════════════════════════════════════════════
ws1 = wb.active
ws1.title = "1. Extracción bibliográfica"
ws1["A1"] = "Matriz de extracción de datos bibliográficos (matriz de vaciado / sistematización)"
ws1["A1"].font = TITLE_FONT
ws1["A2"] = ("Desarrollo de un modelo predictivo de abandono estudiantil mediante inteligencia de "
             "negocios y procesamiento de lenguaje natural — 33 fuentes citadas en el documento (32 del "
             "Avance 1 + el dataset OULAD del Avance 2), verificadas por DOI/Scopus salvo dos excepciones señaladas "
             "explícitamente (Mejía-Peñafiel et al. 2026, sin DOI; Wirth & Hipp 2000, anterior a la "
             "ventana de 5 años).")
ws1["A2"].font = SUB_FONT
ws1.merge_cells("A1:M1")
ws1.merge_cells("A2:M2")

HEADERS_1 = ["N°", "Autor(es)", "Año", "Título", "Fuente / Revista", "DOI", "Pilar temático",
             "Objetivo del estudio", "Metodología", "Resultado principal",
             "Por qué se incluye / relevancia para este trabajo", "Citas\n(Scopus)", "Búsqueda de origen"]

DATA_1 = [
    (1, "Alzabidi, Yakut, Saad y Fındık", 2026, "SOD-FE: a supervised outlier detection and feature engineering approach for student dropout prediction", "Scientific Reports", "10.1038/s41598-026-56591-6", "Predicción",
     "Mejorar la predicción de abandono combinando detección de outliers con ingeniería de características.",
     "IQR + información mutua + Random Forest/XGBoost sobre 2 datasets reales (Portugal, Eslovaquia).",
     "F1 de 98,09% y 98,33% con Random Forest, superando a los modelos base entre 3,4 y 7,5 puntos.",
     "Refuerza la elección de Random Forest como clasificador base y valida el tratamiento de outliers antes del modelado.",
     4, "Búsqueda 1"),
    (2, "Ascoli y Choi", 2025, "Advancing conversational Text-to-SQL: Context strategies and model integration with large language models", "Future Internet", "10.3390/fi17110527", "BI / NL2SQL",
     "Mejorar la traducción de lenguaje natural a SQL mediante estrategias de contexto.",
     "Integración de modelos de lenguaje de gran escala con distintas estrategias de contexto conversacional.",
     "Mejoras medibles en precisión de generación de SQL conversacional.",
     "Respalda directamente el motor conversacional NL2SQL del sistema, aunque sobre bases de datos genéricas sin aislamiento multi-institución.",
     None, "Sesión previa (verificación directa)"),
    (3, "Carballo-Mendívil, Arellano-González, Ríos-Vázquez y Lizardi-Duarte", 2025, "Predicting student dropout from day one: XGBoost-based early warning system using pre-enrollment data", "Applied Sciences", "10.3390/app15169202", "Predicción",
     "Predecir el abandono usando únicamente datos previos a la matrícula.",
     "XGBoost sobre variables de preinscripción, sin datos académicos posteriores.",
     "Sistema de alerta temprana funcional desde el primer día.",
     "Valida la predicción temprana (antes de que existan datos académicos) como enfoque viable y complementario al del presente estudio.",
     23, "Sesión previa (verificación directa)"),
    (4, "Dube y Verster", 2024, "Interpretability of the random forest model under class imbalance", "Data Science in Finance and Economics", "10.3934/DSFE.2024019", "Predicción",
     "Analizar cómo se degrada la interpretabilidad de Random Forest bajo desbalance de clases.",
     "Revisión y experimentación con distintos niveles de desbalance de clases.",
     "La interpretabilidad se degrada de forma medible cuando la clase minoritaria es pequeña.",
     "Advierte sobre un riesgo metodológico directamente aplicable: en este estudio solo el 10% de los alumnos abandona.",
     None, "Sesión previa (verificación directa)"),
    (5, "Duro, Gomes, Correia, Borges y Bernardino", 2026, "Machine learning and deep learning for dropout prediction in higher education: A review", "Computers", "10.3390/computers15030164", "Predicción",
     "Revisar sistemáticamente los modelos de ML/DL usados para predicción de abandono.",
     "Revisión sistemática de literatura.",
     "Los modelos de árboles (Random Forest, Gradient Boosting) mantienen desempeño competitivo frente a redes neuronales profundas.",
     "Confirma la elección de Random Forest sobre aprendizaje profundo, sin requerir la infraestructura de cómputo de este último.",
     None, "Sesión previa (verificación directa)"),
    (6, "Fida, Masood, Tariq y Qayyum", 2022, "A novel hybrid ensemble clustering technique for student performance prediction", "Journal of Universal Computer Science", "10.3897/jucs.73427", "Clustering",
     "Combinar clustering con modelos de ensamble para predecir el rendimiento estudiantil.",
     "Técnica híbrida de clustering seguida de modelos de ensamble.",
     "Mejora medible en la precisión de predicción frente a enfoques no combinados.",
     "Respalda la integración de clustering (K-Means) y predicción propuesta en este trabajo, en vez de tratarlos como módulos aislados.",
     9, "Búsqueda 3"),
    (7, "Gutierrez-Pachas, Garcia-Zanabria, Cuadros-Vargas, Camara-Chavez y Gomez-Nieto", 2023, "Supporting decision-making process on higher education dropout by analyzing academic, socioeconomic, and equity factors through machine learning and survival analysis methods in the Latin American context", "Education Sciences", "10.3390/educsci13020154", "Predicción",
     "Apoyar la toma de decisiones sobre abandono analizando factores académicos, socioeconómicos y de equidad.",
     "Comparación de modelos de Machine Learning y de análisis de supervivencia en contexto latinoamericano.",
     "Los métodos de supervivencia permiten estimar cuándo ocurrirá el abandono, no solo si ocurrirá.",
     "Único antecedente en contexto latinoamericano encontrado — refuerza directamente la pertinencia regional del caso ecuatoriano.",
     32, "Búsqueda 1"),
    (8, "Khatun, Mim, Tasin y Hossain", 2025, "A hybrid framework of statistical, machine learning, and explainable AI methods for school dropout prediction", "PLOS One", "10.1371/journal.pone.0331917", "Predicción",
     "Predecir el abandono combinando métodos estadísticos, de ML y de IA explicable.",
     "Framework híbrido estadístico + ML + técnicas de explicabilidad (XAI).",
     "Modelo preciso y auditable mediante importancia de variables.",
     "Refuerza el uso de explicabilidad (SHAP) como requisito para que una autoridad no técnica confíe en el resultado.",
     None, "Sesión previa (verificación directa)"),
    (9, "Kok, Ho, Chen, Koh y Tian", 2024, "A novel predictive modeling for student attrition utilizing machine learning and sustainable big data analytics", "Applied Sciences", "10.3390/app14219633", "Predicción",
     "Modelar predictivamente la deserción utilizando big data analytics.",
     "Modelos de Machine Learning sobre grandes volúmenes de datos institucionales.",
     "Precisión cercana al 100%, identificando el rendimiento académico como el principal predictor.",
     "Valida el rendimiento académico como variable predictora central, consistente con las variables usadas en este estudio.",
     None, "Sesión previa (verificación directa)"),
    (10, "Komljenovic, Sellar y Birch", 2024, "Turning universities into data-driven organisations: seven dimensions of change", "Higher Education", "10.1007/s10734-024-01277-z", "BI / NL2SQL",
     "Explorar las dificultades reales que enfrentan las universidades al volverse organizaciones basadas en datos.",
     "Estudio empírico cualitativo estructurado en siete dimensiones de cambio (aspiracional, tecnológica, legal, comercial, organizacional, ideológica y otra).",
     "Documenta obstáculos organizacionales, legales y técnicos reales en universidades del Reino Unido.",
     "Aporta una posición crítica que contextualiza por qué la integración propuesta responde a una necesidad institucional documentada, no solo a una decisión técnica.",
     None, "Búsqueda 2"),
    (11, "Lepori y Bornmann", 2026, "Comparing peers with peers in Higher Education Institutions' evaluations: developing good practices to identify similar institutions by subject profile", "Research Evaluation", "10.1093/reseval/rvag012", "Benchmarking",
     "Desarrollar buenas prácticas para comparar instituciones de educación superior similares entre sí.",
     "Desarrollo metodológico de criterios de comparación por perfil institucional (no por rankings genéricos).",
     "Propone un método reproducible para identificar instituciones \"pares\" comparables.",
     "Respalda el módulo de benchmarking institucional externo del sistema propuesto.",
     None, "Sesión previa (verificación directa)"),
    (12, "Marcolino, Porto, Primo, Targino, Ramos, Queiroga, Munoz y Cechinel", 2025, "Student dropout prediction through machine learning optimization: Insights from Moodle log data", "Scientific Reports", "10.1038/s41598-025-93918-1", "Predicción",
     "Predecir el abandono optimizando algoritmos de ML sobre datos de actividad en el LMS.",
     "Ajuste de hiperparámetros sobre registros de actividad de Moodle.",
     "Mejora medible en el desempeño predictivo al incorporar datos de actividad, no solo académicos.",
     "Confirma el valor predictivo de los datos de actividad/asistencia, variable central en el modelo de este trabajo.",
     None, "Sesión previa (verificación directa)"),
    (13, "Melchor, Conejero, Fernández-García, Sánchez-Figueroa y Rodríguez-Echeverría", 2026, "An empirical evaluation of clustering processes for early detection of university dropout", "International Journal of Data Science and Analytics", "10.1007/s41060-025-00965-y", "Clustering",
     "Evaluar procesos de clustering para la detección temprana de abandono cuando no hay datos etiquetados.",
     "Algoritmos de clustering no supervisado sobre datos administrativos y académicos.",
     "El clustering reduce la necesidad de etiquetado, pero exige validación rigurosa de los clusters resultantes.",
     "Valida el clustering como alternativa metodológica legítima frente a la escasez de datos etiquetados, y respalda la integración predicción+clustering.",
     1, "Búsqueda 1 y 3 (duplicado, misma fuente)"),
    (14, "Mohd Talib, Abd Majid y Sahran", 2023, "Identification of student behavioral patterns in higher education using K-Means clustering and support vector machine", "Applied Sciences", "10.3390/app13053267", "Clustering",
     "Identificar patrones de comportamiento estudiantil agrupando por perfiles de rendimiento.",
     "K-Means combinado con Support Vector Machine.",
     "Segmentación efectiva de estudiantes por perfil de comportamiento y rendimiento.",
     "Respalda directamente la elección metodológica de K-Means para la segmentación institucional de este trabajo.",
     34, "Sesión previa (verificación directa)"),
    (15, "Mustofa, Emon, Mamun, Akhy y Ahad", 2025, "A novel AI-driven model for student dropout risk analysis with explainable AI insights", "Computers and Education: Artificial Intelligence", "10.1016/j.caeai.2024.100352", "Predicción",
     "Analizar el riesgo de abandono con un modelo de IA que ofrezca explicaciones auditables.",
     "Modelo de Machine Learning combinado con técnicas de IA explicable.",
     "Importancia de variables auditable por un usuario no experto.",
     "Refuerza la explicabilidad como requisito de usabilidad frente a autoridades académicas no técnicas.",
     None, "Sesión previa (verificación directa)"),
    (16, "Niyogisubizo, Liao, Nziyumva, Murwanashyaka y Nshimyumukiza", 2022, "Predicting student's dropout in university classes using two-layer ensemble machine learning approach: A novel stacked generalization", "Computers and Education: Artificial Intelligence", "10.1016/j.caeai.2022.100066", "Predicción",
     "Predecir el abandono con un enfoque de ensamble en dos capas (stacking).",
     "Stacked generalization combinando varios clasificadores base.",
     "Alto desempeño reportado; es el estudio más citado de todo el corpus revisado (181 citas).",
     "El más citado de la muestra — valida de forma independiente que el ensamble supera a clasificadores individuales.",
     181, "Búsqueda 1"),
    (17, "Ovtsarenko", 2026, "Using AI to forecast student dropout risk in technical education using a learning analytics approach", "Scientific Reports", "10.1038/s41598-026-44919-1", "Predicción",
     "Pronosticar el riesgo de abandono en educación técnica mediante analítica del aprendizaje.",
     "Comparación de clasificadores sobre datos longitudinales de aprendizaje.",
     "Identifica patrones de deterioro que preceden al abandono.",
     "Valida el enfoque de análisis longitudinal de trayectoria académica adoptado en este trabajo.",
     None, "Sesión previa (verificación directa)"),
    (18, "Rabelo y Zárate", 2025, "A model for predicting dropout of higher education students", "Data Science and Management", "10.1016/j.dsm.2024.07.001", "Predicción",
     "Predecir y reducir el abandono estudiantil mediante un modelo de ensamble propio.",
     "Ensamble de regresión logística, redes neuronales y árbol de decisión.",
     "89% de clasificación correcta y 98,1% de identificación de abandonos reales.",
     "Modelo de ensamble directamente comparable en enfoque y resultados al propuesto en este trabajo.",
     None, "Sesión previa (verificación directa)"),
    (19, "Realinho, Machado, Baptista y Martins", 2022, "Predicting student dropout and academic success", "Data", "10.3390/data7110146", "Predicción",
     "Documentar y predecir el abandono y el éxito académico a partir de un dataset agregado.",
     "Agregación de datos demográficos, socioeconómicos, macroeconómicos y académicos de matrícula.",
     "Publicación de un dataset público (UCI) usado como referencia por gran parte del campo.",
     "Dataset canónico del campo — valida la estructura de variables (demográficas, académicas, socioeconómicas) usada en este estudio.",
     130, "Búsqueda 1"),
    (20, "Romero y Liao", 2025, "Statistical and machine learning models for predicting university dropout and scholarship impact", "PLoS ONE", "10.1371/journal.pone.0325047", "Predicción",
     "Modelar el impacto de las becas sobre la deserción universitaria.",
     "Modelos estadísticos y de Machine Learning.",
     "Relación cuantificada entre nivel de beca y probabilidad de deserción.",
     "Aporta un hallazgo relevante (impacto de becas) pero sin proponer mecanismo para comunicarlo a quien decide sobre las becas — brecha que este trabajo cierra.",
     None, "Sesión previa (verificación directa)"),
    (21, "Sequeira, Reis, Alves y Branco", 2024, "Roadmap for implementing business intelligence systems in higher education institutions: Systematic literature review", "Information", "10.3390/info15040208", "BI / NL2SQL",
     "Proponer una hoja de ruta para implementar sistemas de BI en instituciones de educación superior.",
     "Revisión sistemática de literatura.",
     "Hoja de ruta validada con las etapas críticas de adopción de BI.",
     "Respalda la arquitectura de inteligencia de negocios institucional propuesta en este trabajo.",
     15, "Búsqueda 2"),
    (22, "Sequeira, Reis, Branco y Alves", 2025, "From roadmap to ecosystem: A comprehensive framework for implementing business intelligence in higher education institutions", "Systems", "10.3390/systems13111032", "BI / NL2SQL",
     "Evolucionar la hoja de ruta anterior hacia un framework integral de ecosistema de BI.",
     "Design Science Research + caso de estudio real en la Universidad de Trás-os-Montes y Alto Douro (UTAD).",
     "Framework validado en un caso institucional real.",
     "Comparte el mismo enfoque metodológico (Design Science Research) que el presente trabajo, y extiende directamente su antecedente de 2024.",
     3, "Búsqueda 2"),
    (23, "Valles-Coral, Salazar-Ramírez, Injante, Hernandez-Torres, Juárez-Díaz, Navarro-Cabrera, Pinedo y Vidaurre-Rojas", 2022, "Density-based unsupervised learning algorithm to categorize college students into dropout risk levels", "Data", "10.3390/data7110165", "Clustering",
     "Categorizar estudiantes universitarios por nivel de riesgo de abandono.",
     "Comparación de tres algoritmos de clustering no supervisado: DBSCAN, K-Means y HDBSCAN.",
     "HDBSCAN resultó el más robusto en dos de los tres índices de validación interna evaluados.",
     "Valida comparativamente distintos algoritmos de clustering para categorización de riesgo, informando la elección de K-Means.",
     26, "Búsqueda 1 y 3 (duplicado, misma fuente)"),
    (24, "Villar y Andrade", 2024, "Supervised machine learning algorithms for predicting student dropout and academic success: a comparative study", "Discover Artificial Intelligence", "10.1007/s44163-023-00079-z", "Predicción",
     "Comparar algoritmos de ML para predecir abandono y éxito académico bajo datos desbalanceados.",
     "SMOTE + Decision Tree, SVM, Random Forest, Gradient Boosting, XGBoost, CatBoost, LightGBM, con ajuste de hiperparámetros vía Optuna.",
     "LightGBM y CatBoost con Optuna superaron a los métodos de clasificación tradicionales.",
     "Respalda directamente el tratamiento de clases desbalanceadas (SMOTE), condición idéntica a este estudio (10% de abandono).",
     None, "Búsqueda 1"),
    (25, "Wirth y Hipp", 2000, "CRISP-DM: Towards a standard process model for data mining", "Proc. 4th Int. Conf. on the Practical Application of Knowledge Discovery and Data Mining", "(sin DOI — anterior a su adopción generalizada)", "Metodología",
     "Estandarizar el proceso de minería de datos en un modelo de referencia para la industria.",
     "Propuesta original de las seis fases del ciclo CRISP-DM.",
     "Metodología adoptada ampliamente en ciencia de datos hasta la actualidad.",
     "Metodología base de todo el desarrollo del componente predictivo de este trabajo (sección 3.1).",
     None, "Fuente metodológica (anterior a la ventana de 5 años, uso justificado)"),
    (26, "Albreiki, Zaki y Alashwal", 2021, "A systematic literature review of students' performance prediction using machine learning techniques", "Education Sciences", "10.3390/educsci11090552", "Predicción",
     "Revisar sistemáticamente los métodos de aprendizaje automático usados para predecir el rendimiento y abandono estudiantil.",
     "Revisión sistemática de literatura.",
     "Confirma el predominio de los modelos de ensamble sobre métodos individuales en este dominio.",
     "Segunda revisión sistemática independiente que corrobora, de forma no aislada, la conclusión de Duro et al. (2026).",
     None, "Búsqueda 1"),
    (27, "Alzubi, Alrifae, Mahmoud y Atieh", 2025, "Factors influencing business intelligence adoption by Jordanian private universities", "paperASIA", "10.59953/paperasia.v41i1b.378", "BI / NL2SQL",
     "Examinar los factores que facilitan la implementación de sistemas de BI en universidades privadas.",
     "Encuesta PLS-SEM a 385 usuarios de 23 universidades privadas jordanas.",
     "La complejidad percibida del sistema es el mayor obstáculo; el respaldo directivo y la preparación organizacional favorecen la adopción.",
     "Aporta evidencia cuantitativa (encuesta real) al diagnóstico cualitativo de Komljenovic et al. (2024) sobre barreras de adopción de BI.",
     None, "Búsqueda 2"),
    (28, "Kovor, Osei y Agyemang", 2026, "Federated learning for privacy-preserving at-risk student prediction in health professional education: A multi-scenario evaluation of FedAvg and FedProx", "Computers and Education: Artificial Intelligence", "10.1016/j.caeai.2026.100660", "Predicción",
     "Evaluar el aprendizaje federado para predecir riesgo estudiantil preservando la privacidad entre instituciones.",
     "Simulación multi-escenario con FedAvg y FedProx sobre el Open University Learning Analytics Dataset.",
     "El aprendizaje federado retiene entre 99,3% y 99,9% del desempeño de un modelo centralizado, sin compartir datos crudos.",
     "Respalda como trabajo futuro la extensión multi-institucional del sistema sin comprometer el aislamiento de datos ya implementado.",
     None, "Búsqueda 1"),
    (29, "Mejía-Peñafiel, Aguilar-Reyes, Morocho-Barrionuevo y García-Veloz", 2026, "Metodología de implementación de un dashboard en Power BI para el aprendizaje sistémico de estudiantes universitarios", "Revista de Ciencias Sociales", "(sin DOI — revista no indexada en Scopus)", "BI / NL2SQL",
     "Desarrollar una metodología para crear dashboards en Power BI orientados al aprendizaje estadístico de estudiantes.",
     "Enfoque cuantitativo, diseño de campo, investigación descriptiva.",
     "Resultados óptimos y de buena calidad en la aplicación del dashboard para el aprendizaje sistémico.",
     "Único antecedente ecuatoriano de dashboards en Power BI en educación superior; revela la brecha exacta que este trabajo cierra (aprendizaje vs. gestión institucional del riesgo).",
     None, "Hallazgo directo (PDF descargado; no indexado en Scopus)"),
    (30, "Orrego Granados, Ugalde, Salas, Torres y López-Gonzales", 2022, "Visual-predictive data analysis approach for the academic performance of students from a Peruvian university", "Applied Sciences", "10.3390/app122111251", "BI / NL2SQL",
     "Desarrollar un enfoque visual-predictivo del rendimiento académico estudiantil.",
     "Análisis visual combinado con modelos predictivos sobre datos de una universidad peruana.",
     "Valida la visualización como complemento —no sustituto— del modelo predictivo.",
     "Segundo antecedente latinoamericano; respalda directamente el componente de panel visual del sistema propuesto.",
     None, "Búsqueda 2"),
    (31, "Vaarma y Li", 2024, "Predicting student dropouts with machine learning: An empirical study in Finnish higher education", "Technology in Society", "10.1016/j.techsoc.2024.102474", "Predicción",
     "Predecir el abandono estudiantil usando datos de expediente, demográficos y del sistema de gestión del aprendizaje (LMS).",
     "Tres modelos de aprendizaje automático sobre datos de una universidad finlandesa.",
     "La actividad registrada en el LMS es uno de los predictores más importantes, junto con los créditos acumulados.",
     "Triangula internacionalmente (Finlandia) el hallazgo de Marcolino et al. (2025) sobre datos de Moodle en un contexto distinto.",
     None, "Búsqueda 1"),
    (32, "Núñez-Naranjo", 2024, "Analysis of the determinant factors in university dropout: a case study of Ecuador", "Frontiers in Education", "10.3389/feduc.2024.1444534", "Predicción",
     "Analizar los determinantes del abandono universitario mediante análisis multifactorial en una universidad ecuatoriana.",
     "Regresión logística multinivel sobre 1.078 estudiantes admitidos/matriculados en 5 años (484 abandonos analizados) y encuesta a desertores.",
     "Probabilidad estimada de abandono del 44,90%; el modelo predice el comportamiento de las variables con 76,44% de precisión.",
     "Único antecedente ecuatoriano con cifra de abandono cuantificada y metodología de clasificación comparable (regresión logística); reemplaza la cifra no académica de SENESCYT/prensa.",
     21, "Hallazgo directo — búsqueda dirigida en Scopus (16/09/2026)"),
    (33, "Kuzilek, Hlosta y Zdrahal", 2017, "Open University Learning Analytics dataset", "Scientific Data", "10.1038/sdata.2017.171", "Predicción",
     "Publicar un conjunto de datos abierto y anonimizado de estudiantes, cursos y actividad en el aula virtual de la Open University.",
     "Descriptor de datos: 32.593 matrículas de 7 módulos (22 presentaciones, 2013-2014), 10,6 millones de registros de actividad; licencia CC BY 4.0.",
     "Conjunto de referencia para predicción de retiro y rendimiento en educación a distancia (31,16% de retiros por matrícula-módulo, medido sobre el dataset).",
     "Segunda institución REAL del prototipo (OULAD_UK): valida la extensibilidad por perfil, el aislamiento entre dos instituciones y aporta el desempeño realista del modelo (Avance 2). Anterior a la ventana de 5 años: se cita como fuente de datos, no como antecedente teórico.",
     None, "Avance 2 — fuente de datos (verificada en Crossref y PMC5704676, 25/09/2026)"),
]

write_table(ws1, 4, HEADERS_1, DATA_1,
            [4, 22, 6, 42, 22, 22, 12, 30, 30, 30, 38, 8, 20])
ws1.row_dimensions[1].height = 22
ws1.row_dimensions[2].height = 28

# ══════════════════════════════════════════════════════════════════════════
# HOJA 2 — Matriz / diagrama de flujo PRISMA (identificación → inclusión)
# ══════════════════════════════════════════════════════════════════════════
ws2 = wb.create_sheet("2. PRISMA (inclusión-exclusión)")
ws2["A1"] = "Matriz de selección de estudios — proceso tipo PRISMA"
ws2["A1"].font = TITLE_FONT
ws2["A2"] = ("Documenta, por cada búsqueda ejecutada en Scopus (scopus.com), cuántos registros se "
             "identificaron, cuántos se descartaron y por qué, y cuántos quedaron finalmente disponibles "
             "para la comparación crítica en 1.3 Base conceptual.")
ws2["A2"].font = SUB_FONT
ws2.merge_cells("A1:F1")
ws2.merge_cells("A2:F2")

HEADERS_2 = ["Fase PRISMA", "Búsqueda 1\n(Predicción de abandono)", "Búsqueda 2\n(BI / NL2SQL)",
             "Búsqueda 3\n(Clustering institucional)", "Criterio aplicado", "Motivo de exclusión más frecuente"]

DATA_2 = [
    ("1. Identificación — ecuación inicial sin filtrar",
     "TITLE-ABS-KEY(\"student dropout\" OR \"student attrition\") AND (\"machine learning\" OR \"random forest\" OR \"predictive model\") AND (\"higher education\" OR \"university\") → 459 registros",
     "TITLE-ABS-KEY(\"business intelligence\" OR \"natural language to SQL\" OR \"text-to-SQL\" OR \"conversational query\") AND (\"higher education\" OR \"university\" OR \"educational institution\") → 79 registros (filtros ya incluidos desde el inicio)",
     "1ª versión con \"student\" genérico → 862 registros (descartada por exceso de ruido); 2ª versión refinada con \"academic risk\"/\"dropout risk\"/\"at-risk student\"/\"student segmentation\"/\"risk profile\" → 28 registros",
     "Búsqueda en TITLE-ABS-KEY, sin restricción de tipo de documento ni idioma.",
     "Términos individualmente correctos pero demasiado genéricos (ej. \"student\", \"clustering\" solos) generan miles de coincidencias irrelevantes."),
    ("2. Cribado automático — filtros de tipo, idioma, versión y acceso",
     "459 → 134 registros",
     "(aplicado desde la ecuación inicial: 79 registros)",
     "28 registros (ya incluye los filtros)",
     "LIMIT-TO(DOCTYPE,\"ar\") — solo artículos, sin conference papers\nLIMIT-TO(LANGUAGE,\"English\")\nLIMIT-TO(PUBSTAGE,\"final\") — sin \"in press\"\nLIMIT-TO(OA,\"all\") — solo acceso abierto\nPUBYEAR 2021–2026 (últimos 5 años)",
     "Documentos que, siendo relevantes por tema, no cumplían el criterio de acceso abierto o estaban aún \"in press\"."),
    ("3. Cribado manual por título/resumen",
     "134 evaluados → 24 seleccionados como candidatos de alta relevancia",
     "79 evaluados → 19 seleccionados (se excluyeron ~10 por coincidencia espuria)",
     "28 evaluados → 10 candidatos nuevos (3 identificados como duplicados exactos ya cubiertos en Búsqueda 1)",
     "Ajuste directo al tema específico de cada pilar técnico (predicción, BI/NL2SQL, clustering) por sobre coincidencia léxica genérica.",
     "Coincidencia espuria con \"university\" en artículos clínicos/hospitalarios (ej. \"University Hospital of Palermo\") sin relación real con BI o abandono estudiantil; papers centrados en \"rendimiento\" sin tratar abandono."),
    ("4. Verificación de elegibilidad (acceso a texto completo)",
     "24 candidatos → PDF verificado para 22 (4 vía suscripción institucional Elsevier + 18 vía acceso abierto verificado con Undermind)",
     "19 candidatos → PDF pendiente de verificación manual adicional",
     "10 candidatos → PDF verificado para varios vía el mismo método (MDPI, Springer)",
     "Descarga directa del editor (curl / navegador) confirmando encabezado %PDF real, no solo el estado \"Open Access\" declarado por Scopus.",
     "Algunos editores (IEEE Xplore, Oxford Academic, Emerald, ScienceDirect) bloquean la descarga automatizada aunque el artículo sea de acceso abierto."),
    ("5. Inclusión final — citados y comparados en 1.3 Base conceptual",
     "10 de los 24 pasaron a la comparación crítica final (Alzabidi, Gutierrez-Pachas, Niyogisubizo, "
     "Realinho, Villar, Albreiki, Kovor y Vaarma, y 2 compartidos con Búsqueda 3: Melchor y Valles-Coral)",
     "5 de los 19 pasaron a la comparación crítica final (Komljenovic, Sequeira 2024, Sequeira 2025, "
     "Alzubi y Orrego Granados)",
     "1 candidato nuevo pasó a la comparación final (Fida) + 2 ya contabilizados en Búsqueda 1 por ser "
     "la misma fuente (Melchor, Valles-Coral)",
     "Se prioriza impacto (citas), ajuste directo al pilar técnico, y complementariedad con las fuentes ya citadas (evitar redundancia temática).",
     "Estudios redundantes con otro ya citado del mismo hallazgo, o de menor impacto/ajuste frente a alternativas disponibles en el mismo pilar."),
]

write_table(ws2, 4, HEADERS_2, DATA_2, [26, 40, 40, 40, 34, 34])
ws2.row_dimensions[1].height = 22
ws2.row_dimensions[2].height = 40
for r in range(5, 5 + len(DATA_2)):
    ws2.row_dimensions[r].height = 110

ws2["A11"] = "Nota metodológica:"
ws2["A11"].font = Font(bold=True, size=10)
ws2["A12"] = ("Las 14 fuentes restantes citadas en 1.3 Base conceptual (Ascoli y Choi, Carballo-Mendívil "
              "et al., Dube y Verster, Duro et al., Khatun et al., Kok et al., Lepori y Bornmann, Marcolino "
              "et al., Mohd Talib et al., Mustofa et al., Ovtsarenko, Rabelo y Zárate, Romero y Liao, "
              "Wirth y Hipp) se identificaron y verificaron en una ronda de trabajo previa a la sistematización "
              "de estas 3 búsquedas formales en Scopus, mediante verificación directa de metadatos contra "
              "Crossref (DOI, autores, año y revista confirmados uno por uno). Se documentan aquí por "
              "transparencia metodológica, no como parte del flujo PRISMA de las 3 búsquedas descritas arriba.")
ws2["A12"].alignment = WRAP
ws2.merge_cells("A12:F12")

ws2["A13"] = ("Dos fuentes adicionales se incorporaron después de esta sistematización, fuera del flujo "
              "de las 3 búsquedas: Mejía-Peñafiel et al. (2026) se identificó al leer el PDF descargado "
              "bajo un nombre de archivo incorrecto (\"Mej26_Metodologia_Dashboard_Power_BI\"), que "
              "correspondía a un estudio ecuatoriano no indexado en Scopus, no al de Melchor et al. "
              "esperado; Núñez-Naranjo (2024) se localizó mediante una búsqueda dirigida adicional en "
              "Scopus (TITLE-ABS-KEY(dropout AND ecuador AND \"higher education\"), 27 resultados, "
              "16/09/2026) para sustituir una cifra de deserción tomada originalmente de un artículo de "
              "prensa (Diario Expreso, 2019) por evidencia académica verificable; su PDF se descargó "
              "directamente de Frontiers y se incorporó a la carpeta de literatura consultada.")
ws2["A13"].alignment = WRAP
ws2.merge_cells("A13:F13")
ws2.row_dimensions[12].height = 90

# ══════════════════════════════════════════════════════════════════════════
# HOJA 3 — Matriz de consistencia / congruencia
# ══════════════════════════════════════════════════════════════════════════
ws3 = wb.create_sheet("3. Matriz de consistencia")
ws3["A1"] = "Matriz de consistencia (congruencia) del trabajo de titulación"
ws3["A1"].font = TITLE_FONT
ws3["A2"] = ("Verifica la coherencia interna entre el problema, los objetivos, la metodología y los "
             "resultados esperados del presente estudio de caso.")
ws3["A2"].font = SUB_FONT
ws3.merge_cells("A1:F1")
ws3.merge_cells("A2:F2")

HEADERS_3 = ["Problema", "Objetivo", "Nivel Bloom", "Dimensión / unidad de análisis",
             "Metodología / diseño", "Resultado esperado / instrumento"]

DATA_3 = [
    ("La detección de estudiantes en riesgo de abandono ocurre de manera tardía porque las instituciones "
     "registran el estado actual del estudiante sin explotar su trayectoria histórica, con datos "
     "dispersos entre sistemas aislados y dependencia de personal técnico para consultarlos.",
     "OBJETIVO GENERAL: Desarrollar un modelo predictivo de abandono estudiantil, integrado a un sistema "
     "de inteligencia de negocios con dashboards interactivos y procesamiento de lenguaje natural, que "
     "permita a instituciones de educación superior identificar tempranamente a los estudiantes en riesgo.",
     "Crear",
     "Trayectoria académica longitudinal del estudiante universitario (matrícula, rendimiento, "
     "asistencia, situación financiera) a lo largo de múltiples periodos — no un corte transversal único.",
     "CRISP-DM (Wirth & Hipp, 2000) para el componente predictivo; desarrollo iterativo-incremental para "
     "ETL, API y panel visual.",
     "Prototipo de sistema de inteligencia de negocios funcional, probado de extremo a extremo contra un "
     "servidor real (SQL Server), con panel visual y chat conversacional leyendo la misma fuente de "
     "datos gobernada."),
    ("Ausencia de historial académico longitudinal estructurado: los sistemas registran matrícula "
     "vigente, sin conservar la trayectoria histórica en forma explotable para análisis.",
     "OBJETIVO ESPECÍFICO 1: Analizar los procesos actuales de seguimiento académico estudiantil, "
     "identificando las variables asociadas al riesgo de abandono en el contexto universitario.",
     "Analizar",
     "Procesos de seguimiento académico institucional vigentes y variables disponibles (matrícula, "
     "rendimiento, asistencia, mora).",
     "Revisión documental de los sistemas académicos existentes + trayectoria longitudinal sintética y "
     "anonimizada (83.678 registros alumno-periodo de 14.508 alumnos) + dataset real OULAD (Kuzilek et al., "
     "2017) como segunda institución; panel alumno-periodo (características hasta t, abandono en t+1).",
     "Variables predictoras identificadas y cuantificadas por importancia por permutación: en datos "
     f"sintéticos domina {_MU['importancia_permutacion'][0]['variable']}; en datos reales (OULAD) "
     f"{_MO['importancia_permutacion'][0]['variable']} (rendimiento académico, coherente con Kok et al., 2024)."),
    ("Falta de modelos predictivos de riesgo de abandono integrados a los sistemas académicos "
     "institucionales, y de segmentación institucional por perfil de riesgo.",
     "OBJETIVO ESPECÍFICO 2: Desarrollar el modelo predictivo de abandono estudiantil integrado a un "
     "prototipo de sistema de inteligencia de negocios con visualización mediante dashboards interactivos "
     "y consulta en lenguaje natural.",
     "Crear",
     "Modelo dimensional (esquema estrella de Kimball) con dos instituciones: dim_alumno (institución + "
     "cédula), dim_carrera, dim_facultad, dim_tiempo, fact_matriculas, fact_prediccion_abandono (con "
     "factores SHAP), fact_cluster_carrera, fact_evaluacion_modelo.",
     "Un modelo por institución: RandomizedSearchCV (25 combinaciones) con StratifiedGroupKFold por alumno; "
     "comparación RF+ponderación / RF+SMOTE / logística / gradient boosting; K-Means (k=3) validado; "
     "NL2SQL con métricas certificadas y lógica de negocio por institución; tres capas de seguridad.",
     "Modelo serializado con umbral operativo + API REST (/api/ml/prediccion-abandono, /clusters-carrera, "
     "/evaluacion-modelo) + panel con factores y confiabilidad + chat; demostración reproducible "
     "(codigo_fuente/scripts/demo_tesis.ps1)."),
    ("Limitado acceso a herramientas de inteligencia de negocios conversacional y ausencia de "
     "referentes comparativos (benchmarking) institucionales.",
     "OBJETIVO ESPECÍFICO 3: Evaluar el desempeño del modelo predictivo mediante validación cruzada y "
     "validación temporal, contrastando los resultados frente a referentes institucionales externos.",
     "Evaluar",
     "Desempeño predictivo (ROC-AUC, PR-AUC, recall, precisión) en datos sintéticos y reales, calidad de "
     "la segmentación, exactitud del motor NL2SQL y posicionamiento frente a referentes con DOI "
     "(Núñez-Naranjo, 2024; Realinho et al., 2022; Vaarma y Li, 2024; Kuzilek et al., 2017).",
     "Validación cruzada de 5 pliegues agrupada por alumno + prueba temporal (25% más reciente, usada una "
     "sola vez) + evaluación prospectiva en OULAD + silhouette/estabilidad/Kruskal-Wallis + conjunto de 40 "
     "preguntas de referencia y 8 maliciosas + pruebas de integración de seguridad.",
     f"ROC-AUC temporal {_n(_MU['validacion_temporal']['umbral_operativo']['roc_auc'])} (sintéticos) y "
     f"{_n(_MO['validacion_temporal']['umbral_operativo']['roc_auc'])} (OULAD, reales); prospectivo "
     f"{_n(_MO['evaluacion_prospectiva']['y_proximo']['roc_auc'])}; Kruskal-Wallis p = "
     f"{_n(_CU['kruskal_wallis_tasa_abandono']['p_valor'])}; exactitud NL2SQL {_n(_NL['exactitud_relajada'], 2)}; "
     f"{_NL['adversariales_superadas']}/{_NL['adversariales']} preguntas maliciosas contenidas; tasa propia 10,02% "
     "frente a 24,4%-44,9% de los referentes."),
]

write_table(ws3, 4, HEADERS_3, DATA_3, [40, 42, 12, 34, 40, 40])
ws3.row_dimensions[1].height = 22
ws3.row_dimensions[2].height = 26
for r in range(5, 5 + len(DATA_3)):
    ws3.row_dimensions[r].height = 150

# ══════════════════════════════════════════════════════════════════════════
# HOJA 4 — Coherencia literatura ↔ código (Avance 2)
# ══════════════════════════════════════════════════════════════════════════
ws4 = wb.create_sheet("4. Coherencia literatura-código")
ws4["A1"] = "Matriz de coherencia entre la literatura citada y el código del prototipo"
ws4["A1"].font = TITLE_FONT
ws4["A2"] = ("Por cada antecedente citado: qué afirma el documento, qué decisión concreta tomó el código, dónde "
             "está implementada y qué evidencia medida la respalda. Las cifras provienen de los artefactos del "
             "sistema (backend/ml/models/*, backend/eval/*), no se escriben a mano.")
ws4["A2"].font = SUB_FONT
ws4.merge_cells("A1:E1")
ws4.merge_cells("A2:E2")
_imp_o = _MO["importancia_permutacion"][0]["variable"]
_cvo = _MO["comparacion_cv"]
DATA_4 = [
    ("Duro et al. (2026)", "Los modelos longitudinales tienen mayor validez; los árboles son competitivos frente al aprendizaje profundo (1.3).",
     "Panel alumno-periodo (características hasta t, abandono en t+1); RF comparado con gradient boosting y regresión logística.",
     "ml/features_abandono.py; ml/entrenar_abandono.py",
     f"OULAD (CV): RF {_n(_cvo['RF_CLASS_WEIGHT']['roc_auc']['media'])}, gradient boosting {_n(_cvo['GRADIENT_BOOST']['roc_auc']['media'])}, logística {_n(_cvo['LOGISTICA']['roc_auc']['media'])}."),
    ("Ovtsarenko (2026)", "Existen patrones de deterioro que preceden al abandono.",
     "Variables de cambio respecto al periodo anterior, media móvil de 3 periodos y peor valor histórico.",
     "ml/features_abandono.py", "Variables de tendencia entre las más importantes por permutación."),
    ("Carballo-Mendívil et al. (2025)", "La alerta temprana es viable; XGBoost.",
     "Gradient boosting como modelo de referencia; arranque en frío declarado (quien abandona en su primer periodo no se anticipa).",
     "ml/entrenar_abandono.py", "162 retiros en el primer semestre (UNEMI) y 26,3% de retiros previos al inicio (OULAD) documentados como límite."),
    ("Kok et al. (2024)", "El rendimiento académico es el principal predictor.",
     "Importancia por permutación sobre la prueba temporal.", "ml/reporte_validacion.py",
     f"En OULAD (datos reales) la variable más importante es {_imp_o}."),
    ("Rabelo y Zárate (2025); Núñez-Naranjo (2024)", "Regresión logística y ensambles para abandono.",
     "Regresión logística como línea base con los mismos pliegues.", "ml/entrenar_abandono.py",
     f"OULAD: logística {_n(_cvo['LOGISTICA']['roc_auc']['media'])} frente a RF {_n(_cvo['RF_CLASS_WEIGHT']['roc_auc']['media'])}."),
    ("Villar y Andrade (2024)", "SMOTE para clases desbalanceadas.",
     "RF con SMOTE (solo en pliegues de entrenamiento, imblearn.Pipeline) frente a RF con ponderación de clases.",
     "ml/entrenar_abandono.py", f"Modelo final: {_MU['modelo_final']} (UNEMI), {_MO['modelo_final']} (OULAD); diferencias menores a una desviación estándar."),
    ("Dube y Verster (2024)", "La interpretabilidad del RF se degrada con desbalance.",
     "Importancia por permutación (no por impureza); PR-AUC y umbral elegido por recall.", "ml/entrenar_abandono.py",
     f"PR-AUC temporal OULAD {_n(_MO['validacion_temporal']['umbral_operativo']['pr_auc'])} con prevalencia {_n(_MO['validacion_temporal']['umbral_operativo']['prevalencia'])}."),
    ("Khatun et al. (2025); Mustofa et al. (2025)", "IA explicable (SHAP) auditable por usuarios no técnicos.",
     "Tres factores SHAP por alumno, en lenguaje natural, visibles en el panel y consultables en el chat.",
     "ml/predecir_abandono.py; RiesgoAbandonoCard.jsx", "Columnas factor_1..factor_3 en VIS_PREDICCION_ABANDONO."),
    ("Albreiki et al. (2021); Niyogisubizo et al. (2022)", "Los ensambles superan a los clasificadores individuales.",
     "Random Forest frente a regresión logística.", "ml/entrenar_abandono.py", "Se cumple en OULAD; en los datos sintéticos todos los modelos superan 0,98."),
    ("Marcolino et al. (2025); Vaarma y Li (2024)", "La actividad en el LMS predice el abandono.",
     "En OULAD, asistencia = días con actividad en el aula virtual por bloque de 28 días.", "scripts/seed_oulad.py",
     "Señal presente pero menor que el rendimiento en OULAD."),
    ("Mohd Talib et al. (2023)", "K-Means para segmentar perfiles estudiantiles.",
     "K-Means (k = 3) sobre indicadores por carrera, etiquetado por centroide.", "ml/clustering_institucional.py",
     f"Silhouette (k = 3) = {_n(next(b['silhouette'] for b in _CU['barrido_k'] if b['k'] == 3))}."),
    ("Melchor et al. (2026)", "Los clústeres deben validarse rigurosamente antes de decidir.",
     "Silhouette, Davies-Bouldin, Calinski-Harabasz, estabilidad bootstrap y Kruskal-Wallis.", "ml/clustering_institucional.py",
     f"Kruskal-Wallis p = {_n(_CU['kruskal_wallis_tasa_abandono']['p_valor'])}; ARI de estabilidad = {_n(_CU['estabilidad_bootstrap']['ari_medio'])}."),
    ("Valles-Coral et al. (2022); Fida et al. (2022)", "Comparar algoritmos de agrupamiento.",
     "K-Means frente a jerárquico (Ward) y HDBSCAN.", "ml/clustering_institucional.py", "metricas_clustering.json."),
    ("Ascoli y Choi (2025)", "Estrategias de contexto mejoran NL2SQL (ellos miden ESM en CoSQL).",
     "Lógica de negocio por institución + métricas certificadas; evaluación por exactitud de ejecución.",
     "knowledge/business_logic.json; eval/evaluar_nl2sql.py", f"Exactitud por ejecución = {_n(_NL['exactitud_relajada'], 2)} (40 preguntas)."),
    ("Sequeira et al. (2024, 2025); Alzubi et al. (2025)", "La brecha técnica y la complejidad percibida frenan la adopción de BI.",
     "Consulta en español sin SQL; historias de usuario desde la autoridad sin perfil técnico; prueba con usuarios.",
     "api/routes_query.py; documento 2.1", "Usuario de prueba con rol ACADÉMICO en la evaluación."),
    ("Komljenovic et al. (2024)", "Obstáculos organizacionales y legales al volverse data-driven.",
     "Requisitos de protección de datos (LOPDP): anonimización, minimización hacia IA externa, enmascaramiento.",
     "core/privacidad.py; anonimizar_padron.py", "tests/test_privacidad.py."),
    ("Lepori y Bornmann (2026)", "Comparar instituciones pares con pares.",
     "Cada referente declara definición, país, modalidad y nivel de comparabilidad.", "etl/etl_benchmarking.py y su CSV",
     "4 referentes con DOI; se retiraron las cifras de prensa."),
    ("Kovor et al. (2026)", "Aprendizaje federado sin compartir datos crudos.",
     "Un modelo por institución, sin mezclar datos; aislamiento a nivel del motor; federado como trabajo futuro.",
     "ml/entrenar_abandono.py --empresa", "Modelos separados en ml/models/<institución>/."),
    ("Gutierrez-Pachas et al. (2023)", "El riesgo varía según facultad y grupo.",
     "Segmentación por carrera; su muestra balanceada 50/50 no se usa como referente de tasa.", "ml/clustering_institucional.py",
     "Excluido del benchmarking por diseño muestral (verificado en su Tabla 2)."),
    ("Orrego Granados et al. (2022); Mejía-Peñafiel et al. (2026)", "La visualización complementa al modelo.",
     "Panel con riesgo, factores y confiabilidad sobre la misma fuente que el chat.", "RiesgoAbandonoCard.jsx; InteligenciaInstitucionalCard.jsx",
     "Panel y chat leen las mismas vistas VIS_*."),
    ("Alzabidi et al. (2026)", "Detección de atípicos e ingeniería de características antes del modelo.",
     "Informe de atípicos por IQR en la fase de preparación (sin eliminar filas).", "ml/features_abandono.py::informe_atipicos",
     f"UNEMI: {_n(_MU['atipicos_iqr']['asistencia_t']['pct_atipicos'], 2)}% de asistencias atípicas."),
    ("Realinho et al. (2022)", "Dataset de referencia del campo; desbalance.", "Referente de benchmarking (32,12%).",
     "etl/fuentes_externas/*.csv", "Cifra verificada en su texto (1.421 de 4.424)."),
    ("Romero y Liao (2025)", "Impacto de las becas en la deserción.", "beca_porcentaje como variable del modelo; preguntas sobre becas en el conjunto de referencia.",
     "ml/features_abandono.py; eval/nl2sql_gold.json", "Importancia baja en datos sintéticos (becas sin señal diseñada)."),
    ("Kuzilek et al. (2017)", "Fuente del dataset real (nueva en el Avance 2).", "Segunda institución OULAD_UK cargada con un perfil.",
     "scripts/seed_oulad.py; etl/perfiles.py", f"ROC-AUC temporal real = {_n(_MO['validacion_temporal']['umbral_operativo']['roc_auc'])}."),
    ("Wirth y Hipp (2000)", "CRISP-DM como metodología.", "Seis fases documentadas con entregables del repositorio.", "Documento 3.1", "Tabla de entregables por fase."),
]
write_table(ws4, 4, ["Antecedente", "Qué afirma el documento", "Decisión en el código", "Dónde está implementada", "Evidencia medida"],
            DATA_4, [30, 42, 48, 34, 42])
ws4.row_dimensions[1].height = 22
ws4.row_dimensions[2].height = 30

for ws in (ws1, ws2, ws3, ws4):
    ws.sheet_view.showGridLines = False

wb.properties.creator = 'Marlon David Pérez Almachi; Víctor Manuel Lluilema Pisco'
wb.properties.lastModifiedBy = 'Marlon David Pérez Almachi'
wb.save(OUT)
print(f"Guardado: {OUT}")
print(f"Hoja 1: {len(DATA_1)} referencias")
print(f"Hoja 2: {len(DATA_2)} fases PRISMA")
print(f"Hoja 3: {len(DATA_3)} filas (objetivo general + 3 específicos)")
