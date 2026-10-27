# Metabase como alternativa de consulta

La tutoría del Avance 2 sugirió evaluar Metabase como alternativa a la consulta conversacional. El sistema no lo reemplaza: lo incorpora como **segunda vía de consulta**, pensada para analistas que prefieren tableros y preguntas con clics. La consulta en lenguaje natural sigue siendo la vía principal para la autoridad sin perfil técnico.

## Comparación

| Criterio | Consulta conversacional (NL2SQL) | Metabase |
|---|---|---|
| Usuario objetivo | Autoridad sin perfil técnico | Analista institucional |
| Forma de preguntar | Español libre: «¿qué carrera tiene más estudiantes en riesgo alto?» | Constructor visual de preguntas, filtros y tableros |
| Datos visibles | Vistas `VIS_*` de la institución activa (`SESSION_CONTEXT`) con cédula enmascarada | Solo agregados del esquema `bi` (grupos de 5 o más estudiantes) |
| Riesgo de respuesta incorrecta | Mitigado con 40 métricas certificadas, validador del árbol SQL y conjunto dorado | Bajo: el usuario construye la consulta y ve el filtro aplicado |
| Dependencia externa | Proveedores de IA (con seudonimización) | Ninguna: corre en la red de la institución |
| Costo | Uso de la API de IA | Software libre (licencia AGPL); un contenedor Docker |
| Datos personales | Nunca salen sin seudonimizar | No los ve |

Las dos vías leen el mismo almacén estrella y las mismas métricas del modelo. Por eso las cifras coinciden.

## Puesta en marcha

1. En `backend/.env`, definir `METABASE_DB_PASSWORD` con una contraseña larga que cumpla la política de SQL Server (8 o más caracteres con mayúsculas, minúsculas, números y símbolos): el login se crea con `CHECK_POLICY = ON` y el motor rechaza una contraseña débil.
2. Crear el esquema `bi` y la cuenta de solo lectura:
   ```bat
   cd backend
   python -m scripts.ejecutar_sql ..\base_de_datos\crear_vistas_metabase.sql
   ```
3. Levantar Metabase:
   ```bat
   docker compose -f despliegue\metabase\docker-compose.yml up -d
   ```
4. Abrir `http://localhost:3001`, crear la cuenta de administración y agregar la base:
   - tipo SQL Server, host `host.docker.internal`, puerto `1433`;
   - base `ALMACEN_ACADEMICO`, usuario `metabase_lector`.
5. Preguntas sugeridas:
   - tasa de retiro por carrera y periodo (`bi.VIS_BI_ABANDONO_PERIODO`);
   - activos por nivel de riesgo (`bi.VIS_BI_RIESGO_CARRERA`);
   - ROC-AUC por periodo del modelo (`bi.VIS_BI_EVALUACION_MODELO`, esquema `POR_PERIODO` u `ORIGEN_MOVIL`).

## Seguridad

- La cuenta `metabase_lector` tiene `SELECT` solo sobre el esquema `bi` y `DENY SELECT` sobre `dbo`. No ve las tablas físicas ni las vistas con cédula.
- Las vistas agregan y suprimen los grupos con menos de 5 estudiantes, para que nadie pueda reidentificar a un estudiante de una carrera pequeña.
- Metabase se publica solo en la red interna (puerto 3001). No debe exponerse a internet sin un proxy con autenticación institucional.

Autores: Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco · UNEMI · 2026
