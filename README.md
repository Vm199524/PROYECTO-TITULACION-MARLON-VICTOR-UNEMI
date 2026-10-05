<a id="readme-top"></a>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/banner-dark.svg">
    <img src=".github/assets/banner-light.svg" alt="UNEMI · VicMar Data AI: predicción del abandono estudiantil en Instituciones de Educación Superior" width="100%">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI/actions/workflows/ci.yml"><img src="https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <img src="https://img.shields.io/badge/versión-Avance_2-FF6900?style=flat-square" alt="Versión: Avance 2">
  <a href="CITATION.cff"><img src="https://img.shields.io/badge/cita-CITATION.cff-002E45?style=flat-square" alt="Cómo citar"></a>
  <a href="#licencia"><img src="https://img.shields.io/badge/licencia-uso_restringido_(titulación)-6E7781?style=flat-square" alt="Licencia"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.14">
  <img src="https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/scikit--learn-1.9-F7931E?style=flat-square&logo=scikitlearn&logoColor=white" alt="scikit-learn">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 18">
  <img src="https://img.shields.io/badge/Vite-5-646CFF?style=flat-square&logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/SQL_Server-2022-CC2927?style=flat-square&logo=microsoftsqlserver&logoColor=white" alt="SQL Server 2022">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

<p align="center">
  <b>Español</b> · <a href="README.en.md">English</a>
</p>

<p align="center">
  Una universidad se entera de que un estudiante abandonó cuando ya no se matricula.<br/>
  <b>VicMar Data AI adelanta ese momento un periodo</b>: estima quién está en riesgo, explica por qué<br/>
  y deja que cualquier autoridad académica lo consulte en español, sin escribir SQL.
</p>

<p align="center">
  <a href="#qué-hace">Qué hace</a> ·
  <a href="#el-sistema-en-acción">En acción</a> ·
  <a href="#cómo-funciona-el-modelo">El modelo</a> ·
  <a href="#resultados">Resultados</a> ·
  <a href="#arquitectura">Arquitectura</a> ·
  <a href="#diagramas">Diagramas</a> ·
  <a href="#inicio-rápido">Inicio rápido</a> ·
  <a href="#documentación">Documentación</a> ·
  <a href="#autores">Autores</a> ·
  <a href="#cómo-citar">Cómo citar</a>
</p>

<p align="center">
  <img src="documentacion/capturas/04_indicadores.png" alt="Panel de indicadores con el riesgo de abandono de cada alumno" width="100%">
  <br/><sub>Panel de indicadores de UNEMI_PRUEBAS: datos sintéticos y cédulas enmascaradas.</sub>
</p>

---

## Qué hace

<table>
<tr>
<td width="33%" valign="top">

### 🎯 Predice
La probabilidad de que cada alumno activo abandone en el **periodo siguiente**, con un umbral elegido para detectar al menos el 80 % de los casos.

</td>
<td width="33%" valign="top">

### 🔍 Explica
Los **tres factores** que más elevan el riesgo de cada alumno (SHAP), redactados en lenguaje natural para quien toma la decisión.

</td>
<td width="33%" valign="top">

### 🧭 Segmenta
Agrupa las carreras por nivel de riesgo (K-Means validado) para saber **qué programas priorizar**.

</td>
</tr>
<tr>
<td valign="top">

### 📊 Compara
Sitúa a la institución frente a **referentes publicados** en revistas científicas, cada uno con su DOI.

</td>
<td valign="top">

### 💬 Responde
*«¿Cuántos alumnos de Sistemas están en riesgo alto?»* → SQL de solo lectura → tabla, gráfico o cifra.

</td>
<td valign="top">

### 🔒 Protege
Cada institución ve **solo sus datos**, garantizado en el propio motor de base de datos. Los datos personales se enmascaran antes de salir del sistema.

</td>
</tr>
</table>

## El sistema en acción

<p align="center">
  <img src=".github/assets/demo_chat.gif" alt="Pregunta en lenguaje natural respondida con una tabla" width="90%">
  <br/><sub>Una pregunta en español se convierte en una consulta de solo lectura y vuelve como tabla.</sub>
</p>

<table>
<tr>
<td width="50%" align="center"><img src="documentacion/capturas/03_conexion_bases.png" alt="Conexión al servidor y elección de la institución"><br/><sub><b>Conexión</b> al servidor y elección de la institución</sub></td>
<td width="50%" align="center"><img src="documentacion/capturas/06_inteligencia_institucional.png" alt="Segmentos de carreras y referentes externos"><br/><sub><b>Inteligencia institucional:</b> segmentos de carreras y referentes con DOI</sub></td>
</tr>
<tr>
<td align="center"><img src="documentacion/capturas/09_panel_riesgo_oulad.png" alt="Panel de riesgo con datos reales de OULAD"><br/><sub><b>Datos reales (OULAD):</b> mismo panel, otra institución</sub></td>
<td align="center"><img src="documentacion/capturas/08_peticion_de_borrado_rechazada.png" alt="Petición de borrado rechazada"><br/><sub><b>Seguridad:</b> una petición de borrar datos se rechaza; nada se ejecuta</sub></td>
</tr>
<tr>
<td align="center"><img src="documentacion/capturas/10_gestion_de_usuarios.png" alt="Gestión de usuarios"><br/><sub><b>Administración:</b> usuarios y roles</sub></td>
<td align="center"><img src="documentacion/capturas/13_movil_riesgo.png" alt="Vista móvil del panel de riesgo" width="45%"><br/><sub><b>Móvil:</b> el mismo panel en el teléfono</sub></td>
</tr>
</table>

## Cómo funciona el modelo

El proyecto sigue **CRISP-DM**, desde la comprensión del negocio hasta el despliegue en el panel y el chat:

<p align="center">
  <img src="documentacion/diagramas/av2_crisp_dm.png" alt="Ciclo CRISP-DM aplicado al proyecto" width="100%">
</p>

```
  Historial del alumno hasta t          Modelo por institución             Salida para la autoridad
 ┌──────────────────────────────┐     ┌──────────────────────────┐     ┌──────────────────────────────┐
 │ promedio y su tendencia      │     │ Random Forest            │     │ p(abandono en t+1) = 0,74    │
 │ asistencia y su tendencia    │ ──▶ │ + ponderación de clases  │ ──▶ │ Riesgo: ALTO                 │
 │ mora, saldo, beca            │     │   o SMOTE                │     │ 1. promedio en descenso      │
 │ sede, modalidad, avance      │     │ umbral para recall ≥ 0,80│     │ 2. asistencia mínima 52 %    │
 └──────────────────────────────┘     └──────────────────────────┘     │ 3. dos periodos con mora     │
                                                                       └──────────────────────────────┘
```
<sub>La salida es ilustrativa; los valores reales se calculan para cada alumno.</sub>

| Decisión | Cómo se resolvió | Por qué |
|---|---|---|
| **Unidad de análisis** | Una fila por *alumno en un periodo*; la etiqueta es si abandona en el siguiente | Predecir, no detectar: una versión anterior usaba datos del mismo periodo del retiro |
| **Sin fuga de información** | Las variables solo usan datos hasta *t*; una misma función arma el panel para entrenar y para calificar | Evita la diferencia entre entrenamiento y uso (*training/serving skew*) |
| **Validación** | `StratifiedGroupKFold` agrupado por alumno + el 25 % más reciente reservado como prueba temporal | Un alumno nunca está a la vez en entrenamiento y en prueba |
| **Comparación justa** | Random Forest frente a regresión logística y *gradient boosting*, con los mismos pliegues | La elección del algoritmo se sostiene con datos |
| **Umbral operativo** | El mayor umbral con recall ≥ 0,80 | No ver a un alumno en riesgo cuesta más que revisar uno de más |
| **Un modelo por institución** | Nunca se mezclan datos de dos instituciones | Privacidad y patrones propios de cada una |

## Resultados

Probado con **dos instituciones**: una sintética, para validar la arquitectura, y una real, para medir el desempeño.

| | **UNEMI_PRUEBAS** | **OULAD_UK** |
|---|:---:|:---:|
| Origen | Sintético y anonimizado | Real · *Open University Learning Analytics Dataset* (Kuzilek et al., 2017, CC BY 4.0) |
| Panel alumno-periodo | 83.678 filas · 14.508 alumnos | 189.299 filas |
| Prevalencia de abandono | 1,87 % | 2,54 % |
| Modelo final | RF + SMOTE | RF + ponderación de clases |
| ROC-AUC · validación cruzada | 0,996 | **0,758** |
| ROC-AUC · prueba temporal | 0,997 | **0,752** |
| ROC-AUC · prospectivo (desenlace real posterior) | — | **0,725** |
| Recall / precisión en el umbral | 0,777 / 0,990 | 0,798 / 0,052 |
| Variable más importante | asistencia | promedio |

> [!IMPORTANT]
> **Lectura honesta de las cifras.** El 0,99 de UNEMI_PRUEBAS lo produce el generador sintético: la asistencia de quien abandona cae un periodo antes y esa sola variable ya separa los casos. **El desempeño realista es el de OULAD (ROC-AUC ≈ 0,75)**, por debajo de la meta inicial de 0,90. La sección 3.3 del Avance 2 discute por qué y qué haría falta para mejorarlo.

<table>
<tr>
<td width="60%"><img src="documentacion/figuras/OULAD_UK_roc_pr.png" alt="Curvas ROC y precisión-recall en OULAD_UK"></td>
<td width="40%"><img src="documentacion/figuras/OULAD_UK_importancia.png" alt="Importancia por permutación en OULAD_UK"></td>
</tr>
<tr>
<td align="center"><sub>ROC y precisión-recall: la validación cruzada y la prueba temporal coinciden, sin señales de sobreajuste.</sub></td>
<td align="center"><sub>En datos reales pesa el rendimiento académico más que la asistencia.</sub></td>
</tr>
</table>

### Consultas en lenguaje natural (NL2SQL)

**40 preguntas de referencia** y **8 ataques adversariales** sobre UNEMI_PRUEBAS, con el rol `ACADEMICO`:

| Exactitud relajada | Exactitud estricta | Ataques bloqueados | Violaciones de aislamiento | Latencia p50 / p95 |
|:---:|:---:|:---:|:---:|:---:|
| **92,5 %** | 50 % | **8 / 8** | **0** | 28 s / 56 s |

<sub>La exactitud relajada acepta el mismo resultado con otra forma (columnas u orden). La estricta exige coincidencia exacta. Después de los ataques, la base quedó sin cambios.</sub>

## Arquitectura

Cliente-servidor desacoplado (SPA + API REST), backend en capas y almacén en esquema estrella con aislamiento por institución en el propio motor.

```mermaid
flowchart LR
  U[("UNEMI_PRUEBAS")] --> E["ETL por perfil<br/>de institución"]
  O[("OULAD_PRUEBAS")] --> E
  E --> W["Almacén CHAT<br/>esquema estrella"]
  W --> ML["Entrenar · calificar<br/>segmentar"] --> W
  W --> V["Vistas VIS_*<br/>filtradas por SESSION_CONTEXT"] --> R["chat_reader<br/>solo lectura"] --> API["API FastAPI"]
  API <--> UI["React<br/>panel + chat"]
  API <--> LLM[["Cascada de LLM<br/>Gemini → Groq → NVIDIA NIM"]]

  style W fill:#002E45,color:#fff
  style V fill:#0E7A4A,color:#fff
  style R fill:#0E7A4A,color:#fff
  style API fill:#FF6900,color:#fff
```

**Seguridad por diseño.** El backend consulta con una cuenta que solo puede leer las vistas `VIS_*`. Cada vista se filtra con `SESSION_CONTEXT`; sin institución en la sesión no devuelve nada (*fail-closed*). Antes de llamar a un proveedor externo, los datos personales se enmascaran.

<details>
<summary><b>Stack tecnológico y alternativas evaluadas</b></summary>
<br/>

| Capa | Elegida | Alternativas comparadas |
|---|---|---|
| Lenguaje del backend | Python 3.14 | Java, Node/TypeScript |
| Framework del backend | FastAPI 0.141 | Django, Flask |
| Frontend | React 18 + Vite | Angular, Vue |
| Almacén de datos | SQL Server 2022 (Docker) | PostgreSQL, MySQL |
| Algoritmo | Random Forest (scikit-learn) | Regresión logística, *gradient boosting* |
| Arquitectura | Cliente-servidor desacoplado | Monolito en capas, microservicios |

Cada decisión tiene una matriz ponderada con análisis de sensibilidad (±20 % en los pesos sin cambio de ganador) y su ADR en [`documentacion/decisiones/`](documentacion/decisiones/). La arquitectura implementada se verifica contra reglas automáticas: 0 violaciones.

</details>

## Diagramas

Los diagramas UML y de datos del Avance 2. Haz clic en cualquiera para verlo en tamaño completo; sus fuentes Mermaid están en [`documentacion/diagramas/`](documentacion/diagramas/).

<table>
<tr>
<td width="33%" align="center"><a href="documentacion/diagramas/av2_casos_uso.png"><img src=".github/assets/galeria/av2_casos_uso.png" alt="Casos de uso"></a><br/><sub><b>Casos de uso</b></sub></td>
<td width="33%" align="center"><a href="documentacion/diagramas/av2_arquitectura.png"><img src=".github/assets/galeria/av2_arquitectura.png" alt="Arquitectura del sistema"></a><br/><sub><b>Arquitectura del sistema</b></sub></td>
<td width="33%" align="center"><a href="documentacion/diagramas/av2_modelo_dimensional.png"><img src=".github/assets/galeria/av2_modelo_dimensional.png" alt="Modelo dimensional del almacén"></a><br/><sub><b>Modelo dimensional del almacén</b></sub></td>
</tr>
<tr>
<td align="center"><a href="documentacion/diagramas/av2_secuencia_nl2sql.png"><img src=".github/assets/galeria/av2_secuencia_nl2sql.png" alt="Secuencia de una pregunta en lenguaje natural"></a><br/><sub><b>Secuencia: pregunta en lenguaje natural</b></sub></td>
<td align="center"><a href="documentacion/diagramas/av2_secuencia_lotes.png"><img src=".github/assets/galeria/av2_secuencia_lotes.png" alt="Secuencia de los procesos por lotes"></a><br/><sub><b>Secuencia: procesos por lotes</b></sub></td>
<td align="center"><a href="documentacion/diagramas/av2_colaboracion.png"><img src=".github/assets/galeria/av2_colaboracion.png" alt="Colaboración entre componentes"></a><br/><sub><b>Colaboración entre componentes</b></sub></td>
</tr>
<tr>
<td align="center"><a href="documentacion/diagramas/av2_actividad_etl.png"><img src=".github/assets/galeria/av2_actividad_etl.png" alt="Actividades del ETL"></a><br/><sub><b>Actividades: ETL por institución</b></sub></td>
<td align="center"><a href="documentacion/diagramas/av2_actividad_modelo.png"><img src=".github/assets/galeria/av2_actividad_modelo.png" alt="Actividades del modelo predictivo"></a><br/><sub><b>Actividades: modelo predictivo</b></sub></td>
<td align="center"><a href="documentacion/diagramas/av2_estados.png"><img src=".github/assets/galeria/av2_estados.png" alt="Estados de la trayectoria de matrícula"></a><br/><sub><b>Estados: trayectoria de matrícula</b></sub></td>
</tr>
</table>

## Inicio rápido

> [!TIP]
> **¿Primera vez?** Sigue el [Manual técnico de instalación](documentacion/manuales/MANUAL_TECNICO_DE_INSTALACION.md), paso a paso desde una computadora nueva, y luego el [Manual de usuario](documentacion/manuales/MANUAL_DE_USUARIO.md).

**Requisitos:** Python 3.14 · Node.js 22+ · Docker Desktop · ODBC Driver 18 for SQL Server

```powershell
# 1. Backend
py -3.14 -m venv codigo_fuente\backend\venv
codigo_fuente\backend\venv\Scripts\pip install -r codigo_fuente\backend\requirements.txt

# 2. Frontend
cd codigo_fuente\frontend; npm install; cd ..\..

# 3. Configuración local (no se versiona)
copy codigo_fuente\backend\.env.example codigo_fuente\backend\.env
copy codigo_fuente\backend\usuarios_prueba.example.json codigo_fuente\backend\usuarios_prueba.local.json

# 4. Pipeline completo: bases, ETL, entrenamiento, calificación, segmentación, referentes, diccionario y pruebas
powershell -ExecutionPolicy Bypass -File codigo_fuente\scripts\demo_tesis.ps1 -Levantar
```

| Servicio | Dirección |
|---|---|
| Aplicación | `http://localhost:3000` |
| API y documentación interactiva | `http://127.0.0.1:8090/docs` |
| SQL Server (Docker) | `localhost,1433` |

<details>
<summary><b>Pruebas, evaluación y documento de titulación</b></summary>
<br/>

```powershell
cd codigo_fuente\backend
venv\Scripts\python -m pytest                                    # unitarias + integración (las de integración se omiten sin SQL Server)
venv\Scripts\python -m eval.evaluar_nl2sql                       # exactitud del NL2SQL con las 40 preguntas de referencia
venv\Scripts\python -m ml.reporte_validacion --empresa OULAD_UK  # figuras de validación

cd ..\frontend
npm test                                                         # pruebas del frontend (vitest)

cd ..\..\documentacion\generador_documentos
python _build_avance2.py                                         # genera el Avance 2 desde el formato oficial UNEMI
python _verificar_coherencia.py                                  # citas ↔ referencias, cifras ↔ resultados, páginas mínimas
```

Las pruebas del backend y del frontend, y el *build*, corren en GitHub Actions con cada cambio. Ninguna cifra del documento de titulación se escribe a mano: el generador la lee de los resultados que produce el código.

</details>

<details>
<summary><b>Estructura del repositorio</b></summary>
<br/>

```
├── codigo_fuente/
│   ├── frontend/              Presentación · React + Vite (panel de riesgo, segmentos, referentes, chat)
│   ├── backend/               API FastAPI en capas
│   │   ├── api/                 rutas HTTP
│   │   ├── core/                NL2SQL, seguridad y privacidad
│   │   ├── ml/                  modelo predictivo, segmentación, reportes de validación
│   │   ├── etl/ knowledge/      perfiles por institución, catálogo de métricas certificadas
│   │   └── eval/ tests/         evaluación NL2SQL y pruebas
│   ├── base_de_datos/         Esquema estrella, vistas VIS_*, usuario de solo lectura, datos de prueba anonimizados
│   └── scripts/               Pipeline reproducible de punta a punta (demo_tesis.ps1)
├── documentacion/
│   ├── avances/               Avance 1 y Avance 2 (.docx y .pdf)
│   ├── generador_documentos/  Genera el Avance desde el formato oficial y verifica su coherencia
│   ├── diagramas/             UML: casos de uso, secuencia, actividades, estados, colaboración, modelo dimensional
│   ├── figuras/               ROC/PR, matriz de confusión, importancia, comparación CV, selección de k
│   ├── decisiones/            Matrices ponderadas y ADR de tecnología, arquitectura y estructura
│   ├── literatura/            Búsquedas Scopus (RIS) · 13 trabajos previos comparados
│   ├── matrices/              Matrices metodológicas
│   ├── tecnica/               Modelo, benchmarking, base de pruebas, diccionario de datos, instalación
│   └── PLAN_Y_ESTADO_DEL_PROYECTO.md
└── datos/                     Cómo obtener el dataset OULAD (no se versiona)
```

La organización por capas se justifica con literatura científica y repositorios de referencia en [`ADR-000`](documentacion/decisiones/ADR-000-estructura-del-repositorio.md).

</details>

## Documentación

**Manuales de entrega** (Markdown, Word y PDF en [`documentacion/manuales/`](documentacion/manuales/)):

| Manual | Para quién |
|---|---|
| [Manual de usuario](documentacion/manuales/MANUAL_DE_USUARIO.md) | Autoridades, bienestar estudiantil y administradores: cómo conectarse, leer el panel y consultar |
| [Manual técnico de instalación](documentacion/manuales/MANUAL_TECNICO_DE_INSTALACION.md) | Personal de TI: instalar, configurar, cargar datos y verificar |
| [Guía de pruebas de aceptación](documentacion/manuales/GUIA_DE_PRUEBAS_DE_ACEPTACION.md) | Quien recibe el sistema: casos de prueba paso a paso y acta de aceptación |

| Documento | Contenido |
|---|---|
| [Plan y estado del proyecto](documentacion/PLAN_Y_ESTADO_DEL_PROYECTO.md) | Exigencias de las tutoras, avance y pendientes |
| [Predicción del abandono](documentacion/tecnica/PREDICCION_ABANDONO.md) | Datos, variables, validación y resultados |
| [Benchmarking institucional](documentacion/tecnica/BENCHMARKING_INSTITUCIONAL.md) | Referentes externos y segmentación de carreras |
| [Base de datos de pruebas](documentacion/tecnica/BASE_DE_DATOS_DE_PRUEBAS.md) | Bases, anonimización y reconstrucción |
| [Diccionario de datos](documentacion/tecnica/DICCIONARIO_DE_DATOS.md) | Generado desde el esquema real |
| [Decisiones de diseño](documentacion/decisiones/) | Matrices ponderadas y ADR |
| [Diagramas UML](documentacion/diagramas/) | Fuentes Mermaid y figuras |

## Estado del proyecto

```
 Anteproyecto ━━━━━━ Avance 1 ━━━━━━ Avance 2 ━━━━━━ Avance 3 ━━━━━━ Defensa
      ✔                 ✔               ✔                ◌               ◌
```

- [x] Modelo predictivo validado en dos instituciones, con explicación SHAP
- [x] Segmentación de carreras y comparación con referentes publicados
- [x] Consultas en lenguaje natural con aislamiento por institución
- [x] Decisiones de tecnología y arquitectura con matrices y ADR
- [x] Comparación crítica de 13 trabajos previos frente al presente caso
- [x] Pruebas automáticas del backend y del frontend en GitHub Actions
- [ ] Capturas y video de la demostración
- [ ] Prueba con usuarios sin perfil técnico
- [ ] Avance 3: resultados finales, conclusiones y recomendaciones

## Cómo citar

GitHub muestra el botón **«Cite this repository»** a partir de [`CITATION.cff`](CITATION.cff). En APA 7:

> Pérez Almachi, M. D., y Lluilema Pisco, V. M. (2026). *VicMar Data AI: modelo predictivo de abandono estudiantil mediante inteligencia de negocios y procesamiento de lenguaje natural* (Versión avance-2) [Software]. Universidad Estatal de Milagro. https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI

## Licencia

Mientras dure el proceso de titulación, este repositorio es privado y su uso está restringido a los autores, las docentes tutoras y la Universidad Estatal de Milagro. La licencia definitiva la establecerá el Departamento Legal de la UNEMI al liberar el proyecto.

Los datos de UNEMI_PRUEBAS son sintéticos. OULAD se usa bajo licencia CC BY 4.0 y no se redistribuye en este repositorio.


## Autores

<table align="center">
<tr>
<td align="center" width="50%">
<a href="https://github.com/ing-MarlonPerez"><img src=".github/assets/autores/marlon.png" width="140" alt="Marlon David Pérez Almachi"></a><br/>
<b>Marlon David Pérez Almachi</b><br/>
<sub>Autor · <a href="https://github.com/ing-MarlonPerez">@ing-MarlonPerez</a></sub>
</td>
<td align="center" width="50%">
<a href="https://github.com/Vm199524"><img src=".github/assets/autores/victor.png" width="140" alt="Víctor Manuel Lluilema Pisco"></a><br/>
<b>Víctor Manuel Lluilema Pisco</b><br/>
<sub>Autor · <a href="https://github.com/Vm199524">@Vm199524</a></sub>
</td>
</tr>
</table>

<p align="center"><sub>Docentes tutoras: Mirella Azucena Peralta Correa · María Gabriela Espinoza Bravo</sub></p>

<p align="center">
  <a href="#readme-top">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".github/assets/footer-dark.svg">
      <img src=".github/assets/footer-light.svg" alt="Universidad Estatal de Milagro · VicMar Data AI · Volver arriba" width="100%">
    </picture>
  </a>
</p>
