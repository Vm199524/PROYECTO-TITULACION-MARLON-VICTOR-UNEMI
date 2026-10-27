# Avance 3 — Requisitos y control de cumplimiento

**Entrega:** 29 de octubre de 2026 (Drive del grupo y PDF en el aula virtual). **Regla:** el Avance 3 continúa los Avances 1 y 2; lo aprobado (título, objetivos, enfoque) no se cambia sin autorización de la tutora.

Estado: ✔ cumplido · ◐ en curso · ✘ pendiente · 👤 lo hacen los autores

## 1. Máster Mirella Peralta — entregables en el Drive

| # | Entregable | Carpeta | Estado |
|---|---|---|---|
| 1 | Documento finalizado TRABAJO FINAL (PDF y Word), con integrantes y enlace del Drive en la primera página | `01_TRABAJO_FINAL` | ✘ |
| 2 | Presentación del trabajo, una por estudiante | `02_PRESENTACIONES` | ✘ |
| 3 | Video de la explicación práctica (≈15 min entre los dos) | `03_VIDEO_EXPLICACION_PRACTICA` | 👤 (guía: ✘) |
| 4 | Trabajo práctico desarrollado (enlace a GitHub y ZIP sin secretos) | `04_TRABAJO_PRACTICO` | ✘ |
| 5 | Declaración de autoría (plantilla oficial) | `05_DECLARACION_AUTORIA` | ✘ (cédulas por confirmar) |
| 6 | Anexo de interacción con IA | `06_ANEXO_INTERACCION_IA` | ✘ |
| 7 | Anexo de interacción con las docentes (fotografías) | `07_ANEXO_INTERACCION_DOCENTES` | ✘ |
| 8 | Cédula de cada integrante | `08_CEDULAS` | 👤 |
| 9 | Fotografía vigente de cada integrante | `09_FOTOGRAFIAS` | 👤 |

## 2. Máster Mirella Peralta — rúbrica del documento

| Criterio | Dónde se cumple | Estado |
|---|---|---|
| Simplifica la investigación y describe la importancia del tema | 1.1 Descripción | ✔ (Avance 2) |
| Propósito del caso según objetivos y problemática | 1.2 Propósito | ✔ (Avance 2) |
| Base conceptual y comparación de trabajos similares | 1.3 (ampliada con antecedentes por ámbito) | ◐ |
| Problemática y alternativas tecnológicas con requerimientos | 2.1 | ✔ (Avance 2) |
| Métodos y técnicas aplicados | 3.1 | ◐ (explicitar) |
| Arquitectura desde el diseño | 3.2.1 | ✔ |
| Diagrama de flujo de trabajo y solución tecnológica | 3.2.4 | ✔ |
| Recursos: equipos, software, materiales | 3.2.7 | ✔ |
| **Análisis de tecnologías empleadas y tendencias actuales** | 3.2.8 (nueva) | ✘ |
| **Conclusiones que responden a los objetivos, objetivas y con datos** | 4.1 (final) | ✘ |
| **Recomendaciones de continuidad** | 4.3 (final) | ✘ |

### Recomendaciones de la tutora al trabajo

| Recomendación | Cómo se atiende | Estado |
|---|---|---|
| Validar con datos reales anonimizados de una carrera | OULAD (real) y UNEMI_PRUEBAS; solicitud formal a las tutoras como anexo de constancia | ◐ |
| Reportar AUC y recall por periodo | `ml/evaluacion_grupos.py`: `por_periodo`, `por_carrera` y origen móvil en `metricas.json`; tabla en el trabajo final | ✔ |
| Documento de gobierno de datos (LOPDP) | `documentacion/gobierno_datos/GOBIERNO_DE_DATOS.md` (anexo C del trabajo final), complementado por `documentacion/tecnica/GOBIERNO_DE_DATOS_LOPDP.md` | ✔ |
| MLflow | `mlops/registro_mlflow.py`: corrida por entrenamiento y por monitoreo | ✔ |
| Evidently AI (deriva/PSI) | `mlops/deriva.py`: `deriva.json` junto al PSI propio | ✔ |
| SHAP | Ya implementado (factores por estudiante) | ✔ |
| Great Expectations | `mlops/calidad_datos.py`: `calidad_datos.json` | ✔ |
| Metabase como alternativa de consulta | `despliegue/metabase/` y vistas `bi.*` con la cuenta `metabase_lector` | ✔ |

## 3. Máster Gabriela Espinoza — Tarea 3 (`Apellido_Nombre_Tarea3_EstadoDelArte.pdf`)

| # | Elemento | Estado |
|---|---|---|
| 1 | Portada institucional | ✘ |
| 2 | Título aprobado | ✔ |
| 3 | Problema, **preguntas**, objetivos y justificación corregidos | ◐ (faltan las preguntas de investigación) |
| 4 | Matriz de congruencia actualizada | ◐ (existe en PDF; integrarla) |
| 5 | Antecedentes internacionales | ✔ (13 trabajos previos) |
| 6 | Antecedentes nacionales | ✘ (búsqueda en curso) |
| 7 | Antecedentes locales, cuando existan | ✘ (búsqueda en curso) |
| 8 | Estado del arte por ejes | ◐ (1.3.2–1.3.5) |
| 9 | Contexto tecnológico, institucional o territorial | ✘ |
| 10 | Bases teóricas | ✔ (Tinto; Bean y Metzner) |
| 11 | Definición de términos | ✘ |
| 12 | Comparación crítica de autores, métodos y resultados | ✔ (Tabla 3) |
| 13 | Vacío de investigación | ◐ (explicitar) |
| 14 | Metodología actualizada | ✔ |
| 15 | Evidencia del gestor bibliográfico (Zotero) | ✘ |
| 16 | Citas y referencias APA 7 | ◐ (verificador) |
| 17 | Enlace de la carpeta digital | 👤 |

**Rúbrica:** estructura de artículo científico (título, resumen, introducción, metodología, resultados y conclusiones); análisis y aplicación de la arquitectura justificada; APA 7, originalidad y uso adecuado de IA (la IA solo en el anexo).

## 4. Máster Gabriela Espinoza — Tarea 4 (después del 29/10)
Portada, autores, título, tutor, resumen de correcciones, certificado oficial de similitud (porcentaje, fecha, sistema, firma), capturas de coincidencias, declaración de que es la versión entregada y enlace de la carpeta. El análisis se hace sobre el documento completo.

## 5. Lo que hacen los autores
- Enviar la solicitud de datos a las tutoras (oficio y correo preparados).
- Pegar el enlace del Drive en la primera página.
- Grabar el video con la guía.
- Confirmar el número de cédula de Marlon (aparece 0942783457 y 0928476464 en documentos distintos).
- Subir cédulas y fotografías.
- Firmar la declaración de autoría.
- Subir todo al Drive y el PDF al aula virtual.
