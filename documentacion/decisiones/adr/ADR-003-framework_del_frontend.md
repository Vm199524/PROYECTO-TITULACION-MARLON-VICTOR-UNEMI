# ADR-003: Framework del frontend

- **Estado:** Aceptada · **Fecha:** 2026-10-03
- **Decisión:** React (versión 18.3)

## Contexto

El frontend es una aplicación de una sola página con el panel de riesgo, los segmentos, los referentes y el chat; consume la API REST y no accede a la base de datos. Ningún trabajo previo leído declara un framework de frontend, por lo que la decisión se apoya en documentación oficial, repositorios de referencia y el contexto del prototipo.

## Criterios (origen → peso)

- **Plantilla de referencia con FastAPI** (20 %):  *Origen:* ADR-000 (estructura del repositorio)
- **Adopción y comunidad** (20 %): Tamaño de la comunidad del repositorio oficial. *Origen:* RNF-08 (mantenibilidad)
- **Ciclo de soporte** (20 %):  *Origen:* RNF-09
- **Licencia** (10 %):  *Origen:* Costo cero
- **Costo de cambio sobre el prototipo validado** (30 %):  *Origen:* Restricción: plazo del proyecto

## Opciones evaluadas

### React — 4,80 / 5
- Plantilla de referencia con FastAPI: **5**. La plantilla full-stack de FastAPI usa React con Vite. *Fuente:* Repositorio oficial fastapi/full-stack-fastapi-template en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Adopción y comunidad: **5**. Repositorio oficial con 250.872 estrellas. *Fuente:* Repositorio oficial facebook/react en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Ciclo de soporte: **4**. La 18.3.1 sigue documentada; la versión vigente es la 19.3 (septiembre de 2026), por lo que queda una migración pendiente. *Fuente:* React, «Versions» (react.dev/versions), consultado 2026-10-03
- Licencia: **5**. Licencia MIT. *Fuente:* Repositorio oficial facebook/react en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Costo de cambio sobre el prototipo validado: **5**. Panel, chat y pruebas ya implementados. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

### Angular — 3,00 / 5
- Plantilla de referencia con FastAPI: **3**. No es el frontend de la plantilla de referencia. *Fuente:* Repositorio oficial fastapi/full-stack-fastapi-template en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Adopción y comunidad: **4**. Repositorio oficial con 101.015 estrellas. *Fuente:* Repositorio oficial angular/angular en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Ciclo de soporte: **4**. Una versión mayor por año con 24 meses de soporte (12 activos y 12 LTS). *Fuente:* Angular, «Releases» (angular.dev/reference/releases), consultado 2026-10-03
- Licencia: **5**. Licencia MIT. *Fuente:* Repositorio oficial angular/angular en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Costo de cambio sobre el prototipo validado: **1**. Reescritura completa de la interfaz. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

### Vue — 3,10 / 5
- Plantilla de referencia con FastAPI: **3**. No es el frontend de la plantilla de referencia. *Fuente:* Repositorio oficial fastapi/full-stack-fastapi-template en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Adopción y comunidad: **3**. Repositorio oficial (vuejs/core) con 54.481 estrellas. *Fuente:* Repositorio oficial vuejs/core en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Ciclo de soporte: **4**. Vue 3 vigente; versiones menores cada 3 a 6 meses, sin calendario fijo de soporte. *Fuente:* Vue.js, «Releases» (vuejs.org/about/releases), consultado 2026-10-03
- Licencia: **5**. Licencia MIT. *Fuente:* Repositorio oficial vuejs/core en GitHub (licencia, estrellas y última versión por la API), consultado 2026-10-03
- Costo de cambio sobre el prototipo validado: **2**. Reescritura de componentes, aunque con un modelo de componentes parecido. *Fuente:* Repositorio del prototipo: codigo_fuente/ (suite pytest del backend y pruebas del frontend)

## Resultado

| Opción | Puntaje |
|---|---|
| React | 4,80 |
| Vue | 3,10 |
| Angular | 3,00 |

**Sensibilidad:** estable: ninguna variación de ±20 % en un peso cambia la ganadora.

## Decisión y razón

React es coherente con la plantilla de referencia elegida para la estructura (FastAPI + React + Vite), tiene la comunidad más grande y es el frontend ya implementado. Las tres opciones son técnicamente viables para este panel; la literatura del dominio no favorece a ninguna.

## Consecuencias

- Se gana continuidad con el prototipo y con la plantilla de referencia.
- Se sacrifica la estructura más prescriptiva de Angular.
- Riesgo: React 18 ya no es la versión vigente; migrar a la 19 queda como trabajo posterior.

## Verificación en el código

`codigo_fuente/frontend/package.json` debe fijar `react` en la versión `18.3` (lo comprueba verificar_coherencia.py).
