# ADR-000: Estructura del repositorio

- **Estado:** Aceptada · **Fecha:** 2026-10-03
- **Autores:** Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco
- **Decisión:** un solo repositorio con tres carpetas raíz (`codigo_fuente/`, `documentacion/`, `datos/`). El código se organiza por las capas de la arquitectura elegida: cliente-servidor desacoplado con backend en capas.

## Contexto

Hasta el Avance 1, el proyecto acumuló en la raíz carpetas de distintas épocas:
- un prototipo anterior en Node/Express;
- un backend en Python;
- documentos de cada avance mezclados con código;
- datasets, videos y PDF de artículos.

Eso dificultaba saber qué código estaba vigente y reproducir los resultados, y no permitía reconocer la arquitectura con solo mirar las carpetas. Las restricciones son las siguientes:
- **Equipo:** dos desarrolladores, que además son los autores del documento.
- **Reproducibilidad:** el documento se genera leyendo los resultados del código, así que el código y el documento deben poder versionarse juntos.
- **Datos personales:** nada con datos personales ni con derechos de terceros puede publicarse.
- **Arquitectura reconocible:** la arquitectura declarada en 3.2 debe poder verificarse en el código.

## Opciones evaluadas

| Criterio (peso) | A. Repositorio único organizado por capas | B. Varios repositorios (frontend, backend y documento por separado) | C. Estructura plana por avance (la anterior) |
|---|---|---|---|
| La arquitectura se reconoce en las carpetas (30 %) | 5 | 4 | 1 |
| Reproducibilidad: el código y el documento que lee sus resultados cambian juntos (25 %) | 5 | 2 | 3 |
| Costo de coordinación para un equipo de 2 (20 %) | 5 | 2 | 4 |
| Separación de lo publicable y lo privado (15 %) | 4 | 4 | 1 |
| Colaboración equitativa entre autores (10 %) | 3 | 4 | 3 |
| **Puntaje ponderado (sobre 5)** | **4,65** | **3,10** | **2,30** |

Si se varía cada peso en ±20 %, la opción A sigue ganando en todos los casos, porque su ventaja sobre B (1,55 puntos) es mucho mayor que lo que puede mover ese cambio.

## Evidencia

### Literatura (texto completo leído)

1. **La jerarquía de directorios lleva información arquitectónica.** Puchala et al. (2022) recuperan la arquitectura de tres sistemas combinando dependencias estructurales, semánticas y de directorio.
   - Al agregar la información de directorios a las dependencias estructurales, la exactitud de la recuperación (MoJoFM) mejora en promedio un 32 % (p. 12).
   - Considerar la profundidad de la jerarquía rinde más que solo mirar si dos archivos están en la misma carpeta (pp. 14–15).
   - Los autores reconocen que la calidad de la jerarquía condiciona el resultado: en Hadoop, con pocos directorios y componentes dispersos, la mejora fue mínima (pp. 13, 16).

   *Implicación:* si las carpetas siguen las capas (`frontend/`, `backend/api`, `backend/core` y `backend/ml`, `backend/etl` y `backend/nl2sql`, `base_de_datos/`), la arquitectura se puede reconocer y verificar desde la estructura. El estudio no mide la comprensión humana; por eso se usa como respaldo indirecto.

2. **La estructura del repositorio influye en la colaboración, sin una ganadora universal.** Shakikhanli y Bilicki (2025), en proyectos de código abierto de GitHub, encuentran que:
   - los proyectos con varios repositorios concentran más casos de colaboración alta;
   - en los de repositorio único, la productividad se asocia más a la colaboración;
   - los equipos pequeños colaboran más en ambas estructuras.

   El estudio no evalúa equipos de dos personas y presenta correlaciones sin pruebas de significancia. Por eso **no** se usa como aval del repositorio único, sino como advertencia. La opción A se elige por reproducibilidad y costo de coordinación, y se mitiga su riesgo vigilando que ambos autores contribuyan de forma equilibrada (criterio de 10 %).

3. **Dividir en servicios tiene un costo que no se justifica aquí.** Hassan et al. (2025) señalan que migrar de monolito a microservicios exige un esfuerzo de desarrollo y recursos considerables durante periodos largos, y que el éxito no está garantizado (p. 1). Citan además trabajos según los cuales un monolito modular facilita una migración futura (Mazzara et al., 2021, y Faustino et al., 2024, citados en Hassan et al., 2025, p. 4).

   Por coherencia, el repositorio no se fragmenta por servicio: refleja un backend en capas que podría separarse más adelante si la carga lo exigiera (ver la decisión de arquitectura DT-06).

### Repositorios de referencia (software; consultados el 03/10/2026 con la API de GitHub)

| Repositorio | Qué se tomó | Estrellas · licencia |
|---|---|---|
| [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | `backend/` y `frontend/` (React + Vite) como hermanos en un mismo repositorio | 45.856 · MIT |
| [drivendataorg/cookiecutter-data-science](https://github.com/drivendataorg/cookiecutter-data-science) | Separar datos crudos (no versionados), modelos, documentación y código | 10.083 · MIT |
| [alan2207/bulletproof-react](https://github.com/alan2207/bulletproof-react) | Frontend organizado en páginas, componentes, hooks, servicios y utilidades | 35.939 · MIT |

## Decisión

```
codigo_fuente/      frontend/ (presentación) · backend/ (api → core, ml, nl2sql → etl) · base_de_datos/ · scripts/
documentacion/      avances/ · generador_documentos/ · diagramas/ · figuras/ · matrices/ · literatura/ · decisiones/ · tecnica/ · manuales/ · evidencias/
datos/              instrucciones para obtener OULAD; los archivos se descargan aparte y no se versionan
```

- En la versión 3 el backend quedó en `api`, `core`, `ml`, `nl2sql` y `etl`. La correspondencia entre carpetas y capas está en `codigo_fuente/README.md`.
- No se versionan:
  - los PDF de artículos;
  - los datasets externos;
  - los videos;
  - las credenciales y cuentas (`backend/.env` y `backend/datos_locales/`).

## Consecuencias

- **Se gana:**
  - un solo `git clone` reproduce el sistema y el documento;
  - la arquitectura se ve en las carpetas;
  - lo privado queda fuera por `.gitignore`.
- **Se sacrifica:** independencia de versiones entre el frontend y el backend, que no hace falta con un equipo de dos personas.
- **Riesgo que queda:** que un autor concentre los cambios. Se mitiga revisando las contribuciones por autor antes de cada avance.

## Verificación

- `codigo_fuente/README.md` declara las reglas de dependencia entre capas: el frontend solo usa HTTP y el dominio no importa las rutas.
- La decisión DT-06 traduce esas reglas a `arquitectura_reglas.json`, que se verifica sobre el código con `verificar_reglas.py`.

## Referencias

- Hassan, H., Abdel-Fattah, M. A., & Mohamed, W. (2025). A pattern-based framework for automated migration of monolithic applications to microservices. *Big Data and Cognitive Computing, 9*(10), Article 253. https://doi.org/10.3390/bdcc9100253
- Puchala, S. P. R., Chhabra, J. K., & Rathee, A. (2022). Software architecture recovery using integrated dependencies based on structural, semantic, and directory information. *International Journal of Information System Modeling and Design, 13*(1), 1–20. https://doi.org/10.4018/IJISMD.297060
- Shakikhanli, U., & Bilicki, V. (2025). Repository structures: Impact on collaboration and productivity. *Pollack Periodica, 20*(1), 33–38. https://doi.org/10.1556/606.2024.01123
- Software: repositorios de GitHub citados en la tabla anterior, consultados el 3 de octubre de 2026.
