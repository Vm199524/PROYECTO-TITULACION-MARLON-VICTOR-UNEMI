# Gobierno de datos y protección de datos personales (LOPDP)

**Proyecto:** Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional (VicMar, versión 3)
**Institución:** Universidad Estatal de Milagro (UNEMI), Ecuador
**Versión:** 1.1
**Fecha:** 26/10/2026
**Autores:** Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco

---

## 0. Fuente legal y método de verificación

| Elemento | Detalle |
|---|---|
| Norma | Ley Orgánica de Protección de Datos Personales (LOPDP), Registro Oficial Suplemento 459, 26 de mayo de 2021 |
| Texto verificado | PDF `ley_organica_de_proteccion_de_datos_personales.pdf` (39 páginas), edición Lexis Finder que reproduce el texto del R. O. Suplemento 459; encabezado «Estado: Vigente». Consultado el 25/10/2026. Es una edición editorial, por lo que no se redistribuye en el repositorio: la copia de trabajo está en la carpeta local `_MATERIAL_EXTERNO_NO_SUBIR/normativa/` |
| Ficha oficial | Portal de regulaciones del Gobierno del Ecuador: https://www.gob.ec/regulaciones/ley-organica-proteccion-datos-personales (consultado el 25/10/2026). Confirma la suscripción (10/05/2021), la publicación (26/05/2021) y el número de registro (R. O. 459) |
| Criterio | Cada artículo citado en este documento se contrastó con el texto del PDF. La referencia «p.» corresponde a la página de esa edición |

No se analiza aquí el Reglamento General de la LOPDP. Las resoluciones de la Superintendencia de Protección de Datos Personales sobre gestión de riesgos (SPDP-SPD-2025-0003-R) y sobre inteligencia artificial (SPDP-SPD-2026-0009-R) se tratan en la política de gobierno de datos del proyecto, `documentacion/gobierno_datos/GOBIERNO_DE_DATOS.md` (anexo C del trabajo final), que este documento complementa con el análisis artículo por artículo.

---

## 1. Propósito y alcance

Este documento establece las reglas de gobierno de los datos que trata VicMar y la forma en que el prototipo aplica la LOPDP. VicMar estima el riesgo de abandono de cada estudiante activo para apoyar la alerta temprana y el acompañamiento de bienestar estudiantil. También responde preguntas en lenguaje natural sobre los datos académicos.

**Datos del prototipo.** El prototipo funciona con dos instituciones de prueba:

| Código | Origen | Naturaleza |
|---|---|---|
| `UNEMI_PRUEBAS` | Dataset sintético (`base_de_datos/datos_de_prueba/`) | Valores académicos y financieros simulados. Las cédulas, apellidos y nombres se reemplazaron por valores ficticios con `anonimizar_padron.py` (sección 6.4) |
| `OULAD_UK` | Open University Learning Analytics Dataset (Kuzilek et al., 2017), licencia CC BY 4.0 | Datos reales publicados ya anonimizados. El identificador es `OU<id_student>` y el apellido es genérico (`backend/scripts/cargar_oulad.py`) |

El artículo 2, literal c, excluye del ámbito de la ley los «datos anonimizados, en tanto no sea posible identificar a su titular» (p. 5). Por eso, en el estado actual, el prototipo no trata datos personales de estudiantes reales. Aun así, el sistema está diseñado para una institución real: los controles descritos se aplican desde el diseño y por defecto (art. 39, p. 21), y la sección 15 enumera lo que falta antes de cargar datos reales.

**Fuera de alcance:** los sistemas académicos de origen de la institución (matrícula, notas, aula virtual) y su gobierno propio.

---

## 2. Marco legal

### 2.1 Definiciones aplicables (art. 4, pp. 6-7)

| Término | Aplicación en VicMar |
|---|---|
| Dato personal | Cédula, nombres y apellidos, y todo dato vinculado a ellos (trayectoria, predicción, seguimiento) |
| Elaboración de perfiles | La ley la define como el tratamiento que permite «evaluar, analizar o predecir aspectos de una persona natural», incluido el rendimiento. La predicción de riesgo de abandono es elaboración de perfiles |
| Seudonimización | Tratamiento con el que los datos ya no pueden atribuirse al titular sin información adicional guardada por separado. Es lo que se aplica antes de enviar filas a un proveedor de IA |
| Anonimización | Medidas para impedir la identificación o reidentificación sin esfuerzos desproporcionados. Es lo que se aplica al dataset de prueba |
| Responsable / encargado | El responsable decide la finalidad y el tratamiento. El encargado trata datos «a nombre y por cuenta» del responsable |
| Datos sensibles | La lista incluye salud, etnia e identidad de género, entre otros, y una cláusula abierta: datos «cuyo tratamiento indebido pueda dar origen a discriminación» |
| Vulneración de la seguridad | Incidente que afecta la confidencialidad, disponibilidad o integridad de los datos |

### 2.2 Principios (art. 10, pp. 9-11) y cómo se reflejan

| Principio | Reflejo en el sistema |
|---|---|
| c) Transparencia | Factores explicativos visibles en la ficha. El aviso al titular está pendiente (sección 15) |
| d) Finalidad | Uso único: alerta temprana y acompañamiento (sección 5) |
| e) Pertinencia y minimización | Vistas `VIS_*` con columnas acotadas, cédula enmascarada y seudonimización hacia la IA (sección 6) |
| f) Proporcionalidad | Las variables financieras y de aula virtual son opcionales por institución |
| g) Confidencialidad | Control por rol y aislamiento por institución (sección 7) |
| h) Calidad y exactitud | Carga desde la fuente institucional por ETL. La rectificación se hace en el origen (sección 10) |
| i) Conservación | Plazos propuestos en la sección 11 |
| j) Seguridad | Sección 9 |
| k) Responsabilidad proactiva y demostrada | Bitácora de auditoría, este documento y su revisión periódica (sección 14) |

### 2.3 Otros artículos de referencia

| Tema | Artículo (página) |
|---|---|
| Bases de legitimación | Art. 7 (p. 8); consentimiento, art. 8 (pp. 8-9); interés legítimo, art. 9 (p. 9) |
| Derechos del titular | Arts. 12 a 20 (pp. 11-15); arts. 21 y 24 para adolescentes (pp. 15-16) |
| Categorías especiales | Art. 25 (p. 16): datos sensibles, datos de niñas, niños y adolescentes, datos de salud y datos de personas con discapacidad. Datos sensibles, art. 26 (p. 16) |
| Transferencia y encargo | Arts. 33, 34 y 36 (pp. 18-20); transferencia internacional, arts. 55 a 57 (pp. 26-27) |
| Seguridad | Arts. 37 y 39 a 41 (pp. 20-21) |
| Evaluación de impacto | Art. 42 (pp. 21-22) |
| Vulneraciones | Arts. 43 y 46 (pp. 22-23) |
| Obligaciones y delegado | Arts. 47 a 50 (pp. 23-25) |
| Registro Nacional | Art. 51 (p. 25) |
| Requerimientos y reclamos | Arts. 62 y 64 (p. 29) |
| Vigencia | Disposición transitoria primera: el régimen sancionatorio entró en vigencia dos años después de la publicación (p. 35). Disposición general séptima: los derechos pueden exigirse con independencia del régimen sancionatorio (p. 35) |

---

## 3. Roles

| Rol LOPDP | Quién, en un despliegue real | Rol en VicMar | Responsabilidades principales |
|---|---|---|---|
| Responsable del tratamiento (art. 4) | La institución de educación superior | — | Decide la finalidad, aprueba esta política, atiende los derechos y cumple las obligaciones del art. 47 |
| Encargado del tratamiento (arts. 4 y 34) | Proveedor de alojamiento o soporte; proveedores de IA si reciben datos personales; el equipo desarrollador durante un piloto | — | Tratar los datos solo según las instrucciones del responsable, bajo contrato (art. 34). Notificar vulneraciones al responsable en dos días (art. 43) |
| Titulares (art. 4) | Estudiantes; también el personal usuario (cuentas y bitácora) | — | Ejercer los derechos de los arts. 12 a 20 |
| Administración de TI | Departamento de TI | `ADMIN_TI` | Cuentas, bitácora, estado de procesos, credenciales y respaldo |
| Autoridades académicas | Decanato, dirección de carrera, vicerrectorado | `AUTORIDAD` | Consulta para decisiones de gestión. No registran seguimiento |
| Bienestar estudiantil | Bienestar y tutoría | `BIENESTAR` | Atender alertas, usar el simulador y registrar el seguimiento |
| Delegado de protección de datos (DPD) (arts. 48 a 50) | Designado por la institución | — | Asesorar, supervisar, revisar la evaluación de impacto y actuar como punto de contacto con la Autoridad (art. 49) |

**Delegado de protección de datos.** El artículo 48, numeral 1, exige designar un DPD cuando el tratamiento lo realizan entidades del sector público según el artículo 225 de la Constitución, como es el caso de una universidad pública (p. 24). En otro caso, se recomienda designarlo igualmente, porque el tratamiento implica elaboración de perfiles. El titular puede contactar al DPD para ejercer sus derechos (art. 50, num. 6, p. 25).

---

## 4. Inventario y clasificación de los datos

Fuente del esquema: `base_de_datos/crear_almacen_academico.sql` y `documentacion/tecnica/DICCIONARIO_DE_DATOS.md`. La columna «Base legal» remite a la sección 5. Los plazos de retención son una propuesta que debe aprobar el responsable.

| Dato | Finalidad | Base legal | Sensibilidad | Dónde se guarda | Quién accede | Retención propuesta |
|---|---|---|---|---|---|---|
| Cédula | Vincular la trayectoria y evitar duplicados | Art. 7 num. 4 u 8 | Identificador directo | `dim_alumno.cedula` | Los tres roles la ven enmascarada (`******1234`). La API usa un token cifrado | Mientras la trayectoria esté abierta, más un año |
| Apellidos y nombres | Identificar a quién acompañar | Ídem | Identificador directo | `dim_alumno` | Los tres roles (lista, ficha, seguimiento) | Ídem |
| Género | Evaluar la equidad del modelo (`ml/entrenar.py`, función `equidad`). No es variable predictora | Ídem | Riesgo de discriminación (cláusula abierta del art. 4) | `dim_alumno.genero` | Los tres roles (ficha) | Ídem |
| Ciudad de residencia | Contexto descriptivo. No es variable del modelo | Ídem | Ubicación | `dim_alumno` | Los tres roles (`VIS_ALUMNO`) | Evaluar su eliminación por minimización |
| Trayectoria académica (carrera, sede, modalidad, periodo, nivel, estado, promedio, asistencia, créditos, número de matrícula) | Variables del modelo y del panel | Ídem | Personal | `fact_matriculas` | Los tres roles | Las cohortes necesarias para entrenar (por ejemplo, cinco años); después, solo agregados |
| Datos económicos (monto de matrícula, beca, saldo pendiente) | Variables opcionales del modelo | Ídem | Personal económico, de mayor cuidado | `fact_matriculas` (`NULL` si la institución no los registra) | Los tres roles | Ídem |
| Aula virtual y evaluaciones | Variables opcionales del modelo | Ídem | Personal (comportamiento) | `fact_matriculas` | Los tres roles | Ídem |
| Predicción (probabilidad, categoría, percentil, tres factores, contribuciones SHAP, vector de características) | Alerta temprana. Es un perfil (art. 4) | Ídem | Dato inferido; perfil | `fact_prediccion_abandono` (se reemplaza en cada calificación: `ml/calificar.py`, `guardar`) | Los tres roles. El simulador, solo `BIENESTAR` y `ADMIN_TI` | Solo la vigente. El historial, únicamente agregado |
| Registro de seguimiento (tipo, descripción, resultado, usuario que registra) | Acompañamiento y evaluación de la intervención | Ídem | Personal. El texto libre puede contener datos sensibles | `fact_intervencion` | Lectura: los tres roles. Escritura: `BIENESTAR` y `ADMIN_TI` | Mientras el estudiante esté activo, más un año; después, anonimizar |
| Cuentas del personal (usuario, nombre, correo, rol, instituciones, hash bcrypt, último acceso) | Control de acceso | Art. 7 num. 4 o 5 | Personal; credencial | `backend/datos_locales/usuarios.json` (excluido del repositorio) | `ADMIN_TI` | Hasta la baja de la cuenta |
| Bitácora (fecha, acción, usuario, institución, resultado, IP, detalle con cédula enmascarada) | Seguridad y responsabilidad proactiva | Art. 7 num. 4 u 8 | Personal (personal usuario) | `backend/datos_locales/auditoria.jsonl` | `ADMIN_TI` | Dos años |
| Preguntas del chat y resultado | Responder la consulta | Ídem | Puede contener datos personales | Memoria del servidor, una hora (`nl2sql/motor.py`, `_guardar_resultado`). La bitácora guarda solo la intención, la métrica y la huella del SQL | El usuario que pregunta | Una hora (implementado) |
| Agregados (segmentos por carrera, métricas del modelo, referentes externos) | Gestión y confianza en el modelo | No aplica | Sin datos personales | `fact_segmento_carrera`, `fact_evaluacion_modelo`, `fact_referente_externo` | Los tres roles | Indefinida |

**Categorías especiales.** El esquema no incluye datos de salud, etnia ni discapacidad. Si la institución tiene estudiantes menores de 18 años, sus datos son una categoría especial (art. 25, lit. b, p. 16). El artículo 21 (p. 15) exige además autorización expresa o un interés público esencial con salvaguardas. Los adolescentes desde los 15 años pueden consentir (art. 21) y ejercer sus derechos directamente (art. 24, p. 16).

---

## 5. Base legal y finalidad del tratamiento

**Finalidad única:** identificar con anticipación a los estudiantes con riesgo de abandono para ofrecerles acompañamiento (tutoría, consejería, apoyo económico, contacto o derivación) y medir el resultado de ese acompañamiento. Cualquier otro uso es un fin distinto (art. 10, lit. d). Esto incluye admisión, sanciones, asignación o retiro de becas y evaluación docente.

**Base de legitimación (art. 7, p. 8):**

- **Universidad pública:** el numeral 4 permite el tratamiento para el «cumplimiento de una misión realizada en interés público o en el ejercicio de poderes públicos» derivados de una competencia atribuida por una norma con rango de ley. El área jurídica de la institución debe identificar la competencia concreta en la normativa de educación superior.
- **Universidad privada:** el numeral 8, interés legítimo, sujeto al artículo 9. Solo pueden tratarse los datos estrictamente necesarios y el tratamiento debe ser transparente.
- **Datos opcionales sin base suficiente:** el consentimiento (numeral 1; art. 8). Puede revocarse en cualquier momento.

**Decisiones automatizadas (art. 20, pp. 14-15).** El titular tiene derecho a no ser sometido a una decisión «basada única o parcialmente» en valoraciones automatizadas, incluida la elaboración de perfiles, que produzca efectos jurídicos o atente contra sus derechos. Puede pedir una explicación motivada, presentar observaciones, solicitar los criterios de valoración y los tipos de datos usados, e impugnar la decisión. Como la ley menciona también las decisiones *parcialmente* automatizadas, la regla de gobierno es la siguiente: **la predicción solo prioriza ofertas de apoyo y nunca se usa para decisiones con efectos jurídicos o restrictivos sobre el estudiante.** Lo implementado que respalda esta regla:

- La IA no escribe datos. La cuenta `chat_reader` es de solo lectura, y el registro de seguimiento lo hace una persona con rol `BIENESTAR` o `ADMIN_TI` mediante `app_seguimiento` (`api/seguimiento.py`, función `registrar`). El comentario del esquema de `fact_intervencion` lo indica: «La IA nunca escribe aquí».
- La ficha muestra los factores y las contribuciones SHAP de cada predicción (`api/estudiantes.py`, `ficha`). Esto permite cumplir el art. 20, literales a, c y d.
- El simulador advierte que el resultado es una «Estimación del modelo predictivo; no garantiza que la intervención produzca ese efecto» (`api/estudiantes.py`, `simular`).

El art. 12, numeral 17, obliga además a informar al titular sobre la existencia de valoraciones automatizadas y de elaboración de perfiles (p. 11).

---

## 6. Minimización, seudonimización y enmascaramiento (implementado)

| Control | Implementación |
|---|---|
| Vistas gobernadas | Las lecturas de la API usan solo las vistas `VIS_*`, con columnas seleccionadas. Las tablas físicas no se exponen (`crear_almacen_academico.sql`) |
| Cédula enmascarada en pantalla, reportes y exportaciones | `core/privacidad.py`: `enmascarar_cedula` deja visibles los cuatro últimos dígitos. `enmascarar_para_pantalla` se aplica a las respuestas del chat (`nl2sql/motor.py`, `responder`) y `enmascarar_cedula`, a los reportes (`api/reportes.py`, `_datos`) |
| Token opaco en lugar de la cédula | `token_estudiante` y `cedula_desde_token` (Fernet: AES-128-CBC con HMAC-SHA256; llave derivada del secreto del servidor). Validez de 24 horas. La cédula no viaja en direcciones URL ni en registros |
| Seudonimización hacia la IA | `seudonimizar` reemplaza las columnas personales (cédula, nombres, apellidos, correo, teléfono, dirección…) por «Estudiante N» y oculta los números de 10 o 13 dígitos dentro de textos. La detección de columnas está en `es_columna_personal` |
| Detalle técnico fuera del chat | `VIS_PREDICCION_DETALLE` no figura en el esquema del chat (`nl2sql/esquema.py`, `VISTAS`), así que el validador rechaza cualquier SQL que la lea (`nl2sql/validador.py`, `validar`) |
| Variables opcionales | Si una institución no registra un grupo de variables, quedan en `NULL` y el modelo no las usa (`ml/caracteristicas.py`) |
| Límite de filas | El validador agrega `TOP 500` a las consultas sin límite (`LIMITE_FILAS`) |

### 6.4 Anonimización del dataset de prueba

El dataset sintético de UNEMI tomó inicialmente cédulas y nombres de un padrón público, con el resto de columnas simuladas. Así se atribuían abandono y mora inventados a personas identificables. `base_de_datos/datos_de_prueba/anonimizar_padron.py` (`main`) corrige esto:

- Reemplaza la cédula por una ficticia con código de provincia «00», que el Registro Civil no asigna (`cedula_ficticia`). También reemplaza nombres y apellidos por combinaciones genéricas.
- Aplica la misma correspondencia en `historial_matriculas.csv`, por lo que no cambia ninguna métrica.
- No guarda la tabla de correspondencia, porque permitiría revertir la anonimización.

Al 25/10/2026, las 14 508 filas de `alumnos_prueba.csv` tienen cédulas con prefijo «00», y la versión registrada en el repositorio también está anonimizada.

---

## 7. Control de acceso por rol y aislamiento por institución (implementado)

**Aplicación (`core/seguridad.py`).**

- Las contraseñas se guardan con bcrypt (`hash_clave`, `verificar_clave`).
- El token de sesión es un JWT firmado con vencimiento (`crear_token`; 480 minutos por defecto).
- En cada petición, `sesion_actual` valida el JWT y vuelve a consultar la cuenta: si se desactiva, el token deja de servir.
- La institución pedida en la cabecera `X-Institucion` debe estar entre las asignadas al usuario; de lo contrario, la respuesta es 403.
- La dependencia `requiere` exige la capacidad de la acción. La autorización real ocurre en el servidor, no en la interfaz.

| Capacidad | AUTORIDAD | BIENESTAR | ADMIN_TI |
|---|:-:|:-:|:-:|
| Panel, estudiantes, ficha, carreras, referentes, consulta, exportar, ver seguimiento | Sí | Sí | Sí |
| Ver modelo | Sí | — | Sí |
| Simular, registrar seguimiento | — | Sí | Sí |
| Administrar usuarios, ver auditoría, ver estado, ver SQL | — | — | Sí |

**Otros controles de la aplicación.**

- Freno de fuerza bruta: cinco intentos fallidos por usuario e IP bloquean cinco minutos (`api/sesion.py`, `ingresar`).
- No se puede eliminar ni desactivar la última cuenta `ADMIN_TI` activa (`core/usuarios.py`, `eliminar`; `api/admin.py`).
- El token del navegador se guarda en `sessionStorage` (`frontend/src/lib/api.ts`).

**Base de datos (`crear_almacen_academico.sql`, `core/db.py`).**

1. Cada vista `VIS_*` filtra por `SESSION_CONTEXT(N'institucion_activa')`. Sin institución en la sesión, no devuelve filas (falla cerrada).
2. `_conexion_con_contexto` fija la institución en la misma conexión con `@read_only = 1`, de modo que ninguna sentencia posterior puede cambiarla.
3. `chat_reader` solo tiene `SELECT` sobre las vistas y se le retira `db_datareader`. Atiende todas las lecturas de la API y del chat. Si no está configurada, la lectura se rechaza y nunca se usa la cuenta de administración en su lugar.
4. `app_seguimiento` solo puede ejecutar `sp_registrar_intervencion` y `sp_cerrar_intervencion`. Ambos procedimientos toman la institución de `SESSION_CONTEXT`, no de un parámetro, y rechazan estudiantes de otra institución.
5. Se revoca `CONNECT` a `guest` en las bases operativas `UNEMI_PRUEBAS` y `OULAD_PRUEBAS`.
6. La cuenta de administración (`DB_USER`) solo la usan los procesos por lotes.

**Consulta conversacional.** Se aplican cuatro barreras independientes: intención (`nl2sql/guardarrailes.py`, `clasificar`: escritura, inyección, otra institución, tablas físicas), validación del árbol SQL (`nl2sql/validador.py`), vistas filtradas y cuenta de solo lectura. Además, el resultado guardado de una respuesta solo puede recuperarse desde la misma institución (`motor.resultado_guardado`).

---

## 8. Transferencia a proveedores de IA

**Proveedores configurables** (`core/config.py`, `proveedores_ia`): Gemini, Groq, NVIDIA NIM y DeepSeek. Se usan en cascada mediante una API compatible con OpenAI (`nl2sql/proveedores.py`, `completar`). Sin claves configuradas, las métricas certificadas siguen funcionando sin IA.

| Flujo | Qué se envía | Qué no se envía |
|---|---|---|
| Métrica certificada (`nl2sql/enrutador.py`) | Nada: SQL fijo con parámetros | — |
| Barrera de intención | Nada | — |
| Generación de SQL (`nl2sql/generador.py`, `generar`; `corregir`) | Esquema de las vistas (nombres y descripción de columnas), glosario, ejemplos certificados, la pregunta, hasta dos preguntas anteriores de la conversación y, al corregir, el SQL anterior con el mensaje de error | Filas de datos, credenciales, tokens |
| Interpretación, solo a pedido (`nl2sql/redactor.py`, `interpretar`) | La pregunta y hasta 25 filas del resultado, con la cédula ya enmascarada y las columnas personales seudonimizadas | Cédulas completas, nombres reconocidos como columna personal, `VIS_PREDICCION_DETALLE` |

Además, `cifras_no_respaldadas` descarta la interpretación si cita números que no están en el resultado.

**Marco legal.** Mientras solo se envíen datos seudonimizados, sigue habiendo tratamiento: la seudonimización no equivale a anonimización (art. 4). Si un proveedor recibe datos personales, actúa como encargado y su tratamiento debe regularse por contrato (art. 34, p. 19). Si el proveedor está en el exterior, rigen además las reglas de transferencia internacional: nivel adecuado declarado por la Autoridad (art. 56) o garantías adecuadas en un instrumento vinculante (art. 57, pp. 26-27). El titular debe ser informado de las transferencias y de sus destinatarios (art. 12, num. 10).

**Regla para un despliegue con datos reales:**

1. Por defecto, la interpretación con IA queda desactivada y el chat opera con métricas certificadas. La alternativa es un modelo alojado por la institución.
2. Si se usa un proveedor externo, se exigen: contrato de encargo (art. 34), evaluación de la transferencia internacional (arts. 55 a 57), cuentas institucionales con cláusulas de no retención y no uso para entrenamiento, y mención en el aviso de privacidad.
3. La seudonimización pasa a una lista blanca de columnas enviables, en lugar de la detección actual por nombre de columna.
4. La pregunta se depura antes de enviarla. **Implementado:** `core/privacidad.py`, `depurar_texto`, reemplaza cédulas, correos, teléfonos y nombres de estudiantes por marcadores que solo se restauran en el servidor (`nl2sql/generador.py`); lo comprueba `tests/test_privacidad_ia.py`.
5. Cada envío se registra en la bitácora. **Implementado:** evento `INTERPRETACION` (`api/consulta.py`, `interpretar`).

---

## 9. Seguridad y auditoría (implementado)

| Medida (arts. 37 y 39) | Implementación |
|---|---|
| Secretos fuera del código | `backend/.env` (excluido por `.gitignore`), con plantilla `backend/.env.example` sin valores. `core/config.py` impide arrancar en producción con la llave JWT de desarrollo (`validar_produccion`) |
| Datos locales fuera del repositorio | `.gitignore` excluye `backend/datos_locales/` (cuentas, bitácora), los modelos y predicciones por estudiante (`backend/ml/modelos/*/*.joblib`, `*.csv`), los datos OULAD y los documentos con datos personales |
| Cifrado | Hash bcrypt de contraseñas; Fernet para los tokens de estudiante; JWT firmado (HS256 por defecto). Conexión con SQL Server siempre cifrada (`core/db.py`, `_cadena`: `Encrypt=yes`); el certificado autofirmado solo se acepta si `DB_TRUST_SERVER_CERT` lo permite, por defecto en desarrollo y no en producción (`tests/test_conexion_cifrada.py`) |
| Política de contraseñas del motor | Los logins `chat_reader`, `app_seguimiento` y `metabase_lector` se crean con `CHECK_POLICY = ON` (`crear_almacen_academico.sql`, `crear_vistas_metabase.sql`) |
| Cabeceras HTTP | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` (`main.py`, `cabeceras_y_registro`). CORS restringido a orígenes configurados |
| Errores sin detalle interno | `core/db.py`, `_traducir_error` |
| Pruebas | `backend/tests/test_privacidad_seguridad.py`: enmascaramiento, seudonimización, token opaco, bcrypt, matriz de capacidades y JWT |

**Bitácora de auditoría** (`core/auditoria.py`). `registrar` añade una línea JSON por evento a `auditoria.jsonl`, en modo de solo agregado y con un candado para escrituras concurrentes. `consultar` devuelve los eventos con filtros; el acceso es por `/api/admin/auditoria` con la capacidad `ver_auditoria`. Los eventos registrados son:

- `INGRESO` (aceptado o rechazado, con IP)
- `CAMBIO_CLAVE`
- `FICHA` y `SIMULACION` (con la cédula enmascarada)
- `CONSULTA` (intención, métrica, número de filas, huella SHA-256 del SQL mediante `huella`, proveedor y tiempo; no guarda la pregunta ni los datos)
- `INTERPRETACION` (proveedor, modelo, filas enviadas, filas del resultado y huella del mensaje; resultado `OK`, `DESCARTADA` o `SIN_PROVEEDOR`)
- `EXPORTACION`
- `SEGUIMIENTO_ALTA` y `SEGUIMIENTO_CIERRE`
- `CUENTA_ALTA`, `CUENTA_CAMBIO` y `CUENTA_BAJA`

---

## 10. Derechos de los titulares y procedimiento propuesto

| Derecho | Artículo (página) | Plazo legal | Cómo se atiende en VicMar |
|---|---|---|---|
| Información | 12 (pp. 11-12) | Al recoger los datos. Si no se obtuvieron del titular, dentro de 30 días | Aviso de privacidad institucional que mencione el perfilamiento (num. 17) y los proveedores (num. 10). **Pendiente** |
| Acceso | 13 (p. 12) | 15 días; gratuito | Extracción de la ficha (trayectoria, predicción, factores, seguimiento) por `ADMIN_TI` a pedido del DPD |
| Rectificación y actualización | 14 (p. 12) | 15 días | Se corrige en el sistema académico de origen y se recarga el ETL (`etl/etl_academico.py`), que reemplaza los hechos de la institución |
| Eliminación | 15 (p. 12) | 15 días; gratuita | Baja en el origen y recarga. El registro de seguimiento se elimina o anonimiza por script administrado por TI. **No automatizado** |
| Oposición | 16 (pp. 12-13) | 15 días | Marca de exclusión de la calificación. **Pendiente** |
| Portabilidad | 17 (p. 13) | — | No procede sobre información inferida o perfiles (último inciso). Sí procede sobre los datos académicos aportados, en formato estructurado |
| Suspensión del tratamiento | 19 (p. 14) | — | Exclusión temporal mientras se verifica una impugnación de exactitud. **Pendiente** |
| No ser objeto de decisiones automatizadas | 20 (pp. 14-15) | — | Ver la sección 5. Se entrega explicación motivada, factores, tipos de datos y fuente, y vía de impugnación |
| Excepciones | 18 (pp. 13-14) | — | Por ejemplo, obligación legal o investigación científica o estadística |

**Procedimiento propuesto.**

1. El titular presenta su requerimiento por un canal físico o digital gratuito, ante el responsable o el DPD (art. 62, p. 29).
2. Se verifica su identidad. El art. 18, num. 1, excluye solicitantes que no sean el titular o su representante acreditado.
3. Se registra la solicitud y su fecha.
4. TI ejecuta la acción y la registra en la bitácora.
5. Se responde en el término de diez días del art. 62, que es el más corto aplicable. Los artículos 13 a 16 fijan quince días.
6. Si no hay respuesta o se niega la solicitud, el titular puede reclamar ante la Autoridad de Protección de Datos Personales (art. 64, p. 29).

---

## 11. Retención y eliminación

| Elemento | Lo implementado | Regla propuesta |
|---|---|---|
| Hechos de trayectoria | Se reemplazan por institución en cada carga (`etl/etl_academico.py`) | Conservar solo las cohortes necesarias para entrenar; eliminar o agregar lo demás (art. 10, lit. i) |
| Predicciones | Se borran y recalculan en cada calificación (`ml/calificar.py`, `guardar`) | Solo la vigente |
| Artefactos de modelo y CSV de predicciones | Fuera del repositorio | Borrado al reentrenar |
| Seguimiento | Sin plazo | Activo más un año; después, anonimizar |
| Bitácora | Sin rotación | Dos años; después, eliminar de forma segura |
| Caché de respuestas del chat | Una hora (`motor._guardar_resultado`) | Igual |
| Token de estudiante y JWT | 24 horas y 480 minutos | Reducir el JWT a la jornada laboral |
| Exportaciones Excel y PDF | Salen del control del sistema | Prohibir el almacenamiento en equipos personales; borrar tras su uso |

La ley exige que el responsable establezca plazos de supresión o de revisión periódica (art. 10, lit. i, p. 10) y que la eliminación haga los datos irreconocibles «de forma definitiva y segura» (art. 15).

---

## 12. Gestión de incidentes y notificación

| Paso | Responsable | Plazo |
|---|---|---|
| 1. Detección (bitácora, alertas, reporte de un usuario) | TI | Inmediato |
| 2. Contención: desactivar cuentas, rotar `JWT_SECRET_KEY` (invalida los JWT y los tokens de estudiante) y las contraseñas de `chat_reader` y `app_seguimiento` | TI | Inmediato |
| 3. Notificación del encargado al responsable | Encargado | A más tardar en dos días (art. 43, p. 22) |
| 4. Evaluación del riesgo para los titulares | DPD y TI | — |
| 5. Notificación a la Autoridad de Protección de Datos Personales y a la Agencia de Regulación y Control de las Telecomunicaciones | Responsable | Tan pronto sea posible y a más tardar en el término de cinco días desde que se tuvo constancia, salvo que sea improbable un riesgo. Si se excede, se indican los motivos (art. 43) |
| 6. Notificación a los titulares, cuando haya riesgo para sus derechos | Responsable | Sin dilación, dentro del término de tres días. Hay excepciones con calificación de la Autoridad (art. 46, pp. 22-23) |
| 7. Registro del incidente y lecciones aprendidas | DPD | Al cierre |

---

## 13. Evaluación de impacto (EIPD)

El artículo 42 (pp. 21-22) obliga a realizar una evaluación de impacto cuando sea probable un alto riesgo para los derechos del titular o cuando la Autoridad lo requiera. Es obligatoria, entre otros casos, ante una «evaluación sistemática y exhaustiva de aspectos personales» basada en tratamiento automatizado, como la elaboración de perfiles, sobre la cual se tomen decisiones con efectos jurídicos (lit. a). También lo es ante un tratamiento a gran escala de categorías especiales (lit. b). Debe efectuarse **antes** de iniciar el tratamiento.

VicMar elabora perfiles de toda la población estudiantil activa. Su regla de gobierno excluye las decisiones con efectos jurídicos, pero la frontera es delicada y podría haber menores de edad. Por eso **se exige una EIPD antes de cargar datos reales**. Debe cubrir al menos:

- el análisis de riesgos, con la metodología del art. 40 (particularidades del tratamiento, partes involucradas, categorías y volumen);
- las medidas del art. 41;
- el sesgo del modelo, a partir de los resultados de equidad por género, modalidad y sede (`ml/entrenar.py`, `equidad`);
- la transferencia a proveedores de IA.

---

## 14. Responsabilidades y revisión periódica

| Actividad | Responsable (institución) | DPD | TI | Equipo del proyecto (piloto) |
|---|:-:|:-:|:-:|:-:|
| Aprobar esta política y la base legal | A | C | I | C |
| EIPD y análisis de riesgos (arts. 40 a 42) | A | R | C | C |
| Registro Nacional de Protección de Datos (art. 47, num. 12; art. 51) | A | R | C | I |
| Cuentas, roles y revisión trimestral de accesos | I | C | R | — |
| Revisión mensual de la bitácora | I | C | R | — |
| Atención de derechos | A | R | R | — |
| Contratos con encargados y personal (art. 47, nums. 10 y 11) | A | C | I | I |
| Reentrenamiento y monitoreo de deriva y equidad | I | C | R | R |

R = realiza; A = aprueba; C = consultado; I = informado.

**Revisión.** Este documento se revisa una vez al año y también cuando ocurra alguno de estos eventos: una nueva fuente de datos o variable, un nuevo proveedor de IA, un cambio de modelo o un incidente. Así se atiende la evaluación continua de las medidas de seguridad (art. 37; art. 47, num. 3).

---

## 15. Brechas actuales y acciones para una implementación con datos reales

| # | Brecha (estado al 26/10/2026) | Evidencia | Acción |
|---|---|---|---|
| 1 | No existe aviso de privacidad ni información al titular | No hay texto de privacidad en `frontend/src` | Redactar y publicar el aviso del art. 12, con mención expresa del perfilamiento |
| 2 | Los derechos no tienen funcionalidad ni procedimiento formal | — | Implementar exclusión, oposición, suspensión y eliminación del seguimiento; adoptar el procedimiento de la sección 10 |
| 3 | La seudonimización depende del nombre de la columna. **Corregido en parte:** `filas_para_ia` ya excluye los textos libres del seguimiento y, en resultados individuales, `registrado_por` y `ciudad_residencia`; sigue pendiente pasar a una lista blanca | `core/privacidad.py`, `filas_para_ia` | Lista blanca de columnas enviables a la IA |
| 4 | ~~La pregunta y las dos anteriores se envían al proveedor sin depurar~~ **Corregido** | `core/privacidad.py`, `depurar_texto`; `nl2sql/generador.py`, `generar`; `tests/test_privacidad_ia.py` | — |
| 5 | ~~La interpretación con IA no queda en la bitácora~~ **Corregido:** evento `INTERPRETACION` | `api/consulta.py`, `interpretar` | — |
| 6 | Los proveedores de IA no tienen contrato de encargo ni garantías de transferencia internacional (se usan claves de capa gratuita) | `core/config.py` | Aplicar la regla de la sección 8 |
| 7 | ~~La conexión a SQL Server no está cifrada~~ **Corregido:** `Encrypt=yes` siempre; en producción falta instalar un certificado emitido por una autoridad de confianza y fijar `DB_TRUST_SERVER_CERT=no` | `core/db.py`, `_cadena`; `tests/test_conexion_cifrada.py` | Certificado válido en el servidor de producción |
| 8 | ~~Los logins SQL se crean con `CHECK_POLICY = OFF`~~ **Corregido:** `CHECK_POLICY = ON` | `crear_almacen_academico.sql`, `crear_vistas_metabase.sql` | — |
| 9 | La bitácora es un archivo local sin protección contra alteración ni retención | `core/auditoria.py` | Centralizarla (SIEM o tabla con permisos de solo inserción), firmar o encadenar los eventos y aplicar la retención |
| 10 | Las cuentas están en un JSON local, sin MFA; la contraseña mínima es de 8 caracteres; el freno de intentos vive en memoria | `core/usuarios.py`, `api/sesion.py` | Integrar el directorio institucional con MFA |
| 11 | La llave JWT de desarrollo se acepta si `APP_ENV` no es `production`, y la documentación `/docs` está expuesta | `core/config.py`, `main.py` | Exigir la llave siempre y desactivar `/docs` en producción |
| 12 | El texto libre del seguimiento puede recibir datos de salud u otros sensibles (art. 26) | `fact_intervencion.descripcion` | Guía de registro, tipos cerrados y revisión |
| 13 | No hay EIPD, DPD, registro en el Registro Nacional ni contratos de confidencialidad | — | Secciones 3, 13 y 14 |
| 14 | No se identifica la minoría de edad | `dim_alumno` | Marca de menor de 18 años y tratamiento según los arts. 21 y 25 |
| 15 | No hay retención automatizada | — | Tareas programadas de supresión (sección 11) |
| 16 | Las exportaciones contienen nombres | `api/reportes.py`, `api/consulta.py` | Marca de agua y registro del destinatario; limitar a `BIENESTAR` |
| 17 | Falta verificar que las bases SQL Server se recargaron después de la anonimización del dataset | — | Recargar con `reconstruir_sistema.bat` y comprobar el prefijo «00» de las cédulas |
| 18 | No se revisó el Reglamento General de la LOPDP; las resoluciones de la Superintendencia se recogen en `gobierno_datos/GOBIERNO_DE_DATOS.md` | — | Revisión jurídica antes del piloto |

---

## 16. Referencias

Asamblea Nacional del Ecuador. (2021). *Ley Orgánica de Protección de Datos Personales*. Registro Oficial Suplemento 459, 26 de mayo de 2021. https://www.gob.ec/regulaciones/ley-organica-proteccion-datos-personales

Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2017). Open University Learning Analytics dataset. *Scientific Data, 4*, Artículo 170171. https://doi.org/10.1038/sdata.2017.171
