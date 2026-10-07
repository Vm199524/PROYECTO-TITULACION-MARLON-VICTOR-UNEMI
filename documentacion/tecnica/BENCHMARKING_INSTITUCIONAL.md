# Referentes externos y segmentación de carreras

Fuentes, metodología, limitaciones y proceso de actualización de los referentes externos de
abandono (RF-12, HU-08) y de la segmentación de carreras (RF-11, HU-07). El modelo predictivo
se documenta en [PREDICCION_ABANDONO.md](PREDICCION_ABANDONO.md).

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

## 2. Dónde viven: `dim_referente` y `fact_referente_externo`

Patrón de hecho de indicadores en `ALMACEN_ACADEMICO`, separado de `fact_matriculas`: los
indicadores externos son pocos, heterogéneos y de años distintos, y forzarlos al grano de las
matrículas propias sería un error de diseño. La vista `VIS_REFERENTE_EXTERNO` exige una sesión
con institución activa (aunque los referentes son públicos), para que la consulta conversacional
no lea nada sin contexto. Ver `codigo_fuente/base_de_datos/crear_almacen_academico.sql`.

## 3. Carga y actualización

`codigo_fuente/backend/etl/etl_referentes.py` carga
`codigo_fuente/backend/etl/fuentes_externas/referentes_abandono.csv` (paso `referentes` del
pipeline). Es un CSV versionado y auditable, no un extractor automático: los organismos
ecuatorianos no ofrecen una API estable y cada fila declara su fuente, DOI y URL.

Para actualizar: (1) ubicar la cifra en una fuente académica con DOI o en el portal oficial del
organismo; (2) agregar la fila al CSV con su definición exacta, país, modalidad y nivel de
comparabilidad; (3) ejecutar `python -m etl.etl_referentes` desde `codigo_fuente/backend`.

## 4. Segmentación de carreras

`codigo_fuente/backend/ml/segmentar.py` agrupa las carreras (o módulos) de cada institución con
K-means sobre cuatro indicadores estandarizados: tasa histórica de abandono, promedio histórico,
asistencia histórica y riesgo promedio actual (salida del modelo). Se segmentan las carreras
propias y no las universidades, porque con cuatro referentes externos un agrupamiento entre
instituciones no sería defendible.

- **Elección de k:** barrido de 2 a 6 con silueta y Davies-Bouldin; se usa k = 3, número que una
  autoridad puede gestionar.
- **Validación:** estabilidad con 100 remuestreos (ARI), comparación con Ward y HDBSCAN, y
  prueba de Kruskal-Wallis de la tasa histórica entre segmentos. Como esa tasa también se usa
  para agrupar, la prueba confirma la separación pero no es una validación independiente.
- **Etiquetas:** los segmentos se ordenan por un índice de riesgo combinado
  (z de la tasa histórica + z del riesgo promedio) y se nombran «Atención prioritaria»,
  «Estable» y «Bajo riesgo». Los nombres son relativos dentro de la institución.

Resultados actuales (`ml/modelos/*/segmentacion.json`): UNEMI_PRUEBAS, 18 carreras, silueta
0,355, ARI 0,540, Kruskal-Wallis p = 0,004; OULAD, 7 módulos, silueta 0,229, p = 0,145
(descriptiva).

## 5. Exposición en el sistema

El panel, la página de carreras, la de referentes y la consulta conversacional leen las mismas
vistas (`VIS_SEGMENTO_CARRERA`, `VIS_REFERENTE_EXTERNO`). Preguntas como «¿qué carreras necesitan
atención prioritaria?» o «compara nuestra tasa de abandono con la del referente de Ecuador» se
responden con métricas certificadas.

## 6. Limitaciones

- Los referentes son cifras puntuales, no series temporales, y sus definiciones de abandono
  difieren; por eso cada fila declara su definición y comparabilidad.
- La tasa histórica de UNEMI_PRUEBAS está sobrestimada por la censura a la derecha de una
  ventana 2019-2026 y proviene de datos sintéticos: no describe a la UNEMI.
- No se integran todavía datos socioeconómicos del INEC.
