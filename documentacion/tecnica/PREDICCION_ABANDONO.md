# Predicción de abandono estudiantil (módulo ML)

Documento técnico del modelo predictivo, actualizado en el **Avance 2 (25/09/2026)**.
Las cifras de esta página se toman de `codigo_fuente/backend/ml/models/<INSTITUCION>/metrics.json`;
si se reentrena, esos archivos son la fuente de verdad, no esta página.

## 1. Qué se predice

**Con los datos de un alumno hasta su periodo actual, la probabilidad de que abandone en
el periodo siguiente.** La unidad de análisis es el *alumno en un periodo* (sección 1.3
del documento de titulación): cada fila del panel es (alumno, carrera, periodo t), con
características calculadas solo con información hasta t y etiqueta
`y = 1` si el periodo t+1 es `RETIRADO`.

La versión anterior (hasta el 11/09/2026) tenía una fila por alumno y usaba la asistencia
del mismo periodo en que el alumno ya se había retirado: detectaba el abandono, no lo
anticipaba. Por eso su ROC-AUC de 0,9999 no era comparable con el actual.

## 2. Datos: dos instituciones

| Institución | Origen | Periodo | Filas del panel | Con periodo siguiente | Prevalencia al periodo siguiente |
|---|---|---|---|---|---|
| UNEMI_PRUEBAS | Sintético y anonimizado (`codigo_fuente/base_de_datos/datos_de_prueba/`) | Semestre | 83.678 | 69.170 | 1,87 % |
| OULAD_UK | Real y anonimizado: Open University Learning Analytics Dataset (Kuzilek et al., 2017, CC BY 4.0) | Bloque de 28 días | 189.299 | 156.706 | 2,54 % |

**Advertencia sobre los datos sintéticos:** `generate_historial.py` hace caer la asistencia
de quien abandona de ~89 % a ~55 % un periodo antes. Esa sola variable separa los casos
(ROC-AUC 0,996 sin modelo). UNEMI_PRUEBAS sirve para probar la arquitectura; el desempeño
realista se mide en OULAD.

En OULAD, `asistencia_pct` = días con actividad en el aula virtual / días del bloque × 100,
y `promedio` = media (0-10) de las evaluaciones vencidas al cierre del bloque (no entregada
= 0). La presentación 2014J se carga "en curso" hasta el bloque 3; su desenlace real queda
en `OULAD_PRUEBAS.dbo.verdad_futura` para la evaluación prospectiva.

## 3. Características (`codigo_fuente/backend/ml/features_abandono.py`)

Una sola función (`construir_panel`) para entrenar y calificar (evita *training/serving skew*).

| Variable | Qué mide |
|---|---|
| `periodo`, `n_periodos_cursados` | Avance en la trayectoria |
| `promedio_t`, `promedio_delta`, `promedio_media_movil`, `promedio_minimo_hist` | Rendimiento y su tendencia |
| `asistencia_t`, `asistencia_delta`, `asistencia_media_movil`, `asistencia_minima_hist` | Asistencia y su tendencia |
| `en_mora_t`, `saldo_pendiente_t`, `pct_periodos_con_mora` | Situación financiera |
| `beca_porcentaje` | Apoyo financiero |
| `sede_codigo`, `canal_codigo` (one-hot) | Sede y modalidad |

`informe_atipicos()` revisa atípicos por IQR (Alzabidi et al., 2026) sin eliminarlos.

## 4. Entrenamiento y validación (`codigo_fuente/backend/ml/entrenar_abandono.py`)

Un modelo **por institución** (`--empresa`), nunca mezclando datos.

1. **Corte temporal:** el 25 % más reciente del panel se reserva como prueba final.
2. **Ajuste:** `RandomizedSearchCV` (25 combinaciones) del Random Forest con
   `StratifiedGroupKFold` (5 pliegues) **agrupado por alumno**.
3. **Comparación con los mismos pliegues:** RF + ponderación de clases, RF + SMOTE
   (solo en pliegues de entrenamiento), regresión logística y gradient boosting.
   El final es la mejor variante de RF; si una línea base lo supera por > 0,01 de ROC-AUC,
   queda como advertencia en `metrics.json`.
4. **Umbral operativo:** el mayor umbral con recall ≥ 0,80 en las predicciones fuera de pliegue.
5. **Prueba temporal** (una sola vez) + **importancia por permutación**.
6. **Modelo final** reentrenado con todas las filas etiquetadas.

### Resultados (25/09/2026)

| Métrica | UNEMI_PRUEBAS | OULAD_UK |
|---|---|---|
| Modelo final | RF + SMOTE | RF + ponderación de clases |
| ROC-AUC CV (RF elegido) | 0,996 | 0,758 |
| ROC-AUC prueba temporal | 0,997 | 0,752 |
| PR-AUC prueba temporal | 0,976 | 0,080 |
| Recall / precisión en el umbral | 0,777 / 0,990 | 0,798 / 0,052 |
| ROC-AUC prospectivo (bloque siguiente) | — | 0,725 |
| Variable más importante | asistencia_t (artefacto del generador) | promedio_t (rendimiento) |

Con datos reales, el criterio de éxito (a) (ROC-AUC ≥ 0,90) **no se cumple**; se discute
en la sección 3.3 del Avance 2.

## 5. Calificación y explicación (`codigo_fuente/backend/ml/predecir_abandono.py`)

Califica el periodo vigente de cada trayectoria activa. Categorías: ALTO (p ≥ umbral),
MEDIO (p ≥ umbral/2), BAJO. Para ALTO y MEDIO calcula SHAP (TreeExplainer) y guarda los
tres factores que más elevan el riesgo, en lenguaje natural (`factor_1..3`).

## 6. Exposición: panel y chat, misma fuente

`fact_prediccion_abandono` y `fact_evaluacion_modelo` se leen por
`VIS_PREDICCION_ABANDONO` y `VIS_EVALUACION_MODELO` (filtradas por SESSION_CONTEXT, solo
lectura para `chat_reader`), desde `GET /api/ml/prediccion-abandono`,
`GET /api/ml/evaluacion-modelo` y el chat NL2SQL. Las figuras de validación se generan con
`python -m ml.reporte_validacion --empresa X`.

## 7. Reproducir todo

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo_tesis.ps1
```
