# ADR-005: Algoritmo del modelo predictivo de abandono

- **Estado:** Aceptada · **Fecha:** 2026-10-07 (reemplaza la versión del 03/10/2026)
- **Decisión:** LightGBM ajustado con Optuna (lightgbm 4.7.0), elegido por validación cruzada

## Contexto

Clasificación binaria del abandono en el periodo siguiente sobre un panel estudiante-periodo con clases desbalanceadas. Los cuatro candidatos se compararon con los mismos 5 pliegues agrupados por estudiante en las dos instituciones; OULAD (datos reales) pesa más que UNEMI_PRUEBAS (sintético). Reemplaza la versión de la matriz del 03/10/2026, hecha con el panel anterior.

## Criterios (origen → peso)

- **Discriminación en datos reales (ROC-AUC en OULAD)** (35 %): *Origen:* OE2 y RNF de calidad (ROC-AUC ≥ 0,75)
- **Detección de la clase minoritaria (PR-AUC en OULAD)** (15 %): *Origen:* Prioridad del recall (fase 1 de CRISP-DM)
- **Desempeño en la segunda institución (ROC-AUC en UNEMI_PRUEBAS)** (10 %): *Origen:* Portabilidad entre instituciones
- **Explicación por estudiante** (15 %): *Origen:* HU-03 y RF de explicación SHAP
- **Evidencia en trabajos previos** (15 %): *Origen:* Sección 1.3.6
- **Costo de entrenamiento** (10 %): *Origen:* Procesos por lotes nocturnos

## Opciones evaluadas

### LightGBM ajustado con Optuna: 4,65 / 5
- Discriminación en datos reales (ROC-AUC en OULAD): **5**. ROC-AUC 0,803 ± 0,010, el mayor de los cuatro. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Detección de la clase minoritaria (PR-AUC en OULAD): **5**. PR-AUC 0,095, el mayor de los cuatro (prevalencia 0,025). *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Desempeño en la segunda institución (ROC-AUC en UNEMI_PRUEBAS): **5**. ROC-AUC 0,828 ± 0,003, el mayor de los cuatro. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Explicación por estudiante: **5**. SHAP para árboles implementado: tres razones por estudiante redactadas en español. *Fuente:* codigo_fuente/backend/ml/explicacion.py
- Evidencia en trabajos previos: **4**. El boosting de gradiente aparece en 9 estudios y XGBoost en 12 de la revisión; Carballo-Mendívil et al. (2025) compararon LightGBM y XGBoost. *Fuente:* Duro et al. (2026), Computers, 15(3), 164, pp. 9-10, https://doi.org/10.3390/computers15030164; Carballo-Mendívil et al. (2025), tabla de trabajos previos (documentacion/literatura/trabajos_previos.json)
- Costo de entrenamiento: **3**. La búsqueda con Optuna (25 pruebas) es el paso más costoso del entrenamiento; cabe en un proceso por lotes. *Fuente:* datos_locales/pipeline_estado.json

### Random Forest con pesos por clase: 4,30 / 5
- Discriminación en datos reales (ROC-AUC en OULAD): **4**. ROC-AUC 0,797 ± 0,010. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Detección de la clase minoritaria (PR-AUC en OULAD): **4**. PR-AUC 0,085. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Desempeño en la segunda institución (ROC-AUC en UNEMI_PRUEBAS): **4**. ROC-AUC 0,821 ± 0,006. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Explicación por estudiante: **5**. Explicable con el mismo SHAP para árboles. *Fuente:* codigo_fuente/backend/ml/explicacion.py
- Evidencia en trabajos previos: **5**. Es el algoritmo más usado en la revisión de 61 estudios (33). *Fuente:* Duro et al. (2026), Computers, 15(3), 164, pp. 9-10, https://doi.org/10.3390/computers15030164
- Costo de entrenamiento: **4**. Búsqueda aleatoria de 10 combinaciones; más barato que la búsqueda bayesiana. *Fuente:* Romero y Liao (2025), PLOS ONE, 20(6), e0325047, p. 12, https://doi.org/10.1371/journal.pone.0325047

### Regresión logística: 3,75 / 5
- Discriminación en datos reales (ROC-AUC en OULAD): **3**. ROC-AUC 0,787 ± 0,010. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Detección de la clase minoritaria (PR-AUC en OULAD): **3**. PR-AUC 0,082. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Desempeño en la segunda institución (ROC-AUC en UNEMI_PRUEBAS): **4**. ROC-AUC 0,819 ± 0,003. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Explicación por estudiante: **5**. Sus coeficientes se interpretan directamente. *Fuente:* Romero y Liao (2025), PLOS ONE, 20(6), e0325047, p. 12, https://doi.org/10.1371/journal.pone.0325047
- Evidencia en trabajos previos: **4**. Segundo algoritmo más usado (27 estudios). *Fuente:* Duro et al. (2026), Computers, 15(3), 164, pp. 9-10, https://doi.org/10.3390/computers15030164
- Costo de entrenamiento: **5**. El más barato de entrenar de los cuatro. *Fuente:* Romero y Liao (2025), PLOS ONE, 20(6), e0325047, p. 12, https://doi.org/10.1371/journal.pone.0325047

### Random Forest con SMOTE: 2,70 / 5
- Discriminación en datos reales (ROC-AUC en OULAD): **2**. ROC-AUC 0,777 ± 0,007, el menor de los cuatro. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Detección de la clase minoritaria (PR-AUC en OULAD): **2**. PR-AUC 0,071, el menor de los cuatro. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Desempeño en la segunda institución (ROC-AUC en UNEMI_PRUEBAS): **3**. ROC-AUC 0,816 ± 0,005. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)
- Explicación por estudiante: **5**. Explicable con SHAP para árboles. *Fuente:* codigo_fuente/backend/ml/explicacion.py
- Evidencia en trabajos previos: **3**. SMOTE es frecuente en la literatura, pero con validación agrupada no supera a los pesos por clase. *Fuente:* Duro et al. (2026), Computers, 15(3), 164, pp. 9-10, https://doi.org/10.3390/computers15030164
- Costo de entrenamiento: **2**. El sobremuestreo multiplica las filas de la clase minoritaria en cada pliegue. *Fuente:* Resultados propios: codigo_fuente/backend/ml/modelos/<institución>/metricas.json (validación cruzada de 5 pliegues agrupada por estudiante)

## Resultado

| Opción | Puntaje |
|---|---|
| LightGBM ajustado con Optuna | 4,65 |
| Random Forest con pesos por clase | 4,30 |
| Regresión logística | 3,75 |
| Random Forest con SMOTE | 2,70 |

**Sensibilidad:** estable: ninguna variación de ±20 % en un peso cambia la ganadora.

## Decisión y razón

LightGBM obtuvo el mayor ROC-AUC y el mayor PR-AUC medios en las dos instituciones con la misma validación cruzada agrupada por estudiante, y admite la explicación SHAP ya implementada. La elección no se fija a mano: el entrenamiento compara los cuatro candidatos en cada reentrenamiento y conserva el de mayor ROC-AUC medio (desempate por PR-AUC); esta matriz documenta el resultado de la versión 3.

## Consecuencias

- Se gana el mejor ordenamiento del riesgo en datos reales y sintéticos, con explicación por estudiante.
- Se acepta un entrenamiento más costoso por la búsqueda de hiperparámetros con Optuna.
- La regresión logística queda como línea base; si un reentrenamiento cambia la ganadora, el sistema la registra en metricas.json y la pantalla Calidad del modelo la muestra.

## Verificación en el código

`codigo_fuente/backend/requirements.txt` fija `lightgbm` en la versión `4.7.0`; `ml/entrenar.py` compara los cuatro candidatos y guarda la comparación en `metricas.json` (clave `comparacion_cv`).
