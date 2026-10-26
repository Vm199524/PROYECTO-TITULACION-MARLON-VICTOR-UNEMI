# Gobierno de datos del prototipo VicMar (LOPDP)

**Proyecto:** Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional
**Autores:** Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco · Universidad Estatal de Milagro · 2026
**Versión:** 1.0 (Avance 3) · **Estado:** propuesta para la institución que adopte el sistema

Este documento fija las reglas con que el sistema recibe, transforma, usa, comparte, conserva y elimina datos de estudiantes. Responde a una recomendación de la tutoría del Avance 2: validar con datos reales anonimizados de una carrera solo después de contar con un documento de gobierno de datos alineado con la Ley Orgánica de Protección de Datos Personales (LOPDP).

Cada regla remite al control técnico que la hace cumplir en el código, de modo que la protección dependa de la arquitectura y no de la buena voluntad del usuario.

## 1. Marco normativo

| Norma | Qué exige al sistema |
|---|---|
| Ley Orgánica de Protección de Datos Personales (Asamblea Nacional del Ecuador, 2021; Registro Oficial, Quinto Suplemento 459, 26 de mayo de 2021) | Principios de licitud, finalidad, minimización, proporcionalidad, confidencialidad, calidad, conservación limitada, seguridad y responsabilidad proactiva; derechos del titular; análisis de riesgo (art. 40) y evaluación de impacto (art. 42); notificación de vulneraciones en un término de cinco días; derecho a no ser objeto de decisiones basadas únicamente o parcialmente en valoraciones automatizadas (art. 20) |
| Guía de Gestión de Riesgos y Evaluación de Impacto del Tratamiento de Datos Personales (Superintendencia de Protección de Datos Personales [SPDP], Resolución SPDP-SPD-2025-0003-R, 2025) | Metodología obligatoria de gestión de riesgos y de evaluación de impacto antes de un tratamiento de alto riesgo |
| Norma General para la Garantía del Derecho de Protección de Datos Personales en el Uso de Sistemas de Inteligencia Artificial (SPDP, Resolución SPDP-SPD-2026-0009-R, 2026) | Transparencia ante el titular cuando el tratamiento es automatizado, gestión de riesgos y evaluación de impacto, medidas de seguridad, inclusión en el Registro de Actividades de Tratamiento y auditoría según el nivel de riesgo |

El prototipo usa datos sintéticos (UNEMI_PRUEBAS) y datos reales anonimizados de origen público (OULAD, Open University del Reino Unido, licencia CC BY 4.0). Ningún dato personal real de la UNEMI entra al sistema mientras la institución no apruebe los requisitos de la sección 9.

## 2. Roles y responsabilidades

| Rol | Quién lo asume | Responsabilidad |
|---|---|---|
| Responsable del tratamiento | La universidad que adopta el sistema | Decide la finalidad, aprueba la evaluación de impacto y responde ante la SPDP |
| Delegado de protección de datos | Quien designe la universidad | Supervisa el cumplimiento, atiende a los titulares y es el contacto con la autoridad |
| Custodio de los datos | Dirección de TI | Opera el almacén, las cuentas, los respaldos y la clave de seudonimización |
| Encargado técnico del modelo | Equipo de analítica (en el prototipo, los autores) | Entrena, valida, monitorea y documenta el modelo |
| Usuario de las alertas | Autoridad académica y bienestar estudiantil | Revisa cada alerta antes de contactar al estudiante y registra la intervención |
| Titular | Cada estudiante | Ejerce sus derechos de información, acceso, rectificación, eliminación, oposición y portabilidad |

## 3. Clasificación de los datos

| Clase | Ejemplos en el sistema | Tratamiento |
|---|---|---|
| Pública | Referentes externos con DOI, métricas agregadas publicadas | Sin restricción |
| Interna | Métricas del modelo, segmentos de carrera, tasas por periodo | Solo usuarios autenticados |
| Confidencial | Trayectoria académica, promedio, asistencia, saldo, probabilidad de abandono, intervenciones | Vistas filtradas por institución, rol y cédula enmascarada |
| Identificadora | Cédula, nombres y apellidos | Nunca sale del almacén sin enmascarar; el modelo no la usa; no se envía a proveedores de IA |
| Sensible (LOPDP) | Salud, etnia, discapacidad, condición socioeconómica detallada | **No se recolecta.** El contrato del almacén no tiene columnas para estos datos |

## 4. Ciclo de vida y controles

```
Solicitud y autorización → Extracción → Anonimización → Calidad (Great Expectations)
→ ETL al almacén → Entrenamiento (MLflow) → Calificación → Alertas y consulta
→ Monitoreo de deriva (Evidently, PSI) → Conservación limitada → Eliminación
```

| Etapa | Regla | Control técnico | Dónde está |
|---|---|---|---|
| Solicitud | Se usa una base legal (misión institucional de retención) y una finalidad escrita: priorizar el acompañamiento. Ningún otro uso | Ficha del modelo con «usos no previstos» | `backend/api/modelo.py`, página «Calidad del modelo» |
| Extracción | Solo las columnas del contrato del almacén (minimización) | `COLUMNAS_OBLIGATORIAS` y `COLUMNAS_OPCIONALES` | `backend/etl/perfiles.py` |
| Anonimización | Seudónimo HMAC-SHA256 con clave institucional; supresión de nombres; generalización de ciudad; k-anonimato con k = 5 | Script con informe sin datos personales | `backend/scripts/anonimizar_carrera.py` |
| Calidad | Integridad, dominio, rango y volumen antes de entrenar; una falla crítica detiene el pipeline | 23 expectativas de Great Expectations | `backend/mlops/calidad_datos.py` |
| Almacenamiento | Aislamiento por institución en el motor; tablas físicas sin acceso para las cuentas de la aplicación | `SESSION_CONTEXT`, vistas `VIS_*`, cuentas `chat_reader` y `app_seguimiento` | `base_de_datos/crear_almacen_academico.sql` |
| Entrenamiento | Cada modelo queda trazado: datos, parámetros, métricas y artefactos | Experimento por institución en MLflow | `backend/mlops/registro_mlflow.py` |
| Uso | Alerta = sugerencia, no decisión; una persona revisa antes de contactar | Registro de intervención con su responsable | Página «Seguimiento», `sp_registrar_intervencion` |
| Consulta conversacional | La IA externa recibe el esquema y, si se pide interpretación, filas seudonimizadas; nunca cédulas ni nombres | Seudonimización y verificador de cifras | `backend/core/privacidad.py`, `backend/nl2sql/redactor.py` |
| Inteligencia de negocios | Metabase solo ve agregados de 5 o más estudiantes, sin identificadores | Esquema `bi` y cuenta `metabase_lector` | `base_de_datos/crear_vistas_metabase.sql` |
| Monitoreo | Si la distribución de entrada cambia, se avisa y se reentrena | Evidently (DataDriftPreset) y PSI | `backend/mlops/deriva.py`, `backend/ml/calificar.py` |
| Auditoría | Cada ingreso, consulta y exportación queda registrada con su usuario y la huella del SQL | Bitácora de auditoría | Página «Auditoría» |
| Conservación | Trayectorias: mientras dure la finalidad y el estudiante esté matriculado más un periodo; predicciones: se reemplazan en cada calificación; bitácora: 2 años | Recarga completa del ETL y reemplazo de predicciones | Pipeline |
| Eliminación | Al terminar la finalidad o ante una solicitud procedente del titular, se eliminan sus filas y se recalcula | Borrado por seudónimo y nueva carga | Procedimiento de TI |

## 5. Matriz de acceso por rol

| Recurso | Autoridad académica | Bienestar estudiantil | Administrador de TI |
|---|---|---|---|
| Panel, carreras y referentes | Sí | Sí | Sí |
| Listado y ficha del estudiante (cédula enmascarada) | Sí | Sí | Sí |
| Simulador de escenarios | No | Sí | Sí |
| Ver intervenciones | Sí | Sí | Sí |
| Registrar y cerrar intervenciones | No | Sí | Sí |
| Consulta conversacional y exportación | Sí | Sí | Sí |
| Calidad del modelo, deriva y calidad de datos | Sí | No | Sí |
| Usuarios, auditoría, estado del sistema y SQL generado | No | No | Sí |

La matriz se aplica en el backend (`CAPACIDADES_POR_ROL` en `core/seguridad.py`, verificado en cada ruta) y no solo ocultando menús en la interfaz.

## 6. Gobierno del modelo

1. **Validación antes de usar:** validación cruzada agrupada por estudiante, prueba temporal, resultados por periodo y por carrera, y validación con origen móvil. Meta mínima: ROC-AUC ≥ 0,75 y recall del umbral medio ≥ 0,75 en datos reales.
2. **Equidad:** recall y ROC-AUC por género, modalidad y sede. Una brecha de recall superior a 10 puntos entre grupos obliga a revisar variables y umbrales.
3. **Transparencia:** cada alerta muestra sus tres factores principales (SHAP) y la ficha del modelo dice qué predice, con qué datos, para qué no sirve y sus limitaciones.
4. **Supervisión humana (art. 20 LOPDP):** ninguna decisión sobre un estudiante (matrícula, becas, sanciones) se toma con base en la probabilidad. El sistema solo prioriza a quién ofrecer acompañamiento.
5. **Reentrenamiento:** al cierre de cada periodo, o antes si Evidently marca deriva en la mayoría de variables o en dos de las cinco más importantes. Cada reentrenamiento queda en MLflow y se compara con el anterior antes de publicarse.
6. **Retiro del modelo:** si en el monitoreo el ROC-AUC del último periodo cae por debajo de 0,70, el modelo se retira y las alertas se suspenden hasta reentrenar.

## 7. Transferencia internacional y proveedores de IA

Los proveedores de lenguaje (Gemini, Groq, NVIDIA y DeepSeek) operan fuera del Ecuador. En el prototipo reciben solo:

- el esquema de las vistas, sin datos;
- la pregunta del usuario;
- y, solo si el usuario pide una interpretación, las filas del resultado seudonimizadas.

Para un despliegue con datos reales se requiere una de dos opciones:

1. un proveedor con un instrumento contractual que cumpla los estándares de transferencia de la LOPDP;
2. o un modelo de lenguaje alojado en la infraestructura de la institución.

Mientras no exista ninguna de las dos, la interpretación con IA debe deshabilitarse (`CONSULTA_INTERPRETAR=0`).

## 8. Gestión de incidentes

1. Quien detecte el incidente lo reporta a TI y al delegado de protección de datos.
2. TI contiene el incidente: revoca cuentas o tokens, aísla el servidor y conserva la bitácora.
3. El delegado evalúa el riesgo para los titulares.
4. El responsable notifica a la SPDP dentro del término de cinco días que fija la LOPDP y, si el riesgo es alto, informa a los estudiantes afectados.
5. Se registra la causa y la corrección en el Registro de Actividades de Tratamiento.

## 9. Requisitos para validar con datos reales de una carrera de la UNEMI

1. Solicitud formal al responsable del tratamiento con la finalidad, las columnas del contrato y este documento.
2. Evaluación de impacto según la guía de la SPDP (Resolución SPDP-SPD-2025-0003-R), por tratarse de perfiles automatizados de estudiantes.
3. Acuerdo de confidencialidad firmado por los autores.
4. Extracción hecha por TI de la institución. La clave de seudonimización la guarda TI y nunca se entrega a los autores.
5. Anonimización con `anonimizar_carrera.py --k 5 --suprimir` y entrega solo del extracto anonimizado y de su informe.
6. Carga con un perfil `REAL_ANONIMIZADO` y validación de calidad (Great Expectations) antes de entrenar.
7. Reporte de ROC-AUC y recall por periodo y por cohorte de la carrera. Los resultados se publican solo en forma agregada.
8. Eliminación del extracto al terminar la validación y acta de eliminación.

## 10. Indicadores de gobierno

| Indicador | Meta | Fuente |
|---|---|---|
| Expectativas de calidad cumplidas | 100 % de las críticas | `calidad_datos.json` |
| Variables importantes con deriva | Máximo 2 de 5 | `deriva.json` |
| ROC-AUC del último periodo | ≥ 0,75 | `metricas.json` (origen móvil) |
| Brecha de recall entre grupos | ≤ 10 puntos | `metricas.json` (equidad) |
| Consultas que intentan escribir o leer otra institución | 0 ejecutadas | Evaluación de la consulta conversacional |
| Accesos sin bitácora | 0 | Auditoría |

## Referencias

Asamblea Nacional del Ecuador. (2021). *Ley Orgánica de Protección de Datos Personales*. Registro Oficial, Quinto Suplemento 459, 26 de mayo de 2021.

Superintendencia de Protección de Datos Personales. (2025). *Guía de gestión de riesgos y evaluación de impacto del tratamiento de datos personales* (Resolución SPDP-SPD-2025-0003-R).

Superintendencia de Protección de Datos Personales. (2026). *Norma general para la garantía del derecho de protección de datos personales en el uso de sistemas de inteligencia artificial* (Resolución SPDP-SPD-2026-0009-R).

Kuzilek, J., Hlosta, M. y Zdrahal, Z. (2017). Open University Learning Analytics dataset. *Scientific Data, 4*, 170171. https://doi.org/10.1038/sdata.2017.171
