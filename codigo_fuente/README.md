# Código fuente

Todo el código del sistema está en esta carpeta, organizado por la arquitectura elegida: **cliente-servidor desacoplado (SPA + API REST) con backend en capas** y una capa de datos que aísla a cada institución en el propio motor de base de datos (ver `documentacion/decisiones/`).

```
codigo_fuente/
├── frontend/                 CAPA DE PRESENTACIÓN (cliente)
│   ├── src/
│   │   ├── pages/            pantallas (login, panel de escritorio)
│   │   ├── components/       componentes de interfaz; views/ = tarjetas del panel (riesgo, segmentos, referentes)
│   │   ├── mobile/           variantes móviles
│   │   ├── hooks/            lógica de estado reutilizable
│   │   ├── services/         cliente HTTP hacia la API (/api)
│   │   ├── utils/  constants/
│   │   └── test/             pruebas de interfaz
│   ├── public/               recursos estáticos
│   └── package.json, vite.config.ts, index.html
│
├── backend/                  SERVIDOR (API REST en capas)
│   ├── main.py               punto de entrada FastAPI: autenticación, sesiones, rutas del panel
│   ├── api/                  capa de presentación del servidor: rutas del chat (/api/query)
│   ├── core/                 capa de dominio: motor NL2SQL, sanitizador SQL, privacidad, verificador de cifras, seguridad
│   ├── ml/                   dominio analítico: variables del panel alumno-periodo, entrenamiento, calificación,
│   │                         segmentación y reportes; models/<INSTITUCION>/ guarda modelos y métricas
│   ├── knowledge/            catálogo de métricas certificadas y lógica de negocio por institución
│   ├── etl/                  capa de datos: perfiles de mapeo por institución, referentes externos
│   ├── cache/                caché de consultas
│   ├── data/                 diccionario semántico
│   ├── scripts/              tareas por lotes: cargas de prueba, ETL, diccionario de datos, usuarios de prueba
│   ├── eval/                 evaluación del NL2SQL (conjunto de referencia y resultados)
│   ├── tests/                pruebas unitarias y de integración (pytest)
│   ├── config.py, security.py, db_connector.py, conexion_admin.py
│   └── requirements.txt (versiones fijadas), requirements.lock.txt, .env.example
│
├── base_de_datos/            CAPA DE DATOS
│   ├── crear_chat_academico.sql   almacén en esquema estrella, vistas VIS_* con SESSION_CONTEXT y usuario chat_reader
│   └── datos_de_prueba/      dataset sintético anonimizado (alumnos e historial) y sus scripts de generación
│
└── scripts/
    └── demo_tesis.ps1        pipeline reproducible de punta a punta
```

## Reglas de dependencia entre capas
- `frontend` solo habla con el backend por HTTP (`/api`); nunca accede a la base de datos.
- `api/` y `main.py` usan `core/`, `ml/` y `knowledge/`; el dominio no importa las rutas.
- El SQL que genera la IA se ejecuta con `chat_reader`, que solo puede leer las vistas `VIS_*` de su institución.
- Las credenciales se leen de `backend/.env` y `backend/usuarios_prueba.local.json`, que no se versionan.
