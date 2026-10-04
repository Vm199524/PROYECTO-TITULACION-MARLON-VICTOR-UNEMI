<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../.github/assets/banner-dark.svg">
    <img src="../.github/assets/banner-light.svg" alt="UNEMI · VicMar Data AI" width="100%">
  </picture>
</p>

# Documentación del proyecto

Todo lo que respalda el proyecto de titulación: los avances entregados, el generador que los produce a partir del código, las decisiones de diseño, la literatura revisada, los diagramas y los resultados del modelo. Volver al [README principal](../README.md).

## Entregables

| Entregable | Archivos | Nota |
|---|---|---|
| **Avance 1** | [PDF](avances/AVANCE1_MARLON_VICTOR.pdf) · [Word](avances/AVANCE1_MARLON_VICTOR.docx) · [formato oficial (PDF)](avances/Formato%20Oficial%20del%20Proyecto%20de%20titulaci%C3%B3n%20de%20UNEMI%20Marlon%20y%20Victor%20solo%20avance%201.pdf) | Introducción, propósito del caso y base conceptual |
| **Avance 2** | [PDF](avances/Avance_2_VicMar_Data_AI.pdf) · [Word](avances/Avance_2_VicMar_Data_AI.docx) · [registro de cambios](avances/Registro_cambios_Avance2.md) | Además: análisis del caso, requerimientos, metodología, diseño y desarrollo; generado por [`generador_documentos/`](generador_documentos/) |
| **Plan y estado** | [PLAN_Y_ESTADO_DEL_PROYECTO.md](PLAN_Y_ESTADO_DEL_PROYECTO.md) | Exigencias de las tutoras, avance y pendientes |
| **Auditoría** | [AUDITORIA_2026-10-03.md](auditoria/AUDITORIA_2026-10-03.md) | Inventario, riesgos y acciones de la organización del repositorio |

## Resultados del modelo

Las mismas figuras para las dos instituciones: a la izquierda la real (OULAD_UK) y a la derecha la sintética (UNEMI_PRUEBAS). Se generan con `python -m ml.reporte_validacion --empresa <INSTITUCION>`.

| | OULAD_UK · datos reales | UNEMI_PRUEBAS · datos sintéticos |
|---|:---:|:---:|
| **ROC y precisión-recall** | <img src="figuras/OULAD_UK_roc_pr.png" alt="ROC y PR en OULAD_UK" width="100%"> | <img src="figuras/UNEMI_PRUEBAS_roc_pr.png" alt="ROC y PR en UNEMI_PRUEBAS" width="100%"> |
| **Importancia por permutación** | <img src="figuras/OULAD_UK_importancia.png" alt="Importancia en OULAD_UK" width="100%"> | <img src="figuras/UNEMI_PRUEBAS_importancia.png" alt="Importancia en UNEMI_PRUEBAS" width="100%"> |
| **Matriz de confusión** | <img src="figuras/OULAD_UK_matriz_confusion.png" alt="Matriz de confusión en OULAD_UK" width="100%"> | <img src="figuras/UNEMI_PRUEBAS_matriz_confusion.png" alt="Matriz de confusión en UNEMI_PRUEBAS" width="100%"> |
| **Comparación de algoritmos** | <img src="figuras/OULAD_UK_comparacion_cv.png" alt="Comparación de algoritmos en OULAD_UK" width="100%"> | <img src="figuras/UNEMI_PRUEBAS_comparacion_cv.png" alt="Comparación de algoritmos en UNEMI_PRUEBAS" width="100%"> |
| **Selección de k (segmentación)** | <img src="figuras/OULAD_UK_clustering_k.png" alt="Selección de k en OULAD_UK" width="100%"> | <img src="figuras/UNEMI_PRUEBAS_clustering_k.png" alt="Selección de k en UNEMI_PRUEBAS" width="100%"> |

La lectura de estas cifras, incluida la diferencia entre datos reales y sintéticos, está en [`tecnica/PREDICCION_ABANDONO.md`](tecnica/PREDICCION_ABANDONO.md).

## Diagramas

<table>
<tr>
<td width="33%" align="center"><a href="diagramas/av2_casos_uso.png"><img src="../.github/assets/galeria/av2_casos_uso.png" alt="Casos de uso"></a><br/><sub><b>Casos de uso</b></sub></td>
<td width="33%" align="center"><a href="diagramas/av2_arquitectura.png"><img src="../.github/assets/galeria/av2_arquitectura.png" alt="Arquitectura"></a><br/><sub><b>Arquitectura</b></sub></td>
<td width="33%" align="center"><a href="diagramas/av2_modelo_dimensional.png"><img src="../.github/assets/galeria/av2_modelo_dimensional.png" alt="Modelo dimensional"></a><br/><sub><b>Modelo dimensional</b></sub></td>
</tr>
<tr>
<td align="center"><a href="diagramas/av2_secuencia_nl2sql.png"><img src="../.github/assets/galeria/av2_secuencia_nl2sql.png" alt="Secuencia NL2SQL"></a><br/><sub><b>Secuencia: lenguaje natural</b></sub></td>
<td align="center"><a href="diagramas/av2_secuencia_lotes.png"><img src="../.github/assets/galeria/av2_secuencia_lotes.png" alt="Secuencia por lotes"></a><br/><sub><b>Secuencia: procesos por lotes</b></sub></td>
<td align="center"><a href="diagramas/av2_colaboracion.png"><img src="../.github/assets/galeria/av2_colaboracion.png" alt="Colaboración"></a><br/><sub><b>Colaboración</b></sub></td>
</tr>
<tr>
<td align="center"><a href="diagramas/av2_actividad_etl.png"><img src="../.github/assets/galeria/av2_actividad_etl.png" alt="Actividades del ETL"></a><br/><sub><b>Actividades: ETL</b></sub></td>
<td align="center"><a href="diagramas/av2_actividad_modelo.png"><img src="../.github/assets/galeria/av2_actividad_modelo.png" alt="Actividades del modelo"></a><br/><sub><b>Actividades: modelo</b></sub></td>
<td align="center"><a href="diagramas/av2_estados.png"><img src="../.github/assets/galeria/av2_estados.png" alt="Estados"></a><br/><sub><b>Estados de la matrícula</b></sub></td>
</tr>
</table>

Cada diagrama tiene su fuente Mermaid (`.mmd`) junto al PNG, y su descripción está en el Avance 2.

## Decisiones de diseño

Cada decisión compara tres alternativas con una matriz ponderada, un análisis de sensibilidad (±20 % en los pesos) y evidencia académica. Las matrices completas están en [`decisiones/Matriz_decisiones.xlsx`](decisiones/Matriz_decisiones.xlsx).

| ADR | Decisión | Elegida |
|---|---|---|
| [ADR-000](decisiones/ADR-000-estructura-del-repositorio.md) | Estructura del repositorio | Organización por capas |
| [ADR-001](decisiones/adr/ADR-001-lenguaje_de_programacion_del_backend.md) | Lenguaje del backend | Python |
| [ADR-002](decisiones/adr/ADR-002-framework_del_backend.md) | Framework del backend | FastAPI |
| [ADR-003](decisiones/adr/ADR-003-framework_del_frontend.md) | Framework del frontend | React |
| [ADR-004](decisiones/adr/ADR-004-motor_del_almacen_de_datos.md) | Motor del almacén de datos | SQL Server |
| [ADR-005](decisiones/adr/ADR-005-algoritmo_del_modelo_predictivo_de_aband.md) | Algoritmo del modelo predictivo | Random Forest |
| [ADR-006](decisiones/adr/ADR-006-estilo_de_arquitectura_del_sistema.md) | Estilo de arquitectura | Cliente-servidor desacoplado |

La arquitectura implementada se contrasta con el código en [`decisiones/arquitectura_detectada.md`](decisiones/arquitectura_detectada.md), con las reglas de [`decisiones/arquitectura_reglas.json`](decisiones/arquitectura_reglas.json).

## Documentación técnica

| Documento | Contenido |
|---|---|
| [Predicción del abandono](tecnica/PREDICCION_ABANDONO.md) | Datos, variables, validación y resultados del modelo |
| [Benchmarking institucional](tecnica/BENCHMARKING_INSTITUCIONAL.md) | Referentes externos con DOI y segmentación de carreras |
| [Base de datos de pruebas](tecnica/BASE_DE_DATOS_DE_PRUEBAS.md) | Bases sintéticas, anonimización y reconstrucción |
| [Diccionario de datos](tecnica/DICCIONARIO_DE_DATOS.md) | Generado desde el esquema real del almacén |
| [Manual de instalación](tecnica/MANUAL_INSTALACION.md) | Instalación paso a paso en Windows |

## Literatura

| Archivo | Contenido |
|---|---|
| [`trabajos_previos.md`](literatura/trabajos_previos.md) | Comparación crítica de los 13 trabajos previos frente al presente caso |
| [`Avance2_34_referencias_completas.ris`](literatura/Avance2_34_referencias_completas.ris) | Referencias del Avance 2, importables en Zotero o Mendeley |
| `busqueda*_scopus.ris` | Registros seleccionados de cada búsqueda en Scopus |

Los PDF de los artículos no se redistribuyen; cada referencia se cita por su DOI.

## Otras carpetas

| Carpeta | Contenido |
|---|---|
| [`generador_documentos/`](generador_documentos/) | Genera el Avance desde el formato oficial y verifica su coherencia con el código |
| [`matrices/`](matrices/) | Matrices metodológicas del Avance 1 |
| [`presentaciones/`](presentaciones/) | Presentaciones de los avances y guion |
| [`plantillas_unemi/`](plantillas_unemi/) | Formato oficial y reglamento de titulación de la UNEMI |
