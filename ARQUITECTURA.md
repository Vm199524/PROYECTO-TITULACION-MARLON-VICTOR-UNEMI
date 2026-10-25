# Código fuente

El código del sistema está en las carpetas `frontend/`, `backend/`, `base_de_datos/` y `scripts/` de la raíz del repositorio. La arquitectura es **cliente-servidor desacoplada**
(aplicación web de una sola página y API REST) con un **backend en capas** y una capa de datos que
aísla a cada institución en el propio motor de base de datos. La decisión está documentada en
`documentacion/decisiones/DT-06_arquitectura.json` y en el Avance 2 (sección 3.2.1).

```
(raíz del repositorio)
├── frontend/                   CAPA DE PRESENTACIÓN (React 18 + TypeScript + Vite + Tailwind)
│   └── src/
│       ├── paginas/            Panel ejecutivo, Estudiantes en riesgo, Ficha, Seguimiento,
│       │                       Consulta conversacional, Carreras, Referentes, Calidad del modelo,
│       │                       Reportes, Mi cuenta y admin/ (Usuarios, Auditoría, Estado)
│       ├── componentes/        layout (barra lateral, navegación por capacidades), ui, gráficos,
│       │                       marca (logotipo) y diálogos de seguimiento
│       ├── lib/                cliente de la API, sesión, permisos por rol, formato numérico, tema
│       └── pruebas/            pruebas de interfaz (vitest)
│
├── backend/                    SERVIDOR (FastAPI, en capas)
│   ├── main.py                 punto de entrada: monta los routers y la documentación /docs
│   ├── api/                    capa de servicio: sesion, panel, estudiantes, seguimiento, consulta,
│   │                           carreras, referentes, modelo, reportes y admin (27 endpoints)
│   ├── core/                   transversal: configuración, conexiones con SESSION_CONTEXT, seguridad
│   │                           (JWT y capacidades por rol), usuarios, auditoría, privacidad, reportes
│   ├── ml/                     analítica: panel estudiante-periodo, entrenamiento y validación,
│   │                           calibración, calificación, explicación SHAP, simulación, segmentación,
│   │                           exploración y figuras; modelos/<INSTITUCION>/ guarda las métricas
│   ├── nl2sql/                 consulta conversacional: guardarraíles, enrutador sobre 40 métricas
│   │                           certificadas, cascada de proveedores de IA, validador del árbol SQL,
│   │                           redactor de la respuesta
│   ├── etl/                    perfiles de mapeo por institución, ETL al almacén y referentes externos
│   ├── scripts/                procesos por lotes: pipeline.py (orquestador), cargas de UNEMI y OULAD,
│   │                           diccionario de datos y cuentas de demostración
│   ├── eval/                   conjunto dorado (40 preguntas, 12 de robustez y 8 adversariales)
│   │                           y evaluador de la consulta conversacional
│   ├── tests/                  pruebas unitarias y de integración (pytest)
│   └── requirements.txt        versiones fijadas (requirements.lock.txt para reproducir exacto)
│
├── base_de_datos/              CAPA DE DATOS (SQL Server 2022)
│   ├── crear_almacen_academico.sql   almacén en esquema estrella, vistas VIS_* filtradas por
│   │                                 SESSION_CONTEXT, procedimientos de seguimiento y cuentas
│   │                                 chat_reader y app_seguimiento
│   └── datos_de_prueba/        generador del conjunto sintético UNEMI_PRUEBAS (semilla 20260909)
│
└── scripts/
    ├── reconstruir_sistema.bat entorno, dependencias, SQL Server y procesos por lotes en Windows
    ├── levantar_sistema.bat    abre la API (8090) y la aplicación web (3000)
    └── demo_tesis.ps1          reconstrucción completa y guion de la demostración
```

## Reglas de dependencia entre capas

- `frontend` solo habla con el backend por HTTP; nunca accede a la base de datos.
- `api/` usa `core/`, `ml/` y `nl2sql/`; ninguna capa de dominio importa las rutas.
- Toda lectura de la API y todo SQL de la consulta conversacional se ejecutan con `chat_reader`, que
  solo puede leer las vistas `VIS_*` de la institución activa. El registro de seguimiento usa
  `app_seguimiento`, que solo ejecuta dos procedimientos. La cuenta de administración la usan
  únicamente los procesos por lotes.
- Las credenciales se leen de `backend/.env` y las cuentas de usuario de `backend/datos_locales/`;
  ninguno de los dos se versiona.

## Comandos frecuentes

```bat
scripts\reconstruir_sistema.bat              :: todo, de punta a punta
scripts\reconstruir_sistema.bat --desde calificar
scripts\reconstruir_sistema.bat --con-consulta   :: incluye la evaluación con proveedores de IA
scripts\levantar_sistema.bat
cd backend  && venv\Scripts\python -m pytest -q
cd frontend && npm test
```

Instalación paso a paso: [`documentacion/manuales/MANUAL_TECNICO_DE_INSTALACION.md`](../documentacion/manuales/MANUAL_TECNICO_DE_INSTALACION.md).
