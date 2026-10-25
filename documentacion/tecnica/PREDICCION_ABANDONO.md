# Predicción del abandono estudiantil

Documento técnico del modelo predictivo (versión 3.0, Avance 2). Las cifras provienen de
`codigo_fuente/backend/ml/modelos/<INSTITUCION>/metricas.json` y `prospectiva.json`; si se
reentrena, esos archivos son la fuente de verdad.

## 1. Qué se predice

Con los datos de un estudiante hasta el cierre del periodo *t*, la probabilidad de que aparezca
como retirado en *t + 1*. La unidad de análisis es el estudiante en un periodo: cada fila del
panel usa solo información conocida al cierre de *t*. Graduarse o egresar no cuenta como
abandono. Las filas del último periodo de cada estudiante activo no tienen etiqueta y son las que
se califican.

El Avance 1 usaba una fila por estudiante y datos deterministas; su ROC-AUC de 0,9999 no es
comparable con el actual.

## 2. Datos

| Institución | Origen | Periodo | Filas | Etiquetadas | Abandonos en t+1 |
|---|---|---|---|---|---|
| UNEMI_PRUEBAS | Sintético (simulador de factores latentes) | Semestre | 79.268 | 64.760 | 4.260 (6,58 %) |
| OULAD_UK | Real anonimizado (Kuzilek et al., 2017) | Corte de 28 días | 189.299 | 156.706 | 3.986 (2,54 %) |

El perfil de calidad y las figuras exploratorias se generan con `python -m ml.exploracion`.

## 3. Variables (`ml/caracteristicas.py`)

Una sola función (`construir_panel`) arma el panel para entrenar y para calificar.

| Grupo | Variables | Se activa |
|---|---|---|
| Base | Nivel, corte, periodos cursados, avance; promedio y asistencia actuales, rezagados, media móvil, acumulados, mínimos, tendencias, racha baja y posición en la cohorte | Siempre |
| Cartera | En mora, saldo pendiente, porcentaje de periodos en mora, beca | Si hay `saldo_pendiente` |
| Matrícula | Créditos, número de matrícula, días de anticipación | Si hay `numero_matricula` |
| Aula virtual | Actividad (logaritmo), acumulada, cambio, posición en la cohorte, días sin actividad | Si hay `actividad_lms` |
| Evaluaciones | Vencidas, porcentaje entregado, porcentaje tardío, nota | Si hay `evaluaciones_vencidas` |

UNEMI_PRUEBAS usa 41 variables y OULAD 37 (no tiene cartera).

## 4. Entrenamiento y validación (`ml/entrenar.py`)

Un modelo por institución, sin mezclar datos.

1. **Prueba temporal:** los periodos más recientes (al menos el 25 % de las filas etiquetadas).
2. **Ajuste:** búsqueda aleatoria para Random Forest y Optuna (TPE) para LightGBM, con
   validación agrupada por estudiante.
3. **Comparación:** regresión logística, Random Forest con pesos por clase, Random Forest con
   SMOTE y LightGBM, con validación cruzada de 5 pliegues agrupada por estudiante. Se elige el
   mayor ROC-AUC medio (desempate por PR-AUC).
4. **Calibración y umbrales:** Platt sobre predicciones fuera de pliegue; umbral medio para
   recall 0,80 y alto para recall 0,50.
5. **Evaluación:** prueba temporal (ROC-AUC, PR-AUC, Brier, captura en el 10 y 20 % superior,
   equidad por subgrupo, importancia por permutación) y, en OULAD, evaluación prospectiva.

## 5. Resultados

| Métrica | UNEMI_PRUEBAS | OULAD_UK |
|---|---|---|
| Validación cruzada, ROC-AUC de LightGBM | 0,828 ± 0,003 | 0,803 ± 0,010 |
| Prueba temporal, ROC-AUC | 0,829 | 0,766 |
| PR-AUC (prevalencia) | 0,466 (0,065) | 0,103 (0,031) |
| Recall / precisión en el umbral medio | 0,781 / 0,146 | 0,786 / 0,060 |
| Recall / precisión en el umbral alto | 0,492 / 0,450 | 0,462 / 0,092 |
| Abandonos en el 20 % de mayor riesgo | 67,9 % | 55,2 % |
| Brier sin calibrar → calibrado | 0,134 → 0,046 | 0,191 → 0,029 |
| Prospectiva 2014J (corte siguiente) | | ROC-AUC 0,762 · recall 0,913 |

Lectura: el umbral medio sirve para no dejar fuera a casi nadie que abandonará; el contacto
directo se organiza con el umbral alto o con los primeros de la lista hasta la capacidad de
bienestar. En OULAD, con abandonos muy poco frecuentes, la calibración ayuda a ordenar y a
estimar cuántos casos esperar más que como valor individual.

## 6. Calificación, explicación y monitoreo (`ml/calificar.py`)

Cada estudiante activo recibe probabilidad calibrada, nivel de riesgo, percentil y las tres
razones principales según SHAP, redactadas en español. El PSI compara la distribución actual de
las variables con la del entrenamiento y marca las que derivan (más de 0,25).

## 7. Limitaciones

- UNEMI_PRUEBAS es sintético: sus métricas prueban el sistema completo, no describen a la UNEMI.
- En OULAD, «abandono» es retirarse del módulo en el corte siguiente; en UNEMI, no matricularse
  en el semestre siguiente. Las cifras no se promedian entre instituciones.
- El modelo identifica asociaciones, no causas; la decisión de intervenir es siempre de una
  persona.
