# ADR-006: Estilo de arquitectura del sistema

- **Estado:** Aceptada · **Fecha:** 2026-10-03
- **Decisión:** Cliente-servidor desacoplado (SPA + API REST) con backend en capas

## Contexto

Sistema con cuatro piezas (modelo, segmentación, NL2SQL y panel) sobre un almacén gobernado, operado por un equipo de 2 personas en un equipo local con Docker. Los criterios son escenarios de atributos de calidad derivados de los requerimientos.

## Criterios (origen → peso)

- **Incorporar una institución con solo un perfil de mapeo** (20 %): Medida: cero cambios de código para una institución nueva. *Origen:* RF-14 y RNF-11 (modificabilidad)
- **Aislamiento de datos garantizado en el motor** (20 %): Medida: cero filas de otra institución en cualquier respuesta. *Origen:* RNF-01 (seguridad)
- **Panel y chat con las mismas cifras** (15 %): Medida: ambos leen las mismas vistas gobernadas. *Origen:* HU-07 y RF-10 (consistencia)
- **Costo de operación para 2 personas en un equipo local** (25 %): Medida: número de desplegables que hay que operar. *Origen:* Restricción del equipo y de la infraestructura
- **Evolución de la interfaz independiente del backend** (10 %):  *Origen:* RF-11 a RF-13 y variantes móviles
- **Evidencia en trabajos previos** (10 %):  *Origen:* Sección 1.3

## Opciones evaluadas

### Monolito en capas (interfaz renderizada en el servidor) — 4,40 / 5
- Incorporar una institución con solo un perfil de mapeo: **4**. El perfil de mapeo es posible, pero la interfaz y el ETL comparten despliegue. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)
- Aislamiento de datos garantizado en el motor: **5**. El aislamiento reside en el motor (vistas con SESSION_CONTEXT y cuenta de solo lectura), independiente del estilo. *Fuente:* Prueba propia: codigo_fuente/backend/tests/test_integracion_bd.py (22 pruebas de integración contra SQL Server)
- Panel y chat con las mismas cifras: **5**. Una sola aplicación lee las mismas vistas. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)
- Costo de operación para 2 personas en un equipo local: **5**. Un solo desplegable; los monolitos rinden mejor en una sola máquina y convienen a sistemas pequeños y medianos (Blinowski et al., 2022, citado en Hassan et al., 2025, p. 4). *Fuente:* Hassan et al. (2025), Big Data and Cognitive Computing, 9(10), 253, https://doi.org/10.3390/bdcc9100253
- Evolución de la interfaz independiente del backend: **2**. La interfaz queda acoplada a la aplicación del servidor. *Fuente:* Repositorio oficial fastapi/full-stack-fastapi-template en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Evidencia en trabajos previos: **4**. La arquitectura de BI de tres capas que sintetizan Sequeira et al. (2024) es en capas; 10 de 11 trabajos dejan el modelo aislado. *Fuente:* Sequeira et al. (2024), Information, 15(4), 208, pp. 7, 15, https://doi.org/10.3390/info15040208; Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)

### Cliente-servidor desacoplado (SPA + API REST) con backend en capas — 4,65 / 5
- Incorporar una institución con solo un perfil de mapeo: **5**. OULAD_UK se incorporó solo con un perfil en etl/perfiles.py; el mismo ETL y modelo, sin cambios. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)
- Aislamiento de datos garantizado en el motor: **5**. Aislamiento en el motor comprobado: ninguna fila de otra institución en las pruebas ni en la evaluación NL2SQL. *Fuente:* Prueba propia: codigo_fuente/backend/tests/test_integracion_bd.py (22 pruebas de integración contra SQL Server)
- Panel y chat con las mismas cifras: **5**. Panel y chat consumen la misma API, que lee las mismas vistas VIS_*. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)
- Costo de operación para 2 personas en un equipo local: **4**. Dos desplegables (frontend y backend) más la base de datos en Docker. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)
- Evolución de la interfaz independiente del backend: **5**. La SPA consume la API REST y evoluciona aparte, como en la plantilla de referencia. *Fuente:* Repositorio oficial fastapi/full-stack-fastapi-template en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Evidencia en trabajos previos: **4**. Conserva las capas de BI de Sequeira et al. (2024) y separa la presentación. *Fuente:* Sequeira et al. (2024), Information, 15(4), 208, pp. 7, 15, https://doi.org/10.3390/info15040208

### Microservicios (modelo, NL2SQL, ETL y panel por separado) — 3,30 / 5
- Incorporar una institución con solo un perfil de mapeo: **5**. Un servicio de ETL por perfil también lo permite. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)
- Aislamiento de datos garantizado en el motor: **5**. El aislamiento seguiría en el motor. *Fuente:* Prueba propia: codigo_fuente/backend/tests/test_integracion_bd.py (22 pruebas de integración contra SQL Server)
- Panel y chat con las mismas cifras: **3**. Los patrones de base de datos por servicio y CQRS que describe Hassan et al. (2025, p. 16) separan los datos y obligan a sincronizarlos. *Fuente:* Hassan et al. (2025), Big Data and Cognitive Computing, 9(10), 253, https://doi.org/10.3390/bdcc9100253
- Costo de operación para 2 personas en un equipo local: **1**. Migrar a microservicios exige un esfuerzo de desarrollo y recursos considerables y su éxito no está garantizado (Hassan et al., 2025, p. 1); serían al menos cuatro desplegables. *Fuente:* Hassan et al. (2025), Big Data and Cognitive Computing, 9(10), 253, https://doi.org/10.3390/bdcc9100253
- Evolución de la interfaz independiente del backend: **5**. La interfaz sería un servicio más. *Fuente:* Repositorio oficial fastapi/full-stack-fastapi-template en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Evidencia en trabajos previos: **1**. Ningún trabajo previo leído usa microservicios. *Fuente:* Tabla de trabajos previos (documentacion/literatura/trabajos_previos.json, 11 leídos completos)

## Resultado

| Opción | Puntaje |
|---|---|
| Cliente-servidor desacoplado (SPA + API REST) con backend en capas | 4,65 |
| Monolito en capas (interfaz renderizada en el servidor) | 4,40 |
| Microservicios (modelo, NL2SQL, ETL y panel por separado) | 3,30 |

**Sensibilidad:** estable: ninguna variación de ±20 % en un peso cambia la ganadora.

## Decisión y razón

El estilo cliente-servidor desacoplado con backend en capas cumple todos los escenarios de calidad con dos desplegables. Frente al monolito en capas gana por independizar la interfaz (panel, chat y variantes móviles) sin multiplicar la operación. Frente a los microservicios evita un costo de operación y de consistencia que no se justifica para un equipo de 2 personas y una sola institución piloto.

## Consecuencias

- Se gana una interfaz que evoluciona sin tocar el backend y una API documentada.
- Se sacrifica escalar cada pieza por separado.
- Riesgo: si la carga creciera, el backend en capas permite separar primero el entrenamiento por lotes, que ya corre fuera del ciclo de la consulta.
- Reglas verificables en decisiones/arquitectura_reglas.json.
