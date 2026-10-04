# ADR-001: Lenguaje de programación del backend

- **Estado:** Aceptada · **Fecha:** 2026-10-03
- **Decisión:** Python (versión 3.14)

## Contexto

El backend entrena y sirve el modelo de abandono (validación cruzada agrupada, SHAP), ejecuta el ETL, expone la API REST que consume el frontend y llama a proveedores externos de modelos de lenguaje. Equipo de 2 personas, sin presupuesto para licencias. La decisión se documenta sobre un prototipo ya implementado y probado.

## Criterios (origen → peso)

- **Bibliotecas para el modelo y su validación** (35 %): Validación cruzada agrupada y estratificada, manejo del desbalance y explicaciones SHAP disponibles de forma nativa. *Origen:* RF-02, RF-03, RF-05
- **Evidencia en trabajos previos** (20 %): Cuántos trabajos previos leídos declaran el lenguaje. *Origen:* Sección 1.3 (tabla de trabajos previos)
- **Soporte de la versión** (15 %): Versión con soporte vigente durante el proyecto. *Origen:* RNF-09 (reproducibilidad) y mantenibilidad
- **Un solo lenguaje para el modelo y la API** (15 %): Evitar un puente entre lenguajes para servir el modelo. *Origen:* RNF-08 (una sola función de características para entrenar y calificar)
- **Costo de cambio sobre el prototipo validado** (15 %): Esfuerzo de reescribir y volver a validar lo existente. *Origen:* Restricción: plazo del proyecto y prototipo ya probado

## Opciones evaluadas

### Python — 5,00 / 5
- Bibliotecas para el modelo y su validación: **5**. scikit-learn 1.9.1 trae StratifiedGroupKFold; imbalanced-learn y SHAP cubren desbalance y explicaciones; todas fijadas en requirements.txt. *Fuente:* Documentación oficial de scikit-learn 1.9.1, StratifiedGroupKFold (scikit-learn.org), consultada 2026-10-03
- Evidencia en trabajos previos: **5**. Es el lenguaje más declarado: 3 de los 11 trabajos (y 1 usa R); ninguno declara Java ni Node.js. *Fuente:* Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)
- Soporte de la versión: **5**. La rama 3.14 está en corrección de errores con fin de vida en octubre de 2030. *Fuente:* Python Developer's Guide, «Status of Python versions» (devguide.python.org/versions), consultado 2026-10-03
- Un solo lenguaje para el modelo y la API: **5**. main.py importa directamente ml/ para calificar y explicar; el mismo código entrena y sirve. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)
- Costo de cambio sobre el prototipo validado: **5**. Es el lenguaje del backend implementado y probado. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

### Java — 2,10 / 5
- Bibliotecas para el modelo y su validación: **2**. Las bibliotecas que exigen RF-03 y RF-05 (validación agrupada estratificada de scikit-learn y SHAP) se distribuyen para Python; habría que reimplementarlas o invocar Python. *Fuente:* Documentación oficial de scikit-learn 1.9.1, StratifiedGroupKFold (scikit-learn.org), consultada 2026-10-03
- Evidencia en trabajos previos: **1**. Ningún trabajo previo leído declara Java. *Fuente:* Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)
- Soporte de la versión: **5**. JDK 25 alcanzó disponibilidad general el 16/09/2025 y es versión de soporte extendido (LTS). *Fuente:* OpenJDK, «JDK 25» (openjdk.org/projects/jdk/25), consultado 2026-10-03
- Un solo lenguaje para el modelo y la API: **2**. Requeriría servir el modelo de Python como servicio aparte o exportarlo, duplicando la función de características. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)
- Costo de cambio sobre el prototipo validado: **1**. Implica reescribir el backend completo y su suite de pruebas. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

### Node.js (TypeScript) — 1,75 / 5
- Bibliotecas para el modelo y su validación: **1**. Mismas bibliotecas ausentes que en Java; el ecosistema no ofrece las equivalentes oficiales de validación agrupada ni SHAP. *Fuente:* Documentación oficial de scikit-learn 1.9.1, StratifiedGroupKFold (scikit-learn.org), consultada 2026-10-03
- Evidencia en trabajos previos: **1**. Ningún trabajo previo leído declara Node.js. *Fuente:* Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)
- Soporte de la versión: **4**. Node.js 24 es versión LTS; las LTS reciben correcciones críticas durante 30 meses. *Fuente:* Node.js, «Previous releases» (nodejs.org/en/about/previous-releases), consultado 2026-10-03
- Un solo lenguaje para el modelo y la API: **2**. Igual que Java: el modelo seguiría en Python, con un puente entre procesos. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)
- Costo de cambio sobre el prototipo validado: **2**. Existió un prototipo anterior en Node/Express, pero sin el modelo ni la validación; quedó en la carpeta de revisión. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

## Resultado

| Opción | Puntaje |
|---|---|
| Python | 5,00 |
| Java | 2,10 |
| Node.js (TypeScript) | 1,75 |

**Sensibilidad:** estable: ninguna variación de ±20 % en un peso cambia la ganadora.

## Decisión y razón

Python es la única opción que cubre de forma nativa la validación agrupada por alumno, el manejo del desbalance y las explicaciones SHAP que exigen RF-03 y RF-05, y es el lenguaje más declarado en los trabajos previos. Permite que el mismo código entrene y sirva el modelo, como pide RNF-08.

## Consecuencias

- Se gana un único lenguaje para ETL, modelo y API.
- Se sacrifica rendimiento bruto frente a la JVM, que no es el cuello de botella: la latencia del chat la domina el proveedor de LLM (mediana medida de 28,2 s).
- Riesgo: dependencias con versiones exactas; se mitiga con requirements.lock.txt.

## Verificación en el código

`codigo_fuente/backend/requirements.txt` debe fijar `scikit-learn` en la versión `1.9.1` (lo comprueba verificar_coherencia.py).
