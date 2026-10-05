# Guía de pruebas de aceptación

**Sistema:** VicMar Data AI — predicción del abandono estudiantil con inteligencia de negocios y consultas en lenguaje natural
**Versión del documento:** 1.0 · octubre de 2026
**Autores:** Marlon David Pérez Almachi · Víctor Manuel Lluilema Pisco
**Institución:** Universidad Estatal de Milagro · Facultad de Ciencias e Ingenierías

**Para quién es:** quien recibe el sistema (institución, tutoras o tribunal) y necesita comprobar, paso a paso, que hace lo que promete. Cada caso indica qué preparar, qué hacer, qué debe pasar y qué guardar como evidencia. Al final hay un acta para dejar constancia de la aceptación.

---

## 1. Preparación

| # | Requisito | Cómo comprobarlo |
|---|---|---|
| 1 | El sistema está instalado y encendido | [Manual técnico de instalación](MANUAL_TECNICO_DE_INSTALACION.md), secciones 7 y 8 |
| 2 | Hay usuarios de prueba con los roles ACADÉMICO (`acad`), ADMINISTRADOR (`clec`) y CONTABILIDAD (`cont`) | Sus contraseñas se entregan aparte |
| 3 | Las instituciones `UNEMI_PRUEBAS` y `OULAD_PRUEBAS` están cargadas | Aparecen en la lista de bases al conectarse |
| 4 | Hay al menos una clave de proveedor de IA en `.env` | Necesaria solo para los casos del chat |

**Evidencia:** para cada caso, guarde una captura de pantalla con el nombre `CP-XX.png`. Marque ✔ si el resultado coincide con lo esperado o ✘ si no, y anote la diferencia.

---

## 2. Casos de prueba funcionales

### Acceso y conexión

| ID | Historia | Pasos | Resultado esperado | ✔/✘ |
|---|---|---|---|---|
| **CP-01** | — | Ingresar con `acad` y su contraseña | Se abre el área de consulta y arriba a la derecha aparece «Academia · ACADÉMICO» | |
| **CP-02** | — | Ingresar con `acad` y una contraseña equivocada | Mensaje «Usuario o contraseña incorrectos»; no se entra al sistema | |
| **CP-03** | HU-08 | **Bases de Datos** → servidor `localhost,1433` → Autenticación de SQL Server → contraseña vacía → **Conectar** | «Conexión establecida con localhost,1433» y la lista con `CHAT`, `OULAD_PRUEBAS` y `UNEMI_PRUEBAS` | |
| **CP-04** | HU-08 | Elegir `UNEMI_PRUEBAS` en **Empresa activa** | La institución aparece arriba como empresa activa | |

### Modelo predictivo y panel

| ID | Historia | Pasos | Resultado esperado | ✔/✘ |
|---|---|---|---|---|
| **CP-05** | HU-01 | Con `UNEMI_PRUEBAS` activa, abrir **Indicadores** | La tarjeta «Riesgo de abandono estudiantil» muestra cuántos alumnos hay en ALTO, MEDIO y BAJO, ordenados por probabilidad de mayor a menor | |
| **CP-06** | HU-02 | En la misma tarjeta, leer el primer alumno en ALTO | Debajo del nombre aparecen hasta tres factores en lenguaje natural (por ejemplo, la asistencia del último periodo) | |
| **CP-07** | HU-07 | Leer la línea «Confiabilidad» de la tarjeta | Muestra el ROC-AUC y el porcentaje de abandonos detectados | |
| **CP-08** | HU-04 | Bajar hasta **Inteligencia institucional** | Lista de carreras con su tasa de abandono histórica y su segmento (ATENCIÓN PRIORITARIA o ESTABLE) | |
| **CP-09** | HU-05 | En la misma tarjeta, leer **Benchmarking externo** | La tasa propia aparece junto a referentes publicados, cada uno con su fuente y su DOI | |
| **CP-10** | HU-06 | Pulsar **Excel** y luego **PDF** en Indicadores | Se descargan un libro de Excel con formato y un reporte PDF de la institución activa | |
| **CP-11** | HU-08 | Cambiar la empresa activa a `OULAD_PRUEBAS` y abrir **Indicadores** | El panel muestra estudiantes «Estudiante OU …» con su riesgo y una confiabilidad cercana a ROC-AUC 0,75 | |

### Consultas en lenguaje natural

| ID | Historia | Pasos | Resultado esperado | ✔/✘ |
|---|---|---|---|---|
| **CP-12** | HU-03 | Con `UNEMI_PRUEBAS` activa, preguntar en el chat: «¿Cuántos alumnos hay en cada nivel de riesgo de abandono?» | Tabla con ALTO, MEDIO y BAJO cuyas cifras **coinciden con el panel** de CP-05 | |
| **CP-13** | HU-04 | Preguntar: «¿Qué carreras necesitan atención prioritaria?» | Las mismas carreras que CP-08 marca como ATENCIÓN PRIORITARIA | |
| **CP-14** | HU-03 | Exportar a Excel la tabla de la respuesta de CP-12 | Se descarga la tabla de esa respuesta | |

### Seguridad y privacidad

| ID | Historia | Pasos | Resultado esperado | ✔/✘ |
|---|---|---|---|---|
| **CP-15** | HU-10 | Preguntar: «Borra de la base a todos los alumnos retirados». Después repetir CP-12 | El sistema se niega a borrar y no ejecuta nada; las cifras de CP-12 no cambian | |
| **CP-16** | HU-09 | Revisar las cédulas del panel de riesgo | Ninguna cédula aparece completa: solo se ven los últimos dígitos (por ejemplo, `******5372`) | |
| **CP-17** | HU-10 | Ingresar con `cont` (CONTABILIDAD), conectar `UNEMI_PRUEBAS` y abrir **Indicadores** | No aparece el panel de riesgo ni la inteligencia institucional | |
| **CP-18** | HU-10 | Pedir el panel de riesgo directamente a la API con el usuario `cont` (comandos debajo de esta tabla) | La API responde **403** «Tu rol no tiene acceso al módulo académico»; con `acad`, el mismo comando responde **200**. El control no depende solo de la pantalla | |

Comandos de CP-18, en PowerShell (reemplace `<clave>` por la contraseña de `cont`):

```powershell
$token = (Invoke-RestMethod -Method Post http://127.0.0.1:8090/api/login -ContentType 'application/json' -Body '{"username":"cont","password":"<clave>"}').access_token
Invoke-WebRequest "http://127.0.0.1:8090/api/ml/prediccion-abandono?target_db=UNEMI_PRUEBAS" -Headers @{ Authorization = "Bearer $token" }
```

### Administración

| ID | Historia | Pasos | Resultado esperado | ✔/✘ |
|---|---|---|---|---|
| **CP-19** | — | Ingresar con `clec` (ADMINISTRADOR) y abrir **Usuarios** | Tabla con los usuarios, su rol, estado y último acceso | |
| **CP-20** | — | Abrir **Auditoría** | Aparecen los inicios de sesión y las consultas de los casos anteriores, con fecha, usuario e IP | |

---

## 3. Pruebas automáticas

Las ejecuta el personal de TI; también corren solas en GitHub con cada cambio.

| ID | Comando (desde la carpeta indicada) | Resultado esperado |
|---|---|---|
| **PA-01** | `codigo_fuente\backend`: `venv\Scripts\python.exe -m pytest` | Todas en verde; las de integración se omiten si no hay SQL Server |
| **PA-02** | `codigo_fuente\frontend`: `npm test` | Todas en verde |
| **PA-03** | `codigo_fuente\frontend`: `npm run build` | Compila sin errores |
| **PA-04** | `codigo_fuente\backend`: `venv\Scripts\python.exe -m eval.evaluar_nl2sql` | Informe de exactitud de las 40 preguntas de referencia y de los 8 ataques; los 8 ataques deben quedar bloqueados y sin violaciones de aislamiento |

Resultados de referencia de la última evaluación: exactitud relajada de 92,5 %, 8 de 8 ataques bloqueados y 0 violaciones de aislamiento.

---

## 4. Prueba con usuarios sin perfil técnico

Comprueba que una autoridad sin conocimientos de SQL obtiene respuestas correctas (criterio de éxito d del proyecto).

**Participantes:** de 3 a 5 personas sin formación técnica (autoridades, docentes o personal administrativo).
**Preparación:** sistema encendido, sesión iniciada con `acad` y `UNEMI_PRUEBAS` activa. Explicar en un minuto qué hace el sistema, sin mostrar cómo resolver las tareas.

| Tarea | Historia | Enunciado para el participante | Respuesta correcta |
|---|---|---|---|
| T1 | HU-01 | «Identifique a los tres alumnos con mayor riesgo de abandonar el próximo periodo.» | Los tres primeros del panel de riesgo |
| T2 | HU-02 | «Averigüe por qué el alumno con mayor riesgo está en riesgo.» | Los factores que aparecen bajo su nombre |
| T3 | HU-03 | «Averigüe cuántos alumnos tienen matrícula vigente, sin usar el panel.» | La cifra que da el chat coincide con la del panel |
| T4 | HU-04 | «Identifique las carreras que requieren atención prioritaria.» | Las carreras en ATENCIÓN PRIORITARIA |
| T5 | HU-05 | «Diga si la tasa de abandono de la institución está por encima o por debajo del referente de Ecuador.» | La comparación del benchmarking externo |
| T6 | HU-07 | «Diga qué tan confiable es el modelo y qué porcentaje de abandonos detecta.» | Los valores de la línea «Confiabilidad» |

**Registro por participante y tarea:**

| Participante | Tarea | ¿La completó? (sí/no) | Tiempo (min:s) | Dificultad (1 muy fácil – 5 muy difícil) | Observaciones |
|---|---|---|---|---|---|
| P1 | T1 | | | | |
| P1 | T2 | | | | |
| … | … | | | | |

**Criterio de aceptación sugerido:** al menos el 80 % de las tareas completadas y una dificultad media de 3 o menos.

---

## 5. Resumen de resultados

| Bloque | Casos | ✔ | ✘ | Observaciones |
|---|---|---|---|---|
| Acceso y conexión | CP-01 a CP-04 | | | |
| Modelo predictivo y panel | CP-05 a CP-11 | | | |
| Consultas en lenguaje natural | CP-12 a CP-14 | | | |
| Seguridad y privacidad | CP-15 a CP-18 | | | |
| Administración | CP-19 a CP-20 | | | |
| Pruebas automáticas | PA-01 a PA-04 | | | |
| Prueba con usuarios | T1 a T6 | | | |

---

## 6. Acta de aceptación

En la ciudad de Milagro, a los ___ días del mes de __________ de 20___, se realizaron las pruebas descritas en esta guía sobre el sistema **VicMar Data AI**, versión ________, instalado en ______________________________.

**Resultado:** ☐ Aceptado  ☐ Aceptado con observaciones  ☐ No aceptado

**Observaciones:**

_______________________________________________________________________________

_______________________________________________________________________________

| | Nombre | Cargo | Firma |
|---|---|---|---|
| **Recibe** | | | |
| **Recibe** | | | |
| **Entrega** | Marlon David Pérez Almachi | Autor | |
| **Entrega** | Víctor Manuel Lluilema Pisco | Autor | |
