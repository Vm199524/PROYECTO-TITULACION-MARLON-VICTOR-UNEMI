# Comparación del trabajo final: versión de Víctor y versión de la sesión de trabajo

Proyecto VicMar · Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco · UNEMI · 26/10/2026

## 0. Documentos comparados y criterio

| Versión | Archivo | Fecha de guardado | Párrafos / tablas / referencias |
|---|---|---|---|
| Víctor (base oficial, la más reciente) | `AVANCE3_MARLON_VICTOR.docx` (raíz de la carpeta del proyecto, fuera del repositorio) | 26/10/2026, 23:34 UTC | 587 / 50 / 34 |
| Víctor (en el repositorio) | `documentacion/avances/TRABAJO_FINAL_MARLON_VICTOR.docx` | 26/10/2026, 22:43 UTC | 584 / 50 / 34 |
| Sesión de trabajo | `documentacion/avances/Avance 3/01_TRABAJO_FINAL/TRABAJO_FINAL_PEREZ_LLUILEMA.docx` y su PDF (rama `trabajo-sesion-avance3`) | 27/10/2026, 01:49 UTC | 503 / 47 / 55 |

- `AVANCE3_MARLON_VICTOR.docx` y `TRABAJO_FINAL_MARLON_VICTOR.docx` tienen el mismo texto en los párrafos. Solo cambia la tabla de actividades del anexo de información académica (fechas «09/09/2026» y «10/09/2026» en lugar de «07/09/2026 al 09/09/2026» y «Septiembre de 2026»). **La referencia es `AVANCE3_MARLON_VICTOR.docx`.** Conviene copiarlo sobre `TRABAJO_FINAL_MARLON_VICTOR.docx` antes de la entrega para que el repositorio tenga la última versión.
- Ninguno de los dos documentos se modificó. Las propuestas de este archivo se insertan a mano en el documento de Víctor, que tiene ediciones hechas a mano y no se regenera.
- El modelo oficial es el de Víctor (ROC-AUC temporal 0,829 en UNEMI y 0,768 en OULAD). Las cifras del documento de la sesión (0,830 y 0,766) corresponden al modelo anterior y **no se trasladan**. Todas las cifras propuestas abajo salen de `backend/ml/modelos/*/metricas.json`, `calidad_datos.json`, `deriva.json` y de las pruebas del repositorio integrado.
- Las cifras de los antecedentes nacionales y locales y de las tendencias se tomaron del texto completo de cada artículo; el pasaje y la fuente de verificación de cada una están en `documentacion/literatura/avance3_antecedentes.json` y `avance3_tendencias.json`, y sus referencias en los `.ris` del mismo nombre.

## 1. Resumen por sección

| Sección | Versión de Víctor | Versión de la sesión | Falta en la de Víctor |
|---|---|---|---|
| Preliminares | Certificados, declaración firmada por los autores, «CARPETA DIGITAL DEL AVANCE-3» con enlace de Drive después de los índices | Enlace del video antes del resumen; en la declaración de autoría figuran por error los nombres de las tutoras | Ver la sección 2 (observaciones) |
| Resumen y abstract | Cifras del modelo oficial y del origen móvil | Cifras del modelo anterior | Nada |
| 1.1 Descripción | Diagnóstico, Tabla 1, conveniencia y beneficiarios | Igual, más 1.1.1 y 1.1.2 | **1.1.1 Formulación del problema y preguntas de investigación; 1.1.2 Justificación** |
| 1.2 Propósito | Objetivos, delimitación, alcance y criterios de éxito | Igual, más 1.2.4 | **1.2.4 Matriz de congruencia** |
| 1.3 Base conceptual | 1.3.1 a 1.3.7 (antecedentes internacionales en la tabla de trabajos previos) | 1.3.1 a 1.3.11 | **Antecedentes nacionales y locales, vacío de investigación, contexto tecnológico e institucional y definición de términos** |
| 2. Análisis del caso | Completo, con RF y RNF de operación del modelo | Versión anterior | Nada |
| 3.1.6 Evaluación | Validación temporal, **origen móvil por periodo**, desempeño por carrera, prospectiva, equidad, segmentación y consulta | Validación temporal y desglose por periodo (modelo anterior) | Nada: el desglose por periodo de Víctor es más completo; el de la sesión se descarta |
| 3.1.7 Despliegue y operación | MLflow, Evidently, Great Expectations y Metabase integrados (`backend/mlops/`) | Las mismas herramientas como módulos opcionales aparte (3.3.2) | Nada: se conserva la de Víctor; la 3.3.2 de la sesión se descarta |
| 3.2.1 a 3.2.7 Diseño | Completo | Igual | Nada |
| 3.2.8 Tendencias | No existe | Análisis de cinco tendencias con su tabla | **3.2.8 Análisis de las tecnologías empleadas y tendencias actuales** (adaptada a la integración de Víctor) |
| 3.3 Desarrollo | Tecnologías, código del frontend y del backend | No existe; su 3.3 son resultados | **Endurecimiento de la seguridad** (nueva 3.3.4) |
| 4.1 Conclusiones | Una por objetivo, con origen móvil y MLOps | Una por objetivo, con modelo anterior | **Mención de las brechas de seguridad corregidas** |
| 4.3 Recomendaciones | Autoridades, bienestar, TI y futuros trabajos | Igual, más «continuidad del caso» | **Párrafo de continuidad del caso** |
| 5. Referencias | 34 | 55 | **27 referencias** que usan los textos propuestos |
| 6. Anexos | A guía, B conjunto dorado, C gobierno de datos, D instrumento de usabilidad, E enlaces | A, B, C video, D gobierno de datos (LOPDP), E solicitud de datos | **Remisión al documento complementario de LOPDP (en el anexo C) y nuevo anexo F: solicitud de datos anonimizados** |

Al insertar las secciones nuevas cambia la numeración de tablas y figuras: hay que renumerar los títulos y actualizar los índices (Word: seleccionar todo y F9).

## 2. Observaciones sobre la versión de Víctor (no se modificó nada)

1. **Certificado antiplagio.** El certificado dice que Compilatio registró «un 0 % de porcentaje de similitud». El documento todavía no pasó por el análisis y la carrera usa Turnitin. Hay que dejar el porcentaje en blanco hasta tener el reporte, o ponerlo cuando las tutoras lo emitan.
2. **Dos carpetas de Drive distintas.** Antes del resumen aparece `https://drive.google.com/drive/folders/1_4Sjs--ItL6XhGG0o2BSjwcMR6BIKv_l` y en el anexo E `https://drive.google.com/drive/folders/1ZOVwEslSaSjJbUeS1RCL1q3BDyVea9tT`. Debe quedar una sola. Además, el enlace está después de los índices y no en la portada; si la tutora lo pide en la portada, hay que moverlo.
3. **Texto heredado del Avance 2.** En 1.1 dice «En este Avance 2 se rehízo el simulador…». Propuesta: «En la segunda etapa del proyecto se rehízo el simulador…».
4. **Enlace del video.** La versión de la sesión tenía «ENLACE DEL VIDEO – PRESENTACION DEL PROYECTO» (`https://drive.google.com/file/d/18_yiDyvGPhoAgMhu4lMhR_w30cAHkOoj/view?usp=drive_link`); en la de Víctor no aparece. Conviene agregarlo en el anexo E cuando el video final esté subido.

## 3. Texto propuesto para insertar

### 3.1 Nueva 1.1.1 Formulación del problema y preguntas de investigación

Ubicación: al final de 1.1 Descripción, después del párrafo «Beneficiarios».

> **1.1.1 Formulación del problema y preguntas de investigación**
>
> A partir del diagnóstico anterior, el problema se formula así: las autoridades académicas y el personal de bienestar estudiantil de las IES ecuatorianas no disponen de una herramienta que, con los datos de trayectoria que la institución ya registra, anticipe qué estudiantes abandonarán en el periodo siguiente, explique por qué y permita consultar esa información sin depender del área de tecnología y con protección de los datos personales. La pregunta general que orienta el caso es: ¿cómo puede un sistema web basado en aprendizaje automático y consulta conversacional anticipar el abandono estudiantil de forma confiable, explicable y conforme a la LOPDP? De ella se desprenden cuatro preguntas específicas, una por cada objetivo específico:
>
> P1. ¿Qué variables de trayectoria, matrícula, aula virtual, evaluaciones y cartera, disponibles al cierre de cada periodo, se asocian con el abandono en el periodo siguiente?
>
> P2. ¿Qué desempeño alcanza un modelo calibrado y explicable cuando se evalúa con periodos que no vio durante el entrenamiento, tanto con datos de prueba de la UNEMI como con datos reales?
>
> P3. ¿Qué componentes y controles necesita el sistema web para que la autoridad consulte la predicción, entienda sus razones y registre el acompañamiento?
>
> P4. ¿En qué medida el prototipo cumple los criterios de aceptación predictivos, de exactitud de la consulta conversacional y de protección de datos fijados antes de evaluarlo?

### 3.2 Nueva 1.1.2 Justificación

Ubicación: después de 1.1.1. Complementa los párrafos «Conveniencia y utilidad» y «Beneficiarios», que se mantienen.

> **1.1.2 Justificación**
>
> Justificación práctica. El abandono que se detecta tarde ya no puede atenderse; un sistema que ordena a los estudiantes por riesgo al cierre de cada periodo le da a bienestar estudiantil un periodo completo para intervenir, y la consulta en lenguaje natural reduce la dependencia técnica que la literatura identifica como barrera para usar la inteligencia de negocios en las IES (Sequeira et al., 2024). Justificación metodológica. El caso aplica una validación más exigente que la habitual en los estudios revisados: agrupa por estudiante, reserva los periodos más recientes, repite la validación con origen móvil y añade una evaluación prospectiva, prácticas que Duro et al. (2026) señalan como necesarias para que el desempeño informado sea realista. Justificación tecnológica y legal. La protección de los datos se resuelve en el motor de base de datos y no solo en la aplicación, en línea con los principios de finalidad, minimización y seguridad de la LOPDP (Asamblea Nacional del Ecuador, 2021). Justificación social. La educación superior pública se financia con recursos del Estado, y cada estudiante que abandona representa una inversión pública y familiar que no llega a término; anticipar el riesgo es, por tanto, una forma de cuidar esa inversión.

(Se agregó «repite la validación con origen móvil» para que coincida con la 3.1.6 de Víctor.)

### 3.3 Nueva 1.2.4 Matriz de congruencia

Ubicación: al final de 1.2.3, después del párrafo «Criterios de éxito revisados». Las secciones de la última columna siguen la numeración de la versión de Víctor.

> **1.2.4 Matriz de congruencia**
>
> La Tabla N muestra la relación entre el problema, las preguntas, los objetivos, las variables o dimensiones y las técnicas con que se responde cada pregunta; cada fila se cierra con la sección del documento donde se presenta el resultado.
>
> **Tabla N.** *Matriz de Congruencia del Estudio de Caso*

| Pregunta | Objetivo específico | Variables o dimensiones | Técnica e instrumento | Resultado en |
|---|---|---|---|---|
| P1 | OE1. Analizar los procesos de seguimiento y las variables asociadas al abandono | Rendimiento, asistencia, matrícula, aula virtual, evaluaciones, cartera | Revisión de literatura; análisis exploratorio del panel estudiante-periodo | 1.3; 2.1; 3.1.3 |
| P2 | OE2. Construir y validar un modelo calibrado y explicable | Probabilidad de abandono en t+1; ROC-AUC, PR-AUC, recall, Brier | Validación cruzada agrupada, prueba temporal, origen móvil por periodo, prueba prospectiva, SHAP | 3.1.5; 3.1.6 |
| P3 | OE3. Implementar el sistema web por roles | Panel, ficha, segmentación, consulta conversacional, seguimiento | CRISP-DM e incrementos con pruebas; arquitectura cliente-servidor en capas | 3.1.7; 3.2; 3.3 |
| P4 | OE4. Evaluar el prototipo frente a los criterios de aceptación | Métricas predictivas, exactitud por ejecución, preguntas maliciosas, fugas entre instituciones, calidad de datos y deriva | Conjunto de referencia, pruebas automatizadas y de integración, Great Expectations, Evidently | 2.1.8; 3.1.6; 3.1.8; 4.1 |

> *Nota.* Problema general: detección tardía del abandono en las IES ecuatorianas. Elaboración propia.

### 3.4 Nuevas 1.3.7 Antecedentes nacionales y locales y 1.3.8 Vacío de investigación

Ubicación: después de 1.3.6 Comparación con trabajos previos. La actual 1.3.7 «Aporte, beneficios y utilidad del trabajo» pasa a ser 1.3.9.

> **1.3.7 Antecedentes nacionales y locales**
>
> Antecedentes nacionales. En el Ecuador, la predicción del abandono se ha estudiado con datos de varias universidades públicas y particulares. Sandoval-Palis et al. (2020) compararon, en el curso de nivelación de la Escuela Politécnica Nacional, una regresión logística con una red neuronal y obtuvieron un AUC de 0,795 con la red frente a 0,475 con la regresión. Albán y Mauricio (2019) informaron exactitudes superiores al 96 % con redes neuronales en una universidad pública, aunque con factores autodeclarados por encuesta. Guanin-Fajardo et al. (2024), en la Universidad Técnica Estatal de Quevedo, y Cuzme Romero et al. (2025), en la Universidad Técnica de Manabí, aplicaron CRISP-DM: el primero alcanzó un AUC de 87,75 % con XGBoost y el segundo un AUC de 0,95 con Random Forest. En la Escuela Superior Politécnica del Litoral, Quijije-Castro et al. (2026) pasaron de la predicción a la prescripción con un Random Forest calibrado, SHAP y contrafactuales (ROC-AUC entre 0,95 y 0,97). Otros trabajos explican las causas: Buenaño et al. (2024) encontraron con modelos de supervivencia de Cox que pesan más los factores institucionales y académicos; Cedillo-Quizhpe et al. (2026) vincularon las expectativas académicas con la intención de abandono en la Universidad de Cuenca; y Pertegal-Felices et al. (2022) asociaron menor resiliencia con el abandono durante la pandemia en once universidades.
>
> Antecedentes locales. En la propia UNEMI, Arévalo-Cordovilla y Peña (2024) predijeron el éxito en un curso en línea de programación con datos del aula virtual (AUC de 0,9354 con regresión logística) y, con 2.225 estudiantes de una carrera en línea, compararon ensambles con SHAP y métricas de equidad, con un AUC de 0,953 para LightGBM (Arévalo-Cordovilla y Peña, 2025). En 2026 llevaron el modelo a un piloto con un asistente conversacional por WhatsApp que identificó a 39 estudiantes en riesgo, con una tasa de respuesta de 89,7 %, aunque sin grupo de control ni medición de la exactitud en uso (Arévalo-Cordovilla y Peña, 2026). Cabezas-Quinto et al. (2025) documentaron en las carreras de ingeniería de la UNEMI una caída de la aprobación femenina de 63 % en 2016 a 14 % en 2023, con la barrera económica como factor de mayor peso.
>
> Lectura crítica. Los AUC nacionales y locales superiores a 0,95 se obtuvieron con particiones aleatorias o validación cruzada dentro de una misma cohorte, sobre una carrera o un curso, y con el éxito académico o el abandono como desenlace final; ninguno evaluó con periodos posteriores al entrenamiento, que es la condición en la que operará un sistema real. Por eso sus cifras no son comparables con las de este caso, que reserva los periodos más recientes y obtiene valores más modestos. Además, salvo el piloto de Arévalo-Cordovilla y Peña (2026), los estudios entregan un modelo y no un sistema en uso; y ninguno resuelve la consulta de la autoridad en lenguaje natural ni el aislamiento de los datos conforme a la LOPDP.
>
> **1.3.8 Vacío de investigación**
>
> La revisión de los antecedentes internacionales (Tabla de trabajos previos), nacionales y locales permite precisar el vacío que atiende este caso. Existen modelos con buen desempeño, pero (a) rara vez se validan con periodos futuros y con datos reales de más de una institución; (b) casi nunca se integran en un sistema con roles, explicación por estudiante y registro del acompañamiento; (c) la consulta en lenguaje natural sobre los resultados no se ha evaluado con exactitud por ejecución ni con preguntas maliciosas; y (d) la protección de los datos estudiantiles se trata como un requisito general y no como un control técnico aplicado en la base de datos. El caso práctico aborda los cuatro puntos en un mismo prototipo, con la UNEMI como contexto.

### 3.5 Nuevas 1.3.10 Contexto tecnológico e institucional y 1.3.11 Definición de términos

Ubicación: después de 1.3.9 (la actual «Aporte, beneficios y utilidad del trabajo»).

> **1.3.10 Contexto tecnológico e institucional**
>
> El caso se sitúa en la UNEMI, universidad pública ubicada en Milagro, provincia del Guayas, que organiza su oferta por facultades y carreras con modalidades presencial, semipresencial y en línea, y que, como el resto de IES del país, registra matrícula, calificaciones, asistencia, actividad en el aula virtual y cartera en sistemas distintos. En el plano normativo, desde 2021 la LOPDP obliga a quien trata datos personales a justificar la finalidad, minimizar los datos y aplicar medidas de seguridad y responsabilidad proactiva (Asamblea Nacional del Ecuador, 2021), y la Superintendencia de Protección de Datos Personales fijó las reglas de evaluación de impacto y de uso de inteligencia artificial (Superintendencia de Protección de Datos Personales, 2025, 2026), lo que condiciona cualquier uso analítico de la trayectoria estudiantil. En el plano tecnológico, el prototipo se construyó con herramientas libres o de edición gratuita (SQL Server 2022 Developer en Docker, Python, FastAPI y React) que pueden ejecutarse en un solo equipo de la institución, y con proveedores de modelos de lenguaje accedidos por internet, que por su ubicación fuera del país exigen controles adicionales sobre los datos que reciben.
>
> **1.3.11 Definición de términos**
>
> La Tabla N define los términos que se usan con un sentido preciso a lo largo del documento.
>
> **Tabla N.** *Definición de Términos Relevantes*

| Término | Definición en este trabajo |
|---|---|
| Abandono (en t+1) | Situación de un estudiante activo al cierre del periodo t que no continúa en el periodo siguiente sin haberse graduado; en OULAD, retiro del módulo en el corte de 28 días siguiente. |
| Alerta temprana | Señal emitida antes de que ocurra el abandono, con tiempo para intervenir. |
| Aprendizaje automático | Conjunto de métodos que aprenden de datos históricos una función para estimar un resultado en casos nuevos. |
| Calibración | Ajuste de las salidas del modelo para que la probabilidad estimada coincida con la frecuencia observada (Platt, 1999). |
| ROC-AUC | Probabilidad de que el modelo asigne más riesgo a un estudiante que abandona que a uno que continúa; 0,5 equivale al azar. |
| PR-AUC | Área bajo la curva de precisión y recall; se compara con la prevalencia del abandono. |
| Recall | Proporción de los abandonos reales que el sistema alerta. |
| Validación temporal | Evaluación con periodos posteriores a los usados para entrenar. |
| Validación con origen móvil | Repetición de la validación temporal para cada periodo reciente, entrenando solo con los periodos anteriores a él (Tashman, 2000). |
| SHAP | Método que reparte la predicción de un caso entre sus variables (Lundberg y Lee, 2017). |
| PSI | Índice de estabilidad poblacional; mide cuánto cambió la distribución de una variable entre el entrenamiento y los datos nuevos. |
| Deriva de los datos | Cambio en la distribución de las variables de entrada respecto de las usadas para entrenar, que puede degradar el modelo (Gama et al., 2014). |
| NL2SQL | Traducción de una pregunta en lenguaje natural a una consulta SQL (Ascoli y Choi, 2025). |
| Métrica certificada | Consulta SQL fija, verificada por los autores, con la que el sistema responde una pregunta conocida sin recurrir al modelo de lenguaje. |
| Esquema estrella | Modelo dimensional con una tabla de hechos y dimensiones compartidas (Kimball y Ross, 2013). |
| Seudonimización | Sustitución de los datos que identifican a una persona por códigos, de modo que no pueda identificarse sin información adicional guardada aparte. |

> *Nota.* Elaboración propia a partir de las fuentes citadas.

(Las filas «Validación con origen móvil» y «Deriva de los datos» se agregaron para la versión de Víctor y citan referencias que ya están en su lista: Tashman, 2000; Gama et al., 2014.)

### 3.6 Nueva 3.2.8 Análisis de las tecnologías empleadas y tendencias actuales

Ubicación: después de 3.2.7 Recursos. El texto se adaptó a la integración de Víctor: las herramientas ya no son módulos opcionales sino parte del pipeline (sección 3.1.7).

> **3.2.8 Análisis de las tecnologías empleadas y tendencias actuales**
>
> Las tecnologías del prototipo se eligieron con matrices ponderadas (sección 3.2.2); esta sección las contrasta con cinco tendencias que la literatura reciente identifica para los sistemas de aprendizaje automático en producción y que la tutoría recomendó considerar.
>
> MLOps y registro de experimentos. Kreuzberger et al. (2023) definen MLOps como el conjunto de prácticas para llevar un modelo a producción y mantenerlo, con un registro de metadatos de cada entrenamiento como pieza central. Entre 16 plataformas evaluadas, MLflow es la de mayor adopción y se recomienda para equipos pequeños por su bajo costo de operación (Berberi et al., 2025). El prototipo ya guardaba en cada metricas.json los hiperparámetros, la búsqueda de Optuna y las métricas; con MLflow, cada entrenamiento y cada monitoreo quedan además en un registro consultable y comparable entre corridas (sección 3.1.7).
>
> Monitoreo de deriva. Los modelos educativos se degradan cuando cambia el comportamiento estudiantil: Sonnleitner et al. (2025) observaron predicciones sesgadas al pasar del periodo de pandemia al posterior, y Kustitskaya et al. (2025) vigilaron tres años de modelos desplegados con el PSI, con los mismos umbrales de 0,10 y 0,25 que usa este prototipo. El PSI mide el cambio en las variables, pero no su efecto en la precisión, por lo que conviene complementarlo (Becker y Becker, 2021); por eso el prototipo ejecuta además Evidently AI, que aplica pruebas estadísticas por variable sobre los mismos datos.
>
> Calidad de datos como compuerta. Bodor et al. (2023) y Bayram et al. (2026) proponen validar la consistencia y la distribución de los datos antes de entrenar o calificar, y citan Great Expectations como herramienta para expresar esas reglas. El ETL del prototipo ya rechazaba una carga con columnas faltantes o valores fuera de rango; expresadas como 23 expectativas de Great Expectations sobre la trayectoria cargada, esas reglas quedan documentadas y auditables, y una falla crítica detiene el entrenamiento.
>
> Explicabilidad. SHAP se consolidó en la predicción del abandono porque permite explicar a la persona y no solo al modelo (Nagy y Molontay, 2024), y en la propia UNEMI se usó para identificar las notas tempranas como principal señal (Arévalo-Cordovilla y Peña, 2025). El prototipo lo aplica en cada ficha y traduce los factores a frases en español.
>
> Consulta en lenguaje natural frente a inteligencia de negocios de autoservicio. Las revisiones de Text-to-SQL con modelos de lenguaje muestran avances, pero también alucinaciones (Hong et al., 2025) y una superficie de ataque real: las puertas traseras de inyección alcanzan éxitos de hasta 99 % (Zhang et al., 2023) y una arquitectura con clasificadores de preguntas y de consultas mejora la seguridad en 70 % (Chafik et al., 2025). La alternativa es la inteligencia de negocios de autoservicio, como Metabase, cuyos usuarios no técnicos enfrentan dificultades de adopción (Lennerholt et al., 2021); los tableros con lenguaje natural mejoran la eficiencia para encontrar información (Ruoff et al., 2023). Por eso el prototipo entrega a la autoridad una consulta con métricas certificadas, validación del árbol SQL y cuentas de solo lectura, y deja Metabase, limitado al esquema agregado bi, para los analistas.
>
> Alerta temprana con intervención. La predicción por sí sola no reduce el abandono: en un experimento aleatorizado, la consejería apoyada en un sistema de alerta no lo redujo (Plak et al., 2022), mientras que las intervenciones de fijación de metas sí lo hicieron en un curso en línea (Bañeres et al., 2023). De ahí que el prototipo registre cada intervención, para poder medir su efecto en una etapa posterior.
>
> La Tabla N resume cada tendencia, lo que ya cubría el prototipo y el uso que se le dio a la herramienta de referencia.
>
> **Tabla N.** *Tendencias Tecnológicas y su Relación con el Prototipo*

| Tendencia | Herramienta de referencia | Lo que ya tenía el prototipo | Uso en el prototipo |
|---|---|---|---|
| Registro de experimentos (MLOps) | MLflow | metricas.json con hiperparámetros y métricas por corrida | Una corrida por entrenamiento y por monitoreo en el experimento de cada institución |
| Monitoreo de deriva | Evidently AI | PSI de las 10 variables más importantes (monitoreo.json) | Pruebas estadísticas por variable en el paso «mlops» del pipeline (deriva.json) |
| Calidad de datos | Great Expectations | Validación de contrato y de filas en el ETL | 23 expectativas sobre la trayectoria cargada; una falla crítica detiene el entrenamiento (calidad_datos.json) |
| Explicabilidad | SHAP | Tres factores por estudiante en la ficha | Ya integrado |
| Consulta de autoservicio | Metabase | Consulta conversacional con métricas certificadas | Vía de consulta agregada para analistas, con la cuenta metabase_lector sobre el esquema bi |

> *Nota.* Elaboración propia a partir de la literatura citada.

### 3.7 Resultados por periodo y herramientas: no se insertan

- **Desempeño por periodo.** La versión de Víctor ya lo presenta en 3.1.6 con validación con origen móvil (UNEMI de 0,827 a 0,836; OULAD de 0,742 a 0,779) y por carrera. Es más completo que la Tabla 36 de la sesión, que además usaba el modelo anterior. No se inserta nada.
- **Herramientas (MLflow, Evidently, Great Expectations y Metabase).** La versión de Víctor las presenta en 3.1.7 como parte del pipeline, con resultados de la última corrida (23/23 expectativas en ambas instituciones; deriva en 6 de 38 variables en UNEMI y en 16 de 33 en OULAD). La 3.3.2 de la sesión describe módulos opcionales que se descartaron en la integración del código y cifras que ya no corresponden (25 expectativas, OULAD 24/25). No se inserta nada.
- **Hallazgo de la sesión sobre Metabase.** Con la cuenta `chat_reader` y SQL nativo, un usuario de Metabase podía fijar el contexto de cualquier institución. La versión de Víctor evita ese riesgo con un diseño distinto: la cuenta `metabase_lector` solo lee el esquema `bi`, con agregados y sin identificadores, y tiene denegado `dbo`. Las vistas `bi.*` muestran todas las instituciones, así que un despliegue multiinstitución con Metabase necesitaría una cuenta o un filtro por institución. Se propone como recomendación (sección 3.10, punto 5).

### 3.8 Nueva 3.3.4 Endurecimiento de la seguridad

Ubicación: al final de 3.3 Desarrollo, después de 3.3.3 Código del backend.

> **3.3.4 Endurecimiento de la seguridad**
>
> La elaboración del documento de gobierno de datos (Anexo C) y su análisis artículo por artículo de la LOPDP identificaron cuatro brechas en el prototipo, que se corrigieron y quedaron cubiertas por pruebas automatizadas. Primera, la pregunta del usuario salía hacia el proveedor de IA tal como se escribió; ahora la función depurar_texto de core/privacidad.py reemplaza las cédulas, los correos, los teléfonos y los nombres de estudiantes de la institución activa por marcadores (CEDULA_1, NOMBRE_1…) que solo se restauran en el servidor, en el SQL que se ejecuta localmente. Segunda, la interpretación con IA de un resultado no dejaba rastro; ahora cada llamada se registra en la bitácora como evento INTERPRETACION, con el proveedor, el número de filas enviadas y la huella del mensaje, nunca con los datos. Tercera, la función filas_para_ia excluye del envío los textos libres del seguimiento y, en los resultados individuales, las columnas cuasi identificadoras, como quién registró la intervención o la ciudad de residencia. Cuarta, la conexión con SQL Server se cifra siempre (Encrypt=yes), y el certificado autofirmado del contenedor solo se acepta si la variable DB_TRUST_SERVER_CERT lo permite: por defecto en desarrollo y no en producción. Además, las cuentas chat_reader, app_seguimiento y metabase_lector se crean con la política de contraseñas del motor activa (CHECK_POLICY = ON). Las pruebas test_privacidad_ia.py y test_conexion_cifrada.py verifican estos controles. Con ellas, el backend suma 228 pruebas automatizadas: 219 se ejecutan sin base de datos, 8 de integración requieren el contenedor de SQL Server y 1 requiere MLflow instalado.

Si se quiere una figura de código para esta subsección, la función `depurar_texto` (`backend/core/privacidad.py`) y `_cadena` (`backend/core/db.py`) son los extractos más cortos y claros.

### 3.9 Conclusiones: frase propuesta

Ubicación: al final del párrafo «En relación con el cuarto objetivo…», después de «…es la siguiente verificación del prototipo.».

> Al documentar el gobierno de datos se identificaron cuatro brechas de seguridad: la pregunta salía sin depurar hacia el proveedor de IA, la interpretación no quedaba en la bitácora, los textos libres podían enviarse y la conexión con la base no se cifraba. Las cuatro se corrigieron y quedaron cubiertas por pruebas automatizadas (sección 3.3.4).

### 3.10 Recomendaciones: párrafo de continuidad

Ubicación: al final de 4.3, después de «A futuros trabajos de titulación…».

> Para dar continuidad al caso práctico: (1) validar el modelo con datos reales anonimizados de una carrera de la UNEMI y reportar el ROC-AUC y el recall por periodo, con el protocolo de anonimización y la solicitud ya preparados (Anexo F); (2) realizar la prueba de usabilidad con dos autoridades y tres profesionales de bienestar, con la meta de éxito de 80 % y SUS de 68 (Anexo D); (3) completar la evaluación de impacto exigida por la LOPDP antes de usar datos reales (Anexo C); (4) en producción, instalar en SQL Server un certificado emitido por una autoridad de confianza y fijar DB_TRUST_SERVER_CERT=no, y reemplazar la detección de columnas personales por una lista blanca de columnas que pueden enviarse a la IA; y (5) si se habilita Metabase para más de una institución, darle a cada una su propia cuenta o un filtro por institución, porque el esquema bi reúne a todas.

### 3.11 Anexos

**En el anexo C (gobierno de datos)**, al final del párrafo que remite a `documentacion/gobierno_datos/GOBIERNO_DE_DATOS.md`:

> El documento se complementa con documentacion/tecnica/GOBIERNO_DE_DATOS_LOPDP.md, que desarrolla artículo por artículo, con la página de la edición consultada, el fundamento de cada regla: definiciones y principios (arts. 4 y 10), derechos del titular y sus plazos (arts. 12 a 20 y 62), retención y eliminación (art. 10, lit. i, y art. 15), notificación de vulneraciones (arts. 43 y 46) y evaluación de impacto (art. 42), además de la lista de brechas pendientes antes de cargar datos reales.

**Nuevo anexo F. Solicitud de datos académicos anonimizados** (después del anexo E):

> **Anexo F. Solicitud de datos académicos anonimizados**
>
> Para atender la recomendación de validar el modelo con datos reales de una carrera, los autores solicitaron por oficio a las docentes tutoras que canalicen ante la instancia universitaria correspondiente el acceso a un conjunto anonimizado de al menos seis periodos de una carrera, sin nombres, cédulas ni datos de contacto, con un código aleatorio por estudiante generado por la propia universidad. El oficio incluye el protocolo de anonimización y el compromiso de usar los datos solo para la validación académica, procesarlos en local, reportar resultados agregados y eliminarlos al concluir. Como el trámite excede el plazo de esta entrega, la validación se realizó con los datos de prueba de la UNEMI y con el conjunto real OULAD, y la solicitud se mantiene como antecedente para la continuidad del caso. El oficio y el correo de envío están en el repositorio, en documentacion/avances/Avance 3/12_SOLICITUD_DATOS/; el procedimiento de anonimización que se aplicaría está implementado en backend/scripts/anonimizar_carrera.py.

### 3.12 Referencias nuevas para la lista de Víctor

Son las 27 referencias que citan los textos propuestos y que no están en su lista. Se escribieron con «y» entre autores, como en el resto de su lista, y deben intercalarse en orden alfabético.

Albán, M., y Mauricio, D. (2019). Neural networks to predict dropout at the universities. *International Journal of Machine Learning and Computing, 9*(2), 149-153. https://doi.org/10.18178/ijmlc.2019.9.2.779

Arévalo-Cordovilla, F. E., y Peña, M. (2024). Comparative analysis of machine learning models for predicting student success in online programming courses: A study based on LMS data and external factors. *Mathematics, 12*(20), 3272. https://doi.org/10.3390/math12203272

Arévalo-Cordovilla, F. E., y Peña, M. (2025). Evaluating ensemble models for fair and interpretable prediction in higher education using multimodal data. *Scientific Reports, 15*(1), 29420. https://doi.org/10.1038/s41598-025-15388-9

Arévalo-Cordovilla, F. E., y Peña, M. (2026). Early detection and personalized academic support using a predictive chatbot for student success. *PeerJ Computer Science, 12*, e3656. https://doi.org/10.7717/peerj-cs.3656

Bañeres, D., Rodríguez-González, M. E., Guerrero-Roldán, A. E., y Cortadas, P. (2023). An early warning system to identify and intervene online dropout learners. *International Journal of Educational Technology in Higher Education, 20*(1), 3. https://doi.org/10.1186/s41239-022-00371-5

Bayram, F., Ahmed, B. S., y Hallin, E. (2026). End-to-end data quality-driven framework for machine learning in production environment. *Heliyon, 12*(1), e44416. https://doi.org/10.1016/j.heliyon.2025.e44416

Becker, A., y Becker, J. (2021). Dataset shift assessment measures in monitoring predictive models. *Procedia Computer Science, 192*, 3391-3402. https://doi.org/10.1016/j.procs.2021.09.112

Berberi, L., Kozlov, V., Nguyen, G., Sáinz-Pardo Díaz, J., Calatrava, A., Moltó, G., Tran, V., y López García, Á. (2025). Machine learning operations landscape: Platforms and tools. *Artificial Intelligence Review, 58*(6), 167. https://doi.org/10.1007/s10462-025-11164-3

Bodor, A., Hnida, M., y Daoudi, N. (2023). Machine learning models monitoring in MLOps context: Metrics and tools. *International Journal of Interactive Mobile Technologies, 17*(23), 125-139. https://doi.org/10.3991/ijim.v17i23.43479

Buenaño, E., Beletanga, M. J., y Mancheno, M. (2024). What factors are relevant to understanding dropout? Analysis at a co-financed university in Ecuador and policy implications, using survival Cox models. *Journal of Latinos and Education, 23*(4), 1400-1415. https://doi.org/10.1080/15348431.2023.2271570

Cabezas-Quinto, J. J., Chagerben Salinas, L. E., Vinueza Morales, M., Quintanilla Castellanos, J., y Vidal-Silva, C. (2025). Women in engineering at a regional public university: Trends, barriers, and retention strategies. *Societies, 15*(11), 303. https://doi.org/10.3390/soc15110303

Cedillo-Quizhpe, C., Arias Blanco, J. M., y Burguera Condon, J. L. (2026). Influencia de las expectativas académicas sobre los motivos de intención de abandono en estudiantes de una universidad ecuatoriana. *Educación XX1, 29*(1), 95-122. https://doi.org/10.5944/educxx1.42831

Chafik, S., Ezzini, S., y Berrada, I. (2025). Enhancing security in text-to-SQL systems: A novel dataset and agent-based framework. *Natural Language Processing, 31*(6), 1399-1422. https://doi.org/10.1017/nlp.2025.10008

Cuzme Romero, M. G., Meza, J., y García, R. (2025). Predicting student dropout risk using machine learning: A case study at the Technical University of Manabí. *Kasetsart Journal of Social Sciences, 46*(2), 460227. https://doi.org/10.34044/j.kjss.2025.46.2.27

Guanin-Fajardo, J. H., Guaña-Moya, J., y Casillas, J. (2024). Predicting academic success of college students using machine learning techniques. *Data, 9*(4), 60. https://doi.org/10.3390/data9040060

Hong, Z., Yuan, Z., Zhang, Q., Chen, H., Dong, J., Huang, F., y Huang, X. (2025). Next-generation database interfaces: A survey of LLM-based text-to-SQL. *IEEE Transactions on Knowledge and Data Engineering, 37*(12), 7328-7345. https://doi.org/10.1109/TKDE.2025.3609486

Kreuzberger, D., Kühl, N., y Hirschl, S. (2023). Machine learning operations (MLOps): Overview, definition, and architecture. *IEEE Access, 11*, 31866-31879. https://doi.org/10.1109/ACCESS.2023.3262138

Kustitskaya, T. A., Esin, R. V., y Noskov, M. V. (2025). Model drift in deployed machine learning models for predicting learning success. *Computers, 14*(9), 351. https://doi.org/10.3390/computers14090351

Lennerholt, C., Van Laere, J., y Söderström, E. (2021). User-related challenges of self-service business intelligence. *Information Systems Management, 38*(4), 309-323. https://doi.org/10.1080/10580530.2020.1814458

Nagy, M., y Molontay, R. (2024). Interpretable dropout prediction: Towards XAI-based personalized intervention. *International Journal of Artificial Intelligence in Education, 34*(2), 274-300. https://doi.org/10.1007/s40593-023-00331-8

Pertegal-Felices, M. L., Valdivieso-Salazar, D. A., Espín-León, A., y Jimeno-Morenilla, A. (2022). Resilience and academic dropout in Ecuadorian university students during COVID-19. *Sustainability, 14*(13), 8066. https://doi.org/10.3390/su14138066

Plak, S., Cornelisz, I., Meeter, M., y van Klaveren, C. (2022). Early warning systems for more effective student counselling in higher education: Evidence from a Dutch field experiment. *Higher Education Quarterly, 76*(1), 131-152. https://doi.org/10.1111/hequ.12298

Quijije-Castro, R., Constantine-Macías, A., Loayza, F., Valarezo-Anazco, E., Tapia-Rosero, A., Chiluiza-García, K., y Peláez, E. (2026). From prediction to prescription: Profile-aware prescriptive analytics for student dropout in a Latin American public university. *Frontiers in Education, 11*, 1918675. https://doi.org/10.3389/feduc.2026.1918675

Ruoff, M., Gnewuch, U., Maedche, A., y Scheibehenne, B. (2023). Designing conversational dashboards for effective use in crisis response. *Journal of the Association for Information Systems, 24*(6), 1500-1526. https://doi.org/10.17705/1jais.00801

Sandoval-Palis, I., Naranjo, D., Vidal, J., y Gilar-Corbi, R. (2020). Early dropout prediction model: A case study of university leveling course students. *Sustainability, 12*(22), 9314. https://doi.org/10.3390/su12229314

Sonnleitner, B., Madou, T., Deceuninck, M., Theodosiou, F., y Sagaert, Y. R. (2025). Evaluation of early student performance prediction given concept drift. *Computers and Education: Artificial Intelligence, 8*, 100369. https://doi.org/10.1016/j.caeai.2025.100369

Zhang, J., Zhou, Y., Hui, B., Liu, Y., Li, Z., y Hu, S. (2023). TrojanSQL: SQL injection against natural language interface to database. En *Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing* (pp. 4344-4359). Association for Computational Linguistics. https://doi.org/10.18653/v1/2023.emnlp-main.264

## 4. Control después de insertar

1. Cada cita nueva del texto tiene su referencia y cada referencia nueva se cita (27 en total).
2. Renumerar tablas y figuras y actualizar la tabla de contenido y los índices.
3. Revisar que la «Tabla de trabajos previos» citada en 1.3.8 tenga el número que le quede después de renumerar.
4. Corregir el certificado antiplagio, unificar el enlace de Drive y cambiar «En este Avance 2» (sección 2).
5. Copiar la versión final sobre `documentacion/avances/TRABAJO_FINAL_MARLON_VICTOR.docx` y su PDF (Word por COM) antes de subirla.
