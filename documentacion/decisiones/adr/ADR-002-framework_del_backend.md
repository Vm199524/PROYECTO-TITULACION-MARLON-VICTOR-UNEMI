# ADR-002: Framework del backend

- **Estado:** Aceptada · **Fecha:** 2026-10-03
- **Decisión:** FastAPI (versión 0.141)

## Contexto

La API debe atender el panel y el chat, llamar de forma concurrente a una cascada de proveedores externos de LLM y ejecutar el SQL de la IA con una cuenta de solo lectura, fijando el contexto de institución en la misma conexión. Lenguaje ya decidido en DT-01 (Python).

## Criterios (origen → peso)

- **Asincronía para llamadas a servicios externos** (25 %):  *Origen:* RNF-06 y RNF-10 (cascada de proveedores de LLM)
- **Validación y documentación automática de la API** (20 %): Esquemas de entrada y documentación OpenAPI sin código extra. *Origen:* RF-09 y RNF-08
- **Acceso a SQL Server con contexto en la misma conexión** (20 %): No imponer un ORM que gestione las conexiones por su cuenta. *Origen:* RF-16 y RNF-01
- **Licencia y soporte** (15 %):  *Origen:* RNF-09; costo cero
- **Costo de cambio sobre el prototipo validado** (20 %):  *Origen:* Restricción: plazo del proyecto

## Opciones evaluadas

### FastAPI — 4,85 / 5
- Asincronía para llamadas a servicios externos: **5**. Soporte nativo de async/await sobre ASGI. *Fuente:* Documentación oficial de FastAPI (fastapi.tiangolo.com), consultada 2026-10-03
- Validación y documentación automática de la API: **5**. Validación con Pydantic y documentación OpenAPI interactiva en /docs, generadas automáticamente. *Fuente:* Documentación oficial de FastAPI (fastapi.tiangolo.com), consultada 2026-10-03
- Acceso a SQL Server con contexto en la misma conexión: **5**. No impone ORM; el backend usa pyodbc y fija SESSION_CONTEXT y el SELECT en la misma conexión, comprobado por pruebas. *Fuente:* Prueba propia: codigo_fuente/backend/tests/test_integracion_bd.py (22 pruebas de integración contra SQL Server)
- Licencia y soporte: **4**. Licencia MIT y publicaciones frecuentes (0.142.2 del 30/09/2026), aunque sigue en la serie 0.x. *Fuente:* Repositorio oficial fastapi/fastapi en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Costo de cambio sobre el prototipo validado: **5**. Es el framework implementado y probado. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

### Django — 3,15 / 5
- Asincronía para llamadas a servicios externos: **4**. Admite vistas asíncronas con pila ASGI, pero el ORM aún no es totalmente asíncrono y el middleware síncrono anula la ventaja. *Fuente:* Documentación oficial de Django 5.2, «Asynchronous support» (docs.djangoproject.com/en/5.2/topics/async), consultada 2026-10-03
- Validación y documentación automática de la API: **3**. El índice de la documentación no incluye API REST ni OpenAPI en el núcleo; se obtienen con paquetes de terceros. *Fuente:* Índice de la documentación oficial de Django 5.2 (docs.djangoproject.com/en/5.2), consultado 2026-10-03
- Acceso a SQL Server con contexto en la misma conexión: **2**. SQL Server no es un backend oficial; depende del paquete de terceros mssql-django. *Fuente:* Documentación oficial de Django 5.2, «Databases» (docs.djangoproject.com/en/5.2/ref/databases), consultada 2026-10-03
- Licencia y soporte: **5**. Licencia BSD-3; la 5.2 es LTS con soporte hasta abril de 2028. *Fuente:* Django, «Download» (djangoproject.com/download), consultado 2026-10-03
- Costo de cambio sobre el prototipo validado: **2**. Habría que reescribir rutas, autenticación y streaming. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

### Flask — 3,10 / 5
- Asincronía para llamadas a servicios externos: **2**. Es WSGI: cada petición ocupa un worker aun con vistas async, y su soporte async es menos eficiente que el de los frameworks ASGI. *Fuente:* Documentación oficial de Flask 3.1, «Using async and await» (flask.palletsprojects.com), consultada 2026-10-03
- Validación y documentación automática de la API: **2**. Por diseño no incluye validación de formularios ni capa de datos en el núcleo; se agregan con extensiones. *Fuente:* Documentación oficial de Flask 3.1, «Design Decisions in Flask» (flask.palletsprojects.com), consultada 2026-10-03
- Acceso a SQL Server con contexto en la misma conexión: **5**. No incluye capa de base de datos, así que admite el mismo acceso con pyodbc. *Fuente:* Documentación oficial de Flask 3.1, «Design Decisions in Flask» (flask.palletsprojects.com), consultada 2026-10-03
- Licencia y soporte: **4**. Licencia BSD-3; última versión 3.1.3 (febrero de 2026). *Fuente:* Repositorio oficial pallets/flask en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Costo de cambio sobre el prototipo validado: **3**. Rutas parecidas, pero el streaming y la asincronía cambian de semántica. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

## Resultado

| Opción | Puntaje |
|---|---|
| FastAPI | 4,85 |
| Django | 3,15 |
| Flask | 3,10 |

**Sensibilidad:** estable: ninguna variación de ±20 % en un peso cambia la ganadora.

## Decisión y razón

FastAPI es la única de las tres que es asíncrona de origen, valida y documenta la API automáticamente y deja libre el acceso a SQL Server con contexto de sesión, que es la base del aislamiento por institución.

## Consecuencias

- Se gana documentación OpenAPI viva para el frontend y pruebas.
- Se sacrifica el panel de administración y el ORM integrados de Django, que el proyecto no necesita.
- Riesgo: FastAPI sigue en 0.x; se fija la versión exacta y se actualiza con la suite de pruebas.

## Verificación en el código

`codigo_fuente/backend/requirements.txt` debe fijar `fastapi` en la versión `0.141` (lo comprueba verificar_coherencia.py).
