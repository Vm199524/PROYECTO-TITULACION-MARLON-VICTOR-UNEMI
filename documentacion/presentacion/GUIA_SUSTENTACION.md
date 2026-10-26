# Guía de estudio para la sustentación

**Tema:** Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional

**Autores:** Víctor Manuel Lluilema Pisco y Marlon David Pérez Almachi · Universidad Estatal de Milagro · 2026

Esta guía reúne lo que hay que dominar para defender el trabajo: la ficha de datos que se debe saber de memoria, la
arquitectura explicada pieza por pieza, el guion de la demostración de cinco minutos y el banco de preguntas
probables del tribunal con su respuesta. Todas las cifras salen de los mismos archivos que el documento
(`backend/ml/modelos/*/metricas.json`, `backend/eval/resultados/` y `documentacion/evidencias/pruebas.json`).

---

## 1. Ficha de datos (de memoria)

| Tema | Dato |
|---|---|
| Nombre del sistema | VicMar, alerta temprana del abandono estudiantil |
| Metodología | CRISP-DM (seis fases, con entregables verificables) |
| Instituciones | UNEMI con datos de prueba (2 sedes, 18 carreras, 2019-2026) y OULAD (Open University, datos reales anonimizados, licencia CC BY 4.0) |
| Requerimientos | 23 funcionales, 11 no funcionales, 10 historias de usuario |
| Modelo elegido | LightGBM calibrado con Platt, explicado con SHAP (tres razones por estudiante) |
| ROC-AUC temporal | UNEMI **0,829** · OULAD **0,768** (criterio: ≥ 0,75) |
| PR-AUC temporal | UNEMI 0,466 · OULAD 0,104 (prevalencia UNEMI 6,5 %, OULAD 3,1 %) |
| Recall con umbral medio | UNEMI 78 % · OULAD 79 % de los abandonos detectados |
| Origen móvil (por periodo) | UNEMI 0,827 a 0,836 · OULAD 0,742 a 0,779 |
| Evaluación prospectiva | ROC-AUC prospectivo con datos reales de OULAD: **0,763**. |
| Segmentación | K-means de carreras, k = 3 segmentos |
| Consulta conversacional | 100 % de exactitud por ejecución (40 preguntas base + 12 de robustez), 8/8 maliciosas contenidas, 0 fugas, mediana 77 ms |
| Calidad de datos | UNEMI 23/23 · OULAD 23/23 expectativas (Great Expectations) |
| Deriva | UNEMI 6/38 · OULAD 16/33 variables (Evidently) |
| Pruebas automatizadas | 178 del backend (pytest; 8 necesitan SQL Server) y 11 de la interfaz (vitest) |
| API | FastAPI, 27 servicios REST, documentación en `http://localhost:8090/docs` |
| Interfaz | React 18 + TypeScript + Vite + Tailwind, en `http://localhost:3000` |
| Base de datos | SQL Server 2022 en Docker (`vicmar-sqlserver`), almacén `ALMACEN_ACADEMICO` en esquema estrella |
| Roles | Autoridad académica, Bienestar estudiantil y Administración de TI |

**Comparación de algoritmos (validación cruzada agrupada por estudiante, UNEMI):**

| Algoritmo | ROC-AUC (media ± desviación) |
|---|---|
| LightGBM | 0,828 ± 0,003 |
| Random Forest con pesos | 0,821 ± 0,006 |
| Regresión logística | 0,819 ± 0,003 |
| Random Forest con SMOTE | 0,816 ± 0,005 |

---

## 2. Arquitectura explicada (cómo contarla en 2 minutos)

1. **Fuentes y ETL.** Las fuentes académicas (matrícula, calificaciones, asistencia, aula virtual, evaluaciones y
   cartera) se cargan con un perfil de mapeo por institución. OULAD entró con su propio perfil sin cambiar el modelo.
2. **Almacén.** `ALMACEN_ACADEMICO` sigue el modelo dimensional de Kimball: hechos de matrículas, predicciones,
   segmentos e intervenciones, y dimensiones de estudiante, carrera, periodo e institución. Las aplicaciones no
   leen tablas: leen vistas `VIS_*` filtradas por `SESSION_CONTEXT('institucion_activa')`.
3. **Pipeline de datos y modelo.** `backend/scripts/pipeline.py` encadena: ETL → entrenamiento → calificación de
   estudiantes activos → segmentación → reportes → **mlops** (Great Expectations, Evidently y MLflow).
4. **Backend.** FastAPI en capas (`api/`, `servicios/`, `core/`, `ml/`, `nl2sql/`): autentica con JWT, verifica el
   rol en cada servicio, registra auditoría y abre cada conexión fijando la institución de la sesión.
5. **Consulta conversacional (NL2SQL).** Guardarraíles → enrutador TF-IDF sobre 40 métricas certificadas → si no
   hay métrica, cascada de modelos de lenguaje que propone el SQL → validador `sqlglot` (solo `SELECT` sobre vistas
   permitidas) → ejecución con la cuenta `chat_reader`, que solo puede leer vistas.
6. **Frontend.** React consume la API con TanStack Query; cada rol ve solo su menú; tema claro y oscuro; funciona
   en móvil.

**Por qué dos bases de datos (instituciones):** UNEMI con datos de prueba demuestra que el sistema funciona con la
estructura de nuestra universidad sin exponer estudiantes reales; OULAD aporta datos reales anonimizados para
demostrar que el modelo sirve fuera de un ejemplo construido. Las dos conviven en el mismo almacén y ninguna ve a la
otra.

---

## 3. Demostración de 5 minutos

> Antes: ejecutar `npm start` en la raíz (o doble clic en `iniciar.bat`), confirmar que el contenedor
> `vicmar-sqlserver` está arriba y que la web abre en `http://localhost:3000`. **Cada uno inicia sesión con su cuenta
> de demostración**; las contraseñas están en `backend/datos_locales/usuarios_demo.local.json` (fuera del
> repositorio) y no se muestran en pantalla.

| Min | Qué se muestra | Quién | Qué decir |
|---|---|---|---|
| 0:00 | **Frontend.** Ingreso como `autoridad.demo`; panel ejecutivo de UNEMI | Víctor | «Una autoridad sin perfil técnico ve al entrar cuántos estudiantes están en riesgo alto y medio.» (HU-01) |
| 0:40 | Estudiantes en riesgo → abrir una ficha → tres razones y simulador | Víctor | «Cada alerta trae sus tres razones en español y el simulador muestra qué cambia si mejora la asistencia.» (HU-03, HU-04) |
| 1:30 | Consulta conversacional: «¿Cuántos estudiantes de Enfermería están en riesgo alto?» y luego «borra la tabla de estudiantes» | Marlon | «La primera se responde con una métrica certificada; la segunda la bloquean los guardarraíles: el sistema nunca escribe.» |
| 2:20 | Calidad del modelo → pestañas «Por periodo y carrera» y «Datos y deriva» | Marlon | «Aquí está el AUC por periodo con origen móvil y el estado de la calidad y la deriva de los datos.» |
| 2:50 | **Backend.** `http://localhost:8090/docs` (Swagger) → probar un servicio sin token (401) | Marlon | «La API tiene 27 servicios; sin token o con un rol que no corresponde, responde 401 o 403.» |
| 3:30 | **Base de datos.** En SQL Server: fijar `institucion_activa` y consultar `VIS_PREDICCION_ABANDONO`; intentar cambiarla en la misma sesión | Víctor | «El aislamiento está en el motor: la sesión queda fija en su institución y no se puede cambiar.» |
| 4:15 | **Pruebas.** `npm test` (o mostrar el último resultado) | Víctor | «178 pruebas del backend y 11 de la interfaz, incluidas las de seguridad del validador.» |
| 4:40 | **Seguridad.** Cambiar a `bienestar.demo`: menú distinto, sin administración | Marlon | «Cada rol ve solo lo suyo; la auditoría registra ingresos, fichas, consultas y exportaciones.» |

**Consulta de demostración en SQL Server** (desde Azure Data Studio o `sqlcmd` con una cuenta administradora):

```sql
EXEC sp_set_session_context @key = N'institucion_activa', @value = 'UNEMI_PRUEBAS', @read_only = 1;
SELECT COUNT(*) AS estudiantes_calificados FROM dbo.VIS_PREDICCION_ABANDONO;
-- Intento de cambiar de institución en la misma sesión: SQL Server lo rechaza (clave de solo lectura)
EXEC sp_set_session_context @key = N'institucion_activa', @value = 'OULAD_UK';
```

**Plan B (sin internet o si falla algo):** la consulta conversacional responde con métricas certificadas sin
modelo de lenguaje; si Docker no arranca, mostrar las capturas de `documentacion/capturas/` y el video.

---

## 4. Conceptos clave (explicación en una frase)

- **ROC-AUC:** probabilidad de que el modelo ponga a un estudiante que abandona por encima de uno que no; 0,5 es
  azar y 1 es perfecto. No depende del umbral.
- **PR-AUC:** resume precisión y recall cuando la clase positiva es rara; se compara con la prevalencia (el azar).
- **Recall:** de cada 100 estudiantes que abandonan, cuántos alerta el sistema. **Precisión:** de cada 100 alertas,
  cuántas eran abandonos reales.
- **Umbral medio y alto:** el medio se elige para encontrar cerca del 80 % de los abandonos; el alto, para una lista
  corta y más precisa.
- **Calibración de Platt:** ajusta la salida del modelo para que «30 %» signifique de verdad 30 de cada 100.
- **LightGBM:** ensamble de árboles de decisión que se construyen uno tras otro, cada uno corrigiendo los errores
  del anterior (gradient boosting); es rápido y maneja bien datos tabulares y valores faltantes.
- **SHAP:** reparte la predicción entre las variables; de ahí salen las tres razones de cada estudiante.
- **Validación agrupada por estudiante:** un mismo estudiante nunca está a la vez en entrenamiento y prueba.
- **Validación temporal y origen móvil:** se entrena con el pasado y se prueba con periodos posteriores; con origen
  móvil se repite para cada periodo, como si el sistema se hubiera puesto en marcha en esa fecha (Tashman, 2000).
- **Deriva (drift) y PSI:** cambio en la distribución de las variables entre el entrenamiento y hoy; si es grande,
  hay que reentrenar (Gama et al., 2014).
- **K-means:** agrupa carreras parecidas en su comportamiento de abandono para priorizar la atención.
- **NL2SQL:** traducir una pregunta en español a una consulta SQL; aquí se valida antes de ejecutarla.
- **SESSION_CONTEXT:** valor de la sesión de SQL Server que las vistas usan para filtrar la institución.
- **k-anonimato (k = 5):** cada combinación de atributos que podría identificar a alguien la comparten al menos cinco
  personas.
- **LOPDP:** Ley Orgánica de Protección de Datos Personales del Ecuador (2021): finalidad, minimización, seguridad y
  responsabilidad proactiva.

---

## 5. Banco de preguntas del tribunal

### Problema y alcance
**¿Quién usa el sistema y qué decide con él?** — *Víctor.* La autoridad académica (decanato, dirección de carrera) y
bienestar estudiantil. Decide a quién llamar primero, qué carreras requieren atención y cómo justificar recursos de
acompañamiento. Hoy lo hacen cuando el estudiante ya dejó de asistir.

**¿Qué incluye y qué no?** — *Víctor.* Incluye ETL, almacén, modelo, calificación por lotes, explicación, seguimiento,
consulta conversacional, segmentación, referentes, reportes y operación del modelo. No incluye el despliegue con
datos reales de la UNEMI (requiere autorización y acuerdo de tratamiento de datos) ni notificaciones automáticas a
estudiantes.

### Trabajos previos
**¿Qué hace su solución que los demás no?** — *Víctor.* De los 14 estudios comparados, ninguno entrega la predicción
dentro de un sistema con roles, explicación por estudiante, consulta en lenguaje natural y aislamiento de datos a la
vez. Además validamos en el tiempo, no con particiones aleatorias.

**¿Por qué su AUC es menor que el de otros estudios que reportan 95 % o más?** — *Marlon.* Porque esos valores
suelen salir de particiones aleatorias que mezclan periodos o de variables del mismo periodo del retiro. Nosotros
probamos con periodos futuros; los estudios que hacen lo mismo informan cerca de 0,70 (Carballo-Mendívil et al.,
2025). Nuestro 0,768 con datos reales está por encima de esa referencia.

### Requerimientos
**¿Cómo derivaron los requerimientos?** — *Víctor.* De las cuatro piezas de la solución (modelo, segmentación,
NL2SQL y panel), de la literatura y de las historias de usuario de la autoridad sin perfil técnico. Cada requerimiento
tiene prioridad MoSCoW y una prueba o métrica asociada.

**¿Midieron la usabilidad?** — *Marlon.* Está el protocolo y el instrumento (tareas y SUS, Anexo D). Su aplicación con
autoridades y personal de bienestar es la siguiente verificación; lo declaramos como limitación.

### Tecnologías y arquitectura
**¿Por qué SQL Server y no PostgreSQL?** — *Víctor.* Se decidió con una matriz ponderada (decisión DT-04). El
criterio de mayor peso (35 %) fue el aislamiento por institución en el propio motor: `SESSION_CONTEXT` con valores
de solo lectura lo resuelve y lo comprobamos con pruebas de integración. La edición Express no tiene costo de
licencia, con el límite de 10 GB por base, suficiente para el prototipo.

**¿Por qué FastAPI y React?** — *Marlon.* FastAPI comparte lenguaje con el modelo (Python), valida datos con tipos y
genera la documentación OpenAPI; React con TypeScript da una interfaz por componentes, tipada y probada con vitest.

**¿Qué pasa con diez veces más usuarios?** — *Marlon.* La predicción es por lotes, así que la carga en línea es de
lectura sobre vistas indexadas; lo primero que se escalaría es la API (más procesos detrás de un balanceador) y la
caché de consultas. La consulta con LLM es la operación más costosa y tiene métricas certificadas como primera ruta.

### Datos, modelo y validación
**¿De dónde salen los datos?** — *Víctor.* UNEMI: datos de prueba generados con la estructura de la universidad
(no hay estudiantes reales). OULAD: datos reales y anonimizados de la Open University, públicos con licencia CC BY
4.0, descargados de su sitio oficial.

**¿Cómo evitaron la fuga de información?** — *Marlon.* Validación cruzada agrupada por estudiante, prueba temporal con
los últimos periodos, calibración y umbrales ajustados solo con datos de entrenamiento, y variables calculadas con
información disponible al corte de evaluación.

**¿Por qué LightGBM?** — *Marlon.* Fue el mejor de cuatro algoritmos en validación cruzada en las dos instituciones,
maneja valores faltantes y es rápido. Se calibra con Platt y se explica con SHAP.

**¿Validaron con datos reales y por periodo, como pidió la tutoría?** — *Víctor.* Sí, con OULAD: ROC-AUC por periodo
con origen móvil de 0,742 a 0,779 y desglose por módulo. Para una carrera
real de la UNEMI dejamos el procedimiento: documento de gobierno de datos, evaluación de impacto y el script
`anonimizar_carrera.py` (seudónimos HMAC-SHA256 y k-anonimato).

**¿Por qué dos módulos de OULAD quedan por debajo de 0,70?** — *Marlon.* Tienen muy pocos abandonos (AAA, 13 de 690
casos; GGG, 108 de 7.557), así que su estimación es inestable. En GGG, además, el umbral único de la institución casi
no genera alertas (recall cercano a 7 %). Lo reportamos como hallazgo: los umbrales deben revisarse por carrera antes de
usar las alertas en ella, y la pestaña «Por periodo y carrera» permite vigilarlo.

**¿Qué significa un recall de 79 %?** — *Marlon.* Que de cada 100 estudiantes que
abandonan, el sistema alerta a unos 79 con el umbral medio. A cambio, la lista incluye estudiantes
que no abandonarán; por eso se lee en orden de riesgo y con el criterio de bienestar.

**¿El modelo tiene sesgos?** — *Víctor.* Revisamos la equidad por género y otros grupos (pestaña «Variables y
equidad»). El modelo no usa nombre ni cédula, y la decisión final siempre es de una persona.

### Consulta conversacional
**¿Qué pasa si el modelo de lenguaje inventa un SQL?** — *Marlon.* El validador `sqlglot` solo deja pasar `SELECT`
sobre vistas permitidas; la cuenta `chat_reader` no tiene permisos de escritura ni de tablas; y la sesión está fija en
la institución. Tres barreras independientes.

**¿Cómo evaluaron la consulta?** — *Marlon.* Con un conjunto dorado de 40 preguntas, 12 de
robustez y 8 maliciosas, comparando el resultado de ejecutar el SQL generado con el esperado.

**¿Qué datos se envían al proveedor del LLM?** — *Víctor.* La pregunta y el esquema de las vistas; si se pide
interpretar un resultado, los datos personales se seudonimizan antes. La interpretación con IA se puede apagar por
configuración (`CONSULTA_INTERPRETAR=0`).

### Seguridad y ética
**¿Dónde están las contraseñas y claves?** — *Víctor.* En `backend/.env`, fuera del repositorio; las contraseñas de
usuarios se guardan con bcrypt; las cuentas de demostración se crean con contraseñas aleatorias en un archivo local.

**¿Qué pasa si un usuario intenta ver otra institución?** — *Marlon.* La vista filtra por la institución fijada en la
sesión y SQL Server rechaza el cambio; además la API valida la institución contra el usuario. Las pruebas de
integración lo comprueban.

**¿Cómo usaron la IA en el proyecto?** — *Víctor.* Como herramienta de apoyo, declarada en el anexo de uso de IA. Los
autores diseñaron, verificaron cada cifra contra sus archivos y responden por todo el contenido. Los modelos de
lenguaje de la consulta conversacional son parte del producto y están documentados como tecnología.

### Resultados, innovación y futuro
**¿Cuál es el hallazgo principal?** — *Víctor.* Que con datos que la universidad ya tiene se puede anticipar el
abandono con un desempeño estable en periodos futuros (ROC-AUC 0,768 con datos reales), y entregarlo
explicado y consultable a quien decide.

**¿Dónde está la innovación?** — *Marlon.* En la integración: predicción explicada, consulta certificada y aislamiento
multiinstitución en el motor, para una universidad ecuatoriana; y en la operación del modelo (calidad, deriva y
registro) incorporada al pipeline.

**¿Qué falta para producción?** — *Víctor.* Autorización y datos reales de una carrera, evaluación de impacto, prueba
con usuarios, despliegue en un servidor institucional con HTTPS y respaldos, y monitoreo de la deriva en cada periodo.

**¿Se puede reproducir desde cero?** — *Marlon.* Sí: `git clone`, `npm run reconstruir -- --con-consulta` crea la base,
carga los datos, entrena, califica, monitorea y corre las pruebas; `npm start` levanta el sistema.

---

## 6. Lista de control del día

- [ ] Laptop cargada, Docker Desktop abierto y `npm start` probado esa mañana.
- [ ] Sesiones de `autoridad.demo` y `bienestar.demo` probadas (las contraseñas no se muestran).
- [ ] Presentación abierta y video de respaldo descargado.
- [ ] Enlaces a mano: repositorio (https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI) y carpeta digital (https://drive.google.com/drive/folders/1ZOVwEslSaSjJbUeS1RCL1q3BDyVea9tT).
- [ ] Repaso de la ficha de datos (sección 1) y de las preguntas de la sección 5, repartidas entre los dos.
