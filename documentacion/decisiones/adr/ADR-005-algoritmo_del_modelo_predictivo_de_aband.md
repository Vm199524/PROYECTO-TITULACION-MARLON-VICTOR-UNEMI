# ADR-005: Algoritmo del modelo predictivo de abandono

- **Estado:** Aceptada · **Fecha:** 2026-10-03
- **Decisión:** Random Forest (versión scikit-learn 1.9.1)

## Contexto

Clasificación binaria del abandono en el periodo siguiente sobre un panel alumno-periodo con clases desbalanceadas. Las tres opciones se compararon con los mismos 5 pliegues agrupados por alumno en las dos instituciones; OULAD (datos reales) pesa más que UNEMI_PRUEBAS (sintético).

## Criterios (origen → peso)

- **Discriminación en datos reales (ROC-AUC en OULAD)** (35 %):  *Origen:* OE3 y criterio de éxito (a)
- **Detección de la clase minoritaria (PR-AUC en OULAD)** (15 %):  *Origen:* Prioridad del recall (fase 1 de CRISP-DM)
- **Desempeño en la segunda institución (ROC-AUC en UNEMI_PRUEBAS)** (10 %):  *Origen:* RNF-11 (portabilidad)
- **Explicación por alumno** (15 %):  *Origen:* RF-05 y HU-02
- **Evidencia en trabajos previos** (15 %):  *Origen:* Sección 1.3
- **Costo de entrenamiento** (10 %):  *Origen:* RNF-06 (procesos por lotes)

## Opciones evaluadas

### Random Forest — 4,90 / 5
- Discriminación en datos reales (ROC-AUC en OULAD): **5**. ROC-AUC 0,758 ± 0,008, empatado con gradient boosting. *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues)
- Detección de la clase minoritaria (PR-AUC en OULAD): **5**. PR-AUC 0,074, el mayor de los tres. *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues)
- Desempeño en la segunda institución (ROC-AUC en UNEMI_PRUEBAS): **5**. ROC-AUC 0,996. *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues)
- Explicación por alumno: **5**. Explicación SHAP por alumno implementada (tres factores en lenguaje natural); SHAP con árboles también en Carballo-Mendívil et al. (2025) y Khatun et al. (2025). *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues); Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)
- Evidencia en trabajos previos: **5**. Es el algoritmo más usado en la revisión de 61 estudios (33), y en Romero y Liao (2025) obtuvo el mejor AUC. *Fuente:* Duro et al. (2026), Computers, 15(3), 164, pp. 9–10, https://doi.org/10.3390/computers15030164; Romero y Liao (2025), PLOS ONE, 20(6), e0325047, p. 12, https://doi.org/10.1371/journal.pone.0325047
- Costo de entrenamiento: **4**. En Romero y Liao (2025) entrenó en 4,14 s frente a 348,6 s de XGBoost. *Fuente:* Romero y Liao (2025), PLOS ONE, 20(6), e0325047, p. 12, https://doi.org/10.1371/journal.pone.0325047

### Gradient boosting (HistGradientBoosting) — 4,25 / 5
- Discriminación en datos reales (ROC-AUC en OULAD): **5**. ROC-AUC 0,758 ± 0,008, empatado con Random Forest. *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues)
- Detección de la clase minoritaria (PR-AUC en OULAD): **5**. PR-AUC 0,073. *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues)
- Desempeño en la segunda institución (ROC-AUC en UNEMI_PRUEBAS): **4**. ROC-AUC 0,980, el más bajo de los tres en la segunda institución. *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues)
- Explicación por alumno: **4**. Explicable con SHAP para árboles, pero no implementado en el prototipo. *Fuente:* Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)
- Evidencia en trabajos previos: **3**. Gradient boosting aparece en 9 estudios y XGBoost en 12 de la revisión; Carballo-Mendívil et al. (2025) y Khatun et al. (2025) eligen XGBoost. *Fuente:* Duro et al. (2026), Computers, 15(3), 164, pp. 9–10, https://doi.org/10.3390/computers15030164; Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)
- Costo de entrenamiento: **3**. En Romero y Liao (2025) XGBoost fue el más lento (348,6 s); HistGradientBoosting no se midió allí. *Fuente:* Romero y Liao (2025), PLOS ONE, 20(6), e0325047, p. 12, https://doi.org/10.1371/journal.pone.0325047

### Regresión logística — 3,85 / 5
- Discriminación en datos reales (ROC-AUC en OULAD): **3**. ROC-AUC 0,730 ± 0,008, el menor en datos reales. *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues)
- Detección de la clase minoritaria (PR-AUC en OULAD): **3**. PR-AUC 0,059. *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues)
- Desempeño en la segunda institución (ROC-AUC en UNEMI_PRUEBAS): **5**. ROC-AUC 0,997; en datos sintéticos todas las opciones superan 0,98. *Fuente:* Resultados propios: codigo_fuente/backend/ml/models/<institución>/metrics.json (validación cruzada agrupada por alumno, 5 pliegues)
- Explicación por alumno: **5**. Sus coeficientes se interpretan directamente. *Fuente:* Romero y Liao (2025), PLOS ONE, 20(6), e0325047, p. 12, https://doi.org/10.1371/journal.pone.0325047
- Evidencia en trabajos previos: **4**. Segundo algoritmo más usado (27 estudios); la mejor individual en Rabelo y Zárate (2025). *Fuente:* Duro et al. (2026), Computers, 15(3), 164, pp. 9–10, https://doi.org/10.3390/computers15030164; Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)
- Costo de entrenamiento: **5**. Es el más barato de entrenar de los tres. *Fuente:* Romero y Liao (2025), PLOS ONE, 20(6), e0325047, p. 12, https://doi.org/10.1371/journal.pone.0325047

## Resultado

| Opción | Puntaje |
|---|---|
| Random Forest | 4,90 |
| Gradient boosting (HistGradientBoosting) | 4,25 |
| Regresión logística | 3,85 |

**Sensibilidad:** estable: ninguna variación de ±20 % en un peso cambia la ganadora.

## Decisión y razón

Random Forest y gradient boosting empatan en datos reales; Random Forest gana por detectar mejor la clase minoritaria, por rendir igual en la segunda institución, por tener la explicación SHAP ya implementada y por ser el más respaldado en la literatura. La regresión logística queda como línea base.

## Consecuencias

- Se gana un modelo estable entre instituciones y explicable por alumno.
- Se sacrifica la interpretabilidad global directa de la regresión logística.
- Riesgo: el empate con gradient boosting debe revisarse con cada reentrenamiento; el entrenamiento lo registra como advertencia si una alternativa supera en más de 0,01 de ROC-AUC.

## Verificación en el código

`codigo_fuente/backend/requirements.txt` debe fijar `scikit-learn` en la versión `1.9.1` (lo comprueba verificar_coherencia.py).
