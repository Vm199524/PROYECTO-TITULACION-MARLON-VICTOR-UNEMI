# Arquitectura detectada en `C:\Tesis Marlon Y Victor\codigo_fuente`

## Estilo inferido (heurístico)

- **cliente-servidor desacoplado (SPA + API)** — cliente en frontend; API en backend; 49 rutas de API
- **backend en capas** — backend: carpetas api, core, data

## Lenguajes

- Python: 92 archivos
- JavaScript (JSX): 37 archivos
- JavaScript: 22 archivos
- SQL: 1 archivos
- TypeScript: 1 archivos

## Frameworks en uso por aplicación

- `backend`: scikit-learn (ml), FastAPI (backend), SQLAlchemy (datos)
- `frontend`: React (frontend)

## Dependencias declaradas que el código no importa

- `backend`: langchain, openai

## Desplegables (2)

- `backend`
- `frontend`

## Bases de datos: Redis, SQL Server (ODBC) · Mensajería: —

## Rutas de API

- FastAPI/Flask: 49

## Dependencias entre componentes (imports)

| Origen → destino | Imports | Ejemplos |
|---|---|---|
| backend -> backend/core | 38 | backend/main.py:100; backend/main.py:101; backend/main.py:102 |
| backend/api -> backend/core | 31 | backend/api/routes_quantum_core.py:8; backend/api/routes_quantum_core.py:10; backend/api/routes_quantum_core.py:11 |
| backend/tests -> backend/core | 30 | backend/tests/test_aislamiento_empresas.py:22; backend/tests/test_alcance.py:22; backend/tests/test_capa_seguridad_bd.py:23 |
| backend/tests -> backend | 25 | backend/tests/test_capa_seguridad_bd.py:58; backend/tests/test_capa_seguridad_bd.py:154; backend/tests/test_invitado_demo.py:171 |
| backend/core -> backend | 14 | backend/core/aprendizaje.py:176; backend/core/audit_log.py:44; backend/core/bi_snapshot_store.py:27 |
| backend/tests -> backend/api | 14 | backend/tests/test_invitado_demo.py:99; backend/tests/test_invitado_demo.py:109; backend/tests/test_invitado_demo.py:120 |
| backend/scripts -> backend | 10 | backend/scripts/crear_usuario_desarrollador.py:47; backend/scripts/crear_usuario_desarrollador.py:49; backend/scripts/etl_academico.py:34 |
| backend/api -> backend | 9 | backend/api/routes_quantum_core.py:13; backend/api/routes_query.py:48; backend/api/routes_query.py:63 |
| backend/eval -> backend | 4 | backend/eval/evaluar_nl2sql.py:53; backend/eval/evaluar_nl2sql.py:55; backend/eval/evaluar_nl2sql.py:175 |
| backend/ml -> backend | 4 | backend/ml/clustering_institucional.py:54; backend/ml/entrenar_abandono.py:77; backend/ml/predecir_abandono.py:39 |
| backend -> backend/api | 3 | backend/main.py:2737; backend/main.py:2738; backend/main.py:2739 |
| backend -> backend/knowledge | 2 | backend/main.py:1151; backend/main.py:1152 |
| backend/cache -> backend | 2 | backend/cache/query_cache.py:16; backend/cache/redis_manager.py:10 |
| backend/core -> backend/cache | 2 | backend/core/session_history_store.py:20; backend/core/session_state_store.py:27 |
| backend -> backend/cache | 1 | backend/main.py:97 |
| backend/api -> backend/cache | 1 | backend/api/routes_query.py:46 |
| backend/api -> backend/knowledge | 1 | backend/api/routes_query.py:62 |
| backend/etl -> backend | 1 | backend/etl/etl_benchmarking.py:36 |
| backend/eval -> backend/api | 1 | backend/eval/evaluar_nl2sql.py:176 |
| backend/eval -> backend/core | 1 | backend/eval/evaluar_nl2sql.py:186 |
| backend/knowledge -> backend/cache | 1 | backend/knowledge/memory_consolidator.py:11 |
| backend/scripts -> backend/core | 1 | backend/scripts/crear_usuario_desarrollador.py:118 |
| backend/scripts -> backend/etl | 1 | backend/scripts/etl_academico.py:33 |
| backend/tests -> backend/ml | 1 | backend/tests/test_panel_abandono.py:20 |
