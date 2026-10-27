---
title: "Guía del video técnico: VicMar"
subtitle: "Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco · Ingeniería en Tecnologías de la Información · UNEMI · 2026"
---

# Cómo usar esta guía

Esta guía acompaña la grabación del video de la explicación práctica del trabajo de titulación *Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional*. La duración prevista es de **21 minutos** (rango permitido: 15 a 20 recomendado, máximo 30).

**Formato de cada segmento:**
- quién habla, el tiempo y la ventana que se usa: Docker Desktop, VS Code, el navegador o MLflow;
- una tabla con **Ventana | Qué abro | Qué muestro**;
- el recorrido de VS Code (CodeTour) y el diagrama que se usa;
- un texto para decir con naturalidad («Qué digo»), que no hace falta leer al pie de la letra.

**Recorridos en VS Code.** Los siete recorridos están en `.tours/` (fuente: `.tours/fuente_recorridos.json`). Al abrir `VicMar.code-workspace` aparecen en la sección **CODETOUR** del Explorador. VS Code abre el archivo en la línea exacta y basta con pulsar «Next».

**Diagramas.** Están en `documentacion/avances/Avance 3/14_VIDEO_TECNICO/diagramas/` en PNG (4000 × 2250 px) y SVG. Se muestran en VS Code o en el visor de imágenes, a pantalla completa.

**Regla de oro.** Toda cifra que se dice en el video está en un archivo del proyecto. El anexo E indica dónde está cada una.

| # | Segmento | Quién | Tiempo | Recorrido de VS Code | Diagrama |
|---|---|---|---|---|---|
| 0 | Apertura: propósito y objetivo | Marlon | 1,5 min | No | No |
| 1 | Arquitectura | Marlon | 3 min | 1 · Arquitectura | arquitectura_completa |
| 2 | Datos: ETL y almacén en estrella | Víctor | 3 min | 2 · Datos | arquitectura_completa (capa 4) |
| 3 | Modelo de abandono | Víctor | 4 min | 3 · Entrenamiento | flujo_entrenamiento |
| 4 | Evaluación, sesgos y deriva | Marlon | 3 min | 4 · Evaluación | No |
| 5 | Consulta conversacional y seguridad | Víctor | 3 min | 5 · Seguridad y consulta | flujo_pregunta y capas_seguridad |
| 6 | Frontend y flujo en vivo | Marlon | 2 min | 6 · Frontend | No |
| 7 | Pruebas y cierre | Ambos | 1,5 min | 7 · Pruebas | No |
| | **Total** | | **21 min** | | |

# Segmento 0 · Apertura (1,5 min, Marlon)

| Ventana | Qué abro | Qué muestro |
|---|---|---|
| Navegador | README del repositorio en GitHub: https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI | Banner, título del proyecto y autores |
| Navegador | Sistema en http://localhost:3000, pantalla de ingreso | Nombre VicMar, sin iniciar sesión todavía |

**Qué digo:**

> Buenas, somos Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco, de Ingeniería en Tecnologías de la Información de la UNEMI.

> Cada estudiante que entra a la universidad representa una inversión del Estado, de la institución y de su familia. Cuando abandona, esa inversión no llega a convertirse en un título ni en un profesional que aporte a la matriz productiva del país.

> El problema está medido en el Ecuador: Núñez-Naranjo, en 2024, encontró en una universidad ecuatoriana que 484 de 1.078 admitidos abandonaron, una probabilidad de abandono del 44,90 %.

> Si el abandono se anticipa, la universidad puede activar a tiempo becas, tutorías y programas de acompañamiento. Para eso construimos VicMar.

> Nuestro objetivo general es desarrollar un prototipo de sistema web que prediga el abandono de estudiantes universitarios mediante aprendizaje automático y permita consultar sus resultados en lenguaje natural, para que las autoridades y bienestar estudiantil identifiquen a tiempo a quienes están en riesgo.

> En el video mostramos la arquitectura, los datos, el modelo, su evaluación, la consulta conversacional con su seguridad, la interfaz y las pruebas.

# Segmento 1 · Arquitectura (3 min, Marlon)

**Recorrido:** **1 · Arquitectura: cliente-servidor con backend en capas** (10 pasos). **Diagrama:** `arquitectura_completa.png`.

| Ventana | Qué abro | Qué muestro |
|---|---|---|
| VS Code | `diagramas/arquitectura_completa.png` a pantalla completa | Las 5 capas: Presentación, API, Motor de consulta, Datos y Procesos por lotes; los proveedores de IA externos detrás del adaptador; Docker |
| Docker Desktop | Contenedores | `vicmar-sqlserver` en ejecución (verde) |
| VS Code | Recorrido 1, pasos 1-2 | `ARQUITECTURA.md`: estilo cliente-servidor desacoplado |
| VS Code | Recorrido 1, pasos 3-4 | `package.json` (`npm start` → `scripts/iniciar.mjs`) y `frontend/vite.config.ts` (web en el puerto 3000) |
| VS Code | Recorrido 1, pasos 5-8 | `backend/main.py` (aplicación FastAPI y sus routers), `backend/api/consulta.py`, `backend/core/db.py` |
| VS Code | Recorrido 1, paso 10 | `backend/scripts/pipeline.py`: el procesamiento por lotes (ETL, entrenamiento, calificación) fuera del ciclo de la petición |
| Navegador | http://localhost:8090/docs | La documentación OpenAPI de la API |

**Qué digo:**

> VicMar es una arquitectura cliente-servidor desacoplada. Por un lado está la interfaz, una aplicación React de una sola página en el puerto 3000. Por otro, una API REST con FastAPI en el puerto 8090, con el backend organizado en capas.

> Las capas son cinco. Presentación, que es la web. La API, con la sesión, los roles y la auditoría. El motor de consulta, que traduce preguntas a SQL. Los datos, en SQL Server con un almacén en estrella. Y los procesos por lotes: ETL, entrenamiento y calificación, que corren aparte y no frenan la consulta.

> SQL Server corre en Docker, en el contenedor `vicmar-sqlserver`. Todo el sistema se levanta con un solo comando, `npm start`.

> Elegimos este estilo con una matriz de decisión ponderada: obtuvo 4,65 sobre 5, frente a 4,40 del monolito en capas y 3,30 de los microservicios. Ganó por dos cosas: el panel y el chat leen la misma API, así que muestran las mismas cifras, y la interfaz evoluciona sin tocar el backend.

> Somos honestos: en costo de operación gana el monolito, que tiene un solo desplegable. Los microservicios no se justifican para un equipo de dos personas y una institución piloto. La decisión está en el ADR-006.

# Segmento 2 · Datos: ETL por perfil y almacén en estrella (3 min, Víctor)

**Recorrido:** **2 · Datos: ETL por perfiles y almacén en estrella** (12 pasos). **Diagrama:** `arquitectura_completa.png`, capa 4 (Datos).

| Ventana | Qué abro | Qué muestro |
|---|---|---|
| VS Code | Recorrido 2, pasos 1-3: `backend/etl/perfiles.py` | Perfil `UNEMI_PRUEBAS` (base de origen `UNEMI_PRUEBAS`) y perfil `OULAD_UK` (base `OULAD_PRUEBAS`): cada institución es solo un mapeo |
| VS Code | Recorrido 2, paso 4: `backend/mlops/calidad_datos.py` | Las 23 expectativas de calidad que se validan con Great Expectations |
| VS Code | Recorrido 2, pasos 5-6: `backend/etl/etl_academico.py` | Extracción, validación y carga al almacén |
| VS Code | Recorrido 2, pasos 7-12: `base_de_datos/crear_almacen_academico.sql` | Dimensiones `dim_*` y hechos `fact_matriculas`, `fact_prediccion_abandono`; las 8 vistas `VIS_*` con `SESSION_CONTEXT`; las cuentas `chat_reader` y `app_seguimiento` con `CHECK_POLICY = ON` |
| VS Code | `backend/ml/modelos/UNEMI_PRUEBAS/calidad_datos.json` | Resultado: 23 de 23 expectativas cumplidas en UNEMI y en OULAD; `apto_para_entrenar: true` |

**Qué digo:**

> Trabajamos con dos fuentes. UNEMI_PRUEBAS es un conjunto sintético que reproduce la estructura de la UNEMI: dos sedes, 18 carreras, 15 periodos, 14.508 estudiantes y 79.268 registros. OULAD es un conjunto real y anonimizado de la Open University del Reino Unido, con 28.785 estudiantes y 189.299 registros.

> Lo importante es que el modelo y la IA nunca tocan las bases operativas. El ETL lee la base de origen, valida y carga un almacén en estrella al estilo Kimball: dimensiones de alumno, carrera, periodo, sede y modalidad, y tablas de hechos de matrícula y de predicción.

> Cada institución entra con un perfil de mapeo en `perfiles.py`. Así incorporamos OULAD: con un perfil nuevo, el mismo ETL y el mismo modelo.

> Encima del almacén hay ocho vistas `VIS_*`. Todas filtran por `SESSION_CONTEXT`, la institución activa que fija la API a partir del token del usuario. Sin contexto, la vista devuelve cero filas: falla cerrada.

> La calidad la comprobamos con Great Expectations sobre la trayectoria ya cargada: 23 expectativas de integridad, dominio, rango y volumen. UNEMI y OULAD cumplen las 23, y el resultado queda en `calidad_datos.json`. Si una expectativa crítica fallara, el pipeline avisa que no conviene entrenar.

# Segmento 3 · Modelo de abandono (4 min, Víctor)

**Recorrido:** **3 · Entrenamiento del modelo de abandono** (15 pasos). **Diagrama:** `flujo_entrenamiento.png` (12 pasos).

| Ventana | Qué abro | Qué muestro |
|---|---|---|
| VS Code | `diagramas/flujo_entrenamiento.png` | Del almacén al modelo: panel sin fuga, partición temporal, CV agrupada, 4 candidatos, Platt, umbrales, MLflow |
| VS Code | Recorrido 3, pasos 1-5: `backend/ml/caracteristicas.py` | Panel estudiante-periodo; las variables solo usan información hasta el cierre del periodo t; la etiqueta es el abandono en t+1 |
| VS Code | Recorrido 3, pasos 6-13: `backend/ml/entrenar.py` | `particion_temporal`, validación cruzada agrupada por estudiante, los 4 candidatos, `ajustar_lgbm` (Optuna, TPE), calibración y `umbral_para_recall` |
| VS Code | `backend/ml/modelos/UNEMI_PRUEBAS/metricas.json` | Bloques `hiperparametros.LIGHTGBM`, `comparacion_cv` y `umbrales` |
| VS Code | Recorrido 3, pasos 14-15: `backend/ml/entrenar.py` y `backend/mlops/registro_mlflow.py` | El registro de cada entrenamiento en MLflow |
| Navegador | MLflow en http://127.0.0.1:5000 | El experimento de cada institución con la corrida del entrenamiento y la de monitoreo |

**Qué digo:**

> El modelo responde una pregunta concreta: con lo que sabemos al cerrar este periodo, ¿abandonará el estudiante en el siguiente?

> Por eso armamos un panel estudiante-periodo sin fuga de información: cada fila solo usa datos hasta el cierre del periodo. En UNEMI son 64.760 filas etiquetadas, con una prevalencia de abandono de 6,58 %, y 41 variables de trayectoria, cartera, matrícula, aula virtual y evaluaciones.

> La partición es temporal: entrenamos con los periodos antiguos y probamos con los tres más recientes, 2024-2, 2025-1 y 2025-2, que el modelo nunca vio. Dentro del entrenamiento usamos validación cruzada de cinco pliegues agrupada por estudiante, para que el mismo alumno no quede en entrenamiento y prueba a la vez.

> Comparamos cuatro candidatos: regresión logística, Random Forest con pesos por clase, Random Forest con SMOTE y LightGBM. En validación cruzada, LightGBM obtuvo un ROC-AUC de 0,828 con desviación de 0,003; Random Forest ponderado, 0,821; la logística, 0,819, y SMOTE, 0,816.

> LightGBM se ajustó con Optuna, con 25 pruebas registradas. Los hiperparámetros finales en UNEMI son 300 árboles, tasa de aprendizaje de 0,0136, 8 hojas y un mínimo de 317 muestras por hoja: un modelo poco profundo, que generaliza.

> Luego calibramos con Platt sobre predicciones fuera de pliegue, para que la probabilidad se pueda leer como probabilidad. Y fijamos dos umbrales por recall: el medio, 0,0396, busca detectar el 80 % de los abandonos; el alto, 0,1795, el 50 %.

> Cada entrenamiento queda registrado en MLflow con sus parámetros, métricas y artefactos, y el monitoreo agrega su propia corrida. Si MLflow no está instalado, el entrenamiento sigue y lo informa.

# Segmento 4 · Evaluación, sesgos y deriva (3 min, Marlon)

**Recorrido:** **4 · Evaluación: métricas, sesgos, explicación y deriva** (11 pasos). **Diagrama:** ninguno.

| Ventana | Qué abro | Qué muestro |
|---|---|---|
| Navegador | Sistema, página **Calidad del modelo** (`/modelo`) con `admin.ti` | Curvas ROC, PR y calibración; tablas por periodo, por carrera y de origen móvil; calidad de datos y deriva |
| VS Code | Recorrido 4, pasos 1-3: `backend/ml/entrenar.py` | Métricas temporales y equidad por grupo |
| VS Code | Recorrido 4, pasos 4-5: `backend/ml/evaluacion_grupos.py` y el bloque `por_periodo` de `modelos/OULAD_UK/metricas.json` | Métricas por periodo y carrera, origen móvil y la caída de OULAD en 2014J |
| VS Code | Recorrido 4, pasos 6-8: `backend/ml/explicacion.py`, `calificar.py` | SHAP (TreeSHAP) e importancia por permutación |
| VS Code | Recorrido 4, paso 9: `backend/mlops/deriva.py`, `modelos/*/deriva.json` y `monitoreo.json` | Evidently y el PSI propio |
| Navegador | `backend/ml/modelos/<INSTITUCION>/deriva_evidently.html` (se genera con `python -m mlops.validar`) | Informe de deriva de Evidently |

**Qué digo:**

> El indicador principal es el ROC-AUC en la prueba temporal. En UNEMI es 0,829 y en OULAD, 0,768. El PR-AUC, que es más exigente con clases desbalanceadas, es 0,466 en UNEMI y 0,104 en OULAD, frente a prevalencias de 6,5 % y 3,1 %.

> En la práctica importa la captura: revisando el 10 % de estudiantes con más riesgo, la universidad encuentra el 54,7 % de los abandonos en UNEMI y el 34,8 % en OULAD. Con el 20 %, 67,9 % y 55,4 %.

> Con el umbral medio, el recall en UNEMI es 78,1 %. La calibración funciona: el Brier baja de 0,134 sin calibrar a 0,046 calibrado.

> Por periodo, UNEMI es estable: 0,827 en 2024-2, 0,825 en 2025-1 y 0,836 en 2025-2; con origen móvil, entrenando solo con el pasado, el ROC-AUC va de 0,827 a 0,836 en cuatro periodos. En OULAD encontramos un hallazgo: 0,779 en 2014B y baja a 0,740 en 2014J. No lo ocultamos: es el periodo más lejano del entrenamiento y con otra prevalencia, y por eso existe el monitoreo.

> Las variables de más peso en UNEMI son el promedio del periodo y el número de matrícula, seguidas del porcentaje de evaluaciones entregadas y el saldo pendiente. En OULAD pesan el promedio relativo a la cohorte, los días sin actividad y el corte. Cada ficha muestra, con SHAP, cuánto empuja cada variable el riesgo de ese estudiante.

> Revisamos sesgos. En UNEMI, el ROC-AUC es 0,829 para mujeres y para hombres; por modalidad va de 0,818 en híbrida a 0,837 en línea, y por sede, 0,817 en Durán y 0,832 en Milagro. En OULAD hay una brecha por género: 0,748 frente a 0,778, y la reportamos.

> Para la deriva calculamos el PSI de cada variable. En UNEMI todas están estables. En OULAD hay cuatro con deriva, por ejemplo días sin actividad con 0,44, que se explica porque los activos están en los primeros cortes de la presentación. Evidently, con sus propias pruebas estadísticas, marca 6 de 38 variables en UNEMI y 16 de 33 en OULAD; en ninguno de los dos el conjunto se considera con deriva.

> Las limitaciones son claras: los datos de UNEMI son sintéticos, no hubo piloto con usuarios reales y OULAD tiene una prevalencia baja, por eso su PR-AUC es bajo.

# Segmento 5 · Consulta conversacional y seguridad (3 min, Víctor)

**Recorrido:** **5 · Seguridad y consulta en lenguaje natural** (17 pasos). **Diagramas:** `flujo_pregunta.png` (14 controles numerados) y `capas_seguridad.png`.

| Ventana | Qué abro | Qué muestro |
|---|---|---|
| VS Code | `diagramas/flujo_pregunta.png` | El camino de una pregunta por carriles y los 14 controles |
| VS Code | Recorrido 5, pasos 1-4: `backend/api/sesion.py`, `backend/core/seguridad.py` | 5 intentos fallidos → 429; `CAPACIDADES_POR_ROL` (AUTORIDAD, BIENESTAR, ADMIN_TI) |
| VS Code | Recorrido 5, pasos 5-6: `backend/core/db.py` | `Encrypt=yes` y `sp_set_session_context` antes de cada SELECT |
| VS Code | Recorrido 5, pasos 7-8: `core/privacidad.py`, `core/auditoria.py` | `depurar_texto`, `filas_para_ia`; registro `INTERPRETACION` |
| VS Code | Recorrido 5, pasos 9-12: `nl2sql/motor.py`, `guardarrailes.py`, `enrutador.py`, `generador.py` | Barrera de intención; ruta certificada (40 métricas, umbral 0,56) |
| VS Code | Recorrido 5, paso 14: `nl2sql/proveedores.py` | `completar`: la cascada Gemini, Groq, NVIDIA NIM, DeepSeek |
| VS Code | Recorrido 5, paso 15: `nl2sql/validador.py` | Árbol sqlglot: solo SELECT, nodos y funciones prohibidas, límite de 500 filas |
| VS Code | Recorrido 5, pasos 16-17: `motor.py`, `redactor.py` | `cifras_no_respaldadas` |
| VS Code | `diagramas/capas_seguridad.png` | Defensa en profundidad: interfaz, API, motor y base de datos, con auditoría y LOPDP transversales |

**Qué digo:**

> Una pregunta en español atraviesa varias barreras. Primero, la sesión y el rol: el token define quién es y a qué institución pertenece, y tras cinco intentos fallidos el ingreso se bloquea cinco minutos.

> Después, una barrera de intención descarta lo que no es una consulta de datos. Si la pregunta coincide con una de las 40 métricas certificadas, se responde con SQL fijo y parametrizado, sin IA.

> Solo si no hay métrica certificada, se pide el SQL a un proveedor de IA. Antes de enviar la pregunta, `depurar_texto` reemplaza cédulas y nombres. Al proveedor se le manda el esquema de las vistas, nunca filas de datos ni credenciales.

> El SQL que vuelve no se ejecuta a ciegas. El validador lo analiza con sqlglot como árbol: solo acepta SELECT, rechaza INSERT, DELETE, DROP y funciones como `xp_` u `openrowset`, y pone un límite de 500 filas.

> ¿Por qué la IA no puede borrar ni exponer datos? Por tres capas a la vez. El validador solo deja pasar lecturas. La cuenta `chat_reader` solo tiene permiso SELECT sobre las ocho vistas, no sobre las tablas. Y las vistas filtran por la institución que fija la API, no el usuario. Aunque el proveedor alucine, el peor caso es una consulta rechazada.

> Si se pide interpretar el resultado, `filas_para_ia` envía como máximo 25 filas seudonimizadas, cada envío queda en la bitácora como `INTERPRETACION` y, si la respuesta cita cifras que no están en el resultado, se descarta.

> La conexión a SQL Server va cifrada con `Encrypt=yes`, y las cuentas `chat_reader` y `app_seguimiento` tienen mínimo privilegio y política de contraseñas activa. Esto aplica los principios de la LOPDP que documentamos en el gobierno de datos.

> En la evaluación con 40 preguntas de referencia, la exactitud por ejecución fue 100 % y la estricta 65 %; las 8 preguntas maliciosas quedaron contenidas y hubo 0 fugas entre instituciones.

> Los proveedores son intercambiables: todos usan una API compatible con OpenAI, y `proveedores.py` es el adaptador. Mañana se puede conectar un modelo más potente con solo una clave y una entrada de configuración, sin cambiar el diseño.

# Segmento 6 · Frontend y flujo en vivo (2 min, Marlon)

**Recorrido:** **6 · Frontend: React por rol** (10 pasos). **Diagrama:** ninguno.

| Ventana | Qué abro | Qué muestro |
|---|---|---|
| VS Code | Recorrido 6, pasos 1-4: `frontend/src/lib/api.ts`, `lib/sesion.tsx`, `App.tsx` | Cliente hacia la API con el token; rutas por rol (`/panel`, `/estudiantes`, `/estudiantes/:token`, `/seguimiento`, `/consulta`, `/carreras`, `/modelo`, `/admin/...`) |
| Navegador | Ingreso con `bienestar.demo` | Panel institucional con la distribución de riesgo |
| Navegador | **Estudiantes** → un estudiante de riesgo ALTO | Ficha con la cédula enmascarada, la probabilidad y las razones (SHAP) |
| Navegador | Simulador «¿qué pasaría si…?» de la ficha | Cambiar, por ejemplo, la asistencia y ver cómo cambia el riesgo |
| Navegador | Registrar intervención | Guardar una tutoría y verla en **Seguimiento** |
| Navegador | **Consulta** | Preguntar: «¿Cuántos estudiantes tienen riesgo alto por carrera?» |

**Qué digo:**

> La interfaz es React con TypeScript. Cada pantalla se muestra según las capacidades del rol: autoridad consulta, bienestar además simula y registra intervenciones, y administración de TI gestiona cuentas, auditoría y estado.

> Entro como bienestar estudiantil. En el panel veo la distribución del riesgo de los 7.158 estudiantes activos calificados de UNEMI: 564 en alto, 2.019 en medio y 4.575 en bajo.

> Abro un estudiante de riesgo alto. La cédula aparece enmascarada y la ficha explica por qué está en riesgo: qué variables empujan su probabilidad hacia arriba.

> Con el simulador pruebo qué pasaría si mejora su asistencia. Y registro la intervención, que queda en el seguimiento para medir después su efecto.

> Por último, la consulta conversacional: pregunto en español y obtengo la tabla, con la indicación de si vino de una métrica certificada.

# Segmento 7 · Pruebas y cierre (1,5 min, ambos)

**Recorrido:** **7 · Pruebas e integración continua** (12 pasos). **Diagrama:** ninguno.

| Ventana | Qué abro | Qué muestro |
|---|---|---|
| VS Code | Terminal integrada | `cd backend; venv\Scripts\python.exe -m pytest -q` → sin base de datos, 219 aprobadas y 9 omitidas; con SQL Server encendido se ejecutan además las 8 de integración (comprobarlo en el ensayo) |
| VS Code | Terminal integrada | `cd frontend; npm test` → 11 pruebas en 3 archivos |
| VS Code | Recorrido 7 | `test_caracteristicas.py` (sin fuga), `test_mlops.py` (origen móvil), `test_validador.py`, `test_guardarrailes.py`, `test_privacidad_ia.py`, `test_conexion_cifrada.py`, `test_integracion_bd.py`, `.github/workflows/ci.yml` |
| Navegador | Pestaña **Actions** del repositorio | Flujo `CI`: «Backend · pytest» y «Frontend · vitest + build» |

**Qué digo (Víctor):**

> El backend tiene 228 pruebas: 219 pasan sin base de datos, 8 de integración se ejecutan con SQL Server encendido y una se omite si MLflow no está instalado. El frontend tiene 11. Hay pruebas de que no hay fuga temporal, del validador de SQL, de las barreras, de la privacidad hacia la IA, del canal cifrado y de integración contra SQL Server. Todo corre en GitHub Actions en cada cambio.

**Qué digo (Marlon):**

> Cerramos por objetivo. Primero, analizamos los procesos y las variables: 41 variables en cinco grupos. Segundo, construimos un modelo calibrado y explicable: ROC-AUC temporal de 0,829 en UNEMI y 0,768 en OULAD, con Brier de 0,046 y 0,029. Tercero, implementamos el sistema web por roles, con panel, ficha, segmentación y consulta. Cuarto, lo evaluamos: 100 % de exactitud por ejecución en la consulta, 8 de 8 preguntas maliciosas contenidas y 0 fugas entre instituciones.

> El código está en el repositorio de GitHub que ven en pantalla. Muchas gracias.

# Anexo A · Antes de grabar

**1. Tener la última versión del código.** En PowerShell, en la raíz del repositorio (`C:\Tesis Marlon Y Victor` o la carpeta donde se clonó):

```
git status
git stash            # solo si git status muestra cambios locales
git fetch origin
git checkout main    # o: git checkout pruebas, según indique el equipo
git pull
```

- Sin el proyecto en la computadora: `git clone https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI.git`.
- Nunca borrar el contenedor ni sus volúmenes: allí están las bases.

**2. Abrir Docker Desktop.**

```
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

- Si no arranca por sockets dañados (suele pasar tras un apagado brusco): cerrar Docker Desktop por completo y **renombrar** (no borrar) `%LOCALAPPDATA%\Docker\run` y `%LOCALAPPDATA%\docker-secrets-engine`, por ejemplo agregando `_viejo` al nombre; luego volver a abrir Docker Desktop.
- **Nunca** usar «Reset to factory defaults»: borra el contenedor y sus bases.

**3. Encender SQL Server y el sistema.**

```
docker start vicmar-sqlserver
npm start
```

- `npm start` ejecuta `scripts/iniciar.mjs` (equivale a doble clic en `iniciar.bat`): instala lo que falte, arranca el contenedor y levanta la API en http://localhost:8090 (documentación en `/docs`) y la web en http://localhost:3000.
- Alternativa en dos ventanas: `scripts\levantar_sistema.bat`. Si el panel dice que no hay estudiantes calificados: `scripts\reconstruir_sistema.bat --desde entrenar`.

**4. Abrir MLflow** (en otra terminal):

```
cd backend
venv\Scripts\mlflow ui --backend-store-uri sqlite:///datos_locales/mlflow/mlflow.db
```

Abrir http://127.0.0.1:5000 y dejar visible el experimento de UNEMI_PRUEBAS. Si está vacío, `venv\Scripts\python -m mlops.validar --institucion UNEMI_PRUEBAS` registra la corrida de monitoreo sin reentrenar.

**5. Usuarios de prueba.** Las cuentas `autoridad.demo`, `bienestar.demo` y `admin.ti` tienen contraseñas aleatorias guardadas solo en `backend/datos_locales/usuarios_demo.local.json`, que no se versiona. Abrir ese archivo antes de grabar, fuera de cámara. Para regenerarlas: `cd backend` y `venv\Scripts\python -m scripts.crear_usuarios_demo --restablecer`. Las contraseñas nunca se muestran en el video.

**6. VS Code.**
- Abrir `VicMar.code-workspace` (letra de 19 pt en el editor y 16 pt en la terminal, minimapa apagado).
- Instalar la extensión recomendada **CodeTour** si VS Code la sugiere.
- Comprobar que en el Explorador aparece **CODETOUR** con los 7 recorridos; probar que cada uno abre la línea correcta.
- Dejar abiertos los cuatro PNG de `14_VIDEO_TECNICO/diagramas/` y una terminal integrada en la raíz.

**7. Pestañas del navegador, en este orden:** README en GitHub; http://localhost:3000 (ingreso); http://localhost:8090/docs; http://127.0.0.1:5000 (MLflow); el informe HTML de Evidently; la pestaña **Actions** del repositorio.

**8. Ensayo del flujo en vivo (segmento 6).** Con `bienestar.demo`, elegir de antemano un estudiante de riesgo ALTO, probar el simulador y anotar la pregunta de la consulta. Registrar la intervención de prueba en el ensayo solo si se acepta que quede en el seguimiento.

**9. Grabación.** Notificaciones de Windows apagadas (modo «No molestar»), correo y mensajería cerrados, micrófono probado. Ensayo completo cronometrado: el objetivo es 21 minutos; si pasa de 24, recortar los «Qué digo» del segmento 4.

# Anexo B · Si algo falla durante la grabación

| Síntoma | Acción |
|---|---|
| Docker Desktop no arranca | Renombrar `%LOCALAPPDATA%\Docker\run` y `%LOCALAPPDATA%\docker-secrets-engine` (ver anexo A). Nunca reset de fábrica |
| La API no responde o se queda «Esperando a que SQL Server acepte conexiones» | `docker ps`; `docker start vicmar-sqlserver`; revisar `DB_HOST` en `backend/.env` |
| Puerto 3000 u 8090 ocupado | Cerrar la otra instancia; si no, cambiar el puerto en `frontend/vite.config.ts` o en `PUERTO_API` |
| El panel dice «Todavía no hay estudiantes calificados» | `scripts\reconstruir_sistema.bat --desde entrenar` (antes de grabar, no durante) |
| La consulta dice que ningún proveedor de IA está disponible | Usar una pregunta de métrica certificada, que no necesita IA, y explicarlo como parte del diseño |
| Error 429 al iniciar sesión | Esperar cinco minutos (es el freno de intentos) o usar otra cuenta de prueba |
| MLflow no abre | Revisar que se ejecutó desde `backend` y que `mlflow` está instalado (`requirements.txt`); plan B: mostrar `ml/modelos/<INSTITUCION>/mlflow_registro.json` |
| CodeTour no aparece | Abrir los archivos a mano con Ctrl+P y la línea con Ctrl+G |
| Cualquier pantalla del sistema falla | Plan B: capturas en `documentacion/capturas/` (`av2_cap_panel.png`, `av2_cap_estudiantes.png`, `av2_cap_ficha.png`, `av2_cap_seguimiento.png`, `av2_cap_consulta.png`, `av2_cap_calidad.png`, `av2_cap_auditoria.png`) |

# Anexo C · Diez preguntas probables del tribunal

1. **¿Por qué no obtienen 0,99 como otros estudios?** Porque evaluamos sin fuga: el panel solo usa datos hasta el cierre del periodo, la prueba es temporal (periodos que el modelo no vio) y la validación cruzada está agrupada por estudiante. Una partición aleatoria mezcla al mismo alumno en entrenamiento y prueba e infla la cifra. Nuestro 0,829 es lo que se espera en uso real, y la validación con origen móvil lo confirma periodo a periodo. Fuente: `metricas.json`, `test_caracteristicas.py`.
2. **¿Sirven unos datos sintéticos?** Prueban que el sistema funciona de punta a punta con la estructura de la UNEMI. Para la validez externa usamos OULAD, un conjunto real, con ROC-AUC 0,768. Antes de usarlo con decisiones reales hace falta reentrenar con datos de la UNEMI; lo declaramos como limitación.
3. **¿El modelo tiene sesgos?** Lo medimos por género, modalidad y sede. En UNEMI no hay diferencia por género en ROC-AUC (0,8293 en ambos). En OULAD hay una brecha (0,748 mujeres y 0,778 hombres) que reportamos. Fuente: bloque `equidad` de `metricas.json`.
4. **¿Qué pasa si el LLM alucina?** El SQL pasa por el validador sqlglot (solo SELECT), se ejecuta con `chat_reader` (solo lectura de vistas) y la vista filtra por institución. Si la interpretación cita cifras que no están en el resultado, `cifras_no_respaldadas` la descarta. Las 8 preguntas maliciosas quedaron contenidas.
5. **¿Cómo se cumple la LOPDP?** Minimización y seudonimización (cédula enmascarada, token cifrado), control de acceso por rol, aislamiento por institución, canal cifrado, bitácora y reglas para la transferencia a proveedores (arts. 34 y 55 a 57). Fuente: `documentacion/gobierno_datos/GOBIERNO_DE_DATOS.md` y `documentacion/tecnica/GOBIERNO_DE_DATOS_LOPDP.md`.
6. **¿Por qué LightGBM?** Ganó la matriz de decisión del ADR-005 con 4,65, frente a 4,30 del Random Forest ponderado, 3,75 de la logística y 2,70 de SMOTE, y tuvo el mejor ROC-AUC en validación cruzada (0,828 ± 0,003). La logística es más simple de explicar; por eso la ficha usa SHAP.
7. **¿Cómo se reentrena?** `cd backend` y `venv\Scripts\python -m ml.entrenar --institucion UNEMI_PRUEBAS`, o el pipeline completo con `scripts\reconstruir_sistema.bat --desde entrenar`. El PSI de `monitoreo.json`, la deriva de Evidently (`deriva.json`) y la calidad de datos (`calidad_datos.json`) avisan cuándo hace falta.
8. **¿Cómo se escala a otra universidad?** Con un perfil de mapeo en `backend/etl/perfiles.py`: así entró OULAD, sin cambiar el ETL ni el modelo. Cada institución queda aislada por `SESSION_CONTEXT`.
9. **¿Y Metabase?** Lo dejamos como alternativa de inteligencia de negocios clásica: se conecta con la cuenta `metabase_lector`, que solo lee el esquema `bi` (datos agregados, sin identificadores personales) y tiene denegado `dbo`. No reemplaza al chat, porque no aplica el contexto de institución que fija la API. Fuente: `documentacion/tecnica/METABASE_ALTERNATIVA_DE_CONSULTA.md` y `base_de_datos/crear_vistas_metabase.sql`.
10. **¿Cuánto cuesta?** Corre en un equipo local con SQL Server en Docker y herramientas de código abierto (FastAPI, React, LightGBM). Las métricas certificadas no usan IA; los proveedores se intentan en cascada empezando por los gratuitos, y sin claves el chat sigue respondiendo las métricas certificadas.

# Anexo D · Versión de 5 minutos (demostración en la sustentación)

| Min | Quién | Qué se muestra | Qué se dice |
|---|---|---|---|
| 0:00-0:40 | Marlon | `arquitectura_completa.png` | Problema (44,90 %, Núñez-Naranjo, 2024), objetivo y arquitectura cliente-servidor (4,65) |
| 0:40-1:40 | Víctor | `flujo_entrenamiento.png` y MLflow | Panel sin fuga, prueba temporal, LightGBM con Optuna y Platt; ROC-AUC 0,829 UNEMI y 0,768 OULAD |
| 1:40-3:20 | Marlon | Sistema con `bienestar.demo`: panel → ficha → simulador → intervención | Riesgo explicado y acción registrada |
| 3:20-4:20 | Víctor | Consulta conversacional y `capas_seguridad.png` | Ruta certificada, validador, `chat_reader`; 100 % por ejecución, 8/8 maliciosas, 0 fugas |
| 4:20-5:00 | Ambos | Terminal con pytest y Actions | 228 + 11 pruebas; cierre por objetivo |

# Anexo E · Dónde está cada cifra

| Cifra | Valor | Archivo |
|---|---|---|
| Abandono en una universidad ecuatoriana | 44,90 % (484 de 1.078) | Núñez-Naranjo (2024), citado en el trabajo final (`documentacion/avances/TRABAJO_FINAL_MARLON_VICTOR.docx`) |
| Matriz de arquitectura | 4,65 / 4,40 / 3,30 | `documentacion/decisiones/adr/ADR-006-estilo_de_arquitectura_del_sistema.md` |
| Matriz del algoritmo | 4,65 / 4,30 / 3,75 / 2,70 | `documentacion/decisiones/adr/ADR-005-algoritmo_del_modelo_predictivo_de_aband.md` |
| Registros y estudiantes UNEMI | 79.268 y 14.508; 15 periodos, 18 carreras | `backend/ml/modelos/UNEMI_PRUEBAS/exploracion.json` |
| Registros y estudiantes OULAD | 189.299 y 28.785 | `backend/ml/modelos/OULAD_UK/exploracion.json` |
| Filas etiquetadas y prevalencia UNEMI | 64.760; 6,58 % | `UNEMI_PRUEBAS/metricas.json` → `panel` |
| Variables | 41 UNEMI, 37 OULAD | `metricas.json` → `n_variables` |
| ROC-AUC en CV (LightGBM, RF ponderado, logística, SMOTE) UNEMI | 0,8280 ± 0,0034; 0,8214; 0,8188; 0,8164 | `UNEMI_PRUEBAS/metricas.json` → `comparacion_cv` |
| ROC-AUC en CV OULAD (LightGBM) | 0,8043 ± 0,0115 | `OULAD_UK/metricas.json` → `comparacion_cv` |
| Pruebas de Optuna registradas | 25 | `metricas.json` → `busqueda.LIGHTGBM` |
| Hiperparámetros LightGBM UNEMI | 300 árboles; 0,0136; 8 hojas; 317 | `UNEMI_PRUEBAS/metricas.json` → `hiperparametros.LIGHTGBM` |
| Umbrales UNEMI (medio, alto) | 0,0396; 0,1795 (recall objetivo 0,8 y 0,5) | `UNEMI_PRUEBAS/metricas.json` → `umbrales` |
| ROC-AUC temporal | 0,8293 UNEMI; 0,7682 OULAD | `metricas.json` → `validacion_temporal.roc_auc` |
| PR-AUC temporal | 0,4656 UNEMI; 0,1037 OULAD | `metricas.json` → `validacion_temporal.pr_auc` |
| Brier sin calibrar y calibrado | 0,1337 → 0,0455 UNEMI; 0,1921 → 0,0287 OULAD | `metricas.json` → `validacion_temporal` |
| Captura top 10 % y 20 % | 54,65 % y 67,87 % UNEMI; 34,84 % y 55,44 % OULAD | `metricas.json` → `captura_top_10`, `captura_top_20` |
| Recall con umbral medio UNEMI | 78,1 % | `metricas.json` → `validacion_temporal.umbral_medio` |
| ROC-AUC por periodo UNEMI | 0,8274; 0,8248; 0,8359 | `UNEMI_PRUEBAS/metricas.json` → `por_periodo` |
| ROC-AUC con origen móvil UNEMI | 0,8357; 0,8274; 0,8270; 0,8349 (media 0,8313) | `UNEMI_PRUEBAS/metricas.json` → `origen_movil` |
| ROC-AUC por periodo OULAD | 2014B 0,7791; 2014J 0,7395 | `OULAD_UK/metricas.json` → `por_periodo` |
| Equidad UNEMI (género, modalidad, sede) | F 0,8293 / M 0,8293; 0,8182-0,8366; Durán 0,8174 / Milagro 0,8320 | `UNEMI_PRUEBAS/metricas.json` → `equidad` |
| Equidad OULAD por género | F 0,7478 / M 0,7782 | `OULAD_UK/metricas.json` → `equidad` |
| Variables de más peso | UNEMI: promedio_t, numero_matricula; OULAD: promedio_rel_cohorte, dias_sin_actividad | `metricas.json` → `importancia_permutacion` |
| PSI OULAD dias_sin_actividad | 0,4417 (DERIVA) | `OULAD_UK/monitoreo.json` |
| Distribución del riesgo UNEMI | 7.158 calificados: 560 alto, 2.024 medio, 4.574 bajo | `UNEMI_PRUEBAS/monitoreo.json` |
| Evaluación prospectiva OULAD | ROC-AUC 0,7635 (2014J, y siguiente) | `OULAD_UK/prospectiva.json` |
| Consulta: exactitud por ejecución y estricta | 100 %; 65 % (40 preguntas) | `backend/eval/resultados/consulta_UNEMI_PRUEBAS_20261007_2005.json` |
| Preguntas maliciosas y fugas | 8/8 contenidas; 0 violaciones | mismo archivo |
| Métricas certificadas y umbral | 40; 0,56 | `backend/nl2sql/catalogo_metricas.json`; `backend/nl2sql/enrutador.py` |
| Límite de filas del validador | 500 | `backend/nl2sql/validador.py` |
| Bloqueo de ingreso | 5 intentos → 429 por 5 minutos | `backend/api/sesion.py` |
| Great Expectations | 23 expectativas; UNEMI 23/23; OULAD 23/23 | `ml/modelos/<INSTITUCION>/calidad_datos.json` |
| Evidently (variables con deriva) | UNEMI 6 de 38; OULAD 16 de 33; conjunto estable en ambos | `ml/modelos/<INSTITUCION>/deriva.json` |
| Pruebas | 228 backend (219 sin base de datos, 8 de integración con SQL Server, 1 requiere MLflow); 11 frontend | `cd backend; venv\Scripts\python.exe -m pytest -q`; `cd frontend; npm test` |
