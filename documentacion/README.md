<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../.github/assets/banner-dark.svg">
    <img src="../.github/assets/banner-light.svg" alt="UNEMI · VicMar: alerta temprana del abandono en estudiantes universitarios" width="100%">
  </picture>
</p>

<p align="center"><img src="../.github/assets/logo-vicmar.svg" alt="Isotipo de VicMar" width="72"></p>

# Documentación del proyecto

Todo lo que respalda el proyecto de titulación: los avances entregados, el generador que los produce a partir de los resultados del código, los manuales, las decisiones de diseño, la literatura revisada, los diagramas y las evidencias. Volver al [README principal](../README.md).

## Entregables

| Entregable | Archivos | Contenido |
|---|---|---|
| **Avance 1** | [PDF](avances/AVANCE1_MARLON_VICTOR.pdf) · [Word](avances/AVANCE1_MARLON_VICTOR.docx) · [formato oficial (PDF)](avances/Formato%20Oficial%20del%20Proyecto%20de%20titulaci%C3%B3n%20de%20UNEMI%20Marlon%20y%20Victor%20solo%20avance%201.pdf) | Introducción, propósito del caso y base conceptual |
| **Avance 2** | [PDF](avances/AVANCE2_MARLON_VICTOR.pdf) · [Word](avances/AVANCE2_MARLON_VICTOR.docx) · [registro de cambios](avances/Registro_cambios_Avance2.md) | Además: análisis del caso, requerimientos, metodología CRISP-DM fase por fase, diseño, UML, esquema estrella, conclusiones e innovación |
| **Manuales** | [Usuario](manuales/MANUAL_DE_USUARIO.md) · [Instalación](manuales/MANUAL_TECNICO_DE_INSTALACION.md) · [Pruebas de aceptación](manuales/GUIA_DE_PRUEBAS_DE_ACEPTACION.md) | Uso por rol, instalación en Windows y casos de prueba por historia de usuario |
| **Plan y estado** | [PLAN_Y_ESTADO_DEL_PROYECTO.md](PLAN_Y_ESTADO_DEL_PROYECTO.md) | Observaciones de las tutoras, dónde se atienden y pendientes |

## Cómo se genera el Avance 2

El documento se construye sobre una copia del Avance 1 (que conserva portada, certificados, estilos y numeración del formato oficial) y toma cada cifra de los artefactos del sistema: `ml/modelos/<INSTITUCION>/metricas.json`, `segmentacion.json`, `monitoreo.json`, `exploracion.json` y la evaluación de la consulta conversacional.

```bash
cd documentacion/generador_documentos
python construir_avance2.py --base ../avances/AVANCE1_MARLON_VICTOR.docx --salida ../avances/AVANCE2_MARLON_VICTOR.docx
python docx_a_pdf.py ../avances/AVANCE2_MARLON_VICTOR.docx ../avances/AVANCE2_MARLON_VICTOR.pdf   # LibreOffice; en Windows: _docx_a_pdf.ps1
python _verificar_coherencia.py      # citas ↔ referencias, cifras ↔ artefactos, páginas mínimas, numeración
```

| Archivo | Función |
|---|---|
| `construir_avance2.py` | Vacía el cuerpo de la copia, inserta títulos, párrafos, tablas y figuras con los estilos del formato y actualiza resumen, abstract y la ficha del anexo académico |
| `contenido_avance2.py` y `_c1_…_c4_*.py` | Contenido por capítulo; numera figuras y tablas en orden y falla si una queda sin citar |
| `_datos.py` | Lee los artefactos del sistema y da formato a las cifras (coma decimal) |
| `diagramas_svg.py`, `figuras_codigo.py` | Diagramas de actividades, estados, casos de uso, flujo y esquema estrella; imágenes del código |
| `_build_manuales.py` | Convierte los manuales `.md` en `.docx` con portada e índice |

## Resultados del modelo

Las mismas figuras para las dos instituciones; se generan en el paso `reportes` del orquestador (`python -m scripts.pipeline --solo reportes`).

| | UNEMI_PRUEBAS · datos sintéticos | OULAD_UK · datos reales |
|---|:---:|:---:|
| **Exploración** | <img src="figuras/UNEMI_PRUEBAS_exploracion.png" width="100%" alt="Exploración UNEMI_PRUEBAS"> | <img src="figuras/OULAD_UK_exploracion.png" width="100%" alt="Exploración OULAD_UK"> |
| **Comparación de algoritmos** | <img src="figuras/UNEMI_PRUEBAS_comparacion_cv.png" width="100%" alt="Comparación UNEMI_PRUEBAS"> | <img src="figuras/OULAD_UK_comparacion_cv.png" width="100%" alt="Comparación OULAD_UK"> |
| **ROC y precisión-recall** | <img src="figuras/UNEMI_PRUEBAS_roc_pr.png" width="100%" alt="ROC UNEMI_PRUEBAS"> | <img src="figuras/OULAD_UK_roc_pr.png" width="100%" alt="ROC OULAD_UK"> |
| **Calibración** | <img src="figuras/UNEMI_PRUEBAS_calibracion.png" width="100%" alt="Calibración UNEMI_PRUEBAS"> | <img src="figuras/OULAD_UK_calibracion.png" width="100%" alt="Calibración OULAD_UK"> |
| **Matriz de confusión** | <img src="figuras/UNEMI_PRUEBAS_matriz_confusion.png" width="100%" alt="Confusión UNEMI_PRUEBAS"> | <img src="figuras/OULAD_UK_matriz_confusion.png" width="100%" alt="Confusión OULAD_UK"> |
| **Curva de ganancia** | <img src="figuras/UNEMI_PRUEBAS_ganancia.png" width="100%" alt="Ganancia UNEMI_PRUEBAS"> | <img src="figuras/OULAD_UK_ganancia.png" width="100%" alt="Ganancia OULAD_UK"> |
| **Importancia por permutación** | <img src="figuras/UNEMI_PRUEBAS_importancia.png" width="100%" alt="Importancia UNEMI_PRUEBAS"> | <img src="figuras/OULAD_UK_importancia.png" width="100%" alt="Importancia OULAD_UK"> |
| **Equidad por subgrupo** | <img src="figuras/UNEMI_PRUEBAS_equidad.png" width="100%" alt="Equidad UNEMI_PRUEBAS"> | <img src="figuras/OULAD_UK_equidad.png" width="100%" alt="Equidad OULAD_UK"> |
| **Selección de k** | <img src="figuras/UNEMI_PRUEBAS_segmentacion_k.png" width="100%" alt="Selección de k UNEMI_PRUEBAS"> | <img src="figuras/OULAD_UK_segmentacion_k.png" width="100%" alt="Selección de k OULAD_UK"> |

La lectura de estas cifras está en [`tecnica/PREDICCION_ABANDONO.md`](tecnica/PREDICCION_ABANDONO.md) y en la sección 3.1.6 del Avance 2.

## Diagramas

<table>
<tr>
<td width="33%" align="center"><a href="diagramas/av2_casos_uso.png"><img src="diagramas/av2_casos_uso.png" alt="Casos de uso"></a><br/><sub><b>Casos de uso</b></sub></td>
<td width="33%" align="center"><a href="diagramas/av2_arquitectura.png"><img src="diagramas/av2_arquitectura.png" alt="Arquitectura"></a><br/><sub><b>Arquitectura</b></sub></td>
<td width="33%" align="center"><a href="diagramas/av2_modelo_estrella.png"><img src="diagramas/av2_modelo_estrella.png" alt="Esquema estrella"></a><br/><sub><b>Esquema estrella</b></sub></td>
</tr>
<tr>
<td align="center"><a href="diagramas/av2_secuencia_consulta.png"><img src="diagramas/av2_secuencia_consulta.png" alt="Secuencia de la consulta certificada"></a><br/><sub><b>Secuencia: consulta certificada</b></sub></td>
<td align="center"><a href="diagramas/av2_secuencia_consulta_ia.png"><img src="diagramas/av2_secuencia_consulta_ia.png" alt="Secuencia de la consulta generada"></a><br/><sub><b>Secuencia: consulta generada con IA</b></sub></td>
<td align="center"><a href="diagramas/av2_secuencia_ficha.png"><img src="diagramas/av2_secuencia_ficha.png" alt="Secuencia de la ficha"></a><br/><sub><b>Secuencia: ficha del estudiante</b></sub></td>
</tr>
<tr>
<td align="center"><a href="diagramas/av2_colaboracion.png"><img src="diagramas/av2_colaboracion.png" alt="Colaboración"></a><br/><sub><b>Colaboración</b></sub></td>
<td align="center"><a href="diagramas/av2_estados.png"><img src="diagramas/av2_estados.png" alt="Estados"></a><br/><sub><b>Estados de la alerta</b></sub></td>
<td align="center"><a href="diagramas/av2_flujo_trabajo.png"><img src="diagramas/av2_flujo_trabajo.png" alt="Flujo de trabajo"></a><br/><sub><b>Flujo de trabajo</b></sub></td>
</tr>
<tr>
<td align="center"><a href="diagramas/av2_actividad_etl.png"><img src="diagramas/av2_actividad_etl.png" alt="Actividades del ETL"></a><br/><sub><b>Actividades: ETL</b></sub></td>
<td align="center"><a href="diagramas/av2_actividad_modelo.png"><img src="diagramas/av2_actividad_modelo.png" alt="Actividades del modelo"></a><br/><sub><b>Actividades: modelo</b></sub></td>
<td align="center"><a href="diagramas/av2_despliegue.png"><img src="diagramas/av2_despliegue.png" alt="Despliegue"></a><br/><sub><b>Despliegue</b></sub></td>
</tr>
</table>

Las fuentes están en [`diagramas/fuentes/`](diagramas/fuentes/): PlantUML (`.puml`) para secuencia, colaboración y despliegue; la arquitectura en HTML; el resto se genera como SVG con `generador_documentos/diagramas_svg.py`. Su descripción paso a paso está en la sección 3.2.3 del Avance 2.

## Decisiones de diseño

Cada decisión compara alternativas con una matriz ponderada, un análisis de sensibilidad (±20 % en cada peso) y evidencia. Las matrices completas están en [`decisiones/Matriz_decisiones.xlsx`](decisiones/Matriz_decisiones.xlsx).

| ADR | Decisión | Elegida |
|---|---|---|
| [ADR-000](decisiones/ADR-000-estructura-del-repositorio.md) | Estructura del repositorio | Repositorio único organizado por capas |
| [ADR-001](decisiones/adr/ADR-001-lenguaje_de_programacion_del_backend.md) | Lenguaje del backend | Python |
| [ADR-002](decisiones/adr/ADR-002-framework_del_backend.md) | Framework del backend | FastAPI |
| [ADR-003](decisiones/adr/ADR-003-framework_del_frontend.md) | Framework del frontend | React |
| [ADR-004](decisiones/adr/ADR-004-motor_del_almacen_de_datos.md) | Motor del almacén de datos | SQL Server |
| [ADR-005](decisiones/adr/ADR-005-algoritmo_del_modelo_predictivo_de_aband.md) | Algoritmo del modelo predictivo | LightGBM, elegido por validación cruzada entre cuatro candidatos |
| [ADR-006](decisiones/adr/ADR-006-estilo_de_arquitectura_del_sistema.md) | Estilo de arquitectura | Cliente-servidor desacoplado con backend en capas |

## Documentación técnica

| Documento | Contenido |
|---|---|
| [Predicción del abandono](tecnica/PREDICCION_ABANDONO.md) | Datos, variables, validación, calibración, resultados y limitaciones |
| [Benchmarking institucional](tecnica/BENCHMARKING_INSTITUCIONAL.md) | Referentes externos y segmentación de carreras |
| [Base de datos de prueba](tecnica/BASE_DE_DATOS_DE_PRUEBAS.md) | Bases del servidor, simulador sintético y cuentas de mínimo privilegio |
| [Diccionario de datos](tecnica/DICCIONARIO_DE_DATOS.md) | Generado desde el script del almacén (`crear_almacen_academico.sql`) |

## Evidencias, literatura y otras carpetas

| Carpeta | Contenido |
|---|---|
| [`evidencias/`](evidencias/) | Evaluación de la consulta conversacional sobre la réplica del almacén y latencias |
| [`capturas/`](capturas/) | Capturas de la interfaz (escritorio, móvil, tema oscuro, OULAD, administración y API) |
| [`literatura/`](literatura/) | [`trabajos_previos.md`](literatura/trabajos_previos.md), referencias en RIS y registros de cada búsqueda en Scopus; los PDF no se redistribuyen |
| [`matrices/`](matrices/) | Matrices metodológicas del Avance 1 |
| [`presentaciones/`](presentaciones/) | Presentación y guion del Avance 1 |
| [`plantillas_unemi/`](plantillas_unemi/) | Formato oficial y reglamento de titulación de la UNEMI |
