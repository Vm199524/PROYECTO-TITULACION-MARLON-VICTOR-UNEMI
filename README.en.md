<a id="readme-top"></a>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/banner-dark.svg">
    <img src=".github/assets/banner-light.svg" alt="UNEMI · VicMar: early warning of university student dropout" width="100%">
  </picture>
</p>

<p align="center"><a href="README.md">Español</a> · <b>English</b></p>

<p align="center">
  <img src=".github/assets/logo-vicmar.svg" alt="VicMar mark: a graduation cap over the student's path and the early-warning dot" width="128"><br/>
  <sub><b>VICMAR</b> · EARLY WARNING OF STUDENT DROPOUT</sub>
</p>

<p align="center">
  Universities usually learn that a student dropped out when the student fails to re-enroll.<br/>
  <b>VicMar moves that moment one term earlier</b>: it estimates who is at risk, explains why,<br/>
  supports follow-up and lets academic authorities ask for any figure in Spanish, without writing SQL.
</p>

<p align="center">
  <img src=".github/assets/apertura.gif" alt="VicMar opening screen: the emblem draws the student's path, lights the alert and shows six capabilities around the sign-in card" width="100%">
  <br/><sub>Opening screen: the emblem draws the student's path, lights the early-warning dot and shows the six capabilities around the sign-in card.</sub>
</p>

> **Undergraduate capstone project.** *Web-based prototype to predict university student dropout through machine learning and conversational querying.* Information Technology Engineering, State University of Milagro (UNEMI), Ecuador, 2026.

## What it does

| | |
|---|---|
| 🎯 **Predicts** | Calibrated probability that each active student drops out **next term**, with medium and high risk thresholds set by target recall (0.80 and 0.50). |
| 🔍 **Explains** | The three main reasons behind each student's risk (SHAP), a "what if" simulator and suggested actions. |
| 🤝 **Supports follow-up** | Student-support staff log and close tutoring, counselling, financial aid and referrals. |
| 💬 **Answers** | Questions in Spanish are answered by one of **40 certified metrics**; otherwise, LLM-generated SQL is validated on its syntax tree before running. |
| 🧭 **Prioritises programs** | K-means grouping of programs, validated with silhouette, resampling and Kruskal-Wallis. |
| 🔒 **Protects** | Each institution only sees its own data, enforced in SQL Server through `SESSION_CONTEXT` and least-privilege accounts, in line with Ecuador's data-protection law (LOPDP). |

## Visual identity

<table>
<tr>
<td width="140" align="center"><img src=".github/assets/logo-vicmar.svg" alt="VicMar mark" width="112"></td>
<td>

The mark is a tile in **UNEMI orange**: the **graduation cap** is the goal, the **broken line** is the student's path term by term, and the **pulsing dot** at its end is the early warning that lights up before the path breaks. In the app the tile spins on its axis and shows detection waves on its back; every animation stops when the device asks for reduced motion. The name joins its authors: **Vic**tor and **Mar**lon.

</td>
</tr>
</table>

## See it in action

<p align="center">
  <img src=".github/assets/recorrido.gif" alt="Walkthrough: sign-in, executive dashboard, students at risk and a student's record with the what-if simulator" width="100%">
  <br/><sub>Student-support walkthrough: sign-in, executive dashboard, prioritised list and a student's record with suggested actions and the what-if simulator.</sub>
</p>

<p align="center">
  <img src=".github/assets/demo_consulta.gif" alt="A question answered by a certified metric" width="90%">
  <br/><sub>Conversational querying: the question is answered by a certified metric and comes back as a chart, a table and a summary.</sub>
</p>

## What is new in version 3

Version 3 consolidates the academic focus: the whole system, from the database to the interface, is built for **early warning of student dropout**, and every layer was scaled up.

| Area | Version 3 |
|---|---|
| Scope | Students, programs, terms and student support; several institutions in one warehouse, isolated inside the database engine |
| Model | Student-term panel, four algorithms compared, Optuna-tuned LightGBM, Platt calibration, recall-based thresholds, SHAP and drift monitoring (PSI) |
| Validation | Student-grouped cross-validation, temporal test and prospective evaluation on real data (OULAD) |
| Querying | 40 certified metrics, a cascade of four AI providers and syntax-tree validation; the AI never writes nor reads another institution |
| Users | Three roles (academic authority, student support, IT administration), role capabilities, audit log and lockout after failed attempts |
| Interface | Own visual identity (animated mark in UNEMI orange), opening screen with six capabilities, executive dashboard, student profile with a what-if simulator, follow-up, PDF and Excel reports, light and dark themes, mobile layout |
| Operations | `reconstruir_sistema.bat` rebuilds everything end to end; 178 backend tests (8 need SQL Server) and 11 front-end tests |

## Screenshots

<table>
<tr>
<td width="50%" align="center"><img src="documentacion/capturas/av2_cap_panel.png" alt="Executive dashboard"><br/><sub><b>Executive dashboard:</b> institutional thermometer and term reading</sub></td>
<td width="50%" align="center"><img src="documentacion/capturas/av2_cap_ficha.png" alt="Student profile"><br/><sub><b>Student profile:</b> probability, reasons, simulator, actions</sub></td>
</tr>
<tr>
<td align="center"><img src="documentacion/capturas/av2_cap_estudiantes.png" alt="Prioritised list"><br/><sub><b>Prioritised list</b> of students at risk</sub></td>
<td align="center"><img src="documentacion/capturas/av2_cap_consulta.png" alt="Conversational querying"><br/><sub><b>Conversational querying</b> with the answer's origin</sub></td>
</tr>
<tr>
<td align="center"><img src="documentacion/capturas/av2_cap_carreras.png" alt="Program segmentation"><br/><sub><b>Programs:</b> segments and clustering soundness</sub></td>
<td align="center"><img src="documentacion/capturas/av2_cap_calidad.png" alt="Model quality"><br/><sub><b>Model quality</b> explained for decision makers</sub></td>
</tr>
<tr>
<td align="center"><img src="documentacion/capturas/av2_cap_seguimiento.png" alt="Follow-up"><br/><sub><b>Follow-up</b> of support actions</sub></td>
<td align="center"><img src="documentacion/capturas/av2_cap_panel_oulad.png" alt="Real OULAD data"><br/><sub><b>Real data (OULAD):</b> same system, another institution</sub></td>
</tr>
<tr>
<td align="center"><img src="documentacion/capturas/av2_cap_panel_oscuro.png" alt="Dark theme"><br/><sub><b>Dark theme</b></sub></td>
<td align="center"><img src="documentacion/capturas/av2_cap_usuarios.png" alt="Users and roles"><br/><sub><b>Users and roles</b> with assigned institutions</sub></td>
</tr>
</table>

<p align="center">
  <img src="documentacion/capturas/av2_cap_movil_panel.png" alt="Dashboard on a phone" width="30%">
  &nbsp;&nbsp;
  <img src="documentacion/capturas/av2_cap_movil_estudiantes.png" alt="List on a phone" width="30%">
  <br/><sub>The same app on a phone. Screens are in Spanish, the system's working language.</sub>
</p>

## Method

CRISP-DM on a **student-term panel**: each row holds what was known at the end of term *t*; the label is whether the student withdrew in *t + 1*. Logistic regression, class-weighted Random Forest, Random Forest with SMOTE and Optuna-tuned LightGBM are compared through **student-grouped 5-fold cross-validation**, a **temporal test** on the most recent terms and a **prospective evaluation** (OULAD 2014J). The selected model is Platt-calibrated and explained with SHAP; each run validates data quality with Great Expectations, measures drift with Evidently (plus PSI) and is logged in MLflow; Metabase offers an aggregated, personal-data-free query path.

## Results

**UNEMI_PRUEBAS** is **synthetic** test data that replicates UNEMI's structure (14,508 students, 2019 to 2026); **OULAD** is **real anonymised** data from the Open University (Kuzilek et al., 2017).

| Temporal test | UNEMI_PRUEBAS | OULAD (real) |
|---|---|---|
| Selected model (cross-validated ROC-AUC) | LightGBM (0.828 ± 0.003) | LightGBM (0.804 ± 0.012) |
| ROC-AUC | **0.829** | **0.768** |
| PR-AUC (prevalence) | 0.466 (0.065) | 0.104 (0.031) |
| Recall at the medium threshold | 0.781 | 0.787 |
| Dropouts within the top 20 % risk | 67.9 % | 55.4 % |
| Rolling-origin backtest (each term predicted from past terms only) | 0.827 to 0.836 (4 terms) | 0.742 to 0.779 (2 terms) |
| Prospective evaluation (2014J) | | **ROC-AUC 0.764 · recall 0.913** |

Conversational querying (SQL Server 2022 with AI providers, 52 golden-set questions): 100% execution accuracy (65% of the base questions with an exact column match); 33 answered by certified metrics and 19 by validated generated SQL; 8/8 malicious prompts contained; zero cross-institution reads; median response time 77 ms.

## Architecture

Decoupled client-server style with a layered backend: SQL Server 2022 star-schema warehouse with governed `VIS_*` views; batch analytics (ETL, training, scoring, segmentation); FastAPI service layer (27 REST endpoints, JWT, roles, audit log, privacy, conversational engine, PDF and Excel reports); React 18 + TypeScript front end with light and dark themes.

<p align="center"><img src="documentacion/diagramas/av2_arquitectura.png" alt="Architecture" width="90%"></p>

## Getting started (Windows)

From the repository root, one command installs whatever is missing and starts everything:

```bat
npm start                   &REM or double-click iniciar.bat
```

The first run creates `backend\.env` from `.env.example`; fill in passwords, `JWT_SECRET_KEY` and AI keys. To load the data and train the models from scratch: `npm run reconstruir -- --con-consulta`.

The API runs on http://localhost:8090 (`/docs`) and the web app on http://localhost:3000. Demo accounts (`autoridad.demo`, `bienestar.demo`, `admin.ti`) get random passwords stored only in `backend/datos_locales/usuarios_demo.local.json`.

Tests: `python -m pytest -q` (backend, 170 tests plus 8 SQL Server integration tests) and `npm test` (front end, 11 tests).

## Documentation

[Final report (Spanish, PDF)](documentacion/avances/TRABAJO_FINAL_MARLON_VICTOR.pdf) · [Data governance (Spanish)](documentacion/gobierno_datos/GOBIERNO_DE_DATOS.md) · [User manual](documentacion/manuales/MANUAL_DE_USUARIO.md) · [Installation manual](documentacion/manuales/MANUAL_TECNICO_DE_INSTALACION.md) · [Acceptance tests](documentacion/manuales/GUIA_DE_PRUEBAS_DE_ACEPTACION.md)

## Citation

> Pérez Almachi, M. D., & Lluilema Pisco, V. M. (2026). *Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional* (Version 3.0.0) [Computer software]. Universidad Estatal de Milagro. https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI

## Authors

**Marlon David Pérez Almachi** ([@ing-MarlonPerez](https://github.com/ing-MarlonPerez)) · **Víctor Manuel Lluilema Pisco** ([@Vm199524](https://github.com/Vm199524))

Use is restricted to the authors and UNEMI during the degree process. UNEMI_PRUEBAS data are synthetic; OULAD is used under CC BY 4.0 and is not redistributed.

<p align="center">
  <a href="#readme-top">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".github/assets/footer-dark.svg">
      <img src=".github/assets/footer-light.svg" alt="UNEMI · VicMar · Back to top" width="100%">
    </picture>
  </a>
</p>
