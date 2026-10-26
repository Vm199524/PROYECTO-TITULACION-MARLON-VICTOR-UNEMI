# Pendientes para la siguiente sesión (26 de octubre de 2026)

Estado general: trabajo final generado (101 páginas, sin errores en `_verificar_coherencia.py`), prototipo versión 3.1
con validación de origen móvil, métricas por periodo y por carrera, operación del modelo (Great Expectations,
Evidently, MLflow), Metabase como alternativa de consulta y documento de gobierno de datos (LOPDP). Pruebas: 178 del
backend (8 de integración con SQL Server) y 11 de la interfaz.

## En el equipo con SQL Server (Windows)

1. Traer los cambios: `git pull` en la rama `main`.
2. Instalar las dependencias nuevas del backend (MLflow, Great Expectations y Evidently):
   `cd backend && venv\Scripts\pip install -r requirements.txt`.
3. Reentrenar y monitorear sobre SQL Server para que la base tenga las métricas por periodo y por carrera:
   `npm run reconstruir -- --desde entrenar` (el paso `mlops` corre después de `reportes`).
4. Crear las vistas de Metabase (opcional): `backend\venv\Scripts\python backend\scripts\ejecutar_sql.py
   base_de_datos\crear_vistas_metabase.sql` con `METABASE_DB_PASSWORD` en el `.env`, y luego
   `docker compose -f despliegue\metabase\docker-compose.yml up -d` (http://localhost:3001).
5. Ver los experimentos (la interfaz web necesita el paquete completo: `venv\Scripts\pip install mlflow`):
   `cd backend && venv\Scripts\mlflow ui --backend-store-uri sqlite:///datos_locales/mlflow/mlflow.db`.
6. Si se cambia el contenido, regenerar el documento, la presentación y los guiones:
   ```bat
   cd documentacion\generador_documentos
   python construir_trabajo_final.py --base ..\avances\AVANCE1_MARLON_VICTOR.docx --salida ..\avances\TRABAJO_FINAL_MARLON_VICTOR.docx
   powershell -ExecutionPolicy Bypass -File _docx_a_pdf.ps1 -Docx ..\avances\TRABAJO_FINAL_MARLON_VICTOR.docx
   python _verificar_coherencia.py
   python construir_guiones.py
   ```

## Lo que solo pueden hacer los autores

- Grabar el video de 15 minutos con `documentacion/presentacion/Presentacion_Trabajo_Final_Marlon_Victor.pptx` y
  `GUION_VIDEO.md`, subirlo a la carpeta digital y reemplazar en el Anexo E el enlace de la carpeta por el del video.
- Ensayar la sustentación con `documentacion/presentacion/GUIA_SUSTENTACION.md`.
- Validación con una carrera real de la UNEMI: autorización, evaluación de impacto y extracción según
  `documentacion/gobierno_datos/GOBIERNO_DE_DATOS.md` (`backend/scripts/anonimizar_carrera.py`).
- Prueba de usabilidad con 3 a 5 usuarios (instrumento en el Anexo D).
- Porcentaje real de Compilatio.
- Cambiar las credenciales de `sa`, `chat_reader`, `app_seguimiento` y las claves de IA antes de usar datos reales.
