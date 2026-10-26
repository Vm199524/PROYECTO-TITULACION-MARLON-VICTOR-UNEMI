# Guion del video del trabajo final (15 minutos)

**Tema:** Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional

**Autores:** Víctor Manuel Lluilema Pisco y Marlon David Pérez Almachi

Ritmo de referencia: 140 palabras por minuto. Lectura de las notas: Víctor ≈ 5.1 min y Marlon ≈ 5.7 min; la demostración en vivo (diapositiva «Demostración del sistema») suma unos 4 minutos. Total estimado: 15 minutos.

## Reparto por diapositiva

| # | Diapositiva | Expone | Palabras | Tiempo |
|---|---|---|---|---|
| 1 | Portada | Víctor | 49 | 21 s |
| 2 | Contenido | Víctor | 46 | 20 s |
| 3 | El problema | Víctor | 109 | 47 s |
| 4 | Objetivo general | Víctor | 49 | 21 s |
| 5 | Objetivos específicos | Víctor | 37 | 16 s |
| 6 | Trabajos previos frente al caso | Víctor | 94 | 40 s |
| 7 | Metodología CRISP-DM | Víctor | 91 | 39 s |
| 8 | Requerimientos | Víctor | 41 | 18 s |
| 9 | Arquitectura de la solución | Víctor | 92 | 39 s |
| 10 | Frontend y backend | Marlon | 101 | 43 s |
| 11 | Modelo de datos | Marlon | 75 | 32 s |
| 12 | Secuencia de una consulta en lenguaje natural | Marlon | 80 | 34 s |
| 13 | Resultados del modelo | Marlon | 94 | 40 s |
| 14 | Desempeño por periodo y por carrera | Marlon | 123 | 53 s |
| 15 | Consulta conversacional | Marlon | 67 | 29 s |
| 16 | Seguridad y gobierno de datos | Marlon | 86 | 37 s |
| 17 | Operación del modelo (MLOps) | Marlon | 81 | 35 s |
| 18 | Demostración del sistema | Víctor y Marlon | 53 | 23 s |
| 19 | Innovación y limitaciones | Marlon | 69 | 30 s |
| 20 | Conclusiones | Víctor | 77 | 33 s |

## Recomendaciones de grabación

- Grabar en vivo compartiendo la pantalla completa, con la cámara de quien expone visible.
- Cada uno inicia sesión con su propia cuenta de demostración antes de grabar; las contraseñas no se muestran en pantalla.
- Decir las cifras tal como están en el documento (coma decimal: «cero coma ochenta y tres»).
- Mostrar el enlace del repositorio (https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI) y de la carpeta digital del grupo (https://drive.google.com/drive/folders/1ZOVwEslSaSjJbUeS1RCL1q3BDyVea9tT).
- Ensayar con cronómetro: si sobra tiempo, ampliar la demostración; si falta, recortar adjetivos, no datos.

## Texto por diapositiva

### 1. Portada · Víctor

Buenos días. Somos Víctor Manuel Lluilema Pisco y Marlon David Pérez Almachi, de la carrera de Tecnologías de la Información, y presentamos nuestro trabajo de titulación: «Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional». Al sistema lo llamamos VicMar.

### 2. Contenido · Víctor

La presentación sigue el orden del trabajo final. Primero, el problema y lo que nos propusimos; después, la base teórica y la metodología. Luego mostraremos cómo está construido el sistema, qué resultados obtuvo, cómo protege los datos y, al final, el sistema funcionando y las conclusiones.

### 3. El problema · Víctor

Empecemos por el problema. El abandono universitario no es hipotético en el Ecuador: en un estudio con cinco cohortes de una universidad del país, 484 de 1.078 admitidos dejaron la carrera, y la probabilidad de abandono llegó a 44,90 %. Las señales que lo anticipan, como las notas, la asistencia, la actividad en el aula virtual o la deuda, ya están registradas, pero en sistemas separados y se consultan para saber el estado actual del estudiante, no para anticipar su retiro. Además, la literatura muestra que, cuando un modelo se prueba con cohortes futuras, su desempeño ronda 0,70; por eso fijamos un criterio realista de 0,75.

### 4. Objetivo general · Víctor

Nuestro objetivo general responde a tres preguntas. Qué: un prototipo web de alerta temprana. Cómo: con la metodología CRISP-DM, un almacén dimensional, un modelo LightGBM calibrado y una consulta en lenguaje natural. Para qué: para que la autoridad y bienestar estudiantil lleguen antes de que el estudiante abandone.

### 5. Objetivos específicos · Víctor

Para cumplirlo planteamos cuatro objetivos específicos, cada uno con un entregable verificable: el análisis que dio origen a los requerimientos, el modelo validado, el sistema implementado y la evaluación contra criterios fijados antes de ver los resultados.

### 6. Trabajos previos frente al caso · Víctor

En la base conceptual partimos de Tinto, que explica el abandono como falta de integración académica y social, y de Bean y Metzner, que muestran el peso de los factores externos. Luego comparamos catorce estudios; aquí vemos siete. Los modelos predictivos informan desde 76 % hasta casi 100 %, pero los valores más altos suelen salir de particiones aleatorias que mezclan periodos. La última columna es la clave: ninguno entrega la predicción dentro de un sistema con roles, consulta en lenguaje natural y aislamiento de datos a la vez. Ese es el vacío que cubre VicMar.

### 7. Metodología CRISP-DM · Víctor

Para desarrollarlo aplicamos CRISP-DM, con un entregable verificable por fase. En comprensión del negocio fijamos los criterios de éxito y las historias de usuario. En comprensión y preparación de los datos construimos el ETL, el esquema estrella y el panel estudiante-periodo sin fuga de información futura. En modelado comparamos cuatro algoritmos. En evaluación validamos en el tiempo, por periodo, por carrera y de forma prospectiva. Y en despliegue el modelo quedó dentro del sistema, con calificación por lotes y monitoreo de la calidad y la deriva de los datos.

### 8. Requerimientos · Víctor

De ese análisis salieron 23 requerimientos funcionales, 11 no funcionales y diez historias de usuario escritas para una autoridad que no sabe SQL. Lo importante es que los criterios de aceptación se fijaron antes de entrenar, para no acomodarlos al resultado.

### 9. Arquitectura de la solución · Víctor

La arquitectura es cliente-servidor en capas. Abajo, las fuentes académicas pasan por el ETL al almacén ALMACEN_ACADEMICO en SQL Server. El pipeline entrena el modelo, califica a los estudiantes activos, segmenta las carreras y, al final, valida la calidad y la deriva. En el medio, la API FastAPI expone 27 servicios protegidos por rol. Arriba, la interfaz React. Lo importante es que el panel, la ficha y la consulta leen las mismas vistas gobernadas, por eso las cifras coinciden en todo el sistema. Ahora Marlon explica cómo está construido por dentro.

### 10. Frontend y backend · Marlon

Gracias, Víctor. En el frontend usamos React 18 con TypeScript, Vite y Tailwind; cada rol ve solo su menú, hay tema claro y oscuro y funciona en el celular. TanStack Query maneja la caché de las consultas. El backend es FastAPI en Python, el mismo lenguaje del modelo: autentica con JWT, verifica el rol en cada uno de los 27 servicios y registra la auditoría. El modelo usa LightGBM, Platt y SHAP; la consulta usa un enrutador TF-IDF, modelos de lenguaje en cascada y el validador sqlglot. Y la operación del modelo se apoya en MLflow, Great Expectations y Evidently.

### 11. Modelo de datos · Marlon

El almacén sigue el modelo dimensional de Kimball. Las tablas de hechos guardan las matrículas por periodo, las predicciones, los segmentos de carrera y las intervenciones de bienestar; las dimensiones describen al estudiante, la carrera, el periodo y la institución. Un detalle de diseño importante: las aplicaciones nunca leen las tablas directamente, sino vistas VIS que se filtran solas por la institución fijada en la sesión. El diccionario de datos completo está en el documento.

### 12. Secuencia de una consulta en lenguaje natural · Marlon

Este diagrama de secuencia muestra cómo se responde una pregunta en español. Primero, los guardarraíles descartan pedidos peligrosos, como borrar o modificar datos. Luego el enrutador busca una de las 40 métricas certificadas; si la encuentra, responde en milisegundos. Si no, un modelo de lenguaje propone el SQL, el validador comprueba que sea solo una consulta de lectura sobre vistas permitidas y se ejecuta con la cuenta chat_reader, que únicamente ve los datos de su institución. Son tres barreras independientes.

### 13. Resultados del modelo · Marlon

Pasemos a los resultados. El ROC-AUC mide qué tan bien ordena el modelo: la probabilidad de que un estudiante que abandona quede por encima de uno que no; 0,5 es azar y 1 es perfecto. Comparamos cuatro algoritmos con validación cruzada agrupada por estudiante y LightGBM fue el mejor en las dos instituciones. Con periodos que el modelo nunca vio obtuvimos 0,829 en los datos de prueba de la UNEMI y 0,768 con los datos reales de OULAD, y con el umbral medio detecta cerca de 79 % de los abandonos.

### 14. Desempeño por periodo y por carrera · Marlon

En la tutoría se nos pidió validar con datos reales anonimizados y reportar el AUC y el recall por periodo. Lo hicimos con validación de origen móvil: cada periodo se predijo entrenando solo con los anteriores, como si el sistema se hubiera puesto en marcha en esa fecha. En OULAD el ROC-AUC se mantuvo entre 0,742 y 0,779, por encima del mínimo de 0,70 que fijamos para cada periodo. Por módulo, que en OULAD hace las veces de carrera, cinco de siete superan ese mínimo; los dos que no lo alcanzan tienen muy pocos abandonos, y eso nos dice que los umbrales deben revisarse por carrera. Para una carrera real de la UNEMI dejamos listo el procedimiento de anonimización.

### 15. Consulta conversacional · Marlon

La consulta conversacional se evaluó con un conjunto dorado: preguntas reales de una autoridad, con su resultado esperado. Acertó en todas por resultado de ejecución, contuvo las ocho preguntas maliciosas, como intentos de borrar tablas o de ver otra institución, y nunca leyó datos ajenos. La mayoría responde en milisegundos porque usa métricas certificadas; el modelo de lenguaje solo entra cuando la pregunta no tiene una métrica.

### 16. Seguridad y gobierno de datos · Marlon

La seguridad no depende solo de la pantalla: está en la base de datos. Cada conexión fija su institución con SESSION_CONTEXT y las vistas filtran solo esa; SQL Server no deja cambiarla en la misma sesión. Las cuentas tienen el mínimo privilegio, hay tres roles y todo queda auditado. Para validar con una carrera real de la UNEMI dejamos el documento de gobierno de datos según la LOPDP y un script que reemplaza las cédulas por seudónimos y garantiza k-anonimato con k igual a cinco.

### 17. Operación del modelo (MLOps) · Marlon

También incorporamos las herramientas sugeridas en la tutoría. Great Expectations valida los datos antes de entrenar y detiene el proceso si falla una regla crítica. Evidently compara a los estudiantes de hoy con los del entrenamiento para detectar la deriva, que es la señal para reentrenar. MLflow registra cada modelo con sus parámetros y métricas. Metabase queda como vía de consulta para analistas, sin datos personales. Y todo el sistema está cubierto por pruebas automatizadas del backend y de la interfaz.

### 18. Demostración del sistema · Víctor y Marlon

Ahora mostramos el sistema funcionando (unos cuatro minutos). Víctor ingresa como autoridad, recorre el panel y la lista priorizada y abre la ficha de un estudiante con sus tres razones. Marlon hace una pregunta en lenguaje natural y muestra la calidad del modelo por periodo. El código está en el repositorio de GitHub.

### 19. Innovación y limitaciones · Marlon

La innovación no está en un algoritmo nuevo, sino en la integración: una predicción explicada en español, una consulta certificada y un aislamiento aplicado en el motor, pensados para una universidad ecuatoriana. También somos claros con las limitaciones: la UNEMI se evaluó con datos de prueba, falta la prueba con usuarios y el modelo prioriza, pero no reemplaza el criterio de bienestar. Ambas validaciones pendientes ya tienen su procedimiento.

### 20. Conclusiones · Víctor

Cerramos con una conclusión por objetivo. Las señales del abandono ya existen en los sistemas académicos y de ellas salieron los requerimientos. El modelo se sostuvo en periodos que no vio. El sistema funciona de punta a punta y su operación está automatizada. Y la evaluación cumple los criterios fijados al inicio. En síntesis, es viable que una universidad ecuatoriana pase de medir el abandono a anticiparlo con los datos que ya tiene. Gracias por su atención.
