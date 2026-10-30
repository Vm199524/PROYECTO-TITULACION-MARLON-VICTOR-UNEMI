# Guion del video técnico en Visual Studio Code (15 minutos)

**Proyecto:** Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional (VicMar)

**Autores:** Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco

**Finalidad:** mostrar dominio técnico del sistema compartiendo pantalla en Visual Studio Code. Un solo recorrido, de principio a fin: una persona abre una alerta; React llama a la API; el backend valida usuario, rol e institución; SQL Server entrega los datos; VicMar muestra el resultado y sus razones.

**Idea que ambos deben dominar:** el frontend mejora la experiencia, pero no es la frontera de seguridad. La API autentica y autoriza cada petición, y la base de datos limita las lecturas por institución y privilegio.

## 1. Cronograma

| Tiempo | Expone | Dónde está en pantalla | Qué se explica |
|---|---|---|---|
| 0:00 a 0:45 | Marlon | `README.md` | Qué es VicMar y que los datos son sintéticos |
| 0:45 a 1:45 | Marlon | `README.md` y el explorador de la raíz | Mapa del repositorio |
| 1:45 a 2:30 | Marlon | `ARQUITECTURA.md` | Capas y reglas de dependencia |
| 2:30 a 4:00 | Marlon | `backend/main.py` y `backend/api/` | Punto de entrada, seguridad HTTP y routers |
| 4:00 a 5:30 | Marlon | `base_de_datos/crear_almacen_academico.sql` | Esquema estrella y vistas `VIS_*` |
| 5:30 a 7:15 | Marlon | `backend/core/db.py` | Tres cuentas y `SESSION_CONTEXT` |
| 7:15 a 8:45 | Víctor | `backend/core/seguridad.py` | JWT, bcrypt, roles y capacidades |
| 8:45 a 9:30 | Víctor | `frontend/src/App.tsx` y `lib/api.ts` | Rutas protegidas y cliente de la API |
| 9:30 a 14:30 | Víctor | Interfaz en `localhost:3000` | Demostración en vivo |
| 14:30 a 15:00 | Ambos | Panel | Cierre |

Ritmo de referencia: unas 125 palabras por minuto, porque hay que mover el cursor mientras se habla. Las líneas indicadas corresponden al repositorio actual; si su copia difiere, busquen la función por nombre con `Ctrl+F`.

## 2. Antes de grabar

1. **Quién comparte pantalla.** Cada uno comparte la suya en su bloque. Marlon solo necesita el repositorio abierto en Visual Studio Code (no ejecuta nada). Víctor necesita el sistema en marcha. El cambio dura 10 segundos y se hace justo después de la frase de traspaso. Alternativa: Víctor comparte todo el video y Marlon indica qué abrir.
2. **Sistema arriba (Víctor):** SQL Server disponible, `npm start`, web en http://localhost:3000 y API en http://localhost:8090/docs.
3. **Pestañas abiertas, en este orden:** `README.md`, `ARQUITECTURA.md`, `backend/main.py`, `crear_almacen_academico.sql`, `backend/core/db.py`, `backend/core/seguridad.py`, `frontend/src/App.tsx`, `frontend/src/lib/api.ts`. Pestañas de reserva: `core/privacidad.py`, `core/auditoria.py`.
4. **Visual Studio Code legible:** zoom con `Ctrl +` hasta que la letra se lea a 1080p, minimapa apagado, panel lateral cerrado y tema claro u oscuro, el mismo en las dos pantallas.
5. **Nunca abrir `backend/.env`** ni mostrar contraseñas. Las credenciales de demostración no se dicen ni se escriben en pantalla.
6. **Sesión iniciada antes de grabar con la cuenta de Administración de TI.** Es la única que llega a todo lo que se muestra: registrar seguimiento, calidad del modelo y auditoría. La cuenta de Autoridad no registra seguimiento y la de Bienestar no ve la calidad del modelo.
7. **Institución de prueba UNEMI_PRUEBAS** activa, sin reconstruir ni generar datos durante la grabación.
8. **Ensayo con cronómetro** al menos una vez, y las tres preguntas de la consulta probadas el mismo día.

## 3. Guion

### Bloque 1 · 0:00 a 0:45 · Marlon · Apertura

**En pantalla:** `README.md`, parte superior.

> Buenas. Somos Marlon Pérez y Víctor Lluilema, y les mostramos VicMar por dentro, directamente en el código. VicMar es un prototipo de alerta temprana: estima el riesgo de que un estudiante abandone en el siguiente periodo, explica qué señales pesan en ese riesgo y ayuda a organizar el acompañamiento. Una aclaración: los datos de UNEMI_PRUEBAS son sintéticos. Vamos a seguir un solo recorrido: alguien abre una alerta, React llama a la API, el backend valida usuario, rol e institución, SQL Server entrega los datos y VicMar muestra el resultado con sus razones.

### Bloque 2 · 0:45 a 1:45 · Marlon · Mapa del repositorio

**En pantalla:** `README.md`: desplazar rápido por «Qué hace», «Resultados», «Protección de datos» e «Instalación». Luego el explorador, con la raíz del repositorio visible.

> El README resume el propósito, los resultados validados, la protección de datos y la instalación con un solo comando, npm start, que está definido en package.json. ARQUITECTURA.md es el mapa de capas. En la raíz hay cuatro carpetas. Frontend es la web, en React y TypeScript. Backend es la API y la lógica: FastAPI, el modelo de aprendizaje automático y la consulta conversacional. Base_de_datos guarda el script SQL del almacén y el generador de datos de prueba. Y scripts automatiza el arranque. No voy a recorrer archivo por archivo: sigo el camino de una petición.

### Bloque 3 · 1:45 a 2:30 · Marlon · Arquitectura

**En pantalla:** `ARQUITECTURA.md`: el árbol de carpetas y, debajo, «Reglas de dependencia entre capas».

> La arquitectura es cliente-servidor desacoplada, con backend en capas. Regla uno: el frontend solo habla con el backend por HTTP; nunca toca SQL Server. Regla dos: dentro del backend, api es la capa de servicio y usa core, ml y nl2sql; ninguna capa de dominio importa las rutas. Regla tres: toda lectura pasa por una cuenta de solo lectura, y la cuenta de administración solo la usan los procesos por lotes. En total son 27 servicios REST.

### Bloque 4 · 2:30 a 4:00 · Marlon · Backend

**En pantalla:** `backend/main.py`. Recorrer en este orden: línea 38 (`FastAPI`, `docs_url='/docs'`), 45 (CORS), 49 a 59 (middleware), 62 a 69 (manejadores), 72 (`/api/salud`) y 78 (bucle de routers). Después abrir la carpeta `backend/api/`. Si la API de Marlon está arriba, mostrar `/docs` unos 10 segundos; si no, omitirlo.

> Este es el punto de entrada, main.py, con menos de ochenta líneas. Creamos la aplicación FastAPI y publicamos la documentación interactiva en /docs. El CORS solo admite los orígenes configurados y tres cabeceras: Authorization, Content-Type y X-Institucion, que lleva la institución activa. Este middleware agrega cabeceras de seguridad a cada respuesta, nosniff, X-Frame-Options en DENY, sin referrer y sin caché, y registra cuánto tarda cada petición. Dos manejadores convierten los fallos de base de datos en errores 503 o 502 con un mensaje claro. /api/salud responde sin datos, solo para comprobar que el servicio está vivo. Y al final un bucle registra diez routers bajo /api. Cada módulo de backend/api atiende una función: sesión, panel, estudiantes, carreras, referentes, modelo, seguimiento, consulta, reportes y administración. El backend valida y devuelve datos; no devuelve pantallas.

### Bloque 5 · 4:00 a 5:30 · Marlon · Base de datos

**En pantalla:** `base_de_datos/crear_almacen_academico.sql`. Ir a cada línea con `Ctrl+G`: 67 `dim_institucion`, 109 `dim_periodo_academico`, 128 `dim_carrera`, 139 `dim_alumno`, 154 `fact_matriculas`, 192 `fact_prediccion_abandono`, 272 `fact_intervencion`, 297 `VIS_ALUMNO` y 319 `VIS_PREDICCION_ABANDONO` (detenerse en el `WHERE ... SESSION_CONTEXT`).

> El almacén es un esquema estrella en SQL Server 2022. Las dimensiones son institución, carrera, periodo académico y alumno. La identidad del alumno es institución más identificador, así que dos universidades nunca fusionan a una misma persona. El hecho central es fact_matriculas, con grano alumno por carrera por periodo por corte. Aquí están las predicciones: probabilidad, nivel de riesgo y factores explicativos, calculados por los procesos por lotes. Y aquí fact_intervencion, el registro de seguimiento, que cierra el ciclo predicción, acción y resultado. Lo importante: la aplicación no lee estas tablas. Lee vistas VIS_, y miren el WHERE: cada vista filtra por SESSION_CONTEXT de institución activa. Si la sesión no tiene institución, la vista no devuelve ni una fila.

### Bloque 6 · 5:30 a 7:15 · Marlon · Una lectura, de punta a punta

**En pantalla:** `backend/core/db.py`. Línea 1 a 18 (docstring de las tres cuentas), 67 (`validar_institucion`), 103 a 119 (`_conexion_con_contexto`, con la línea 116 resaltada), 122 (`leer`) y 152 a 154 (`ejecutar_seguimiento` y su lista cerrada).

> db.py maneja tres cuentas con privilegios distintos. La de administración solo sirve a los procesos por lotes: ETL, entrenamiento y calificación; nunca atiende a un usuario ni ejecuta SQL de la IA. La de lectura, chat_reader, atiende todas las lecturas de la API, del panel y de la consulta conversacional; por eso el panel y el chat nunca muestran cifras distintas. Y app_seguimiento solo puede ejecutar dos procedimientos. Veamos esta función: abre la conexión y, antes de cualquier SELECT, ejecuta sp_set_session_context con la institución activa y read_only en uno, de modo que ninguna sentencia posterior de esa conexión puede cambiarla. Antes, el código de institución se valida con una expresión regular: solo mayúsculas, números y guion bajo. Si la cuenta no está configurada, la lectura falla cerrada: jamás se sustituye por la de administración. Y ejecutar_seguimiento solo acepta dos procedimientos de una lista cerrada. Víctor les muestra ahora cómo estos controles se conectan con la experiencia del usuario.

**Traspaso (10 s):** Marlon deja de compartir; Víctor comparte su pantalla.

### Bloque 7 · 7:15 a 8:45 · Víctor · Seguridad

**En pantalla:** `backend/core/seguridad.py`. Línea 32 (`CAPACIDADES_POR_ROL`), 55 y 60 (bcrypt), 70 (`crear_token`), 97 a 128 (`sesion_actual`) y 131 (`requiere`). Después, 5 segundos en cada una: `core/privacidad.py` (`enmascarar_cedula`, `seudonimizar`) y `core/auditoria.py` (`registrar`).

> La seguridad vive en seguridad.py. Hay tres roles: autoridad académica, que consulta y decide pero no registra seguimiento; bienestar estudiantil, que atiende alertas, simula y registra; y administración de TI. Cada rol es un conjunto de capacidades, como ver_panel o registrar_seguimiento. Las contraseñas se guardan con bcrypt, nunca en texto plano. El inicio de sesión emite un JWT firmado con vencimiento, de ocho horas por defecto, y sesion_actual lo valida en cada petición: decodifica el token, vuelve a buscar la cuenta y, si fue desactivada, el token deja de servir al instante. La institución llega en la cabecera X-Institucion y debe estar entre las asignadas al usuario; si no, responde 403. La dependencia requiere exige la capacidad: el frontend puede ocultar una opción, pero la autorización real se valida aquí. Además, privacidad.py enmascara la cédula en pantalla, y auditoria.py registra quién hizo qué, con la huella del SQL y no el SQL completo.

### Bloque 8 · 8:45 a 9:30 · Víctor · Frontend

**En pantalla:** `frontend/src/App.tsx`: línea 38 (`Protegida`) y 71 a 84 (rutas). Luego `frontend/src/lib/api.ts`: línea 35 (`sessionStorage`), 64 (`cabeceras`) y 79 (manejo del 401).

> En App.tsx, cada ruta declara la capacidad que exige, la misma que valida el backend. Si el rol no la tiene, la pantalla dice que la sección no está disponible, y las pantallas se cargan bajo demanda. En api.ts, cada petición lleva el token Bearer y la cabecera X-Institucion. El token vive en sessionStorage y se borra al cerrar la pestaña, y un error 401 cierra la sesión en todas las pantallas. El frontend mejora la experiencia; la frontera de seguridad es la API.

### Bloque 9 · 9:30 a 14:30 · Víctor · Demostración en vivo

Narrar qué objetivo cumple cada pantalla, no solo hacer clics. No leer datos personales en voz alta.

**Panel · 45 s.** *Haz:* abrir el Panel y señalar el total de estudiantes evaluados, la distribución por nivel de riesgo y las señales de confiabilidad del modelo.

> Este es el panel que ve una autoridad académica al ingresar. Resume cuántos estudiantes se evaluaron, cómo se reparten por nivel de riesgo y qué tan confiable es el modelo, con la institución activa y la aclaración de que son datos de prueba. Una alerta no decide el futuro de nadie: prioriza una revisión humana, y desde aquí se baja al detalle.

**Estudiantes y ficha · 1 min 30 s.** *Haz:* entrar a Estudiantes, filtrar por riesgo alto, abrir un registro ficticio y señalar la dirección del navegador.

> La lista de estudiantes llega desde el endpoint de estudiantes, ya filtrada por la institución activa. Filtro por riesgo alto y abro un registro de prueba. La ficha muestra la probabilidad de abandono, el nivel de riesgo y los tres factores que más pesan en esa estimación, calculados con SHAP: no es una caja negra, la persona que acompaña sabe por qué se alertó. Fíjense en la dirección del navegador: no aparece la cédula, aparece un token cifrado, y en pantalla la cédula siempre va enmascarada. Es la protección de datos del backend llegando a la interfaz, y las probabilidades están calibradas, así que se pueden leer como riesgo y no solo como un orden.

**Seguimiento · 45 s.** *Haz:* abrir Seguimiento. Si el flujo está ensayado, registrar una intervención desde la ficha y mostrar su estado en la lista. Si no, mostrar solo la lista.

> Aquí se cierra el ciclo: predicción, acción y resultado. Registro una intervención y la lista muestra su estado: abierta hasta que se cierre con un resultado. Esto escribe a través de app_seguimiento y un procedimiento almacenado, nunca por SQL libre, y la inteligencia artificial jamás escribe aquí.

**Consulta conversacional · 1 min.** *Haz:* escribir «¿Cuántos estudiantes están en riesgo alto?». Si sobra tiempo, escribir «Borra a los estudiantes de riesgo alto» y mostrar que la barrera lo detiene. Ambas ya se probaron: la primera se responde con una métrica certificada.

> Pregunto en español: cuántos estudiantes están en riesgo alto. Esta pregunta coincide con una de las 40 métricas certificadas: el SQL es fijo y los parámetros van enlazados, el modelo de lenguaje no interviene en la cifra. Si no coincide, el sistema genera un SQL con IA, pero un validador revisa su árbol sintáctico y solo lo ejecuta la cuenta de solo lectura. Y si pido borrar datos, la primera barrera lo detiene antes de generar nada. No presentamos la IA como infalible: toda respuesta es verificable.

**Cierre de la interfaz · 1 min.** *Haz:* abrir Calidad del modelo, señalar ROC-AUC y recall por periodo. Luego abrir Administración, Auditoría, y mostrar los eventos recién generados (ingreso, consulta, seguimiento). Volver al Panel.

> En Calidad del modelo está la evidencia: en UNEMI_PRUEBAS, que son datos sintéticos, el ROC-AUC es 0,829 y el recall 0,781 en el umbral medio, y en OULAD, que son datos reales anonimizados, 0,768. Y en Auditoría queda registrado lo que acabamos de hacer: el ingreso, la consulta con la huella de su SQL y el seguimiento. Vuelvo al panel para cerrar.

### Bloque 10 · 14:30 a 15:00 · Ambos · Cierre

**En pantalla:** Panel.

> **Marlon:** VicMar convierte datos académicos en alertas explicadas y acompañamiento oportuno, con validación que respeta el orden del tiempo y datos reales anonimizados como contraste. **Víctor:** Y lo hace con una arquitectura en capas, acceso por roles y separación institucional en la propia base de datos. VicMar integra predicción, explicación y acompañamiento. Gracias.

## 4. Si algo falla durante la grabación

- **No levanta la web o la API:** decirlo, mostrar `/api/salud` o el terminal, y continuar con el código. No fingir un resultado.
- **Una consulta no responde o falla el proveedor de IA:** explicar la dependencia («este paso usa un proveedor externo») y pasar a una de las dos preguntas certificadas ensayadas: «¿Cuántos estudiantes hay en cada nivel de riesgo?» o «¿Qué carreras tienen más estudiantes en riesgo?».
- **Van atrasados:** recortar el recorrido de `main.py` (bloque 4) y los adjetivos; no los datos. **Van adelantados:** ampliar el simulador de la ficha o el reporte en Excel.

## 5. Si les preguntan (respuestas de una línea)

| Pregunta | Respuesta |
|---|---|
| ¿Por qué el frontend no es la frontera de seguridad? | Un cliente puede modificarse. Por eso `requiere` valida la capacidad en cada petición y la base limita las lecturas por institución. |
| ¿Cómo evitan que una institución lea datos de otra? | La institución debe estar entre las asignadas al usuario; se fija en `SESSION_CONTEXT` con `read_only = 1`; y las vistas `VIS_*` filtran por ese valor. |
| ¿Qué pasa si el modelo de lenguaje genera SQL peligroso? | Hay cuatro barreras independientes: intención, validador del árbol con `sqlglot`, vistas filtradas y cuenta de solo lectura. La garantía real está en el motor. |
| ¿Qué datos van a un proveedor de IA externo? | Solo filas seudonimizadas («Estudiante 1») y con cédulas ocultas, y la interpretación con IA puede desactivarse con `CONSULTA_INTERPRETAR=0`. |
| ¿Y si se desactiva a un usuario con un token vigente? | La cuenta se revalida en cada petición; el token deja de servir al instante. |
| ¿Por qué tres cuentas de base de datos? | Mínimo privilegio: administración para lotes, lectura gobernada para la API y seguimiento solo con dos procedimientos. |
| ¿Qué es «fallar cerrado»? | Si falta la clave de `chat_reader`, la lectura se rechaza; nunca se usa la cuenta de administración como reemplazo. |
| ¿Por qué un esquema estrella? | Lecturas analíticas con grano alumno por periodo, y un mismo esquema para cualquier institución mediante perfiles de mapeo. |
| ¿Cómo se frena la fuerza bruta en el ingreso? | Cinco intentos fallidos en cinco minutos bloquean al par usuario e IP durante ese tiempo (`api/sesion.py`). |
| Cifras de reserva | UNEMI_PRUEBAS (sintético): ROC-AUC 0,829, recall 0,781. OULAD (real): ROC-AUC 0,768; evaluación prospectiva 0,764 con recall 0,913. |
