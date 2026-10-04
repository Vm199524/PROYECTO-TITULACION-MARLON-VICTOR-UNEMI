<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/banner-dark.svg">
    <img src=".github/assets/banner-light.svg" alt="UNEMI · VicMar Data AI: student dropout prediction for higher education institutions" width="100%">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI/actions/workflows/ci.yml"><img src="https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="CITATION.cff"><img src="https://img.shields.io/badge/cite-CITATION.cff-002E45?style=flat-square" alt="Cite"></a>
  <a href="#license"><img src="https://img.shields.io/badge/license-restricted_(thesis)-6E7781?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="README.md">Español</a> · <b>English</b>
</p>

<p align="center">
  A university learns that a student dropped out when they fail to re-enrol.<br/>
  <b>VicMar Data AI moves that moment one term earlier</b>: it estimates who is at risk, explains why,<br/>
  and lets academic staff ask questions in plain Spanish, without writing SQL.
</p>

---

**Undergraduate thesis project** — Universidad Estatal de Milagro (UNEMI), Ecuador. Authors: Marlon David Pérez Almachi and Víctor Manuel Lluilema Pisco. The full documentation is in Spanish.

## What it does

| | |
|---|---|
| 🎯 **Predicts** | Probability that each active student drops out **next term**, with a threshold tuned for recall ≥ 0.80 |
| 🔍 **Explains** | The three factors that raise each student's risk (SHAP), in plain language |
| 🧭 **Segments** | Groups degree programmes by risk level (validated K-Means) |
| 📊 **Benchmarks** | Compares the institution with published figures, each with its DOI |
| 💬 **Answers** | Natural-language questions → read-only SQL → table, chart or figure |
| 🔒 **Protects** | Per-institution isolation enforced inside the database engine (`SESSION_CONTEXT`, fail-closed); personal data masked before any external call |

## Model

A **student-term panel**: each row is a student in term *t*, built only with information available up to *t*, labelled with whether they drop out in *t+1*. One **Random Forest per institution**, tuned with `StratifiedGroupKFold` grouped by student, compared on the same folds against logistic regression and gradient boosting, and evaluated once on the most recent 25 % of the panel (temporal hold-out).

| | UNEMI_PRUEBAS (synthetic) | OULAD_UK (real) |
|---|:---:|:---:|
| Student-term rows | 83,678 | 189,299 |
| Dropout prevalence | 1.87 % | 2.54 % |
| ROC-AUC · cross-validation | 0.996 | **0.758** |
| ROC-AUC · temporal test | 0.997 | **0.752** |
| ROC-AUC · prospective (later real outcome) | — | **0.725** |
| Recall / precision at threshold | 0.777 / 0.990 | 0.798 / 0.052 |

> [!IMPORTANT]
> The 0.99 on the synthetic dataset is an artefact of its generator. **Realistic performance is the OULAD result (ROC-AUC ≈ 0.75)**, below the initial 0.90 target; the thesis discusses why. OULAD: Open University Learning Analytics Dataset (Kuzilek et al., 2017, CC BY 4.0).

**NL2SQL** (40 reference questions + 8 adversarial prompts): 92.5 % relaxed execution accuracy, 50 % strict, 8/8 attacks blocked, 0 isolation violations.

## Stack

Python 3.14 · FastAPI · scikit-learn · SHAP · React 18 + Vite · SQL Server 2022 (Docker) · LLM cascade (Gemini → Groq → NVIDIA NIM). Client–server architecture (SPA + REST API) with a layered backend and a star-schema warehouse. Each technology choice is backed by a weighted decision matrix with sensitivity analysis and an ADR in [`documentacion/decisiones/`](documentacion/decisiones/).

## Quick start (Windows)

```powershell
py -3.14 -m venv codigo_fuente\backend\venv
codigo_fuente\backend\venv\Scripts\pip install -r codigo_fuente\backend\requirements.txt
cd codigo_fuente\frontend; npm install; cd ..\..
copy codigo_fuente\backend\.env.example codigo_fuente\backend\.env
copy codigo_fuente\backend\usuarios_prueba.example.json codigo_fuente\backend\usuarios_prueba.local.json
powershell -ExecutionPolicy Bypass -File codigo_fuente\scripts\demo_tesis.ps1 -Levantar
```

App at `http://localhost:3000`, API docs at `http://127.0.0.1:8090/docs`.

## Citation

See [`CITATION.cff`](CITATION.cff) or use GitHub's **"Cite this repository"** button.

## License

During the thesis process this repository is private and its use is restricted to the authors, their supervisors and Universidad Estatal de Milagro. The final license will be set by UNEMI's Legal Department when the project is released.

<p align="center"><sub>© 2026 Marlon David Pérez Almachi and Víctor Manuel Lluilema Pisco</sub></p>
