# Registro de cambios del Avance 2

`AVANCE2_MARLON_VICTOR.docx` se genera con `generador_documentos/construir_avance2.py` sobre una copia del Word del
Avance 1 (con las correcciones de los autores), que **no se modifica**. La copia conserva portada, certificados,
preliminares, estilos, encabezados y numeración del formato oficial, y reemplaza el cuerpo. Este registro resume lo que
cambia respecto del Avance 1 para que los autores lo revisen antes de entregarlo.

**Versión:** 7 de octubre de 2026 · 85 páginas · 34 figuras · 35 tablas · 28 referencias.

## Observaciones de la tutoría atendidas

| Observación | Dónde |
|---|---|
| La numeración de Referencias y Anexos no seguía el formato | Capítulos **4. Conclusiones y recomendaciones**, **5. Referencias**, **6. Anexos** y **7. Anexo de información académica**, sin numeración automática; lo controla `_verificar_coherencia.py` |
| Faltaba una tabla comparativa de al menos 10 estudios | 1.3.6: 14 trabajos previos comparados por problema, técnica, datos, validación, resultado y relación con el caso |
| RF y RNF derivados de las cuatro piezas | 2.1.5 (RF-01 a RF-18, agrupados en datos, modelo, segmentación, consulta, panel, seguridad y administración) y 2.1.6 (RNF-01 a RNF-10) |
| Historias de usuario para la autoridad sin perfil técnico | 2.1.4: HU-01 a HU-10 con criterios de aceptación |
| Requisitos de protección de datos estudiantiles | 2.1.7: requisitos de la LOPDP (minimización, aislamiento, confidencialidad, transferencia internacional, evaluación de impacto) y el control que los cumple |
| Métricas de calidad (AUC, recall, exactitud de la consulta) | 2.1.8 (metas) y 3.1.6 (resultados) |
| Cada fase de CRISP-DM documentada | 3.1.2 a 3.1.7, una sección por fase, con entregables |
| Esquema estrella con diccionario de datos | 3.2.5: modelo entidad-relación, diccionario con tipos, precisión y nulidad, dimensiones y vistas |
| UML: secuencia de la consulta y actividades del ETL | 3.2.3: casos de uso, tres secuencias, colaboración, estados y actividades del ETL y del modelo; 3.2.4: flujo de trabajo |
| Código del modelo y del backend con resultados reales | 3.1.5 a 3.1.7: código del entrenamiento, la API, el motor de consulta, el validador y una vista; validación cruzada, temporal y prospectiva |
| Demo funcionando | 3.1.7 (seis capturas del sistema) y Anexo C (videos) |

## Contenido nuevo o reescrito

- **1. Introducción:** descripción con causas y efectos, justificación y beneficiarios; propósito con objetivo general
  y cuatro objetivos específicos; delimitación (qué, cómo, para qué); base conceptual con supuestos epistemológicos,
  teorías del abandono, aprendizaje automático, segmentación y consulta conversacional.
- **2. Análisis del caso:** alternativas de solución, aportes de la literatura, actores y roles, historias de usuario,
  casos de uso, requerimientos, protección de datos y métricas de calidad.
- **3. Diseño y desarrollo:** CRISP-DM con análisis exploratorio de las dos instituciones, coeficientes del simulador
  sintético, calidad del ETL, comparación de cuatro modelos, calibración, umbrales por recall, equidad, segmentación
  con advertencia de circularidad, evaluación de la consulta conversacional, estrategia de pruebas con trazabilidad
  HU → RF → prueba, arquitectura comparada con sus alternativas, infraestructura y recursos.
- **4. Conclusiones:** una por objetivo específico, análisis de innovación y recomendaciones.
- **Resumen y abstract** reescritos (237 y 211 palabras) y ficha del anexo académico actualizada.

## Cambios de fondo respecto del Avance 1

| Antes (Avance 1) | Ahora (Avance 2) | Por qué |
|---|---|---|
| ROC-AUC de 0,9999 con una fila por estudiante y datos deterministas | Panel estudiante-periodo; ROC-AUC temporal de 0,829 (UNEMI_PRUEBAS) y 0,766 (OULAD, real) | El valor anterior venía de datos generados por reglas y de variables del mismo periodo del retiro |
| Una sola institución de prueba | UNEMI_PRUEBAS (sintética) y OULAD_UK (real anonimizada), aisladas en el motor | Comprobar que el sistema se transfiere a otra institución con datos reales |
| Algoritmo fijado de antemano | Cuatro candidatos comparados; LightGBM elegido por validación cruzada | La elección debe salir de la evidencia y repetirse en cada reentrenamiento |
| Consulta en lenguaje natural sin medición | 40 métricas certificadas, validador del árbol SQL, conjunto dorado de 60 preguntas y pruebas de ataque | El criterio de éxito debe ser verificable |

## Pendiente de los autores

- Enlaces de los videos del Anexo C.
- Tabla de actividades con la tutora en la declaración de autoría.
- Porcentaje real de Compilatio.
- Actualizar en Word la tabla de contenido y los índices si se edita el documento a mano.
