# Registro de cambios — Avance 2

`Avance_2_VicMar_Data_AI.docx` se genera con `_build_avance2.py` a partir del documento
oficial del Avance 1, **que no se modifica**. Este registro lista todo lo que la copia cambia
respecto de ese documento, para que los autores lo revisen antes de entregarlo.

## Secciones nuevas (retroalimentación de las tutoras)

- **2. Análisis del caso / 2.1 Requerimientos:** alternativas, actores y persona, historias
  de usuario (HU-01 a HU-10), requerimientos funcionales por pieza (RF-01 a RF-16),
  requerimientos no funcionales con protección de datos (LOPDP), métricas de calidad con meta
  y resultado, matriz de trazabilidad y plan de validación con usuarios.
- **3. Diseño y desarrollo del trabajo práctico:**
  - 3.1 Metodología: seis fases de CRISP-DM con entregables e iteraciones.
  - 3.2 Diseño: arquitectura y siete diagramas UML (casos de uso, secuencia de la consulta en
    lenguaje natural, secuencia de lotes, colaboración, actividades del ETL, actividades del
    modelo, estados), esquema estrella con diccionario de datos generado del esquema real,
    y recursos.
  - 3.3 Desarrollo: tecnologías con versiones, código del backend y del frontend extraído de
    los archivos al generar, y resultados reales de validación con su discusión.

## Cambios en la sección 1 (coherencia con el código)

| Dónde | Antes | Ahora | Por qué |
|---|---|---|---|
| Resumen y Abstract | ROC-AUC de 0,9999 en validación temporal | ROC-AUC en datos de prueba y en OULAD (datos reales), segmentación con p de Kruskal-Wallis y exactitud del NL2SQL | El 0,9999 venía de un modelo que usaba la asistencia del mismo periodo del retiro; el modelo actual predice el periodo siguiente |
| 1.2 Alcance funcional | «se valida sobre datos de prueba de una institución ecuatoriana» | Se añade el contraste con OULAD (Kuzilek et al., 2017) como segunda institución | Es lo que el sistema hace ahora |
| 1.2 Criterio (d) | Sin forma de medirlo | Se mide con 40 preguntas de referencia (exactitud por ejecución) y una prueba con usuarios | El criterio debe ser verificable |
| 1.3, párrafo de Villar y Andrade | «SMOTE, la misma aplicada en el presente trabajo» | «SMOTE, que el presente trabajo compara con la ponderación de clases» | El código compara ambas técnicas; cuál gana depende de la institución |
| 1.3, asignaturas | Nombres genéricos («Bases de Datos», «Seguridad de la Información») | Nombres de la malla vigente de TI de la UNEMI | Coherencia con la malla oficial |
| Títulos Referencias y Anexos | Numeración automática incoherente («2. Referencias», «6. Anexos») | Sin numeración automática; secciones 2 y 3 numeradas a mano como «1. Introducción» | Evitar numeración rota |
| Referencias | 32 | 35: + Kuzilek et al. (2017), Asamblea Nacional del Ecuador (2021, LOPDP) y Hassan et al. (2025) | Nuevas citas de las secciones 2 y 3 |
| 1.3, comparación crítica | Comparación solo en prosa | Dos tablas que contrastan los 13 trabajos previos con el caso (problema, datos, validación, tecnologías, arquitectura, limitación y aporte), más un párrafo con lo que muestran | Observación de la tutora: falta una tabla comparativa explícita |

## Cambios del 3 de octubre de 2026

- **3.2 Diseño:** comparación de tres estilos arquitectónicos (monolito en capas, cliente-servidor desacoplado y
  microservicios) con seis escenarios de calidad, matriz ponderada, análisis de sensibilidad y verificación automática
  de la arquitectura en el código (`documentacion/decisiones/DT-06_arquitectura.json` y `arquitectura_reglas.json`).
- **3.3 Desarrollo:** cinco decisiones tecnológicas con tres opciones cada una (lenguaje, framework del backend,
  framework del frontend, motor del almacén y algoritmo), cada puntaje con su fuente
  (`documentacion/decisiones/DT-01` a `DT-05` y sus ADR en `decisiones/adr/`).
- **Verificador:** `_verificar_coherencia.py` falla ahora si «Referencias» o «Anexos» llevan número.

## Cambios del 5 de octubre de 2026 (instrucciones del Avance 2)

| Dónde | Cambio | Por qué |
|---|---|---|
| Portada, ficha, certificados y Anexo | Título oficial: «Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional» | Es el título que figura en las instrucciones del Avance 2 |
| Ficha de registro | El resumen y el abstract de la ficha son ahora los mismos del documento (antes conservaba el ROC-AUC de 0,9999 del Avance 1) | Coherencia de cifras |
| 1.1 Descripción | Se numera el título | Formato oficial |
| 4. Conclusiones y recomendaciones | Sección nueva: una conclusión por objetivo específico, una general, análisis de innovación y recomendaciones; cifras leídas de los artefactos del sistema | Las instrucciones piden conclusiones preliminares con análisis de innovación |
| 5. Referencias, 6. Anexos, 7. Anexo de información académica | Numeración del formato oficial de titulación (el verificador la exige) | Observación de la tutora sobre la numeración |
| Anexo de información académica | Se reemplazan tres filas que el formato base traía de otro proyecto (flota de vehículos, PostgreSQL, microservicios, modelo en cascada) por el aporte real de cada asignatura | Solo debe figurar el trabajo de los autores |
| 3.3 Demostración del prototipo | Se insertan ocho capturas de `documentacion/capturas/` | Demo funcionando |

Pendiente: el PDF se regenera con `_docx_a_pdf.ps1` (Word en Windows), que además actualiza la tabla de contenido. Después se ejecuta `_verificar_coherencia.py`.

## Atención a las observaciones de las tutoras

| Observación | Dónde se atiende | Estado |
|---|---|---|
| La numeración de Referencias (2.) y Anexos (6.) no corresponde al formato | Títulos sin numeración automática; control en el verificador | Atendida |
| Falta una tabla comparativa explícita de los ≥10 estudios previos frente al caso | 1.3, dos tablas con los 13 estudios y la fila «Presente trabajo» | Atendida (11 leídos completos; 2 desde su resumen verificado, porque el editor exige verificación humana) |
| Derivar RF/RNF de las cuatro piezas | 2.1: RF-01 a RF-16 por pieza y RNF-01 a RNF-11 | Atendida |
| Historias de usuario para la autoridad académica sin perfil técnico | 2.1: HU-01 a HU-10 con criterios de aceptación | Atendida |
| Requisitos de protección de datos estudiantiles | 2.1: RNF-02 a RNF-05 (LOPDP) | Atendida |
| Métricas de calidad (AUC, recall, exactitud NL2SQL) | 2.1: tabla de métricas con meta y resultado | Atendida |
| Documentar cada fase de CRISP-DM | 3.1: seis fases con entregables y control de calidad | Atendida |
| Esquema estrella con diccionario de datos | 3.2: modelo dimensional y diccionario generado del esquema real | Atendida |
| UML: secuencia de la consulta en lenguaje natural y actividades del ETL | 3.2: siete diagramas | Atendida |
| Código del modelo y del backend con resultados reales de validación cruzada y temporal | 3.3: fragmentos extraídos del código y tablas de resultados | Atendida |
| Demo funcionando | 3.3: recorrido descrito y ocho capturas del prototipo; falta el video | **Parcial** (falta el video) |

## Pendientes para los autores

- Ejecutar la prueba con 3 a 5 usuarios sin perfil técnico (protocolo en la sección 2.1) y
  reportar sus resultados en el siguiente avance.
- Completar la tabla de actividades del Anexo (fechas e interacciones con las tutoras) y los
  enlaces de los videos.
- Revisar la redacción de la discusión de resultados (sección 3.3): el criterio (a) no se
  cumple con datos reales y el documento lo dice explícitamente.
- Revisar en la sección 1.3 las frases sobre trabajos previos que la lectura completa matizó (detalle en
  `documentacion/PLAN_Y_ESTADO_DEL_PROYECTO.md`).
