# ADR-004: Motor del almacén de datos

- **Estado:** Aceptada para el prototipo · **Fecha:** 2026-10-03
- **Decisión:** SQL Server (versión 2022)

## Contexto

El almacén en esquema estrella guarda la trayectoria de varias instituciones. El SQL que genera la IA debe ejecutarse con una cuenta de solo lectura y ver solo las filas de la institución activa, garantizado por el propio motor. La institución destino es pública y el costo de licencias importa.

## Criterios (origen → peso)

- **Aislamiento por institución en el motor** (35 %): Seguridad por filas o contexto de sesión nativos. *Origen:* RF-16 y RNF-01
- **Costo de licencia en producción** (25 %):  *Origen:* Restricción: institución pública, costo cero
- **Evidencia en trabajos previos** (10 %):  *Origen:* Sección 1.3
- **Costo de cambio sobre el prototipo validado** (30 %): Vistas, permisos, ETL y pruebas ya implementados. *Origen:* Restricción: plazo del proyecto

## Opciones evaluadas

### SQL Server — 4,30 / 5
- Aislamiento por institución en el motor: **5**. SESSION_CONTEXT con valores de solo lectura y seguridad por filas en todas las ediciones; el aislamiento se comprobó con pruebas de integración. *Fuente:* Microsoft Learn, «SESSION_CONTEXT (Transact-SQL)», consultado 2026-10-03; Microsoft Learn, «Editions and supported features of SQL Server 2022», consultado 2026-10-03; Prueba propia: codigo_fuente/backend/tests/test_integracion_bd.py (22 pruebas de integración contra SQL Server)
- Costo de licencia en producción: **3**. La edición Express es gratuita, pero limita la base a 10 GB y a 1 socket o 4 núcleos; la Developer no se puede usar en producción. *Fuente:* Microsoft Learn, «Editions and supported features of SQL Server 2022», consultado 2026-10-03
- Evidencia en trabajos previos: **3**. Aparece en las implementaciones de BI que reúne la revisión de Sequeira et al.; 9 de 11 trabajos no declaran motor. *Fuente:* Sequeira et al. (2024), Information, 15(4), 208, pp. 7, 15, https://doi.org/10.3390/info15040208
- Costo de cambio sobre el prototipo validado: **5**. Es el motor implementado: vistas VIS_*, cuenta chat_reader y 22 pruebas de seguridad. *Fuente:* Prueba propia: codigo_fuente/backend/tests/test_integracion_bd.py (22 pruebas de integración contra SQL Server)

### PostgreSQL — 3,90 / 5
- Aislamiento por institución en el motor: **5**. Políticas de seguridad por fila nativas, con denegación por defecto si no hay política. *Fuente:* PostgreSQL 18 Documentation, «Row Security Policies», consultado 2026-10-03
- Costo de licencia en producción: **5**. Licencia PostgreSQL, libre y sin costo, similar a BSD o MIT. *Fuente:* PostgreSQL, «License» (postgresql.org/about/licence), consultado 2026-10-03
- Evidencia en trabajos previos: **3**. Aparece en las implementaciones de BI que reúne la revisión de Sequeira et al. *Fuente:* Sequeira et al. (2024), Information, 15(4), 208, pp. 7, 15, https://doi.org/10.3390/info15040208
- Costo de cambio sobre el prototipo validado: **2**. Habría que reescribir las vistas, los permisos y el contexto de sesión, y repetir las pruebas. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

### MySQL — 2,10 / 5
- Aislamiento por institución en el motor: **2**. Los privilegios llegan a nivel de tabla, columna y rutina; no hay políticas por fila nativas. *Fuente:* MySQL 8.4 Reference Manual, «Privileges Provided by MySQL», consultado 2026-10-03
- Costo de licencia en producción: **4**. Edición comunitaria con licencia GPLv2. *Fuente:* Archivo LICENSE del repositorio oficial mysql/mysql-server (GPLv2), consultado 2026-10-03
- Evidencia en trabajos previos: **1**. Ningún trabajo previo leído lo declara. *Fuente:* Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)
- Costo de cambio sobre el prototipo validado: **1**. Además de la reescritura, el aislamiento tendría que hacerse en la aplicación. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

## Resultado

| Opción | Puntaje |
|---|---|
| SQL Server | 4,30 |
| PostgreSQL | 3,90 |
| MySQL | 2,10 |

**Sensibilidad:** estable: ninguna variación de ±20 % en un peso cambia la ganadora.

## Decisión y razón

SQL Server y PostgreSQL empatan en el criterio más importante, el aislamiento por institución dentro del motor; MySQL queda descartado por no tenerlo. SQL Server gana por el costo de cambio: el aislamiento ya está implementado y probado. Si se quita ese criterio, gana PostgreSQL por su licencia, así que para un despliegue institucional sin licencias de SQL Server se recomienda migrar a PostgreSQL.

## Consecuencias

- Se gana un aislamiento ya verificado con 22 pruebas de integración.
- Se sacrifica costo: en producción haría falta Express (límite de 10 GB) o una licencia de pago.
- Riesgo: dependencia de T-SQL; la lógica está concentrada en crear_almacen_academico.sql para facilitar una migración.

## Verificación en el código

`codigo_fuente/backend/requirements.txt` debe fijar `pyodbc` en la versión `5.3` (lo comprueba verificar_coherencia.py).
