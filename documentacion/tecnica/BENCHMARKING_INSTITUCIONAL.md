# Benchmarking con enfoque en inteligencia institucional (Módulo 2)

Implementa el segundo work package pedido. Documenta fuentes, metodología,
limitaciones y proceso de actualización — para citar en el capítulo de
metodología de la tesis, igual que [PREDICCION_ABANDONO.md](PREDICCION_ABANDONO.md)
para el Módulo 1.

## 1. Identificación de fuentes externas

**Actualizado en el Avance 2 (25/09/2026).** Solo se cargan cifras publicadas en fuentes
académicas con DOI, verificadas en el texto completo del artículo (la tabla o el párrafo
exacto queda anotado en `definicion_indicador`). Las cifras que antes se tomaban de prensa
(Diario Expreso, citando a SENESCYT, ESPOL, Universidad de Guayaquil, UNESCO y Banco Mundial)
**se retiraron**: una nota periodística no es una fuente verificable para un trabajo de
titulación. El loader rechaza cualquier fila que las cite.

| Referente | Tasa de abandono | Qué mide exactamente | País / modalidad | Comparabilidad | Fuente |
|---|---|---|---|---|---|
| Universidad privada del Ecuador | 44,90 % | 484 abandonos de 1.078 admitidos o matriculados, 2014-2019 (Tabla 3) | Ecuador / mixta | ALTA | Núñez-Naranjo (2024), 10.3389/feduc.2024.1444534 |
| Institución politécnica de Portugal | 32,12 % | 1.421 de 4.424, abandono al término de la duración normal, cohortes 2008/09-2018/19 | Portugal / presencial | MEDIA | Realinho et al. (2022), 10.3390/data7110146 |
| The Open University | 31,16 % | 10.156 retiros de 32.593 matrículas módulo-presentación, 2013-2014 (medido sobre el dataset) | Reino Unido / distancia | BAJA | Kuzilek et al. (2017), 10.1038/sdata.2017.171 |
| Universidad de ciencias aplicadas de Finlandia | 24,38 % | 2.149 de 8.813 estudiantes con resultado final, 2015-2020 | Finlandia / no reportada | MEDIA | Vaarma y Li (2024), 10.1016/j.techsoc.2024.102474 |

Niveles de comparabilidad (Lepori y Bornmann, 2026, "comparar pares con pares"): ALTA =
mismo país y nivel; MEDIA = pregrado presencial o mixto en otro país; BAJA = otra
modalidad u otra unidad de medida. Gutierrez-Pachas et al. (2023) **no** se usa como
referente de tasa: su muestra está balanceada 50/50 por diseño.

Cifras oficiales de SENESCYT/SIAU o CACES se incorporarán solo cuando se verifiquen en el
portal oficial del organismo.

## 2. Dónde vive: `dim_institucion_externa` / `fact_benchmark_externo`

Patrón "indicator fact" (EAV acotado) en `CHAT`, deliberadamente separado
del modelo dimensional de matrícula (`fact_matriculas`): los indicadores
externos son heterogéneos, pocos, y de fuentes/años distintos — forzarlos al
mismo grano que las matrículas propias sería una mala decisión de diseño.
Ver `codigo_fuente/base_de_datos/crear_chat_academico.sql`.

Sin `SESSION_CONTEXT`: son datos públicos, no pertenecen a ninguna empresa
conectada — visibles siempre, a diferencia de `VIS_ALUMNO`.

## 3. Pipeline de integración

`codigo_fuente/backend/etl/etl_benchmarking.py` carga
`codigo_fuente/backend/etl/fuentes_externas/benchmark_educacion_superior_ecuador.csv` (el
dataset curado de la sección 1) al warehouse. Es un CSV versionado, no un
scraper en vivo — decisión deliberada:

- CACES/SENESCYT/CES no ofrecen una API estable; automatizar el scraping de
  un portal gubernamental que puede rediseñarse sin aviso sería frágil y
  quedaría desactualizado sin que nadie lo note.
- Un CSV versionado es **auditable**: cada fila declara su fuente y URL
  exactas (columnas `fuente`, `url_fuente`), así que cualquiera puede
  verificar de dónde salió cada cifra.

### Proceso de actualización (cuando un organismo publique un reporte nuevo)

1. Ubicar la cifra nueva en una fuente académica con DOI o en el portal oficial del
   organismo y anotar: institución, indicador, valor, año, definición exacta, país,
   modalidad, nivel de comparabilidad, fuente, DOI y URL.
2. Agregar una fila a
   `codigo_fuente/backend/etl/fuentes_externas/benchmark_educacion_superior_ecuador.csv`
   (o corregir una existente si el organismo revisó una cifra).
3. Correr `python -m etl.etl_benchmarking` (recarga completa, igual que
   `etl_academico.py`).

No hay cadencia fija porque estos organismos no publican en un calendario
predecible — CACES evalúa por ciclos plurianuales, SENESCYT publica reportes
cuando cierra cada período. Revisar manualmente antes de cada defensa de
tesis o entrega institucional.

## 4. Clustering institucional

`codigo_fuente/backend/ml/clustering_institucional.py` — K-Means, `k=3`, sobre 3
indicadores por carrera (`StandardScaler` antes, porque las escalas son muy
distintas): tasa de abandono histórica, rendimiento académico histórico, y
riesgo promedio actual (salida del modelo de
[PREDICCION_ABANDONO.md](PREDICCION_ABANDONO.md)).

**Interpretación explícita del requerimiento** (documentada porque es
ambigua): "clustering institucional" podría leerse como agrupar
universidades completas, o como segmentar unidades *dentro* de una
institución. Con solo 3-4 puntos de comparación externos reales (sección 1),
un K-Means entre universidades no es estadísticamente defendible — n
demasiado chico para que los clusters signifiquen algo. Lo que sí tiene
volumen real es segmentar las **carreras/facultades propias** (18 carreras
en los datos de prueba) por perfil de riesgo — es la lectura que aporta
inteligencia institucional accionable de verdad: qué programas necesitan
atención prioritaria.

Los clusters se etiquetan por el centroide de tasa de abandono (ascendente),
nunca por un id numérico arbitrario:
`Bajo riesgo / alto rendimiento` · `Estable` · `Atención prioritaria`.

## 5. Indicadores comparativos y exposición dual

Igual que el Módulo 1, panel + chat leen la **misma fuente**:

- `GET /api/ml/clusters-carrera` y `GET /api/benchmarking/comparativo`
  (dashboard, `InteligenciaInstitucionalCard.jsx`).
- `VIS_CLUSTER_CARRERA` / `VIS_BENCHMARK_EXTERNO` están en la lista blanca
  `VIS_*`, así que el motor NL2SQL las descubre solo — se le puede preguntar
  al chat "¿qué carreras necesitan atención prioritaria?" o "¿cómo se
  compara nuestra tasa de abandono con la del referente de Ecuador?" sin cambios
  adicionales en `main.py`.

## 6. Hallazgos y recomendaciones (sobre los datos de prueba)

Con los datos sintéticos de `UNEMI_PRUEBAS` (10,02 % de abandono histórico), la tasa propia
queda por debajo de los cuatro referentes publicados (24,4 % a 44,9 %). No es una
conclusión sobre UNEMI: la tasa base del dataset de prueba se fijó al generarlo. Con datos
reales, el mismo comparativo ubica a la institución frente a pares de comparabilidad
declarada, y el clustering de carreras indica qué programas priorizar.

**Recomendación estratégica** (aplicable con datos reales): priorizar la intervención en las
carreras del segmento "Atención prioritaria" y usar el comparativo como referencia de
urgencia frente a pares de comparabilidad ALTA, no como meta a igualar mecánicamente.

## 7. Limitaciones honestas

- Los referentes son **puntuales** (una cifra por estudio), no series temporales.
- Las definiciones de abandono difieren entre estudios (cohorte, matrícula-módulo,
  resultado final); por eso cada fila declara su definición y su comparabilidad.
- El clustering de UNEMI_PRUEBAS usa datos sintéticos; con datos reales, los centroides
  y las etiquetas cambiarán. En OULAD (7 módulos) la segmentación no es significativa.
- No hay integración con datos socioeconómicos de INEC; queda como extensión futura.
